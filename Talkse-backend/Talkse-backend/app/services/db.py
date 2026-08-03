import os
import json
import logging
import psycopg2
from psycopg2 import pool, errors as pg_errors
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from datetime import datetime

logger = logging.getLogger("talkse")

class SlotTakenError(Exception):
    """Raised when a concurrent booking already claimed this provider/slot."""
    pass

load_dotenv()

DEFAULT_DB_URL = "postgresql://postgres:postgres@localhost:5433/postgres"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DB_URL)

DEFAULT_TENANT_ID = "042"

_pool = None
def get_pool():
    global _pool
    if _pool is None:
        _pool = pool.SimpleConnectionPool(1, 10, DATABASE_URL)
    return _pool

def get_connection():
    return get_pool().getconn()

def release_connection(conn):
    if conn:
        get_pool().putconn(conn)

def init_db():
    """Initializes the appointments table and unique slot index in Postgres."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS appointments (
                    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    idempotency_key    TEXT UNIQUE NOT NULL,
                    service_id         TEXT NOT NULL,
                    provider_id        TEXT NOT NULL,
                    caller_name        TEXT NOT NULL,
                    caller_phone       TEXT,
                    scheduled_start    TIMESTAMPTZ NOT NULL,
                    scheduled_end      TIMESTAMPTZ NOT NULL,
                    status             TEXT NOT NULL DEFAULT 'confirmed',
                    deposit_required   BOOLEAN NOT NULL DEFAULT false,
                    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
                );
            """)
            cur.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS uq_provider_slot
                    ON appointments (provider_id, scheduled_start)
                    WHERE status = 'confirmed';
            """)
            conn.commit()
            logger.info("[DB] Initialized appointments table and unique index successfully.")
    finally:
        release_connection(conn)

def init_tenant_tables():
    """Real per-tenant clinic config, replacing the single global
    clinic_data.json. Run once at startup, before init_db()."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS clinics (
                    id           TEXT PRIMARY KEY,
                    name         TEXT NOT NULL,
                    timezone     TEXT NOT NULL DEFAULT 'America/Chicago',
                    hours        JSONB NOT NULL,
                    plan         TEXT NOT NULL DEFAULT 'free',
                    clinic_data  JSONB NOT NULL DEFAULT '{}'::jsonb
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS providers (
                    id            TEXT NOT NULL,
                    tenant_id     TEXT NOT NULL REFERENCES clinics(id),
                    name          TEXT NOT NULL,
                    working_days  JSONB NOT NULL,
                    provider_data JSONB NOT NULL DEFAULT '{}'::jsonb,
                    PRIMARY KEY (tenant_id, id)
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS services (
                    id            TEXT NOT NULL,
                    tenant_id     TEXT NOT NULL REFERENCES clinics(id),
                    name          TEXT NOT NULL,
                    category      TEXT,
                    price_usd     NUMERIC,
                    duration_minutes INT NOT NULL DEFAULT 30,
                    provider_ids  JSONB NOT NULL DEFAULT '[]'::jsonb,
                    service_data  JSONB NOT NULL DEFAULT '{}'::jsonb,
                    PRIMARY KEY (tenant_id, id)
                );
            """)
            conn.commit()
            logger.info("[DB] Tenant tables (clinics/providers/services) ready.")
    finally:
        release_connection(conn)

def migrate_tenant_columns():
    """Adds tenant_id to the tables that didn't have it, backfills to
    DEFAULT_TENANT_ID, then enforces NOT NULL + indexes. Idempotent —
    safe to run on every startup."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            for table in ("appointments", "documents", "document_chunks"):
                cur.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS tenant_id TEXT;")
                cur.execute(f"UPDATE {table} SET tenant_id = %s WHERE tenant_id IS NULL;",
                            (DEFAULT_TENANT_ID,))
                cur.execute(f"ALTER TABLE {table} ALTER COLUMN tenant_id SET NOT NULL;")
                cur.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_tenant ON {table}(tenant_id);")
            conn.commit()
            logger.info("[DB] tenant_id backfilled and enforced on appointments/documents/document_chunks.")
    finally:
        release_connection(conn)

def enable_tenant_rls():
    """Defense-in-depth: even if application code forgets a WHERE tenant_id
    clause somewhere, Postgres itself refuses cross-tenant rows once
    app.current_tenant is set on the connection."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            for table in ("appointments", "documents", "document_chunks"):
                cur.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
                cur.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table};")
                cur.execute(f"""
                    CREATE POLICY tenant_isolation ON {table}
                        USING (tenant_id = current_setting('app.current_tenant', true));
                """)
            conn.commit()
            logger.info("[DB] Row-level security enabled on tenant tables.")
    finally:
        release_connection(conn)

def set_session_tenant(conn, tenant_id: str):
    """Call right after get_connection() for any request that touches
    tenant-scoped tables, so RLS actually applies to this connection."""
    with conn.cursor() as cur:
        cur.execute("SET app.current_tenant = %s;", (tenant_id,))

def get_appointment(tenant_id: str, id_or_key: str) -> dict | None:
    conn = get_connection()
    try:
        set_session_tenant(conn, tenant_id)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM appointments 
                WHERE tenant_id = %s AND (id::text = %s OR idempotency_key = %s);
            """, (tenant_id, str(id_or_key), str(id_or_key)))
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        release_connection(conn)

def get_overlapping_appointments(tenant_id: str, provider_id: str, start_dt, end_dt, exclude_id: str = None) -> list[dict]:
    conn = get_connection()
    try:
        set_session_tenant(conn, tenant_id)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if exclude_id:
                cur.execute("""
                    SELECT * FROM appointments
                    WHERE tenant_id = %s AND provider_id = %s AND status = 'confirmed'
                      AND id::text != %s AND (scheduled_start < %s AND scheduled_end > %s);
                """, (tenant_id, provider_id, str(exclude_id), end_dt, start_dt))
            else:
                cur.execute("""
                    SELECT * FROM appointments
                    WHERE tenant_id = %s AND provider_id = %s AND status = 'confirmed'
                      AND (scheduled_start < %s AND scheduled_end > %s);
                """, (tenant_id, provider_id, end_dt, start_dt))
            return [dict(r) for r in cur.fetchall()]
    finally:
        release_connection(conn)

def insert_appointment(tenant_id: str, idempotency_key: str, service_id: str, provider_id: str, caller_name: str, scheduled_start, scheduled_end, deposit_required: bool = False, caller_phone: str = None) -> dict:
    existing = get_appointment(tenant_id, idempotency_key)
    if existing:
        logger.info(f"[DB] Idempotency key '{idempotency_key}' found. Returning existing appointment.")
        return existing

    conn = get_connection()
    try:
        set_session_tenant(conn, tenant_id)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            try:
                cur.execute("""
                    INSERT INTO appointments (tenant_id, idempotency_key, service_id, provider_id, caller_name, caller_phone, scheduled_start, scheduled_end, deposit_required)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *;
                """, (tenant_id, idempotency_key, service_id, provider_id, caller_name, caller_phone, scheduled_start, scheduled_end, deposit_required))
                row = cur.fetchone()
                conn.commit()
                return dict(row)
            except pg_errors.UniqueViolation:
                conn.rollback()
                logger.warning(f"[DB] Slot for provider '{provider_id}' at {scheduled_start} was claimed concurrently.")
                raise SlotTakenError(
                    f"The slot for provider '{provider_id}' at {scheduled_start} was just booked by another caller."
                )
    finally:
        release_connection(conn)

def cancel_appointment(tenant_id: str, id_or_key: str) -> dict | None:
    conn = get_connection()
    try:
        set_session_tenant(conn, tenant_id)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                UPDATE appointments SET status = 'cancelled', updated_at = now()
                WHERE tenant_id = %s AND (id::text = %s OR idempotency_key = %s)
                RETURNING *;
            """, (tenant_id, str(id_or_key), str(id_or_key)))
            row = cur.fetchone()
            conn.commit()
            return dict(row) if row else None
    finally:
        release_connection(conn)

def update_appointment_time(tenant_id: str, id_or_key: str, new_start, new_end) -> dict | None:
    conn = get_connection()
    try:
        set_session_tenant(conn, tenant_id)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                UPDATE appointments SET scheduled_start = %s, scheduled_end = %s, updated_at = now()
                WHERE tenant_id = %s AND (id::text = %s OR idempotency_key = %s)
                RETURNING *;
            """, (new_start, new_end, tenant_id, str(id_or_key), str(id_or_key)))
            row = cur.fetchone()
            conn.commit()
            return dict(row) if row else None
    finally:
        release_connection(conn)

def list_appointments_for_tenant(tenant_id: str) -> list[dict]:
    conn = get_connection()
    try:
        set_session_tenant(conn, tenant_id)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM appointments WHERE tenant_id = %s ORDER BY created_at DESC;", (tenant_id,))
            return [dict(r) for r in cur.fetchall()]
    finally:
        release_connection(conn)

def get_clinic_row(tenant_id: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM clinics WHERE id = %s;", (tenant_id,))
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        release_connection(conn)

def list_providers_for_tenant(tenant_id: str) -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM providers WHERE tenant_id = %s;", (tenant_id,))
            return [dict(r) for r in cur.fetchall()]
    finally:
        release_connection(conn)

def list_services_for_tenant(tenant_id: str) -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM services WHERE tenant_id = %s;", (tenant_id,))
            return [dict(r) for r in cur.fetchall()]
    finally:
        release_connection(conn)

def upsert_clinic(tenant_id: str, name: str, timezone: str, hours: dict, plan: str, clinic_data: dict):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO clinics (id, name, timezone, hours, plan, clinic_data)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name, timezone = EXCLUDED.timezone,
                    hours = EXCLUDED.hours, plan = EXCLUDED.plan, clinic_data = EXCLUDED.clinic_data;
            """, (tenant_id, name, timezone, json.dumps(hours), plan, json.dumps(clinic_data)))
            conn.commit()
    finally:
        release_connection(conn)

def upsert_provider(tenant_id: str, provider_id: str, name: str, working_days: list, provider_data: dict):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO providers (id, tenant_id, name, working_days, provider_data)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (tenant_id, id) DO UPDATE SET
                    name = EXCLUDED.name, working_days = EXCLUDED.working_days,
                    provider_data = EXCLUDED.provider_data;
            """, (provider_id, tenant_id, name, json.dumps(working_days), json.dumps(provider_data)))
            conn.commit()
    finally:
        release_connection(conn)

def upsert_service(tenant_id: str, service_id: str, name: str, category: str, price_usd, duration_minutes: int, provider_ids: list, service_data: dict):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO services (id, tenant_id, name, category, price_usd, duration_minutes, provider_ids, service_data)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (tenant_id, id) DO UPDATE SET
                    name = EXCLUDED.name, category = EXCLUDED.category, price_usd = EXCLUDED.price_usd,
                    duration_minutes = EXCLUDED.duration_minutes, provider_ids = EXCLUDED.provider_ids,
                    service_data = EXCLUDED.service_data;
            """, (service_id, tenant_id, name, category, price_usd, duration_minutes, json.dumps(provider_ids), json.dumps(service_data)))
            conn.commit()
    finally:
        release_connection(conn)

def init_rag_tables():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            try:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            except Exception as e:
                logger.warning(f"[DB] Could not create pgvector extension: {e}")
                conn.rollback()

            cur.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    source_url TEXT NOT NULL,
                    category TEXT NOT NULL,
                    title TEXT,
                    content_hash TEXT,
                    tenant_id TEXT NOT NULL,
                    updated_at TIMESTAMPTZ DEFAULT now()
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS document_chunks (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                    chunk_text TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    embedding VECTOR(768)
                );
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_chunks_embedding
                ON document_chunks USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 50);
            """)
            conn.commit()
            logger.info("[DB] RAG tables ready.")
    finally:
        release_connection(conn)

def init_tts_usage_table():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tts_usage (
                    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    call_id      TEXT NOT NULL,
                    tenant_id    TEXT,
                    provider     TEXT NOT NULL,
                    char_count   INTEGER NOT NULL,
                    elapsed_secs REAL,
                    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
                );
            """)
            conn.commit()
            logger.info("[DB] tts_usage table ready.")
    finally:
        release_connection(conn)

def init_call_logs_table():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS call_logs (
                    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    call_id        TEXT NOT NULL,
                    tenant_id      TEXT NOT NULL,
                    caller_name    TEXT,
                    status         TEXT NOT NULL,
                    started_at     TIMESTAMPTZ,
                    ended_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
                    transcript     JSONB,
                    booking_result JSONB
                );
            """)
            conn.commit()
            logger.info("[DB] call_logs table ready.")
    finally:
        release_connection(conn)

def log_tts_usage(call_id: str, tenant_id: str | None, provider: str, char_count: int, elapsed_secs: float):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO tts_usage (call_id, tenant_id, provider, char_count, elapsed_secs)
                VALUES (%s, %s, %s, %s, %s);
            """, (call_id, tenant_id, provider, char_count, elapsed_secs))
            conn.commit()
    finally:
        release_connection(conn)

def insert_call_log(tenant_id: str, call_id: str, caller_name: str, status: str, started_at: datetime | None, transcript: list, booking_result: dict | None):
    conn = get_connection()
    try:
        set_session_tenant(conn, tenant_id)
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO call_logs (call_id, tenant_id, caller_name, status, started_at, transcript, booking_result)
                VALUES (%s, %s, %s, %s, %s, %s, %s);
            """, (call_id, tenant_id, caller_name, status, started_at, json.dumps(transcript) if transcript else None, json.dumps(booking_result) if booking_result else None))
            conn.commit()
    finally:
        release_connection(conn)

def list_calls_for_tenant(tenant_id: str, limit: int = 50, offset: int = 0) -> list[dict]:
    conn = get_connection()
    try:
        set_session_tenant(conn, tenant_id)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM call_logs 
                WHERE tenant_id = %s 
                ORDER BY ended_at DESC 
                LIMIT %s OFFSET %s;
            """, (tenant_id, limit, offset))
            return [dict(r) for r in cur.fetchall()]
    finally:
        release_connection(conn)

def get_call_log(tenant_id: str, call_id: str) -> dict | None:
    conn = get_connection()
    try:
        set_session_tenant(conn, tenant_id)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM call_logs WHERE tenant_id = %s AND call_id = %s;
            """, (tenant_id, call_id))
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        release_connection(conn)

def get_tenant_stats(tenant_id: str) -> dict:
    """Aggregates calls, bookings, and escalations for today."""
    conn = get_connection()
    try:
        set_session_tenant(conn, tenant_id)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    COUNT(*) as calls_today,
                    COUNT(*) FILTER (WHERE status = 'done') as bookings_today,
                    COUNT(*) FILTER (WHERE status IN ('flagged_human_review', 'emergency_transferred')) as escalations_today
                FROM call_logs
                WHERE tenant_id = %s 
                  AND ended_at >= current_date;
            """, (tenant_id,))
            row = cur.fetchone()
            return dict(row) if row else {"calls_today": 0, "bookings_today": 0, "escalations_today": 0}
    finally:
        release_connection(conn)

def get_document_hash(tenant_id: str, source_url: str) -> str | None:
    conn = get_connection()
    try:
        set_session_tenant(conn, tenant_id)
        with conn.cursor() as cur:
            cur.execute("SELECT content_hash FROM documents WHERE tenant_id = %s AND source_url = %s;", (tenant_id, source_url))
            row = cur.fetchone()
            return row[0] if row else None
    finally:
        release_connection(conn)

def upsert_document(tenant_id: str, source_url: str, category: str, title: str, content_hash: str) -> str:
    conn = get_connection()
    try:
        set_session_tenant(conn, tenant_id)
        with conn.cursor() as cur:
            cur.execute("SELECT id, content_hash FROM documents WHERE tenant_id = %s AND source_url = %s;", (tenant_id, source_url))
            row = cur.fetchone()
            if row and row[1] == content_hash:
                return str(row[0])  # unchanged, skip re-embedding
            if row:
                cur.execute("DELETE FROM document_chunks WHERE tenant_id = %s AND document_id = %s;", (tenant_id, row[0]))
                cur.execute("UPDATE documents SET content_hash=%s, updated_at=now() WHERE tenant_id=%s AND id=%s;",
                            (content_hash, tenant_id, row[0]))
                conn.commit()
                return str(row[0])
            cur.execute("""
                INSERT INTO documents (tenant_id, source_url, category, title, content_hash)
                VALUES (%s, %s, %s, %s, %s) RETURNING id;
            """, (tenant_id, source_url, category, title, content_hash))
            new_id = cur.fetchone()[0]
            conn.commit()
            return str(new_id)
    finally:
        release_connection(conn)

def insert_chunk(tenant_id: str, document_id: str, chunk_text: str, embedding: list[float]):
    conn = get_connection()
    try:
        set_session_tenant(conn, tenant_id)
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO document_chunks (tenant_id, document_id, chunk_text, embedding)
                VALUES (%s, %s, %s, %s);
            """, (tenant_id, document_id, chunk_text, embedding))
            conn.commit()
    finally:
        release_connection(conn)

if __name__ == "__main__":
    init_db()
