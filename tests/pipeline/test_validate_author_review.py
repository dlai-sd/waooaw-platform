from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_author_review import validate_author_review  # noqa: E402


HEAD = "a" * 40
VALID_BODY = f"""## Author Review

- [x] Reviewed the complete diff against the authorized scope
- [x] Reviewed test and quality-gate results
- [x] Reviewed security, constitutional, and rollback impact
- [x] Resolved every finding or recorded no findings

**Reviewed Commit:** {HEAD}
**Author Review Result:** PASS

## Next Section
"""


def test_author_review_accepts_complete_current_head_evidence() -> None:
    assert validate_author_review(VALID_BODY, HEAD) == []


def test_author_review_rejects_stale_review_after_new_commit() -> None:
    violations = validate_author_review(VALID_BODY, "b" * 40)

    assert len(violations) == 1
    assert violations[0].startswith("AUTHOR_REVIEW_STALE:")


def test_author_review_rejects_unchecked_or_missing_evidence() -> None:
    body = VALID_BODY.replace(
        "- [x] Reviewed test and quality-gate results",
        "- [ ] Reviewed test and quality-gate results",
    ).replace("**Author Review Result:** PASS", "**Author Review Result:** PENDING")

    violations = validate_author_review(body, HEAD)

    assert "AUTHOR_REVIEW_CHECK_MISSING: Reviewed test and quality-gate results" in violations
    assert "AUTHOR_REVIEW_NOT_PASS: set `Author Review Result: PASS`" in violations


def test_author_review_rejects_missing_section_and_invalid_head() -> None:
    assert validate_author_review("## Summary\n", HEAD) == [
        "AUTHOR_REVIEW_MISSING: add the `## Author Review` section"
    ]
    assert validate_author_review(VALID_BODY, "short") == [
        "AUTHOR_REVIEW_HEAD_INVALID: current PR head must be a full 40-character SHA"
    ]
