import { ProfessionalsApi } from '@/lib/api/generated/apis/ProfessionalsApi';
import type { ProfessionalMarketplacePageV1 } from '@/lib/api/generated/models/ProfessionalMarketplacePageV1';
import { Configuration } from '@/lib/api/generated/runtime';

export interface ProfessionalDiscoveryResult {
  professionalType: string;
  projectionVersion: string;
  displayName: string;
  suitability: string[];
  eligibility: { eligible: boolean; explanation: string };
}

export interface ProfessionalDisclosure extends ProfessionalDiscoveryResult {
  skills: Array<{ skillId: string; displayName: string; applicableInTrial: boolean; activationCondition?: string | null }>;
  limitations: string[];
  authorityNeeds: string[];
  customerRights: string[];
  trial: { available: boolean; durationDays: number; paidApiCallsAllowed: boolean; externalActionsAllowed: boolean };
  evidencePosture: string;
  indicativePrice: { currency: string; amountInrPaise: number; cadence: string; qualification: string };
}

const businessPlatformUrl = process.env.BUSINESS_PLATFORM_URL ?? 'http://localhost:5001';

export async function browseMarketplaceProfessionals(
  accessToken: string,
  filters: { cursor?: string; professionalType?: string; q?: string } = {},
): Promise<ProfessionalMarketplacePageV1> {
  const api = new ProfessionalsApi(new Configuration({ basePath: businessPlatformUrl, accessToken }));
  return api.browseMarketplaceProfessionals(
    { ...filters, limit: 24 },
    { cache: 'no-store' },
  );
}

async function getJson(path: string): Promise<unknown> {
  const response = await fetch(`${businessPlatformUrl}${path}`, { cache: 'no-store' });
  if (!response.ok) throw new Error(`Business Platform catalog request failed with ${response.status}.`);
  return response.json();
}

export async function discoverProfessionals(outcome: string): Promise<ProfessionalDiscoveryResult[]> {
  const result = await getJson(`/api/v1/professionals?outcome=${encodeURIComponent(outcome)}`);
  if (!Array.isArray(result)) throw new Error('Professional discovery response was not an array.');
  return result as ProfessionalDiscoveryResult[];
}

export async function getProfessionalDisclosure(professionalType: string): Promise<ProfessionalDisclosure> {
  return getJson(`/api/v1/professionals/${encodeURIComponent(professionalType)}/disclosure`) as Promise<ProfessionalDisclosure>;
}