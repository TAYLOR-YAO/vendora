import { NextResponse } from 'next/server';
export async function POST() {
  const out = NextResponse.json({ ok: true });
  out.cookies.set('access', '', { httpOnly: true, secure: true, sameSite: 'lax', path: '/', maxAge: 0 });
  out.cookies.set('refresh', '', { httpOnly: true, secure: true, sameSite: 'lax', path: '/', maxAge: 0 });
  return out;
}
