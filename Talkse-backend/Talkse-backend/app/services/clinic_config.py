"""Per-tenant clinic configuration, backed by Postgres (clinics/providers/
services tables) instead of a single global clinic_data.json. Cached
in-process per tenant_id to avoid a DB round trip on every lookup within
a call; call refresh_tenant_cache(tenant_id) after editing a tenant's
config via the dashboard."""
import logging
from datetime import datetime

from app.services import db

logger = logging.getLogger("talkse")

_cache: dict[str, dict] = {}  # tenant_id -> {"clinic": ..., "providers": [...], "services": [...]}


def _load_tenant(tenant_id: str) -> dict:
    if tenant_id in _cache:
        return _cache[tenant_id]
    clinic = db.get_clinic_row(tenant_id) or {}
    providers = db.list_providers_for_tenant(tenant_id)
    services = db.list_services_for_tenant(tenant_id)
    entry = {"clinic": clinic, "providers": providers, "services": services}
    _cache[tenant_id] = entry
    return entry


def refresh_tenant_cache(tenant_id: str):
    _cache.pop(tenant_id, None)


def get_plan_for_tenant(tenant_id: str | None) -> str:
    if not tenant_id:
        return "free"
    tenant = _load_tenant(tenant_id)
    return tenant["clinic"].get("plan", "free")


def get_clinic(tenant_id: str) -> dict:
    return _load_tenant(tenant_id)["clinic"].get("clinic_data", {})


def get_emergency_protocol(tenant_id: str) -> dict:
    return get_clinic(tenant_id).get("emergency_protocol", {})


def get_service(tenant_id: str, service_id_or_name: str) -> dict | None:
    if not service_id_or_name:
        return None
    services = _load_tenant(tenant_id)["services"]
    query = str(service_id_or_name).lower().strip()

    for svc in services:
        if svc["id"].lower() == query:
            return svc
    for svc in services:
        if query in svc["name"].lower() or svc["name"].lower() in query:
            return svc
    for svc in services:
        cat = (svc.get("category") or "").lower()
        if cat and (query == cat or query in cat):
            return svc

    keywords = {
        "botox": "svc_botox_touchup", "consultation": "svc_consult", "consult": "svc_consult",
        "filler": "svc_filler_lips", "hydrafacial": "svc_hydrafacial", "laser": "svc_laser_small",
        "peel": "svc_peel", "acne": "svc_peel", "skin": "svc_hydrafacial", "facial": "svc_hydrafacial",
    }
    for kw, default_id in keywords.items():
        if kw in query:
            return get_service(tenant_id, default_id)
    return None


def get_provider(tenant_id: str, provider_id_or_name: str) -> dict | None:
    if not provider_id_or_name:
        return None
    providers = _load_tenant(tenant_id)["providers"]
    query = str(provider_id_or_name).lower().strip()
    for prov in providers:
        if prov["id"].lower() == query or query in prov["name"].lower() or prov["name"].lower() in query:
            return prov
    return None


def providers_for_service(tenant_id: str, service_id: str) -> list[dict]:
    svc = get_service(tenant_id, service_id)
    if not svc:
        return []
    allowed_ids = set(svc.get("provider_ids", []))
    return [p for p in _load_tenant(tenant_id)["providers"] if p["id"] in allowed_ids]


def is_clinic_open(tenant_id: str, dt: datetime) -> bool:
    clinic_row = _load_tenant(tenant_id)["clinic"]
    hours = clinic_row.get("hours", {}) if clinic_row else {}
    day_name = dt.strftime("%A").lower()
    hours_info = hours.get(day_name, {})
    if hours_info.get("closed", False):
        return False
    open_str, close_str = hours_info.get("open"), hours_info.get("close")
    if not open_str or not close_str:
        return False
    open_time = datetime.strptime(open_str, "%H:%M").time()
    close_time = datetime.strptime(close_str, "%H:%M").time()
    return open_time <= dt.time() <= close_time


def provider_works_on(tenant_id: str, provider_id: str, dt_or_day) -> bool:
    prov = get_provider(tenant_id, provider_id)
    if not prov:
        return False
    day_str = dt_or_day.strftime("%A") if isinstance(dt_or_day, datetime) else str(dt_or_day).capitalize()
    working_days = [d.capitalize() for d in (prov.get("working_days") or [])]
    return day_str in working_days
