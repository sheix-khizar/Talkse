import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Make sure we can import app modules properly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "services"))

from app.core.config import settings
from app.services import db
from app.api.v1 import calls, appointments, rag, clinic
from app.ws import voice_gateway

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    db.init_db()
    db.init_rag_tables()
    yield
    # Shutdown

app = FastAPI(title="Talkse API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(calls.router)
app.include_router(appointments.router)
app.include_router(rag.router)
app.include_router(clinic.router)
app.include_router(voice_gateway.router)
