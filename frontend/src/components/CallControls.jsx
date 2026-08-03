import React, { useState, memo } from 'react';
import { endCall } from '../api/callActions';
import './CallControls.css';

const CallControls = memo(function CallControls({ callId }) {
  const [actionStatus, setActionStatus] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleEndCall = async () => {
    if (!callId) return;
    setLoading(true);
    setActionStatus(null);
    try {
      const res = await endCall(callId);
      setActionStatus(res.message || 'Call ended.');
    } catch (err) {
      console.error(err);
      setActionStatus(`⚠️ Failed to end call: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="call-controls-container">
      {actionStatus && (
        <div className="action-status-banner">
          <span>{actionStatus}</span>
        </div>
      )}

      <button
        className="btn-end-call"
        onClick={handleEndCall}
        disabled={loading || !callId}
      >
        {loading ? 'ENDING...' : 'END CALL'}
      </button>
    </div>
  );
});

export default CallControls;
