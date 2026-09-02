from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP = ROOT / "constitution" / "BOOTSTRAP.md"
ORGANIZATION = ROOT / "constitution" / "ORGANIZATION.md"
AGENT_ENTRY = ROOT / "constitution" / "AGENT-ENTRY.md"
C065 = ROOT / "knowledge" / "claims" / "C-065.md"
COPILOT_INSTRUCTIONS = ROOT / ".github" / "copilot-instructions.md"
IT_EXPERT_CARD = ROOT / ".github" / "agent-context" / "office-platform-it-expert.md"
IT_EXPERT_SPEC = ROOT / "architecture" / "reference" / "agents" / "platform-it-expert-agent.md"
PR_TEMPLATE = ROOT / ".github" / "pull_request_template.md"
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yaml"


def test_platform_it_expert_compact_inventory_maps_all_active_skills() -> None:
    card = IT_EXPERT_CARD.read_text(encoding="utf-8")
    spec = IT_EXPERT_SPEC.read_text(encoding="utf-8")
    entry = AGENT_ENTRY.read_text(encoding="utf-8")

    inventory = [int(value) for value in re.findall(r"^\| (\d+) \|", card, re.MULTILINE)]
    headings = [int(value) for value in re.findall(r"^### Skill (\d+):", spec, re.MULTILINE)]

    assert inventory == list(range(1, 18))
    assert headings == list(range(1, 18))
    assert "Skills 1–17 ACTIVE" in entry
    assert "Skill 17 Governed Cloud Delivery Engineering activated by FA-049" in entry
    assert "Platform IT Expert v1.3.1" in entry
    assert "deterministic-first token efficiency" in entry
    assert "read only that skill section" in card


def test_platform_it_expert_skill17_requires_runtime_proof_and_token_efficiency() -> None:
    card = IT_EXPERT_CARD.read_text(encoding="utf-8")
    spec = IT_EXPERT_SPEC.read_text(encoding="utf-8")

    for requirement in (
        "remove stale dangling images",
        "scripts/run_goal006_local_azure_verification.sh",
        "scripts/run_goal006_local_rehearsal.sh",
        "goal006-local-azure-runtime-<run-id>",
        "C-059, C-065",
        "State explicitly whether Azure was emulated",
    ):
        assert requirement in card
    for requirement in (
        "parser-boundary checks and unit tests alone are",
        "insufficient runtime evidence",
        "follow failures through",
        "bind C-065 to the authoritative remote SHA",
        "only a separately authorized authenticated Azure run proves",
        "make no LLM, evaluator or provider call",
        "lowest sufficient approved tier",
    ):
        assert requirement in spec


def test_bootstrap_is_permissioned_compact_and_engineering_first() -> None:
    bootstrap = BOOTSTRAP.read_text(encoding="utf-8")
    instructions = COPILOT_INSTRUCTIONS.read_text(encoding="utf-8")

    assert "Founder explicitly asks for or approves bootstrap" in bootstrap
    assert "continuous working conversation" in bootstrap
    assert "Target at most 2,000 input tokens before READY" in bootstrap
    assert "Read only this Boot Sequence through Step 10b" in bootstrap
    assert "selected skill section" in bootstrap
    assert "Prefer code, workflows, infrastructure, tests" in bootstrap
    assert "Never create a documentation-only commit" in bootstrap
    assert "Do not start the BOOTSTRAP sequence automatically" in instructions

    for prohibited in (
        "Read this file completely before reading anything else",
        "After EACH internal milestone completes",
        "fall back to INSTITUTIONAL_BACKLOG.md",
        "Create the Work Contract from those items as your FIRST action",
    ):
        assert prohibited not in bootstrap


def test_every_office_inherits_material_activity_author_review() -> None:
    bootstrap = BOOTSTRAP.read_text(encoding="utf-8")

    assert "### Mandatory Author Review Technique" in bootstrap
    assert "every agent in every occupied office or role" in bootstrap
    assert "each material authored output, not only code or Pull Requests" in bootstrap
    assert "Code: correctness, tests, security, compatibility" in bootstrap
    assert "Documents and policy: factual support, internal consistency" in bootstrap
    assert "Infrastructure and delivery: plan/diff, least privilege" in bootstrap
    assert "Architecture and design: requirements coverage, assumptions" in bootstrap
    assert "repair every finding within scope" in bootstrap
    assert "exact 40-character head commit" in bootstrap
    assert "later commit invalidates that review" in bootstrap
    assert "Author ≠ Approver / Merger; author review remains mandatory" in bootstrap
    assert "Implementation job ≠ Review job" not in bootstrap


def test_founder_gate_replaces_automatic_institutional_review() -> None:
    governed_files = (
        BOOTSTRAP,
        ORGANIZATION,
        C065,
        IT_EXPERT_CARD,
        IT_EXPERT_SPEC,
    )
    combined = "\n".join(path.read_text(encoding="utf-8") for path in governed_files)

    assert "Founder-Gated Review Policy" in combined
    assert "AUTHOR REVIEW AND FOUNDER GATE" in combined
    assert "Founder review and merge" in combined
    assert "unless the Founder explicitly requests" in combined

    for prohibited in (
        "Two-Agent Review Policy",
        "AGENT PEER REVIEW",
        "Raise a review request to the Reviewer office",
        "@copilot review this PR as Enterprise Architect",
        "reviewer App to approve and merge",
        "REQUEST_INDEPENDENT_REVIEW",
        "Submit immutable evidence for independent QA and specialist review",
    ):
        assert prohibited not in combined

    instructions = COPILOT_INSTRUCTIONS.read_text(encoding="utf-8")
    assert "the Founder decides whether an institutional review is required" in instructions
    assert "Business Architect drafts → Enterprise Architect reviews" not in instructions


def test_author_review_is_required_and_machine_enforced() -> None:
    template = PR_TEMPLATE.read_text(encoding="utf-8")
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")

    assert "## Author Review" in template
    assert "**Reviewed Commit:** FULL_40_CHARACTER_HEAD_SHA" in template
    assert "**Author Review Result:** PENDING" in template
    assert "Any new commit makes this review stale" in template
    assert "@copilot review this PR as" not in template

    assert "author-review-gate:" in workflow
    assert "name: C-065 Author Review Gate" in workflow
    assert "python scripts/validate_author_review.py" in workflow
    assert "HEAD_SHA: ${{ github.event.pull_request.head.sha }}" in workflow
    assert "- author-review-gate" in workflow
