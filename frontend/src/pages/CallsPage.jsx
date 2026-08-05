import React, { useEffect, useState } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { apiFetch } from '../api/client';
import { 
  PhoneCall, 
  Clock, 
  User, 
  CheckCircle2, 
  XCircle, 
  RefreshCw, 
  Bot, 
  MessageSquare, 
  Calendar,
  Sparkles,
  ChevronRight,
  ShieldAlert,
  FileText
} from 'lucide-react';
import './CallsPage.css';

// Helper for patient initials avatar
const getInitials = (name) => {
  if (!name || name === 'Unknown' || name === 'Unknown Caller') return 'UC';
  const parts = name.trim().split(' ');
  if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  return name.slice(0, 2).toUpperCase();
};

export default function CallsPage() {
  const { getToken } = useAuth();
  const [calls, setCalls] = useState([]);
  const [selectedCall, setSelectedCall] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadCalls = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch('/api/v1/calls/history', {}, getToken);
      if (!res.ok) throw new Error('Failed to fetch call history');
      const data = await res.json();
      setCalls(data || []);
      if (data && data.length > 0) setSelectedCall(data[0]);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
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
        <div className="glass-loader-card">
          <div className="cube-loader">
            <div className="cube-face cube-front"></div>
            <div className="cube-face cube-back"></div>
            <div className="cube-face cube-right"></div>
            <div className="cube-face cube-left"></div>
            <div className="cube-face cube-top"></div>
            <div className="cube-face cube-bottom"></div>
          </div>
          <p className="loading-text">Loading 3D Call Records...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container calls-3d-wrapper">
      {/* ── Page Header ── */}
      <div className="page-header-3d">
        <div className="header-title-group">
          <div className="header-icon-glow">
            <PhoneCall className="icon-3d" size={28} />
          </div>
          <div>
            <h2 className="page-title-3d">Telephony Call Logs</h2>
            <p className="page-subtitle-3d">Real-time transcripts, AI session recordings & caller details</p>
          </div>
        </div>

        <button className="refresh-btn-3d" onClick={loadCalls} title="Refresh Call Logs">
          <RefreshCw size={16} className={loading ? 'spin' : ''} />
          <span>Sync Calls</span>
        </button>
      </div>

      {error && (
        <div className="error-banner-3d">
          <XCircle size={20} />
          <span>{error}</span>
        </div>
      )}

      {/* ── Main 3D Layout ── */}
      <div className="calls-layout-3d">
        {/* Left Column: Call History List */}
        <div className="calls-sidebar-3d">
          <div className="sidebar-header">
            <h3 className="sidebar-title">Recent Inbound Calls</h3>
            <span className="count-badge-3d">{calls.length} Logs</span>
          </div>

          <div className="calls-list-scroll">
            {calls.length === 0 ? (
              <div className="empty-calls-list">
                <PhoneCall size={32} />
                <p>No call history recorded yet.</p>
              </div>
            ) : (
              calls.map(call => {
                const callerName = call.caller_name || 'Unknown Caller';
                const isSelected = selectedCall?.id === call.id;
                const statusDone = call.status === 'done' || call.status === 'completed';

                return (
                  <div 
                    key={call.id} 
                    className={`call-card-3d ${isSelected ? 'card-selected' : ''}`}
                    onClick={() => fetchCallDetails(call.call_id || call.id)}
                  >
                    <div className="call-card-top">
                      <div className="caller-avatar-sm">
                        {getInitials(callerName)}
                      </div>
                      <div className="caller-main-info">
                        <h4 className="caller-name-text">{callerName}</h4>
                        <span className="call-time-text">
                          {new Date(call.ended_at || call.created_at).toLocaleString([], {
                            month: 'short', 
                            day: 'numeric', 
                            hour: 'numeric', 
                            minute: '2-digit'
                          })}
                        </span>
                      </div>
                      <ChevronRight size={16} className="chevron-icon" />
                    </div>

                    <div className="call-card-bottom">
                      <span className={`status-pill-call ${statusDone ? 'status-done' : 'status-other'}`}>
                        <span className="dot-mini"></span>
                        {call.status || 'completed'}
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right Column: 3D Call Detail & Transcript Pane */}
        <div className="call-detail-pane-3d">
          {selectedCall ? (
            <div className="detail-content-3d">
              {/* Caller Header Card */}
              <div className="caller-detail-header-3d">
                <div className="caller-hero-flex">
                  <div className="caller-avatar-lg">
                    {getInitials(selectedCall.caller_name)}
                  </div>
                  <div>
                    <h3 className="caller-title-lg">{selectedCall.caller_name || 'Unknown Caller'}</h3>
                    <span className="call-id-sub">Call ID: {selectedCall.call_id || selectedCall.id}</span>
                  </div>
                </div>

                <div className={`status-badge-lg ${selectedCall.status === 'done' ? 'bg-done' : 'bg-other'}`}>
                  <CheckCircle2 size={16} />
                  <span className="capitalize">{selectedCall.status}</span>
                </div>
              </div>

              {/* Call Meta Grid */}
              <div className="meta-chips-grid-3d">
                <div className="meta-chip-item">
                  <span className="chip-label"><Clock size={12} /> Call Date</span>
                  <span className="chip-val">
                    {new Date(selectedCall.ended_at || selectedCall.created_at).toLocaleString()}
                  </span>
                </div>

                <div className="meta-chip-item">
                  <span className="chip-label"><Sparkles size={12} /> Voice Pipeline</span>
                  <span className="chip-val">ElevenLabs / Deepgram</span>
                </div>

                {selectedCall.booking_result && (
                  <div className="meta-chip-item">
                    <span className="chip-label"><Calendar size={12} /> Booking Outcome</span>
                    <span className="chip-val highlight-green">{selectedCall.booking_result.status || 'Confirmed'}</span>
                  </div>
                )}
              </div>

              {/* Transcript Section */}
              <div className="transcript-section-3d">
                <div className="transcript-header-flex">
                  <div className="header-left-flex">
                    <MessageSquare size={18} className="chat-icon" />
                    <h4>Call Transcript Conversation</h4>
                  </div>
                  <span className="turns-count">
                    {selectedCall.transcript ? selectedCall.transcript.length : 0} Turns
                  </span>
                </div>

                {selectedCall.transcript && selectedCall.transcript.length > 0 ? (
                  <div className="transcript-bubbles-scroll-3d">
                    {selectedCall.transcript.map((turn, i) => {
                      const isAI = turn.role === 'ai' || turn.role === 'assistant';

                      return (
                        <div key={i} className={`chat-bubble-wrapper ${isAI ? 'bubble-ai-wrap' : 'bubble-user-wrap'}`}>
                          <div className={`chat-bubble-3d ${isAI ? 'bubble-ai' : 'bubble-user'}`}>
                            <div className="bubble-role-header">
                              {isAI ? (
                                <>
                                  <Bot size={13} />
                                  <span>AI Receptionist</span>
                                </>
                              ) : (
                                <>
                                  <User size={13} />
                                  <span>{selectedCall.caller_name || 'Caller'}</span>
                                </>
                              )}
                            </div>
                            <p className="bubble-message-text">{turn.text}</p>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="empty-transcript-3d">
                    <FileText size={32} />
                    <p>No recorded audio transcript for this session.</p>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="empty-selection-3d">
              <PhoneCall size={48} />
              <h4>Select a Call Record</h4>
              <p>Choose an inbound call from the left menu to view details and transcript.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
