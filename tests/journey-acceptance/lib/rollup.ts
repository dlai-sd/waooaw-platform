// Implements: validation/acceptance/rollup.v1.yaml (WC107-R019); architecture/reference/acceptance/customer-journey-acceptance-architecture.md §8
// Constitutional basis: C-023 (Evidence First), C-049 (Honest Limitation), C-059 (Implementation Traceability)

export interface RollupJourney {
  id: string;
  title: string;
  steps: string[];
  reason?: string;
}

export interface RollupMap {
  requirement: string;
  devices: string[];
  journeys: RollupJourney[];
}

export interface RollupReport {
  candidate: {
    commit: string;
    device: string;
    environment: string;
    finished_at: string;
    services: { name: string; image: string }[];
  };
  steps: { stepId: string; verdict: string }[];
}

export interface RollupCell {
  journey: string;
  device: string;
  status: string;
  reasons: string[];
}

export interface RollupResult {
  requirement: string;
  status: "PASS" | "OPEN";
  candidate: { commit: string; images: string[] } | null;
  mismatches: string[];
  cells: RollupCell[];
}

function imagesOf(report: RollupReport): string {
  return report.candidate.services
    .map((service) => `${service.name}=${service.image}`)
    .sort()
    .join(",");
}

/**
 * The requirement is proven only for one exact deployed candidate: every report must carry the same commit and the same
 * service images, and every journey must pass on every device. A journey with no steps stays open, never skipped.
 */
export function rollup(map: RollupMap, reports: RollupReport[]): RollupResult {
  const mismatches: string[] = [];
  const first = reports[0];
  if (first === undefined) {
    mismatches.push("no report was supplied");
  } else {
    for (const report of reports) {
      if (report.candidate.commit !== first.candidate.commit) {
        mismatches.push(`a ${report.candidate.device} report is for commit ${report.candidate.commit.slice(0, 12)}, not ${first.candidate.commit.slice(0, 12)}`);
      }
      if (imagesOf(report) !== imagesOf(first)) {
        mismatches.push(`a ${report.candidate.device} report was taken against different service images`);
      }
    }
  }
  const cells: RollupCell[] = [];
  for (const journey of map.journeys) {
    for (const device of map.devices) {
      if (journey.steps.length === 0) {
        cells.push({ journey: journey.id, device, status: "NOT-COVERED", reasons: [journey.reason ?? "no step can prove this journey"] });
        continue;
      }
      const reasons: string[] = [];
      let status = "PASS";
      for (const stepId of journey.steps) {
        const candidates = reports
          .filter((report) => report.candidate.device === device)
          .filter((report) => report.steps.some((step) => step.stepId === stepId))
          .sort((left, right) => right.candidate.finished_at.localeCompare(left.candidate.finished_at));
        const verdict = candidates[0]?.steps.find((step) => step.stepId === stepId)?.verdict ?? "MISSING";
        if (verdict !== "PASS") {
          status = status === "PASS" || verdict === "FAIL" ? verdict : status;
          reasons.push(`${stepId} is ${verdict} on ${device}`);
        }
      }
      cells.push({ journey: journey.id, device, status, reasons });
    }
  }
  const passed = mismatches.length === 0 && cells.every((cell) => cell.status === "PASS");
  return {
    requirement: map.requirement,
    status: passed ? "PASS" : "OPEN",
    candidate: first === undefined ? null : { commit: first.candidate.commit, images: imagesOf(first).split(",") },
    mismatches,
    cells,
  };
}

export function renderRollup(result: RollupResult): string {
  const lines = [`# ${result.requirement} rollup: ${result.status}`, ""];
  for (const mismatch of result.mismatches) {
    lines.push(`- Candidate mismatch: ${mismatch}`);
  }
  const open = result.cells.filter((cell) => cell.status !== "PASS");
  lines.push("", "## Open", ...(open.length > 0 ? open.map((cell) => `- ${cell.journey} on ${cell.device}: ${cell.status}${cell.reasons.length > 0 ? ` (${cell.reasons.join("; ")})` : ""}`) : ["- none"]));
  lines.push("", "## Passed", ...(result.cells.filter((cell) => cell.status === "PASS").map((cell) => `- ${cell.journey} on ${cell.device}`)), "");
  return lines.join("\n");
}
