import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  use: {
    baseURL: process.env.BASE_URL ?? 'http://127.0.0.1:3000',
    trace: 'retain-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    {
      name: 'mobile-360',
      use: { ...devices['Pixel 7'], viewport: { width: 360, height: 800 } },
    },
  ],
  webServer: process.env.BASE_URL
    ? undefined
    : {
        command:
          'NEXTAUTH_SECRET=playwright-only-not-a-runtime-secret NEXTAUTH_URL=http://127.0.0.1:3000 pnpm build && HOSTNAME=127.0.0.1 PORT=3000 NEXTAUTH_SECRET=playwright-only-not-a-runtime-secret NEXTAUTH_URL=http://127.0.0.1:3000 node .next/standalone/server.js',
        url: 'http://127.0.0.1:3000',
        reuseExistingServer: true,
        timeout: 180_000,
      },
});