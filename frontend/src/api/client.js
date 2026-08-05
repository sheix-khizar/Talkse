export async function apiFetch(url, options = {}, getToken) {
  let token = null;
  if (typeof getToken === 'function') {
    try {
      token = await getToken();
    } catch (e) {
      token = null;
    }
  }
  const headers = { ...options.headers };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return fetch(url, {
    ...options,
    headers,
  });
}
