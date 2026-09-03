// Implements: architecture/reference/ux/wc-078-visual-experience-implementation-plan.md §11.1 (WC-07 declares; WC-08 executes)
// Constitutional basis: C-059 (Implementation Traceability)

import type { JourneyStageId, ProfessionalStoryId } from '../../lib/professional-journey-content';
import type { SupportedLocale } from '../../lib/preferences';

export type ScreenshotGroupId = 'G1' | 'G2' | 'G3' | 'G4' | 'G5' | 'G6' | 'G7' | 'G8';
export type ScreenshotTheme = 'light' | 'dark' | 'system';
export type ScreenshotMotion = 'normal' | 'reduced';
export type ScreenshotAnnouncement = 'visible' | 'dismissed';
export type ScreenshotConsent = 'banner' | 'preferences-open' | 'closed';
export type ScreenshotZoom = 'default' | '200%';
export type ScreenshotViewport = Readonly<{ width: number; height: number }>;

export type ScreenshotCase = Readonly<{
  id: string;
  group: ScreenshotGroupId;
  viewport: ScreenshotViewport;
  zoom: ScreenshotZoom;
  locale: SupportedLocale;
  theme: ScreenshotTheme;
  motion: ScreenshotMotion;
  announcement: ScreenshotAnnouncement;
  consent: ScreenshotConsent;
  professional?: ProfessionalStoryId;
  stage?: JourneyStageId;
}>;

const viewports: readonly ScreenshotViewport[] = [
  { width: 360, height: 800 },
  { width: 768, height: 1024 },
  { width: 1440, height: 900 },
];
const expandedViewport = viewports[2];
const compactViewport = viewports[0];

const themes: readonly ScreenshotTheme[] = ['light', 'dark', 'system'];
const professionals: readonly ProfessionalStoryId[] = ['agricultural-advisor', 'digital-marketing-professional'];
const stages: readonly JourneyStageId[] = ['opening', 'business', 'goals', 'agreement', 'ready', 'working'];
// One Devanagari sample (hi) and one Dravidian sample (ta) join Urdu RTL for the G6 script/direction sample.
const g6Locales: readonly SupportedLocale[] = ['ur', 'hi', 'ta'];
const consentStates: readonly ScreenshotConsent[] = ['banner', 'preferences-open'];

function baseCase(overrides: Partial<ScreenshotCase> & Pick<ScreenshotCase, 'group' | 'id' | 'viewport'>): ScreenshotCase {
  return { zoom: 'default', locale: 'en', theme: 'light', motion: 'normal', announcement: 'visible', consent: 'closed', ...overrides };
}

const g1: ScreenshotCase[] = viewports.flatMap((viewport) =>
  themes.map((theme) => baseCase({ group: 'G1', id: `G1-${viewport.width}x${viewport.height}-${theme}`, viewport, theme })));

const g2: ScreenshotCase[] = viewports.map((viewport) =>
  baseCase({ group: 'G2', id: `G2-${viewport.width}x${viewport.height}-200pct`, viewport, zoom: '200%' }));

const g3: ScreenshotCase[] = viewports.map((viewport) =>
  baseCase({ group: 'G3', id: `G3-${viewport.width}x${viewport.height}-reduced`, viewport, motion: 'reduced' }));

const g4: ScreenshotCase[] = professionals.flatMap((professional) =>
  stages.map((stage) => baseCase({ group: 'G4', id: `G4-${professional}-${stage}-expanded`, viewport: expandedViewport, professional, stage })));

const g5: ScreenshotCase[] = professionals.flatMap((professional) =>
  stages.map((stage) => baseCase({ group: 'G5', id: `G5-${professional}-${stage}-compact`, viewport: compactViewport, professional, stage })));

const g6: ScreenshotCase[] = g6Locales.flatMap((locale) =>
  [expandedViewport, compactViewport].map((viewport) => baseCase({ group: 'G6', id: `G6-${locale}-${viewport.width}x${viewport.height}`, viewport, locale })));

const g7: ScreenshotCase[] = viewports.map((viewport) =>
  baseCase({ group: 'G7', id: `G7-${viewport.width}x${viewport.height}-dismissed`, viewport, announcement: 'dismissed' }));

const g8: ScreenshotCase[] = consentStates.flatMap((consent) =>
  viewports.map((viewport) => baseCase({ group: 'G8', id: `G8-${viewport.width}x${viewport.height}-${consent}`, viewport, consent })));

/** Section 11.1 deterministic 54-case manifest. WC-07 declares this array; WC-08 generates, hashes, and indexes captures. */
export const wc078ScreenshotManifest: readonly ScreenshotCase[] = [...g1, ...g2, ...g3, ...g4, ...g5, ...g6, ...g7, ...g8];

/** G9 adds no capture; it applies the dedicated collision assertion to this exact G8 360px consent-banner case. */
export const wc078CollisionCaseId = 'G8-360x800-banner';
