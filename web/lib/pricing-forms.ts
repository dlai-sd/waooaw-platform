// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import { inrFromPaise, paiseFromInr, subjectKeyFor, type PricingKind } from '@/lib/pricing-admin-client';

export type FieldType = 'text' | 'int' | 'number' | 'inr' | 'select' | 'datetime' | 'json';

export type FieldSpec = {
  name: string;
  label: string;
  type: FieldType;
  options?: readonly string[];
  optional?: boolean;
  help?: string;
};

export type FormKind = Exclude<PricingKind, 'PACKAGE'>;

export type FormSpec = {
  kind: FormKind;
  title: string;
  fields: readonly FieldSpec[];
  exactlyOneOf?: readonly [string, string];
};

export const formSpecs: Record<FormKind, FormSpec> = {
  RATE: {
    kind: 'RATE',
    title: 'Thread rate',
    fields: [
      { name: 'threadId', label: 'Thread identifier', type: 'text' },
      { name: 'provider', label: 'Provider', type: 'text' },
      { name: 'unit', label: 'Billing unit', type: 'text' },
      { name: 'rawCostPaise', label: 'Raw cost per unit (paise)', type: 'int' },
      { name: 'fxBufferPct', label: 'Currency buffer (%)', type: 'number' },
      { name: 'opsOverheadPct', label: 'Operations overhead (%)', type: 'number' },
      { name: 'riskPremiumPct', label: 'Risk premium (%)', type: 'number' },
    ],
  },
  POLICY: {
    kind: 'POLICY',
    title: 'Platform pricing policy',
    fields: [
      { name: 'minimumMarginPct', label: 'Minimum margin (%)', type: 'number' },
      { name: 'paymentGraceDays', label: 'Payment grace (days)', type: 'int' },
      { name: 'sunsetNoticeDays', label: 'Sunset notice (days)', type: 'int' },
      { name: 'costToleranceFraction', label: 'Cost tolerance (fraction)', type: 'number' },
      { name: 'costAlertFraction', label: 'Cost alert (fraction)', type: 'number' },
      { name: 'upgradeTiming', label: 'Upgrade takes effect', type: 'select', options: ['IMMEDIATE', 'AT_RENEWAL'] },
      {
        name: 'downgradeTiming',
        label: 'Downgrade takes effect',
        type: 'select',
        options: ['IMMEDIATE', 'AT_RENEWAL'],
      },
      { name: 'changeSizeGuardPercent', label: 'Large change guard (%)', type: 'number' },
      { name: 'priceMultipleGuard', label: 'Price multiple guard (times)', type: 'number' },
    ],
  },
  GRANT: {
    kind: 'GRANT',
    title: 'Trial or setup grant',
    fields: [
      { name: 'kind', label: 'Grant kind', type: 'select', options: ['TRIAL', 'SETUP'] },
      { name: 'agentType', label: 'Agent type', type: 'text' },
      { name: 'agentVersion', label: 'Agent version', type: 'text' },
      { name: 'paise', label: 'Grant value (INR)', type: 'inr', optional: true },
      { name: 'units', label: 'Grant units (JSON of thread to units)', type: 'json', optional: true },
      { name: 'durationDays', label: 'Valid for (days)', type: 'int', optional: true },
      { name: 'windowDays', label: 'Window (days)', type: 'int', optional: true },
    ],
  },
  BUDGET: {
    kind: 'BUDGET',
    title: 'Spend budget or ceiling',
    fields: [
      {
        name: 'scope',
        label: 'Budget scope',
        type: 'select',
        options: [
          'ENVIRONMENT_CEILING',
          'ACQUISITION_TENANT',
          'ACQUISITION_CAMPAIGN',
          'ACQUISITION_LEAD',
          'SIMULATION',
        ],
      },
      { name: 'ref', label: 'Scope reference', type: 'text' },
      { name: 'maximumPaise', label: 'Maximum (INR)', type: 'inr' },
      { name: 'perVisitorMessages', label: 'Messages per visitor', type: 'int', optional: true },
      { name: 'perDayNewSessions', label: 'New sessions per day', type: 'int', optional: true },
    ],
  },
  COUPON: {
    kind: 'COUPON',
    title: 'Discount coupon',
    exactlyOneOf: ['percent', 'amountPaise'],
    fields: [
      { name: 'code', label: 'Coupon code (capital letters and digits)', type: 'text' },
      { name: 'agentType', label: 'Agent type', type: 'text' },
      { name: 'agentVersion', label: 'Agent version', type: 'text' },
      { name: 'percent', label: 'Percent off (whole number)', type: 'int', optional: true },
      { name: 'amountPaise', label: 'Amount off (INR)', type: 'inr', optional: true },
      { name: 'capPaise', label: 'Discount cap (INR)', type: 'inr' },
      { name: 'expiresAt', label: 'Expires at (UTC)', type: 'datetime' },
      { name: 'reason', label: 'Goodwill reason', type: 'text' },
      { name: 'maxRedemptions', label: 'Maximum redemptions', type: 'int' },
    ],
  },
};

export type FormValues = Record<string, string>;

export type BuiltBody =
  | { ok: true; body: Record<string, unknown>; subjectKey: string }
  | { ok: false; errors: Record<string, string> };

// Operator-typed JSON; undefined means the text is not JSON (JSON.parse never yields undefined).
function parseJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return undefined;
  }
}

function convert(field: FieldSpec, raw: string): { value?: unknown; error?: string } {
  const text = raw.trim();
  if (text === '') return field.optional ? {} : { error: `${field.label} is required.` };
  switch (field.type) {
    case 'text':
      return { value: text };
    case 'select':
      return field.options?.includes(text)
        ? { value: text }
        : { error: `${field.label} must be one of the listed options.` };
    case 'int':
      return /^\d{1,12}$/.test(text) ? { value: Number(text) } : { error: `${field.label} must be a whole number.` };
    case 'number': {
      const value = Number(text);
      return Number.isFinite(value) && value >= 0
        ? { value }
        : { error: `${field.label} must be a number, zero or more.` };
    }
    case 'inr': {
      const paise = paiseFromInr(text);
      return paise === null
        ? { error: `${field.label} must be an amount with at most two decimals.` }
        : { value: paise };
    }
    case 'datetime': {
      const moment = new Date(/(Z|[+-]\d\d:\d\d)$/.test(text) ? text : `${text}Z`);
      return Number.isNaN(moment.getTime())
        ? { error: `${field.label} must be a date and time in UTC.` }
        : { value: moment.toISOString() };
    }
    case 'json': {
      const parsed = parseJson(text);
      if (parsed === undefined) return { error: `${field.label} must be valid JSON.` };
      const valid =
        parsed !== null &&
        typeof parsed === 'object' &&
        !Array.isArray(parsed) &&
        Object.values(parsed).every((entry) => typeof entry === 'number' && Number.isFinite(entry) && entry >= 0);
      return valid ? { value: parsed } : { error: `${field.label} must be an object of numbers.` };
    }
  }
}

export function buildBody(spec: FormSpec, values: FormValues): BuiltBody {
  const body: Record<string, unknown> = {};
  const errors: Record<string, string> = {};
  for (const field of spec.fields) {
    const { value, error } = convert(field, values[field.name] ?? '');
    if (error) errors[field.name] = error;
    else if (value !== undefined) body[field.name] = value;
  }
  if (spec.exactlyOneOf) {
    const [first, second] = spec.exactlyOneOf;
    if (!errors[first] && !errors[second] && first in body === second in body) {
      errors[first] = 'Give a percent or an amount, not both and not neither.';
    }
  }
  if (Object.keys(errors).length > 0) return { ok: false, errors };
  return { ok: true, body, subjectKey: subjectKeyFor(spec.kind, body) };
}

export function valuesFromBody(spec: FormSpec, body: Record<string, unknown> | undefined): FormValues {
  const values: FormValues = {};
  for (const field of spec.fields) {
    const stored = body?.[field.name];
    if (stored === undefined || stored === null) values[field.name] = '';
    else if (field.type === 'inr') values[field.name] = inrFromPaise(stored);
    else if (field.type === 'json') values[field.name] = JSON.stringify(stored);
    else if (field.type === 'datetime') values[field.name] = String(stored).slice(0, 16);
    else values[field.name] = String(stored);
  }
  return values;
}
