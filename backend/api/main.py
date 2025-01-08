# api/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
from anthropic import Anthropic  # Changed this line
from pydantic import BaseModel

load_dotenv()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Anthropic client - changed to simply Anthropic()
client = Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY")
)

class Query(BaseModel):
    question: str

@app.post("/api/query")
async def process_query(query: Query):
    try:
        # Using the correct message format
        response = client.beta.messages.create(  # Changed this line
            model="claude-3-opus-20240229",
            max_tokens=1000,
            messages=[{
                "role": "user",
                "content": f"Question about plasticlist data: {query.question}"
            }]
        )
        
        return {"response": response.content[0].text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}