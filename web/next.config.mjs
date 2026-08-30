// Implements: architecture/reference/ux/hybrid-ui-acceptance-contract.md §UX-PWA-02
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

import withPWAInit from '@ducanh2912/next-pwa';

const withPWA = withPWAInit({
  dest: 'public',
  disable: process.env.NODE_ENV === 'development',
  register: true,
  cacheStartUrl: false,
  dynamicStartUrl: false,
  cacheOnFrontEndNav: false,
  workboxOptions: {
    exclude: [/static\/chunks\/app\/(?:\(auth\)|\(authenticated\)|\(founder\)|api)\//],
    runtimeCaching: [
      {
        urlPattern: ({ request }) => request.mode === 'navigate',
        handler: 'NetworkOnly',
      },
      {
        urlPattern: /\/api\//,
        handler: 'NetworkOnly',
      },
      {
        urlPattern: /\/_next\/static\/|\/waooaw-platform-logo\.png$|\/icon(?:\?.*)?$/,
        handler: 'CacheFirst',
        options: {
          cacheName: 'waooaw-static-shell-v1',
          expiration: { maxEntries: 80, maxAgeSeconds: 60 * 60 * 24 * 30 },
        },
      },
      {
        urlPattern: /.*/,
        handler: 'NetworkOnly',
      },
    ],
  },
});

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: process.env.BUILD_STANDALONE === 'true' ? 'standalone' : undefined,
  poweredByHeader: false,
  reactStrictMode: true,
  async headers() {
    return [{ source: '/:path*', headers: [
      { key: 'X-Frame-Options', value: 'DENY' },
      { key: 'X-Content-Type-Options', value: 'nosniff' },
      { key: 'Strict-Transport-Security', value: 'max-age=31536000; includeSubDomains' },
      { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
      { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=(), payment=()' },
    ] }];
  },
};

export default withPWA(nextConfig);