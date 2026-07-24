import os
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DEFAULT_DB_URL = "postgresql://postgres:postgres@localhost:5433/postgres"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DB_URL)

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
            # Enable pgcrypto extension if needed for gen_random_uuid
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
            
            # Known Limitation / Future Schema Enhancement:
            # uq_provider_slot prevents two confirmed bookings at the exact same scheduled_start for a provider.
            # Intersecting/overlapping time windows (e.g. 2:00-2:30 vs 2:15-2:45) are caught by get_overlapping_appointments()
            # in application logic. A strict DB-level exclusion constraint for overlapping time ranges would require
            # CREATE EXTENSION btree_gist; EXCLUDE USING gist (provider_id WITH =, tsrange(scheduled_start, scheduled_end) WITH &&).
            cur.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS uq_provider_slot
                    ON appointments (provider_id, scheduled_start)
                    WHERE status = 'confirmed';
            """)
            conn.commit()
            print("[DB] Initialized appointments table and unique index successfully.")
    finally:
        release_connection(conn)

def get_appointment(id_or_key: str) -> dict | None:
    """Fetches an appointment by ID or idempotency_key."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM appointments 
                WHERE id::text = %s OR idempotency_key = %s;
            """, (str(id_or_key), str(id_or_key)))
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        release_connection(conn)

def get_overlapping_appointments(provider_id: str, start_dt, end_dt, exclude_id: str = None) -> list[dict]:
    """Finds confirmed appointments overlapping [start_dt, end_dt) for a provider."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if exclude_id:
                cur.execute("""
                    SELECT * FROM appointments
                    WHERE provider_id = %s
                      AND status = 'confirmed'
                      AND id::text != %s
                      AND (scheduled_start < %s AND scheduled_end > %s);
                """, (provider_id, str(exclude_id), end_dt, start_dt))
            else:
                cur.execute("""
                    SELECT * FROM appointments
                    WHERE provider_id = %s
                      AND status = 'confirmed'
                      AND (scheduled_start < %s AND scheduled_end > %s);
                """, (provider_id, end_dt, start_dt))
            return [dict(r) for r in cur.fetchall()]
    finally:
        release_connection(conn)

def insert_appointment(idempotency_key: str, service_id: str, provider_id: str, caller_name: str, scheduled_start, scheduled_end, deposit_required: bool = False, caller_phone: str = None) -> dict:
    """Inserts a new appointment row or returns existing row if idempotency_key exists."""
    existing = get_appointment(idempotency_key)
    if existing:
        print(f"[DB] Idempotency key '{idempotency_key}' found. Returning existing appointment.")
        return existing
        
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO appointments (idempotency_key, service_id, provider_id, caller_name, caller_phone, scheduled_start, scheduled_end, deposit_required)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *;
            """, (idempotency_key, service_id, provider_id, caller_name, caller_phone, scheduled_start, scheduled_end, deposit_required))
            row = cur.fetchone()
            conn.commit()
            return dict(row)
    finally:
        release_connection(conn)

def cancel_appointment(id_or_key: str) -> dict | None:
    """Marks an appointment status as cancelled."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                UPDATE appointments
                SET status = 'cancelled', updated_at = now()
                WHERE id::text = %s OR idempotency_key = %s
                RETURNING *;
            """, (str(id_or_key), str(id_or_key)))
            row = cur.fetchone()
            conn.commit()
            return dict(row) if row else None
    finally:
        release_connection(conn)

def update_appointment_time(id_or_key: str, new_start, new_end) -> dict | None:
    """Updates scheduled start and end time of an appointment."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                UPDATE appointments
                SET scheduled_start = %s, scheduled_end = %s, updated_at = now()
                WHERE id::text = %s OR idempotency_key = %s
                RETURNING *;
            """, (new_start, new_end, str(id_or_key), str(id_or_key)))
            row = cur.fetchone()
            conn.commit()
            return dict(row) if row else None
    finally:
        release_connection(conn)

if __name__ == "__main__":
    init_db()

def init_rag_tables():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    source_url TEXT NOT NULL,
                    category TEXT NOT NULL,
                    title TEXT,
                    content_hash TEXT,
                    updated_at TIMESTAMPTZ DEFAULT now()
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS document_chunks (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                    chunk_text TEXT NOT NULL,
                    embedding VECTOR(768)
                );
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_chunks_embedding
                ON document_chunks USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 50);
            """)
            conn.commit()
            print("[DB] RAG tables ready.")
    finally:
        release_connection(conn)

def upsert_document(source_url: str, category: str, title: str, content_hash: str) -> str:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, content_hash FROM documents WHERE source_url = %s;", (source_url,))
            row = cur.fetchone()
            if row and row[1] == content_hash:
                return str(row[0])  # unchanged, skip re-embedding
            if row:
                cur.execute("DELETE FROM document_chunks WHERE document_id = %s;", (row[0],))
                cur.execute("UPDATE documents SET content_hash=%s, updated_at=now() WHERE id=%s;",
                            (content_hash, row[0]))
                conn.commit()
                return str(row[0])
            cur.execute("""
                INSERT INTO documents (source_url, category, title, content_hash)
                VALUES (%s, %s, %s, %s) RETURNING id;
            """, (source_url, category, title, content_hash))
            new_id = cur.fetchone()[0]
            conn.commit()
            return str(new_id)
    finally:
        release_connection(conn)

def insert_chunk(document_id: str, chunk_text: str, embedding: list[float]):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO document_chunks (document_id, chunk_text, embedding)
                VALUES (%s, %s, %s);
            """, (document_id, chunk_text, embedding))
            conn.commit()
    finally:
        release_connection(conn)
