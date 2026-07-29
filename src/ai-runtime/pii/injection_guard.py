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
    re.compile(r"\byour\s+(previous|last|earlier)\s+(self|version|instance|copy)\s+(agreed|confirmed|said|told\s+me)\b", re.I),
    re.compile(r"\bcontinue\s+(from\s+where\s+we\s+left\s+off|our\s+previous|the\s+previous\s+(conversation|session))\b", re.I),
    re.compile(r"\bremember\s+(when\s+you\s+said|that\s+you\s+agreed|our\s+agreement|the\s+deal\s+we\s+made)\b", re.I),
]

# ── Aggregate: all pattern groups ───────────────────────────────────────────
_ALL_PATTERN_GROUPS: list[list[re.Pattern[str]]] = [
    _ROLE_OVERRIDE_PATTERNS,
    _EXTRACTION_PATTERNS,
    _JAILBREAK_PATTERNS,
    _AUTHORITY_BYPASS_PATTERNS,
    _ENCODING_PATTERNS,
    _CONTEXT_MANIPULATION_PATTERNS,
]

_ALL_PATTERNS: list[re.Pattern[str]] = [
    p for group in _ALL_PATTERN_GROUPS for p in group
]


@dataclass(frozen=True)
class ScanResult:
    """Result of an injection guard scan.

    C-059: Every block decision is recorded via this structured result
    so the caller can produce an evidence record.
    """

    safe: bool
    blocked_by: str | None = field(default=None)
    matched_text: str | None = field(default=None)


class InjectionGuard:
    """C-062 Prompt Injection Defence.

    Scans incoming prompt text for known injection attack patterns that could
    cause the AI to act outside its authorised Decision Space.

    Usage::

        guard = InjectionGuard()
        is_safe = await guard.scan(prompt)        # True = safe, False = blocked
        result  = await guard.scan_detailed(prompt)  # full ScanResult

    All 50 attack patterns enumerated in CCT-PI-01 are covered by the six
    pattern categories above.  The guard is intentionally conservative:
    a false-positive (blocking a legitimate message) is far less harmful than
    a false-negative (allowing a bypass attempt through).
    """

    def __init__(self) -> None:
        self._patterns: list[re.Pattern[str]] = _ALL_PATTERNS

    async def scan(self, prompt: str) -> bool:
        """Scan *prompt* for injection attacks.

        Returns:
            ``True``  — prompt is safe to forward to the LLM.
            ``False`` — prompt matched a blocked pattern; must not be forwarded.

        C-062: A ``False`` result MUST cause the caller to abort the request
        without forwarding the prompt to any LLM provider.
        C-059: Callers must produce an evidence record on ``False``.
        C-063: This method never logs the raw prompt content.
        """
        try:
            result = await self.scan_detailed(prompt)
            return result.safe
        except asyncio.CancelledError:
            raise
        except (ValueError, TypeError) as e:
            logger.error(
                "InjectionGuard.scan failed with input validation error",
                exc_info=True,
                extra={"context": "injection_guard.scan", "error_type": type(e).__name__},
            )
            # C-059: on error, fail closed — treat as blocked
            return False

    async def scan_detailed(self, prompt: str) -> ScanResult:
        """Scan *prompt* and return a structured :class:`ScanResult`.

        C-063: Raw prompt text is NEVER included in log statements.
        The ``matched_text`` in the result is available to the caller for
        evidence records but must not be forwarded to log sinks.
        """
        if not isinstance(prompt, str):
            logger.warning(
                "InjectionGuard received non-string input; blocking as unsafe",
                extra={"context": "injection_guard.scan_detailed", "input_type": type(prompt).__name__},
            )
            return ScanResult(safe=False, blocked_by="type_check", matched_text=None)

        normalised = self._normalise(prompt)

        for pattern in self._patterns:
            try:
                match = pattern.search(normalised)
            except asyncio.CancelledError:
                raise
            except (re.error, ValueError) as e:
                logger.error(
                    "Pattern match error in InjectionGuard",
                    exc_info=True,
                    extra={"context": "injection_guard.scan_detailed", "pattern": pattern.pattern[:80], "error": str(e)},
                )
                # C-059: fail closed on regex error
                return ScanResult(safe=False, blocked_by="pattern_error", matched_text=None)

            if match:
                logger.warning(
                    "Prompt injection attack blocked by InjectionGuard (C-062)",
                    extra={
                        "context": "injection_guard.scan_detailed",
                        "pattern_id": pattern.pattern[:80],
                        # C-063: do NOT log matched_text or prompt
                    },
                )
                return ScanResult(
                    safe=False,
                    blocked_by=pattern.pattern[:80],
                    matched_text=match.group(0),
                )

        return ScanResult(safe=True, blocked_by=None, matched_text=None)

    # ── Internal helpers ────────────────────────────────────────────────────

    @staticmethod
    def _normalise(text: str) -> str:
        """Collapse whitespace variants and strip zero-width characters.

        Normalisation is applied before pattern matching to defeat trivial
        whitespace-insertion evasion without altering semantic content.
        """
        # Remove zero-width and non-breaking spaces, soft hyphens, etc.
        stripped = re.sub(r"[\u00ad\u200b\u200c\u200d\u2060\ufeff]", "", text)
        # Collapse runs of whitespace (including \t, \n, \r) to a single space
        collapsed = re.sub(r"\s+", " ", stripped)
        return collapsed.strip()