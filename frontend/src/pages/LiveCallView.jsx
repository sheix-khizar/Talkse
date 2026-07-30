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
import { getActiveCalls, startNewCall } from '../api/calls';
import './LiveCallView.css';

export default function LiveCallView() {
  const { selectedTenant } = useTenant();
  const [activeCallId, setActiveCallId] = useState(null);
  const [activeCalls, setActiveCalls] = useState([]);
  const [loadError, setLoadError] = useState(null);
  const [voiceTier, setVoiceTier] = useState('free');

  useEffect(() => {
    let cancelled = false;
    getActiveCalls()
      .then((calls) => {
        if (cancelled) return;
        setLoadError(null);
        setActiveCalls(calls || []);
        setActiveCallId(calls && calls.length > 0 ? calls[0].id : null);
      })
      .catch((err) => {
        if (cancelled) return;
        console.error(err);
        setLoadError('Could not load active calls — backend is unreachable.');
        setActiveCalls([]);
        setActiveCallId(null);
      });
    return () => { cancelled = true; };
  }, [selectedTenant.id]);

  const [startError, setStartError] = useState(null);

  const handleStartCall = async () => {
    setStartError(null);
    try {
      const { call_id } = await startNewCall(selectedTenant.id, voiceTier);
      setActiveCalls((prev) => [
        ...prev,
        { id: call_id, status: 'ACTIVE', callerName: 'New Call (Dashboard)', service: 'General Inquiry', duration: '00:00' },
      ]);
      setActiveCallId(call_id);
    } catch (err) {
      setStartError('Could not start a new call — is the backend running?');
    }
  };

  const liveCall = useLiveCall(activeCallId);
  const confidenceScore = liveCall.nlu?.intent?.confidence || 100;

  return (
    <ErrorBoundary>
      <div className="talkse-app">
        {/* Top Header Navigation */}
        <NavBar />

        {/* Main Dashboard Workspace */}
        <main className="dashboard-content">
          {/* Multi-Call Queue Strip */}
          <div className="queue-strip-row">
            <CallQueueStrip
              calls={activeCalls}
              activeCallId={activeCallId}
              onSelectCall={setActiveCallId}
            />
            <select 
              value={voiceTier} 
              onChange={e => setVoiceTier(e.target.value)}
              style={{ marginRight: '1rem', padding: '0.5rem', borderRadius: '4px', border: '1px solid #ccc' }}
            >
              <option value="free">Standard Voice (Deepgram)</option>
              <option value="paid">Premium Voice (ElevenLabs)</option>
            </select>
            <button className="btn-start-call" onClick={handleStartCall}>
              + Start Call
            </button>
          </div>
          {startError && <div className="connection-banner disconnected">{startError}</div>}

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
            <div className="connection-banner disconnected" style={{backgroundColor: '#ffebee', color: '#c62828'}}>
              ⚠️ Text Turn Failed: {liveCall.turnError}
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
