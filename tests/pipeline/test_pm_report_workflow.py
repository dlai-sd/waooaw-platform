"""Contracts for the read-only Platform Delivery Report workflow."""

from pathlib import Path


WORKFLOW = Path(".github/workflows/pm-report.yaml").read_text(encoding="utf-8")
CI_WORKFLOW = Path(".github/workflows/ci.yaml").read_text(encoding="utf-8")
DEPLOY_WORKFLOW = Path(".github/workflows/deploy-demo.yaml").read_text(encoding="utf-8")


def test_pm_report_runs_after_merged_pull_requests() -> None:
    assert "pull_request:" in WORKFLOW
    assert "types: [closed]" in WORKFLOW
    assert "branches: [main]" in WORKFLOW
    assert "github.event.pull_request.merged == true" in WORKFLOW


def test_pm_report_posts_status_without_mutating_repository() -> None:
    assert "issues: write" in WORKFLOW
    assert "contents: read" in WORKFLOW
    assert "contents: write" not in WORKFLOW
    assert "Post report to Platform Status issue" in WORKFLOW
    assert 'gh issue comment "$STATUS_ISSUE"' in WORKFLOW
    assert "Update PROJECT_STATE.md delivery summary" not in WORKFLOW
    assert "git commit" not in WORKFLOW
    assert "git push" not in WORKFLOW
    assert "git add" not in WORKFLOW


def test_post_merge_reporting_cannot_invalidate_current_main_release() -> None:
    assert "push:" in CI_WORKFLOW
    assert "branches: [main]" in CI_WORKFLOW
    assert "goal006-exact-six-release-${{ github.sha }}" in CI_WORKFLOW
    assert 'latest_main_sha=$(gh api "repos/$GITHUB_REPOSITORY/git/ref/heads/main"' in DEPLOY_WORKFLOW
    assert "select(.head_sha == $sha)" in DEPLOY_WORKFLOW
    assert "git push" not in WORKFLOW
