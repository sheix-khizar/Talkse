from fastapi.testclient import TestClient
from app.main import app
from app.session.store import new_session, get_session

client = TestClient(app)


def test_switch_live_pipeline_updates_session():
    call_id = "test_pipeline_switch_call"
    new_session(call_id, {
        "tenant_id": "042", "plan": "free", "voice_pipeline": "deepgram",
        "status": "collecting", "turn_count": 0,
    })

    res = client.put(f"/api/v1/calls/{call_id}/pipeline", json={"provider": "elevenlabs"})
    assert res.status_code == 200
    assert res.json()["voice_pipeline"] == "elevenlabs"

    state = get_session(call_id)
    assert state["voice_pipeline"] == "elevenlabs"


def test_switch_pipeline_rejects_invalid_provider():
    call_id = "test_pipeline_invalid"
    new_session(call_id, {"tenant_id": "042", "status": "collecting"})
    res = client.put(f"/api/v1/calls/{call_id}/pipeline", json={"provider": "not_a_real_provider"})
    assert res.status_code == 422


def test_switch_pipeline_404_on_missing_call():
    res = client.put("/api/v1/calls/does_not_exist/pipeline", json={"provider": "deepgram"})
    assert res.status_code == 404
