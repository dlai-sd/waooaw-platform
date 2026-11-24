// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

export type DiffEntry = { path: string; before?: string; after?: string };

export type Diff = { effectiveVersionId?: string | null; changes: DiffEntry[] };

export type ProfileCost = {
  profile: string;
  personaName?: string;
  expectedMonthlyCostPaise: number;
  marginPercent: number;
  dayOneExposurePaise?: number;
  proRataRefundPaise?: number;
};

export type SimulationWarning = { code: string; componentId?: string; message: string };

export type AffectedPackage = {
  packageVersionId: string;
  subjectKey: string;
  currentFloorPaise: number;
  newFloorPaise: number;
  priceInclGstPaise: number;
  belowFloor: boolean;
};

export type BuildUpCostLine = {
  componentId: string;
  threadId: string;
  quantity: number;
  unitsPerUnit: number;
  unitCostPaise?: number;
  lineCostPaise?: number;
  authorized: boolean;
};

export type BuildUp = {
  costLines: BuildUpCostLine[];
  infrastructureSharePaise: number;
  costFloorPaise: number;
  unauthorizedThreadIds: string[];
  uncostedComponentIds: string[];
  targetMarginPercent?: number;
  suggestedPriceInclGstPaise?: number;
  suggestionStatus: 'COMPLETE' | 'INCOMPLETE' | 'UNUSABLE';
};

export type Simulation = {
  draftId: string;
  kind: string;
  state: string;
  simulatedAt: string;
  costFloorPaise?: number;
  basePricePaise?: number;
  gstPaise?: number;
  priceInclGstPaise?: number;
  marginPercent?: number;
  minimumCompliantPricePaise?: number;
  buildUp?: BuildUp;
  diff?: Diff;
  profiles: ProfileCost[];
  warnings: SimulationWarning[];
  affectedPackages: AffectedPackage[];
};

export type VersionList<T> = { items: T[]; nextCursor?: string };

export type LiveMarginBreach = {
  packageVersionId: string;
  subjectKey: string;
  floorPaise: number;
  priceInclGstPaise: number;
  marginPercent: number;
  minimumMarginPercent: number;
  reason: 'BELOW_FLOOR' | 'BELOW_MINIMUM_MARGIN';
};

export type LiveMargin = { computedAt: string; packagesChecked: number; breaches: LiveMarginBreach[] };

export type ComponentCost = {
  componentId: string;
  recipeCostPaise: number;
  actualCostPaise: number;
  impliedMarginPercent: number;
  toleranceState: 'WITHIN_TOLERANCE' | 'ALERT' | 'EXCEEDED';
};

export type FundingDashboard = {
  generatedAt: string;
  periodFrom?: string;
  periodTo?: string;
  spendByAccountClass: { accountClass: string; spentPaise: number }[];
  spendByTenant: { tenantRef: string; spentPaise: number }[];
  spendByCampaign: { campaignRef: string; spentPaise: number }[];
  leadSpend: { leadRef: string; spentPaise: number }[];
  costPerLeadPaise: number;
  costPerConversationPaise: number;
  trialToHire: { trials: number; hires: number; conversionPercent: number };
  grantConsumption: {
    grantKind: string;
    agentType: string;
    agentVersion: string;
    consumedPaise: number;
    grantedPaise: number;
  }[];
  componentCost: ComponentCost[];
  events: { eventKind: string; count: number }[];
  breakers: { breaker: string; state: string }[];
  liveMarginBreaches: number;
};

export type MarginDashboard = {
  generatedAt: string;
  periodFrom?: string;
  periodTo?: string;
  packages: {
    packageVersionId: string;
    subjectKey: string;
    priceInclGstPaise: number;
    basePricePaise: number;
    costFloorPaise: number;
    marginPercent: number;
    minimumMarginPercent: number;
  }[];
  componentCost: ComponentCost[];
  liveMarginBreaches: number;
};

export type CatalogueThread = { threadId: string; unit: string; rawCostPaise: number };

export type PackageCatalogue = {
  agents: { agentType: string; agentVersion: string }[];
  threads: CatalogueThread[];
};
