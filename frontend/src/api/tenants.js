import { apiFetch } from './client';

export async function fetchTenantConfig(tenantId, getToken) {
  const res = await apiFetch(`/api/v1/tenants/${tenantId}/config`, {}, getToken);
  if (!res.ok) throw new Error('Failed to fetch clinic config');
  return res.json();
}

export async function updateTenantPlan(tenantId, plan, getToken) {
  const res = await apiFetch(`/api/v1/tenants/${tenantId}/plan`, {
    method: 'PUT',
    body: JSON.stringify({ plan })
  }, getToken);
  if (!res.ok) throw new Error('Failed to update plan');
  return res.json();
}
