// Implements: architecture/reference/ux/wc-078-visual-experience-implementation-plan.md §11.1 (WC-08 executes the WC-07 declaration)
// Constitutional basis: C-023 (Evidence First), C-059 (Implementation Traceability)
//
// WC-08 scope: this spec deterministically GENERATES the 54 Section 11.1 screenshot captures plus
// the G9 collision assertion and writes a machine-readable artifact index. It does not perform or
// substitute for the named Founder/human substantive review; every case is written with verdict
// "PENDING_SUBSTANTIVE_REVIEW" and VRA-15 remains unbound until WC-09.
//
// Runs on a single deterministic Chromium project only — the manifest already fixes an explicit
// viewport per case, so replaying it across every configured browser project would duplicate work
// and overwrite the same file 5x rather than adding coverage. The full cross-browser matrix remains
// the responsibility of wc078-public-acquisition.spec.ts.

import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import type { Page } from '@playwright/test';
import { expect, test } from '@playwright/test';
import { marketingConfig } from '../../config/marketing';
import { consentCookieName } from '../../lib/consent';
import type { ScreenshotCase, ScreenshotConsent } from './wc078-screenshot-manifest';
import { wc078CollisionCaseId, wc078ScreenshotManifest } from './wc078-screenshot-manifest';

const baseURL = process.env.BASE_URL ?? 'http://127.0.0.1:3000';
const repoRoot = path.resolve(__dirname, '..', '..', '..');
const evidenceDir = process.env.WC078_EVIDENCE_DIR ? path.resolve(process.env.WC078_EVIDENCE_DIR) : path.join(repoRoot, 'test-results', 'wc078');
const screenshotDir = path.join(evidenceDir, 'screenshots');

// Test-only fixture text. The real announcement is configuration-disabled in production
// (web/config/site.ts `announcement.enabled: false`); this label is rendered so no reviewer can
// mistake it for real production content, and it renders no source/config change.
const fixtureAnnouncementMessage = 'Illustrative announcement — WC-08 screenshot fixture (production announcement is configuration-disabled)';

type CaseRecord = Readonly<{
  id: string;
  group: string;
  axes: Readonly<{
    viewport: string;
    zoom: string;
    locale: string;
    theme: string;
    motion: string;
    announcement: string;
    consent: string;
    professional?: string;
    stage?: string;
  }>;
  screenshot_path: string;
  sha256: string;
  captured_at: string;
  notes: readonly string[];
}>;

type G9Record = Readonly<{ case_id: string; assertion: string; overlap_detected: boolean; result: 'PASS' | 'FAIL' }>;

const collectedCases: CaseRecord[] = [];
let collectedG9: G9Record | null = null;

function resolveHeadSha(): string {
  if (/^[0-9a-f]{40}$/.test(process.env.WC078_REVIEWED_HEAD ?? '')) return process.env.WC078_REVIEWED_HEAD as string;
  try {
    return execFileSync('git', ['rev-parse', 'HEAD'], { cwd: repoRoot, encoding: 'utf8' }).trim();
  } catch {
    return 'PENDING_HEAD_BINDING';
  }
}

async function injectAnnouncementFixture(page: Page): Promise<void> {
  await page.evaluate((message) => {
    const bar = document.createElement('div');
    bar.className = 'announcement-bar';
    bar.setAttribute('role', 'region');
    bar.setAttribute('aria-label', 'Announcement');
    bar.setAttribute('data-wc078-fixture', 'announcement');
    const paragraph = document.createElement('p');
    paragraph.textContent = message;
    const dismiss = document.createElement('button');
    dismiss.type = 'button';
    dismiss.className = 'announcement-dismiss';
    dismiss.setAttribute('aria-label', 'Dismiss announcement');
    dismiss.textContent = '\u00d7';
    bar.append(paragraph, dismiss);
    document.body.insertBefore(bar, document.body.firstChild);
    document.documentElement.style.setProperty('--announcement-offset', `${bar.getBoundingClientRect().height}px`);
  }, fixtureAnnouncementMessage);
}

async function applyConsentCookie(page: Page, consent: ScreenshotConsent): Promise<void> {
  if (consent === 'banner') return; // no cookie: the real first-visit banner renders unprompted
  const value = JSON.stringify({ policyVersion: marketingConfig.policyVersion, necessary: true, analytics: false, advertising: false, updatedAt: new Date().toISOString() });
  await page.context().addCookies([{ name: consentCookieName, value: encodeURIComponent(value), url: baseURL }]);
}

async function reopenConsentPreferences(page: Page): Promise<void> {
  await page.getByRole('button', { name: 'Cookie preferences' }).click();
  await expect(page.locator('aside.consent-banner')).toBeVisible();
}

async function establishJourneyState(page: Page, kase: ScreenshotCase): Promise<void> {
  const showcase = page.locator('.journey-showcase');
  await showcase.waitFor({ state: 'visible' });
  await showcase.evaluate((element) => element.scrollIntoView({ block: 'center', inline: 'nearest' }));
  if (kase.professional && kase.stage) {
    const professional = kase.professional;
    const stage = kase.stage;
    // The showcase autoplays every professional/stage combination once, in a fixed 800ms schedule,
    // before settling. Waiting for the exact real DOM state (not a sleep) and then re-selecting the
    // already-active professional freezes it there via the same click handler a user would use.
    await page.waitForFunction(
      ({ professional: expectedProfessional, stage: expectedStage }) => {
        const node = document.querySelector('.journey-showcase');
        return node?.getAttribute('data-story-id') === expectedProfessional && node?.getAttribute('data-stage-id') === expectedStage;
      },
      { professional, stage },
      { timeout: 15_000 },
    );
    const label = professional === 'agricultural-advisor' ? 'Agricultural Advisor' : 'Digital Marketing Professional';
    await page.getByRole('button', { name: new RegExp(label) }).click();
    await expect(showcase).toHaveAttribute('data-story-id', professional);
    await expect(showcase).toHaveAttribute('data-stage-id', stage);
  } else {
    await expect(page.locator('.journey-settled')).toBeVisible({ timeout: 15_000 });
  }
}

function overlaps(a: { top: number; right: number; bottom: number; left: number }, b: typeof a): boolean {
  return a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top;
}

async function assertNoFixedControlOverlap(page: Page): Promise<boolean> {
  const rects = await page.evaluate(() => {
    function rectOf(selector: string) {
      const element = document.querySelector(selector);
      if (!element) return null;
      const rect = element.getBoundingClientRect();
      return { top: rect.top, right: rect.right, bottom: rect.bottom, left: rect.left };
    }
    return { announcement: rectOf('.announcement-bar'), consent: rectOf('aside.consent-banner') };
  });
  if (!rects.announcement || !rects.consent) return false;
  return overlaps(rects.announcement, rects.consent);
}

test.beforeAll(async () => {
  await mkdir(screenshotDir, { recursive: true });
});

for (const kase of wc078ScreenshotManifest) {
  test(kase.id, async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== 'chromium-expanded', 'WC-08 screenshot manifest captures run once on a single deterministic Chromium project');

    await page.context().clearCookies();
    await page.context().addCookies([
      { name: 'waooaw-locale', value: kase.locale, url: baseURL },
      { name: 'waooaw-theme', value: kase.theme === 'system' ? 'system' : kase.theme, url: baseURL },
    ]);
    await applyConsentCookie(page, kase.consent);
    await page.emulateMedia({
      reducedMotion: kase.motion === 'reduced' ? 'reduce' : 'no-preference',
      colorScheme: kase.theme === 'light' ? 'light' : 'dark',
    });
    await page.setViewportSize(kase.viewport);
    await page.goto('/');

    const notes: string[] = [];
    if (kase.announcement === 'visible') {
      await injectAnnouncementFixture(page);
      notes.push('announcement rendered via approved test-only fixture; production announcement remains configuration-disabled (web/config/site.ts)');
    }
    if (kase.consent === 'preferences-open') {
      await reopenConsentPreferences(page);
    }
    if (kase.zoom === '200%') {
      await page.evaluate(() => { document.documentElement.style.fontSize = '200%'; });
      notes.push('200% zoom reproduced via root font-size scaling, the existing reflow-test technique in wc078-public-acquisition.spec.ts');
    }

    await establishJourneyState(page, kase);
    await page.evaluate(() => document.fonts.ready);
    await page.waitForLoadState('networkidle');
    await page.evaluate(() => window.scrollTo({ top: 0, left: 0, behavior: 'instant' }));

    const fileName = `${kase.id}.png`;
    const filePath = path.join(screenshotDir, fileName);
    const buffer = await page.screenshot({ path: filePath, fullPage: true, animations: 'disabled' });
    const sha256 = createHash('sha256').update(buffer).digest('hex');

    if (kase.id === wc078CollisionCaseId) {
      const overlapDetected = await assertNoFixedControlOverlap(page);
      collectedG9 = { case_id: kase.id, assertion: 'fixed-control-geometric-overlap', overlap_detected: overlapDetected, result: overlapDetected ? 'FAIL' : 'PASS' };
      expect(overlapDetected, 'G9: announcement and consent fixed controls must not geometrically overlap at 360px').toBe(false);
    }

    collectedCases.push({
      id: kase.id,
      group: kase.group,
      axes: {
        viewport: `${kase.viewport.width}x${kase.viewport.height}`,
        zoom: kase.zoom,
        locale: kase.locale,
        theme: kase.theme,
        motion: kase.motion,
        announcement: kase.announcement,
        consent: kase.consent,
        ...(kase.professional ? { professional: kase.professional } : {}),
        ...(kase.stage ? { stage: kase.stage } : {}),
      },
      screenshot_path: `screenshots/${fileName}`,
      sha256,
      captured_at: new Date().toISOString(),
      notes,
    });
  });
}

test.afterAll(async () => {
  if (collectedCases.length === 0) return;
  const index = {
    schema_version: '1.0',
    work_contract: 'WC-078',
    generated_at: new Date().toISOString(),
    reviewed_head: resolveHeadSha(),
    manifest_total: wc078ScreenshotManifest.length,
    cases_generated: collectedCases.length,
    verdict: 'PENDING_SUBSTANTIVE_REVIEW',
    contact_sheet: null,
    cases: collectedCases,
    g9: collectedG9,
  };
  await writeFile(path.join(screenshotDir, 'index.json'), `${JSON.stringify(index, null, 2)}\n`, 'utf8');
});
