import React, { useState, memo } from 'react';
import { handOffToHuman, transferCall, endCall } from '../api/callActions';
import './CallControls.css';

const CallControls = memo(function CallControls({ callId = 'call_88f2e1a9d023' }) {
  const [handoffNotes, setHandoffNotes] = useState('');
  const [actionStatus, setActionStatus] = useState(null);
  const [loadingAction, setLoadingAction] = useState(null);

  const handleHandoff = async () => {
    setLoadingAction('handoff');
    setActionStatus(null);
    try {
      const res = await handOffToHuman(callId, handoffNotes);
      setActionStatus(res.message || 'Handoff initiated.');
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingAction(null);
    }
  };

  const handleTransfer = async () => {
    setLoadingAction('transfer');
    setActionStatus(null);
    try {
      const res = await transferCall(callId);
      setActionStatus(res.message || 'Call transfer initiated.');
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingAction(null);
    }
  };

  const handleEndCall = async () => {
    setLoadingAction('end');
    setActionStatus(null);
    try {
      const res = await endCall(callId);
      setActionStatus(res.message || 'Call ended.');
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingAction(null);
    }
  };

  return (
    <div className="call-controls-container">
      {actionStatus && (
        <div className="action-status-banner">
          <span>{actionStatus}</span>
        </div>
      )}

      {/* Hand Off Button */}
      <button
        className="btn-handoff"
        onClick={handleHandoff}
        disabled={loadingAction === 'handoff'}
      >
        {loadingAction === 'handoff' ? 'HANDING OFF...' : 'HAND OFF TO HUMAN'}
      </button>

      {/* Notes Textarea */}
      <textarea
        className="controls-notes-textarea"
        placeholder="Notes..."
        value={handoffNotes}
        onChange={(e) => setHandoffNotes(e.target.value)}
      />

      {/* Action Buttons Stack */}
      <div className="controls-btn-stack">
        <button
          className="btn-transfer"
          onClick={handleTransfer}
          disabled={loadingAction === 'transfer'}
        >
          {loadingAction === 'transfer' ? 'TRANSFERRING...' : 'TRANSFER CALL'}
        </button>

        <button
          className="btn-end-call"
          onClick={handleEndCall}
          disabled={loadingAction === 'end'}
        >
          {loadingAction === 'end' ? 'ENDING...' : 'END CALL'}
        </button>
      </div>
    </div>
  );
});

export default CallControls;
