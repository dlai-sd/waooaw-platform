// Implements: work-contracts/WC-078-public-acquisition-experience-plan.md §Content Rules
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { readFile } from 'node:fs/promises';
import { join } from 'node:path';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { siteConfig } from '@/config/site';
import { projectPublicLegalSource } from '@/lib/public-legal';
import { breadcrumbData } from '@/lib/public-seo';
import { StructuredData } from './StructuredData';

async function legalSource(sourceFile: string): Promise<string> {
  const candidates = [join(process.cwd(), 'legal', sourceFile), join(process.cwd(), '..', 'legal', sourceFile)];
  for (const candidate of candidates) {
    try { return await readFile(candidate, 'utf8'); } catch { /* Try the development or standalone location. */ }
  }
  throw new Error(`Approved legal source unavailable: ${sourceFile}`);
}

export async function LegalPage({ effectiveDate, path, sourceFile, summary, title }: { effectiveDate: string; path: string; sourceFile: string; summary: string; title: string }) {
  const source = projectPublicLegalSource(await legalSource(sourceFile), sourceFile);
  return <article className="public-document legal-document"><StructuredData value={breadcrumbData(title, path)} /><header><p className="eyebrow">Version 1.0 - Effective {effectiveDate}</p><h1>{title}</h1><p>{summary}</p></header><div className="legal-source"><ReactMarkdown remarkPlugins={[remarkGfm]} components={{ a: ({ href, children }) => {
    const publicHref = href?.startsWith('mailto:') ? `mailto:${siteConfig.contactEmail}` : href;
    return <a href={publicHref} rel={publicHref?.startsWith('http') ? 'noreferrer' : undefined}>{children}</a>;
  } }}>{source}</ReactMarkdown></div></article>;
}