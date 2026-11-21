# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-06
# Constitutional basis: C-059, C-088, C-089, C-091
"""Signed, versioned export of the effective and authorized pricing versions, and draft-only import.

An export carries every EFFECTIVE and AUTHORIZED version with its digest and is signed (HMAC-SHA256)
with the environment's bundle key. An import verifies the signature and every entry digest, then
creates each entry as a DRAFT through the same validators as any other draft; an entry whose draft
carries a rule violation (for example a package priced below its cost floor) is discarded at once and
reported as rejected. Nothing imported is ever effective: the Founder still authorizes each draft.

``bodyDigest`` of an entry is the SHA-256 of the normalized stored form (``to_internal(to_public(body))``),
so a seed written without optional defaults and its published form have one digest.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any

from pricing.body_adapter import to_internal, to_public
from pricing.models import (
    ActorContext,
    PricingDraftInvalid,
    PricingError,
    PricingKind,
    PricingUnavailable,
    PricingVersion,
    Violation,
    VersionState,
    body_digest,
    error_for_violations,
)
from pricing.service import PricingService

BUNDLE_SCHEMA_VERSION = "1.0"
BUNDLE_VERSION = 1
SIGNATURE_ALGORITHM = "HMAC-SHA256"
KEY_ID_VARIABLE = "WBE_PRICING_BUNDLE_KEY_ID"
KEY_VARIABLE = "WBE_PRICING_BUNDLE_KEY"
EXPORT_STATES = (VersionState.EFFECTIVE, VersionState.AUTHORIZED)
PAGE = 500


def canonical_digest(kind: PricingKind, body: Mapping[str, Any]) -> str:
    """Digest of the normalized form of a stored body (see module docstring)."""
    return body_digest(to_internal(kind, to_public(kind, body)))


def _bundle_digest(content: Mapping[str, Any]) -> str:
    encoded = json.dumps(content, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class BundleSigner:
    """HMAC signer for bundles; without a configured key export and import fail closed."""

    def __init__(self, key_id: str | None, secret: bytes | None) -> None:
        self._key_id = key_id
        self._secret = secret

    @classmethod
    def from_environment(cls) -> BundleSigner:
        key_id, secret = os.getenv(KEY_ID_VARIABLE), os.getenv(KEY_VARIABLE)
        return cls(key_id or None, secret.encode("utf-8") if secret else None)

    def _require(self) -> tuple[str, bytes]:
        if not self._key_id or not self._secret:
            raise PricingUnavailable("The pricing bundle signing key is not configured; export and import are closed.")
        return self._key_id, self._secret

    def sign(self, digest: str) -> dict[str, str]:
        key_id, secret = self._require()
        value = hmac.new(secret, digest.encode("ascii"), hashlib.sha256).hexdigest()
        return {"keyId": key_id, "algorithm": SIGNATURE_ALGORITHM, "value": value}

    def verify(self, digest: str, signature: Mapping[str, Any]) -> bool:
        key_id, secret = self._require()
        expected = hmac.new(secret, digest.encode("ascii"), hashlib.sha256).hexdigest()
        return (
            signature.get("keyId") == key_id
            and signature.get("algorithm") == SIGNATURE_ALGORITHM
            and isinstance(signature.get("value"), str)
            and hmac.compare_digest(str(signature["value"]), expected)
        )


def _iso(value: datetime | None) -> str | None:
    return None if value is None else value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _entry(version: PricingVersion) -> dict[str, Any]:
    return {
        "kind": version.kind.value,
        "subjectKey": version.subject_key,
        "versionNo": version.version_no,
        "state": version.state.value,
        "body": to_public(version.kind, version.body),
        "bodyDigest": canonical_digest(version.kind, version.body),
        "effectiveFrom": _iso(version.effective_from),
        "supersedes": None if version.supersedes is None else str(version.supersedes),
        "authorizedBy": version.authorized_by,
        "evidenceId": None if version.evidence_id is None else str(version.evidence_id),
    }


async def export_bundle(
    service: PricingService, actor_id: str, signer: BundleSigner, now: datetime
) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for state in EXPORT_STATES:
        offset = 0
        while True:
            page = await service.list_versions(state=state, limit=PAGE, offset=offset)
            entries.extend(_entry(item) for item in page if item.authorized_by and item.evidence_id)
            if len(page) < PAGE:
                break
            offset += PAGE
    entries.sort(key=lambda item: (item["kind"], item["subjectKey"], item["versionNo"]))
    content = {
        "schemaVersion": BUNDLE_SCHEMA_VERSION,
        "bundleVersion": BUNDLE_VERSION,
        "exportedAt": _iso(now),
        "exportedBy": actor_id,
        "entries": entries,
    }
    digest = _bundle_digest(content)
    return {**content, "bundleDigest": digest, "signature": signer.sign(digest)}


def _refusal(code: str, field: str, message: str) -> PricingDraftInvalid:
    return PricingDraftInvalid([Violation(code=code, field=field, message=message)])


def _verify_bundle(bundle: Mapping[str, Any], signer: BundleSigner) -> list[Mapping[str, Any]]:
    content = {key: bundle.get(key) for key in ("schemaVersion", "bundleVersion", "exportedAt", "exportedBy", "entries")}
    entries = bundle.get("entries")
    signature = bundle.get("signature")
    if (
        content["schemaVersion"] != BUNDLE_SCHEMA_VERSION
        or content["bundleVersion"] != BUNDLE_VERSION
        or not isinstance(entries, list)
        or not isinstance(signature, Mapping)
    ):
        raise _refusal("BUNDLE_SHAPE_INVALID", "bundle", "The bundle is not a version 1.0 pricing bundle.")
    digest = _bundle_digest(content)
    if bundle.get("bundleDigest") != digest or not signer.verify(digest, signature):
        raise _refusal("BUNDLE_SIGNATURE_INVALID", "bundle.signature", "The bundle digest or signature does not verify.")
    return [item for item in entries if isinstance(item, Mapping)]


def _violation_rows(violations: Sequence[Violation]) -> list[dict[str, str]]:
    return [
        {"code": item.code, "path": item.field or "body", "message": (item.message or item.code)[:500]}
        for item in violations
    ][:100]


def _rejected(kind: str, subject: str, code: str, message: str, violations: Sequence[Violation] = ()) -> dict[str, Any]:
    row: dict[str, Any] = {"kind": kind, "subjectKey": subject, "code": code, "message": message[:500]}
    if violations:
        row["violations"] = _violation_rows(violations)
    return row


async def import_bundle(
    service: PricingService,
    actor: ActorContext,
    bundle: Mapping[str, Any],
    signer: BundleSigner,
    *,
    deploy_maximum_paise: int | None = None,
) -> dict[str, list[dict[str, Any]]]:
    created: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for entry in _verify_bundle(bundle, signer):
        kind_value, subject = str(entry.get("kind")), str(entry.get("subjectKey"))
        try:
            kind = PricingKind(kind_value)
            body = entry.get("body")
            if not isinstance(body, Mapping):
                raise _refusal("BUNDLE_ENTRY_INVALID", "body", "The entry carries no body.")
            internal = to_internal(kind, body)
            if canonical_digest(kind, internal) != entry.get("bodyDigest"):
                raise _refusal("BUNDLE_ENTRY_DIGEST_MISMATCH", "bodyDigest", "The entry digest does not match its body.")
            result = await service.create_draft(actor, kind, internal, deploy_maximum_paise=deploy_maximum_paise)
        except ValueError:
            rejected.append(_rejected(kind_value, subject, "PRICING_DRAFT_INVALID", "The entry kind is unknown."))
            continue
        except PricingDraftInvalid as error:
            rejected.append(_rejected(kind_value, subject, error.code, error.message, error.violations))
            continue
        except PricingError as error:
            rejected.append(_rejected(kind_value, subject, error.code, error.message))
            continue
        if result.version.subject_key != subject or result.violations:
            await service.discard(actor, result.version.version_id, "Import refused by the pricing validators.")
            code = error_for_violations(result.violations).code if result.violations else "PRICING_DRAFT_INVALID"
            rejected.append(
                _rejected(
                    kind_value,
                    subject,
                    code,
                    "The entry fails the pricing validators.",
                    result.violations
                    or [Violation(code="BUNDLE_SUBJECT_MISMATCH", field="subjectKey", message="The subject does not match the body.")],
                )
            )
            continue
        created.append(
            {
                "kind": kind.value,
                "subjectKey": result.version.subject_key,
                "versionId": str(result.version.version_id),
                "state": VersionState.DRAFT.value,
            }
        )
    return {"created": created, "rejected": rejected}
