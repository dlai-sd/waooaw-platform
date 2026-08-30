"""Fail-closed professional admission guard at the PAAS activation boundary."""

# Implements: WC-079 AA-07, AA-09
# constitutional_basis: C-003, C-023, C-025, C-059, C-063, C-079

from __future__ import annotations

import hmac
import re
from dataclasses import dataclass


_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_SEMVER = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")


class AdmissionGuardError(RuntimeError):
    """Privacy-safe activation denial."""

    def __init__(self, code: str = "ADMISSION_ACTIVATION_DENIED") -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class AdmissionActivationBinding:
    professional_type_id: str
    professional_version: str
    admission_state: str
    admission_content_digest: str
    artifact_digest: str
    runtime_version: str
    customer_contract_digest: str


class AdmissionActivationGuard:
    """Bind a BP-authorized activation snapshot to this exact runtime image."""

    def __init__(self, runtime_version: str | None, artifact_digest: str | None) -> None:
        self._runtime_version = runtime_version
        self._artifact_digest = artifact_digest

    def require_admitted(self, binding: AdmissionActivationBinding) -> None:
        if not self._runtime_version or not self._artifact_digest:
            raise AdmissionGuardError("ADMISSION_GUARD_UNAVAILABLE")
        valid = (
            binding.admission_state == "ACTIVE"
            and bool(_SEMVER.fullmatch(binding.professional_version))
            and bool(_SEMVER.fullmatch(binding.runtime_version))
            and bool(_DIGEST.fullmatch(binding.admission_content_digest))
            and bool(_DIGEST.fullmatch(binding.artifact_digest))
            and bool(_DIGEST.fullmatch(binding.customer_contract_digest))
            and hmac.compare_digest(binding.runtime_version, self._runtime_version)
            and hmac.compare_digest(binding.artifact_digest, self._artifact_digest)
        )
        if not valid:
            raise AdmissionGuardError()