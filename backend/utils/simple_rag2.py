import os
from pathlib import Path
from typing import List, Dict
import requests
from anthropic import Anthropic
from pinecone.grpc import PineconeGRPC as Pinecone
from pinecone import ServerlessSpec
import time
from dotenv import load_dotenv
import backoff
import logging
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables from .env
load_dotenv()


class SimpleRAG:
    def __init__(self, index_name: str = "plasticlist2"):
        logger.info("Initializing SimpleRAG...")

        # Initialize API keys
        self.voyage_api_key = os.getenv("VOYAGE_API_KEY")
        if not self.voyage_api_key:
            raise ValueError("VOYAGE_API_KEY not found in environment variables")

        # Initialize clients
        self.anthropic = Anthropic()
        self.index_name = index_name
        self.voyage_url = "https://api.voyageai.com/v1/embeddings"

        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=4000,
            chunk_overlap=200,
            length_function=len,
            add_start_index=True,
        )

        # Initialize Pinecone with GRPC client
        self.pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

        # Create index if it doesn't exist
        self.create_index()
        self.index = self.pc.Index(self.index_name)
        logger.info("SimpleRAG initialization complete")

    @backoff.on_exception(
        backoff.expo,
        (requests.exceptions.RequestException, Exception),
        max_tries=3,
        max_time=30,
    )
    def get_embedding(self, text: str) -> List[float]:
        """Get embeddings from Voyage AI with exponential backoff retry."""
        logger.debug(f"Getting embedding for text of length {len(text)}")

        if len(text) > 8192:
            logger.warning("Text too long for embedding, truncating...")
            text = text[:8192]

        headers = {
            "Authorization": f"Bearer {self.voyage_api_key}",
            "Content-Type": "application/json",
        }
        data = {"model": "voyage-3-large", "input": text}

        try:
            # Add a small delay between requests to respect rate limits
            time.sleep(0.05)

            logger.debug("Sending request to Voyage AI")
            response = requests.post(self.voyage_url, headers=headers, json=data)

            if response.status_code != 200:
                logger.error(
                    f"Voyage API error: {response.status_code} - {response.text}"
                )
                response.raise_for_status()

            response_data = response.json()
            logger.debug("Successfully got response from Voyage AI")

            if (
                "data" in response_data
                and len(response_data["data"]) > 0
                and "embedding" in response_data["data"][0]
            ):
                return response_data["data"][0]["embedding"]
            else:
                logger.error(f"Unexpected response format: {response_data}")
                raise Exception("Could not find embeddings in response")

        except Exception as e:
            logger.error(f"Error in get_embedding: {str(e)}")
            raise

    def create_index(self):
        """Create Pinecone index if it doesn't exist."""
        try:
            # Check if index exists
            if self.index_name not in self.pc.list_indexes().names():
                logger.info(f"Creating new index: {self.index_name}")
                self.pc.create_index(
                    name=self.index_name,
                    dimension=1024,  # Voyage embedding dimension
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region="us-east-1"),
                )

                logger.info("Waiting for index to be ready...")
                while not self.pc.describe_index(self.index_name).status["ready"]:
                    time.sleep(1)
                logger.info("Index is ready!")
            else:
                logger.info(f"Index {self.index_name} already exists")

        except Exception as e:
            logger.error(f"Error managing index: {e}")
            raise

    def process_text_file(self, filepath: Path) -> List[Dict]:
        """Process a single text file into chunks using LangChain's text splitter."""
        logger.info(f"Processing file: {filepath}")

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read()
            logger.info(f"File read successfully, length: {len(text)}")

            # Split text into chunks using LangChain
            chunks = self.text_splitter.create_documents([text])
            vectors = []

            # Process each chunk
            for i, chunk in enumerate(chunks):
                try:
                    logger.info(f"Processing chunk {i + 1}/{len(chunks)}")
                    # Get embedding for the chunk
                    embedding = self.get_embedding(chunk.page_content)

                    # Create vector record
                    vector = {
                        "id": f"{filepath.stem}_chunk_{i}",
                        "values": embedding,
                        "metadata": {
                            "text": chunk.page_content,
                            "source": filepath.name,
                            "chunk_index": i,
                            "total_chunks": len(chunks),
                            "start_index": chunk.metadata.get("start_index", 0),
                        },
                    }
                    vectors.append(vector)
                    logger.info(f"Successfully processed chunk {i + 1}")

                except Exception as e:
                    logger.error(f"Error processing chunk {i}: {e}")
                    continue

            return vectors

        except Exception as e:
            logger.error(f"Error in process_text_file: {e}")
            raise

    def save_vectors(self, vectors: List[Dict], filepath: str = "utils/embeddings.txt"):
        """Save vectors to a file."""
        import json

        logger.info(f"Saving {len(vectors)} vectors to {filepath}")

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        try:
            with open(filepath, "w") as f:
                json.dump(vectors, f)
            logger.info("Vectors saved successfully")
        except Exception as e:
            logger.error(f"Error saving vectors: {e}")
            raise

    def load_vectors(self, filepath: str = "utils/embeddings.txt") -> List[Dict]:
        """Load vectors from a file."""
        import json

        if not os.path.exists(filepath):
            logger.info(f"No existing vectors file found at {filepath}")
            return None

        try:
            with open(filepath, "r") as f:
                vectors = json.load(f)
            logger.info(f"Loaded {len(vectors)} vectors from file")
            return vectors
        except Exception as e:
            logger.error(f"Error loading vectors: {e}")
            return None

    def ingest_files(self, data_dir: str = "data/raw"):
        """Ingest all .txt files from the data directory."""
        logger.info(f"Starting file ingestion from {data_dir}")

        # Try to load existing vectors
        all_vectors = self.load_vectors()

        if all_vectors is None:
            data_path = Path(data_dir)
            all_vectors = []

            # Process only .txt files
            for filepath in data_path.glob("*.txt"):
                logger.info(f"Found file: {filepath.name}")
                try:
                    vectors = self.process_text_file(filepath)
                    all_vectors.extend(vectors)
                    logger.info(f"Successfully processed {filepath.name}")
                except Exception as e:
                    logger.error(f"Error processing {filepath.name}: {e}")
                    continue

            # Save vectors to file
            if all_vectors:
                self.save_vectors(all_vectors)

        # Batch upsert all vectors
        if all_vectors:
            try:
                # Upsert in smaller batches
                batch_size = 50
                for i in range(0, len(all_vectors), batch_size):
                    batch = all_vectors[i : i + batch_size]
                    logger.info(
                        f"Upserting batch {i // batch_size + 1}/{(len(all_vectors) - 1) // batch_size + 1}"
                    )
                    self.index.upsert(vectors=batch, namespace="default")
                logger.info("All vectors uploaded successfully")
            except Exception as e:
                logger.error(f"Error upserting vectors to Pinecone: {e}")
                raise

    def query(self, question: str, k: int = 3) -> str:
        """Query the RAG system."""
        logger.info(f"Processing query: {question}")

        # Get embedding for the question
        query_embedding = self.get_embedding(question)

        # Search Pinecone
        results = self.index.query(
            vector=query_embedding, top_k=k, include_metadata=True, namespace="default"
        )

        # Construct prompt with context
        context_parts = []
        for match in results.matches:
            source = match.metadata.get("source", "Unknown")
            chunk_index = match.metadata.get("chunk_index", 0)
            total_chunks = match.metadata.get("total_chunks", 1)
            context_parts.append(
                f"Content from {source} (part {chunk_index + 1}/{total_chunks}):\n{match.metadata['text']}"
            )

        context = "\n\n".join(context_parts)

        prompt = f"""Here is some context about PlasticList:

    {context}

    Based on this context, please answer the following question:
    {question}

    If the context doesn't contain enough information to answer the question fully, please say so.
    """

        # Get response from Claude
        response = self.anthropic.beta.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.content[0].text


def main():
    """Test the RAG system."""
    logger.info("Starting main function")

    # Check environment variables
    required_vars = ["ANTHROPIC_API_KEY", "PINECONE_API_KEY", "VOYAGE_API_KEY"]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        logger.error(f"Missing environment variables: {', '.join(missing)}")
        return

    try:
        rag = SimpleRAG()

        # First, ingest files
        logger.info("Starting file ingestion")
        rag.ingest_files()

        # Test some queries
        test_questions = [
            "Who are the core team members?",
            "What is the methodology of the project?",
            "Who are the advisors for this project?",
        ]

        logger.info("Starting test queries")
        for question in test_questions:
            logger.info(f"Testing question: {question}")
            print(f"\nQ: {question}")
            print(f"A: {rag.query(question)}")

    except Exception as e:
        logger.error(f"Error in main: {e}")
        raise


if __name__ == "__main__":
    main()
