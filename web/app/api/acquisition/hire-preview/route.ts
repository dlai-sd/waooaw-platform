// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-13
// Implements: work-contracts/WC-169-paid-hire-and-connected-accounts.md WC169-R013
// Constitutional basis: C-023, C-059, C-063

import { readServerResponse, logServerFailure } from '@/lib/server-failure';
import { withServerFailureBoundary, readRequestJson } from '@/lib/server-failure-boundary';
import { type NextRequest, NextResponse } from 'next/server';
import { resolveHireQuote } from '@/lib/api/hire-quote';
import { getIdentitySession } from '@/lib/api/identity';
import { getProfessionalDisclosure } from '@/lib/api/professionals';
import { accessTokenFromRequest } from '@/lib/server-auth';

const versionPattern = /^\d+\.\d+\.\d+$/;
const packageCodePattern = /^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$/;
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
    if (!disclosure.eligibility.eligible || disclosure.projectionVersion !== body.professionalVersion) {
      return NextResponse.json({ title: 'Professional commercial terms are unavailable.' }, { status: 409 });
    }
    const resolved = await resolveHireQuote(
      accessToken,
      body.professionalType,
      body.professionalVersion,
      body.packageCode
    );
    if (resolved.kind === 'not-offered') {
      return NextResponse.json({ title: 'Hire is not available for sale right now.' }, { status: 409 });
    }
    if (resolved.kind === 'unavailable') {
      return NextResponse.json({ title: 'Hire pricing is unavailable right now.' }, { status: 503 });
    }
    const { quote } = resolved;
    const response = await fetch(`${process.env.BILLING_ENGINE_URL ?? 'http://localhost:8140'}/payments/hire-preview`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        professional_type: disclosure.professionalType,
        professional_version: disclosure.projectionVersion,
        gross_amount_inr_paise: quote.grossAmountInrPaise,
        gst_amount_inr_paise: quote.gstAmountInrPaise,
        cadence: quote.cadence,
        ...(typeof body.couponCode === 'string' && body.couponCode.trim()
          ? { coupon_code: body.couponCode.trim().toUpperCase() }
          : {}),
      }),
      cache: 'no-store',
    });
    const result = await readServerResponse(response, 'web.acquisition.hire.preview.response_invalid', {
      title: 'Hire commercial preview is unavailable.',
    });
    if (!response.ok || !result || typeof result !== 'object' || Array.isArray(result)) {
      return NextResponse.json(result, { status: response.status, headers: { 'Cache-Control': 'no-store' } });
    }
    const details = (await loadPackages(accessToken, body.professionalType, body.professionalVersion)).find(
      (item) => item.packageCode === quote.packageCode
    );
    return NextResponse.json(
      {
        ...result,
        quoteVersion: quote.quoteVersion,
        package: {
          packageCode: quote.packageCode,
          billingPeriodDays: quote.billingPeriodDays,
          priceInclGstPaise: quote.grossAmountInrPaise,
          basePricePaise: quote.basePriceInrPaise,
          gstPaise: quote.gstAmountInrPaise,
          ...(details ? { displayName: details.displayName, components: details.components } : {}),
        },
      },
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
