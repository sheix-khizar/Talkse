// Calls API client for multi-call queue fetching.
// No fallback data — a failed request throws, and the caller is
// responsible for showing a real error to the user.

import { apiFetch } from './client';

export async function getActiveCalls(getToken) {
  const res = await apiFetch(`/api/v1/calls/`, {}, getToken);
  if (!res.ok) {
    throw new Error(`Failed to fetch active calls (${res.status})`);
  }
  return await res.json();
}

export async function startNewCall(tenantId, planOverride, getToken) {
  const params = new URLSearchParams();
  if (tenantId) params.set('tenant_id', tenantId);
  if (planOverride === 'free' || planOverride === 'paid') {
    params.set('plan', planOverride);
  }
  const qs = params.toString();
  const res = await apiFetch(`/api/v1/calls/${qs ? `?${qs}` : ''}`, { method: 'POST' }, getToken);
  if (!res.ok) throw new Error(`Failed to start call (${res.status})`);
  return await res.json(); // { call_id, reply_text, tenant_id, plan }
}

export async function startCall() {
  try {
    const res = await fetch(`/api/v1/calls/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    });
    if (!res.ok) throw new Error("Failed to start call");
    return await res.json();
  } catch (err) {
    console.warn("Failed to start call via API:", err);
    throw err;
  }
}
