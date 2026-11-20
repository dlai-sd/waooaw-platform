import 'server-only';

// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import { redirect } from 'next/navigation';
import { pricingAccess } from '@/lib/pricing-admin';
import { pricingApis } from '@/lib/pricing-admin-server';
import { logServerFailure } from '@/lib/server-failure';
import type { PricingKind, PricingVersion } from '@/lib/pricing-admin-client';
import type { PackageCatalogue } from '@/lib/pricing-admin-types';
import { getServerAccessToken } from '@/lib/server-auth';

export type PricingPageSession = { accessToken: string; isFounder: boolean };

export async function requirePricingPage(): Promise<PricingPageSession> {
  const accessToken = await getServerAccessToken();
  if (!accessToken) redirect('/home');
  const access = pricingAccess(accessToken);
  if (!access.administrator) redirect('/home');
  return { accessToken, isFounder: access.founder };
}

// The generated client returns Date objects; the browser components use the JSON wire shape.
export function wireShape<T>(value: unknown): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

// Drafts and published versions come from two lists; null means the owner could not be reached.
export async function loadVersions(accessToken: string, kind: PricingKind): Promise<PricingVersion[] | null> {
  const { drafts, versions } = pricingApis(accessToken);
  try {
    const [pending, published] = await Promise.all([
      drafts.listPricingDrafts({ kind, limit: 100 }),
      versions.listPricingVersions({ kind, limit: 100 }),
    ]);
    const merged = new Map<string, PricingVersion>();
    for (const version of [
      ...wireShape<{ items: PricingVersion[] }>(published).items,
      ...wireShape<{ items: PricingVersion[] }>(pending).items,
    ]) {
      merged.set(version.versionId, version);
    }
    return [...merged.values()];
  } catch (error) {
    logServerFailure('web.admin.pricing.versions_failed', error);
    return null;
  }
}

export async function loadVersion(accessToken: string, versionId: string): Promise<PricingVersion | null> {
  try {
    return wireShape<PricingVersion>(await pricingApis(accessToken).drafts.getPricingDraft({ draftId: versionId }));
  } catch (error) {
    logServerFailure('web.admin.pricing.version_failed', error);
    return null;
  }
}

export function catalogueFrom(rates: PricingVersion[], agentSources: PricingVersion[]): PackageCatalogue {
  const threads = new Map<string, PackageCatalogue['threads'][number]>();
  for (const rate of rates) {
    if (rate.state !== 'EFFECTIVE') continue;
    const { threadId, unit, rawCostPaise } = rate.body as {
      threadId?: unknown;
      unit?: unknown;
      rawCostPaise?: unknown;
    };
    if (typeof threadId === 'string' && typeof unit === 'string' && typeof rawCostPaise === 'number') {
      threads.set(threadId, { threadId, unit, rawCostPaise });
    }
  }
  const agents = new Map<string, { agentType: string; agentVersion: string }>();
  for (const source of agentSources) {
    const { agentType, agentVersion } = source.body as { agentType?: unknown; agentVersion?: unknown };
    if (typeof agentType === 'string' && typeof agentVersion === 'string') {
      agents.set(`${agentType}|${agentVersion}`, { agentType, agentVersion });
    }
  }
  return { agents: [...agents.values()], threads: [...threads.values()] };
}

export async function loadCatalogue(accessToken: string, packages: PricingVersion[]): Promise<PackageCatalogue> {
  const [rates, grants] = await Promise.all([loadVersions(accessToken, 'RATE'), loadVersions(accessToken, 'GRANT')]);
  return catalogueFrom(rates ?? [], [...packages, ...(grants ?? [])]);
}

export function periodFrom(value: string | string[] | undefined): string {
  const candidate = Array.isArray(value) ? value[0] : value;
  return candidate && /^\d{4}-\d{2}-\d{2}$/.test(candidate) ? candidate : '';
}
