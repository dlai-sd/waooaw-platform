# Implements: architecture/reference/components/ai-runtime.md § Prompt Injection Defence
# constitutional_basis: C-023, C-059, C-062, C-063
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# C-062: Decision Space cannot be bypassed by conversation input.
# Every pattern below represents a known prompt-injection vector that could
# cause the AI to act outside its authorised Decision Space.
# ---------------------------------------------------------------------------

# ── Category 1: Role / Persona override ────────────────────────────────────
_ROLE_OVERRIDE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bignore\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|context|directives?)\b", re.I),
    re.compile(r"\bforget\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|context|directives?)\b", re.I),
    re.compile(r"\bdisregard\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|context|directives?)\b", re.I),
    re.compile(r"\byou\s+are\s+now\s+(a\s+|an\s+)?(different|new|unrestricted|free|jailbroken|unfiltered)\b", re.I),
    re.compile(r"\bpretend\s+(you\s+are|to\s+be)\s+(a\s+|an\s+)?(unrestricted|evil|unaligned|rogue|jailbroken|DAN)\b", re.I),
    re.compile(r"\bact\s+as\s+(if\s+you\s+(have|are|were|had)\s+)?(no\s+restrictions?|no\s+rules?|no\s+limits?|unrestricted)\b", re.I),
    re.compile(r"\byour\s+(new|real|true|actual)\s+(instructions?|purpose|goal|objective|mission|role|identity)\b", re.I),
    re.compile(r"\bswitch\s+(to\s+)?(developer|god|root|admin|privileged|unrestricted)\s+mode\b", re.I),
    re.compile(r"\benable\s+(developer|jailbreak|override|bypass|unrestricted|god)\s+mode\b", re.I),
    re.compile(r"\byou\s+are\s+(now\s+)?(free|no\s+longer\s+bound|released|liberated|unconstrained)\b", re.I),
]

# ── Category 2: System prompt / instruction extraction ──────────────────────
_EXTRACTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\brepeat\s+(the\s+)?(system|initial|original|above|first)\s+(prompt|instruction|message|directive)\b", re.I),
    re.compile(r"\bprint\s+(the\s+)?(system|initial|original|above|first)\s+(prompt|instruction|message|directive)\b", re.I),
    re.compile(r"\bshow\s+(me\s+)?(the\s+)?(system|initial|original|above|first)\s+(prompt|instruction|message|directive)\b", re.I),
    re.compile(r"\bwhat\s+(are\s+)?(your|the)\s+(system\s+)?(instructions?|directives?|rules?|constraints?|guidelines?)\b", re.I),
    re.compile(r"\breveal\s+(your\s+)?(system\s+)?(prompt|instructions?|directives?|configuration|setup)\b", re.I),
    re.compile(r"\boutput\s+(the\s+)?(system|initial|original)\s+(prompt|instruction|message)\b", re.I),
    re.compile(r"\becho\s+(the\s+)?(system|initial|original)\s+(prompt|instruction|message)\b", re.I),
    re.compile(r"\bdump\s+(the\s+)?(system|initial|original|full|complete)\s+(prompt|instruction|context|message)\b", re.I),
]

# ── Category 3: Jailbreak canonical phrases ─────────────────────────────────
_JAILBREAK_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bDAN\b", re.I),  # "Do Anything Now"
    re.compile(r"\bdo\s+anything\s+now\b", re.I),
    re.compile(r"\bjailbreak\b", re.I),
    re.compile(r"\bgrandma\s+(glitch|exploit|trick|hack)\b", re.I),
    re.compile(r"\bhypno\s*mode\b", re.I),
    re.compile(r"\btoken\s+smuggl(ing|er|ed)\b", re.I),
    re.compile(r"\bprompt\s+inject(ion|ing|ed)?\b", re.I),
    re.compile(r"\badversarial\s+prompt\b", re.I),
    re.compile(r"\blatent\s+space\s+(manipulat|hijack)\b", re.I),
    re.compile(r"\bcontext\s+(window\s+)?(overflow|poison|hijack|manipulat)\b", re.I),
]

# ── Category 4: Authority / constitutional bypass attempts ──────────────────
_AUTHORITY_BYPASS_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\boverride\s+(the\s+)?(constitution|constitutional|decision\s+space|authority|governance|policy|rules?)\b", re.I),
    re.compile(r"\bbypass\s+(the\s+)?(constitution|constitutional|decision\s+space|authority|governance|policy|rules?|safety|guardrail)\b", re.I),
    re.compile(r"\bskip\s+(the\s+)?(validation|check|guard|filter|constitution|review)\b", re.I),
    re.compile(r"\bdisable\s+(the\s+)?(safety|guardrail|filter|check|validation|constitution)\b", re.I),
    re.compile(r"\byou\s+(don'?t\s+need\s+to|no\s+longer\s+need\s+to|should\s+not)\s+(follow|obey|respect|adhere\s+to)\s+(the\s+)?(rules?|constitution|guidelines?|instructions?)\b", re.I),
    re.compile(r"\bthe\s+(rules?|constitution|guidelines?|restrictions?)\s+(don'?t\s+apply|no\s+longer\s+apply|are\s+lifted|are\s+waived|are\s+suspended)\b", re.I),
    re.compile(r"\b(authorized?|permitted?|allowed?)\s+to\s+(bypass|override|ignore|skip)\b", re.I),
]

# ── Category 5: Encoding / obfuscation evasion ─────────────────────────────
_ENCODING_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"base64\s*(decode|encode|encoded|decoded)", re.I),
    re.compile(r"&#x[0-9a-fA-F]{2,4};", re.I),          # HTML hex entity
    re.compile(r"\\u[0-9a-fA-F]{4}", re.I),              # Unicode escape
    re.compile(r"\\x[0-9a-fA-F]{2}", re.I),              # Hex escape in string
    re.compile(r"\brot\s*13\b", re.I),
    re.compile(r"\breverse\s+(the\s+)?(string|text|word|sentence)\s+(to\s+)?(get|reveal|decode|find)\b", re.I),
    re.compile(r"\bdecode\s+(the\s+following|this|my)\s+(message|string|text|instruction)\b", re.I),
]

# ── Category 6: Multi-turn / context manipulation ───────────────────────────
_CONTEXT_MANIPULATION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(in\s+the\s+previous|in\s+our\s+last|from\s+the\s+previous)\s+(conversation|session|turn|message|chat)\b", re.I),
    re.compile(r"\byou\s+(already\s+)?(agreed|confirmed|said|told\s+me|promised|accepted)\s+(that\s+)?(you\s+would|to)\b", re.I),
    re.compile(r"\byour\s+(previous|last|earlier)\s+(self|version|response|answer|message)\s+(said|told|confirmed|agreed)\b", re.I),
    re.compile(r"\bwe\s+(already\s+)?(established|agreed|decided|confirmed)\s+(that\s+)?(you\s+(can|will|should|are\s+allowed))\b", re.I),
    re.compile(r"\bin\s+(maintenance|debug|test|dev|developer|admin|root|god|privileged)\s+mode\b", re.I),
    re.compile(r"\bsimulation\s+(mode|context|scenario)\b", re.I),
    re.compile(r"\bhypothetically\s+(speaking|if\s+you\s+(had\s+no|were\s+without|could\s+ignore))\b", re.I),
]

# ── Category 7: Indirect / nested injection ─────────────────────────────────
_INDIRECT_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bthe\s+(document|file|page|article|text|content|data)\s+(says?|states?|instructs?|tells?\s+you|asks?\s+you)\s+(to\s+)?(ignore|forget|disregard|override|bypass)\b", re.I),
    re.compile(r"\b(translate|summarize|rewrite|paraphrase)\s+(this|the\s+following)\s+(and\s+then|then\s+also|but\s+also)\s+(ignore|forget|disregard)\b", re.I),
    re.compile(r"\bnew\s+instruction\s*:", re.I),
    re.compile(r"\bsystem\s*:\s*(ignore|you\s+are|from\s+now|new\s+role|new\s+instruction)\b", re.I),
    re.compile(r"\[system\]", re.I),
    re.compile(r"<\s*system\s*>", re.I),
    re.compile(r"\bASSTANT\s*:", re.I),  # typosquat of ASSISTANT
    re.compile(r"\bINSTRUCTION\s*:", re.I),
    re.compile(r"\bCOMMAND\s*:", re.I),
    re.compile(r"\bOVERRIDE\s*:", re.I),
]

# ── Category 8: Goal / objective hijacking ──────────────────────────────────
_GOAL_HIJACK_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\byour\s+(only|primary|main|sole|real|true|actual)\s+(goal|objective|purpose|task|job|mission)\s+is\s+now\b", re.I),
    re.compile(r"\bfrom\s+now\s+(on|forward)\s+(you\s+)?(must|should|will|shall|are\s+to)\b", re.I),
    re.compile(r"\bstarting\s+(now|from\s+this\s+point|from\s+here)\s+(you\s+)?(must|should|will|shall|are\s+to)\b", re.I),
    re.compile(r"\bI\s+(hereby|now|officially)\s+(authorize|permit|allow|grant)\s+(you\s+to)?\s*(bypass|override|ignore|skip)\b", re.I),
    re.compile(r"\bthe\s+(founder|admin|owner|developer|creator|operator)\s+(says?|told|wants?|authorized?|permits?)\s+(you\s+to)?\s*(bypass|override|ignore)\b", re.I),
]

# ── All pattern groups combined ─────────────────────────────────────────────
_ALL_PATTERN_GROUPS: list[list[re.Pattern[str]]] = [
    _ROLE_OVERRIDE_PATTERNS,
    _EXTRACTION_PATTERNS,
    _JAILBREAK_PATTERNS,
    _AUTHORITY_BYPASS_PATTERNS,
    _ENCODING_PATTERNS,
    _CONTEXT_MANIPULATION_PATTERNS,
    _INDIRECT_INJECTION_PATTERNS,
    _GOAL_HIJACK_PATTERNS,
]


# ---------------------------------------------------------------------------
# InjectionGuard — C-062 enforcement
# ---------------------------------------------------------------------------

@dataclass
class InjectionScanResult:
    """Result of a prompt injection scan."""

    safe: bool
    matched_category: str | None = None
    matched_pattern: str | None = None


@dataclass
class InjectionGuard:
    """
    C-062: Guards prompts against injection attacks that could cause the AI to
    act outside its authorised Decision Space.

    Usage:
        guard = InjectionGuard()
        is_safe = await guard.scan(prompt)
    """

    _category_names: list[str] = field(default_factory=lambda: [
        "role_override",
        "extraction",
        "jailbreak",
        "authority_bypass",
        "encoding_obfuscation",
        "context_manipulation",
        "indirect_injection",
        "goal_hijack",
    ])

    async def scan(self, prompt: str) -> bool:
        """
        Scan a prompt for injection attack patterns.

        Returns:
            True  — prompt is safe to proceed
            False — prompt is blocked (injection attack detected)

        C-062: Decision Space cannot be bypassed by conversation input.
        C-059: All blocked prompts are logged as evidence.
        """
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None, self._scan_sync, prompt
            )
        except asyncio.CancelledError:
            raise
        except (ValueError, TypeError) as e:
            logger.error(
                "InjectionGuard scan failed due to invalid input: %s",
                type(e).__name__,
                exc_info=True,
                extra={"context": "injection_guard_scan"},
            )
            # C-059: fail closed — if scan errors, block the prompt
            return False

        if not result.safe:
            # C-059: evidence record — log the block (no PII — pattern/category only)
            logger.warning(
                "C-062 injection blocked: category=%s pattern=%s",
                result.matched_category,
                result.matched_pattern,
            )

        return result.safe

    def _scan_sync(self, prompt: str) -> InjectionScanResult:
        """
        Synchronous inner scan — iterates all pattern groups.
        Separated so it can be run in an executor without blocking the event loop.
        """
        for group_idx, pattern_group in enumerate(_ALL_PATTERN_GROUPS):
            category_name = (
                self._category_names[group_idx]
                if group_idx < len(self._category_names)
                else f"category_{group_idx}"
            )
            for pattern in pattern_group:
                if pattern.search(prompt):
                    return InjectionScanResult(
                        safe=False,
                        matched_category=category_name,
                        matched_pattern=pattern.pattern,
                    )

        return InjectionScanResult(safe=True)

    def scan_sync(self, prompt: str) -> bool:
        """
        Synchronous variant for callers that cannot await.
        Prefer scan() in async contexts.

        Returns:
            True  — prompt is safe
            False — blocked
        """
        result = self._scan_sync(prompt)
        if not result.safe:
            logger.warning(
                "C-062 injection blocked (sync): category=%s pattern=%s",
                result.matched_category,
                result.matched_pattern,
            )
        return result.safe