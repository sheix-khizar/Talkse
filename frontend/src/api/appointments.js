import { apiFetch } from './client';

export async function fetchAppointments(getToken) {
  const res = await apiFetch('/api/v1/appointments/', {}, getToken);
  if (!res.ok) throw new Error('Failed to fetch appointments');
  return res.json();
}
