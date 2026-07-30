# Implements: architecture/reference/billing/wbe-component-spec.md full
# constitutional_basis: C-023, C-059, C-063, C-090
from __future__ import annotations


class InsufficientFundsError(Exception):
    """
    Raised when a wallet bucket has insufficient available_paise for a reservation.
    Maps to HTTP 402 at the router layer.
    Constitutional: C-089 (margin floor gate enforced upstream; this guard is
    the last line before over-spend).
    """

    def __init__(self, message: str = "Insufficient funds in wallet bucket") -> None:
        super().__init__(message)


class BucketNotFoundError(KeyError):
    """
    Raised when a requested (wallet_id, thread_type) bucket does not exist.
    Maps to HTTP 404 at the router layer.
    """

    def __init__(self, wallet_id: str, thread_type: str) -> None:
        super().__init__(
            f"No bucket found for wallet_id={wallet_id} thread_type={thread_type}"
        )
        self.wallet_id = wallet_id
        self.thread_type = thread_type


class DuplicateReservationError(Exception):
    """
    Raised when an idempotency_key collision is detected but the existing
    reservation belongs to a different caller context (defensive check).
    Maps to HTTP 409 at the router layer.
    """

    def __init__(self, idempotency_key: str) -> None:
        super().__init__(
            f"Reservation already exists for idempotency_key={idempotency_key}"
        )
        self.idempotency_key = idempotency_key


class BillingProfileGateError(PermissionError):
    """
    Raised when C-088 billing profile gate check fails during subscription activation.
    Maps to HTTP 403 at the router layer.
    """

    def __init__(self, customer_id: str, status: str) -> None:
        super().__init__(
            f"C-088 gate: billing_profile_status={status} not FOUNDER_AUTHORIZED "
            f"for customer_id={customer_id}"
        )
        self.customer_id = customer_id
        self.status = status


class GrandfatherPriceViolationError(ValueError):
    """
    Raised when a renewal would charge more than the agreed price
    after the C-090 grandfather window has expired.
    Maps to HTTP 422 at the router layer.
    """

    def __init__(self, wallet_id: str, plan_price: int, agreed_price: int) -> None:
        super().__init__(
            f"C-090 violation: plan_price={plan_price} > agreed_price={agreed_price} "
            f"for wallet_id={wallet_id}"
        )
        self.wallet_id = wallet_id
        self.plan_price = plan_price
        self.agreed_price = agreed_price


class ReservationNotFoundError(KeyError):
    """
    Raised when a release() call references a reservation_id that does not exist
    in the database.
    Maps to HTTP 404 at the router layer.
    """

    def __init__(self, reservation_id: str) -> None:
        super().__init__(
            f"No reservation found for reservation_id={reservation_id}"
        )
        self.reservation_id = reservation_id


class WalletNotFoundError(KeyError):
    """
    Raised when a requested wallet_id does not correspond to any CustomerWallet row.
    Maps to HTTP 404 at the router layer.
    """

    def __init__(self, wallet_id: str) -> None:
        super().__init__(f"No wallet found for wallet_id={wallet_id}")
        self.wallet_id = wallet_id


class SubscriptionAlreadyActiveError(Exception):
    """
    Raised when activate_subscription() is called for a customer that already
    has an active subscription contract for the same agent_type + bundle_tier.
    Maps to HTTP 409 at the router layer.
    Constitutional: prevents double-activation race conditions (C-038 pro-rata
    integrity depends on a single authoritative period start).
    """

    def __init__(self, customer_id: str, agent_type: str, bundle_tier: str) -> None:
        super().__init__(
            f"Subscription already active for customer_id={customer_id} "
            f"agent_type={agent_type} bundle_tier={bundle_tier}"
        )
        self.customer_id = customer_id
        self.agent_type = agent_type
        self.bundle_tier = bundle_tier


class RenewalPeriodOverlapError(ValueError):
    """
    Raised when renew() is called with a new_period_start that overlaps an
    existing active period, which would corrupt pro-rata calculations (C-038).
    Maps to HTTP 422 at the router layer.
    """

    def __init__(self, wallet_id: str, new_period_start: str, existing_end: str) -> None:
        super().__init__(
            f"C-038 violation: new_period_start={new_period_start} overlaps "
            f"existing period ending={existing_end} for wallet_id={wallet_id}"
        )
        self.wallet_id = wallet_id
        self.new_period_start = new_period_start
        self.existing_end = existing_end


class EvidenceRecordError(RuntimeError):
    """
    Raised when C-059 evidence recording via ce_stub fails and the operation
    cannot proceed without a traceable audit trail.
    Maps to HTTP 503 at the router layer — callers must retry.
    Constitutional: C-059 (every mutation must have a persisted evidence record).
    """

    def __init__(self, action: str, cause: str) -> None:
        super().__init__(
            f"C-059 evidence record failed for action={action}: {cause}"
        )
        self.action = action
        self.cause = cause