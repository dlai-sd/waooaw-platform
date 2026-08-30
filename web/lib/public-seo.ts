// Implements: work-contracts/WC-078-public-acquisition-experience-plan.md §Search Discovery Contract
// Constitutional basis: C-002 (Evidence Integrity), C-059 (Implementation Traceability)
import type { Metadata } from 'next';
import { absoluteUrl, siteConfig } from '@/config/site';

export function publicMetadata(title: string, description: string, path: string, type: 'website' | 'article' = 'website'): Metadata {
  const canonical = absoluteUrl(path);
  const languages = Object.fromEntries([...siteConfig.locales.map((locale) => [locale, canonical]), ['x-default', canonical]]);
  const image = { url: absoluteUrl('/waooaw-platform-logo.png'), width: 1254, height: 1254, alt: 'WAOOAW Platform' };
  const production = siteConfig.environment === 'production';
  return {
    title,
    description,
    robots: { index: production, follow: production },
    alternates: { canonical, languages },
    openGraph: { type, title, description, url: canonical, siteName: siteConfig.name, images: [image] },
    twitter: { card: 'summary_large_image', title, description, images: [image.url] },
  };
}

export function breadcrumbData(name: string, path: string) {
  return { '@context': 'https://schema.org', '@type': 'BreadcrumbList', itemListElement: [{ '@type': 'ListItem', position: 1, name: 'Home', item: absoluteUrl('/') }, { '@type': 'ListItem', position: 2, name, item: absoluteUrl(path) }] };
}