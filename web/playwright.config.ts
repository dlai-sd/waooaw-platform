import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  use: {
    baseURL: process.env.BASE_URL ?? 'http://127.0.0.1:3000',
    trace: 'retain-on-failure',
  },
  projects: [
    { name: 'chromium-expanded', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } } },
    { name: 'firefox-expanded', use: { ...devices['Desktop Firefox'], viewport: { width: 1440, height: 900 } } },
    { name: 'webkit-expanded', use: { ...devices['Desktop Safari'], viewport: { width: 1440, height: 900 } } },
    {
      name: 'chromium-compact-360',
      use: { ...devices['Pixel 7'], viewport: { width: 360, height: 800 } },
    },
    { name: 'chromium-intermediate', use: { ...devices['Desktop Chrome'], viewport: { width: 768, height: 1024 } } },
  ],
  webServer: process.env.BASE_URL
    ? undefined
    : {
        command:
          'node tests/e2e/fixtures/f1-services.mjs & fixture_pid=$!; trap \'kill "$fixture_pid"\' EXIT; rm -rf .next && BUSINESS_PLATFORM_URL=http://127.0.0.1:5001 NEXTAUTH_SECRET=playwright-only-not-a-runtime-secret NEXTAUTH_URL=http://127.0.0.1:3000 PROFESSIONAL_RUNTIME_URL=http://127.0.0.1:5001 npm run build && BUSINESS_PLATFORM_URL=http://127.0.0.1:5001 NEXTAUTH_SECRET=playwright-only-not-a-runtime-secret NEXTAUTH_URL=http://127.0.0.1:3000 PROFESSIONAL_RUNTIME_URL=http://127.0.0.1:5001 npm run start -- --hostname 127.0.0.1 --port 3000',
        url: 'http://127.0.0.1:3000',
        reuseExistingServer: true,
        timeout: 180_000,
      },
});