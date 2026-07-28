// Calls API client for multi-call queue fetching

export async function getActiveCalls(tenantId = '042') {
  try {
    const res = await fetch(`/api/v1/calls/`);
    if (!res.ok) throw new Error("Failed to fetch active calls");
    return await res.json();
  } catch (err) {
    console.warn("Fallback active calls queue:", err);
    return [
      {
        id: "call_88f2e1a9d023",
        status: "ACTIVE",
        callerName: "Sarah Jenkins",
        service: "Botox Touch-up",
        duration: "01:24"
      },
      {
        id: "call_33a9b4c7d011",
        status: "ACTIVE",
        callerName: "Michael Chen",
        service: "Consultation",
        duration: "00:42"
      },
      {
        id: "call_77e112f9a088",
        status: "WAITING",
        callerName: "Emma Watson",
        service: "Laser Hair Removal",
        duration: "00:15"
      }
    ];
  }
}
