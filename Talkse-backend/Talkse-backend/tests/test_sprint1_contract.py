"""
Tests verifying Sprint 1 contract fixes:
- GET /api/v1/calls endpoint return structure
- session store active sessions scanner
- WebSocket message format payload
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.session.store import list_active_sessions


def test_list_active_sessions_scanner():
    with patch("app.session.store._r") as mock_redis:
        mock_redis.scan_iter.return_value = ["call:conv_123", "call:conv_456"]
        mock_redis.get.side_effect = [
            '{"status": "collecting", "caller_name": "Alice"}',
            '{"status": "completed", "caller_name": "Bob"}'
        ]
        
        sessions = list_active_sessions()
        assert len(sessions) == 2
        assert sessions[0] == ("conv_123", {"status": "collecting", "caller_name": "Alice"})
        assert sessions[1] == ("conv_456", {"status": "completed", "caller_name": "Bob"})


def test_list_active_calls_endpoint():
    client = TestClient(app)
    with patch("app.session.store.list_active_sessions") as mock_list:
        mock_list.return_value = [
            ("conv_123", {"status": "collecting", "caller_name": "Alice", "service": "Botox"}),
            ("conv_456", {"status": "confirmed", "caller_name": "Bob", "service": "Consultation"})
        ]
        response = client.get("/api/v1/calls/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["id"] == "conv_123"
        assert data[0]["status"] == "ACTIVE"
        assert data[0]["callerName"] == "Alice"
        assert data[0]["service"] == "Botox"
        assert data[1]["status"] == "CONFIRMED"


@pytest.mark.asyncio
async def test_websocket_emit_contract():
    from app.ws.voice_gateway import _emit
    mock_ws = MagicMock()
    
    async def async_send_json(obj):
        mock_ws.last_sent = obj
        
    mock_ws.send_json = async_send_json
    await _emit(mock_ws, "call.started", {"callId": "123", "callerPhone": "555-0100"})
    
    assert mock_ws.last_sent == {
        "type": "call.started",
        "data": {"callId": "123", "callerPhone": "555-0100"}
    }
