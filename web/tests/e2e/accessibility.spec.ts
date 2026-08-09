import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

test('public shell is private, installable, responsive, and accessible', async ({ page }) => {
  const protectedRequests: string[] = [];
  page.on('request', (request) => {
    if (/\/api\/(relationships|employment|evidence|billing)/.test(request.url())) protectedRequests.push(request.url());
  });
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1, name: 'WAOOAW' })).toBeVisible();
  await expect(page.getByRole('link', { name: /Browse professionals/i })).toBeVisible();
  await expect(page.locator('link[rel="manifest"]')).toHaveAttribute('href', '/manifest.webmanifest');

  const manifest = await page.request.get('/manifest.webmanifest');
  expect(manifest.ok()).toBe(true);
  expect(await manifest.json()).toMatchObject({ display: 'standalone', short_name: 'WAOOAW' });
  const horizontalOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth
  );
  expect(horizontalOverflow).toBe(false);
  expect(protectedRequests).toEqual([]);

  const results = await new AxeBuilder({ page }).analyze();
  const critical = results.violations.filter((violation) => violation.impact === 'critical');
  expect(critical).toEqual([]);
});

test('authentication and shared system states remain stable', async ({ page }) => {
  for (const path of ['/login', '/register', '/403', '/offline', '/missing-f1-route']) {
    await page.goto(path);
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
    expect(overflow, `${path} must not overflow`).toBe(false);
  }
});

test('Urdu direction, dark theme, focus, and reduced motion bootstrap before interaction', async ({ context, page }) => {
  await context.addCookies([
    { name: 'waooaw-locale', value: 'ur', domain: '127.0.0.1', path: '/' },
    { name: 'waooaw-theme', value: 'dark', domain: '127.0.0.1', path: '/' },
  ]);
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/login');
  await expect(page.locator('html')).toHaveAttribute('lang', 'ur');
  await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await page.keyboard.press('Tab');
  await expect(page.getByRole('link', { name: 'Skip to main content' })).toBeFocused();
});