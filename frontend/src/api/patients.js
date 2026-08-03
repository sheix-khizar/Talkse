// Patient API client. No fallback data. A 404 means "no patient record
// yet" and is treated as a normal, expected result (returns null) — any
// other failure throws and the caller shows a real error.

import { apiFetch } from './client';

export async function getPatientByPhone(tenantId, phone, getToken) {
  const response = await apiFetch(
    `/api/v1/tenants/${tenantId}/patients?phone=${encodeURIComponent(phone)}`,
    {},
    getToken
  );
  if (response.status === 404) {
    return null;
  }
  if (!response.ok) {
    throw new Error(`Patient fetch failed (${response.status})`);
  }
  return await response.json();
}
