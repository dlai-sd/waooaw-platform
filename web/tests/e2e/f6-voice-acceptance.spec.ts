// Implements: UX-VOICE-01 through UX-VOICE-12
// Constitutional basis: C-001, C-023, C-042, C-059, C-063, C-071

import AxeBuilder from '@axe-core/playwright';
import { expect, test, type BrowserContext, type Page } from '@playwright/test';
import { encode } from 'next-auth/jwt';

const secret = 'playwright-only-not-a-runtime-secret';

async function addSession(context: BrowserContext, projectName: string) {
  const value = await encode({ secret, maxAge: 3600, token: { accessToken: `fixture-access-token-${projectName}`, founder: false, sub: `fixture-user-${projectName}` } });
  await context.addCookies([{ name: 'next-auth.session-token', value, domain: '127.0.0.1', httpOnly: true, path: '/', sameSite: 'Lax' }]);
}

async function installCaptureMock(page: Page) {
  await page.addInitScript(() => {
    class CaptureRecorder {
      static isTypeSupported() { return true; }
      state: RecordingState = 'inactive';
      mimeType = 'audio/webm';
      ondataavailable: ((event: { data: Blob }) => void) | null = null;
      onstop: (() => void) | null = null;
      start() { this.state = 'recording'; }
      pause() { this.state = 'paused'; }
      resume() { this.state = 'recording'; }
      stop() {
        this.state = 'inactive';
        this.ondataavailable?.({ data: new Blob(['governed voice'], { type: this.mimeType }) });
        this.onstop?.();
      }
    }
    Object.defineProperty(window, 'MediaRecorder', { configurable: true, value: CaptureRecorder });
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: { getUserMedia: async () => ({ getTracks: () => [{ stop() {} }] }) },
    });
  });
}

async function openVoice(page: Page, relationshipId = 'relationship-voice') {
  await page.goto(`/relationships/${relationshipId}`);
  await expect(page.getByRole('heading', { name: 'Record a message' })).toBeVisible();
}

async function captureAndReview(page: Page) {
  await page.getByLabel('I agree to record and transcribe this draft.').check();
  await page.getByRole('button', { name: 'Record' }).click();
  await expect(page.getByRole('button', { name: 'Pause' })).toBeVisible();
  await page.getByRole('button', { name: 'Pause' }).click();
  await expect(page.getByRole('button', { name: 'Resume' })).toBeVisible();
  await page.getByRole('button', { name: 'Resume' }).click();
  await page.getByRole('button', { name: 'Stop', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Upload for transcript' })).toBeVisible();
  await page.getByRole('button', { name: 'Upload for transcript' }).click();
  await expect(page.getByLabel('Review transcript')).toHaveValue('Please review this governed voice draft.');
}

test.beforeEach(async ({ context, page }, testInfo) => {
  await context.clearCookies();
  await addSession(context, testInfo.project.name);
  await installCaptureMock(page);
});

test('UX-VOICE-02 UX-VOICE-03 UX-VOICE-04 UX-VOICE-10: capture, review, correction, and explicit send work across browser engines', async ({ page }) => {
  const requests: string[] = [];
  page.on('request', (request) => { if (request.url().includes('/api/voice/')) requests.push(request.url()); });
  await openVoice(page);
  await captureAndReview(page);

  const send = page.getByRole('button', { name: 'Send voice contribution' });
  await expect(send).toBeDisabled();
  await page.getByLabel('Review transcript').fill('Corrected governed voice draft.');
  await page.getByRole('button', { name: 'Confirm correction' }).click();
  await expect(send).toBeEnabled();
  await expect(page.getByRole('button', { name: 'Recorded' })).toHaveCount(0);
  await send.click();
  await expect(page.getByRole('button', { name: 'Recorded' })).toBeDisabled();
  expect(requests.length).toBeGreaterThanOrEqual(5);
  expect(requests.every((url) => new URL(url).origin === 'http://127.0.0.1:3000')).toBe(true);
  expect(requests.every((url) => !/professional-runtime|ai-runtime|provider|storage/i.test(url))).toBe(true);
});

test('UX-VOICE-09 UX-VOICE-10: exact viewport composition is accessible and unobscured', async ({ page }, testInfo) => {
  test.skip(!['chromium-expanded', 'chromium-compact-360', 'chromium-intermediate'].includes(testInfo.project.name), 'Exact viewport matrix runs in Chromium.');
  await openVoice(page);
  const voice = page.locator('.voice-contribution');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
  const geometry = await voice.evaluate((element) => {
    const bounds = element.getBoundingClientRect();
    return { left: bounds.left, right: bounds.right, width: bounds.width, viewport: innerWidth };
  });
  expect(geometry.left).toBeGreaterThanOrEqual(0);
  expect(geometry.right).toBeLessThanOrEqual(geometry.viewport);
  expect(geometry.width).toBeGreaterThan(0);
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations.filter(({ impact }) => impact === 'critical' || impact === 'serious')).toEqual([]);
  await page.getByRole('button', { name: 'Use text instead' }).focus();
  await page.keyboard.press('Enter');
  await expect(page.getByLabel('Message your professional')).toBeFocused();
});

test('UX-VOICE-06 UX-VOICE-12: offline draft and Emergency Stop fail closed with text fallback', async ({ context, page }) => {
  await openVoice(page, 'relationship-voice-resilience');
  await page.getByLabel('I agree to record and transcribe this draft.').check();
  await page.getByRole('button', { name: 'Record' }).click();
  await page.getByRole('button', { name: 'Stop', exact: true }).click();
  await context.setOffline(true);
  await page.getByRole('button', { name: 'Upload for transcript' }).click();
  await expect(page.locator('.voice-contribution').getByRole('alert')).toContainText('offline');
  await expect(page.getByRole('button', { name: 'Reconcile or retry' })).toBeVisible();
  await context.setOffline(false);
  await page.getByLabel('Message your professional').fill('Preserve this text fallback.');
  await page.getByRole('button', { name: 'Emergency Stop' }).click();
  await expect(page.getByText(/Emergency Stop is active. Voice commands are disabled/)).toBeVisible();
  await expect(page.getByLabel('Message your professional')).toHaveValue('Preserve this text fallback.');
  await expect(page.getByLabel('Message your professional')).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Send', exact: true })).toBeDisabled();
});

test('UX-VOICE-11: RTL, reduced motion, and 200 percent zoom preserve operation', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'chromium-expanded', 'Presentation variants run once in Chromium.');
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.setViewportSize({ width: 720, height: 450 });
  await openVoice(page, 'relationship-voice-presentation');
  await page.evaluate(() => { document.documentElement.dir = 'rtl'; });
  await expect(page.getByRole('button', { name: 'Record' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Emergency Stop' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
  await page.getByRole('button', { name: 'Use text instead' }).click();
  await expect(page.getByLabel('Message your professional')).toBeFocused();
});