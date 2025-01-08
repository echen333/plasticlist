import os
from pathlib import Path
from uuid import uuid4
import pandas as pd
from anthropic import Anthropic
import pinecone
from typing import Dict, List, Any
import tiktoken

class DataProcessor:
    def __init__(self, raw_data_dir: str = "data/raw"):
        """
        Initialize the DataProcessor with configurations.
        
        Args:
            raw_data_dir: Directory containing the raw data files
        """
        self.raw_data_dir = Path(raw_data_dir)
        self.tokenizer = tiktoken.get_encoding("cl100k_base")  # Claude's base tokenizer
        self.CHUNK_SIZE = 1000  # tokens
        self.CHUNK_OVERLAP = 100  # tokens
        
        # Initialize Anthropic and Pinecone clients
        self.anthropic = Anthropic()
        pinecone.init(
            api_key=os.getenv("PINECONE_API_KEY"),
            environment=os.getenv("PINECONE_ENVIRONMENT")
        )
        self.index = pinecone.Index(os.getenv("PINECONE_INDEX"))

    def count_tokens(self, text: str) -> int:
        """Count the number of tokens in a text string."""
        return len(self.tokenizer.encode(text))

    def process_text_file(self, filepath: Path) -> List[Dict[str, Any]]:
        """
        Process a text file into chunks if needed.
        Small files are kept as single chunks.
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()
        
        # For short files (less than 2 chunk sizes), keep as single chunk
        if self.count_tokens(text) < self.CHUNK_SIZE * 2:
            return [{
                'text': text,
                'source': str(filepath.relative_to(self.raw_data_dir)),
                'type': 'text'
            }]
        
        # For longer files, split into chunks
        chunks = []
        current_chunk = ""
        current_tokens = 0
        
        for line in text.split('\n'):
            line_tokens = self.count_tokens(line + '\n')
            
            if current_tokens + line_tokens > self.CHUNK_SIZE:
                if current_chunk:
                    chunks.append({
                        'text': current_chunk.strip(),
                        'source': str(filepath.relative_to(self.raw_data_dir)),
                        'type': 'text'
                    })
                current_chunk = line + '\n'
                current_tokens = line_tokens
            else:
                current_chunk += line + '\n'
                current_tokens += line_tokens
        
        if current_chunk:
            chunks.append({
                'text': current_chunk.strip(),
                'source': str(filepath.relative_to(self.raw_data_dir)),
                'type': 'text'
            })
        
        return chunks

    def process_tsv(self, filepath: Path) -> List[Dict[str, Any]]:
        """
        Process TSV file into chunks, separating metadata from measurements.
        """
        df = pd.read_csv(filepath, sep='\t')
        chunks = []
        
        # Separate metadata columns from measurement columns
        metadata_cols = [
            'product', 'tags', 'lot_no', 'manufacturing_date', 
            'expiration_date', 'collected_on', 'collected_at',
            'collection_notes', 'shipped_in', 'shipment_type'
        ]
        
        measurement_cols = [col for col in df.columns if col.endswith('_ng_g')]
        
        for idx, row in df.iterrows():
            # Create natural language description of metadata
            metadata_parts = []
            
            if pd.notna(row.get('product')):
                metadata_parts.append(f"Product: {row['product']}")
            if pd.notna(row.get('tags')):
                metadata_parts.append(f"Tags: {row['tags']}")
            if pd.notna(row.get('collected_at')):
                metadata_parts.append(f"Collected at: {row['collected_at']}")
            if pd.notna(row.get('collection_notes')):
                metadata_parts.append(f"Collection notes: {row['collection_notes']}")
            if pd.notna(row.get('shipped_in')):
                metadata_parts.append(f"Shipped in: {row['shipped_in']}")
            if pd.notna(row.get('manufacturing_date')):
                metadata_parts.append(f"Manufacturing date: {row['manufacturing_date']}")
            if pd.notna(row.get('expiration_date')):
                metadata_parts.append(f"Expiration date: {row['expiration_date']}")
            
            metadata_text = ". ".join(metadata_parts) + "."
            
            # Store measurements separately in metadata
            measurements = {
                col: row[col] 
                for col in measurement_cols 
                if pd.notna(row.get(col))
            }
            
            chunks.append({
                'text': metadata_text.strip(),
                'source': f"{filepath.relative_to(self.raw_data_dir)}:row_{idx}",
                'type': 'sample_data',
                'measurements': measurements,
                'row_id': idx
            })
        
        return chunks

    def process_all_files(self) -> None:
        """
        Process all files in the raw data directory and upload to Pinecone.
        """
        all_chunks = []
        
        # Process all files in the raw data directory
        for filepath in self.raw_data_dir.glob('*.*'):
            if filepath.suffix == '.tsv':
                chunks = self.process_tsv(filepath)
            elif filepath.suffix == '.txt':
                chunks = self.process_text_file(filepath)
            else:
                print(f"Skipping unsupported file: {filepath}")
                continue
            
            all_chunks.extend(chunks)
        
        # Create embeddings and upload to Pinecone
        for chunk in all_chunks:
            # Get embedding from Anthropic
            embedding = self.anthropic.embeddings.create(
                model="claude-3-embedding-3",
                text=chunk['text']
            ).embeddings[0]
            
            # Prepare metadata
            metadata = {
                'text': chunk['text'],
                'source': chunk['source'],
                'type': chunk['type']
            }
            
            # Add measurements to metadata if it's sample data
            if chunk['type'] == 'sample_data':
                metadata['measurements'] = chunk['measurements']
                metadata['row_id'] = chunk['row_id']
            
            # Upload to Pinecone
            self.index.upsert([(str(uuid4()), embedding, metadata)])
            
            print(f"Processed and uploaded chunk from: {chunk['source']}")

def main():
    """Main function to run the data processor."""
    # Ensure environment variables are set
    required_env_vars = [
        "ANTHROPIC_API_KEY",
        "PINECONE_API_KEY",
        "PINECONE_ENVIRONMENT",
        "PINECONE_INDEX"
    ]
    
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        print(f"Missing required environment variables: {', '.join(missing_vars)}")
        return
    
    processor = DataProcessor()
    processor.process_all_files()
    print("Data processing complete!")

if __name__ == "__main__":
    main()