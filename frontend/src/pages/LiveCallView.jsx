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
import { getActiveCalls, startCall } from '../api/calls';
import './LiveCallView.css';

export default function LiveCallView() {
  const { selectedTenant } = useTenant();
  const [activeCallId, setActiveCallId] = useState(null);
  const [activeCalls, setActiveCalls] = useState([]);

  const refreshCalls = () => {
    getActiveCalls(selectedTenant.id).then((calls) => {
      setActiveCalls(calls || []);
      if (calls && calls.length > 0) {
        if (!activeCallId || !calls.find(c => c.id === activeCallId)) {
          setActiveCallId(calls[0].id);
        }
      } else {
        setActiveCallId(null);
      }
    });
  };

  useEffect(() => {
    refreshCalls();
  }, [selectedTenant.id]);

  const handleNewCall = async () => {
    try {
      const result = await startCall();
      if (result.call_id) {
        setActiveCallId(result.call_id);
        setTimeout(refreshCalls, 500); // Wait a bit for backend to process
      }
    } catch (err) {
      console.error("Failed to start new call", err);
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
          <CallQueueStrip
            calls={activeCalls}
            activeCallId={activeCallId}
            onSelectCall={setActiveCallId}
            onNewCall={handleNewCall}
          />

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
