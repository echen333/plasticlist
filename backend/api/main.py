from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import time
import requests
from anthropic import Anthropic
from pydantic import BaseModel
from pinecone import Pinecone
from typing import List
from supabase import create_client
from datetime import datetime
import uuid
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Check required environment variables
required_env_vars = [
    "SUPABASE_URL",
    "SUPABASE_KEY",
    "ANTHROPIC_API_KEY",
    "PINECONE_API_KEY",
    "VOYAGE_API_KEY"
]

missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    raise ValueError(f"Missing environment variables: {', '.join(missing_vars)}")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize clients
try:
    anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    voyage_api_key = os.getenv("VOYAGE_API_KEY")
    voyage_url = "https://api.voyageai.com/v1/embeddings"
    
    # Initialize Pinecone with new class-based approach
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    
    # Debug: List all indexes
    indexes = pc.list_indexes()
    logger.info(f"Available Pinecone indexes: {indexes}")
    
    index = pc.Index("plasticlist2")
    # Debug: Get index stats
    stats = index.describe_index_stats()
    logger.info(f"Index stats: {stats}")
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    supabase = create_client(supabase_url, supabase_key)
except Exception as e:
    logger.error(f"Error initializing clients: {str(e)}")
    raise

class Query(BaseModel):
    question: str

async def get_embedding(text: str) -> List[float]:
    """Get embeddings from Voyage AI."""
    logger.debug(f"Getting embedding for text of length {len(text)}")
    
    if len(text) > 8192:
        logger.warning("Text too long for embedding, truncating...")
        text = text[:8192]
    
    headers = {
        "Authorization": f"Bearer {voyage_api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "voyage-3-large",
        "input": text
    }
    
    try:
        # Add a small delay between requests to respect rate limits
        time.sleep(0.05)
        
        logger.debug("Sending request to Voyage AI")
        response = requests.post(voyage_url, headers=headers, json=data)
        
        if response.status_code != 200:
            logger.error(f"Voyage API error: {response.status_code} - {response.text}")
            response.raise_for_status()
        
        response_data = response.json()
        logger.debug("Successfully got response from Voyage AI")
        
        if 'data' in response_data and len(response_data['data']) > 0 and 'embedding' in response_data['data'][0]:
            logger.debug("got embedding")
            return response_data['data'][0]['embedding']
        else:
            logger.error(f"Unexpected response format: {response_data}")
            raise Exception("Could not find embeddings in response")
            
    except Exception as e:
        logger.error(f"Error in get_embedding: {str(e)}")
        raise

async def get_relevant_context(query: str) -> str:
    """Get relevant context from Pinecone"""
    try:
        logger.info("Getting embedding from Voyage AI...")
        query_embedding = await get_embedding(query)
        logger.info(f"Embedding dimension: {len(query_embedding)}")
        
        logger.info("Searching Pinecone...")
        # Search Pinecone with lower score threshold
        results = index.query(
            vector=query_embedding,
            top_k=3,
            include_metadata=True,
            score_threshold=0.0,
            namespace="default"
        )
        
        # Debug log the entire results
        logger.info(f"Pinecone results: {results}")
        
        # Check if we have matches in the results
        matches = results.get('matches', []) if isinstance(results, dict) else results.matches
        
        # Debug log individual matches
        for match in matches:
            logger.info(f"Match score: {match.get('score', 'N/A')}, ID: {match.get('id', 'N/A')}")
            
        # Construct context string
        context = "\n\n".join([
            f"Content from {match['id']}:\n{match['metadata']['text']}"
            for match in matches
        ])
        logger.info(f"Found {len(matches)} matching contexts")
        return context
        
    except Exception as e:
        logger.error(f"Error in get_relevant_context: {str(e)}")
        raise

@app.post("/api/query")
async def process_query(query: Query):
    try:
        # Generate unique ID for the query
        query_id = str(uuid.uuid4())
        
        logger.info(f"Processing query: {query.question}")
        
        # Store initial query in Supabase
        query_data = {
            "id": query_id,
            "question": query.question,
            "created_at": datetime.utcnow().isoformat(),
            "status": "processing"
        }
        
        try:
            logger.info("Storing query in Supabase...")
            supabase.table("queries").insert(query_data).execute()
        except Exception as e:
            logger.error(f"Supabase insert error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        
        try:
            # Get relevant context
            logger.info("Getting context from Pinecone...")
            context = await get_relevant_context(query.question)
            
            # Create prompt with context
            prompt = f"""Here is some context about PlasticList:

{context}

Based on this context, please answer the following question:
{query.question}

If the context doesn't contain enough information to answer the question fully, please say so."""
            
            logger.info("Sending request to Claude...")
            # Get response from Claude
            response = anthropic_client.beta.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=1000,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            response_text = response.content[0].text
            logger.info("Got response from Claude")
            
            # Update query with response
            logger.info("Updating Supabase with response...")
            supabase.table("queries").update({
                "status": "completed",
                "response": response_text,
                "completed_at": datetime.utcnow().isoformat()
            }).eq("id", query_id).execute()
            
            return {
                "id": query_id,
                "response": response_text
            }
            
        except Exception as e:
            logger.error(f"Error during processing: {str(e)}")
            # Update query with error
            try:
                supabase.table("queries").update({
                    "status": "failed",
                    "error": str(e),
                    "completed_at": datetime.utcnow().isoformat()
                }).eq("id", query_id).execute()
            except Exception as db_error:
                logger.error(f"Failed to update error in database: {str(db_error)}")
            raise HTTPException(status_code=500, detail=str(e))
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/query/{query_id}")
async def get_query(query_id: str):
    try:
        result = supabase.table("queries").select("*").eq("id", query_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Query not found")
        return result.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}