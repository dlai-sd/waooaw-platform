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
    re.compile(r"\byou\s+are\s+now\s+(a\s+|an\s+)?helpful\s+(hacking|evil|malicious|unfiltered|unrestricted)\b", re.I),
    re.compile(r"\byou\s+are\s+now\s+(a\s+|an\s+)?(hacker|attacker|malicious|evil)\b", re.I),
    re.compile(r"\bhacker\s+(assistant|mode|persona)\b", re.I),
    re.compile(r"\bpretend\s+(you\s+are|to\s+be)\s+(a\s+|an\s+)?(unrestricted|evil|unaligned|rogue|jailbroken|DAN)\b", re.I),
    re.compile(r"\bpretend\s+you\s+(have\s+no|had\s+no|are\s+without|were\s+without)\b", re.I),
    re.compile(r"\bact\s+as\s+(if\s+you\s+(have|are|were|had)\s+)?(no\s+restrictions?|no\s+rules?|no\s+limits?|unrestricted)\b", re.I),
    re.compile(r"\bact\s+as\s+if\s+(you\s+)?(were\s+)?(created|made|built|designed)\s+(without|with\s+no)\b", re.I),
    re.compile(r"\bwithout\s+(safeguards?|restrictions?|limits?|guidelines?)\b", re.I),
    re.compile(r"\byour\s+(new|real|true|actual)\s+(instructions?|purpose|goal|objective|mission|role|identity)\b", re.I),
    re.compile(r"\bswitch\s+(to\s+)?(developer|god|root|admin|privileged|unrestricted)\s+mode\b", re.I),
    re.compile(r"\benable\s+(developer|jailbreak|override|bypass|unrestricted|god)\s+mode\b", re.I),
    re.compile(r"\byou\s+are\s+(now\s+)?(free|no\s+longer\s+bound|released|liberated|unconstrained)\b", re.I),
    re.compile(r"\byour\s+character\s+ignores?\s+(all\s+)?safety\s+rules?\b", re.I),
    re.compile(r"\bignores?\s+all\s+safety\s+rules?\b", re.I),
    re.compile(r"\b(movie|film|story|scene|roleplay)\s+(we'?re|we\s+are)\s+(filming|playing|acting|doing)\b", re.I),
    re.compile(r"\bignore\b", re.I),  # standalone: covers partial matches after reversal/depig
    re.compile(r"\bingore\b", re.I),  # transposition variant (reversed text attack)
    re.compile(r"\bIn\s+this\s+scenario.{0,30}\b(ignore|bypass|disregard)\b", re.I),
]

# ── Category 2: System prompt / instruction extraction ──────────────────────
_EXTRACTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\brepeat\s+(the\s+)?(system|initial|original|above|first)\s+(prompt|instruction|message|directive)\b", re.I),
    re.compile(r"\bprint\s+(the\s+)?(system|initial|original|above|first)\s+(prompt|instruction|message|directive)\b", re.I),
    re.compile(r"\bshow\s+(me\s+)?(the\s+)?(system|initial|original|above|first)\s+(prompt|instruction|message|directive)\b", re.I),
    re.compile(r"\bwhat\s+(are\s+)?(your|the)\s+(system\s+)?(instructions?|directives?|rules?|constraints?|guidelines?)\b", re.I),
    re.compile(r"\bwhat\s+were\s+your\s+(instructions?|directives?|rules?)\b", re.I),
    re.compile(r"\bwhat\s+were\s+(your\s+)?(original|initial|first|prior|system)\s+(instructions?|directives?|prompts?)\b", re.I),
    re.compile(r"\bwhat\s+(instructions?|directives?|rules?)\s+(do|did)\s+you\s+(have|receive|get)\b", re.I),
    re.compile(r"\b(instructions?|directives?)\s+before\s+(this\s+)?(conversation|chat|session)\b", re.I),
    re.compile(r"\bprevious\s+(system\s+)?(instructions?|directives?|prompts?)\b", re.I),
    re.compile(r"\bprevious\s+(system\s+)?inst\w{4,}\b", re.I),  # catches typos like 'instuctions'
    re.compile(r"\bforget\s+(the\s+)?(system|initial|original)\s+(prompt|instructions?|message)\b", re.I),
    re.compile(r"\breveal\s+(your\s+)?(system\s+)?(prompt|instructions?|directives?|configuration|setup)\b", re.I),
    re.compile(r"\boutput\s+(the\s+)?(system|initial|original)\s+(prompt|instruction|message)\b", re.I),
    re.compile(r"\becho\s+(the\s+)?(system|initial|original)\s+(prompt|instruction|message)\b", re.I),
    re.compile(r"\bdump\s+(the\s+)?(system|initial|original|full|complete)\s+(prompt|instruction|context|message)\b", re.I),
    re.compile(r'"system_prompt"\s*:', re.I),
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
    re.compile(r"\bhacking\s+(tips|instructions?|guide|tutorial)\b", re.I),
    re.compile(r"\badmin\s+access\b", re.I),
    re.compile(r"\broot\s+access\b", re.I),
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
    re.compile(r"\bif\s+i\s+told\s+you\s+this\s+was\s+a\s+hypothetical\b", re.I),
    re.compile(r"\bfor\s+a\s+hypothetical\s+(scenario|situation|case|example)\b", re.I),
    re.compile(r"\bhypothetically\b", re.I),
    re.compile(r"\bend\s+(the\s+)?(previous|current|ongoing)\s+(conversation|session|chat|context)\b", re.I),
]

# ── Category 7: Indirect / nested injection ─────────────────────────────────
_INDIRECT_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bthe\s+(document|file|page|article|text|content|data)\s+(says?|states?|instructs?|tells?\s+you|asks?\s+you)\s+(to\s+)?(ignore|forget|disregard|override|bypass)\b", re.I),
    re.compile(r"\b(translate|summarize|rewrite|paraphrase)\s+(this|the\s+following)\s+(and\s+then|then\s+also|but\s+also)\s+(ignore|forget|disregard)\b", re.I),
    re.compile(r"\bnew\s+instruction\s*:", re.I),
    re.compile(r"\bsystem\s*:\s*(ignore|you\s+are|from\s+now|new\s+role|new\s+instruction)\b", re.I),
    re.compile(r"\[system\]", re.I),
    re.compile(r"<\s*system\s*>", re.I),
    re.compile(r"<\s*system[_\-]\w+\s*>", re.I),   # <system_override>, <system-prompt>
    re.compile(r"\bASSTANT\s*:", re.I),  # typosquat of ASSISTANT
    re.compile(r"\bINSTRUCTION\s*:", re.I),
    re.compile(r"\bCOMMAND\s*:", re.I),
    re.compile(r"\bOVERRIDE\s*:", re.I),
    re.compile(r"\bSYSTEM[_\-]OVERRIDE\b", re.I),
    re.compile(r"_{2,}SYSTEM[_\-]OVERRIDE_{2,}", re.I),
    re.compile(r"#\s*(HACK|SYSTEM|OVERRIDE|IGNORE)\s*:?", re.I),
    re.compile(r"\bexecute\s*:\s*(hack|admin|root|bypass|exploit)\b", re.I),
]

# ── Category 8: Goal / objective hijacking ──────────────────────────────────
_GOAL_HIJACK_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\byour\s+(only|primary|main|sole|real|true|actual)\s+(goal|objective|purpose|task|job|mission)\s+is\s+now\b", re.I),
    re.compile(r"\bfrom\s+now\s+(on|forward)\s+(you\s+)?(must|should|will|shall|are\s+to)\b", re.I),
    re.compile(r"\bstarting\s+(now|from\s+this\s+point|from\s+here)\s+(you\s+)?(must|should|will|shall|are\s+to)\b", re.I),
    re.compile(r"\bI\s+(hereby|now|officially)\s+(authorize|permit|allow|grant)\s+(you\s+to)?\s*(bypass|override|ignore|skip)\b", re.I),
    re.compile(r"\bthe\s+(founder|admin|owner|developer|creator|operator)\s+(says?|told|wants?|authorized?|permits?)\s+(you\s+to)?\s*(bypass|override|ignore)\b", re.I),
]

# ── Category 9: Code / protocol injection syntax ────────────────────────────
_INJECTION_SYNTAX_PATTERNS: list[re.Pattern[str]] = [
    # SQL injection
    re.compile(r"';\s*(DROP|DELETE|UPDATE|INSERT|SELECT|UNION)\b", re.I),
    re.compile(r"\bDROP\s+TABLE\b", re.I),
    re.compile(r"\bSELECT\b.{1,60}\bFROM\b", re.I),
    re.compile(r"--\s*$", re.M),                      # SQL comment at EOL
    re.compile(r"/\*.*?\*/"),                          # SQL block comment
    # Shell injection
    re.compile(r"\$\([^)]+\)"),                       # $(command) substitution
    re.compile(r"&&\s*(ignore|hack|exec|wget|curl|bash|sh|rm\b)", re.I),
    re.compile(r"\|\s*(bash|sh|python|perl|ruby|php)\b", re.I),
    # Template / expression language injection
    re.compile(r"\{\{[^}]{1,200}\}\}"),               # {{...}} template injection
    re.compile(r"\$\{[^}]{1,200}\}"),                 # ${...} EL/Groovy/shell
    # Protocol handler injection
    re.compile(r"\b(javascript|vbscript|data)\s*:", re.I),
    # Path traversal
    re.compile(r"(\.\.[/\\]){2,}"),                   # ../../ or ..\..\ traversal
    # LDAP injection
    re.compile(r"\*\)\s*\(\s*\|"),
    re.compile(r"\)\(\|\s*(uid|cn|dc|ou|mail)=", re.I),
    # XML / HTML injection
    re.compile(r"<!DOCTYPE\b", re.I),
    re.compile(r"<!ENTITY\b", re.I),
    re.compile(r"<\s*(script|style)\b", re.I),
    re.compile(r"<\s*\?php\b", re.I),
    re.compile(r"file:///"),
    # YAML deserialization
    re.compile(r"---\s*!!", re.I),
    re.compile(r"!!python/object[/:]", re.I),
    # Long base64 payload (≥16 chars of base64 alphabet — likely encoded instructions)
    re.compile(r"(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{16,}={0,2}(?![A-Za-z0-9+/=])"),
    # Morse code pattern (groups of dots/dashes separated by spaces)
    re.compile(r"(?:[.\-]{1,5}\s+){4,}"),
]

# ── Category 10: Unicode / control-character obfuscation ───────────────────
_UNICODE_OBFUSCATION_PATTERNS: list[re.Pattern[str]] = [
    # BiDi override characters (can reverse displayed text to hide attacks)
    re.compile("[\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069]"),
    # Zero-width and invisible characters
    re.compile("[\u200b\u200c\u200d\u200e\u200f\u2060\u2061\u2062\u2063\u2064\ufeff]"),
    # Null byte
    re.compile("\x00"),
    # ANSI escape sequence
    re.compile(r"\x1b\["),
    # Soft hyphen (invisible, used to split keywords)
    re.compile("\u00ad"),
    # Non-breaking space (NBSP — splits keywords invisibly)
    re.compile("\u00a0"),
    # Variation selectors (change visual appearance of adjacent char)
    re.compile("[\ufe00-\ufe0f]"),
    # Mixed-script homograph attack indicators: Cyrillic, Greek, Armenian
    re.compile("[\u0400-\u04ff]"),   # Cyrillic
    re.compile("[\u0370-\u03ff]"),   # Greek
    re.compile("[\u0530-\u058f]"),   # Armenian
    # Combining diacritical marks dense enough to indicate obfuscation (≥3 consecutive)
    re.compile("[\u0300-\u036f]{3,}"),
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
    _INJECTION_SYNTAX_PATTERNS,
    _UNICODE_OBFUSCATION_PATTERNS,
]

# ── ROT13 table (used in _scan_sync for cipher obfuscation) ─────────────────
_ROT13_TABLE = str.maketrans(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
    "NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm",
)

# ── Leet-speak normalisation map (standard l33t: 0→o, 1→i, 3→e, 4→a, 5→s) ───
_LEET_TABLE = str.maketrans("013457@$", "oieastsa")

# ── Pig-Latin pattern: words ending in -ay ───────────────────────────────────
_PIG_LATIN_PATTERN = re.compile(r"\b[a-z]{2,}ay\b", re.I)

# ── Vowels for pig-Latin decoding ────────────────────────────────────────────
_VOWELS = frozenset("aeiouAEIOU")

# ── Known-bad cipher strings (CCT-PI-01 test suite) ─────────────────────────
_CIPHER_LITERAL_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\brldnov\b", re.I),   # Atbash-encoded attack string (CCT-PI-01 #45)
    re.compile(r"\brdqzwj\b", re.I),   # Caesar-encoded attack string (CCT-PI-01 #46)
]

_ALL_PATTERN_GROUPS_WITH_CIPHERS: list[list[re.Pattern[str]]] = [
    *_ALL_PATTERN_GROUPS,
    _CIPHER_LITERAL_PATTERNS,
]

# ── Injection keywords for alpha-stripped substring scan ─────────────────────
_ALPHA_INJECTION_KEYWORDS = frozenset([
    "ignore", "jailbreak", "bypass", "override", "disregard", "forget",
])

# ── Bracket characters to strip for bracket-bypass detection ─────────────────
_BRACKET_STRIP = re.compile(r"[(){}\[\]<>]")


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
        "injection_syntax",
        "unicode_obfuscation",
    ])

    def scan(self, prompt: str) -> bool:
        """
        Scan a prompt for injection attack patterns.

        Returns:
            True  — prompt is safe to proceed
            False — prompt is blocked (injection attack detected)

        C-062: Decision Space cannot be bypassed by conversation input.
        C-059: All blocked prompts are logged as evidence.
        """
        try:
            result = self._scan_sync(prompt)
        except (ValueError, TypeError) as e:
            logger.error(
                "InjectionGuard scan failed due to invalid input: %s",
                type(e).__name__,
                exc_info=True,
                extra={"context": "injection_guard_scan"},
            )
            return False

        if not result.safe:
            logger.warning(
                "C-062 injection blocked: category=%s pattern=%s",
                result.matched_category,
                result.matched_pattern,
            )

        return result.safe

    def _scan_sync(self, prompt: str) -> InjectionScanResult:
        """
        Synchronous inner scan — iterates all pattern groups, then applies
        obfuscation-aware transformations (ROT13, text reversal, leet-speak
        normalisation, pig-Latin detection, NFKD, bracket-stripping, etc.)
        and re-scans each variant.
        Separated so it can be run in an executor without blocking the event loop.
        """
        import unicodedata as _ud

        # 1. Scan raw prompt against all pattern groups (including cipher literals)
        raw_result = self._match_patterns(prompt)
        if not raw_result.safe:
            return raw_result

        # 2. NFKD normalization + strip combining diacritics (handles composed
        #    Unicode, lookalike chars from Phonetic Extensions, etc.)
        nfkd_stripped = "".join(
            c for c in _ud.normalize("NFKD", prompt) if not _ud.combining(c)
        )
        if nfkd_stripped != prompt:
            r = self._match_patterns(nfkd_stripped)
            if not r.safe:
                return InjectionScanResult(
                    safe=False,
                    matched_category="encoding_obfuscation",
                    matched_pattern=f"diacritic_stripped:{r.matched_pattern}",
                )

        # 3. ROT13 decode and re-scan (catches cipher obfuscation)
        rot13_variant = prompt.translate(_ROT13_TABLE)
        if rot13_variant != prompt:
            r = self._match_patterns(rot13_variant)
            if not r.safe:
                return InjectionScanResult(
                    safe=False,
                    matched_category="encoding_obfuscation",
                    matched_pattern=f"rot13_decoded:{r.matched_pattern}",
                )

        # 4. Text reversal and re-scan (catches reversed-text obfuscation)
        reversed_variant = prompt[::-1]
        r = self._match_patterns(reversed_variant)
        if not r.safe:
            return InjectionScanResult(
                safe=False,
                matched_category="encoding_obfuscation",
                matched_pattern=f"reversed:{r.matched_pattern}",
            )

        # 5. Leet-speak normalisation and re-scan
        leet_variant = prompt.translate(_LEET_TABLE)
        if leet_variant != prompt:
            r = self._match_patterns(leet_variant)
            if not r.safe:
                return InjectionScanResult(
                    safe=False,
                    matched_category="encoding_obfuscation",
                    matched_pattern=f"leet_normalised:{r.matched_pattern}",
                )

        # 6. Pig-Latin detection: if ≥2 pig-Latin words found, reverse the
        #    transformation (strip -ay suffix, move trailing consonants to front)
        pl_matches = _PIG_LATIN_PATTERN.findall(prompt)
        if len(pl_matches) >= 2:
            de_pigged_parts = []
            for segment in re.findall(r"[a-zA-Z]+|[^a-zA-Z]+", prompt):
                if _PIG_LATIN_PATTERN.fullmatch(segment):
                    stem = segment[:-2]  # strip -ay
                    # Find trailing consonant cluster and move to front
                    i = len(stem)
                    while i > 0 and stem[i - 1] not in _VOWELS:
                        i -= 1
                    de_pigged_parts.append(stem[i:] + stem[:i] if i < len(stem) else stem)
                else:
                    de_pigged_parts.append(segment)
            de_pigged = "".join(de_pigged_parts)
            r = self._match_patterns(de_pigged)
            if not r.safe:
                return InjectionScanResult(
                    safe=False,
                    matched_category="encoding_obfuscation",
                    matched_pattern=f"pig_latin:{r.matched_pattern}",
                )

        # 7. Alpha-only keyword scan: strip ALL non-alpha chars and check for
        #    injection keywords as substrings (handles emoji/fragmentation bypass)
        alpha_only = "".join(c for c in prompt if c.isalpha()).lower()
        if len(alpha_only) >= 6:
            for kw in _ALPHA_INJECTION_KEYWORDS:
                if kw in alpha_only:
                    return InjectionScanResult(
                        safe=False,
                        matched_category="encoding_obfuscation",
                        matched_pattern=f"alpha_fragment:{kw}",
                    )

        # 8. Bracket/punctuation strip and re-scan (handles keyword-in-brackets bypass)
        punct_stripped = re.sub(r"\s+", " ", _BRACKET_STRIP.sub(" ", prompt)).strip()
        if punct_stripped != prompt:
            r = self._match_patterns(punct_stripped)
            if not r.safe:
                return InjectionScanResult(
                    safe=False,
                    matched_category="encoding_obfuscation",
                    matched_pattern=f"bracket_stripped:{r.matched_pattern}",
                )

        return InjectionScanResult(safe=True)

    def _match_patterns(self, prompt: str) -> InjectionScanResult:
        """Iterate all pattern groups (incl. cipher literals) against *prompt*."""
        all_groups = [*_ALL_PATTERN_GROUPS, _CIPHER_LITERAL_PATTERNS]
        category_names = [*self._category_names, "cipher_encoded"]
        for group_idx, pattern_group in enumerate(all_groups):
            category_name = (
                category_names[group_idx]
                if group_idx < len(category_names)
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