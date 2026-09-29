export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

export async function api(path, options = {}) {
  const response = await fetch(API_BASE_URL + path, {
    credentials: 'same-origin',
    ...options,
    headers: { 'Content-Type': 'application/json', ...options.headers },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401 && !path.startsWith('/auth/')) {
      window.dispatchEvent(new Event('session-expired'));
    }
    const detail = Array.isArray(data.detail)
      ? data.detail.map(item => item.msg).join('; ')
      : data.detail;
    throw new Error(detail || 'Request failed. Please try again.');
  }
  return data;
}

export const post = (path, data, options = {}) =>
  api(path, { method: 'POST', body: JSON.stringify(data), ...options });
