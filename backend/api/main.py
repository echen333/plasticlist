from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
from anthropic import Anthropic
from pydantic import BaseModel
import pinecone
from typing import List
from supabase import create_client
from datetime import datetime
import uuid

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
    pinecone.init(
        api_key=os.getenv("PINECONE_API_KEY"),
        environment="gcp-starter"  # Using default starter environment
    )
    index = pinecone.Index("plasticlist")
    
    # Initialize Supabase with error handling
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    supabase = create_client(supabase_url, supabase_key)
except Exception as e:
    print(f"Error initializing clients: {str(e)}")
    raise

class Query(BaseModel):
    question: str

async def get_relevant_context(query: str) -> List[str]:
    """Get relevant context from Pinecone"""

    return [] # TODO

    try:
        print("Getting embedding from Anthropic...")
        # Get query embedding
        embedding = await anthropic_client.embeddings.create(
            model="claude-3-opus-20240229",
            input=query
        )
        
        print("Searching Pinecone...")
        # Search Pinecone
        results = index.query(
            vector=embedding.embeddings[0],
            top_k=5,
            include_metadata=True
        )
        
        # Extract text from results
        contexts = [match.metadata['text'] for match in results.matches]
        print(f"Found {len(contexts)} matching contexts")
        return contexts
        
    except Exception as e:
        print(f"Error in get_relevant_context: {str(e)}")
        raise
    
    # Search Pinecone
    results = index.query(
        vector=embedding.embeddings[0],
        top_k=5,
        include_metadata=True
    )
    
    # Extract text from results
    contexts = [match.metadata['text'] for match in results.matches]
    return contexts

@app.post("/api/query")
async def process_query(query: Query):
    try:
        # Generate unique ID for the query
        query_id = str(uuid.uuid4())
        
        print(f"Processing query: {query.question}")
        
        # Store initial query in Supabase
        query_data = {
            "id": query_id,
            "question": query.question,
            "created_at": datetime.utcnow().isoformat(),
            "status": "processing"
        }
        
        try:
            print("Storing query in Supabase...")
            supabase.table("queries").insert(query_data).execute()
        except Exception as e:
            print(f"Supabase insert error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        
        try:
            # Get relevant context
            print("Getting context from Pinecone...")
            contexts = await get_relevant_context(query.question)
            print(f"Found {len(contexts)} context chunks")
            
            # Create prompt with context
            prompt = f"""You are an expert on PlasticList data and findings. Use the following context to answer the question. 
Be specific and cite data when possible. If you can't answer based on the context, say so.
Context:
{' '.join(contexts)}
Question: {query.question}"""
            
            print("Sending request to Claude...")
            # Get response from Claude
            response = anthropic_client.beta.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=1000,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            response_text = response.content[0].text
            print("Got response from Claude")
            
            # Update query with response
            print("Updating Supabase with response...")
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
            print(f"Error during processing: {str(e)}")
            # Update query with error
            try:
                supabase.table("queries").update({
                    "status": "failed",
                    "error": str(e),
                    "completed_at": datetime.utcnow().isoformat()
                }).eq("id", query_id).execute()
            except Exception as db_error:
                print(f"Failed to update error in database: {str(db_error)}")
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