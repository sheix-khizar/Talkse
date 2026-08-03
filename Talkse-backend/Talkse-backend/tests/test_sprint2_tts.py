"""
Unit tests for Sprint 2 TTS live path integration.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock, mock_open
from app.ws.voice_gateway import _synthesize_and_emit


@pytest.mark.anyio
async def test_synthesize_and_emit():
    mock_ws = MagicMock()
    sent_data = []

    async def async_send_json(obj):
        sent_data.append(obj)

    mock_ws.send_json = async_send_json

    m_open = mock_open(read_data=b"fake_wav_bytes")

    with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread, \
         patch("builtins.open", m_open), \
         patch("os.path.exists", return_value=True), \
         patch("os.remove", return_value=None):
        
        mock_to_thread.return_value = (0.5, "deepgram")
        await _synthesize_and_emit(mock_ws, "call_999", "Hello patient", {})

        mock_to_thread.assert_called_once()
        assert len(sent_data) == 1
        assert sent_data[0]["type"] == "audio.chunk"
        assert "audio_base64" in sent_data[0]["data"]
