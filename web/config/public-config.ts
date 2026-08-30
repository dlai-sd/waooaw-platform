// Implements: work-contracts/WC-078-public-acquisition-experience-plan.md §Configuration Layers
// Constitutional basis: C-002 (Evidence Integrity), C-059 (Implementation Traceability), C-063 (Data Minimisation)
import { messages } from '@/lib/i18n';
import { marketingConfig } from './marketing';
import { siteConfig } from './site';
import { themeConfig } from './theme';

type PublicConfiguration = { site: Record<string, unknown>; theme: Record<string, unknown>; marketing: Record<string, unknown>; messages: Record<string, Record<string, string>> };
const supportedLocales = ['en', 'hi', 'mr', 'ta', 'te', 'kn', 'gu', 'bn', 'ml', 'pa', 'ur'];
const expectedKeys = {
  site: ['name', 'company', 'canonicalOrigin', 'contactEmail', 'environment', 'locales', 'announcement', 'sectionSwitches', 'socialLinks', 'publicNavigation', 'footerGroups'],
  theme: ['brandBlue', 'brandGreen', 'brandOrange', 'brandNavy', 'radius', 'duration'],
  marketing: ['policyVersion', 'attributionWindowMinutes', 'ga4', 'serverGtm', 'meta'],
};

function exactKeys(value: Record<string, unknown>, expected: readonly string[]): boolean {
  return Object.keys(value).sort().join('|') === [...expected].sort().join('|');
}

export function validatePublicConfiguration(configuration: PublicConfiguration): string[] {
  const errors: string[] = [];
  if (!exactKeys(configuration.site, expectedKeys.site)) errors.push('SITE_KEYS_INVALID');
  if (!exactKeys(configuration.theme, expectedKeys.theme)) errors.push('THEME_KEYS_INVALID');
  if (!exactKeys(configuration.marketing, expectedKeys.marketing)) errors.push('MARKETING_KEYS_INVALID');
  try {
    const origin = new URL(String(configuration.site.canonicalOrigin));
    if (origin.protocol !== 'https:' && origin.hostname !== 'localhost' && origin.hostname !== '127.0.0.1') errors.push('CANONICAL_ORIGIN_UNSAFE');
  } catch { errors.push('CANONICAL_ORIGIN_INVALID'); }
  if (configuration.site.contactEmail !== 'customersupport@dlaisd.com') errors.push('PUBLIC_CONTACT_INVALID');
  const locales = configuration.site.locales as unknown[];
  if (!Array.isArray(locales) || locales.join('|') !== supportedLocales.join('|') || new Set(locales).size !== locales.length) errors.push('LOCALES_INVALID');
  const navigation = configuration.site.publicNavigation as { href?: unknown }[];
  if (!Array.isArray(navigation) || navigation.some(({ href }) => typeof href !== 'string' || !href.startsWith('/')) || new Set(navigation.map(({ href }) => href)).size !== navigation.length) errors.push('NAVIGATION_INVALID');
  const colorValues = Object.entries(configuration.theme).filter(([key]) => key.startsWith('brand')).map(([, value]) => value);
  if (colorValues.some((value) => typeof value !== 'string' || !/^#[0-9a-f]{6}$/i.test(value))) errors.push('THEME_COLOR_INVALID');
  const localeKeys = Object.keys(configuration.messages).sort();
  const sourceKeys = Object.keys(configuration.messages.en ?? {}).sort().join('|');
  if (localeKeys.join('|') !== [...supportedLocales].sort().join('|') || Object.values(configuration.messages).some((catalog) => Object.keys(catalog).sort().join('|') !== sourceKeys || Object.values(catalog).some((value) => !value.trim()))) errors.push('LOCALE_CATALOG_INVALID');
  const serialized = JSON.stringify(configuration);
  if (/"[^"\n]*(?:secret|password|token)[^"\n]*"\s*:/i.test(serialized) || /-----BEGIN [A-Z ]+ PRIVATE KEY-----|\bsk-[A-Za-z0-9]{20,}/.test(serialized)) errors.push('PUBLIC_SECRET_INVALID');
  for (const destination of ['ga4', 'meta'] as const) {
    const value = configuration.marketing[destination] as { enabled?: boolean; id?: string };
    if (value?.enabled && !value.id) errors.push(`${destination.toUpperCase()}_READINESS_INVALID`);
  }
  return errors;
}

export function assertPublicConfiguration(configuration: PublicConfiguration): void {
  const errors = validatePublicConfiguration(configuration);
  if (errors.length) throw new Error(`Invalid public configuration: ${errors.join(', ')}`);
}

assertPublicConfiguration({ site: siteConfig, theme: themeConfig, marketing: marketingConfig, messages });