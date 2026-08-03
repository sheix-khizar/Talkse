import React, { useEffect, useState } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { apiFetch } from '../api/client';
import LiveTranscript from '../components/LiveTranscript';
import './CallsPage.css';

export default function CallsPage() {
  const { getToken } = useAuth();
  const [calls, setCalls] = useState([]);
  const [selectedCall, setSelectedCall] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function loadCalls() {
      try {
        const res = await apiFetch('/api/v1/calls/history', {}, getToken);
        if (!res.ok) throw new Error('Failed to fetch calls');
        const data = await res.json();
        setCalls(data);
        if (data.length > 0) setSelectedCall(data[0]);
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    }
    loadCalls();
  }, [getToken]);

  const fetchCallDetails = async (callId) => {
    try {
      const res = await apiFetch(`/api/v1/calls/${callId}`, {}, getToken);
      if (!res.ok) throw new Error('Failed to load call details');
      const data = await res.json();
      setSelectedCall(data);
    } catch (e) {
      console.error(e);
    }
  };

  if (loading) {
    return (
      <div className="page-container flex-center">
        <div className="loading-spinner"></div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h2 className="page-title">Call History</h2>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div className="calls-layout">
        <div className="calls-list">
          {calls.length === 0 ? (
            <div className="empty-state">No call history found.</div>
          ) : (
            calls.map(call => (
              <div 
                key={call.id} 
                className={`call-card ${selectedCall?.id === call.id ? 'active' : ''}`}
                onClick={() => fetchCallDetails(call.call_id)}
              >
                <div className="call-card-header">
                  <span className="caller-name">{call.caller_name || 'Unknown Caller'}</span>
                  <span className="call-time">
                    {new Date(call.ended_at).toLocaleString([], {month:'short', day:'numeric', hour:'numeric', minute:'2-digit'})}
                  </span>
                </div>
                <div className="call-card-body">
                  <span className={`status-badge ${call.status}`}>{call.status}</span>
                </div>
              </div>
            ))
          )}
        </div>

        <div className="call-detail-pane">
          {selectedCall ? (
            <div className="call-detail-content">
              <h3>Call Details</h3>
              <div className="detail-meta">
                <p><strong>Caller:</strong> {selectedCall.caller_name || 'Unknown'}</p>
                <p><strong>Status:</strong> {selectedCall.status}</p>
                <p><strong>Ended:</strong> {new Date(selectedCall.ended_at).toLocaleString()}</p>
                {selectedCall.booking_result && (
                  <p><strong>Booking Outcome:</strong> {selectedCall.booking_result.status}</p>
                )}
              </div>
              <div className="transcript-section">
                <h4>Transcript</h4>
                {selectedCall.transcript && selectedCall.transcript.length > 0 ? (
                  <div className="transcript-readonly">
                    {selectedCall.transcript.map((turn, i) => (
                      <div key={i} className={`transcript-bubble ${turn.role}`}>
                        <div className="bubble-header">{turn.role === 'ai' ? 'AI Receptionist' : 'Caller'}</div>
                        <div className="bubble-text">{turn.text}</div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-muted">No transcript available for this call.</p>
                )}
              </div>
            </div>
          ) : (
            <div className="empty-state">Select a call to view details</div>
          )}
        </div>
      </div>
    </div>
  );
}
