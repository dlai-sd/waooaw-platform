"""WC-109 Stage 0 authority and baseline binding."""

import hashlib
import json
import subprocess
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "validation/evidence/wc109-baseline.json"


def git_content(commit: str, path: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout


def test_wc109_baseline_binds_authority_inventory_and_all_requirements_once() -> None:
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    merged_commit = baseline["merged_wc108_commit"]
    baseline_head = baseline["baseline_head"]

    subprocess.run(
        ["git", "merge-base", "--is-ancestor", merged_commit, baseline_head],
        cwd=ROOT,
        check=True,
    )
    for key in ("contract", "ledger"):
        path = baseline["authority"][f"{key}_path"]
        digest = hashlib.sha256(git_content(merged_commit, path)).hexdigest()
        assert digest == baseline["authority"][f"{key}_sha256"]

    catalog = yaml.safe_load(git_content(baseline_head, "validation/engineering-validation.yaml"))
    inventory = baseline["validation_inventory"]
    assert inventory["defined_gate_count"] == len(catalog["gates"])
    assert inventory["full_gate_count"] == len(catalog["full_gates"])
    assert inventory["main_full_inventory"] is catalog["main_full_inventory"] is True
    assert inventory["release_full_inventory"] is catalog["release_full_inventory"] is True
    assert inventory["selective_hosted_validation_founder_approved"] is False

    selected = [
        requirement
        for stage in baseline["implementation_order"]
        for requirement in stage["requirements"]
    ]
    assert set(selected) == {f"WC109-R{number:03d}" for number in range(1, 37)}
    assert len(selected) == len(set(selected))
    assert baseline["authority"]["ledger_result"] == "PLANNED"