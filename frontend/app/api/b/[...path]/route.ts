import { NextRequest, NextResponse } from 'next/server';

const BACKEND = (process.env.BACKEND_INTERNAL || 'http://127.0.0.1:8080').replace(/\/$/, '');

function joinURL(base: string, path: string) {
  return base + (path.startsWith('/') ? path : '/' + path);
}

export async function ALL(req: NextRequest, ctx: { params: { path?: string[] } }) {
  const rawPath = '/' + (ctx.params.path ?? []).join('/');
  const target = new URL(joinURL(BACKEND, rawPath) + (req.nextUrl.search || ''));

  const access = req.cookies.get('access')?.value;
  const headers = new Headers(req.headers);
  headers.set('host', target.host);
  headers.set('origin', BACKEND);
  headers.set('referer', BACKEND + '/');
  headers.set('accept', 'application/json');
  if (!headers.get('content-type')) headers.set('content-type', 'application/json');
  headers.set('authorization', access ? `Bearer ${access}` : '');

  const init: RequestInit = {
    method: req.method,
    headers,
    body: req.method === 'GET' || req.method === 'HEAD' ? undefined : await req.text(),
    redirect: 'manual',
  };

  const res = await fetch(target.toString(), init);
  const text = await res.text();

  return new NextResponse(text, {
    status: res.status,
    headers: { 'content-type': res.headers.get('content-type') || 'application/json' },
  });
}

export const GET = ALL; export const POST = ALL; export const PUT = ALL;
export const PATCH = ALL; export const DELETE = ALL; export const OPTIONS = ALL;
