# test_supabase.py
from dotenv import load_dotenv
import os
from supabase import create_client
import uuid
from datetime import datetime

load_dotenv()

def test_supabase():
    # Initialize Supabase
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    supabase = create_client(supabase_url, supabase_key)
    
    # Create test data
    test_id = str(uuid.uuid4())
    test_data = {
        "id": test_id,
        "question": "test question",
        "status": "pending",
        "created_at": datetime.utcnow().isoformat()
    }
    
    try:
        print("Attempting to insert test data...")
        result = supabase.table("queries").insert(test_data).execute()
        print("Success! Inserted data:", result.data)
        
        print("\nAttempting to fetch the inserted data...")
        fetch_result = supabase.table("queries").select("*").eq("id", test_id).execute()
        print("Success! Fetched data:", fetch_result.data)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        
if __name__ == "__main__":
    test_supabase()