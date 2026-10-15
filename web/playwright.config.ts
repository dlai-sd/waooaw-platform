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
          'IDENTITY_PROVIDER_DELAY_MS=2500 node tests/e2e/fixtures/f1-services.mjs & fixture_pid=$!; trap \'kill "$fixture_pid"\' EXIT; rm -rf .next && BUSINESS_PLATFORM_URL=http://127.0.0.1:5001 IDENTITY_EVENT_SIGNING_KEY=playwright-only-identity-event-signing-key KEYCLOAK_ISSUER=https://identity.example/realms/waooaw NEXTAUTH_SECRET=playwright-only-not-a-runtime-secret NEXTAUTH_URL=http://127.0.0.1:3000 PROFESSIONAL_RUNTIME_URL=http://127.0.0.1:5001 WAOOAW_SERVER_SESSION_MODE=disabled npm run build && BUSINESS_PLATFORM_URL=http://127.0.0.1:5001 IDENTITY_EVENT_SIGNING_KEY=playwright-only-identity-event-signing-key KEYCLOAK_ISSUER=https://identity.example/realms/waooaw NEXTAUTH_SECRET=playwright-only-not-a-runtime-secret NEXTAUTH_URL=http://127.0.0.1:3000 PROFESSIONAL_RUNTIME_URL=http://127.0.0.1:5001 WAOOAW_SERVER_SESSION_MODE=disabled npm run start -- --hostname 127.0.0.1 --port 3000',
        url: 'http://127.0.0.1:3000',
        reuseExistingServer: true,
        timeout: 180_000,
      },
});
