# app/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .tasks import parse_resume_task, create_embedding_task, embedding_model, qdrant_client

app = FastAPI(title="AI Blackbox API")

# Pydantic models for request body validation
class ResumeParseRequest(BaseModel):
    resumeUrl: str

class SyncRequest(BaseModel):
    collection: str
    documentId: str
    textContent: str
    
class MatchRequest(BaseModel):
    collection: str
    textContent: str
    limit: int = 10

# --- API Endpoints ---

@app.get("/health")
def read_health():
    """Health check endpoint."""
    return {"status": "ok"}

@app.post("/v1/parsing/resume")
def submit_resume_parsing(request: ResumeParseRequest):
    """Asynchronous endpoint to start resume parsing."""
    task = parse_resume_task.delay(request.resumeUrl)
    return {"taskId": task.id, "status": "processing"}

@app.post("/internal/sync")
def sync_document(request: SyncRequest):
    """Endpoint for the main product to send us new data to be embedded."""
    task = create_embedding_task.delay(request.collection, request.documentId, request.textContent)
    return {"taskId": task.id, "status": "syncing"}

@app.post("/v1/matching/search")
def find_matches(request: MatchRequest):
    """
    Finds the best matches for a given text in a collection.
    This is a synchronous, real-time operation.
    """
    try:
        # 1. Create a vector embedding from the incoming text content on the fly.
        vector = embedding_model.encode(request.textContent).tolist()

        # 2. Search the specified Qdrant collection for the most similar vectors.
        search_result = qdrant_client.search(
            collection_name=request.collection,
            query_vector=vector,
            limit=request.limit,
        )
        
        # 3. Format the results into the clean JSON structure the product team expects.
        ranked_results = [{"id": hit.id, "score": hit.score} for hit in search_result]
        
        return {"rankedResults": ranked_results}

    except Exception as e:
        print(f"Error during matching search: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during search.")