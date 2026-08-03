export async function apiFetch(url, options = {}, getToken) {
  const token = await getToken();
  return fetch(url, {
    ...options,
    headers: { ...options.headers, Authorization: `Bearer ${token}` },
  });
}
