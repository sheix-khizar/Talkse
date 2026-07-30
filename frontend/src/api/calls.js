// Calls API client for multi-call queue fetching.
// No fallback data — a failed request throws, and the caller is
// responsible for showing a real error to the user.

export async function getActiveCalls() {
  const res = await fetch(`/api/v1/calls/`);
  if (!res.ok) {
    throw new Error(`Failed to fetch active calls (${res.status})`);
  }
  return await res.json();
}

export async function startNewCall(tenantId = '042', plan = 'free') {
  const url = `/api/v1/calls/?tenant_id=${tenantId}&plan=${plan}`;
  const res = await fetch(url, { method: 'POST' });
  if (!res.ok) {
    throw new Error(`Failed to start call (${res.status})`);
  }
  return await res.json(); // { call_id, reply_text }
}
