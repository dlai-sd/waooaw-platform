// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-04
// Constitutional basis: C-001, C-059, C-063, ADR-051

import type {
  CreateWorkbenchHandoffRequestV1,
  ExperienceBlockV2,
  WorkbenchCapabilityListV1,
  WorkbenchEvidenceListV1,
  WorkbenchGoalListV1,
  WorkbenchPlanV1,
  WorkbenchProjectionV1,
  WorkbenchWalletV1,
  WorkbenchWorkItemListV1,
} from '@/lib/api/generated/workbench-v1/src';

// Server loaders and browser refreshes both carry the JSON wire shape, where timestamps are ISO strings.
export type Wire<T> = T extends Date
  ? string
  : T extends ReadonlyArray<infer Item>
    ? Array<Wire<Item>>
    : T extends object
      ? { [Key in keyof T]: Wire<T[Key]> }
      : T;

export type WorkbenchProjection = Wire<WorkbenchProjectionV1>;
export type WorkbenchGoalList = Wire<WorkbenchGoalListV1>;
export type WorkbenchPlan = Wire<WorkbenchPlanV1>;
export type WorkbenchCapabilityList = Wire<WorkbenchCapabilityListV1>;
export type WorkbenchWallet = Wire<WorkbenchWalletV1>;
export type WorkbenchEvidenceList = Wire<WorkbenchEvidenceListV1>;
export type WorkbenchWorkItemList = Wire<WorkbenchWorkItemListV1>;
export type WorkbenchBlock = Wire<ExperienceBlockV2>;
export type WorkbenchHandoffPurpose = CreateWorkbenchHandoffRequestV1['purpose'];

// The answer to redeeming a single-use handoff link (consumeWorkbenchHandoff).
export type WorkbenchHandoffConsumption = {
  schemaVersion: string;
  purpose: string;
  contextRef?: string | null;
};

export type WorkbenchSnapshot = {
  projection: WorkbenchProjection;
  version: string;
  goals: WorkbenchGoalList | null;
  plan: WorkbenchPlan | null;
  capabilities: WorkbenchCapabilityList | null;
  wallet: WorkbenchWallet | null;
  evidence: WorkbenchEvidenceList | null;
  workItems: WorkbenchWorkItemList | null;
};

export type WorkbenchLoad =
  | { state: 'available'; snapshot: WorkbenchSnapshot }
  | { state: 'disabled' }
  | { state: 'unavailable' };

export type WorkbenchProblem = {
  code?: string;
  title?: string;
  detail?: string;
  correlationId?: string;
};
