#!/usr/bin/env python3
# Implements: architecture/reference/acceptance/customer-journey-acceptance-architecture.md §9 Architecture Fitness Contract (F1-F5, F17, F19, F20)
# Constitutional basis: C-059 (Implementation Traceability), C-071 (Quality Obligation)
"""Static gates and plan compilation for customer journey acceptance (ADR-054, WC-158).

Everything here is deterministic and needs no deployed environment. Run it only through the repository's Docker runners.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

ACCEPTANCE = Path("validation/acceptance")
PLANS = ACCEPTANCE / "plans"
ENVIRONMENTS = ACCEPTANCE / "environments"
WORKFLOW = Path(".github/workflows/customer-journey-acceptance.yaml")
SPECS = Path("tests/journey-acceptance/specs")
HARNESS = Path("tests/journey-acceptance")
GOAL_005 = Path("goals/GOAL-005-agent-employment-experience-program.md")
GAP_REGISTER = Path("architecture/reference/product/waooaw-product-gap-register.md")
DRIVERS = Path("knowledge/architectural-drivers.md")
CREDENTIAL_WORD = re.compile(r"(SECRET|TOKEN|PASSWORD|CREDENTIAL|API_?KEY|PRIVATE_?KEY)", re.IGNORECASE)
WORKFLOW_REFERENCE = re.compile(r"customer-journey-acceptance\.ya?ml|Customer Journey Acceptance")
ENVIRONMENT_NAMES = {"demo", "uat", "qa", "prod", "production", "dev"}
SPEC_STEP = re.compile(
    r"acceptanceStep\(\s*[\"'](?P<step>S[0-9]+[a-z]?)[\"']\s*,\s*\{\s*covers:\s*\[(?P<ids>[^\]]*)\]", re.DOTALL
)
ENV_COMPARISON = re.compile(r"(?:===|!==|==|!=)\s*[\"'](?P<name>[a-z]+)[\"']")


def load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def schema_violations(instance: Any, schema_path: Path, label: str) -> list[str]:
    validator = Draft202012Validator(json.loads(schema_path.read_text(encoding="utf-8")))
    return [
        f"SCHEMA {label}: {'/'.join(map(str, error.absolute_path)) or '<root>'}: {error.message}"
        for error in validator.iter_errors(instance)
    ]


def known_identifiers(root: Path) -> dict[str, set[str]]:
    requirements: set[str] = set()
    for ledger in sorted((root / "work-contracts").glob("*-requirements.yaml")):
        loaded = load_yaml(ledger)
        for item in (loaded or {}).get("requirements", []) or []:
            if isinstance(item, dict) and "requirement_id" in item:
                requirements.add(str(item["requirement_id"]))
    goal = (root / GOAL_005).read_text(encoding="utf-8")
    gaps = (root / GAP_REGISTER).read_text(encoding="utf-8")
    drivers = (root / DRIVERS).read_text(encoding="utf-8")
    return {
        "stories": set(re.findall(r"\bAE-\d{2}-S\d{2}\b", goal)),
        "gaps": set(re.findall(r"^\| (PG-\d{2}) \|", gaps, re.MULTILINE)),
        "requirements": requirements,
        "drivers": set(re.findall(r"^## (AD-\d{3})\b", drivers, re.MULTILINE)),
    }


def step_identifiers(step: dict[str, Any]) -> list[str]:
    proves = step.get("proves") or {}
    return [*proves.get("stories", []), *proves.get("gaps", []), *proves.get("requirements", []), *proves.get("drivers", [])]


def plan_violations(plan: dict[str, Any], known: dict[str, set[str]]) -> list[str]:
    """F4 witness discipline and F5 traceability."""
    found = []
    exceptions = {item["claim"]: item["reason"] for item in plan.get("witness_exceptions", []) or []}
    for step in plan.get("steps", []):
        proves = step.get("proves") or {}
        if not step_identifiers(step):
            found.append(f"F5 step {step['id']} cites no requirement, story, gap or driver identifier")
        for kind, register in (
            ("stories", "stories"),
            ("gaps", "gaps"),
            ("requirements", "requirements"),
            ("drivers", "drivers"),
        ):
            for identifier in proves.get(kind, []):
                if identifier not in known[register]:
                    found.append(f"F5 step {step['id']} cites {identifier}, which does not exist in its register")
        for claim in step.get("claims", []):
            witnesses = set(claim.get("witnesses_required", []))
            if len(witnesses) < 2 and not str(exceptions.get(claim["id"], "")).strip():
                found.append(
                    f"F4 claim {claim['id']} requires fewer than two witnesses and has no listed exception with a reason"
                )
    return found


def spec_declarations(root: Path) -> list[dict[str, Any]]:
    declarations = []
    specs = root / SPECS
    for path in sorted(specs.rglob("*.ts")) if specs.exists() else []:
        text = path.read_text(encoding="utf-8")
        for match in SPEC_STEP.finditer(text):
            ids = [value for value in re.findall(r"[\"']([^\"']+)[\"']", match.group("ids"))]
            declarations.append({"file": path.relative_to(root).as_posix(), "step": match.group("step"), "covers": ids})
    return declarations


def spec_violations(plan: dict[str, Any], declarations: list[dict[str, Any]], known: dict[str, set[str]]) -> list[str]:
    """F20: plan and spec agreement in both directions."""
    found = []
    steps = {step["id"]: step for step in plan.get("steps", [])}
    all_known = set().union(*known.values())
    covered_steps = {declaration["step"] for declaration in declarations}
    for step_id in steps:
        if step_id not in covered_steps:
            found.append(f"F20 plan step {step_id} has no spec")
    for declaration in declarations:
        step = steps.get(declaration["step"])
        if step is None:
            found.append(f"F20 {declaration['file']} cites plan step {declaration['step']}, which does not exist")
            continue
        allowed = set(step_identifiers(step))
        for identifier in declaration["covers"]:
            if identifier not in all_known:
                found.append(f"F20 {declaration['file']} cites {identifier}, which does not exist")
            elif identifier not in allowed:
                found.append(f"F20 {declaration['file']} cites {identifier}, which step {declaration['step']} does not prove")
    return found


def covered_identifiers(declarations: list[dict[str, Any]]) -> set[str]:
    return {identifier for declaration in declarations for identifier in declaration["covers"]}


def coverage_violations(
    plan: dict[str, Any],
    declarations: list[dict[str, Any]],
    live_scope: dict[str, Any],
    baseline: dict[str, Any],
    base_baseline: dict[str, Any] | None,
) -> list[str]:
    """F19: the ratchet. Coverage may rise, never fall; a live-scope identifier without a spec must be a recorded deferral."""
    found = []
    covered = covered_identifiers(declarations)
    covered_steps = {declaration["step"] for declaration in declarations}
    plan_steps = {step["id"] for step in plan.get("steps", [])}
    floor = float(baseline.get("plan_step_floor", 1.0))
    ratio = len(plan_steps & covered_steps) / len(plan_steps) if plan_steps else 1.0
    if ratio < floor:
        found.append(f"F19 plan-step coverage {ratio:.2f} is below the floor {floor:.2f}")
    deferred = set((live_scope.get("deferred") or {}).keys())
    baseline_deferred = set(baseline.get("deferred", []) or [])
    in_scope = {identifier for key in ("requirements", "stories", "gaps") for identifier in live_scope.get(key, []) or []}
    for identifier in sorted(in_scope - covered):
        if identifier not in deferred:
            found.append(f"F19 live-scope {identifier} has no spec and no recorded deferral")
        elif identifier not in baseline_deferred:
            found.append(f"F19 live-scope {identifier} is deferred but not accepted in coverage-baseline.yaml")
    for identifier in sorted(deferred - in_scope):
        found.append(f"F19 deferral {identifier} is not in the live scope")
    for identifier in sorted(set(baseline.get("covered", []) or []) - covered):
        found.append(f"F19 {identifier} was covered by the accepted baseline and no longer is")
    if base_baseline is not None:
        for identifier in sorted(set(base_baseline.get("covered", []) or []) - set(baseline.get("covered", []) or [])):
            found.append(f"F19 the pull request removes {identifier} from the covered baseline")
        if float(baseline.get("plan_step_floor", 1.0)) < float(base_baseline.get("plan_step_floor", 1.0)):
            found.append("F19 the pull request lowers the plan-step floor")
        for identifier in sorted(baseline_deferred - set(base_baseline.get("deferred", []) or [])):
            found.append(f"F19 the pull request adds deferral {identifier} without a spec")
    return found


def environment_profiles(root: Path) -> dict[str, Path]:
    return {path.stem: path for path in sorted((root / ENVIRONMENTS).glob("*.yaml"))}


def workflow_violations(root: Path) -> list[str]:
    """F1, F2, F3 (workflow side) and F17."""
    path = root / WORKFLOW
    if not path.exists():
        return [f"F1 {WORKFLOW} does not exist"]
    text = path.read_text(encoding="utf-8")
    document = yaml.safe_load(text)
    triggers = document.get(True, document.get("on"))
    found = []
    names = set(triggers) if isinstance(triggers, dict) else {triggers} if isinstance(triggers, str) else set(triggers or [])
    if names != {"workflow_dispatch"}:
        found.append(f"F1 workflow triggers must be only workflow_dispatch, found {sorted(map(str, names))}")
    if not (document.get("concurrency") or {}).get("group"):
        found.append("F1 workflow needs a concurrency group of one run per environment")
    for match in re.finditer(r"\$\{\{[^}]*?\bsecrets\.(?P<name>\w+)", text):
        if match.group("name") != "GITHUB_TOKEN":
            found.append(f"F2 workflow references secrets.{match.group('name')}")
    if re.search(r"secrets:\s*inherit", text):
        found.append("F2 workflow inherits secrets")
    for match in re.finditer(r"vars\.(?P<name>\w+)", text):
        if CREDENTIAL_WORD.search(match.group("name")):
            found.append(f"F2 workflow reads credential-named variable vars.{match.group('name')}")
    inputs = ((triggers or {}).get("workflow_dispatch") or {}).get("inputs", {}) if isinstance(triggers, dict) else {}
    listed = set((inputs.get("environment") or {}).get("options", []))
    profiles = set(environment_profiles(root))
    if listed != profiles:
        found.append(f"F3 workflow environment options {sorted(listed)} differ from profile files {sorted(profiles)}")
    if re.search(r"(?:inputs|event\.inputs)\.environment\s*(?:==|!=)", text):
        found.append("F3 workflow logic branches on the environment name")
    for other in sorted((root / ".github").rglob("*")):
        if other.is_file() and other != path and other.suffix in {".yaml", ".yml", ".json"}:
            if WORKFLOW_REFERENCE.search(other.read_text(encoding="utf-8", errors="ignore")):
                found.append(f"F17 {other.relative_to(root).as_posix()} references the acceptance workflow")
    validation = root / "validation"
    for other in sorted(validation.rglob("*.yaml")) if validation.exists() else []:
        if (root / ACCEPTANCE) in other.parents:
            continue
        if WORKFLOW_REFERENCE.search(other.read_text(encoding="utf-8", errors="ignore")):
            found.append(f"F17 {other.relative_to(root).as_posix()} references the acceptance workflow")
    return found


def harness_violations(root: Path) -> list[str]:
    """F3 (code side): harness code never branches on an environment name."""
    names = ENVIRONMENT_NAMES | set(environment_profiles(root))
    found = []
    for path in sorted((root / HARNESS).rglob("*.ts")):
        relative = path.relative_to(root).as_posix()
        if "/__tests__/" in relative:
            continue
        for match in ENV_COMPARISON.finditer(path.read_text(encoding="utf-8")):
            if match.group("name") in names:
                found.append(f"F3 {relative} branches on the environment name {match.group('name')}")
    return found


def load_context(root: Path) -> dict[str, Any]:
    plans = sorted((root / PLANS).glob("*.v*.yaml"))
    loaded = {path: load_yaml(path) for path in plans}
    return {
        "plans": loaded,
        "known": known_identifiers(root),
        "live_scope": load_yaml(root / ACCEPTANCE / "live-scope.yaml") or {},
        "baseline": load_yaml(root / ACCEPTANCE / "coverage-baseline.yaml") or {},
        "declarations": spec_declarations(root),
    }


def base_baseline(root: Path, ref: str | None) -> dict[str, Any] | None:
    if not ref:
        return None
    result = subprocess.run(  # noqa: S603
        ["git", "-c", "safe.directory=*", "show", f"{ref}:{(ACCEPTANCE / 'coverage-baseline.yaml').as_posix()}"],  # noqa: S607
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    return yaml.safe_load(result.stdout) if result.returncode == 0 else None


def check(root: Path, base_ref: str | None = None) -> list[str]:
    context = load_context(root)
    found: list[str] = []
    plans = list(context["plans"].items())
    all_steps: dict[str, str] = {}
    for path, plan in plans:
        found.extend(schema_violations(plan, root / ACCEPTANCE / "plan.schema.json", path.name))
        found.extend(plan_violations(plan, context["known"]))
        step_ids = {step["id"] for step in plan.get("steps", [])}
        for step_id in sorted(step_ids & set(all_steps)):
            found.append(f"F5 step {step_id} in {path.name} is already used by {all_steps[step_id]}")
        all_steps.update({step_id: path.name for step_id in step_ids})
        relevant = [declaration for declaration in context["declarations"] if declaration["step"] in step_ids]
        found.extend(spec_violations(plan, relevant, context["known"]))
    for declaration in context["declarations"]:
        if declaration["step"] not in all_steps:
            found.append(f"F20 {declaration['file']} cites plan step {declaration['step']}, which does not exist")
    if plans:
        merged = {"steps": [step for _, plan in plans for step in plan.get("steps", [])]}
        found.extend(
            coverage_violations(
                merged,
                context["declarations"],
                context["live_scope"],
                context["baseline"],
                base_baseline(root, base_ref),
            )
        )
    else:
        found.append("F5 no journey plan exists")
    profiles = environment_profiles(root)
    for name, path in profiles.items():
        profile = load_yaml(path)
        found.extend(schema_violations(profile, root / ACCEPTANCE / "environment.schema.json", path.name))
        if profile.get("environment") != name:
            found.append(f"F3 profile {path.name} declares environment {profile.get('environment')}")
        plan_ids = {plan["journey_id"] for plan in context["plans"].values()}
        for journey in profile.get("journeys", []):
            if journey not in plan_ids:
                found.append(f"F5 profile {path.name} lists journey {journey}, which has no plan")
    found.extend(workflow_violations(root))
    found.extend(harness_violations(root))
    return found


def compile_outputs(root: Path, journey: str, environment: str, out: Path) -> None:
    violations = check(root)
    if violations:
        raise SystemExit("acceptance static gates failed:\n- " + "\n- ".join(violations))
    profiles = environment_profiles(root)
    if environment not in profiles:
        raise SystemExit(f"environment {environment} has no profile")
    plan_path = next(path for path, plan in load_context(root)["plans"].items() if plan["journey_id"] == journey)
    profile = load_yaml(profiles[environment])
    if journey not in profile["journeys"]:
        raise SystemExit(f"environment {environment} does not allow journey {journey}")
    live_scope = load_yaml(root / ACCEPTANCE / "live-scope.yaml") or {}
    out.mkdir(parents=True, exist_ok=True)
    compiled = {
        "plan": load_yaml(plan_path),
        "planDigest": digest(plan_path),
        "liveScope": sorted(
            {identifier for key in ("requirements", "stories", "gaps") for identifier in live_scope.get(key, []) or []}
        ),
    }
    (out / "plan.json").write_text(json.dumps(compiled, indent=2), encoding="utf-8")
    (out / "profile.json").write_text(
        json.dumps({**profile, "profile_digest": digest(profiles[environment])}, indent=2), encoding="utf-8"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("check", "compile"):
        command = commands.add_parser(name)
        command.add_argument("--repository-root", type=Path, default=Path("."))
        if name == "check":
            command.add_argument("--base-ref", default=None)
        else:
            command.add_argument("--journey", required=True)
            command.add_argument("--environment", required=True)
            command.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args(argv)
    root = arguments.repository_root.resolve()
    if arguments.command == "check":
        violations = check(root, arguments.base_ref)
        if violations:
            print("Acceptance static gates failed:", file=sys.stderr)
            for violation in violations:
                print(f"- {violation}", file=sys.stderr)
            return 1
        print("Acceptance static gates passed")
        return 0
    compile_outputs(root, arguments.journey, arguments.environment, arguments.out)
    print("Compiled acceptance plan and profile")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
