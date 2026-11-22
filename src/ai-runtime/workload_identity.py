"""ADR-046 certificate and trust-anchor primitives used by AIR's Key Vault credential source."""

# Implements: ADR-046 sections 3, 4 and 5 (mirrors src/professional-runtime/workload_identity.py primitives)
# constitutional_basis: C-001, C-023, C-026, C-059, C-063, C-083, C-084, C-085

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.x509.oid import ExtendedKeyUsageOID, ObjectIdentifier

from employment_auth import RouteGrant

DELEGATION_SIGNING_OID = ObjectIdentifier("1.3.6.1.4.1.55555.46.1")

__all__ = ["RouteGrant"]

DelegationPublicKey = Ed25519PublicKey | ec.EllipticCurvePublicKey


class ServiceAuthError(RuntimeError):
    """Privacy-safe service authentication or authorization failure."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def extract_peer_identity(
    certificate: x509.Certificate,
    trust_domain: str,
    revoked_serials: frozenset[int] = frozenset(),
    now: datetime | None = None,
) -> str:
    """Extract one exact environment-scoped SPIFFE URI SAN from a TLS-authenticated peer."""
    current = now or datetime.now(timezone.utc)
    if certificate.serial_number in revoked_serials:
        raise ServiceAuthError("SERVICE_AUTHENTICATION_FAILED")
    if current < certificate.not_valid_before_utc or current >= certificate.not_valid_after_utc:
        raise ServiceAuthError("SERVICE_AUTHENTICATION_FAILED")
    names = certificate_uris(certificate)
    expected_prefix = f"spiffe://{trust_domain}/workload/"
    if len(names) != 1 or not names[0].startswith(expected_prefix) or "*" in names[0]:
        raise ServiceAuthError("SERVICE_AUTHENTICATION_FAILED")
    return names[0]


def certificate_uris(certificate: x509.Certificate) -> list[str]:
    try:
        return certificate.extensions.get_extension_for_class(x509.SubjectAlternativeName).value.get_values_for_type(
            x509.UniformResourceIdentifier
        )
    except x509.ExtensionNotFound:
        return []


def has_extended_key_usage(certificate: x509.Certificate, usage: ObjectIdentifier) -> bool:
    try:
        return usage in certificate.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value
    except x509.ExtensionNotFound:
        return False


def _within(certificate: x509.Certificate, current: datetime) -> bool:
    return certificate.not_valid_before_utc <= current < certificate.not_valid_after_utc


def is_ca_certificate(certificate: x509.Certificate) -> bool:
    try:
        return certificate.extensions.get_extension_for_class(x509.BasicConstraints).value.ca
    except x509.ExtensionNotFound:
        return False


def issued_by(certificate: x509.Certificate, issuer: x509.Certificate) -> bool:
    try:
        certificate.verify_directly_issued_by(issuer)
    except (ValueError, TypeError, InvalidSignature):
        return False
    return True


@dataclass(frozen=True)
class TrustAnchors:
    """Roots and intermediates of the current trust bundle with its revocations."""

    roots: tuple[x509.Certificate, ...]
    intermediates: tuple[x509.Certificate, ...]
    revoked_serials: frozenset[int] = frozenset()
    revoked_identity_uris: frozenset[str] = frozenset()

    def is_revoked(self, certificate: x509.Certificate) -> bool:
        return certificate.serial_number in self.revoked_serials or any(
            uri in self.revoked_identity_uris for uri in certificate_uris(certificate)
        )

    def _intermediate_valid(self, intermediate: x509.Certificate, current: datetime) -> bool:
        return (
            is_ca_certificate(intermediate)
            and _within(intermediate, current)
            and any(is_ca_certificate(root) and _within(root, current) and issued_by(intermediate, root) for root in self.roots)
        )

    def chains(self, certificate: x509.Certificate, current: datetime) -> bool:
        """True when a non-CA certificate is valid now, not revoked and issued by a valid intermediate of these roots."""
        if is_ca_certificate(certificate) or not _within(certificate, current) or self.is_revoked(certificate):
            return False
        return any(
            issued_by(certificate, intermediate) and self._intermediate_valid(intermediate, current)
            for intermediate in self.intermediates
        )


@dataclass(frozen=True)
class DelegationKey:
    public_key: DelegationPublicKey
    certificate: x509.Certificate
    activate_after: int = 0


DelegationKeys = Mapping[tuple[str, str], DelegationPublicKey | DelegationKey]


def peer_certificate_trusted(certificate: x509.Certificate, anchors: TrustAnchors, current: datetime) -> bool:
    """Application-level check that the TLS peer chains to the current roots with client authentication."""
    return anchors.chains(certificate, current) and has_extended_key_usage(certificate, ExtendedKeyUsageOID.CLIENT_AUTH)
