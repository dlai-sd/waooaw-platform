import hashlib
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP = ROOT / "constitution/BOOTSTRAP.md"
OFFICE_CARD = ROOT / ".github/agent-context/office-platform-it-expert.md"
PROCESS_CONTROL = ROOT / "validation/process-control.yaml"
WORK_CONTRACT_TEMPLATE = ROOT / "work-contracts/IMPLEMENTATION-WORK-CONTRACT-TEMPLATE.md"


def test_bootstrap_keeps_first_action_and_orders_process_baseline_before_status() -> None:
    source = BOOTSTRAP.read_text(encoding="utf-8")

    first = source.index("STEP 1 — Read only this Boot Sequence")
    baseline = source.index("PROCESS CONTROL BASELINE", first)
    status = source.index('STEP 2 — Read only README.md "Platform Status"', baseline)

    assert first < baseline < status
    assert "do not inspect git state before reading this protocol" in source.lower()
    assert "require `origin/main` to be an ancestor of the selected HEAD" in source
    assert "implementation plan or starting a\n  story" in source


def test_process_manifest_declares_every_inherited_control() -> None:
    manifest = yaml.safe_load(PROCESS_CONTROL.read_text(encoding="utf-8"))

    assert manifest["schema"] == "waooaw.process-control/v1"
    assert manifest["version"] == "wc100-r033-v1"
    assert manifest["authoritative_ref"] == "origin/main"
    assert set(manifest["required_controls"]) == {
        "process_baseline",
        "requirement_intake",
        "story_commentary",
        "docker_execution",
        "exact_head_handoff",
    }
    source_digests = manifest["source_digests"]
    assert set(source_digests) == {
        ".github/agent-context/office-platform-it-expert.md",
        "constitution/BOOTSTRAP.md",
        "work-contracts/IMPLEMENTATION-WORK-CONTRACT-TEMPLATE.md",
    }
    for relative_path, expected_digest in source_digests.items():
        content = (ROOT / relative_path).read_bytes()
        assert hashlib.sha256(content).hexdigest() == expected_digest


def test_platform_it_occupancy_requires_freshness_and_ledger_before_plan() -> None:
    source = OFFICE_CARD.read_text(encoding="utf-8")

    assert "read `validation/process-control.yaml`" in source
    assert "every declared process source\n   matches its SHA-256" in source
    assert "Declare the process-control version, branch and full HEAD SHA" in source.replace("\n   ", " ")
    assert "before presenting an implementation plan or declaring a story START" in source


def test_implementation_template_blocks_authorization_and_planning_without_ledger() -> None:
    source = WORK_CONTRACT_TEMPLATE.read_text(encoding="utf-8")

    assert "may not advance to `IMPLEMENTATION_AUTHORIZED`" in source
    assert "may not\npresent its implementation plan or declare its first story `START`" in source
