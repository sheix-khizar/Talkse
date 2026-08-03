// Integration Test Simulation for Live Call Sequence
export function runLiveCallSimulation(onEvent) {
  const events = [
    {
      delay: 500,
      event: {
        type: 'call.started',
        data: { callId: 'call_sim_991', callerPhone: '555-123-4567' }
      }
    },
    {
      delay: 1500,
      event: {
        type: 'transcript.partial',
        data: { role: 'customer', text: "Hi, I'm calling to book a Botox..." }
      }
    },
    {
      delay: 3000,
      event: {
        type: 'transcript.final',
        data: { role: 'customer', text: "Hi, I'm calling to book a Botox touch-up for tomorrow afternoon." }
      }
    },
    {
      delay: 4500,
      event: {
        type: 'transcript.final',
        data: { role: 'ai', text: "Certainly! I have an opening with Dr. Smith tomorrow at 4 PM." }
      }
    },
    {
      delay: 6000,
      event: {
        type: 'state.changed',
        data: {
          nlu: {
            intent: { label: 'Schedule Appointment', confidence: 100 },
            provider: { label: 'Dr. Smith', confidence: 100 },
            time: { label: '16:00, Tomorrow', confidence: 100 },
            service: { label: 'Botox Touch-up', confidence: 100 }
          }
        }
      }
    }
  ];

  events.forEach(({ delay, event }) => {
    setTimeout(() => {
      onEvent(event);
    }, delay);
  });
}
