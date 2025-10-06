// frontend/middleware.ts
import {NextRequest, NextResponse} from 'next/server';
import createMiddleware from 'next-intl/middleware';

const intl = createMiddleware({
  locales: ['en', 'fr', 'de'],
  defaultLocale: 'en'
});

export default function middleware(req: NextRequest) {
  const {pathname, search} = req.nextUrl;

  // Rewrite /api/b requests to append slash (no 30x)
  if (pathname.startsWith('/api/b') && !pathname.endsWith('/')) {
    const url = req.nextUrl.clone();
    url.pathname = pathname + '/';
    url.search = search;
    return NextResponse.rewrite(url);
  }

  return intl(req);
}

export const config = {
  matcher: [
    '/((?!api|_next|.*\\..*).*)', // pages for next-intl
    '/api/b/:path*'               // our proxy base
  ]
};
