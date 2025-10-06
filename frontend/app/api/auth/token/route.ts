import { NextResponse } from 'next/server';

const BACKEND_INTERNAL =
  (process.env.BACKEND_INTERNAL || 'http://127.0.0.1:8080').replace(/\/$/, '');

export async function POST(req: Request) {
  const body = await req.text();
  const url = `${BACKEND_INTERNAL}/api/token/`; // keep trailing slash

  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
      body,
      redirect: 'manual', // don't follow 30x automatically
    });

    const text = await res.text();
    return new NextResponse(text, {
      status: res.status,
      headers: { 'Content-Type': res.headers.get('Content-Type') || 'application/json' },
    });
  } catch {
    return NextResponse.json({ detail: 'Proxy error contacting backend /api/token/' }, { status: 502 });
  }
}
