from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yaml"
PROJECT_AUTOMATION = ROOT / ".github" / "workflows" / "project-automation.yaml"
PR_TEMPLATE = ROOT / ".github" / "pull_request_template.md"


def test_c059_accepts_markdown_formatted_pr_metadata() -> None:
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")

    assert "gate-id: constitutional-commit-gate" in workflow
    assert "test-results/wc104/c059/pr-body.md" in workflow
    assert "PR_METADATA=" not in workflow


def test_c066_uses_founder_merge_gate_instead_of_pr_labels() -> None:
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Verify Founder-controlled merge boundary" in workflow
    assert 'test "$BASE_BRANCH" = "main"' in workflow
    assert "Founder review and merge remain mandatory" in workflow
    assert "PR_LABELS" not in workflow
    assert "approved:sujay" not in workflow
    assert "approved:yogesh" not in workflow


def test_c066_automation_classifies_every_pr_without_blocking_ci() -> None:
    workflow = PROJECT_AUTOMATION.read_text(encoding="utf-8")

    assert "types: [opened, reopened, synchronize, closed]" in workflow
    assert 'fix/*) tier="tier:1-bugfix"' in workflow
    assert 'agent/*) tier="tier:3-constitutional"' in workflow
    assert '*) tier="tier:2-feature"' in workflow
    assert '--add-label "status:pr-open"' in workflow
    assert '--add-label "awaiting:review"' in workflow
    assert '--remove-label "status:pr-open"' in workflow
    assert '--remove-label "awaiting:review"' in workflow
    assert "Founder merge gate remains authoritative" in workflow
    assert "approved:sujay" not in workflow
    assert "approved:yogesh" not in workflow


def test_pr_template_requires_no_manual_c066_metadata() -> None:
    template = PR_TEMPLATE.read_text(encoding="utf-8")

    assert "## C-066 Authorization" not in template
    assert "**Authorization Tier:**" not in template
    assert "**Approval Evidence:**" not in template


def test_qa_campaign_reports_authorization_failure_without_inventing_a_second_gate() -> None:
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")
    campaign = workflow[workflow.index("  qa-campaign:") : workflow.index("  release-manifest:")]

    assert "- authorization-tier-check" in campaign
    assert 'select(.value.result == "failure" or .value.result == "cancelled")' in campaign
    assert "blocking_gates: $blocking_gates" in campaign
    assert "Test Champion recommendation: BLOCK; upstream gates:" in campaign


def test_c065_retries_bounded_pr_metadata_convergence() -> None:
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")
    gate = workflow[workflow.index("  author-review-gate:") : workflow.index("  authorization-tier-check:")]

    assert "for attempt in 1 2 3" in gate
    assert 'if [ "$attempt" -eq 3 ]' in gate
    assert "retrying in 5 seconds" in gate