# Implements: work-contracts/WC-135-visitor-conversation-and-simulated-customers.md WC135-R012, WC135-R013
# Constitutional basis: C-048, C-049, C-059, C-063
"""Gate logic comparing a baseline simulated-customer report with a new one."""

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from visitor_simulation.runner import REPORT_SCHEMA

IMPROVED = "improved"
REGRESSED = "regressed"
UNCHANGED = "unchanged"
MISSING = "missing"
NEW = "new"
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

    def to_json(self) -> dict[str, Any]:
        return {
            "persona": self.persona,
            "baselineTaskSuccess": self.baseline_rate,
            "newTaskSuccess": self.new_rate,
            "delta": self.delta,
            "noise": self.noise,
            "verdict": self.verdict,
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

    @property
    def gate_passed(self) -> bool:
        return not self.reasons

    @property
    def verdict(self) -> str:
        if not self.gate_passed:
            return "FAIL"
        return "IMPROVED" if any(p.verdict == IMPROVED for p in self.personas) else "PASS"

    def to_json(self) -> dict[str, Any]:
        return {
            "gatePassed": self.gate_passed,
            "verdict": self.verdict,
            "reasons": list(self.reasons),
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
    if not isinstance(data, dict) or data.get("schema") != REPORT_SCHEMA:
        raise ReportError(f"{path} is not a {REPORT_SCHEMA} report")
    return data


def _relative_lift(baseline: float, new: float) -> float | None:
    if baseline > 0:
        return (new - baseline) / baseline
    return None if new > 0 else 0.0


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
    """
    if noise_basis not in NOISE_BASES:
        raise ValueError(f"noise_basis must be one of {', '.join(NOISE_BASES)}")
    rows: list[PersonaComparison] = []
    reasons: list[str] = []
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
        rows.append(PersonaComparison(pid, base["taskSuccessRate"], current["taskSuccessRate"], delta, round(noise, 4), verdict))
        if verdict == REGRESSED:
            reasons.append(f"PERSONA_REGRESSION: {pid} task success {delta:+.2%} exceeds run-to-run noise {noise:.2%}")
    rows.extend(
        PersonaComparison(pid, None, cur["taskSuccessRate"], None, 0.0, NEW)
        for pid, cur in new_personas.items()
        if pid not in base_personas and cur.get("runs")
    )
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
    return Comparison(rows, base_lead, new_lead, lift, min_lift, lift_met, violations, reasons)


def render_markdown(comparison: Comparison) -> str:
    lift = "n/a (baseline was 0)" if comparison.lift is None else f"{comparison.lift:+.1%}"
    lines = [
        "# Simulated-customer comparison",
        "",
        f"**Gate: {comparison.verdict}**",
        "",
        "| Persona | Baseline task success | New task success | Change | Noise | Verdict |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for row in comparison.personas:
        base = "-" if row.baseline_rate is None else f"{row.baseline_rate:.1%}"
        new = "-" if row.new_rate is None else f"{row.new_rate:.1%}"
        delta = "-" if row.delta is None else f"{row.delta:+.1%}"
        lines.append(f"| {row.persona} | {base} | {new} | {delta} | {row.noise:.1%} | {row.verdict} |")
    lines += [
        "",
        f"- Lead rate (full success + lead): {comparison.baseline_lead_rate:.1%} to {comparison.new_lead_rate:.1%}; "
        f"relative lift {lift}",
        f"- Policy violations in the new report: {comparison.new_policy_violations}",
        "",
    ]
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
