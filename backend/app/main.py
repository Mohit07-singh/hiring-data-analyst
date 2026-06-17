from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.core.generator import generate_response
from app.database.vector_store import get_vector_store

app = FastAPI(
    title="Hiring Data RAG API",
    description="Backend API for retrieving and querying candidate profile database.",
    version="1.0.0"
)

# Enable CORS for frontend integration (React/Next.js/Plain HTML)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this to specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str
    k: int = 5

class QueryResponse(BaseModel):
    response: str

@app.post("/api/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest):
    """
    Accepts a natural language search query, performs RAG similarity search,
    and returns a response synthesized by the LLM.
    """
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    
    try:
        response_text = generate_response(request.query, k=request.k)
        return QueryResponse(response=response_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    """
    Checks the status of the API server and connectivity to ChromaDB.
    """
    try:
        db = get_vector_store()
        count = db._collection.count()
        return {
            "status": "healthy",
            "database": "connected",
            "indexed_candidates": count
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }
