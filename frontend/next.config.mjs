import createNextIntlPlugin from 'next-intl/plugin';

const withNextIntl = createNextIntlPlugin('./i18n.ts'); // it's recommended to hoist this to the top of the file

/** @type {import('next').NextConfig} */
const nextConfig = {
    output: 'standalone',
};

export default withNextIntl(nextConfig);