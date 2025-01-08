# Import the Pinecone library
from pinecone.grpc import PineconeGRPC as Pinecone
from pinecone import ServerlessSpec
import time
from dotenv import load_dotenv
import os

load_dotenv()

# pinecone.init(api_key=os.getenv('PINECONE_API_KEY'))

# Initialize a Pinecone client with your API key
pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))

# Define a sample dataset where each item has a unique ID and piece of text
data = [
    {"id": "vec1", "text": "Apple is a popular fruit known for its sweetness and crisp texture."},
    {"id": "vec2", "text": "The tech company Apple is known for its innovative products like the iPhone."},
    {"id": "vec3", "text": "Many people enjoy eating apples as a healthy snack."},
    {"id": "vec4", "text": "Apple Inc. has revolutionized the tech industry with its sleek designs and user-friendly interfaces."},
    {"id": "vec5", "text": "An apple a day keeps the doctor away, as the saying goes."},
    {"id": "vec6", "text": "Apple Computer Company was founded on April 1, 1976, by Steve Jobs, Steve Wozniak, and Ronald Wayne as a partnership."}
]

# Convert the text into numerical vectors that Pinecone can index
embeddings = pc.inference.embed(
    model="multilingual-e5-large",
    inputs=[d['text'] for d in data],
    parameters={"input_type": "passage", "truncate": "END"}
)

print(embeddings)

print(embeddings.data[0]['values'])
assert(len(embeddings.data[0]['values']) == 1024)

print("trying to create an index")

# Create a serverless index
index_name = "example-index"

# if not pc.has_index(index_name):
if index_name not in pc.list_indexes().names():
    pc.create_index(
        name=index_name,
        dimension=1024,
        metric="cosine",
        spec=ServerlessSpec(
            cloud='aws', 
            region='us-east-1'
        ) 
    ) 

# Wait for the index to be ready
while not pc.describe_index(index_name).status['ready']:
    time.sleep(1)


# upserting vectors
print("upserting vectors")

# Target the index where you'll store the vector embeddings
index = pc.Index("example-index")

# Prepare the records for upsert
# Each contains an 'id', the embedding 'values', and the original text as 'metadata'
records = []
for d, e in zip(data, embeddings):
    records.append({
        "id": d['id'],
        "values": e['values'],
        "metadata": {'text': d['text']}
    })

# print(records)
# Upsert the records into the index
index.upsert(
    vectors=records,
    namespace="example-namespace"
)

