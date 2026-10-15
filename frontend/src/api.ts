export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message); }
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    ...options,
    headers: { 'Content-Type': 'application/json', 'X-Local-Request': '1', ...options.headers },
    signal: options.signal,
  });
  const data = await response.json();
  if (!response.ok) throw new ApiError(data.error || 'No se pudo completar la operación.', response.status);
  return data as T;
}

export const cents = (value: string | number): number => {
  const number = Number(value);
  return Number.isFinite(number) ? Math.round((number + Number.EPSILON) * 100) : 0;
};
export const amount = (value: number): string => (value / 100).toFixed(2);

export function operationKey(): string {
  const bytes = new Uint8Array(16);
  window.crypto.getRandomValues(bytes);
  bytes[6] = (bytes[6] & 15) | 64;
  bytes[8] = (bytes[8] & 63) | 128;
  const hex = Array.from(bytes, b => b.toString(16).padStart(2, '0')).join('');
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

export function stored<T>(key: string, fallback: T): T {
  try { return JSON.parse(sessionStorage.getItem(key) || 'null') || fallback; }
  catch { return fallback; }
}
