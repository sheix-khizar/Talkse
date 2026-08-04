from datetime import timedelta

from dateutil import parser as dtparser
from fastapi import APIRouter, HTTPException, Query
from psycopg2.extras import RealDictCursor

from app.services import booking_engine
from app.services import clinic_config as config
from app.services import db

router = APIRouter(prefix="/api/v1/tenants/{tenant_id}", tags=["tenants"])


@router.get("/tts-usage")
def get_tts_usage(tenant_id: str):
    conn = db.get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT provider, COUNT(*) AS calls, SUM(char_count) AS total_chars
                FROM tts_usage WHERE tenant_id = %s GROUP BY provider;
            """, (tenant_id,))
            return [dict(r) for r in cur.fetchall()]
    finally:
        db.release_connection(conn)

@router.get("/stats")
def get_stats(tenant_id: str):
    return db.get_tenant_stats(tenant_id)

@router.get("/config")
def get_tenant_config(tenant_id: str):
    """Returns the full clinic configuration including providers and services."""
    clinic = db.get_clinic_row(tenant_id)
    if not clinic:
        raise HTTPException(404, "Clinic not found")
    
    providers = db.list_providers_for_tenant(tenant_id)
    services = db.list_services_for_tenant(tenant_id)
    
    return {
        "clinic": clinic,
        "providers": providers,
        "services": services
    }

from pydantic import BaseModel

class PlanUpdateRequest(BaseModel):
    plan: str

@router.put("/plan")
def update_tenant_plan(tenant_id: str, request: PlanUpdateRequest):
    """Updates the tenant's active plan (e.g., 'free' vs 'paid')."""
    if request.plan not in ("free", "paid"):
        raise HTTPException(422, "Plan must be 'free' or 'paid'")
        
    clinic = db.get_clinic_row(tenant_id)
    if not clinic:
        raise HTTPException(404, "Clinic not found")
        
    db.upsert_clinic(
        tenant_id=tenant_id,
        name=clinic["name"],
        timezone=clinic["timezone"],
        hours=clinic["hours"],
        plan=request.plan,
        clinic_data=clinic["clinic_data"]
    )
    # Clear the cache in clinic_config so the new plan is fetched next time
    config.refresh_tenant_cache(tenant_id)
    
    return {"status": "success", "plan": request.plan}


@router.get("/patients")
def get_patient(tenant_id: str, phone: str = Query(...)):
    """STOPGAP — there is no `patients` table yet (see fix_plan.md Sprint 6:
    multi-tenancy). Derives a patient view from this phone number's
    appointment history instead of a real patient record. `tenant_id` is
    accepted but not yet enforced, since `appointments` has no tenant
    column yet either."""
    conn = db.get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT * FROM appointments
                WHERE caller_phone = %s
                ORDER BY scheduled_start DESC;
                """,
                (phone,),
            )
            rows = [dict(r) for r in cur.fetchall()]
    finally:
        db.release_connection(conn)

    if not rows:
        raise HTTPException(404, "No patient found for this phone number")

    latest = rows[0]
    return {
        "id": latest["caller_phone"] or "unknown",
        "name": latest["caller_name"],
        "phone": latest["caller_phone"],
        "customerType": "Recurring Customer" if len(rows) > 1 else "New Customer",
        "previousAppointments": [
            f"{r['scheduled_start'].strftime('%b %d')} - {r['service_id']}"
            for r in rows[1:]
        ],
        "notes": "",
    }


@router.post("/appointments")
def create_appointment(tenant_id: str, payload: dict):
    """Dashboard-driven booking — staff already know the resolved
    service_id/provider_id/time, so this bypasses the conversational
    state machine in booking_engine.book_appointment() and calls the
    lower-level slot check + insert directly. `tenant_id` accepted but
    not yet enforced (see note above)."""
    service_id = payload.get("service_id")
    provider_id = payload.get("provider_id")
    requested_time = payload.get("requested_time")
    caller_phone = payload.get("caller_phone")
    idempotency_key = payload.get("idempotency_key") or payload.get("idempotencyKey")

    if not (service_id and provider_id and requested_time):
        raise HTTPException(422, "service_id, provider_id, and requested_time are required")

    try:
        requested_start = dtparser.parse(requested_time)
    except (ValueError, TypeError):
        raise HTTPException(422, f"Could not parse requested_time: {requested_time!r}")

    idempotency_key = idempotency_key or f"web_{provider_id}_{requested_start.isoformat()}"

    available, reason = booking_engine.is_slot_available(tenant_id, provider_id, service_id, requested_start)
    if not available:
        raise HTTPException(409, reason)

    service = config.get_service(tenant_id, service_id)
    duration = service.get("duration_minutes", 30) if service else 30
    scheduled_end = requested_start + timedelta(minutes=duration)

    try:
        appt = db.insert_appointment(
            tenant_id=tenant_id,
            idempotency_key=idempotency_key,
            service_id=service_id,
            provider_id=provider_id,
            caller_name=payload.get("caller_name", "Walk-in / Dashboard"),
            caller_phone=caller_phone,
            scheduled_start=requested_start,
            scheduled_end=scheduled_end,
        )
    except db.SlotTakenError as e:
        raise HTTPException(409, str(e))

    return {
        "appointment_id": str(appt["id"]),
        "status": appt["status"],
        "scheduled_time": appt["scheduled_start"].isoformat(),
        "provider": provider_id,
        "service": service_id,
    }
