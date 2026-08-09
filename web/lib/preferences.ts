// Implements: architecture/reference/ux/hybrid-visual-system-contract.md §Typography and Script Contract
// Constitutional basis: C-042 (Vocabulary Mandate), C-059 (Implementation Traceability)

export const supportedLocales = ['en', 'hi', 'mr', 'ta', 'te', 'kn', 'gu', 'bn', 'ml', 'pa', 'ur'] as const;

export type SupportedLocale = (typeof supportedLocales)[number];
export type TextDirection = 'ltr' | 'rtl';
export type ThemePreference = 'light' | 'dark' | 'system';

export const defaultLocale: SupportedLocale = 'en';
export const defaultTheme: ThemePreference = 'system';

export function resolveLocale(value: string | undefined): SupportedLocale {
  const locale = value?.toLowerCase().split('-')[0];
  return supportedLocales.find((candidate) => candidate === locale) ?? defaultLocale;
}

export function directionForLocale(locale: SupportedLocale): TextDirection {
  return locale === 'ur' ? 'rtl' : 'ltr';
}

export function resolveTheme(value: string | undefined): ThemePreference {
  return value === 'light' || value === 'dark' || value === 'system' ? value : defaultTheme;
}
