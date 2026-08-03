import json
import logging
from datetime import datetime, timedelta
from dateutil import parser

from app.services import clinic_config as config
from app.services import db

logger = logging.getLogger("talkse")


def check_emergency_protocol(arg1: str | None, arg2: str | None = None) -> str | None:
    if arg2 is None:
        tenant_id = db.DEFAULT_TENANT_ID
        text = arg1
    else:
        tenant_id = arg1
        text = arg2
    if not text:
        return None
    lower = text.lower()
    emergency_keywords = [
        "difficulty breathing", "can't breathe", "cannot breathe",
        "severe swelling", "swelling up", "chest pain",
        "anaphylaxis", "allergic reaction",
    ]
    for kw in emergency_keywords:
        if kw in lower:
            return config.get_emergency_protocol(tenant_id).get(
                "life_threatening_instructions",
                "If you are experiencing a medical emergency such as difficulty breathing, "
                "severe swelling, or chest pain, please call 911 immediately.",
            )
    return None


def check_contraindications(service: dict, transcript_or_state) -> str | None:
    if not service:
        return None
    text_to_check = transcript_or_state.lower() if isinstance(transcript_or_state, str) \
        else json.dumps(transcript_or_state).lower()
    contraindications = service.get("contraindications", [])
    risk_terms = {
        "pregnant": ["pregnant", "pregnancy", "expecting"],
        "breastfeeding": ["breastfeeding", "nursing", "lactating"],
        "accutane": ["accutane", "isotretinoin"],
    }
    for condition, keywords in risk_terms.items():
        if any(kw in text_to_check for kw in keywords):
            if service.get("category") in ("injectable", "laser", "body_contouring", "peel") or contraindications:
                return (f"For safety reasons, {service['name']} cannot be performed during {condition}. "
                        f"This request has been flagged for human provider review.")
    return None


def parse_time_string(time_str: str) -> datetime | None:
    if not time_str:
        return None
    now = datetime.now()
    try:
        dt = parser.parse(time_str, fuzzy=True, default=now)
    except Exception:
        return (now + timedelta(days=1)).replace(hour=14, minute=0, second=0, microsecond=0)
    if dt < now:
        dt = dt + timedelta(days=1)
    return dt


def is_slot_available(tenant_id: str, provider_id: str, service_id: str, requested_start: datetime,
                       exclude_appt_id: str = None) -> tuple[bool, str]:
    svc = config.get_service(tenant_id, service_id)
    if not svc:
        return False, f"Service '{service_id}' was not found."
    prov = config.get_provider(tenant_id, provider_id)
    if not prov:
        return False, f"Provider '{provider_id}' was not found."
    if prov["id"] not in svc.get("provider_ids", []):
        return False, f"{prov['name']} does not perform {svc['name']}."
    if not config.provider_works_on(tenant_id, prov["id"], requested_start):
        working_days = ", ".join(prov.get("working_days", []))
        return False, f"{prov['name']} does not work on {requested_start.strftime('%A')}s (works {working_days})."
    if not config.is_clinic_open(tenant_id, requested_start):
        return False, f"The clinic is closed on {requested_start.strftime('%A')} at {requested_start.strftime('%I:%M %p')}."
    duration = svc.get("duration_minutes", 30)
    scheduled_end = requested_start + timedelta(minutes=duration)
    overlapping = db.get_overlapping_appointments(tenant_id, prov["id"], requested_start, scheduled_end, exclude_appt_id)
    if overlapping:
        return False, f"{prov['name']} already has a confirmed booking during that time slot."
    return True, "Slot is available"


def book_appointment(state: dict, idempotency_key: str, tenant_id: str | None = None) -> dict:
    tenant_id = tenant_id or state.get("tenant_id", db.DEFAULT_TENANT_ID)
    svc_input = state.get("service") or "botox"
    service = config.get_service(tenant_id, svc_input) or config.get_service(tenant_id, "svc_botox_touchup")

    contra_reason = check_contraindications(service, state)
    if contra_reason:
        return {"status": "rejected", "reason": contra_reason, "requires_human": True}

    valid_providers = config.providers_for_service(service["id"], tenant_id)
    if not valid_providers:
        return {"status": "rejected", "reason": f"No providers available for {service['name']}.", "requires_human": True}

    time_input = state.get("preferred_time") or "tomorrow at 2pm"
    requested_start = parse_time_string(time_input)

    provider, reason = None, "No providers were available at the requested time."
    for candidate in valid_providers:
        candidate_start = requested_start
        if not config.provider_works_on(tenant_id, candidate["id"], candidate_start):
            for offset in range(1, 8):
                test_dt = requested_start + timedelta(days=offset)
                if config.provider_works_on(tenant_id, candidate["id"], test_dt) and config.is_clinic_open(tenant_id, test_dt):
                    candidate_start = test_dt
                    break
        available, candidate_reason = is_slot_available(tenant_id, candidate["id"], service["id"], candidate_start)
        if available:
            provider, requested_start = candidate, candidate_start
            break
        reason = candidate_reason

    if provider is None:
        return {"status": "rejected", "reason": reason}

    duration = service.get("duration_minutes", 30)
    scheduled_end = requested_start + timedelta(minutes=duration)
    clinic_data = config.get_clinic(tenant_id)
    deposit_threshold = clinic_data.get("deposit_policy", {}).get("applies_to_services_priced_over_usd", 200)
    deposit_required = (service.get("price_usd") or 0) >= deposit_threshold
    caller_name = state.get("caller_name") or "Valued Client"

    try:
        appt = db.insert_appointment(
            tenant_id=tenant_id, idempotency_key=idempotency_key, service_id=service["id"],
            provider_id=provider["id"], caller_name=caller_name,
            scheduled_start=requested_start, scheduled_end=scheduled_end,
            deposit_required=deposit_required,
        )
    except db.SlotTakenError as e:
        return {"status": "rejected", "reason": str(e)}

    return {
        "status": "confirmed", "appointment": appt,
        "service_name": service["name"], "provider_name": provider["name"],
        "scheduled_start": requested_start.strftime("%A, %b %d at %I:%M %p"),
        "deposit_required": deposit_required,
        "message": f"Successfully booked {service['name']} with {provider['name']} for "
                   f"{requested_start.strftime('%A, %b %d at %I:%M %p')}.",
    }


def reschedule_appointment(tenant_id: str, existing_ref: str, new_time_str: str) -> dict:
    appt = db.get_appointment(tenant_id, existing_ref)
    if not appt:
        return {"status": "rejected", "reason": f"No active appointment found for reference '{existing_ref}'."}

    service = config.get_service(tenant_id, appt["service_id"])
    provider = config.get_provider(tenant_id, appt["provider_id"])
    new_start = parse_time_string(new_time_str)

    available, reason = is_slot_available(tenant_id, provider["id"], service["id"], new_start, exclude_appt_id=str(appt["id"]))
    if not available:
        return {"status": "rejected", "reason": f"Cannot reschedule to that time: {reason}"}

    duration = service.get("duration_minutes", 30)
    new_end = new_start + timedelta(minutes=duration)
    clinic_data = config.get_clinic(tenant_id)
    notice_hours = clinic_data.get("cancellation_policy", {}).get("notice_required_hours", 24)
    hours_until_appt = (appt["scheduled_start"] - datetime.now(appt["scheduled_start"].tzinfo)).total_seconds() / 3600.0
    notice_warning = f" (Note: Less than {notice_hours} hours notice given; deposit may be forfeited per clinic policy)." \
        if hours_until_appt < notice_hours else ""

    updated = db.update_appointment_time(tenant_id, appt["id"], new_start, new_end)
    return {
        "status": "rescheduled", "appointment": updated,
        "new_start": new_start.strftime("%A, %b %d at %I:%M %p"),
        "message": f"Rescheduled appointment for {updated['caller_name']} to "
                   f"{new_start.strftime('%A, %b %d at %I:%M %p')}.{notice_warning}",
    }


def cancel_appointment(arg1: str, arg2: str | None = None) -> dict:
    if arg2 is None:
        tenant_id = db.DEFAULT_TENANT_ID
        existing_ref = arg1
    else:
        tenant_id = arg1
        existing_ref = arg2
    appt = db.get_appointment(tenant_id, existing_ref)
    if not appt:
        return {"status": "rejected", "reason": f"No active appointment found for reference '{existing_ref}'."}
    cancelled = db.cancel_appointment(tenant_id, appt["id"])
    return {
        "status": "cancelled", "appointment": cancelled,
        "message": f"Appointment reference '{existing_ref}' for {cancelled['caller_name']} has been cancelled.",
    }
