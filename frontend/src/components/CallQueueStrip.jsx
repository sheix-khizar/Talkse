import React from 'react';
import { PhoneCall, Clock } from 'lucide-react';
import './CallQueueStrip.css';

export default function CallQueueStrip({ calls = [], activeCallId, onSelectCall }) {
  return (
    <div className="call-queue-strip">
      <div className="queue-label">
        <PhoneCall size={14} />
        <span>LIVE CALL QUEUE ({calls.length})</span>
      </div>

      <div className="queue-chips-container">
        {calls.map((call) => {
          const isSelected = call.id === activeCallId;
          const isWaiting = call.status === 'WAITING';

          return (
            <button
              key={call.id}
              onClick={() => onSelectCall(call.id)}
              className={`queue-chip ${isSelected ? 'selected' : ''} ${isWaiting ? 'waiting' : 'active'}`}
            >
              <span className={`chip-dot ${isWaiting ? 'dot-amber' : 'dot-green'}`} />
              <div className="chip-meta">
                <span className="chip-name">{call.callerName}</span>
                <span className="chip-service">{call.service}</span>
              </div>
              <span className="chip-time">
                <Clock size={12} />
                {call.duration}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
