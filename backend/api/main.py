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
import aiohttp
import traceback

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
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # Add Vite dev server
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
        # time.sleep(0.005)
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
            top_k=4,  # Get 30 vectors as requested
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

import pandas as pd
import ast
from io import StringIO
import sys
import contextlib
import builtins

def is_safe_code(code: str) -> bool:
    """Basic security check for Python code"""
    forbidden = ['eval', 'exec', 'open', 'os', 'sys', 'subprocess']
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in forbidden:
                return False
            # Just check for any dangerous imports
            if isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                module = node.names[0].name.split('.')[0]
                if module in forbidden:
                    return False
    except:
        return False
    return True

@contextlib.contextmanager
def capture_output():
    """Capture stdout and stderr"""
    new_out, new_err = StringIO(), StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_err
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = old_out, old_err

async def execute_python_query(query: str) -> str:
    """Execute a Python query on the TSV data"""
    if not is_safe_code(query):
        return "Error: Query contains forbidden operations"
    
    try:
        # Load your TSV data
        df = pd.read_csv('data/raw/samples.tsv', sep='\t')
        
        # Create a copy of builtins with only safe functions
        safe_builtins = {
            name: getattr(builtins, name)
            for name in [
                'print', 'len', 'range', 'str', 'int', 'float', 'bool',
                'list', 'dict', 'sum', 'min', 'max', 'round', 'sorted',
                'enumerate', 'zip', 'abs', '__import__'  # Add __import__
            ]
        }
        
        # Add the globals we want available to the query
        globals_dict = {
            '__builtins__': safe_builtins,
            'pd': pd,
            'df': df,
        }

        # Capture output
        with capture_output() as (out, err):
            # Execute the query in a clean local namespace
            local_dict = {}
            exec(query, globals_dict, local_dict)
            
            # Collect output
            output = out.getvalue()
            error_output = err.getvalue()
            
            # Check for result variable
            result_str = ""
            if 'result' in local_dict:
                # Handle DataFrames specially
                if isinstance(local_dict['result'], pd.DataFrame):
                    result_str = local_dict['result'].to_string()
                else:
                    result_str = str(local_dict['result'])

        # Combine all outputs
        final_output = ""
        if output:
            final_output += f"Output:\n{output}\n"
        if result_str:
            final_output += f"Result variable:\n{result_str}\n"
        if error_output:
            final_output += f"Errors:\n{error_output}\n"
            
        return final_output.strip()[:30000] if final_output.strip() else "No output generated"
        
    except Exception as e:
        error_trace = traceback.format_exc()
        return f"Error executing query:\n{error_trace}"

async def process_query_stream(query_id: str, question: str):
    full_response = ""
    chunks_received = 0
    
    try:
        logger.debug(f"Starting stream for: {query_id}")

        # [Previous code for PYTHON_QUERY_TOOL, context gathering, and prompt remains the same]
        PYTHON_QUERY_TOOL = {
            "name": "run_python_query",
            "description": """Executes a Python query on the PlasticList TSV data...""",  # Your existing description
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "A complete Python code snippet that uses pandas to analyze the TSV data. The data will be available as a pandas DataFrame named 'df'."
                    }
                },
                "required": ["query"]
            }
        }

        # Previous context gathering remains the same
        full_history = await get_conversation_text(query_id)
        context = await get_relevant_context(question)
        prompt = f"""Conversation so far (if any):
{full_history}

Now the user is asking:
{question}

Additional context about PlasticList and the TSV:
{context}

You have access to a Python query tool that can analyze samples.tsv data of plasticlist directly. It contains more than 600 rows and 100 columns. Use this tool when you need to perform calculations, filtering, or statistical analysis that isn't readily available in the context as the context only provides a preview of the entries in the TSV and not all of them. Note that there are over 100 different fields in the TSV so do not print all of them unless told to do so. For queries that look to filter the TSV data, check in your python program that if the final table has less than 20 entries, print the dataframe using .to_markdown() and then follow the original user query exactly. If the user is asking for the entries, display all entries again for the user (try to do in a nice table) since they cannot see the Python output. If the user asks you to do data analysis in a general form, add lots of extra debug and print statements and analyze lots of things in the Python snippets just in case it is helpful to the context. Do not use the tool if it is not necessary and the context suffices!

Make sure to transcribe exactly what was in the output of the Python program. Note that we can render markdown so include the python program in a python codeblock. 

Also, if you use the tool, you must include the Python snippet in your final response as well.  Try to be more concise in your analysis please, list only interesting facts. Also, use more markdown and bold in your answers to highlight important facts. Note that there is a string limit in your python output program so be wary of outputting too much information. """

        headers = {
            "Content-Type": "application/json",
            "X-Api-Key": os.getenv("ANTHROPIC_API_KEY"),
            "anthropic-version": "2023-06-01"
        }

        data = {
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 8024,
            "tools": [PYTHON_QUERY_TOOL],
            "tool_choice": {"type": "auto"},
            "messages": [{"role": "user", "content": prompt}],
            "stream": True
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=data
            ) as response:
                async for chunk in response.content:
                    chunk_str = chunk.decode('utf-8')
                    logger.debug(f"Raw chunk received: {chunk_str}")
                    
                    if chunk_str.startswith("data: "):
                        try:
                            json_str = chunk_str[6:]  # Remove "data: " prefix
                            if json_str.strip() == "[DONE]":
                                continue
                                
                            data = json.loads(json_str)
                            logger.debug(f"Processed JSON data: {data}")

                            # Handle message delta with tool_use stop reason
                            if data.get("type") == "message_delta" and \
                            data.get("delta", {}).get("stop_reason") == "tool_use":
                                logger.debug("Detected tool_use stop reason - continuing stream")
                                continue

                            # Handle content block start
                            if data.get("type") == "content_block_start":
                                if data.get("content_block", {}).get("type") == "tool_use":
                                    logger.debug(f"Tool use block started: {data}")
                                    current_tool_input = ""  # Reset tool input buffer
                                continue

                            # Handle content block delta
                            if data.get("type") == "content_block_delta":
                                delta = data.get("delta", {})
                                
                                # Handle text_delta
                                if delta.get("type") == "text_delta":
                                    text = delta.get("text", "")
                                    if text:
                                        full_response += text
                                        chunks_received += 1
                                        sse_data = f"data: {json.dumps({'content': text})}\n\n"
                                        logger.debug(f"Yielding text SSE data: {sse_data}")
                                        yield sse_data

                                # Handle input_json_delta (building tool input)
                                elif delta.get("type") == "input_json_delta":
                                    partial_json = delta.get("partial_json", "")
                                    logger.debug(f"Received partial JSON: {partial_json}")
                                    current_tool_input += partial_json
                                    logger.debug(f"Current tool input build: {current_tool_input}")

                                    # Try to parse complete JSON when we have a complete query
                                    try:
                                        tool_input = json.loads(current_tool_input)
                                        if "query" in tool_input:
                                            logger.debug(f"Complete tool input received: {tool_input}")
                                            query = tool_input["query"]
                                            
                                            # Execute Python query
                                            logger.debug(f"Executing Python query: {query}")
                                            query_result = await execute_python_query(query)
                                            logger.debug(f"Query execution result: {query_result}")

                                            if query_result.startswith("Error executing query:"):
                                                # Mark the query as failed in the database
                                                await update_query_in_db(query_id, query_result, "failed")
                                                
                                                # Send the error message back to the client
                                                sse_data = f"data: {json.dumps({'error': query_result})}\n\n"
                                                logger.debug(f"Yielding error SSE data: {sse_data}")
                                                yield sse_data
                                                return  # Exit the function after handling the error

                                            # Send tool result back
                                            # In your process_query_stream function, modify the tool result handling section:

                                            tool_result_data = {
                                                "model": "claude-3-5-sonnet-20241022",
                                                "max_tokens": 8024,
                                                "tools": [
                                                    {
                                                        "name": "run_python_query",
                                                        "description": "Executes a Python query on the PlasticList TSV data",
                                                        "input_schema": {
                                                            "type": "object",
                                                            "properties": {
                                                                "query": {
                                                                    "type": "string",
                                                                    "description": "A complete Python code snippet that uses pandas to analyze the TSV data. The data will be available as a pandas DataFrame named 'df'."
                                                                }
                                                            },
                                                            "required": ["query"]
                                                        }
                                                    }
                                                ],
                                                "messages": [
                                                    {
                                                        "role": "user", 
                                                        "content": prompt
                                                    },
                                                    {
                                                        "role": "assistant",
                                                        "content": [
                                                            {
                                                                "type": "tool_use",
                                                                "id": data.get("id", "default_tool_id"),
                                                                "name": "run_python_query",
                                                                "input": tool_input
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        "role": "user",
                                                        "content": [
                                                            {
                                                                "type": "tool_result",
                                                                "tool_use_id": data.get("id", "default_tool_id"),
                                                                "content": query_result
                                                            }
                                                        ]
                                                    }
                                                ]
                                            }

                                            logger.debug("Sending tool result back to Claude")
                                            tool_response_raw = await session.post(
                                                "https://api.anthropic.com/v1/messages",
                                                headers=headers,
                                                json=tool_result_data
                                            )
                                            
                                            tool_response = await tool_response_raw.json()
                                            logger.debug(f"Received tool response: {tool_response}")
                                            
                                            if 'content' in tool_response:
                                                text = tool_response['content'][0]['text']
                                                full_response += text
                                                sse_data = f"data: {json.dumps({'content': text})}\n\n"
                                                logger.debug(f"Yielding tool result SSE data: {sse_data}")
                                                yield sse_data

                                    except json.JSONDecodeError:
                                        # Not a complete JSON yet, continue building
                                        logger.debug("Incomplete JSON, continuing to build")
                                        continue

                            # Handle message stop
                            if data.get("type") == "message_stop":
                                logger.debug("Received message_stop - ending stream")
                                break

                        except json.JSONDecodeError as e:
                            logger.error(f"JSON decode error: {e}")
                            continue
                        except Exception as e:
                            logger.error(f"Error processing chunk: {e}")
                            continue

            await asyncio.sleep(0.001)

        logger.debug(f"Stream finished. Full response length: {len(full_response)}")
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


@app.post("/api/query/generate-followups")
async def generate_followups(query: Query):
    """Generate followup questions for a given query using Claude."""
    logger.debug(f"Generating followups for query: {query.model_dump_json()}")
    try:
        # Get only the most recent conversation for context
        result = supabase.table("queries").select("*").eq("id", query.conversation_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Query not found")
            
        current_query = result.data[0]
        current_response = current_query.get("response", "")
        
        # Use a simpler prompt with just the current Q&A
        prompt = f"""Based on this Q&A:
Q: {current_query['question']}
A: {current_response}

Generate exactly 3 follow-up questions that would be good to ask next. Format them exactly like this:
FOLLOWUP1: [first question]
FOLLOWUP2: [second question]
FOLLOWUP3: [third question]

Make sure each question starts with FOLLOWUPn: on its own line. Questions should be concise and directly related to the previous answer."""
        
        # Use a faster model for quicker responses
        response = anthropic_client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        
        logger.debug(f"Claude response: {response.content[0].text}")
        return {"followups": response.content[0].text}
    except Exception as e:
        logger.error(f"Error generating followups: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    logger.debug("healthy")
    return {"status": "healthy"}
