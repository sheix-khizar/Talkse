from fastapi import APIRouter
from app.services.rag.rag_chat import answer_question_streaming

router = APIRouter(prefix="/api/v1/rag", tags=["rag"])

@router.post("/query")
def rag_query(payload: dict):
    tenant_id = payload.get("tenant_id")
    stream_gen = answer_question_streaming(payload["question"], tenant_id)
    sources = next(stream_gen)
    answer = " ".join(list(stream_gen))
    return {"answer": answer, "sources": sources}
