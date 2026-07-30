from app.api.v1.calls import resolve_call_plan

def test_explicit_override_wins_regardless_of_tenant():
    assert resolve_call_plan("042", "free") == "free"
    assert resolve_call_plan("043", "paid") == "paid"

def test_invalid_override_falls_back_to_tenant_plan():
    assert resolve_call_plan("042", "invalid_plan") == "paid"

def test_no_override_uses_tenant_config():
    assert resolve_call_plan("042", None) == "paid"
    assert resolve_call_plan("043", None) == "free"

def test_legacy_clinic_prefixed_tenant_id_still_resolves():
    assert resolve_call_plan("clinic_042", None) == "paid"

def test_unknown_tenant_defaults_to_free():
    assert resolve_call_plan("unknown", None) == "free"
