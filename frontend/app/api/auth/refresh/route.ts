import { NextRequest, NextResponse } from 'next/server';
const BACKEND = (process.env.BACKEND_INTERNAL || 'http://127.0.0.1:8080').replace(/\/$/, '');
const ACCESS_MAX_AGE = 60 * 5;

export async function POST(req: NextRequest) {
  const refresh = req.cookies.get('refresh')?.value;
  if (!refresh) return NextResponse.json({ detail: 'No refresh' }, { status: 401 });

  const res = await fetch(`${BACKEND}/api/token/refresh/`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', 'accept': 'application/json' },
    body: JSON.stringify({ refresh }),
    redirect: 'manual',
  });

  const data = await res.json().catch(() => ({}));
  if (!res.ok || !data?.access) return NextResponse.json({ detail: 'Refresh failed' }, { status: 401 });

  const out = NextResponse.json({ ok: true });
  out.cookies.set('access', data.access, { httpOnly: true, secure: true, sameSite: 'lax', path: '/', maxAge: ACCESS_MAX_AGE });
  return out;
}
