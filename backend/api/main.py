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
from fastapi import Request
import uuid
import logging
import json
import asyncio
from typing import Optional

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
    conversation_id: str

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

async def get_conversation_text(query_id: str) -> str:
    """Fetch conversation history for the given query ID."""
    # Get current query
    result = supabase.table("queries").select("*").eq("id", query_id).execute()
    logger.debug(f"Current query result: {result.data}")
    
    if not result.data:
        return ""
    
    current_query = result.data[0]
    conversation_id = current_query["conversation_id"]
    if not conversation_id:
        return ""

    # Fetch all conversation queries
    conversation_res = (
        supabase.table("queries")
        .select("*")
        .eq("conversation_id", conversation_id)
        .execute()
    )
    
    logger.debug(f"Full conversation: {conversation_res.data}")
    
    # Build conversation history chronologically
    conversation_data = sorted(conversation_res.data, key=lambda x: x["created_at"])
    conversation_blocks = []
    
    for row in conversation_data:
        # Skip current query
        if row["id"] == query_id:
            continue
            
        # Include all previous Q&A pairs
        response = row.get("response", "")
        if response:  # Include if there's any response
            conversation_blocks.append(f"Q: {row['question']}\nA: {response}")
    
    history = "\n\n".join(conversation_blocks)
    logger.debug(f"Final history: {history}")
    return history

async def process_query_stream(query_id: str, question: str):
    full_response = ""
    chunks_received = 0
    
    try:
        logger.debug(f"Starting stream for: {query_id}")

        # 1. Fetch the entire conversation so far
        full_history = await get_conversation_text(query_id)

        # 2. Add your general "PlasticList" context
        context = await get_relevant_context(question)

        # 3. Build the final prompt
        prompt = f"""Conversation so far (if any):
{full_history}

Now the user is asking:
{question}

Additional context about PlasticList:
{context}

You are very smart! Please answer the user's latest question in detail to the best of your ability.
"""

        logger.debug(f"YOOYOYO{prompt[:1000]}")
        stream = anthropic_client.beta.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
            stream=True
        )

        logger.debug("Stream created, processing chunks...")
        
        for message in stream:  # Regular for loop, not async
            if message.type == 'content_block_delta' and hasattr(message.delta, 'text'):
                text = message.delta.text
                chunks_received += 1
                full_response += text
                sse_data = f"data: {json.dumps({'content': text})}\n\n"
                yield sse_data
                await asyncio.sleep(0.01)
        
        # 4. Once done, update DB and yield end signal
        logger.debug("updating query in db")
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

class InitialQuery(BaseModel):
    question: str

class FollowUpQuery(BaseModel):
    question: str
    conversation_id: str

@app.post("/api/query/initial")
async def create_initial_query(query: InitialQuery):
    logger.debug(f"Received initial query: {query.model_dump_json()}")
    query_id = str(uuid.uuid4())
    conversation_id = str(uuid.uuid4())  # Generate new conversation_id

    query_data = {
        "id": query_id,
        "question": query.question,
        "created_at": datetime.utcnow().isoformat(),
        "status": "processing",
        "conversation_id": conversation_id  # New conversation
    }

    try:
        supabase.table("queries").insert(query_data).execute()
        return {"id": query_id, "conversation_id": conversation_id}
    except Exception as e:
        logger.error(f"Error creating initial query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/query/followup")
async def create_followup_query(query: FollowUpQuery):
    logger.debug(f"Received followup query: {query.model_dump_json()}")
    query_id = str(uuid.uuid4())

    query_data = {
        "id": query_id,
        "question": query.question,
        "created_at": datetime.utcnow().isoformat(),
        "status": "processing",
        "conversation_id": query.conversation_id  # Use existing conversation
    }

    try:
        supabase.table("queries").insert(query_data).execute()
        return {"id": query_id, "conversation_id": query.conversation_id}
    except Exception as e:
        logger.error(f"Error creating followup query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/query/{query_id}/stream")
async def stream_query(query_id: str):
    """Stream the response for a given query ID"""
    logger.debug("Streaming right now")
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
    try:
        # 1. Get the specific query
        result = supabase.table("queries").select("*").eq("id", query_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Query not found")
        query_data = result.data[0]
        logger.debug(f"query_data: {query_data}")

        # 2. Safely retrieve conversation_id
        conversation_id = query_data.get("conversation_id")
        
        # 3. Fetch entire conversation if we do have conversation_id
        conversation_res = (
            supabase.table("queries")
            .select("*")
            .eq("conversation_id", conversation_id)
            # .order("created_at", ascending=True) # TODO!!
            .execute()
        )

        logger.debug(f"current_query {query_data} conversation: {conversation_res.data}")
        return {
            "current_query": query_data,
            "conversation": conversation_res.data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health_check():
    logger.debug("healthy")
    return {"status": "healthy"}