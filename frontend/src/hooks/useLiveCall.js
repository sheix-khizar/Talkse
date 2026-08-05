import { useState, useEffect, useRef } from 'react';
import { getPatientByPhone } from '../api/patients';
import { apiFetch } from '../api/client';
import { setCallPipeline } from '../api/callActions';

export function useLiveCall(callId = null, getToken) {
  const [status, setStatus] = useState('ACTIVE');
  const [durationSeconds, setDurationSeconds] = useState(0);
  const [transcript, setTranscript] = useState([]);
  const [patient, setPatient] = useState(null);
  const [nlu, setNlu] = useState(null);
  const [isAiSpeaking, setIsAiSpeaking] = useState(false);
  const [activePlan, setActivePlan] = useState(null);
  const [activeProvider, setActiveProvider] = useState('deepgram');
  const [connectionState, setConnectionState] = useState(callId ? 'CONNECTING' : 'DISCONNECTED');
  const [turnError, setTurnError] = useState(null);

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
    if (status && status !== 'ENDED' && status !== 'DISCONNECTED' && status !== 'NOT_FOUND') {
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
      const wsEnvUrl = import.meta.env.VITE_WS_URL;
      const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
      const wsBase = wsEnvUrl || `${proto}://${window.location.host}`;
      const wsUrl = `${wsBase}/ws/calls/${callId}`;
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
          console.error(`WebSocket connection error for call ${callId}`);
          setConnectionState('ERROR');
        };

        socket.onclose = (event) => {
          if (isUnmounted) return;
          console.log("WebSocket closed", event.code);

          if (event.code === 4404) {
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
        console.error("WebSocket init error:", e);
        setConnectionState('ERROR');
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
          getPatientByPhone('tenant_042', data.callerPhone, getToken).then(setPatient);
        }
        if (data?.plan) {
          setActivePlan(data.plan);
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
        if (data?.voicePipeline) setActiveProvider(data.voicePipeline);
        break;

      case 'audio.chunk':
        enqueueAudioChunk(data.audio_base64);
        break;

      case 'call.ended':
        setStatus('ENDED');
        setIsAiSpeaking(false);
        break;

      default:
        break;
    }
  };

  const switchPipeline = async (provider) => {
    setActiveProvider(provider);
    if (!callId) return;
    try {
      await setCallPipeline(callId, provider, getToken);
    } catch (err) {
      console.error('Failed to switch pipeline:', err);
      setTurnError(err.message);
    }
  };

  const [isMicActive, setIsMicActive] = useState(false);
  const audioContextRef = useRef(null);
  const mediaStreamRef = useRef(null);
  const processorRef = useRef(null);

  // --- Echo prevention: mic frames are dropped while the AI is speaking. ---
  const micMutedRef = useRef(false);
  const muteGraceTimeoutRef = useRef(null);
  const ECHO_GRACE_PERIOD_MS = 400;

  const muteMic = () => {
    if (muteGraceTimeoutRef.current) {
      clearTimeout(muteGraceTimeoutRef.current);
      muteGraceTimeoutRef.current = null;
    }
    micMutedRef.current = true;
  };

  const unmuteMicAfterGrace = () => {
    if (muteGraceTimeoutRef.current) clearTimeout(muteGraceTimeoutRef.current);
    muteGraceTimeoutRef.current = setTimeout(() => {
      micMutedRef.current = false;
      muteGraceTimeoutRef.current = null;
    }, ECHO_GRACE_PERIOD_MS);
  };

  // --- Playback queue ---
  const audioQueueRef = useRef([]);
  const isPlayingRef = useRef(false);
  const currentAudioUrlRef = useRef(null);

  const enqueueAudioChunk = (base64Audio) => {
    audioQueueRef.current.push(base64Audio);
    if (!isPlayingRef.current) {
      playNextInQueue();
    }
  };

  const playNextInQueue = () => {
    if (audioQueueRef.current.length === 0) {
      isPlayingRef.current = false;
      unmuteMicAfterGrace();
      return;
    }

    isPlayingRef.current = true;
    muteMic();

    const base64Audio = audioQueueRef.current.shift();
    try {
      const binary = atob(base64Audio);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
      const blob = new Blob([bytes], { type: 'audio/wav' });
      const url = URL.createObjectURL(blob);
      currentAudioUrlRef.current = url;

      const audio = new Audio(url);
      audio.onended = () => {
        URL.revokeObjectURL(url);
        playNextInQueue();
      };
      audio.onerror = (err) => {
        console.error('Audio playback error:', err);
        URL.revokeObjectURL(url);
        playNextInQueue();
      };
      audio.play().catch((err) => {
        console.warn('Audio playback blocked:', err);
        URL.revokeObjectURL(url);
        playNextInQueue();
      });
    } catch (err) {
      console.error('Failed to play audio chunk:', err);
      playNextInQueue();
    }
  };

  const startMicrophone = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      mediaStreamRef.current = stream;

      const audioCtx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
      audioContextRef.current = audioCtx;

      const source = audioCtx.createMediaStreamSource(stream);

      if (audioCtx.audioWorklet) {
        const workletCode = `
          class PCMProcessor extends AudioWorkletProcessor {
            constructor() {
              super();
              this.buffer = new Int16Array(3200);
              this.bufferIdx = 0;
            }
            process(inputs) {
              const input = inputs[0];
              if (input && input.length > 0) {
                const channelData = input[0];
                if (channelData) {
                  for (let i = 0; i < channelData.length; i++) {
                    const s = Math.max(-1, Math.min(1, channelData[i]));
                    this.buffer[this.bufferIdx++] = s < 0 ? s * 0x8000 : s * 0x7FFF;
                    if (this.bufferIdx >= 3200) {
                      const sendBuffer = this.buffer.slice(0, 3200);
                      this.port.postMessage(sendBuffer.buffer, [sendBuffer.buffer]);
                      this.bufferIdx = 0;
                    }
                  }
                }
              }
              return true;
            }
          }
          registerProcessor('pcm-processor', PCMProcessor);
        `;
        const blob = new Blob([workletCode], { type: 'application/javascript' });
        const workletUrl = URL.createObjectURL(blob);
        await audioCtx.audioWorklet.addModule(workletUrl);
        URL.revokeObjectURL(workletUrl);

        const workletNode = new AudioWorkletNode(audioCtx, 'pcm-processor');
        processorRef.current = workletNode;

        workletNode.port.onmessage = (e) => {
          if (micMutedRef.current) return;
          if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
          wsRef.current.send(e.data);
        };

        source.connect(workletNode);
        workletNode.connect(audioCtx.destination);
      } else {
        const processor = audioCtx.createScriptProcessor(4096, 1, 1);
        processorRef.current = processor;

        processor.onaudioprocess = (e) => {
          if (micMutedRef.current) return;
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
      }

      setIsMicActive(true);
    } catch (err) {
      console.error("Microphone access failed:", err);
    }
  };

  const stopMicrophone = () => {
    if (muteGraceTimeoutRef.current) {
      clearTimeout(muteGraceTimeoutRef.current);
      muteGraceTimeoutRef.current = null;
    }
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
    setTurnError(null);
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

      const res = await apiFetch(`/api/v1/calls/${callId}/turn`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
      }, getToken);

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
            enqueueAudioChunk(data.audio_base64);
          }
        }
        if (data.state) {
          if (data.state.status) setStatus(data.state.status);
          if (data.state.intent) {
            setNlu({
              intent: { label: data.state.intent, confidence: 95 },
              service: data.state.service,
              time: data.state.preferred_time,
              callerName: data.state.caller_name
            });
          }
        }
      } else {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Backend error: ${res.status} ${res.statusText}`);
      }
    } catch (err) {
      console.error("Failed to send text turn:", err);
      setTurnError(err.message);
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
    sendTextTurn,
    turnError,
    activePlan,
    activeProvider,
    switchPipeline,
  };
}
