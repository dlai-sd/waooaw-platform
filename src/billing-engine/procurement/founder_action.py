# Implements: <spec-path> §<section>
# constitutional_basis: C-059 (Implementation Traceability)
from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)


class FounderActionGenerator:
    """
    Idempotent Founder Action (FA) entry generator.
    Reads security/FOUNDER-ACTIONS.md, appends new FA entries under correct P0/P1/P2 sections.
    C-077: Procurement runway threshold enforcement.
    C-059: Evidence trail via logging.
    """

    FA_FILE_PATH: Path = Path(__file__).parent.parent.parent.parent / "security" / "FOUNDER-ACTIONS.md"

    @staticmethod
    def _get_next_fa_number(content: str) -> int:
        r"""
        Extract the highest FA number from the markdown table.
        Regex: r'\|\s*\*\*FA-(\d+)\*\*'
        Returns: max_number + 1 (or 1 if no FA entries found).
        """
        matches: list[str] = re.findall(r"\|\s*\*\*FA-(\d+)\*\*", content)
        if not matches:
            logger.info("No existing FA entries found; starting at FA-1")
            return 1
        max_num: int = max(int(m) for m in matches)
        return max_num + 1

    @staticmethod
    def _fa_entry_exists(
        content: str, provider: str, priority: str
    ) -> bool:
        """
        Check if an FA entry for this provider + priority already exists.
        Pattern: looks for any row containing provider name and priority level.
        Returns: True if found, False otherwise (idempotency check).
        """
        pattern: str = rf"Provider {re.escape(provider)}.*\| P{priority} \|"
        return bool(re.search(pattern, content, re.DOTALL))

    @staticmethod
    def _format_fa_row(
        fa_number: int, provider: str, days_remaining: float, priority: str
    ) -> str:
        """
        Format a new FA table row in markdown format.
        Template: | **FA-NNN** | Provider {provider} runway {days_remaining}d - replenishment required | P{n} | C-077 procurement runway | 1 hour | OPEN |
        """
        days_str: str = f"{float(days_remaining):.1f}"
        row: str = (
            f"| **FA-{fa_number}** | Provider {provider} runway {days_str}d - replenishment required "
            f"| P{priority} | C-077 procurement runway | 1 hour | OPEN |"
        )
        return row

    @staticmethod
    def _find_section_insertion_point(
        content: str, priority: str
    ) -> int:
        """
        Find the insertion point for a new FA row under the P{priority} section.
        Returns the index after the last row in that priority section.
        If section not found, returns index at end of file.
        """
        # Look for section header: ### P{priority} or similar pattern
        section_pattern: str = rf"### P{priority}"
        section_match: re.Match[str] | None = re.search(section_pattern, content)

        if not section_match:
            logger.warning("Priority section P%s not found; appending at end of file", priority)
            return len(content)

        # Find the end of this priority section (next ### or end of string)
        section_start: int = section_match.end()
        next_section: re.Match[str] | None = re.search(r"\n### ", content[section_start:])

        if next_section:
            insertion_point: int = section_start + next_section.start()
        else:
            insertion_point = len(content)

        return insertion_point

    @classmethod
    def maybe_create(
        cls,
        provider: str,
        days_remaining: float,
        priority: str,
        fa_file_path: Path | None = None,
    ) -> str | None:
        """
        Conditionally create a new FA entry in security/FOUNDER-ACTIONS.md.
        Idempotent: if an entry for this provider + priority already exists, return None.

        Args:
            provider: Provider name (e.g. "anthropic", "sarvam").
            days_remaining: Runway in days (float).
            priority: "0", "1", or "2" (string, not int).
            fa_file_path: Override path for testing (tmp_path fixture).

        Returns:
            FA number as string (e.g. "FA-42") if created; None if idempotent skip.
            Raises: FileNotFoundError if file does not exist and fa_file_path not provided.

        C-059: Logs all decisions (creation, skip, error).
        """
        if fa_file_path is None:
            fa_file_path = cls.FA_FILE_PATH

        if not fa_file_path.exists():
            logger.error(
                "Founder Actions file not found at %s",
                fa_file_path,
                extra={"provider": provider, "priority": priority},
            )
            raise FileNotFoundError(f"Founder Actions file not found: {fa_file_path}")

        try:
            content: str = fa_file_path.read_text(encoding="utf-8")
        except OSError:
            logger.error(
                "Failed to read Founder Actions file",
                exc_info=True,
                extra={"provider": provider, "priority": priority, "path": str(fa_file_path)},
            )
            raise

        # Idempotency check: if entry exists, skip creation
        if cls._fa_entry_exists(content, provider, priority):
            logger.info(
                "FA entry already exists for provider=%s priority=%s; skipping creation",
                provider,
                priority,
                extra={"provider": provider, "priority": priority},
            )
            return None

        # Compute next FA number
        next_fa_number: int = cls._get_next_fa_number(content)
        fa_number_str: str = f"FA-{next_fa_number}"

        # Format new row
        new_row: str = cls._format_fa_row(next_fa_number, provider, days_remaining, priority)

        # Find insertion point under P{priority} section
        insertion_point: int = cls._find_section_insertion_point(content, priority)

        # Insert row (before the next section or at EOF) with newline
        new_content: str = content[:insertion_point] + "\n" + new_row + content[insertion_point:]

        try:
            fa_file_path.write_text(new_content, encoding="utf-8")
        except OSError:
            logger.error(
                "Failed to write Founder Actions file",
                exc_info=True,
                extra={"provider": provider, "priority": priority, "path": str(fa_file_path)},
            )
            raise

        logger.info(
            "Created new FA entry %s for provider=%s priority=%s days_remaining=%s",
            fa_number_str,
            provider,
            priority,
            days_remaining,
            extra={"fa_number": fa_number_str, "provider": provider, "priority": priority},
        )

        return fa_number_str