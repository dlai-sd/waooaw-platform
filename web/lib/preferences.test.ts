// Implements: architecture/reference/ux/hybrid-ui-acceptance-contract.md §Accessibility, Language, and RTL
// Constitutional basis: C-042 (Vocabulary Mandate), C-059 (Implementation Traceability)

import {
  defaultLocale,
  defaultTheme,
  directionForLocale,
  resolveLocale,
  resolveTheme,
  supportedLocales,
} from './preferences';

describe('experience preferences', () => {
  it.each(supportedLocales)('accepts the supported %s locale', (locale) => {
    expect(resolveLocale(locale)).toBe(locale);
  });

  it('normalizes regional locale tags and defaults unknown values', () => {
    expect(resolveLocale('ur-PK')).toBe('ur');
    expect(resolveLocale('EN-IN')).toBe('en');
    expect(resolveLocale('fr')).toBe(defaultLocale);
    expect(resolveLocale(undefined)).toBe(defaultLocale);
  });

  it('uses RTL only for Urdu', () => {
    expect(directionForLocale('ur')).toBe('rtl');
    expect(directionForLocale('en')).toBe('ltr');
    expect(directionForLocale('hi')).toBe('ltr');
  });

  it.each(['light', 'dark', 'system'] as const)('accepts the %s theme', (theme) => {
    expect(resolveTheme(theme)).toBe(theme);
  });

  it('defaults unknown themes to system', () => {
    expect(resolveTheme('contrast')).toBe(defaultTheme);
    expect(resolveTheme(undefined)).toBe(defaultTheme);
  });
});
