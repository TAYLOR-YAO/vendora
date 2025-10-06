import { NextRequest, NextResponse } from 'next/server';
import { jwtDecode } from 'jwt-decode';

type JWTPayload = {
  user_id: string;
  full_name?: string;
  exp: number; // seconds
  iat: number;
  [k: string]: any;
};

export async function GET(req: NextRequest) {
  const access = req.cookies.get('access')?.value;
  if (!access) {
    return NextResponse.json({ authenticated: false }, { status: 401 });
  }

  try {
    // decode without verifying (we only need display info; backend enforces auth)
    const p = jwtDecode<JWTPayload>(access);
    const nowMs = Date.now();
    const expMs = (p.exp ?? 0) * 1000;

    return NextResponse.json({
      authenticated: true,
      user: { user_id: p.user_id, full_name: p.full_name ?? '' },
      // handy client hints
      exp: expMs,
      now: nowMs,
      ttlMs: Math.max(0, expMs - nowMs),
    });
  } catch {
    return NextResponse.json({ authenticated: false }, { status: 401 });
  }
}
