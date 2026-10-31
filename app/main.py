
from fastapi import FastAPI, HTTPException

from app.schemas import ChatRequest, ChatResponse
from app.rag.pipeline import run_rag

app = FastAPI(
    title="Orbit Shop RAG Support API",
    description="AI-powered customer support using RAG",
    version="1.0.0",
)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "message": "RAG Support API is running",
    }


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    try:
        result = run_rag(
            question=request.question,
            top_k=request.top_k,
        )
        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process question: {str(e)}",
        )
