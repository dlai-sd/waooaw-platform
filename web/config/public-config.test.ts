// Implements: work-contracts/WC-078-public-acquisition-experience-plan.md §Configuration Layers
// Constitutional basis: C-023 (Evidence First), C-059 (Implementation Traceability)
import { messages } from '@/lib/i18n';
import { marketingConfig } from './marketing';
import { validatePublicConfiguration } from './public-config';
import { siteConfig } from './site';
import { themeConfig } from './theme';

const valid = () => JSON.parse(JSON.stringify({ site: siteConfig, theme: themeConfig, marketing: marketingConfig, messages })) as { site: Record<string, unknown>; theme: Record<string, unknown>; marketing: Record<string, unknown>; messages: Record<string, Record<string, string>> };

describe('public configuration schema', () => {
  it('accepts the repository configuration', () => expect(validatePublicConfiguration(valid())).toEqual([]));
  it.each([
    ['unknown key', (value: ReturnType<typeof valid>) => { value.site.unknown = true; }, 'SITE_KEYS_INVALID'],
    ['unsafe URL', (value: ReturnType<typeof valid>) => { value.site.canonicalOrigin = 'javascript:alert(1)'; }, 'CANONICAL_ORIGIN_UNSAFE'],
    ['invalid color', (value: ReturnType<typeof valid>) => { value.theme.brandBlue = 'blue'; }, 'THEME_COLOR_INVALID'],
    ['missing locale key', (value: ReturnType<typeof valid>) => { delete value.messages.ur.register; }, 'LOCALE_CATALOG_INVALID'],
    ['secret-like key', (value: ReturnType<typeof valid>) => { value.marketing = { ...value.marketing, apiSecret: 'not-public' }; }, 'PUBLIC_SECRET_INVALID'],
  ])('rejects %s', (_name, mutate, expected) => {
    const configuration = valid();
    mutate(configuration);
    expect(validatePublicConfiguration(configuration)).toContain(expected);
  });
});