from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yaml"


def test_c059_accepts_markdown_formatted_pr_metadata() -> None:
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")

    assert "PR_METADATA=\"$(tr -d '*_`' <<< \"$PR_BODY\")\"" in workflow
    assert "Work Contract:[[:space:]]*WC-[0-9]+" in workflow
    assert (
        "grep -qiE 'Constitutional basis(:|[[:space:]]*$)' <<< \"$PR_METADATA\""
        in workflow
    )


def test_c066_reconciles_delayed_authorization_labels() -> None:
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")

    assert "for attempt in $(seq 1 7); do" in workflow
    assert "Authorization labels not reconciled yet" in workflow
    assert 'if [ "$attempt" -lt 7 ]; then' in workflow
    assert "sleep 5" in workflow
    assert workflow.index("for attempt in $(seq 1 7); do") < workflow.index(
        'echo "PR labels: $PR_LABELS"'
    )