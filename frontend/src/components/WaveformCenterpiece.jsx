import React, { memo } from 'react';
import { Mic, MicOff } from 'lucide-react';
import './WaveformCenterpiece.css';

const WaveformCenterpiece = memo(function WaveformCenterpiece({
  isTalking = true,
  isUserSpeaking = false,
  intent = "Schedule Appointment",
  isMicActive = false,
  onToggleMic
}) {
  const isAnimating = isTalking || isUserSpeaking;

  let statusText;
  if (isTalking) {
    statusText = 'AI RECEPTIONIST: TALKING...';
  } else if (isUserSpeaking) {
    statusText = 'LISTENING: YOU ARE SPEAKING...';
  } else if (isMicActive) {
    statusText = 'READY — WAITING FOR YOU TO SPEAK';
  } else {
    statusText = 'MIC OFF';
  }

  return (
    <div className="waveform-centerpiece-container">
      {/* 3D Glass Cloud Bubble Shell */}
      <div className={`glass-cloud-wrapper ${isTalking ? 'is-talking' : ''} ${isUserSpeaking ? 'is-listening' : ''}`}>
        {/* Animated Background Audio Spectrum Waves */}
        <div className={`waveform-spectrum left-spectrum ${isAnimating ? 'animating' : 'paused'}`}>
          <div className="bar bar-1"></div>
          <div className="bar bar-2"></div>
          <div className="bar bar-3"></div>
          <div className="bar bar-4"></div>
          <div className="bar bar-5"></div>
          <div className="bar bar-6"></div>
          <div className="bar bar-7"></div>
        </div>

        <div className={`waveform-spectrum right-spectrum ${isAnimating ? 'animating' : 'paused'}`}>
          <div className="bar bar-7"></div>
          <div className="bar bar-6"></div>
          <div className="bar bar-5"></div>
          <div className="bar bar-4"></div>
          <div className="bar bar-3"></div>
          <div className="bar bar-2"></div>
          <div className="bar bar-1"></div>
        </div>

        {/* Fluid Glass Orb Elements */}
        <div className="fluid-orb orb-1"></div>
        <div className="fluid-orb orb-2"></div>
        <div className="fluid-orb orb-3"></div>

        {/* Center Text Overlay */}
        <div className="center-content">
          <h2 className="ai-status-heading">
            {statusText}
          </h2>
          <p className="ai-intent-sub">Current Intent: {intent}</p>
          
          {onToggleMic && (
            <button
              onClick={onToggleMic}
              style={{
                marginTop: '0.75rem',
                padding: '0.5rem 1rem',
                borderRadius: '20px',
                border: 'none',
                background: isMicActive ? '#ef4444' : '#0d9488',
                color: '#ffffff',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.5rem',
                boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                zIndex: 10
              }}
            >
              {isMicActive ? <MicOff size={16} /> : <Mic size={16} />}
              {isMicActive ? 'Mute Mic' : 'Start Speaking (Mic)'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
});

export default WaveformCenterpiece;
