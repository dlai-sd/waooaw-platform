// Implements: architecture/reference/ux/hybrid-ui-acceptance-contract.md §CCT-UX-I18N-01
// Constitutional basis: C-042 (Vocabulary Mandate), C-059 (Implementation Traceability)

import { getMessages, messages } from './i18n';
import { globalErrorMessages } from './global-error-messages';
import { supportedLocales } from './preferences';

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