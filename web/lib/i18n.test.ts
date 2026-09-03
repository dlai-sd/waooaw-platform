// Implements: architecture/reference/ux/hybrid-ui-acceptance-contract.md §CCT-UX-I18N-01
// Implements: architecture/reference/ux/wc-078-visual-experience-implementation-plan.md §12 (WC-01), §12 (WC-06)
// Constitutional basis: C-042 (Vocabulary Mandate), C-059 (Implementation Traceability)

import { getMessages, messages } from './i18n';
import { globalErrorMessages } from './global-error-messages';
import { directionForLocale, supportedLocales } from './preferences';
import type { ProfessionalJourneyContent } from './professional-journey-content';
import {
  getProfessionalJourneyContent,
  journeyAllowedFallbackTerms,
  journeyProhibitedInternalTerms,
  journeySelfReviewLedger,
  validateAllProfessionalJourneyLocales,
  validateProfessionalJourneyContent,
} from './professional-journey-content';

describe('F1 translations', () => {
  it('provides every F1 key for all eleven locales', () => {
    const englishKeys = Object.keys(messages.en).sort();
    expect(supportedLocales).toHaveLength(11);
    for (const locale of supportedLocales) {
      expect(Object.keys(getMessages(locale)).sort()).toEqual(englishKeys);
      expect(Object.values(getMessages(locale)).every((value) => value.trim().length > 0)).toBe(true);
    }
  });

  it('uses translated customer commands rather than English metadata only', () => {
    for (const locale of supportedLocales.filter((candidate) => candidate !== 'en')) {
      expect(getMessages(locale).browseProfessionals).not.toBe(messages.en.browseProfessionals);
      expect(getMessages(locale).skipToContent).not.toBe(messages.en.skipToContent);
    }
  });

  it('translates auth, system, and protected labels for Urdu', () => {
    expect(messages.ur.signInSecurely).not.toBe(messages.en.signInSecurely);
    expect(messages.ur.returnHome).not.toBe(messages.en.returnHome);
    expect(messages.ur.customerNavigation).not.toBe(messages.en.customerNavigation);
  });

  it('keeps the client-safe global error catalog aligned', () => {
    for (const locale of supportedLocales) {
      expect(globalErrorMessages[locale]).toEqual({
        globalErrorTitle: messages[locale].globalErrorTitle,
        globalErrorDescription: messages[locale].globalErrorDescription,
        tryAgain: messages[locale].tryAgain,
      });
    }
  });
});

describe('WC-078 professional journey showcase content', () => {
  it('provides a structurally complete two-story, six-stage, four-rail model for every locale', () => {
    for (const locale of supportedLocales) {
      const content = getProfessionalJourneyContent(locale);
      expect(content.heroTitle.trim().length).toBeGreaterThan(0);
      expect(content.heroSubtitle.trim().length).toBeGreaterThan(0);
      expect(content.finalMessage.trim().length).toBeGreaterThan(0);
      expect(content.accessibleSummary.trim().length).toBeGreaterThan(0);
      expect(Object.keys(content.railLabels).sort()).toEqual(['business', 'goals', 'ways-of-working', 'working'].sort());
      expect(Object.values(content.railLabels).every((label) => label.trim().length > 0)).toBe(true);
      expect(content.stories).toHaveLength(2);
      expect(content.stories.map((story) => story.id).sort()).toEqual(['agricultural-advisor', 'digital-marketing-professional'].sort());
      const stageIds = new Set<string>();
      for (const story of content.stories) {
        expect(story.selectorLabel.trim().length).toBeGreaterThan(0);
        expect(story.contextLabel.trim().length).toBeGreaterThan(0);
        expect(story.illustrationLabel.trim().length).toBeGreaterThan(0);
        expect(story.stages).toHaveLength(6);
        for (const stage of story.stages) {
          stageIds.add(`${story.id}:${stage.id}`);
          expect(stage.title.trim().length).toBeGreaterThan(0);
          expect(stage.summary.trim().length).toBeGreaterThan(0);
          expect(stage.details.length).toBeGreaterThan(0);
          expect(stage.details.every((detail) => detail.trim().length > 0)).toBe(true);
        }
      }
      expect(stageIds.size).toBe(12); // no duplicate story/stage IDs
    }
  });

  it('uses genuine non-English translations for every locale except allowlisted proper nouns', () => {
    const english = getProfessionalJourneyContent('en');
    function isAllowedFallback(value: string): boolean {
      return journeyAllowedFallbackTerms.includes(value);
    }
    for (const locale of supportedLocales.filter((candidate) => candidate !== 'en')) {
      const content = getProfessionalJourneyContent(locale);
      if (!isAllowedFallback(content.heroTitle)) expect(content.heroTitle).not.toBe(english.heroTitle);
      if (!isAllowedFallback(content.heroSubtitle)) expect(content.heroSubtitle).not.toBe(english.heroSubtitle);
      if (!isAllowedFallback(content.finalMessage)) expect(content.finalMessage).not.toBe(english.finalMessage);
      if (!isAllowedFallback(content.accessibleSummary)) expect(content.accessibleSummary).not.toBe(english.accessibleSummary);
      for (const railId of Object.keys(content.railLabels) as (keyof typeof content.railLabels)[]) {
        if (!isAllowedFallback(content.railLabels[railId])) expect(content.railLabels[railId]).not.toBe(english.railLabels[railId]);
      }
      content.stories.forEach((story, storyIndex) => {
        const englishStory = english.stories[storyIndex];
        if (!isAllowedFallback(story.selectorLabel)) expect(story.selectorLabel).not.toBe(englishStory.selectorLabel);
        if (!isAllowedFallback(story.contextLabel)) expect(story.contextLabel).not.toBe(englishStory.contextLabel);
        story.stages.forEach((stage, stageIndex) => {
          const englishStage = englishStory.stages[stageIndex];
          if (!isAllowedFallback(stage.title)) expect(stage.title).not.toBe(englishStage.title);
          if (!isAllowedFallback(stage.summary)) expect(stage.summary).not.toBe(englishStage.summary);
        });
      });
    }
  });
});

describe('WC-06 constitutional self-review ledger and locale validator', () => {
  it('passes the deterministic validator with an APPROVED, WAOOAW-AI-attributed ledger record for all eleven locales', () => {
    const results = validateAllProfessionalJourneyLocales();
    for (const locale of supportedLocales) {
      expect(results[locale]).toEqual([]);
      expect(journeySelfReviewLedger[locale].self_review_status).toBe('APPROVED');
      expect(journeySelfReviewLedger[locale].translator_agent).toBe('WAOOAW AI');
      expect(journeySelfReviewLedger[locale].source_catalog_hash.length).toBeGreaterThan(0);
    }
  });

  it('keeps prohibited internal governance terms out of customer-facing journey copy for every locale', () => {
    for (const locale of supportedLocales) {
      const issues = validateProfessionalJourneyContent(locale, getProfessionalJourneyContent(locale));
      expect(issues.filter((issue) => issue.reason.startsWith('prohibited-term'))).toEqual([]);
    }
    for (const term of journeyProhibitedInternalTerms) {
      expect(term.trim().length).toBeGreaterThan(0);
    }
  });

  it('detects a seeded English-fallback string in a non-English locale with locale and key identification (focused check)', () => {
    const hindi = getProfessionalJourneyContent('hi');
    const english = getProfessionalJourneyContent('en');
    const seeded: ProfessionalJourneyContent = { ...hindi, heroSubtitle: english.heroSubtitle };
    const issues = validateProfessionalJourneyContent('hi', seeded);
    expect(issues).toContainEqual({ locale: 'hi', key: 'heroSubtitle', reason: 'english-fallback' });
  });

  it('supplies Urdu RTL semantics through the existing locale direction utility', () => {
    expect(directionForLocale('ur')).toBe('rtl');
    for (const locale of supportedLocales.filter((candidate) => candidate !== 'ur')) {
      expect(directionForLocale(locale)).toBe('ltr');
    }
  });
});