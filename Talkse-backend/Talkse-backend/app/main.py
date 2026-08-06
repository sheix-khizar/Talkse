
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("talkse")
from app.core.config import settings
from app.services import db
from app.api.v1 import calls, appointments, rag, clinic, tenants, signalwire_webhook
from app.ws import voice_gateway, signalwire_gateway

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    db.init_db()
    db.init_tenant_tables()
    db.init_rag_tables()
    db.migrate_tenant_columns()
    db.migrate_phone_column()
    db.init_tts_usage_table()
    db.init_call_logs_table()
    db.enable_tenant_rls()
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

from fastapi import Request

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/")
@app.get("/")
async def root_voice(request: Request):
    return await signalwire_webhook.voice(request)

app.include_router(calls.router)
app.include_router(appointments.router)
app.include_router(rag.router)
app.include_router(clinic.router)
app.include_router(tenants.router)
app.include_router(voice_gateway.router)
app.include_router(signalwire_webhook.router)
app.include_router(signalwire_gateway.router)
