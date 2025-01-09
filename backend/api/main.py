from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
import os
import time
import requests
from anthropic import Anthropic
from pydantic import BaseModel
from pinecone import Pinecone
from typing import List, AsyncGenerator
from supabase import create_client
from datetime import datetime
import uuid
import logging
import json
import asyncio

# Set up logging
# logging.basicConfig(level=logging.INFO)
logging.basicConfig(level=logging.DEBUG)
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
    expose_headers=["*"]  # Needed for EventSource
)

# Initialize clients
try:
    anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    voyage_api_key = os.getenv("VOYAGE_API_KEY")
    voyage_url = "https://api.voyageai.com/v1/embeddings"
    
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    index_general = pc.Index("plasticlist2")
    index_tsv = pc.Index("plasticlist3")
    
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
    if len(text) > 8192:
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
        time.sleep(0.05)
        response = requests.post(voyage_url, headers=headers, json=data)
        
        if response.status_code != 200:
            logger.error(f"Voyage API error: {response.status_code} - {response.text}")
            response.raise_for_status()
        
        response_data = response.json()
        
        if 'data' in response_data and len(response_data['data']) > 0 and 'embedding' in response_data['data'][0]:
            return response_data['data'][0]['embedding']
        else:
            raise Exception("Could not find embeddings in response")
            
    except Exception as e:
        logger.error(f"Error in get_embedding: {str(e)}")
        raise

async def get_relevant_context(query: str) -> str:
    """Get relevant context from both Pinecone indices"""
    try:
        # Get query embedding once and reuse
        query_embedding = await get_embedding(query)
        
        # Get context from general knowledge index (plasticlist2)
        general_results = index_general.query(
            vector=query_embedding,
            top_k=3,
            include_metadata=True,
            score_threshold=0.0,
            namespace="default"
        )
        
        # Get context from TSV data index (plasticlist3)
        tsv_results = index_tsv.query(
            vector=query_embedding,
            top_k=30,  # Get 30 vectors as requested
            include_metadata=True,
            score_threshold=0.0,
            namespace="default"
        )
        
        # Process general knowledge results
        general_matches = general_results.get('matches', []) if isinstance(general_results, dict) else general_results.matches
        general_context = "\n\n".join([
            f"Content from general knowledge ({match['id']}):\n{match['metadata']['text']}"
            for match in general_matches
        ])
        
        # Process TSV data results
        tsv_matches = tsv_results.get('matches', []) if isinstance(tsv_results, dict) else tsv_results.matches
        tsv_context = "\n\n".join([
            f"TSV Entry {i+1}:\n{match['metadata']['text']}"
            for i, match in enumerate(tsv_matches)
        ])
        
        # Combine contexts with clear separation
        combined_context = f"""General Knowledge:\n{general_context}\n\nTSV Data:\n{tsv_context}"""
        
        return combined_context
        
    except Exception as e:
        logger.error(f"Error in get_relevant_context: {str(e)}")
        raise

async def process_query_stream(query_id: str, question: str):
    full_response = ""
    chunks_received = 0
    
    try:
        logger.debug(f"Starting stream for: {query_id}")
        context = await get_relevant_context(question)
        
        prompt = f"""Here is some context about PlasticList:
{context}
Based on this context, please answer the following question:
{question}
If the context doesn't contain enough information to answer the question fully, please say so."""

        stream = anthropic_client.beta.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
            stream=True
        )
        
        logger.debug("Stream created, processing chunks...")
        
        for message in stream:  # Regular for loop, not async
            logger.debug(f"Event type: {message.type}")
            if message.type == 'content_block_delta' and hasattr(message.delta, 'text'):
                text = message.delta.text
                chunks_received += 1
                full_response += text
                sse_data = f"data: {json.dumps({'content': text})}\n\n"
                logger.debug(f"Chunk {chunks_received}: {text}")
                yield sse_data
                await asyncio.sleep(0.01)
        
        # Update database and end stream
        await update_query_in_db(query_id, full_response, "completed")
        yield f"data: {json.dumps({'end': True, 'total_chunks': chunks_received})}\n\n"
        
    except Exception as e:
        logger.error(f"Error in stream: {str(e)}")
        await update_query_in_db(query_id, full_response, "failed", str(e))
        yield f"data: {json.dumps({'error': str(e)})}\n\n"

async def update_query_in_db(query_id: str, response: str, status: str, error: str = None):
    try:
        data = {
            "status": status,
            "response": response,
            "completed_at": datetime.utcnow().isoformat()
        }
        if error:
            data["error"] = error
        supabase.table("queries").update(data).eq("id", query_id).execute()
    except Exception as e:
        logger.error(f"Database update failed: {str(e)}")

@app.post("/api/query")
async def create_query(query: Query):
    """Create a new query and return its ID immediately"""
    query_id = str(uuid.uuid4())
    
    # Store initial query in Supabase
    query_data = {
        "id": query_id,
        "question": query.question,
        "created_at": datetime.utcnow().isoformat(),
        "status": "processing"
    }
    
    try:
        supabase.table("queries").insert(query_data).execute()
        return {"id": query_id}
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/query/{query_id}/stream")
async def stream_query(query_id: str):
    """Stream the response for a given query ID"""
    try:
        # Get query details from Supabase
        result = supabase.table("queries").select("*").eq("id", query_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Query not found")
        
        query_data = result.data[0]

        # Add debug log for completed responses
        if query_data["status"] == "completed":
            logger.debug(f"Sending completed response: {query_data['response']}")
        
        # Set up SSE headers
        headers = {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
        
        if query_data["status"] == "completed":
            # If already completed, return full response immediately
            return StreamingResponse(
                content=iter([f"data: {json.dumps({'content': query_data['response']})}\n\n"]),
                media_type="text/event-stream",
                headers=headers
            )
        
        # Start streaming response
        return StreamingResponse(
            content=process_query_stream(query_id, query_data["question"]),
            media_type="text/event-stream",
            headers=headers
        )
    except Exception as e:
        logger.error(f"Streaming error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/query/{query_id}")
async def get_query(query_id: str):
    """Get query details"""
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