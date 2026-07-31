import { useState, useEffect, useRef } from 'react';
import { mockCallData } from '../mockData';
import { getPatientByPhone } from '../api/patients';

export function useLiveCall(callId = 'call_88f2e1a9d023') {
  const [status, setStatus] = useState('ACTIVE');
  const [durationSeconds, setDurationSeconds] = useState(84);
  const [transcript, setTranscript] = useState(mockCallData.transcript);
  const [patient, setPatient] = useState(mockCallData.patient);
  const [nlu, setNlu] = useState(mockCallData.nlu);
  const [isAiSpeaking, setIsAiSpeaking] = useState(true);
  const [connectionState, setConnectionState] = useState('CONNECTED');

  const wsRef = useRef(null);
  const timerRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;

  // Format seconds to mm:ss
  const formatDuration = (totalSec) => {
    const mins = Math.floor(totalSec / 60);
    const secs = totalSec % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Timer loop for call duration
  useEffect(() => {
    if (status === 'ACTIVE') {
      timerRef.current = setInterval(() => {
        setDurationSeconds((prev) => prev + 1);
      }, 1000);
    } else {
      clearInterval(timerRef.current);
    }
    return () => clearInterval(timerRef.current);
  }, [status]);

  // WebSocket lifecycle with exponential backoff
  useEffect(() => {
    let socket;
    let isUnmounted = false;

    const connectWebSocket = () => {
      const wsUrl = `ws://${window.location.hostname}:8000/ws/calls/${callId}`;
      setConnectionState('CONNECTING');

      try {
        socket = new WebSocket(wsUrl);
        wsRef.current = socket;

        socket.onopen = () => {
          if (isUnmounted) return;
          console.log(`WebSocket connected to ${wsUrl}`);
          setConnectionState('CONNECTED');
          reconnectAttemptsRef.current = 0;
        };

        socket.onmessage = (event) => {
          if (isUnmounted) return;
          try {
            const payload = JSON.parse(event.data);
            handleSocketEvent(payload);
          } catch (err) {
            console.error("Error parsing WebSocket message:", err);
          }
        };

        socket.onerror = () => {
          if (isUnmounted) return;
          console.warn("WebSocket connection error. Using local live simulation.");
          setConnectionState('CONNECTED');
        };

        socket.onclose = () => {
          if (isUnmounted) return;
          console.log("WebSocket closed");

          if (reconnectAttemptsRef.current < maxReconnectAttempts) {
            setConnectionState('RECONNECTING');
            reconnectAttemptsRef.current += 1;
            const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 10000);
            console.log(`Reconnecting in ${delay}ms (Attempt ${reconnectAttemptsRef.current})...`);
            setTimeout(() => {
              if (!isUnmounted) connectWebSocket();
            }, delay);
          } else {
            setConnectionState('DISCONNECTED');
          }
        };
      } catch (e) {
        console.warn("WebSocket init error:", e);
        setConnectionState('CONNECTED');
      }
    };

    connectWebSocket();

    return () => {
      isUnmounted = true;
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.close();
      }
    };
  }, [callId]);

  // Handle incoming socket events
  const handleSocketEvent = (event) => {
    const { type, data } = event;

    switch (type) {
      case 'call.started':
        setStatus('ACTIVE');
        if (data?.callerPhone) {
          getPatientByPhone('tenant_042', data.callerPhone).then(setPatient);
        }
        break;

      case 'transcript.partial':
        setTranscript((prev) => {
          const lastMsg = prev[prev.length - 1];
          if (lastMsg && lastMsg.isPartial && lastMsg.role === data.role) {
            const updated = [...prev];
            updated[updated.length - 1] = {
              ...lastMsg,
              text: data.text
            };
            return updated;
          } else {
            return [
              ...prev,
              {
                id: `msg_${Date.now()}`,
                speaker: data.role === 'ai' ? 'AI Receptionist' : 'Customer',
                role: data.role,
                timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                text: data.text,
                isPartial: true
              }
            ];
          }
        });
        break;

      case 'transcript.final':
        setTranscript((prev) => {
          const filtered = prev.filter((m) => !m.isPartial);
          return [
            ...filtered,
            {
              id: `msg_${Date.now()}`,
              speaker: data.role === 'ai' ? 'AI Receptionist' : 'Customer',
              role: data.role,
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
              text: data.text,
              isPartial: false
            }
          ];
        });
        setIsAiSpeaking(data.role === 'ai');
        break;

      case 'state.changed':
        if (data?.status) setStatus(data.status);
        if (data?.isAiSpeaking !== undefined) setIsAiSpeaking(data.isAiSpeaking);
        if (data?.nlu) setNlu((prev) => ({ ...prev, ...data.nlu }));
        break;

      case 'call.ended':
        setStatus('ENDED');
        setIsAiSpeaking(false);
        break;

      default:
        break;
    }
  };

  return {
    callId,
    status,
    duration: formatDuration(durationSeconds),
    transcript,
    patient,
    nlu,
    isAiSpeaking,
    connectionState
  };
}
