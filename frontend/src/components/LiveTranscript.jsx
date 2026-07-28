import React, { useState, useEffect, useRef, memo } from 'react';
import { MoreHorizontal, Send } from 'lucide-react';
import './LiveTranscript.css';

const LiveTranscript = memo(function LiveTranscript({ transcript, onSendText }) {
  const listRef = useRef(null);
  const [inputText, setInputText] = useState('');

  // Auto-scroll to bottom on transcript update
  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [transcript]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!inputText.trim() || !onSendText) return;
    onSendText(inputText);
    setInputText('');
  };

  return (
    <div className="transcript-container">
      <div className="transcript-header">
        <h3 className="transcript-title">LIVE TRANSCRIPT</h3>
        <button className="transcript-menu-btn" aria-label="Transcript options">
          <MoreHorizontal size={18} />
        </button>
      </div>

      <div
        className="transcript-list"
        ref={listRef}
        role="log"
        aria-live="polite"
        aria-atomic="false"
        tabIndex={0}
      >
        {transcript.map((msg) => {
          const isCustomer = msg.role === 'customer';
          return (
            <div key={msg.id} className={`transcript-item ${msg.isPartial ? 'partial-msg' : ''}`}>
              <div className="msg-header">
                <div className="speaker-info">
                  {isCustomer ? (
                    <img
                      src={msg.avatar || "https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=150&q=80"}
                      alt={msg.speaker}
                      className="speaker-avatar"
                    />
                  ) : (
                    <div className="ai-speaker-badge">
                      <span>AI</span>
                    </div>
                  )}
                  <span className="speaker-name">{msg.speaker}</span>
                </div>
                <span className="msg-timestamp">{msg.timestamp}</span>
              </div>
              <p className="msg-bubble-text">
                {msg.text}
                {msg.isPartial && <span className="typing-cursor">...</span>}
              </p>
            </div>
          );
        })}
      </div>

      {onSendText && (
        <form onSubmit={handleSubmit} style={{ display: 'flex', padding: '0.5rem', gap: '0.5rem', borderTop: '1px solid #e2e8f0' }}>
          <input
            type="text"
            placeholder="Type a response..."
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            style={{
              flex: 1,
              padding: '0.5rem 0.75rem',
              borderRadius: '8px',
              border: '1px solid #cbd5e1',
              fontSize: '0.875rem'
            }}
          />
          <button
            type="submit"
            style={{
              padding: '0.5rem 0.75rem',
              borderRadius: '8px',
              border: 'none',
              background: '#0d9488',
              color: '#fff',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
            <Send size={16} />
          </button>
        </form>
      )}
    </div>
  );
});

export default LiveTranscript;
