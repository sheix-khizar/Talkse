// Call Actions API client (End Call only — Hand-off and Transfer removed,
// no backend/telephony support for either and no plan to add them yet).
// No fallback data — a failed request throws, and the caller is
// responsible for showing a real error to the user.

export async function endCall(callId) {
  const res = await fetch(`/api/v1/calls/${callId}/end`, {
    method: 'POST'
  });
  if (!res.ok) {
    throw new Error(`Failed to end call (${res.status})`);
  }
  return await res.json();
}
