import AxeBuilder from '@axe-core/playwright';
import { expect, test, type BrowserContext, type Page } from '@playwright/test';
import { encode } from 'next-auth/jwt';
import { messages } from '../../lib/i18n';
import { supportedLocales, type SupportedLocale } from '../../lib/preferences';

const secret = 'playwright-only-not-a-runtime-secret';
const f1Routes = ['/', '/professionals', '/blogs', '/login', '/register', '/verify', '/auth/error', '/403', '/offline', '/missing-f1-route'];

async function addSession(context: BrowserContext, founder: boolean) {
  const value = await encode({ secret, maxAge: 60 * 60, token: { accessToken: 'fixture-access-token', founder, sub: 'fixture-user' } });
  await context.addCookies([{ name: 'next-auth.session-token', value, domain: '127.0.0.1', httpOnly: true, path: '/', sameSite: 'Lax' }]);
}

async function hasHorizontalOverflow(page: Page) {
  return page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
}

async function horizontalOverflowDetails(page: Page) {
  return page.evaluate(() => {
    const viewportWidth = document.documentElement.clientWidth;
    const elements = [...document.querySelectorAll<HTMLElement>('body *')]
      .filter((element) => {
        const bounds = element.getBoundingClientRect();
        return bounds.left < 0 || bounds.right > viewportWidth;
      })
      .slice(0, 8)
      .map((element) => `${element.tagName.toLowerCase()}.${element.className || '(no-class)'}`);
    const intrinsicallyWide = [...document.querySelectorAll<HTMLElement>('body *')]
      .filter((element) => element.scrollWidth > element.clientWidth)
      .slice(0, 8)
      .map((element) => `${element.tagName.toLowerCase()}.${element.className || '(no-class)'}=${element.scrollWidth}/${element.clientWidth}`);
    return [
      `root=${document.documentElement.scrollWidth}/${document.documentElement.clientWidth}`,
      `body=${document.body.scrollWidth}/${document.body.clientWidth}`,
      ...elements,
      ...intrinsicallyWide,
    ];
  });
}

test.beforeEach(async ({ context }) => {
  await context.clearCookies();
  await context.addCookies([
    { name: 'waooaw-locale', value: 'en', domain: '127.0.0.1', path: '/' },
    { name: 'waooaw-theme', value: 'light', domain: '127.0.0.1', path: '/' },
  ]);
});

test('UX-SHELL-01 UX-PWA-01: public navigation is private and installable', async ({ page }) => {
  const protectedRequests: string[] = [];
  page.on('request', (request) => {
    if (/\/api\/(relationships|employment|evidence|billing)/.test(request.url())) protectedRequests.push(request.url());
  });
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1, name: 'WAOOAW' })).toBeVisible();
  await expect(page.getByRole('heading', { name: messages.en.gettingStarted })).toBeVisible();
  await expect(page.getByRole('heading', { name: messages.en.expertProfessionals })).toBeVisible();
  await expect(page.getByRole('heading', { name: messages.en.constitutionalPromise })).toBeVisible();
  await expect(page.locator('link[rel="manifest"]')).toHaveAttribute('href', '/manifest.webmanifest');
  const manifest = await page.request.get('/manifest.webmanifest');
  expect(manifest.ok()).toBe(true);
  expect(await manifest.json()).toMatchObject({ display: 'standalone', name: 'WAOOAW', scope: '/', short_name: 'WAOOAW' });
  expect(protectedRequests).toEqual([]);
});

test('UX-RESP-01 UX-SHELL-05: every F1 route is stable at 360x800', async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 800 });
  for (const path of f1Routes) {
    await page.goto(path);
    await expect(page.getByRole('heading', { level: 1 }).first()).toBeVisible();
    expect(await hasHorizontalOverflow(page), `${path} must not overflow at 360px`).toBe(false);
  }
});

test('CCT-UX-I18N-01 CCT-UX-RTL-01 CCT-UX-RTL-02 UX-RESP-06: all scripts translate and reflow at 200% zoom', async ({ context, page }) => {
  await page.setViewportSize({ width: 720, height: 900 });
  for (const locale of supportedLocales) {
    await context.addCookies([{ name: 'waooaw-locale', value: locale, domain: '127.0.0.1', path: '/' }]);
    await page.goto('/');
    await expect(page.locator('html')).toHaveAttribute('lang', locale);
    await expect(page.locator('html')).toHaveAttribute('dir', locale === 'ur' ? 'rtl' : 'ltr');
    await expect(page.getByRole('link', { name: new RegExp(messages[locale].browseProfessionals) }).first()).toBeVisible();
    const family = await page.locator('body').evaluate((element) => getComputedStyle(element).fontFamily);
    const expectedFamily: Record<SupportedLocale, RegExp> = {
      en: /Noto_Sans/i, hi: /Devanagari/i, mr: /Devanagari/i, ta: /Tamil/i, te: /Telugu/i,
      kn: /Kannada/i, gu: /Gujarati/i, bn: /Bengali/i, ml: /Malayalam/i, pa: /Gurmukhi/i, ur: /Nastaliq/i,
    };
    expect(family).toMatch(expectedFamily[locale]);
    await page.evaluate(() => { document.documentElement.style.fontSize = '200%'; });
    const overflow = await hasHorizontalOverflow(page);
    const offenders = overflow ? await horizontalOverflowDetails(page) : [];
    expect(overflow, `${locale} must reflow at 200% zoom; offenders: ${offenders.join(', ')}`).toBe(false);
  }
});

test('CCT-UX-A11Y-01 CCT-UX-A11Y-03 CCT-UX-MOTION-01: keyboard, focus, motion, and axe pass', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  for (const path of ['/', '/login', '/register', '/403', '/offline']) {
    await page.goto(path);
    const skipLink = page.getByRole('link', { name: messages.en.skipToContent });
    if (await skipLink.count()) {
      await page.keyboard.press('Tab');
      await expect(skipLink).toBeFocused();
      await skipLink.press('Enter');
      await expect(page.locator('#main-content')).toBeFocused();
    }
    const results = await new AxeBuilder({ page }).analyze();
    const blocking = results.violations.filter((violation) => violation.impact === 'critical' || violation.impact === 'serious');
    expect(blocking, `${path} has unreviewed serious or critical axe findings`).toEqual([]);
  }
});

test('UX-SHELL-03 CCT-UX-HO-01: signed customer and Founder boundaries compose on the server', async ({ context, page }) => {
  await addSession(context, false);
  await page.goto('/home');
  await expect(page).toHaveURL(/\/home$/);
  const stop = page.getByRole('button', { name: 'No active work to stop' });
  await expect(stop).toBeVisible();
  const box = await stop.boundingBox();
  expect(box?.height).toBeGreaterThanOrEqual(56);
  await expect(stop).toBeDisabled();

  await page.goto('/founder');
  await expect(page).toHaveURL(/\/403$/);
  await expect(page.getByRole('navigation', { name: 'Founder navigation' })).toHaveCount(0);
  await expect(page.getByText('Founder administration')).toHaveCount(0);

  await context.clearCookies();
  await addSession(context, true);
  await page.goto('/founder');
  await expect(page).toHaveURL(/\/founder$/);
  await expect(page.getByRole('navigation', { name: 'Founder navigation' })).toBeVisible();
});

test('UX-PWA-02 UX-PRIV-01: generated worker caches static assets only', async ({ page }) => {
  const response = await page.request.get('/sw.js');
  expect(response.ok()).toBe(true);
  const worker = await response.text();
  expect(worker).toContain('waooaw-static-shell-v1');
  expect(worker).toContain('NetworkOnly');
  expect(worker).not.toMatch(/(?:apis|pages|rsc|cross-origin)-/i);
  expect(worker).not.toMatch(/relationship payload|accessToken|tenantId|evidence payload/i);
});

test('UX-VIS-01: F1-owned public and system states match reviewed baselines', async ({ context, page }, testInfo) => {
  const compact = testInfo.project.name.includes('compact');
  const locale: SupportedLocale = compact ? 'ur' : 'en';
  await context.addCookies([
    { name: 'waooaw-locale', value: locale, domain: '127.0.0.1', path: '/' },
    { name: 'waooaw-theme', value: compact ? 'dark' : 'light', domain: '127.0.0.1', path: '/' },
  ]);
  for (const [name, path] of [['home', '/'], ['login', '/login'], ['forbidden', '/403'], ['offline', '/offline']] as const) {
    await page.goto(path);
    await expect(page).toHaveScreenshot(`${name}-${locale}.png`, { animations: 'disabled', fullPage: true, maxDiffPixelRatio: 0.01 });
  }
});

test('UX-PERF-01 UX-PERF-02 UX-PERF-03: public shell remains within F1 budgets', async ({ page, request }, testInfo) => {
  test.skip(testInfo.project.name !== 'chromium-expanded', 'Performance entries use the approved expanded Chromium profile.');
  const publicResponse = await request.get('/');
  const initialHtml = await publicResponse.text();
  await page.goto('/');
  const metrics = await page.evaluate((html) => {
    const resources = performance.getEntriesByType('resource') as PerformanceResourceTiming[];
    const initialDocument = new DOMParser().parseFromString(html, 'text/html');
    const initialScriptUrls = new Set([...initialDocument.scripts]
      .map((script) => script.getAttribute('src'))
      .filter((source): source is string => Boolean(source))
      .map((source) => new URL(source, window.location.origin).href));
    const scripts = resources.filter((entry) => initialScriptUrls.has(entry.name));
    const initialAssetUrls = new Set([
      ...initialScriptUrls,
      ...[...document.querySelectorAll<HTMLLinkElement>('link[rel="stylesheet"]')].map((link) => link.href),
      ...[...document.images].map((image) => image.currentSrc || image.src),
    ]);
    const initialResources = resources.filter((entry) => initialAssetUrls.has(entry.name) || entry.initiatorType === 'font');
    const documentBytes = (performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming)?.encodedBodySize ?? 0;
    const stylesAndFonts = resources.filter((entry) => entry.initiatorType === 'css' || entry.initiatorType === 'font');
    const fcp = performance.getEntriesByName('first-contentful-paint')[0]?.startTime ?? 0;
    return {
      fcp,
      initialJsBytes: scripts.reduce((total, entry) => total + entry.encodedBodySize, 0),
      scripts: scripts.map((entry) => ({ url: entry.name, bytes: entry.encodedBodySize, responseEnd: entry.responseEnd })),
      publicBytes: documentBytes + initialResources.reduce((total, entry) => total + entry.encodedBodySize, 0),
      loadedFonts: stylesAndFonts.filter((entry) => entry.initiatorType === 'font').length,
    };
  }, initialHtml);
  expect(metrics.fcp).toBeLessThanOrEqual(1500);
  expect(metrics.initialJsBytes, JSON.stringify(metrics.scripts)).toBeLessThanOrEqual(100 * 1024);
  expect(metrics.publicBytes).toBeLessThanOrEqual(200 * 1024);
  expect(metrics.loadedFonts).toBeLessThanOrEqual(1);
});