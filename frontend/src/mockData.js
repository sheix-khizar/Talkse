export const mockCallData = {
  callId: "call_88f2e1a9d023",
  status: "ACTIVE",
  duration: "01:24",
  tenant: {
    name: "Lumina Aesthetics",
    id: "042"
  },
  patient: {
    name: "Sarah Jenkins",
    avatar: "https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=150&q=80",
    phone: "555-123-4567",
    customerType: "Recurring Customer",
    category: "Lunnoeading",
    previousAppointments: [
      "Last Month - Botox",
      "Last Month - Dr. Smith",
      "Last Month - Botox Touch-up"
    ],
    notes: ""
  },
  nlu: {
    intent: { label: "Schedule Appointment", confidence: 100 },
    provider: { label: "Dr. Smith", confidence: 100 },
    time: { label: "16:00, Tuesday", confidence: 100 },
    service: { label: "Botox Touch-up", confidence: 100 }
  },
  transcript: [
    {
      id: "m1",
      speaker: "Customer",
      role: "customer",
      timestamp: "1:33 AM",
      avatar: "https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=150&q=80",
      text: "Hello, I'd like to book an appointment for a Botox touch-up. With onrl took actions in specific converzation?"
    },
    {
      id: "m2",
      speaker: "AI Receptionist",
      role: "ai",
      timestamp: "11:33 AM",
      avatar: null, // Will render teal AI badge icon
      text: "Hi Sarah! Certainly, I can help with that. Are you looking for a specific provider?"
    },
    {
      id: "m3",
      speaker: "Customer",
      role: "customer",
      timestamp: "11:03 AM",
      avatar: "https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=150&q=80",
      text: "Hello, I'd spenk to book an appointment for a Botox touch-up..."
    }
  ]
};
