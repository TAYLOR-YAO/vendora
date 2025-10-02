const base = process.env.NEXT_PUBLIC_API_BASE || '';
export async function api(path: string, opts: RequestInit = {}) {
  const res = await fetch(base + path, { ...opts, headers: { 'Content-Type': 'application/json', ...(opts.headers||{}) } });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}
