import { NextRequest, NextResponse } from 'next/server';
const BACKEND = (process.env.BACKEND_INTERNAL || 'http://127.0.0.1:8080').replace(/\/$/, '');
const ACCESS_MAX_AGE = 60 * 5;            // 5m
const REFRESH_MAX_AGE = 60 * 60 * 24 * 7; // 7d

export async function POST(req: NextRequest) {
  const body = await req.text(); // { email, password }
  const res = await fetch(`${BACKEND}/api/token/`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', 'accept': 'application/json' },
    body,
    redirect: 'manual',
  });

  const text = await res.text();
  let data: any = {}; try { data = JSON.parse(text || '{}'); } catch {}

  if (!res.ok) return NextResponse.json(data || { detail: 'Login failed' }, { status: res.status });

  const { access, refresh } = data || {};
  const out = NextResponse.json({ ok: true });
  out.cookies.set('access', access || '', { httpOnly: true, secure: true, sameSite: 'lax', path: '/', maxAge: ACCESS_MAX_AGE });
  out.cookies.set('refresh', refresh || '', { httpOnly: true, secure: true, sameSite: 'lax', path: '/', maxAge: REFRESH_MAX_AGE });
  return out;
}
