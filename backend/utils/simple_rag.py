import os
from pathlib import Path
from typing import List, Dict
import requests
from anthropic import Anthropic
import pinecone
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

class SimpleRAG:
    def __init__(self, index_name: str = "plasticlist"):
        # Initialize API keys
        self.voyage_api_key = os.getenv("VOYAGE_API_KEY")
        if not self.voyage_api_key:
            raise ValueError("VOYAGE_API_KEY not found in environment variables")
            
        # Initialize clients
        self.anthropic = Anthropic()
        self.index_name = index_name
        self.voyage_url = "https://api.voyageai.com/v1/embeddings"
        
        # Initialize Pinecone
        pinecone.init(
            api_key=os.getenv("PINECONE_API_KEY"),
            environment="gcp-starter"
        )
        
        # Create index if it doesn't exist
        self.create_index()
        self.index = pinecone.Index(self.index_name)
    
    def create_index(self):
        """Create Pinecone index if it doesn't exist or recreate if dimensions don't match."""
        try:
            # Check if index exists
            existing_indexes = pinecone.list_indexes()
            
            # If index exists, check its dimension
            if self.index_name in existing_indexes:
                index_info = pinecone.describe_index(self.index_name)
                current_dim = index_info.dimension
                
                # If dimensions don't match, delete and recreate
                if current_dim != 1536:
                    print(f"Index exists but has wrong dimension ({current_dim}). Recreating...")
                    pinecone.delete_index(self.index_name)
                    # Wait a bit for deletion to complete
                    import time
                    time.sleep(5)
                else:
                    print(f"Index {self.index_name} exists with correct dimensions")
                    return

            # Create new index
            print(f"Creating new index: {self.index_name}")
            pinecone.create_index(
                name=self.index_name,
                dimension=1536,  # Voyage AI embeddings dimension
                metric="cosine",
                pod_type="starter"
            )
            
            print("Waiting for index to be ready... (this can take 1-2 minutes)")
            while True:
                try:
                    index_info = pinecone.describe_index(self.index_name)
                    if index_info.status.get('ready', False):
                        print("Index is ready!")
                        break
                except:
                    pass
                print(".", end="", flush=True)
                time.sleep(5)
                
        except Exception as e:
            print(f"Error managing index: {e}")
            raise

    def get_embedding(self, text: str) -> List[float]:
        """Get embeddings from Voyage AI."""
        headers = {
            "Authorization": f"Bearer {self.voyage_api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "voyage-large-2",
            "input": text
        }
        
        try:
            response = requests.post(self.voyage_url, headers=headers, json=data)
            response.raise_for_status()  # Raise an exception for bad status codes
            
            response_data = response.json()
            print("Voyage AI Response:", response_data)  # For debugging
            
            # Return the embedding from the response
            if 'data' in response_data and len(response_data['data']) > 0 and 'embedding' in response_data['data'][0]:
                print("SUCCESS")
                return response_data['data'][0]['embedding']
            else:
                print(f"Unexpected response format: {response_data}")
                raise Exception("Could not find embeddings in response")
                
        except requests.exceptions.RequestException as e:
            print(f"Error making request to Voyage AI: {e}")
            print(f"Response content: {response.text if response else 'No response'}")
            raise

    def process_text_file(self, filepath: Path) -> Dict:
        """Process a single text file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()
            
        # Get embedding
        embedding = self.get_embedding(text)
        
        return {
            'text': text,
            'embedding': embedding,
            'source': filepath.name
        }

    def ingest_files(self, data_dir: str = "data/raw"):
        """Ingest all .txt files from the data directory."""
        data_path = Path(data_dir)
        
        # Process only .txt files
        for filepath in data_path.glob("*.txt"):
            print(f"Processing {filepath.name}...")
            doc = self.process_text_file(filepath)
            
            # Upload to Pinecone with correct format
            vectors = [{
                'id': filepath.name,
                'values': doc['embedding'],
                'metadata': {'text': doc['text']}
            }]

            print(vectors)
            
            self.index.upsert(vectors=vectors)
            print(f"Uploaded {filepath.name} to Pinecone")

    def query(self, question: str, k: int = 3) -> str:
        """Query the RAG system."""
        # Get embedding for the question
        query_embedding = self.get_embedding(question)
        
        # Search Pinecone
        results = self.index.query(
            vector=query_embedding,
            top_k=k,
            include_metadata=True
        )
        
        # Construct prompt with context
        context = "\n\n".join([
            f"Content from {match.id}:\n{match.metadata['text']}"
            for match in results.matches
        ])
        
        prompt = f"""Here is some context about PlasticList:

{context}

Based on this context, please answer the following question:
{question}

If the context doesn't contain enough information to answer the question fully, please say so.
"""
        
        # Get response from Claude
        response = self.anthropic.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1000,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        
        return response.content[0].text

def main():
    """Test the RAG system."""
    # Check environment variables
    required_vars = ["ANTHROPIC_API_KEY", "PINECONE_API_KEY", "VOYAGE_API_KEY"]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        print(f"Missing environment variables: {', '.join(missing)}")
        return

    rag = SimpleRAG()
    
    # First, ingest files
    print("Ingesting files...")
    rag.ingest_files()
    
    # Test some queries
    test_questions = [
        "Who are the core team members?",
        "What is the methodology of the project?",
        "Who are the advisors for this project?"
    ]
    
    print("\nTesting queries...")
    for question in test_questions:
        print(f"\nQ: {question}")
        print(f"A: {rag.query(question)}")

if __name__ == "__main__":
    main()