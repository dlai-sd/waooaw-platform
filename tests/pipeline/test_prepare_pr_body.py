from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from prepare_pr_body import prepare_body  # noqa: E402
from validate_author_review import validate_author_review  # noqa: E402


HEAD = "a" * 40


def test_prepare_body_canonicalizes_author_review_for_current_head() -> None:
    source = """## Summary

Ready for review.

## Author Review

- [ ] stale wording

**Reviewed Commit:** FULL_40_CHARACTER_HEAD_SHA
**Author Review Result:** PENDING

## Specification Compliance
Content remains.
"""

    prepared = prepare_body(source, HEAD)

    assert validate_author_review(prepared, HEAD) == []
    assert prepared.count("## Author Review") == 1
    assert "## Specification Compliance\nContent remains." in prepared


def test_prepare_body_requires_template_section() -> None:
    try:
        prepare_body("## Summary\n", HEAD)
    except ValueError as error:
        assert "Author Review" in str(error)
    else:
        raise AssertionError("missing Author Review section was accepted")
