from fastapi import APIRouter, HTTPException
from app.services.rag.rag_chat import answer_question_streaming

router = APIRouter(prefix="/api/v1/rag", tags=["rag"])

@router.post("/query")
def rag_query(payload: dict):
    tenant_id = payload.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id is required")
    stream_gen = answer_question_streaming(tenant_id, payload["question"])
    sources = next(stream_gen)
    answer = " ".join(list(stream_gen))
    return {"answer": answer, "sources": sources}
