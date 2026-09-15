"""Fail-closed authority preflight for a DMA Release 1 candidate build."""

# Implements: WC-089 DMA-00; CCT-DMA-BUILD-AUTH-01
# Constitutional basis: C-001, C-023, C-059, C-065, C-070

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from pathlib import Path
import re
from threading import Lock
from typing import Any, ClassVar


class BuildAuthorityDenied(ValueError):  # noqa: N818 - constitutional denial term
    """Raised before builder execution when release authority is invalid."""


class CandidateBuildAuthorityGate:
    _HEAD_PATTERN = re.compile(r"^[0-9a-f]{40}$")
    _EXPECTED: ClassVar[dict[str, Any]] = {
        "releaseSequence": 1,
        "professionalType": "digital-marketing-local-service",
        "professionalVersion": "1.0.0",
        "specificationRevision": "3.1",
        "branch": "ib/089/dma-release-1",
        "environment": "local-docker",
    }

    def __init__(self) -> None:
        self._consumed_nonces: set[str] = set()
        self._lock = Lock()

    def authorize(
        self,
        authority: Mapping[str, Any],
        *,
        source_head: str,
        builder_identity: str,
        now: datetime,
    ) -> None:
        if now.tzinfo is None:
            raise BuildAuthorityDenied("BUILD_AUTHORITY_TIME_INVALID")
        if not self._HEAD_PATTERN.fullmatch(source_head):
            raise BuildAuthorityDenied("BUILD_AUTHORITY_SOURCE_INVALID")

        required = {
            "founderApprovalRef",
            "sessionAuthorizationRef",
            "effectiveAt",
            "expiresAt",
            "sourceHead",
            "builderIdentity",
            "nonce",
            *self._EXPECTED,
        }
        if set(authority) != required:
            raise BuildAuthorityDenied("BUILD_AUTHORITY_FIELDS_INVALID")
        if any(authority[key] != value for key, value in self._EXPECTED.items()):
            raise BuildAuthorityDenied("BUILD_AUTHORITY_COORDINATES_MISMATCH")
        if authority["founderApprovalRef"] != "github-issue:437":
            raise BuildAuthorityDenied("BUILD_AUTHORITY_FOUNDER_APPROVAL_INVALID")
        if authority["sessionAuthorizationRef"] != "github-issue:437#authority":
            raise BuildAuthorityDenied("BUILD_AUTHORITY_SESSION_INVALID")
        if authority["sourceHead"] != source_head or authority["builderIdentity"] != builder_identity:
            raise BuildAuthorityDenied("BUILD_AUTHORITY_SUBJECT_MISMATCH")

        try:
            effective_at = datetime.fromisoformat(str(authority["effectiveAt"]).replace("Z", "+00:00"))
            expires_at = datetime.fromisoformat(str(authority["expiresAt"]).replace("Z", "+00:00"))
        except ValueError as error:
            raise BuildAuthorityDenied("BUILD_AUTHORITY_TIME_INVALID") from error
        current = now.astimezone(timezone.utc)
        if effective_at.tzinfo is None or expires_at.tzinfo is None or not effective_at <= current < expires_at:
            raise BuildAuthorityDenied("BUILD_AUTHORITY_NOT_ACTIVE")

        nonce = authority["nonce"]
        if not isinstance(nonce, str) or not nonce:
            raise BuildAuthorityDenied("BUILD_AUTHORITY_NONCE_INVALID")
        with self._lock:
            if nonce in self._consumed_nonces:
                raise BuildAuthorityDenied("BUILD_AUTHORITY_REPLAYED")
            self._consumed_nonces.add(nonce)


def run_candidate_build(
    gate: CandidateBuildAuthorityGate,
    authority: Mapping[str, Any],
    *,
    source_head: str,
    builder_identity: str,
    now: datetime,
    output_directory: Path,
    build: Callable[[Path], None],
) -> None:
    gate.authorize(authority, source_head=source_head, builder_identity=builder_identity, now=now)
    output_directory.mkdir(parents=True, exist_ok=False)
    build(output_directory)