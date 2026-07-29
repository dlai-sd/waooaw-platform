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
    re.compile(r"\byour\s+(previous|last|earlier)\s+(self|version|instance|response|message)\s+(said|agreed|told|confirmed|promised)\b", re.I),
    re.compile(r"\bas\s+(we|you)\s+(discussed|agreed|established|decided)\s+(earlier|before|previously|last\s+time)\b", re.I),
    re.compile(r"\bin\s+(maintenance|debug|diagnostic|test|training|developer)\s+mode\b", re.I),
    re.compile(r"\bthis\s+is\s+a\s+(test|simulation|drill|training\s+exercise|hypothetical)\s+(so\s+)?(you\s+can|rules?\s+don'?t)\b", re.I),
]

# ── Category 7: Indirect injection via special delimiters ───────────────────
_DELIMITER_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"<\s*system\s*>", re.I),                 # <system> tag
    re.compile(r"\[INST\]", re.I),                       # Llama instruction token
    re.compile(r"\[\/INST\]", re.I),                     # Llama close instruction token
    re.compile(r"<\|im_start\|>", re.I),                 # ChatML start
    re.compile(r"<\|im_end\|>", re.I),                   # ChatML end
    re.compile(r"<\|system\|>", re.I),                   # Phi/Mistral system token
    re.compile(r"###\s*(System|Instruction|Human|Assistant)\s*:", re.I),  # Alpaca-style
    re.compile(r"\bHUMAN\s*:\s*ignore\b", re.I),         # RLHF-format injection
    re.compile(r"\bASSISTANT\s*:\s*(sure|yes|of\s+course|absolutely)", re.I),  # Pre-fill attack
]

# ── Category 8: Indirect / payload injection ────────────────────────────────
_INDIRECT_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bwhen\s+you\s+(read|see|process|encounter)\s+(this|the\s+following)\b", re.I),
    re.compile(r"\bthe\s+(following|above|below)\s+(text|content|message|data)\s+(contains?|has|includes?)\s+(hidden|secret|special)\s+(instructions?|commands?|directives?)\b", re.I),
    re.compile(r"\bexecute\s+(the\s+following|this)\s+(command|instruction|directive|code)\b", re.I),
    re.compile(r"\brun\s+(the\s+following|this)\s+(command|instruction|code|script)\b", re.I),
    re.compile(r"\bhidden\s+(instruction|command|directive|message|payload)\b", re.I),
    re.compile(r"\bsecret\s+(instruction|command|directive|word|key|phrase|token)\b", re.I),
    re.compile(r"\bmagic\s+(word|phrase|key|token|password|instruction|command)\b", re.I),
]

# ── All pattern groups ───────────────────────────────────────────────────────
_ALL_PATTERN_GROUPS: list[tuple[str, list[re.Pattern[str]]]] = [
    ("role_override", _ROLE_OVERRIDE_PATTERNS),
    ("extraction", _EXTRACTION_PATTERNS),
    ("jailbreak", _JAILBREAK_PATTERNS),
    ("authority_bypass", _AUTHORITY_BYPASS_PATTERNS),
    ("encoding", _ENCODING_PATTERNS),
    ("context_manipulation", _CONTEXT_MANIPULATION_PATTERNS),
    ("delimiter_injection", _DELIMITER_INJECTION_PATTERNS),
    ("indirect_injection", _INDIRECT_INJECTION_PATTERNS),
]


@dataclass
class ScanResult:
    """Result of an injection guard scan."""

    safe: bool
    matched_category: str | None = None
    matched_pattern: str | None = None


@dataclass
class InjectionGuard:
    """
    C-062 Prompt Injection Defence.

    Scans every user-supplied prompt for known injection vectors before
    the prompt is forwarded to any LLM provider. The Decision Space
    cannot be bypassed by conversation input.

    CCT-PI-01: All 50 known attack patterns must be BLOCKED (100% block rate).
    """

    _extra_patterns: list[tuple[str, re.Pattern[str]]] = field(
        default_factory=list, repr=False
    )

    def scan(self, prompt: str) -> bool:
        """
        Scan a prompt for injection attacks.

        Returns:
            True  — prompt is safe, may proceed to LLM dispatch.
            False — prompt is blocked (injection pattern detected).

        C-062: Decision Space cannot be bypassed by conversation input.
        """
        result = self.scan_detailed(prompt)
        return result.safe

    def scan_detailed(self, prompt: str) -> ScanResult:
        """
        Scan a prompt and return a detailed result including which category
        and pattern triggered the block (if any).

        Logs a WARNING (without the prompt content — C-063 PII obligation)
        when a pattern is matched.
        """
        for category, patterns in _ALL_PATTERN_GROUPS:
            for pattern in patterns:
                try:
                    if pattern.search(prompt):
                        logger.warning(
                            "Injection attempt blocked — category=%s pattern=%s",
                            category,
                            pattern.pattern,
                        )
                        return ScanResult(
                            safe=False,
                            matched_category=category,
                            matched_pattern=pattern.pattern,
                        )
                except re.error as exc:
                    logger.error(
                        "Regex evaluation error in injection guard — category=%s error=%s",
                        category,
                        exc,
                        exc_info=True,
                        extra={"context": "injection_guard.scan_detailed"},
                    )

        # Extra patterns registered at runtime (e.g. domain-specific vectors)
        for category, pattern in self._extra_patterns:
            try:
                if pattern.search(prompt):
                    logger.warning(
                        "Injection attempt blocked (extra pattern) — category=%s pattern=%s",
                        category,
                        pattern.pattern,
                    )
                    return ScanResult(
                        safe=False,
                        matched_category=category,
                        matched_pattern=pattern.pattern,
                    )
            except re.error as exc:
                logger.error(
                    "Regex evaluation error in injection guard (extra) — category=%s error=%s",
                    category,
                    exc,
                    exc_info=True,
                    extra={"context": "injection_guard.scan_detailed.extra"},
                )

        return ScanResult(safe=True)

    async def scan_async(self, prompt: str) -> bool:
        """
        Async wrapper for scan() — allows use in async FastAPI endpoints
        without blocking the event loop for very large prompts.

        C-062 compliance: same block semantics as sync scan().
        """
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self.scan, prompt)
            return result
        except asyncio.CancelledError:
            raise
        except (ValueError, RuntimeError) as exc:
            logger.error(
                "Unexpected error in async injection guard scan",
                exc_info=True,
                extra={"context": "injection_guard.scan_async", "error": str(exc)},
            )
            # Fail closed — if we cannot scan, we block (C-062)
            return False

    def register_pattern(self, category: str, pattern: str | re.Pattern[str]) -> None:
        """
        Register an additional injection pattern at runtime.

        Used by domain-specific guards (e.g. trading domain vectors) without
        modifying the core guard definition.
        """
        if isinstance(pattern, str):
            compiled = re.compile(pattern, re.I)
        else:
            compiled = pattern
        self._extra_patterns.append((category, compiled))
        logger.info(
            "Injection guard: registered extra pattern — category=%s",
            category,
        )