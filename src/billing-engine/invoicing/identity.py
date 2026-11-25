# Implements: work-contracts/WC-172-safe-to-charge-real-customers.md WC172-R006
# Implements: adr/ADR-022-payment-processing-razorpay-india.md section 5 (GST compliance)
# Constitutional basis: C-059, C-063, C-088
"""WAOOAW's GST identity as it appears on every tax document (decision D6).

The legal name, GSTIN, registered address, state and SAC come from configuration, never from code, so the Founder
supplies them per environment and the tax professional's confirmation is recorded in the contract. With no identity
configured nothing is issued: a payment still succeeds, and the daily reconciliation reports it as a payment without
an invoice until the identity is set.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

_GSTIN: Final = re.compile(r"^(?P<state>[0-9]{2})[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
_ALPHABET: Final = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
DEFAULT_SAC: Final = "9984"
DEFAULT_RATE_PERCENT: Final = 18


class TaxIdentityNotConfigured(RuntimeError):
    """The supplier identity is missing or invalid, so no tax document may be issued."""


def gstin_checksum(first_fourteen: str) -> str:
    """The GSTIN check character: a Luhn-style mod-36 sum over the first fourteen characters."""
    total = 0
    for index, character in enumerate(first_fourteen):
        value = _ALPHABET.index(character) * (2 if index % 2 else 1)
        total += value // 36 + value % 36
    return _ALPHABET[(36 - total % 36) % 36]


def is_valid_gstin(gstin: str) -> bool:
    value = gstin.strip().upper()
    return bool(_GSTIN.match(value)) and gstin_checksum(value[:14]) == value[14]


@dataclass(frozen=True)
class SupplierIdentity:
    legal_name: str
    gstin: str
    address: str
    state_code: str
    sac_code: str = DEFAULT_SAC
    series_prefix: str = "WAOOAW"

    def as_document(self) -> dict[str, str]:
        return {
            "legalName": self.legal_name,
            "gstin": self.gstin,
            "address": self.address,
            "stateCode": self.state_code,
            "sacCode": self.sac_code,
        }


def supplier_from(
    legal_name: str, gstin: str, address: str, state_code: str, sac_code: str = DEFAULT_SAC
) -> SupplierIdentity:
    """Build the identity or refuse: every field is required and the GSTIN must be valid and in its own state."""
    values = (legal_name.strip(), gstin.strip().upper(), address.strip(), state_code.strip())
    if not all(values):
        raise TaxIdentityNotConfigured("The GST identity is incomplete.")
    name, number, place, state = values
    if not is_valid_gstin(number) or number[:2] != state:
        raise TaxIdentityNotConfigured("The GSTIN is invalid or does not belong to the stated state.")
    return SupplierIdentity(name, number, place, state, sac_code.strip() or DEFAULT_SAC)
