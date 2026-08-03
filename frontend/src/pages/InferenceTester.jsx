import React, { useState, useEffect, useRef } from 'react';
import { Mic, MicOff, Send, PhoneCall, PhoneOff } from 'lucide-react';
import { useLiveCall } from '../hooks/useLiveCall';
import { startCall } from '../api/calls';
import './InferenceTester.css';

export default function InferenceTester() {
  const [activeCallId, setActiveCallId] = useState(null);
  const liveCall = useLiveCall(activeCallId);
  const [inputText, setInputText] = useState('');
  const transcriptRef = useRef(null);

  // Auto-scroll to bottom on transcript update
  useEffect(() => {
    if (transcriptRef.current) {
      transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight;
    }
  }, [liveCall.transcript]);

  const handleStartCall = async () => {
    try {
      const result = await startCall();
      if (result.call_id) {
        setActiveCallId(result.call_id);
      }
    } catch (err) {
      console.error("Failed to start new call", err);
    }
  };

  const handleEndCall = () => {
    if (liveCall.isMicActive) {
      liveCall.stopMicrophone();
    }
    setActiveCallId(null);
  };

  const handleSendText = (e) => {
    e.preventDefault();
    if (!inputText.trim()) return;
    liveCall.sendTextTurn(inputText);
    setInputText('');
  };

  return (
    <div className="inference-tester-container">
      <div className="tester-header">
        <h1>Voice AI Inference Tester</h1>
        <p>A simplified interface for interacting directly with the AI receptionist as a caller.</p>
      </div>

      {!activeCallId ? (
        <div className="start-call-section">
          <button className="btn-primary start-call-btn" onClick={handleStartCall}>
            <PhoneCall size={20} />
            Start New Call
          </button>
        </div>
      ) : (
        <div className="active-call-section">
          <div className="call-status-bar">
            <div className="status-indicator">
              <span className={`status-dot ${liveCall.connectionState === 'CONNECTED' ? 'green' : 'amber'}`}></span>
              <span className="status-text">
                {liveCall.connectionState === 'CONNECTED' ? 'Call Active' : liveCall.connectionState}
              </span>
            </div>
            <button className="btn-danger end-call-btn" onClick={handleEndCall}>
              <PhoneOff size={16} />
              End Call
            </button>
          </div>

          {/* AI State Visualization */}
          <div className="ai-visualization-panel">
            <div className={`ai-orb ${liveCall.isAiSpeaking ? 'ai-speaking' : 'ai-listening'}`}>
              <div className="orb-inner"></div>
            </div>
            <h3 className="ai-state-text">
              {liveCall.isAiSpeaking ? 'AI is speaking...' : 'AI is listening...'}
            </h3>
            {liveCall.nlu?.intent?.label && (
              <div className="nlu-pill">Intent: {liveCall.nlu.intent.label}</div>
            )}
          </div>

          {/* Transcript Area */}
          <div className="transcript-box" ref={transcriptRef}>
            {liveCall.transcript.map((msg) => {
              const isCustomer = msg.role === 'customer';
              return (
                <div key={msg.id} className={`chat-bubble-wrapper ${isCustomer ? 'user-wrapper' : 'ai-wrapper'}`}>
                  <div className={`chat-bubble ${isCustomer ? 'user-bubble' : 'ai-bubble'} ${msg.isPartial ? 'partial' : ''}`}>
                    <div className="bubble-sender">{isCustomer ? 'You' : 'AI'}</div>
                    <div className="bubble-text">
                      {msg.text}
                      {msg.isPartial && <span className="typing-dots">...</span>}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Input Controls */}
          <div className="input-controls">
            <button
              className={`mic-toggle-btn ${liveCall.isMicActive ? 'mic-active' : ''}`}
              onClick={liveCall.toggleMicrophone}
            >
              {liveCall.isMicActive ? <MicOff size={24} /> : <Mic size={24} />}
            </button>
            
            <form onSubmit={handleSendText} className="text-input-form">
              <input
                type="text"
                placeholder="Or type your message..."
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                className="text-input"
              />
              <button type="submit" className="send-text-btn" disabled={!inputText.trim()}>
                <Send size={18} />
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
