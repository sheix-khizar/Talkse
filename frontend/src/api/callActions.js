// Call Actions API client (End Call and Live Pipeline Switch).
// No fallback data — a failed request throws, and the caller is
// responsible for showing a real error to the user.

import { apiFetch } from './client';

export async function endCall(callId, getToken) {
  const res = await apiFetch(`/api/v1/calls/${callId}/end`, {
    method: 'POST'
  }, getToken);
  if (!res.ok) {
    throw new Error(`Failed to end call (${res.status})`);
  }
  return await res.json();
}

export async function setCallPipeline(callId, provider, getToken) {
  const res = await apiFetch(`/api/v1/calls/${callId}/pipeline`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ provider })
  }, getToken);
  if (!res.ok) {
    throw new Error(`Failed to switch pipeline (${res.status})`);
  }
  return await res.json();
}
