# api/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
from anthropic import Anthropic
from pydantic import BaseModel
import pinecone
from typing import List

load_dotenv()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize clients
anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
pinecone.init(
    api_key=os.getenv("PINECONE_API_KEY"),
    environment=os.getenv("PINECONE_ENVIRONMENT")
)
index = pinecone.Index("plasticlist")

class Query(BaseModel):
    question: str

async def get_relevant_context(query: str) -> List[str]:
    """Get relevant context from Pinecone"""
    # Get query embedding
    embedding = await anthropic_client.embeddings.create(
        model="claude-3-opus-20240229",
        input=query
    )
    
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
        # Get relevant context
        contexts = await get_relevant_context(query.question)
        
        # Create prompt with context
        prompt = f"""You are an expert on PlasticList data and findings. Use the following context to answer the question. 
Be specific and cite data when possible. If you can't answer based on the context, say so.

Context:
{' '.join(contexts)}

Question: {query.question}"""

        # Get response from Claude
        response = anthropic_client.beta.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=1000,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        
        return {"response": response.content[0].text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}