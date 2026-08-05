# Implements: <spec-path> §<section>
# constitutional_basis: C-059 (Implementation Traceability)
from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from procurement.founder_action import FounderActionGenerator

logger = logging.getLogger(__name__)


@pytest.fixture
def tmp_fa_file(tmp_path: Path) -> Path:
    """
    Fixture: create a temporary FOUNDER-ACTIONS.md file for testing.
    Initializes with basic P0/P1/P2 sections and one example FA entry.

    Args:
        tmp_path: pytest tmp_path fixture (auto-provided).

    Returns:
        Path to the temporary FA file.

    Constitutional basis:
    - C-059: Testing evidence trail (FA file mutations logged).
    """
    fa_file = tmp_path / "FOUNDER-ACTIONS.md"
    fa_file.write_text(
        "# Founder Actions\n\n"
        "## P0 (Critical -- 7 days runway)\n\n"
        "| **FA Number** | Description | Priority | Basis | SLA | Status |\n"
        "|---|---|---|---|---|---|\n"
        "| **FA-1** | Provider anthropic runway 5.0d - replenishment required | P0 | C-077 procurement runway | 1 hour | OPEN |\n\n"
        "## P1 (High -- 14 days runway)\n\n"
        "| **FA Number** | Description | Priority | Basis | SLA | Status |\n"
        "|---|---|---|---|---|---|\n\n"
        "## P2 (Medium -- 30 days runway)\n\n"
        "| **FA Number** | Description | Priority | Basis | SLA | Status |\n"
        "|---|---|---|---|---|---|\n",
        encoding="utf-8",
    )
    return fa_file


class TestFounderActionGeneratorGetNextFANumber:
    """Test suite: FounderActionGenerator._get_next_fa_number()."""

    def test_get_next_fa_number_with_existing_entries(self) -> None:
        """
        Happy path: extract max FA number and return next.
        Input: content with FA-1, FA-5, FA-3.
        Expected: return 6.
        """
        content = (
            "| **FA-1** | desc | P0 |\n"
            "| **FA-5** | desc | P1 |\n"
            "| **FA-3** | desc | P2 |\n"
        )
        result = FounderActionGenerator._get_next_fa_number(content)
        assert result == 6

    def test_get_next_fa_number_no_entries(self) -> None:
        """
        Edge case: no FA entries in content.
        Expected: return 1 (start at FA-1).
        """
        content = "# Founder Actions\n\nNo FA entries here.\n"
        result = FounderActionGenerator._get_next_fa_number(content)
        assert result == 1

    def test_get_next_fa_number_single_entry(self) -> None:
        """
        Edge case: only one FA entry (FA-42).
        Expected: return 43.
        """
        content = "| **FA-42** | Some action | P0 |\n"
        result = FounderActionGenerator._get_next_fa_number(content)
        assert result == 43


class TestFounderActionGeneratorFAEntryExists:
    """Test suite: FounderActionGenerator._fa_entry_exists()."""

    def test_fa_entry_exists_found(self) -> None:
        """
        Happy path: entry for provider + priority exists.
        Input: content with "Provider anthropic" and "| P0 |".
        Expected: return True.
        """
        content = (
            "| **FA-1** | Provider anthropic runway 5.0d - replenishment required "
            "| P0 | C-077 procurement runway | 1 hour | OPEN |\n"
        )
        result = FounderActionGenerator._fa_entry_exists(content, "anthropic", "0")
        assert result is True

    def test_fa_entry_exists_not_found(self) -> None:
        """
        Happy path: entry for provider + priority does NOT exist.
        Input: content with "Provider sarvam" but no "P2".
        Expected: return False.
        """
        content = (
            "| **FA-1** | Provider anthropic runway 5.0d - replenishment required "
            "| P0 | C-077 procurement runway | 1 hour | OPEN |\n"
        )
        result = FounderActionGenerator._fa_entry_exists(content, "sarvam", "2")
        assert result is False

    def test_fa_entry_exists_case_sensitive(self) -> None:
        """
        Edge case: provider name is case-sensitive.
        Input: content has "Provider Anthropic" (capitalized).
        Expected: return False when searching for "anthropic" (lowercase).
        """
        content = (
            "| **FA-1** | Provider Anthropic runway 5.0d - replenishment required "
            "| P0 | C-077 procurement runway | 1 hour | OPEN |\n"
        )
        result = FounderActionGenerator._fa_entry_exists(content, "anthropic", "0")
        assert result is False

    def test_fa_entry_exists_different_priority(self) -> None:
        """
        Edge case: same provider exists with P0, but we search for P1.
        Input: "Provider sarvam" + "P0".
        Expected: return False when searching for "sarvam" + "P1".
        """
        content = (
            "| **FA-2** | Provider sarvam runway 10.0d - replenishment required "
            "| P0 | C-077 procurement runway | 1 hour | OPEN |\n"
        )
        result = FounderActionGenerator._fa_entry_exists(content, "sarvam", "1")
        assert result is False


class TestFounderActionGeneratorFormatFARow:
    """Test suite: FounderActionGenerator._format_fa_row()."""

    def test_format_fa_row_integer_days(self) -> None:
        """
        Happy path: format row with integer days_remaining.
        Expected: row contains "FA-42", provider name, days in X.0 format, priority P1.
        """
        row = FounderActionGenerator._format_fa_row(42, "anthropic", 10, "1")
        assert "**FA-42**" in row
        assert "Provider anthropic" in row
        assert "10.0d" in row
        assert "| P1 |" in row
        assert "C-077 procurement runway" in row
        assert "OPEN" in row

    def test_format_fa_row_float_days(self) -> None:
        """
        Happy path: format row with float days_remaining (e.g., 12.5).
        Expected: row contains "12.5d" (one decimal place).
        """
        row = FounderActionGenerator._format_fa_row(99, "sarvam", 12.5, "2")
        assert "**FA-99**" in row
        assert "Provider sarvam" in row
        assert "12.5d" in row
        assert "| P2 |" in row

    def test_format_fa_row_zero_days(self) -> None:
        """
        Edge case: days_remaining = 0.0 (critical).
        Expected: row contains "0.0d".
        """
        row = FounderActionGenerator._format_fa_row(5, "google", 0.0, "0")
        assert "**FA-5**" in row
        assert "0.0d" in row
        assert "| P0 |" in row


class TestFounderActionGeneratorFindSectionInsertionPoint:
    """Test suite: FounderActionGenerator._find_section_insertion_point()."""

    def test_find_section_insertion_point_p0(self) -> None:
        """
        Happy path: find insertion point for P0 section.
        Input: content with ### P0 header and P1 section after.
        Expected: return index just before ### P1.
        """
        content = (
            "# Header\n"
            "### P0\n"
            "Some P0 entries\n"
            "### P1\n"
            "Some P1 entries\n"
        )
        point = FounderActionGenerator._find_section_insertion_point(content, "0")
        # Should be before "### P1"
        assert content[point:point + 7] == "### P1"

    def test_find_section_insertion_point_p2_at_end(self) -> None:
        """
        Edge case: P2 is the last section (no next ### after).
        Expected: return len(content).
        """
        content = (
            "# Header\n"
            "### P0\n"
            "P0 content\n"
            "### P2\n"
            "P2 content\n"
        )
        point = FounderActionGenerator._find_section_insertion_point(content, "2")
        assert point == len(content)

    def test_find_section_insertion_point_missing_section(self) -> None:
        """
        Edge case: section not found (e.g., ### P1 does not exist).
        Expected: return len(content) (append at end).
        """
        content = "# Header\n### P0\nContent\n"
        point = FounderActionGenerator._find_section_insertion_point(content, "2")
        assert point == len(content)


class TestFounderActionGeneratorMaybeCreate:
    """Test suite: FounderActionGenerator.maybe_create()."""

    def test_maybe_create_new_entry_p0(self, tmp_fa_file: Path) -> None:
        """
        Happy path: create new FA entry for P0 priority.
        Pre-condition: tmp_fa_file has no entry for "sarvam" + "P0".
        Expected: returns "FA-2", file is updated with new row.
        """
        fa_num = FounderActionGenerator.maybe_create(
            provider="sarvam",
            days_remaining=6.5,
            priority="0",
            fa_file_path=tmp_fa_file,
        )
        assert fa_num == "FA-2"
        content = tmp_fa_file.read_text(encoding="utf-8")
        assert "Provider sarvam" in content
        assert "6.5d" in content
        assert "| P0 |" in content

    def test_maybe_create_idempotent_skip(self, tmp_fa_file: Path) -> None:
        """
        Idempotency: second call with same provider + priority returns None, no duplicate.
        Pre-condition: tmp_fa_file already has "Provider anthropic" + "P0".
        Expected: returns None, file unchanged.
        """
        first_call = FounderActionGenerator.maybe_create(
            provider="anthropic",
            days_remaining=5.0,
            priority="0",
            fa_file_path=tmp_fa_file,
        )
        assert first_call is None  # Already exists

        content_after = tmp_fa_file.read_text(encoding="utf-8")
        # Count occurrences of "Provider anthropic" + "P0" in the file
        fa_lines = [
            line for line in content_after.split("\n")
            if "Provider anthropic" in line and "| P0 |" in line
        ]
        assert len(fa_lines) == 1  # Exactly one entry, no duplicate

    def test_maybe_create_different_priority_same_provider(
        self, tmp_fa_file: Path
    ) -> None:
        """
        Same provider, different priority: both entries should exist.
        Pre-condition: tmp_fa_file has "Provider anthropic" + "P0".
        Action: create "Provider anthropic" + "P1".
        Expected: returns "FA-2", both P0 and P1 entries exist.
        """
        fa_num = FounderActionGenerator.maybe_create(
            provider="anthropic",
            days_remaining=14.0,
            priority="1",
            fa_file_path=tmp_fa_file,
        )
        assert fa_num == "FA-2"

        content = tmp_fa_file.read_text(encoding="utf-8")
        p0_lines = [
            line for line in content.split("\n")
            if "Provider anthropic" in line and "| P0 |" in line
        ]
        p1_lines = [
            line for line in content.split("\n")
            if "Provider anthropic" in line and "| P1 |" in line
        ]
        assert len(p0_lines) == 1
        assert len(p1_lines) == 1

    def test_maybe_create_file_not_found(self, tmp_path: Path) -> None:
        """
        Error case: fa_file_path does not exist.
        Expected: raises FileNotFoundError.
        """
        nonexistent_file = tmp_path / "nonexistent.md"
        with pytest.raises(FileNotFoundError):
            FounderActionGenerator.maybe_create(
                provider="anthropic",
                days_remaining=5.0,
                priority="0",
                fa_file_path=nonexistent_file,
            )

    def test_maybe_create_file_read_error(self, tmp_path: Path) -> None:
        """
        Error case: file exists but is not readable (permission denied).
        Expected: raises OSError.
        """
        fa_file = tmp_path / "FOUNDER-ACTIONS.md"
        fa_file.write_text("# Test\n", encoding="utf-8")
        fa_file.chmod(0o000)

        try:
            with pytest.raises(OSError):
                FounderActionGenerator.maybe_create(
                    provider="anthropic",
                    days_remaining=5.0,
                    priority="0",
                    fa_file_path=fa_file,
                )
        finally:
            fa_file.chmod(0o644)

    def test_maybe_create_multiple_entries_incrementing_numbers(
        self, tmp_fa_file: Path
    ) -> None:
        """
        Happy path: create multiple FA entries; each increments FA number correctly.
        Pre-condition: tmp_fa_file has FA-1.
        Action: create three new entries.
        Expected: returns "FA-2", "FA-3", "FA-4" in sequence.
        """
        fa_2 = FounderActionGenerator.maybe_create(
            provider="sarvam",
            days_remaining=20.0,
            priority="1",
            fa_file_path=tmp_fa_file,
        )
        assert fa_2 == "FA-2"

        fa_3 = FounderActionGenerator.maybe_create(
            provider="google",
            days_remaining=8.0,
            priority="0",
            fa_file_path=tmp_fa_file,
        )
        assert fa_3 == "FA-3"

        fa_4 = FounderActionGenerator.maybe_create(
            provider="azure",
            days_remaining=25.0,
            priority="2",
            fa_file_path=tmp_fa_file,
        )
        assert fa_4 == "FA-4"

        content = tmp_fa_file.read_text(encoding="utf-8")
        assert "**FA-2**" in content
        assert "**FA-3**" in content
        assert "**FA-4**" in content

    def test_maybe_create_uses_default_path_when_not_provided(
        self, tmp_path: Path
    ) -> None:
        """
        Default path behavior: when fa_file_path is None, constructor sets FA_FILE_PATH.
        Note: This test verifies the constructor path is checked; actual file may not exist.
        Expected: raises FileNotFoundError (since real FA_FILE_PATH likely doesn't exist in test env).
        """
        with pytest.raises(FileNotFoundError):
            FounderActionGenerator.maybe_create(
                provider="anthropic",
                days_remaining=5.0,
                priority="0",
                fa_file_path=None,
            )

    def test_maybe_create_preserves_existing_content(self, tmp_fa_file: Path) -> None:
        """
        Content preservation: creating a new entry preserves all existing entries.
        Pre-condition: tmp_fa_file has header, P0/P1/P2 sections, and FA-1.
        Action: create new FA-2.
        Expected: FA-1 still present, header unchanged, all sections intact.
        """
        original_content = tmp_fa_file.read_text(encoding="utf-8")
        assert "| **FA-1**" in original_content
        assert "## P0" in original_content

        _fa_num = FounderActionGenerator.maybe_create(
            provider="sarvam",
            days_remaining=15.0,
            priority="1",
            fa_file_path=tmp_fa_file,
        )

        new_content = tmp_fa_file.read_text(encoding="utf-8")
        assert "| **FA-1**" in new_content
        assert "## P0" in new_content
        assert "Provider sarvam" in new_content

    def test_maybe_create_logging_on_creation(
        self, tmp_fa_file: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """
        Constitutional basis C-059: verify logging on successful creation.
        Expected: logger.info contains "Created new FA entry", provider, priority.
        """
        with caplog.at_level(logging.INFO):
            fa_num = FounderActionGenerator.maybe_create(
                provider="ollama",
                days_remaining=22.0,
                priority="1",
                fa_file_path=tmp_fa_file,
            )

        assert fa_num == "FA-2"
        assert "Created new FA entry" in caplog.text
        assert "ollama" in caplog.text
        assert "priority=1" in caplog.text

    def test_maybe_create_logging_on_idempotent_skip(
        self, tmp_fa_file: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """
        Constitutional basis C-059: verify logging on idempotent skip.
        Expected: logger.info contains "already exists", provider, priority.
        """
        with caplog.at_level(logging.INFO):
            fa_num = FounderActionGenerator.maybe_create(
                provider="anthropic",
                days_remaining=5.0,
                priority="0",
                fa_file_path=tmp_fa_file,
            )

        assert fa_num is None
        assert "already exists" in caplog.text
        assert "anthropic" in caplog.text