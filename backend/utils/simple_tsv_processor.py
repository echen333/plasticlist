import os
from pathlib import Path
from typing import List, Dict
import requests
import pandas as pd
from anthropic import Anthropic
from pinecone.grpc import PineconeGRPC as Pinecone
from pinecone import ServerlessSpec
import time
from dotenv import load_dotenv
import backoff
import logging
import json

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables from .env
load_dotenv()


class TSVProcessor:
    def __init__(self, index_name: str = "plasticlist3"):
        logger.info("Initializing TSV Processor...")

        # Initialize API keys
        self.voyage_api_key = os.getenv("VOYAGE_API_KEY")
        if not self.voyage_api_key:
            raise ValueError("VOYAGE_API_KEY not found in environment variables")

        # Initialize settings
        self.index_name = index_name
        self.voyage_url = "https://api.voyageai.com/v1/embeddings"

        # Important columns to process
        self.important_columns = [
            "id",
            "product_id",
            "product",
            "tags",
            "triplicate_1_sample_id",
            "triplicate_2_sample_id",
            "lot_no",
            "manufacturing_date",
            "expiration_date",
            "collected_on",
            "collected_at",
            "collection_notes",
            "blinded_name",
            "blinded_photo",
            "shipped_on",
            "shipped_in",
            "shipment_type",
            "arrived_at_lab_on",
            "analysis_method_phthalates",
            "analysis_method_bisphenols",
        ]

        # Initialize Pinecone
        self.pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

        # Create index if it doesn't exist
        self.create_index()
        self.index = self.pc.Index(self.index_name)

        logger.info("TSV Processor initialization complete")

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
            time.sleep(0.01)

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

    def format_row_text(self, row) -> str:
        """Format a row's data into a meaningful text string for embedding."""
        text_parts = []
        logger.debug(f"Processing row with product: {row.get('product', 'N/A')}")

        # Add each non-null field with its header
        for col in self.important_columns:
            if pd.notna(row[col]) and row[col] != "":
                # Clean and format the value
                value = str(row[col]).strip()
                if value:
                    text_parts.append(f"{col}: {value}")
                    logger.debug(
                        f"Added field {col}: {value[:100]}..."
                    )  # Show first 100 chars

        final_text = " | ".join(text_parts)
        logger.debug(f"Final formatted text (first 200 chars): {final_text[:200]}...")
        return final_text

    def process_tsv_file(self, filepath: str = "data/raw/samples.tsv") -> List[Dict]:
        """Process TSV file and create embeddings for each row."""
        logger.info(f"Processing TSV file: {filepath}")

        try:
            # Read TSV file
            df = pd.read_csv(filepath, sep="\t", low_memory=False)
            logger.info(f"Successfully read TSV with {len(df)} rows")

            # Debug column information
            available_columns = set(df.columns)
            missing_columns = set(self.important_columns) - available_columns
            if missing_columns:
                logger.warning(f"Missing columns in TSV: {missing_columns}")

            logger.debug("Available columns in TSV:")
            for col in available_columns:
                non_null_count = df[col].count()
                logger.debug(f"  - {col}: {non_null_count}/{len(df)} non-null values")

            vectors = []

            # Process each row
            for index, row in df.iterrows():
                try:
                    # Format row text
                    row_text = self.format_row_text(row)

                    # Debug the text being embedded
                    logger.debug(f"Row {index} - Getting embedding for text:")
                    logger.debug("=" * 80)
                    logger.debug(row_text)
                    logger.debug("=" * 80)

                    # Get embedding
                    embedding = self.get_embedding(row_text)
                    logger.debug(
                        f"Successfully got embedding of length {len(embedding)}"
                    )

                    # Create vector record
                    vector = {
                        "id": f"row_{row['id']}",
                        "values": embedding,
                        "metadata": {
                            "text": row_text,
                            "product": row["product"],
                            "product_id": row["product_id"],
                            "row_index": index,
                        },
                    }
                    vectors.append(vector)

                    if (index + 1) % 50 == 0:
                        logger.info(f"Processed {index + 1} rows")

                except Exception as e:
                    logger.error(f"Error processing row {index}: {e}")
                    continue

            return vectors

        except Exception as e:
            logger.error(f"Error processing TSV file: {e}")
            raise

    def save_vectors(
        self, vectors: List[Dict], filepath: str = "utils/tsv_embeddings.txt"
    ):
        """Save vectors to a file."""
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

    def load_vectors(self, filepath: str = "utils/tsv_embeddings.txt") -> List[Dict]:
        """Load vectors from a file."""
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

    def ingest_tsv(self):
        """Process TSV file and upload vectors to Pinecone."""
        logger.info("Starting TSV ingestion")

        # Try to load existing vectors
        vectors = self.load_vectors()

        if vectors is None:
            # Process TSV and create new vectors
            vectors = self.process_tsv_file()

            # Save vectors to file
            if vectors:
                self.save_vectors(vectors)

        # Upload to Pinecone
        if vectors:
            try:
                # Upsert in batches
                batch_size = 50
                for i in range(0, len(vectors), batch_size):
                    batch = vectors[i : i + batch_size]
                    logger.info(
                        f"Upserting batch {i // batch_size + 1}/{(len(vectors) - 1) // batch_size + 1}"
                    )
                    self.index.upsert(vectors=batch, namespace="default")
                logger.info("All vectors uploaded successfully")

            except Exception as e:
                logger.error(f"Error upserting vectors to Pinecone: {e}")
                raise


def main():
    """Process TSV file and create embeddings."""
    logger.info("Starting main function")

    # Check environment variables
    required_vars = ["PINECONE_API_KEY", "VOYAGE_API_KEY"]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        logger.error(f"Missing environment variables: {', '.join(missing)}")
        return

    try:
        processor = TSVProcessor()
        processor.ingest_tsv()
        logger.info("TSV processing complete")

    except Exception as e:
        logger.error(f"Error in main: {e}")
        raise


if __name__ == "__main__":
    main()
