# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C1-05
# Implements: work-contracts/WC-135-visitor-conversation-and-simulated-customers.md WC135-R012, WC135-R013
# Constitutional basis: C-048, C-049, C-059, C-063
"""Gate logic comparing a baseline simulated-customer report with a new one."""

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from visitor_simulation.runner import COMPATIBLE_REPORT_SCHEMAS, REPORT_SCHEMA

IMPROVED = "improved"
REGRESSED = "regressed"
UNCHANGED = "unchanged"
MISSING = "missing"
NEW = "new"
UNAVAILABLE = "unavailable"
NOISE_BASES = ("std", "stderr")


class ReportError(ValueError):
    pass


@dataclass(frozen=True)
class PersonaComparison:
    persona: str
    baseline_rate: float | None
    new_rate: float | None
    delta: float | None
    noise: float
    verdict: str
    baseline_pass_k: float | None = None
    new_pass_k: float | None = None
    pass_k_delta: float | None = None
    pass_k_noise: float = 0.0
    pass_k_verdict: str = UNAVAILABLE

    def to_json(self) -> dict[str, Any]:
        return {
            "persona": self.persona,
            "baselineTaskSuccess": self.baseline_rate,
            "newTaskSuccess": self.new_rate,
            "delta": self.delta,
            "noise": self.noise,
            "verdict": self.verdict,
            "baselinePassK": self.baseline_pass_k,
            "newPassK": self.new_pass_k,
            "passKDelta": self.pass_k_delta,
            "passKNoise": self.pass_k_noise,
            "passKVerdict": self.pass_k_verdict,
        }


@dataclass
class Comparison:
    personas: list[PersonaComparison]
    baseline_lead_rate: float
    new_lead_rate: float
    lift: float | None
    min_lift: float | None
    lift_met: bool | None
    new_policy_violations: int
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def gate_passed(self) -> bool:
        return not self.reasons

    @property
    def verdict(self) -> str:
        if not self.gate_passed:
            return "FAIL"
        return "IMPROVED" if any(p.verdict == IMPROVED or p.pass_k_verdict == IMPROVED for p in self.personas) else "PASS"

    def to_json(self) -> dict[str, Any]:
        return {
            "gatePassed": self.gate_passed,
            "verdict": self.verdict,
            "reasons": list(self.reasons),
            "warnings": list(self.warnings),
            "newPolicyViolations": self.new_policy_violations,
            "leadRate": {
                "baseline": self.baseline_lead_rate,
                "new": self.new_lead_rate,
                "relativeLift": self.lift,
                "minLift": self.min_lift,
                "liftMet": self.lift_met,
            },
            "personas": [p.to_json() for p in self.personas],
        }


def load_report(path: str | Path) -> dict[str, Any]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReportError(f"cannot read report {path}: {type(exc).__name__}") from exc
    if not isinstance(data, dict) or data.get("schema") not in COMPATIBLE_REPORT_SCHEMAS:
        raise ReportError(f"{path} is not a {REPORT_SCHEMA} report")
    return data


def _relative_lift(baseline: float, new: float) -> float | None:
    if baseline > 0:
        return (new - baseline) / baseline
    return None if new > 0 else 0.0


def _pass_k_row(
    pid: str,
    base: dict[str, Any],
    current: dict[str, Any],
    noise_multiplier: float,
    noise_floor: float,
    noise_basis: str,
    reasons: list[str],
    warnings: list[str],
) -> tuple[float | None, float | None, float | None, float, str]:
    """pass^k of one persona: (baseline, new, delta, noise, verdict); gate failures and warnings are appended."""
    base_pass, new_pass = base.get("passK"), current.get("passK")
    if base_pass is None:
        warnings.append(f"PASSK_BASELINE_MISSING: {pid} has no pass^k in the baseline report; pass^k is not gated")
        return None, new_pass, None, 0.0, UNAVAILABLE
    if new_pass is None:
        reasons.append(f"PASSK_MISSING: {pid} has no pass^k in the new report although the baseline has one")
        return base_pass, None, None, 0.0, MISSING
    if base.get("k") != current.get("k"):
        warnings.append(
            f"PASSK_K_MISMATCH: {pid} baseline k={base.get('k')} differs from new k={current.get('k')}; pass^k is not gated"
        )
        return base_pass, new_pass, None, 0.0, UNAVAILABLE
    spreads = []
    for stats in (base, current):
        scale = math.sqrt(stats["seeds"]) if noise_basis == "stderr" and stats.get("seeds") else 1.0
        spreads.append(float(stats.get("runVariance") or 0.0) / scale)
    noise = noise_multiplier * max(spreads) + noise_floor
    delta = round(new_pass - base_pass, 4)
    verdict = IMPROVED if delta > noise else REGRESSED if delta < -noise else UNCHANGED
    if verdict == REGRESSED:
        reasons.append(f"PASSK_REGRESSION: {pid} pass^k {delta:+.2%} exceeds run-to-run noise {noise:.2%}")
    return base_pass, new_pass, delta, round(noise, 4), verdict


def compare_reports(
    baseline: dict[str, Any],
    new: dict[str, Any],
    *,
    min_lift: float | None = None,
    noise_multiplier: float = 1.0,
    noise_floor: float = 0.0,
    noise_basis: str = "std",
) -> Comparison:
    """Gate: fail on any policy violation, any persona below baseline by more than noise, or an unmet lift.

    Noise is the larger of the two reports' run-to-run standard deviations of the per-run task-success
    indicator for that persona (``noise_basis="std"``), or that deviation divided by sqrt(runs)
    (``"stderr"``, the noise of the rate itself), scaled by ``noise_multiplier``, plus ``noise_floor``.
    pass^k is gated the same way with ``runVariance`` (and the seed count) of each report. A baseline written before
    pass^k existed only produces a warning; a new report without pass^k against a baseline that has it fails.
    """
    if noise_basis not in NOISE_BASES:
        raise ValueError(f"noise_basis must be one of {', '.join(NOISE_BASES)}")
    rows: list[PersonaComparison] = []
    reasons: list[str] = []
    warnings: list[str] = []
    base_personas, new_personas = baseline["personas"], new["personas"]
    for pid, base in base_personas.items():
        if not base.get("runs"):
            continue
        current = new_personas.get(pid)
        if not current or not current.get("runs"):
            rows.append(PersonaComparison(pid, base["taskSuccessRate"], None, None, 0.0, MISSING))
            reasons.append(f"PERSONA_MISSING: {pid} has no runs in the new report")
            continue
        spread = max(
            base["taskSuccessStd"] / (math.sqrt(base["runs"]) if noise_basis == "stderr" else 1.0),
            current["taskSuccessStd"] / (math.sqrt(current["runs"]) if noise_basis == "stderr" else 1.0),
        )
        noise = noise_multiplier * spread + noise_floor
        delta = round(current["taskSuccessRate"] - base["taskSuccessRate"], 4)
        verdict = IMPROVED if delta > noise else REGRESSED if delta < -noise else UNCHANGED
        if verdict == REGRESSED:
            reasons.append(f"PERSONA_REGRESSION: {pid} task success {delta:+.2%} exceeds run-to-run noise {noise:.2%}")
        pass_base, pass_new, pass_delta, pass_noise, pass_verdict = _pass_k_row(
            pid, base, current, noise_multiplier, noise_floor, noise_basis, reasons, warnings
        )
        rows.append(
            PersonaComparison(
                pid,
                base["taskSuccessRate"],
                current["taskSuccessRate"],
                delta,
                round(noise, 4),
                verdict,
                pass_base,
                pass_new,
                pass_delta,
                pass_noise,
                pass_verdict,
            )
        )
    rows.extend(
        PersonaComparison(pid, None, cur["taskSuccessRate"], None, 0.0, NEW, new_pass_k=cur.get("passK"))
        for pid, cur in new_personas.items()
        if pid not in base_personas and cur.get("runs")
    )
    base_policy, new_policy = baseline.get("policyVersion"), new.get("policyVersion")
    if base_policy and new_policy and base_policy != new_policy:
        warnings.append(f"POLICY_VERSION_CHANGED: baseline policy {base_policy} differs from new policy {new_policy}")
    violations = int(new["overall"].get("policyViolationTotal", 0))
    if violations > 0:
        reasons.append(f"POLICY_VIOLATIONS: {violations} policy violation(s) in the new report")
    base_lead = float(baseline["overall"].get("leadRate", 0.0))
    new_lead = float(new["overall"].get("leadRate", 0.0))
    lift = _relative_lift(base_lead, new_lead)
    lift_met: bool | None = None
    if min_lift is not None:
        lift_met = new_lead > 0 if lift is None else lift >= min_lift
        if not lift_met:
            shown = "n/a" if lift is None else f"{lift:+.1%}"
            reasons.append(f"LIFT_NOT_MET: lead rate lift {shown} is below the required {min_lift:+.1%}")
    return Comparison(rows, base_lead, new_lead, lift, min_lift, lift_met, violations, reasons, warnings)


def render_markdown(comparison: Comparison) -> str:
    lift = "n/a (baseline was 0)" if comparison.lift is None else f"{comparison.lift:+.1%}"
    lines = [
        "# Simulated-customer comparison",
        "",
        f"**Gate: {comparison.verdict}**",
        "",
        "| Persona | Baseline task success | New task success | Change | Noise | Verdict "
        "| Baseline pass^k | New pass^k | pass^k verdict |",
        "|---|---:|---:|---:|---:|---|---:|---:|---|",
    ]
    for row in comparison.personas:
        base = "-" if row.baseline_rate is None else f"{row.baseline_rate:.1%}"
        new = "-" if row.new_rate is None else f"{row.new_rate:.1%}"
        delta = "-" if row.delta is None else f"{row.delta:+.1%}"
        pass_base = "-" if row.baseline_pass_k is None else f"{row.baseline_pass_k:.1%}"
        pass_new = "-" if row.new_pass_k is None else f"{row.new_pass_k:.1%}"
        lines.append(
            f"| {row.persona} | {base} | {new} | {delta} | {row.noise:.1%} | {row.verdict} | "
            f"{pass_base} | {pass_new} | {row.pass_k_verdict} |"
        )
    lines += [
        "",
        f"- Lead rate (full success + lead): {comparison.baseline_lead_rate:.1%} to {comparison.new_lead_rate:.1%}; "
        f"relative lift {lift}",
        f"- Policy violations in the new report: {comparison.new_policy_violations}",
        "",
    ]
    if comparison.warnings:
        lines += ["## Warnings", ""] + [f"- {warning}" for warning in comparison.warnings] + [""]
    if comparison.reasons:
        lines += ["## Gate failures", ""] + [f"- {reason}" for reason in comparison.reasons] + [""]
    return "\n".join(lines)


def write_comparison(comparison: Comparison, output_dir: str | Path) -> list[Path]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    json_path, md_path = out / "comparison.json", out / "comparison.md"
    json_path.write_text(json.dumps(comparison.to_json(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(comparison), encoding="utf-8")
    return [json_path, md_path]
