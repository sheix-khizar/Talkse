
// Appointment Booking API client. No fallback data — a failed booking
// throws and the caller must show the real error, since silently
// pretending a booking succeeded is actively dangerous (a customer could
// show up to an appointment that was never actually created).


import { apiFetch } from './client';

export async function createAppointment(tenantId, payload, getToken) {
  const response = await apiFetch(`/api/v1/tenants/${tenantId}/appointments`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      ...payload,
      idempotencyKey: payload.idempotencyKey || `app_web_${Date.now()}`
    })
  }, getToken);

  if (!response.ok) {
    const errData = await response.json().catch(() => ({}));
    throw new Error(errData.detail || `Booking creation failed (${response.status})`);
  }

  return await response.json();
}
