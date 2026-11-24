// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import { inrFromPaise, paiseFromInr } from '@/lib/pricing-admin-client';

export const componentKinds = ['COUNTED', 'SELECTED', 'TIME_ACCESS', 'CAPACITY'] as const;
export const cadences = ['SPREAD', 'UPFRONT', 'DAILY', 'WEEKLY', 'MONTHLY'] as const;

// The package engine requires this component at exactly this quantity in every package.
export const PROACTIVE_COMPONENT_ID = 'PROACTIVE_MESSAGE';
export const PROACTIVE_QUANTITY = 30;

export type RecipeRow = { threadId: string; unitsPerUnit: string };

export type ComponentRowState = {
  key: string;
  componentId: string;
  kind: string;
  quantity: string;
  cadence: string;
  selectableMaximum: string;
  allocationInr: string;
  topupAllowed: boolean;
  recipe: RecipeRow[];
};

export type PackageState = {
  agentType: string;
  agentVersion: string;
  packageCode: string;
  displayName: string;
  description: string;
  targetMarginPct: string;
  billingPeriodDays: string;
  priceInr: string;
  gstRatePercent: string;
  infrastructureInr: string;
  components: ComponentRowState[];
};

let keyCounter = 0;
const nextKey = () => {
  keyCounter += 1;
  return `component-${keyCounter}`;
};

export function emptyComponent(componentId = ''): ComponentRowState {
  const proactive = componentId === PROACTIVE_COMPONENT_ID;
  return {
    key: nextKey(),
    componentId,
    kind: 'COUNTED',
    quantity: proactive ? String(PROACTIVE_QUANTITY) : '',
    cadence: 'SPREAD',
    selectableMaximum: '',
    allocationInr: '',
    topupAllowed: false,
    recipe: [],
  };
}

export function emptyPackage(): PackageState {
  return {
    agentType: '',
    agentVersion: '',
    packageCode: '',
    displayName: '',
    description: '',
    targetMarginPct: '',
    billingPeriodDays: '',
    priceInr: '',
    gstRatePercent: '',
    infrastructureInr: '0',
    components: [emptyComponent(PROACTIVE_COMPONENT_ID)],
  };
}

function text(value: unknown): string {
  return value === undefined || value === null ? '' : String(value);
}

export function packageFromBody(body: Record<string, unknown>): PackageState {
  const stored = Array.isArray(body.components) ? (body.components as Record<string, unknown>[]) : [];
  return {
    agentType: text(body.agentType),
    agentVersion: text(body.agentVersion),
    packageCode: text(body.packageCode),
    displayName: text(body.displayName),
    description: text(body.description),
    targetMarginPct: text(body.targetMarginPct),
    billingPeriodDays: text(body.billingPeriodDays),
    priceInr: inrFromPaise(body.priceInclGstPaise),
    gstRatePercent: text(body.gstRatePercent),
    infrastructureInr: inrFromPaise(body.infrastructureSharePaise),
    components: stored.map((component) => ({
      key: nextKey(),
      componentId: text(component.componentId),
      kind: text(component.kind),
      quantity: text(component.quantity),
      cadence: text(component.cadence) || 'SPREAD',
      selectableMaximum: text(component.selectableMaximum),
      allocationInr: inrFromPaise(component.priceAllocationPaise),
      topupAllowed: component.topupAllowed === true,
      recipe: (Array.isArray(component.recipe) ? (component.recipe as Record<string, unknown>[]) : []).map((entry) => ({
        threadId: text(entry.threadId),
        unitsPerUnit: text(entry.unitsPerUnit),
      })),
    })),
  };
}

export function allocationTotalPaise(components: readonly ComponentRowState[]): number {
  return components.reduce((sum, component) => sum + (paiseFromInr(component.allocationInr) ?? 0), 0);
}

// Display only: the owner derives the authoritative base price and GST.
export function derivedPrice(priceInr: string, gstRatePercent: string): { basePaise: number; gstPaise: number } | null {
  const price = paiseFromInr(priceInr);
  const rate = /^\d{1,3}$/.test(gstRatePercent.trim()) ? Number(gstRatePercent) : null;
  if (price === null || rate === null) return null;
  const basePaise = Math.round((price * 100) / (100 + rate));
  return { basePaise, gstPaise: price - basePaise };
}

export type BuiltPackage =
  | { ok: true; body: Record<string, unknown>; subjectKey: string }
  | { ok: false; errors: string[] };

export const MAXIMUM_DESCRIPTION = 500;

// Empty means "not set" and the policy minimum margin applies; null means the text is not a valid percent.
function parseMargin(value: string): number | null | undefined {
  const trimmed = value.trim();
  if (trimmed === '') return undefined;
  if (!/^\d{1,2}(\.\d{1,2})?$/.test(trimmed)) return null;
  return Number(trimmed);
}

const whole = (value: string) => (/^\d{1,9}$/.test(value.trim()) ? Number(value) : null);

export function buildPackage(state: PackageState): BuiltPackage {
  const errors: string[] = [];
  const required = {
    agentType: 'Agent type',
    agentVersion: 'Agent version',
    packageCode: 'Package code',
    displayName: 'Package name',
  } as const;
  for (const [field, label] of Object.entries(required)) {
    if (state[field as keyof typeof required].trim() === '') errors.push(`${label} is required.`);
  }
  const price = paiseFromInr(state.priceInr);
  if (price === null || price === 0)
    errors.push('Price including GST must be an amount above zero with at most two decimals.');
  const period = whole(state.billingPeriodDays);
  if (period === null || period < 1 || period > 366) errors.push('Billing period must be between 1 and 366 days.');
  const gst = whole(state.gstRatePercent);
  if (gst === null || gst > 100) errors.push('GST rate must be a whole percent from 0 to 100.');
  const infrastructure = paiseFromInr(state.infrastructureInr);
  if (infrastructure === null) errors.push('Infrastructure share must be an amount with at most two decimals.');
  if (state.components.length === 0) errors.push('Add at least one component.');
  const description = state.description.trim();
  if (description.length > MAXIMUM_DESCRIPTION)
    errors.push(`Description can be at most ${MAXIMUM_DESCRIPTION} characters.`);
  const margin = parseMargin(state.targetMarginPct);
  if (margin === null)
    errors.push('Target margin must be a percent from 0 up to but not including 100, with at most two decimals.');

  const components = state.components.map((component, index) => {
    const label = component.componentId.trim() || `Component ${index + 1}`;
    const quantity = whole(component.quantity);
    const allocation = paiseFromInr(component.allocationInr);
    const maximum = component.selectableMaximum.trim() === '' ? undefined : whole(component.selectableMaximum);
    if (component.componentId.trim() === '') errors.push(`${label}: component identifier is required.`);
    if (quantity === null || quantity < 1) errors.push(`${label}: quantity must be a whole number of at least 1.`);
    if (allocation === null) errors.push(`${label}: price allocation must be an amount with at most two decimals.`);
    if (maximum === null || maximum === 0)
      errors.push(`${label}: selectable maximum must be a whole number of at least 1.`);
    if (component.componentId === PROACTIVE_COMPONENT_ID && quantity !== PROACTIVE_QUANTITY) {
      errors.push(`${label}: the proactive message component is fixed at ${PROACTIVE_QUANTITY}.`);
    }
    const recipe = component.recipe.map((entry) => {
      const units = whole(entry.unitsPerUnit);
      if (entry.threadId.trim() === '') errors.push(`${label}: every recipe row needs a thread.`);
      if (units === null || units < 1) errors.push(`${label}: recipe units must be whole numbers of at least 1.`);
      return { threadId: entry.threadId.trim(), unitsPerUnit: units ?? 0 };
    });
    return {
      componentId: component.componentId.trim(),
      kind: component.kind,
      quantity: quantity ?? 0,
      cadence: component.cadence,
      ...(maximum ? { selectableMaximum: maximum } : {}),
      priceAllocationPaise: allocation ?? 0,
      recipe,
      topupAllowed: component.topupAllowed,
    };
  });

  if (errors.length > 0) return { ok: false, errors };
  const body = {
    agentType: state.agentType.trim(),
    agentVersion: state.agentVersion.trim(),
    packageCode: state.packageCode.trim(),
    displayName: state.displayName.trim(),
    ...(description === '' ? {} : { description }),
    ...(margin === undefined || margin === null ? {} : { targetMarginPct: margin }),
    billingPeriodDays: period,
    priceInclGstPaise: price,
    gstRatePercent: gst,
    infrastructureSharePaise: infrastructure,
    components,
  };
  return { ok: true, body, subjectKey: `package:${body.agentType}|${body.agentVersion}|${body.packageCode}` };
}
