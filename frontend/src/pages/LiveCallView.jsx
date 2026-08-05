import React, { useState, useEffect } from 'react';
import NavBar from '../components/NavBar';
import CallQueueStrip from '../components/CallQueueStrip';
import LiveCallBanner from '../components/LiveCallBanner';
import PatientCard from '../components/PatientCard';
import WaveformCenterpiece from '../components/WaveformCenterpiece';
import NluBookingPanel from '../components/NluBookingPanel';
import LowConfidenceBanner from '../components/LowConfidenceBanner';
import LiveTranscript from '../components/LiveTranscript';
import CallControls from '../components/CallControls';
import ErrorBoundary from '../components/ErrorBoundary';
import { useLiveCall } from '../hooks/useLiveCall';
import { useTenant } from '../context/TenantContext';
import { getActiveCalls } from '../api/calls';
import { useAuth } from '@clerk/clerk-react';
import './LiveCallView.css';

export default function LiveCallView() {
  const { selectedTenant } = useTenant();
  const { getToken } = useAuth();
  const [activeCallId, setActiveCallId] = useState(null);
  const [activeCalls, setActiveCalls] = useState([]);
  const [loadError, setLoadError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    const fetchActiveCalls = () => {
      getActiveCalls(getToken)
        .then((calls) => {
          if (cancelled) return;
          setLoadError(null);
          const callList = calls || [];
          setActiveCalls(callList);

          // Auto-select incoming SignalWire call
          if (callList.length > 0) {
            setActiveCallId((prevId) => {
              const stillActive = callList.some((c) => c.id === prevId);
              return stillActive ? prevId : callList[0].id;
            });
          } else {
            setActiveCallId(null);
          }
        })
        .catch((err) => {
          if (cancelled) return;
          console.error(err);
          setLoadError('Could not load active calls — backend is unreachable.');
          setActiveCalls([]);
          setActiveCallId(null);
        });
    };

    fetchActiveCalls();
    const interval = setInterval(fetchActiveCalls, 2000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [selectedTenant.id, getToken]);

  const liveCall = useLiveCall(activeCallId, getToken);
  const confidenceScore = liveCall.nlu?.intent?.confidence || 100;

  return (
    <ErrorBoundary>
      <div className="talkse-app">

        {/* Main Dashboard Workspace */}
        <main className="dashboard-content">
          {/* Multi-Call Queue Strip */}
          <div className="queue-strip-row">
            <CallQueueStrip
              calls={activeCalls}
              activeCallId={activeCallId}
              onSelectCall={setActiveCallId}
            />
            {activeCalls.length === 0 && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#64748b', fontSize: '0.875rem' }}>
                <span className="pulse-dot" style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#22c55e', display: 'inline-block' }}></span>
                Listening for incoming SignalWire calls...
              </div>
            )}
          </div>

          {/* Connection status warning if disconnected, reconnecting or not found */}
          {liveCall.connectionState === 'RECONNECTING' && (
            <div className="connection-banner reconnecting">
              🔄 Connection dropped. Reconnecting to live WebSocket...
            </div>
          )}
          {liveCall.connectionState === 'DISCONNECTED' && activeCallId && (
            <div className="connection-banner disconnected">
              ⚠️ Live WebSocket disconnected.
            </div>
          )}
          {liveCall.connectionState === 'NOT_FOUND' && (
            <div className="connection-banner disconnected">
              ⚠️ Call session not found on server (4404).
            </div>
          )}

          {loadError && (
            <div className="connection-banner disconnected">⚠️ {loadError}</div>
          )}

          {liveCall.turnError && (
            <div className="connection-banner disconnected" style={{ backgroundColor: '#ffebee', color: '#c62828' }}>
              ⚠️ Text Turn Failed: {liveCall.turnError}
            </div>
          )}

          {liveCall.callId && (
            <div className="pipeline-selector-banner">
              <span className="pipeline-title">🎙️ Voice Pipeline:</span>
              <div className="pipeline-toggle-group">
                <button
                  type="button"
                  className={`pipeline-toggle-btn ${liveCall.activeProvider === 'deepgram' ? 'active' : ''}`}
                  onClick={() => liveCall.switchPipeline('deepgram')}
                  disabled={liveCall.status === 'ENDED'}
                >
                  Standard (Deepgram)
                </button>
                <button
                  type="button"
                  className={`pipeline-toggle-btn ${liveCall.activeProvider === 'elevenlabs' ? 'active' : ''}`}
                  onClick={() => liveCall.switchPipeline('elevenlabs')}
                  disabled={liveCall.status === 'ENDED'}
                >
                  ⚡ Premium (ElevenLabs)
                </button>
              </div>
              <span className="pipeline-hint">
                Switches the voice on the very next AI reply — no need to hang up.
              </span>
            </div>
          )}

          {/* Active Call Status Bar */}
          <LiveCallBanner
            callId={liveCall.callId}
            status={liveCall.status}
            duration={liveCall.duration}
            tenant={selectedTenant}
          />

          {/* 3-Column Grid Layout */}
          <div className="dashboard-grid">
            {/* Left Column: Patient Card */}
            <div className="grid-col col-left">
              <PatientCard patient={liveCall.patient} />
            </div>

            {/* Center Column: Waveform Orb + Low Confidence Banner + NLU Panel */}
            <div className="grid-col col-center">
              <WaveformCenterpiece
                isTalking={liveCall.isAiSpeaking}
                intent={liveCall.nlu?.intent?.label || 'Schedule Appointment'}
                isMicActive={liveCall.isMicActive}
                onToggleMic={liveCall.toggleMicrophone}
              />

              <LowConfidenceBanner confidenceScore={confidenceScore} />

              <NluBookingPanel nlu={liveCall.nlu} tenantId={selectedTenant.id} />
            </div>

            {/* Right Column: Live Transcript + Call Controls */}
            <div className="grid-col col-right">
              <LiveTranscript
                transcript={liveCall.transcript}
                onSendText={liveCall.sendTextTurn}
              />
              <CallControls callId={liveCall.callId} />
            </div>
          </div>
        </main>
      </div>
    </ErrorBoundary>
  );
}
