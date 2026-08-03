"""One-time migration: loads clinic_data.json into the DB-backed
clinics/providers/services tables for DEFAULT_TENANT_ID, so existing
fixture data isn't lost when clinic_config.py switches to DB-backed reads.
Run with: python seed_clinic_config.py
"""
import json
import os
from app.services import db

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "clinic_data.json")

def main():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    tenant_id = db.DEFAULT_TENANT_ID
    clinic = data.get("clinic", {})
    db.upsert_clinic(
        tenant_id=tenant_id,
        name=clinic.get("name", "Unnamed Clinic"),
        timezone=clinic.get("timezone", "America/Chicago"),
        hours=clinic.get("hours", {}),
        plan="paid",  # matches TENANT_PLANS["042"] = "paid" today
        clinic_data=clinic,  # keeps cancellation_policy/deposit_policy/etc. accessible
    )
    for prov in data.get("providers", []):
        db.upsert_provider(tenant_id, prov["id"], prov["name"], prov.get("working_days", []), prov)
    for svc in data.get("services", []):
        db.upsert_service(
            tenant_id, svc["id"], svc["name"], svc.get("category"),
            svc.get("price_usd"), svc.get("duration_minutes", 30),
            svc.get("provider_ids", []), svc,
        )
    print(f"[Seed] Migrated clinic_data.json into tenant '{tenant_id}'.")

if __name__ == "__main__":
    main()
