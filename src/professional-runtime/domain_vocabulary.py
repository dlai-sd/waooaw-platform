"""Domain vocabulary resolution: {DVE.TOKEN} references resolve from the vocabulary bound to the admitted agent version."""

# Implements: architecture/reference/product/ae02-real-work-solution-contract.md DC-1 Domain vocabulary resolution
# Constitutional basis: C-042, C-049, C-059, C-063
# IB: IB-170

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any

_TOKEN = re.compile(r"\{DVE\.([A-Z][A-Z0-9_]*)\}")
_DOMAIN = re.compile(r"^[a-z][a-z0-9_]{1,63}$")


class VocabularyDigestMismatch(Exception):  # noqa: N818 - named for the refusal it records
    """The loaded vocabulary is not the one the manifest names. Resolution fails closed."""


class VocabularyNotBound(Exception):  # noqa: N818 - named for the refusal it records
    """No vocabulary is bound to this agent version."""


@dataclass(frozen=True)
class VocabularyGap:
    token: str
    reason: str  # TOKEN_UNKNOWN or TOKEN_HAS_NO_WORDING


@dataclass(frozen=True)
class ResolvedText:
    text: str
    gaps: tuple[VocabularyGap, ...]
    limitations: tuple[str, ...]
    vocabulary_version: str
    vocabulary_digest: str


class DomainVocabulary:
    """One versioned vocabulary. The business domain is data chosen by the customer, never a code branch."""

    def __init__(self, version: str, digest: str, default_domain: str, tokens: Mapping[str, Mapping[str, str]]) -> None:
        self.version = version
        self.digest = digest
        self._default = default_domain
        self._tokens = {name: dict(by_domain) for name, by_domain in tokens.items()}

    @classmethod
    def from_reference(cls, root: Path, reference: Mapping[str, Any]) -> DomainVocabulary:
        """Load the document a manifest `vocabularyRef` names and prove it is exactly that document."""
        path = root / str(reference["contractRef"]).split("#", maxsplit=1)[0]
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest != reference["contractDigest"]:
            raise VocabularyDigestMismatch(str(reference["contractRef"]))
        document = json.loads(raw)
        if document["version"] != reference["contractVersion"]:
            raise VocabularyDigestMismatch(str(reference["contractRef"]))
        return cls(document["version"], digest, document["defaultDomain"], document["tokens"])

    def resolve(self, text: str, business_domain: str | None) -> ResolvedText:
        gaps: list[VocabularyGap] = []
        limitations: list[str] = []
        domain = business_domain if business_domain and _DOMAIN.match(business_domain) else None
        known = any(domain in by_domain for by_domain in self._tokens.values()) if domain else False
        if business_domain and not known:
            limitations.append(f"The business domain '{business_domain}' has no wording here; general wording was used.")

        def replace(match: re.Match[str]) -> str:
            token = match.group(1)
            by_domain = self._tokens.get(token)
            if by_domain is None:
                gaps.append(VocabularyGap(token, "TOKEN_UNKNOWN"))
                return f"[missing wording: {token}]"
            wording = by_domain.get(domain) if domain and known else None
            wording = wording or by_domain.get(self._default)
            if wording is None:
                gaps.append(VocabularyGap(token, "TOKEN_HAS_NO_WORDING"))
                return f"[missing wording: {token}]"
            return wording

        resolved = _TOKEN.sub(replace, text)
        limitations.extend(f"No wording for {gap.token}: {gap.reason}." for gap in gaps)
        return ResolvedText(resolved, tuple(gaps), tuple(limitations), self.version, self.digest)


class VocabularyRegistry:
    """Maps an admitted agent version to its own vocabulary. Shared code reads this data; it never names an agent."""

    def __init__(self) -> None:
        self._bound: dict[tuple[str, str], DomainVocabulary] = {}
        self._lock = Lock()

    def bind(self, agent_type: str, agent_version: str, vocabulary: DomainVocabulary) -> None:
        with self._lock:
            self._bound[(agent_type, agent_version)] = vocabulary

    def resolve(self, agent_type: str, agent_version: str, text: str, business_domain: str | None) -> ResolvedText:
        with self._lock:
            vocabulary = self._bound.get((agent_type, agent_version))
        if vocabulary is None:
            raise VocabularyNotBound(f"{agent_type}@{agent_version}")
        return vocabulary.resolve(text, business_domain)
