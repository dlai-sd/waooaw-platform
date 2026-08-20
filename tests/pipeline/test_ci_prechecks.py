from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yaml"


def test_c059_accepts_markdown_formatted_pr_metadata() -> None:
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")

    assert "python scripts/validate_c059.py" in workflow
    assert "--pr-body-file /tmp/pr-body.md" in workflow
    assert "PR_METADATA=" not in workflow


def test_c066_reconciles_delayed_authorization_labels() -> None:
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")

    assert "for attempt in $(seq 1 7); do" in workflow
    assert "Authorization labels not reconciled yet" in workflow
    assert 'if [ "$attempt" -lt 7 ]; then' in workflow
    assert "sleep 5" in workflow
    assert workflow.index("for attempt in $(seq 1 7); do") < workflow.index(
        'echo "PR labels: $PR_LABELS"'
    )