// Implements: architecture/reference/acceptance/customer-journey-acceptance-architecture.md §3 Components (Test plan)
// Constitutional basis: C-059 (Implementation Traceability)
import { readFileSync } from "node:fs";
import type { WitnessId, ClaimDefinition, DepthLevel } from "./types.ts";
import { defineClaim } from "./claim.ts";

export interface PlanClaim {
  id: string;
  statement: string;
  witnesses_required: WitnessId[];
  depth_target?: DepthLevel;
  exception?: { reason: string };
}

export interface PlanStep {
  id: string;
  title: string;
  customer: string;
  stimulus: string;
  failure_path?: boolean;
  claims: PlanClaim[];
  provider_mode_required?: string;
  preconditions?: string[];
  requires_settings?: string[];
  proves?: { stories?: string[]; gaps?: string[]; requirements?: string[]; drivers?: string[] };
}

export interface Plan {
  schema: string;
  journey_id: string;
  version: number;
  steps: PlanStep[];
}

export interface CompiledPlan {
  plan: Plan;
  planDigest: string;
  liveScope: string[];
  agent: { id: string; display_name: string; offer_pattern: string };
}

/** The plan is compiled from reviewed YAML to JSON by scripts/acceptance_static_gates.py; the harness reads only the JSON. */
export function loadCompiledPlan(path: string): CompiledPlan {
  const loaded = JSON.parse(readFileSync(path, "utf8")) as CompiledPlan;
  for (const step of loaded.plan.steps) {
    for (const claim of step.claims) {
      defineClaim(claimDefinition(claim));
    }
  }
  return loaded;
}

export function claimDefinition(claim: PlanClaim): ClaimDefinition {
  return {
    id: claim.id,
    statement: claim.statement,
    witnessesRequired: claim.witnesses_required,
    exception: claim.exception,
    depthTarget: claim.depth_target,
  };
}

export function planStep(plan: Plan, stepId: string): PlanStep {
  const step = plan.steps.find((candidate) => candidate.id === stepId);
  if (step === undefined) {
    throw new Error(`plan has no step ${stepId}`);
  }
  return step;
}

export function stepIdentifiers(step: PlanStep): string[] {
  const proves = step.proves ?? {};
  return [
    ...(proves.stories ?? []),
    ...(proves.gaps ?? []),
    ...(proves.requirements ?? []),
    ...(proves.drivers ?? []),
  ];
}
