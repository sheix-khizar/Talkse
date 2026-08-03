from fastapi import APIRouter
from app.services.rag.rag_chat import answer_question_streaming

router = APIRouter(prefix="/api/v1/rag", tags=["rag"])

@router.post("/query")
def rag_query(payload: dict):
    stream_gen = answer_question_streaming(payload["question"])
    sources = next(stream_gen)
    answer = " ".join(list(stream_gen))
    return {"answer": answer, "sources": sources}
