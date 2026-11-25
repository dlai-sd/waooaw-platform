# Implements: work-contracts/WC-172-safe-to-charge-real-customers.md WC172-R010
# Implements: adr/ADR-022-payment-processing-razorpay-india.md (live keys are for production only)
# Constitutional basis: C-059, C-063, C-088
"""Payment mode per environment, checked once at startup.

Production runs in LIVE mode and every other environment in TEST mode. A live Razorpay key outside production, a test
key in production, a mode that disagrees with the key and a readiness state that disagrees with the environment each
stop the service from starting, so a mistaken setting can never put real money through a test environment or a
sandbox charge through production.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

LIVE_KEY_PREFIX: Final = "rzp_live_"
TEST_KEY_PREFIX: Final = "rzp_test_"


class MoneyModeError(RuntimeError):
    """The environment, payment mode, key and readiness state do not agree; the service must not start."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class MoneyMode:
    environment: str
    payment_mode: str
    key_mode: str  # LIVE, TEST or NONE

    @property
    def is_live(self) -> bool:
        return self.payment_mode == "LIVE"


def key_mode(key_id: str) -> str:
    value = key_id.strip()
    if not value:
        return "NONE"
    if value.startswith(LIVE_KEY_PREFIX):
        return "LIVE"
    if value.startswith(TEST_KEY_PREFIX):
        return "TEST"
    raise MoneyModeError("MONEY_KEY_MODE_UNKNOWN")


def require_consistent_mode(environment: str, payment_mode: str, key_id: str, readiness_state: str) -> MoneyMode:
    production = environment == "production"
    if production != (payment_mode == "LIVE"):
        raise MoneyModeError("MONEY_MODE_ENVIRONMENT_MISMATCH")
    mode = key_mode(key_id)
    if mode == "LIVE" and not production:
        raise MoneyModeError("LIVE_KEY_OUTSIDE_PRODUCTION")
    if mode == "TEST" and production:
        raise MoneyModeError("TEST_KEY_IN_PRODUCTION")
    if readiness_state == "READY_LIVE" and not (production and mode == "LIVE"):
        raise MoneyModeError("READINESS_STATE_MISMATCH")
    if readiness_state == "READY_TEST" and (production or mode != "TEST"):
        raise MoneyModeError("READINESS_STATE_MISMATCH")
    return MoneyMode(environment, payment_mode, mode)
