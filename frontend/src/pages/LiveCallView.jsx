import React, { useState, useEffect } from 'react';
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
import { Radio, Zap, Mic, AlertCircle } from 'lucide-react';
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
      <div className="live-call-wrapper-3d">
        <main className="dashboard-content-3d">
          {/* Multi-Call Queue Strip Bar */}
          <div className="queue-strip-row-3d">
            <CallQueueStrip
              calls={activeCalls}
              activeCallId={activeCallId}
              onSelectCall={setActiveCallId}
            />
            {activeCalls.length === 0 && (
              <div className="listening-pulse-chip">
                <span className="dot-pulse-green"></span>
                <span>Listening for incoming SignalWire calls...</span>
              </div>
            )}
          </div>

          {/* Connection status warning banners */}
          {liveCall.connectionState === 'RECONNECTING' && (
            <div className="connection-banner-3d reconnecting">
              <AlertCircle size={16} /> Connection dropped. Reconnecting to live WebSocket...
            </div>
          )}
          {liveCall.connectionState === 'DISCONNECTED' && activeCallId && (
            <div className="connection-banner-3d disconnected">
              <AlertCircle size={16} /> Live WebSocket disconnected.
            </div>
          )}
          {liveCall.connectionState === 'NOT_FOUND' && (
            <div className="connection-banner-3d disconnected">
              <AlertCircle size={16} /> Call session not found on server (404).
            </div>
          )}

          {loadError && (
            <div className="connection-banner-3d disconnected">
              <AlertCircle size={16} /> {loadError}
            </div>
          )}

          {liveCall.turnError && (
            <div className="connection-banner-3d disconnected">
              <AlertCircle size={16} /> Text Turn Failed: {liveCall.turnError}
            </div>
          )}

          {/* Voice Pipeline Selector Banner */}
          <div className="pipeline-selector-banner-3d">
            <div className="pipeline-title-group">
              <Mic size={18} style={{ color: '#0f766e' }} />
              <span className="pipeline-title-3d">AI Voice Engine:</span>
            </div>
            <div className="pipeline-toggle-group-3d">
              <button
                type="button"
                className={`pipeline-toggle-btn-3d ${liveCall.activeProvider === 'deepgram' ? 'active' : ''}`}
                onClick={() => liveCall.switchPipeline('deepgram')}
                disabled={liveCall.status === 'ENDED'}
              >
                <Radio size={14} /> Standard (Deepgram)
              </button>
              <button
                type="button"
                className={`pipeline-toggle-btn-3d ${liveCall.activeProvider === 'elevenlabs' ? 'active' : ''}`}
                onClick={() => liveCall.switchPipeline('elevenlabs')}
                disabled={liveCall.status === 'ENDED'}
              >
                <Zap size={14} /> Premium (ElevenLabs)
              </button>
            </div>
            <span className="pipeline-hint-3d">
              ⚡ Dynamically switches voice synthesis on next turn
            </span>
          </div>

          {/* Active Call Status Bar */}
          <LiveCallBanner
            callId={liveCall.callId}
            status={liveCall.status}
            duration={liveCall.duration}
            tenant={selectedTenant}
          />

          {/* 3-Column 3D Grid Layout */}
          <div className="dashboard-grid-3d">
            {/* Left Column: Patient Card */}
            <div className="grid-col-3d col-left-3d">
              <PatientCard patient={liveCall.patient} />
            </div>

            {/* Center Column: Waveform Orb + Low Confidence Banner + NLU Panel */}
            <div className="grid-col-3d col-center-3d">
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
            <div className="grid-col-3d col-right-3d">
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
