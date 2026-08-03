import React from 'react';
import './LiveCallBanner.css';

export default function LiveCallBanner({ callId, status, duration, tenant }) {
  return (
    <div className="live-call-banner">
      <div className="banner-left">
        <span className="live-dot" />
        <span className="live-title">LIVE CALL: {status}</span>
      </div>

      <div className="banner-center">
        <span className="banner-meta-item">
          <strong>Call ID:</strong> {callId}
        </span>
        <span className="banner-divider">|</span>
        <span className="banner-meta-item">
          <strong>Duration:</strong> {duration}
        </span>
      </div>

      <div className="banner-right">
        <span className="banner-meta-item">
          <strong>Tenant:</strong> {tenant?.name || 'Lumina Aesthetics'}
        </span>
        <span className="banner-divider">|</span>
        <span className="banner-meta-item">
          <strong>ID:</strong> {tenant?.id || '042'}
        </span>
      </div>
    </div>
  );
}
