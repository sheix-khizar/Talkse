import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DEFAULT_DB_URL = "postgresql://postgres:postgres@localhost:5433/postgres"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DB_URL)

def get_connection():
    return psycopg2.connect(DATABASE_URL)

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
            
            cur.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS uq_provider_slot
                    ON appointments (provider_id, scheduled_start)
                    WHERE status = 'confirmed';
            """)
            conn.commit()
            print("[DB] Initialized appointments table and unique index successfully.")
    finally:
        conn.close()

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
        conn.close()

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
        conn.close()

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
        conn.close()

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
        conn.close()

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
        conn.close()

if __name__ == "__main__":
    init_db()
