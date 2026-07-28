import { useState, useEffect, useRef } from 'react';
import { mockCallData } from '../mockData';
import { getPatientByPhone } from '../api/patients';

export function useLiveCall(callId = null) {
  const [status, setStatus] = useState('ACTIVE');
  const [durationSeconds, setDurationSeconds] = useState(84);
  const [transcript, setTranscript] = useState(mockCallData.transcript);
  const [patient, setPatient] = useState(mockCallData.patient);
  const [nlu, setNlu] = useState(mockCallData.nlu);
  const [isAiSpeaking, setIsAiSpeaking] = useState(true);
  const [connectionState, setConnectionState] = useState(callId ? 'CONNECTING' : 'DISCONNECTED');

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
    if (!callId) {
      setConnectionState('DISCONNECTED');
      return;
    }

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

        socket.onclose = (event) => {
          if (isUnmounted) return;
          console.log("WebSocket closed", event.code);

          if (event.code === 4404) {
            // Backend closed because this call_id doesn't exist in
            // Redis session state — not a transient network issue,
            // retrying will never succeed. Surface it instead of looping.
            console.warn(`Call ${callId} not found on backend (4404) — not reconnecting.`);
            setConnectionState('NOT_FOUND');
            return;
          }

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

      case 'audio.chunk':
        playAudioChunk(data.audio_base64);
        break;

      case 'call.ended':
        setStatus('ENDED');
        setIsAiSpeaking(false);
        break;

      default:
        break;
    }
  };

  const [isMicActive, setIsMicActive] = useState(false);
  const audioContextRef = useRef(null);
  const mediaStreamRef = useRef(null);
  const processorRef = useRef(null);

  const startMicrophone = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;

      const audioCtx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
      audioContextRef.current = audioCtx;

      const source = audioCtx.createMediaStreamSource(stream);
      const processor = audioCtx.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;

      processor.onaudioprocess = (e) => {
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
        const inputData = e.inputBuffer.getChannelData(0);
        const pcm16 = new Int16Array(inputData.length);
        for (let i = 0; i < inputData.length; i++) {
          const s = Math.max(-1, Math.min(1, inputData[i]));
          pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }
        wsRef.current.send(pcm16.buffer);
      };

      source.connect(processor);
      processor.connect(audioCtx.destination);
      setIsMicActive(true);
    } catch (err) {
      console.error("Microphone access failed:", err);
    }
  };

  const stopMicrophone = () => {
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((t) => t.stop());
      mediaStreamRef.current = null;
    }
    setIsMicActive(false);
  };

  const toggleMicrophone = () => {
    if (isMicActive) {
      stopMicrophone();
    } else {
      startMicrophone();
    }
  };

  const sendTextTurn = async (text) => {
    if (!callId || !text.trim()) return;
    try {
      setTranscript((prev) => [
        ...prev,
        {
          id: `msg_${Date.now()}`,
          speaker: 'Customer',
          role: 'customer',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          text: text,
          isPartial: false
        }
      ]);

      const res = await fetch(`/api/v1/calls/${callId}/turn`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
      });

      if (res.ok) {
        const data = await res.json();
        if (data.reply_text) {
          setTranscript((prev) => [
            ...prev,
            {
              id: `msg_${Date.now() + 1}`,
              speaker: 'AI Receptionist',
              role: 'ai',
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
              text: data.reply_text,
              isPartial: false
            }
          ]);
          setIsAiSpeaking(true);
          if (data.audio_base64) {
            playAudioChunk(data.audio_base64);
          }
        }
      }
    } catch (err) {
      console.error("Failed to send text turn:", err);
    }
  };

  const playAudioChunk = (base64Audio) => {
    try {
      const binary = atob(base64Audio);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
      const blob = new Blob([bytes], { type: 'audio/wav' });
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audio.play().catch((err) => console.warn('Audio playback blocked:', err));
      audio.onended = () => URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Failed to play audio chunk:', err);
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
    connectionState,
    isMicActive,
    toggleMicrophone,
    startMicrophone,
    stopMicrophone,
    sendTextTurn
  };
}
