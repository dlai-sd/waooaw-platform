// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-13
// Constitutional basis: C-023, C-059, C-063

import { readServerResponse, logServerFailure } from '@/lib/server-failure';
import { withServerFailureBoundary, readRequestJson } from '@/lib/server-failure-boundary';
import { type NextRequest, NextResponse } from 'next/server';
import { getIdentitySession } from '@/lib/api/identity';
import { getProfessionalDisclosure } from '@/lib/api/professionals';
import { accessTokenFromRequest } from '@/lib/server-auth';

const versionPattern = /^\d+\.\d+\.\d+$/;
const packageCodePattern = /^[A-Z][A-Z0-9_]{0,63}$/;
const businessPlatformUrl = process.env.BUSINESS_PLATFORM_URL ?? 'http://localhost:5001';

type PackageComponent = {
  componentId: string;
  label: string;
  quantity: number;
  cadence: string;
  selectableMaximum?: number;
};
type PackageView = {
  packageCode: string;
  displayName: string;
  billingPeriodDays: number;
  priceInclGstPaise: number;
  basePricePaise: number;
  gstPaise: number;
  components: PackageComponent[];
};

async function loadPackages(accessToken: string, professionalType: string, professionalVersion: string) {
  try {
    const response = await fetch(
      `${businessPlatformUrl}/api/v1/marketplace/agents/${encodeURIComponent(professionalType)}/versions/${encodeURIComponent(professionalVersion)}/packages?limit=100`,
      { headers: { Authorization: `Bearer ${accessToken}`, Accept: 'application/json' }, cache: 'no-store' }
    );
    if (!response.ok) return [];
    const list = (await response.json()) as { items?: PackageView[] };
    return Array.isArray(list.items) ? list.items : [];
  } catch (error) {
    logServerFailure('web.acquisition.hire.preview.packages_unavailable', error);
    return [];
  }
}

async function POSTHandler(request: NextRequest) {
  const accessToken = await accessTokenFromRequest(request);
  if (!accessToken) return NextResponse.json({ title: 'Secure sign in is required.' }, { status: 401 });
  const identity = await getIdentitySession(accessToken);
  if (identity.kind !== 'ready') {
    return NextResponse.json({ title: 'Complete registration before hiring a professional.' }, { status: 409 });
  }

  const body = (await readRequestJson(request)) as {
    professionalType?: string;
    professionalVersion?: string;
    packageCode?: string;
    couponCode?: string;
  };
  if (
    !body.professionalType ||
    !/^[A-Z][A-Z0-9_]{0,63}$/.test(body.professionalType) ||
    !body.professionalVersion ||
    !versionPattern.test(body.professionalVersion) ||
    (body.packageCode !== undefined && !packageCodePattern.test(body.packageCode))
  ) {
    return NextResponse.json({ title: 'Hire commercial preview is invalid.' }, { status: 400 });
  }

  try {
    const disclosure = await getProfessionalDisclosure(body.professionalType);
    if (
      !disclosure.eligibility.eligible ||
      disclosure.projectionVersion !== body.professionalVersion ||
      disclosure.indicativePrice.currency !== 'INR'
    ) {
      return NextResponse.json({ title: 'Professional commercial terms are unavailable.' }, { status: 409 });
    }
    const packages = await loadPackages(accessToken, body.professionalType, body.professionalVersion);
    const selected = body.packageCode ? packages.find((item) => item.packageCode === body.packageCode) : packages[0];
    if (body.packageCode && !selected) {
      return NextResponse.json({ title: 'The selected package is unavailable.' }, { status: 409 });
    }
    const grossPaise = selected?.priceInclGstPaise ?? disclosure.indicativePrice.amountInrPaise;
    const gstPaise = selected?.gstPaise ?? Math.floor((grossPaise * 18) / 118);
    const response = await fetch(`${process.env.BILLING_ENGINE_URL ?? 'http://localhost:8140'}/payments/hire-preview`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        professional_type: disclosure.professionalType,
        gross_amount_inr_paise: grossPaise,
        gst_amount_inr_paise: gstPaise,
        cadence: disclosure.indicativePrice.cadence,
        ...(typeof body.couponCode === 'string' && body.couponCode.trim()
          ? { coupon_code: body.couponCode.trim().toUpperCase() }
          : {}),
      }),
      cache: 'no-store',
    });
    const result = await readServerResponse(response, 'web.acquisition.hire.preview.response_invalid', {
      title: 'Hire commercial preview is unavailable.',
    });
    const includesPackage = selected && result && typeof result === 'object' && !Array.isArray(result);
    return NextResponse.json(
      includesPackage
        ? {
            ...result,
            package: {
              packageCode: selected.packageCode,
              displayName: selected.displayName,
              billingPeriodDays: selected.billingPeriodDays,
              priceInclGstPaise: selected.priceInclGstPaise,
              basePricePaise: selected.basePricePaise,
              gstPaise: selected.gstPaise,
              components: selected.components,
            },
          }
        : result,
      {
        status: response.status,
        headers: { 'Cache-Control': 'no-store' },
      }
    );
  } catch (error) {
    logServerFailure('web.acquisition.hire.preview.request_failed', error);
    return NextResponse.json({ title: 'Hire commercial preview is unavailable.' }, { status: 503 });
  }
}

export const POST = withServerFailureBoundary('web.acquisition.hire.preview.post_failed', POSTHandler);
