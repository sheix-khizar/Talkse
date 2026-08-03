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
    raw_providers = db.list_providers_for_tenant(tenant_id)
    raw_services = db.list_services_for_tenant(tenant_id)
    providers = [{**p.get("provider_data", {}), **p} for p in raw_providers]
    services = [{**s.get("service_data", {}), **s} for s in raw_services]
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


def _find_service_in_list(services: list[dict], query_or_id: str) -> dict | None:
    if not query_or_id:
        return None
    query = str(query_or_id).lower().strip()

    for svc in services:
        if svc.get("id", "").lower() == query:
            return svc
    for svc in services:
        svc_name = svc.get("name", "").lower()
        if svc_name and (query in svc_name or svc_name in query):
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
            for svc in services:
                if svc.get("id", "").lower() == default_id:
                    return svc
    return None


def get_service(arg1: str, arg2: str | None = None) -> dict | None:
    """Finds service by ID/name/category. Accepts args as (service_id_or_name, tenant_id)
    or (tenant_id, service_id_or_name) in either order."""
    if not arg1:
        return None

    if arg2 is not None:
        t1_services = _load_tenant(arg1)["services"]
        if t1_services:
            svc = _find_service_in_list(t1_services, arg2)
            if svc:
                return svc
        t2_services = _load_tenant(arg2)["services"]
        if t2_services:
            svc = _find_service_in_list(t2_services, arg1)
            if svc:
                return svc
        svc = _find_service_in_list(t1_services, arg2) or _find_service_in_list(t2_services, arg1)
        if svc:
            return svc

    tenant_id = db.DEFAULT_TENANT_ID
    query_str = arg1
    if arg2 and not _find_service_in_list(_load_tenant(tenant_id)["services"], arg1):
        query_str = arg2
    return _find_service_in_list(_load_tenant(tenant_id)["services"], query_str)


def _find_provider_in_list(providers: list[dict], query_or_id: str) -> dict | None:
    if not query_or_id:
        return None
    query = str(query_or_id).lower().strip()
    for prov in providers:
        prov_id = prov.get("id", "").lower()
        prov_name = prov.get("name", "").lower()
        if prov_id == query or (prov_name and (query in prov_name or prov_name in query)):
            return prov
    return None


def get_provider(arg1: str, arg2: str | None = None) -> dict | None:
    """Finds provider by ID/name. Accepts args as (provider_id_or_name, tenant_id)
    or (tenant_id, provider_id_or_name) in either order."""
    if not arg1:
        return None
    if arg2 is not None:
        p1 = _find_provider_in_list(_load_tenant(arg1)["providers"], arg2)
        if p1:
            return p1
        p2 = _find_provider_in_list(_load_tenant(arg2)["providers"], arg1)
        if p2:
            return p2
    tenant_id = db.DEFAULT_TENANT_ID
    return _find_provider_in_list(_load_tenant(tenant_id)["providers"], arg1)


def providers_for_service(service_id: str, tenant_id: str = db.DEFAULT_TENANT_ID) -> list[dict]:
    svc = get_service(service_id, tenant_id)
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
