// next.config.js
const API_BASE = (process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000').replace(/\/$/, '');

const nextConfig = {
  i18n: { locales: ['en', 'fr', 'de'], defaultLocale: 'en' },
  trailingSlash: false,
  async rewrites() {
    return [
      // Proxy everything under /api/b to your backend
      { source: '/api/b/:path*', destination: `${API_BASE}/:path*` },
    ];
  },
};

module.exports = nextConfig;
