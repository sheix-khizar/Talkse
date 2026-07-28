import React, { memo } from 'react';
import './WaveformCenterpiece.css';

const WaveformCenterpiece = memo(function WaveformCenterpiece({ isTalking = true, intent = "Schedule Appointment" }) {
  return (
    <div className="waveform-centerpiece-container">
      {/* 3D Glass Cloud Bubble Shell */}
      <div className={`glass-cloud-wrapper ${isTalking ? 'is-talking' : ''}`}>
        {/* Animated Background Audio Spectrum Waves */}
        <div className={`waveform-spectrum left-spectrum ${isTalking ? 'animating' : 'paused'}`}>
          <div className="bar bar-1"></div>
          <div className="bar bar-2"></div>
          <div className="bar bar-3"></div>
          <div className="bar bar-4"></div>
          <div className="bar bar-5"></div>
          <div className="bar bar-6"></div>
          <div className="bar bar-7"></div>
        </div>

        <div className={`waveform-spectrum right-spectrum ${isTalking ? 'animating' : 'paused'}`}>
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
            {isTalking ? 'AI RECEPCIONIST: TALKING...' : 'AI RECEPCIONIST: LISTENING...'}
          </h2>
          <p className="ai-intent-sub">Current Intent: {intent}</p>
        </div>
      </div>
    </div>
  );
});

export default WaveformCenterpiece;
