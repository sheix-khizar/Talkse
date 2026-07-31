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
import './LiveCallView.css';

export default function LiveCallView() {
  const { selectedTenant } = useTenant();
  const [activeCallId, setActiveCallId] = useState('call_88f2e1a9d023');
  const [activeCalls, setActiveCalls] = useState([]);

  useEffect(() => {
    getActiveCalls(selectedTenant.id).then((calls) => {
      setActiveCalls(calls);
      if (calls.length > 0) {
        setActiveCallId(calls[0].id);
      }
    });
  }, [selectedTenant.id]);

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
          />

          {/* Connection status warning if disconnected or reconnecting */}
          {liveCall.connectionState === 'RECONNECTING' && (
            <div className="connection-banner reconnecting">
              🔄 Connection dropped. Reconnecting to live WebSocket...
            </div>
          )}
          {liveCall.connectionState === 'DISCONNECTED' && (
            <div className="connection-banner disconnected">
              ⚠️ Live WebSocket disconnected.
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
              />

              <LowConfidenceBanner confidenceScore={confidenceScore} />

              <NluBookingPanel nlu={liveCall.nlu} tenantId={selectedTenant.id} />
            </div>

            {/* Right Column: Live Transcript + Call Controls */}
            <div className="grid-col col-right">
              <LiveTranscript transcript={liveCall.transcript} />
              <CallControls callId={liveCall.callId} />
            </div>
          </div>
        </main>
      </div>
    </ErrorBoundary>
  );
}
