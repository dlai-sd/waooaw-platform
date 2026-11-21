# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C7-02
# Constitutional basis: C-048, C-049, C-059, C-063, C-088, C-091
"""Deterministic loopback fake of the Pricing Admin API semantics (pricing scenario target).

It reproduces the rules of ``pricing-admin-business-platform.openapi.yaml`` and the pricing engine with fabricated
numbers: the version state machine, the cost floor and minimum compliant price, the change-size and price-multiple
guards, Founder-only authorization with step-up, effective dates, pinned existing customers, ceiling raise and lower,
export and import as drafts, the safety-direction actions and the live-margin watch. Money is integer paise.
"""

import hashlib
from dataclasses import dataclass
from typing import Any

GST_RATE_PERCENT = 18
CHANGE_SIZE_GUARD_PERCENT = 30
PRICE_MULTIPLE_GUARD = 20
MINIMUM_MARGIN_PERCENT = 55
STARTER = "package:dma|1.0.0|STARTER"
LITE = "package:dma|1.0.0|LITE"
CEILING_SUBJECT = "budget:ENVIRONMENT_CEILING|demo"
TRIAL_GRANT = "grant:TRIAL|dma|1.0.0"
SEED_FLOORS = {STARTER: 19628, LITE: 20000}
SEED_PRICES = {STARTER: 200000, LITE: 60000}
DEPLOY_MAXIMUM_PAISE = 50000
SEED_CEILING_PAISE = 30000
COMMITTED_PAISE = 12000
PROFILES = (("BEST_CASE", 20), ("TYPICAL", 60), ("WORST_CASE", 100))
ADMIN_ACTORS = ("PRICING_ADMIN", "FOUNDER")
EDITABLE_STATES = ("DRAFT", "SIMULATED", "SUBMITTED")


def round_half_up_div(numerator: int, denominator: int) -> int:
    return (2 * numerator + denominator) // (2 * denominator)


def base_price_paise(price_incl_gst_paise: int) -> int:
    return round_half_up_div(price_incl_gst_paise * 100, 100 + GST_RATE_PERCENT)


def minimum_compliant_base_paise(cost_floor_paise: int) -> int:
    return -(-cost_floor_paise * 100 // (100 - MINIMUM_MARGIN_PERCENT))


def minimum_compliant_price_paise(cost_floor_paise: int) -> int:
    """Smallest GST-inclusive price whose base price reaches the minimum compliant base (same search as the engine)."""
    needed = minimum_compliant_base_paise(cost_floor_paise)
    price = -(-needed * (100 + GST_RATE_PERCENT) // 100)
    while base_price_paise(price) < needed:
        price += 1
    while price > 1 and base_price_paise(price - 1) >= needed:
        price -= 1
    return price


def _moved_beyond_guard(effective: int | None, proposed: int) -> bool:
    return effective is not None and effective > 0 and abs(proposed - effective) * 100 > effective * CHANGE_SIZE_GUARD_PERCENT


class _Refused(Exception):  # noqa: N818 - a typed pricing refusal, mirrors the API problem responses
    def __init__(self, status: int, code: str, **extra: Any) -> None:
        super().__init__(code)
        self.status = status
        self.code = code
        self.extra = extra


@dataclass
class _Version:
    alias: str
    subject: str
    kind: str
    value: int
    state: str
    needs_second: bool
    version_no: int
    effective_from: int | None = None
    supersedes: str | None = None
    evidence_id: str | None = None
    second_confirmed: bool = False
    imported: bool = False


class PricingFake:
    """Scenario target: ``handle`` serves ``POST /scenario/reset`` and ``POST /scenario/step``."""

    def __init__(self) -> None:
        self._actions = {name[4:]: getattr(self, name) for name in dir(self) if name.startswith("_do_")}
        self.seed = 0
        self.reset(0)

    @classmethod
    def action_names(cls) -> tuple[str, ...]:
        return tuple(sorted(name[4:] for name in dir(cls) if name.startswith("_do_")))

    def reset(self, seed: int) -> None:
        self.seed = seed
        self.today = 0
        self.floors = dict(SEED_FLOORS)
        self.ceiling = SEED_CEILING_PAISE
        self.package_open = {STARTER: True, LITE: True}
        self.grants = {TRIAL_GRANT: True}
        self.versions: dict[str, _Version] = {}
        self.effective: dict[str, str] = {}
        self.customers: dict[str, dict[str, Any]] = {}
        self.last_export: list[dict[str, Any]] = []
        self.notifications = 0
        for index, (subject, price) in enumerate(SEED_PRICES.items(), start=1):
            alias = f"seed-{subject.rsplit('|', 1)[1].lower()}"
            self.versions[alias] = _Version(alias, subject, "PACKAGE", price, "EFFECTIVE", False, index, effective_from=0)
            self.effective[subject] = alias
        self.versions["seed-ceiling"] = _Version(
            "seed-ceiling", CEILING_SUBJECT, "BUDGET", SEED_CEILING_PAISE, "EFFECTIVE", False, 1, effective_from=0
        )
        self.effective[CEILING_SUBJECT] = "seed-ceiling"
        self.customers["existing-customer"] = {"subject": STARTER, "versionId": "seed-starter"}

    def handle(
        self, method: str, path: str, headers: dict[str, str], body: dict[str, Any] | None
    ) -> tuple[int, dict[str, str], dict[str, Any]]:
        if method == "GET" and path == "/scenario/health":
            return 200, {}, {"status": "ok", "target": "pricing-fake"}
        if method != "POST" or not isinstance(body, dict) or "$invalid" in body:
            return 400, {}, self._problem("SCENARIO_REQUEST_INVALID")
        if path == "/scenario/reset":
            seed = body.get("seed")
            if isinstance(seed, bool) or not isinstance(seed, int):
                return 400, {}, self._problem("SCENARIO_REQUEST_INVALID")
            self.reset(seed)
            return 200, {}, {"outcome": "RESET", "seed": seed}
        if path != "/scenario/step":
            return 404, {}, self._problem("SCENARIO_ROUTE_UNKNOWN")
        action, params = body.get("action"), body.get("params")
        handler = self._actions.get(action) if isinstance(action, str) else None
        if handler is None or not isinstance(params, dict):
            return 400, {}, self._problem("SCENARIO_ACTION_UNKNOWN")
        actor = str(body.get("actor", ""))
        try:
            payload = handler(actor, params)
            status = 200
        except _Refused as refusal:
            status, payload = refusal.status, {**self._problem(refusal.code), **refusal.extra}
        except (KeyError, TypeError, ValueError):
            return 400, {}, self._problem("SCENARIO_PARAMS_INVALID")
        payload["state"] = self._snapshot()
        return status, {}, payload

    @staticmethod
    def _problem(code: str) -> dict[str, Any]:
        return {"outcome": code, "code": code}

    def _ref(self, kind: str, label: str) -> str:
        return f"{kind}-{hashlib.sha256(f'{self.seed}:{kind}:{label}'.encode()).hexdigest()[:12]}"

    def _snapshot(self) -> dict[str, Any]:
        return {
            "today": self.today,
            "ceilingPaise": self.ceiling,
            "committedPaise": COMMITTED_PAISE,
            "packageOpen": dict(self.package_open),
            "grants": dict(self.grants),
            "effective": dict(sorted(self.effective.items())),
            "versions": {alias: version.state for alias, version in sorted(self.versions.items())},
            "founderNotifications": self.notifications,
        }

    @staticmethod
    def _require_admin(actor: str) -> None:
        if actor not in ADMIN_ACTORS:
            raise _Refused(403, "PRICING_FORBIDDEN")

    def _version(self, params: dict[str, Any], key: str = "id") -> _Version:
        version = self.versions.get(str(params.get(key)))
        if version is None:
            raise _Refused(404, "PRICING_VERSION_NOT_FOUND")
        return version

    def _validate(self, kind: str, subject: str, value: int) -> bool:
        """Validates the body and returns whether a second confirmation is needed (change-size or multiple guard)."""
        if value <= 0:
            raise _Refused(422, "PRICING_DRAFT_INVALID")
        if kind == "BUDGET":
            if value > DEPLOY_MAXIMUM_PAISE:
                raise _Refused(422, "PRICING_CEILING_ABOVE_MAXIMUM", maximumPaise=DEPLOY_MAXIMUM_PAISE)
            return _moved_beyond_guard(self.ceiling, value)
        floor = self.floors.get(subject)
        if floor is None:
            raise _Refused(422, "PRICING_DRAFT_INVALID")
        minimum = minimum_compliant_price_paise(floor)
        if value < minimum:
            raise _Refused(422, "PRICING_BELOW_FLOOR", minimumCompliantPricePaise=minimum)
        effective = self.versions[self.effective[subject]].value if subject in self.effective else None
        return _moved_beyond_guard(effective, value) or value > PRICE_MULTIPLE_GUARD * floor

    @staticmethod
    def _illegal(version: _Version, target: str) -> _Refused:
        return _Refused(409, "PRICING_ILLEGAL_TRANSITION", fromState=version.state, toState=target)

    def _new_draft(self, params: dict[str, Any], *, imported: bool = False) -> _Version:
        alias = str(params["id"])
        if alias in self.versions:
            raise _Refused(409, "SCENARIO_ALIAS_IN_USE")
        kind = str(params.get("kind", "PACKAGE"))
        subject = CEILING_SUBJECT if kind == "BUDGET" else str(params.get("subject", STARTER))
        value = int(params["maximumPaise" if kind == "BUDGET" else "priceInclGstPaise"])
        needs_second = self._validate(kind, subject, value)
        number = 1 + sum(1 for version in self.versions.values() if version.subject == subject)
        version = _Version(alias, subject, kind, value, "DRAFT", needs_second, number, imported=imported)
        self.versions[alias] = version
        return version

    @staticmethod
    def _describe(version: _Version) -> dict[str, Any]:
        return {
            "versionId": version.alias,
            "subjectKey": version.subject,
            "versionNo": version.version_no,
            "versionState": version.state,
            "needsSecondConfirmation": version.needs_second,
            "effectiveFrom": version.effective_from,
            "supersedes": version.supersedes,
            "evidenceId": version.evidence_id,
        }

    def _apply(self, version: _Version) -> None:
        previous = self.effective.get(version.subject)
        if previous is not None:
            self.versions[previous].state = "SUPERSEDED"
            version.supersedes = previous
        version.state = "EFFECTIVE"
        self.effective[version.subject] = version.alias
        if version.kind == "BUDGET":
            self.ceiling = version.value

    def _do_create_draft(self, actor: str, params: dict[str, Any]) -> dict[str, Any]:
        self._require_admin(actor)
        version = self._new_draft(params)
        return {"outcome": "DRAFT_CREATED", **self._describe(version)}

    def _do_edit_draft(self, actor: str, params: dict[str, Any]) -> dict[str, Any]:
        self._require_admin(actor)
        version = self._version(params)
        if version.state not in EDITABLE_STATES:
            raise self._illegal(version, "DRAFT")
        version.needs_second = self._validate(version.kind, version.subject, int(params["value"]))
        version.value = int(params["value"])
        version.state = "DRAFT"
        return {"outcome": "DRAFT_EDITED", **self._describe(version)}

    def _do_simulate(self, actor: str, params: dict[str, Any]) -> dict[str, Any]:
        self._require_admin(actor)
        version = self._version(params)
        if version.state != "DRAFT":
            raise self._illegal(version, "SIMULATED")
        version.state = "SIMULATED"
        if version.kind == "BUDGET":
            diff = {"fromMaximumPaise": self.ceiling, "toMaximumPaise": version.value}
            return {"outcome": "SIMULATED", **self._describe(version), "diff": diff}
        floor = self.floors[version.subject]
        base = base_price_paise(version.value)
        current = self.versions[self.effective[version.subject]].value
        return {
            "outcome": "SIMULATED",
            **self._describe(version),
            "costFloorPaise": floor,
            "basePricePaise": base,
            "gstPaise": version.value - base,
            "marginPercent": (base - floor) * 1000 // base / 10,
            "minimumCompliantPricePaise": minimum_compliant_price_paise(floor),
            "diff": {"fromPricePaise": current, "toPricePaise": version.value},
            "profiles": {name: {"monthlyCostPaise": (floor * share + 50) // 100} for name, share in PROFILES},
        }

    def _do_submit(self, actor: str, params: dict[str, Any]) -> dict[str, Any]:
        self._require_admin(actor)
        version = self._version(params)
        if version.state != "SIMULATED":
            raise self._illegal(version, "SUBMITTED")
        confirmed = bool(params.get("secondConfirmation", False))
        if version.needs_second and not confirmed:
            raise _Refused(409, "PRICING_NEEDS_SECOND_CONFIRMATION")
        version.second_confirmed = confirmed
        version.state = "SUBMITTED"
        return {"outcome": "SUBMITTED", **self._describe(version), "secondConfirmed": confirmed}

    def _do_authorize(self, actor: str, params: dict[str, Any]) -> dict[str, Any]:
        if actor != "FOUNDER":
            raise _Refused(403, "PRICING_FORBIDDEN")
        if not params.get("stepUp"):
            raise _Refused(403, "PRICING_STEP_UP_REQUIRED")
        version = self._version(params)
        if version.state != "SUBMITTED":
            raise self._illegal(version, "AUTHORIZED")
        effective_from = int(params.get("effectiveFrom", self.today))
        if effective_from < self.today:
            raise _Refused(422, "PRICING_DRAFT_INVALID")
        version.state = "AUTHORIZED"
        version.effective_from = effective_from
        version.evidence_id = self._ref("ev", version.alias)
        if effective_from <= self.today:
            self._apply(version)
        return {"outcome": "AUTHORIZED", **self._describe(version)}

    def _do_discard(self, actor: str, params: dict[str, Any]) -> dict[str, Any]:
        self._require_admin(actor)
        version = self._version(params)
        if version.state not in EDITABLE_STATES:
            raise self._illegal(version, "DISCARDED")
        version.state = "DISCARDED"
        return {"outcome": "DISCARDED", **self._describe(version)}

    def _do_advance_clock(self, actor: str, params: dict[str, Any]) -> dict[str, Any]:
        self.today += int(params["days"])
        due = sorted(
            (v for v in self.versions.values() if v.state == "AUTHORIZED" and (v.effective_from or 0) <= self.today),
            key=lambda v: (v.effective_from or 0, v.alias),
        )
        for version in due:
            self._apply(version)
        return {"outcome": "CLOCK_ADVANCED", "madeEffective": [version.alias for version in due]}

    def _do_hire_customer(self, actor: str, params: dict[str, Any]) -> dict[str, Any]:
        subject = str(params.get("subject", STARTER))
        if not self.package_open.get(subject, False):
            raise _Refused(409, "PACKAGE_CLOSED_TO_NEW_CUSTOMERS")
        version = self.versions[self.effective[subject]]
        self.customers[str(params["customer"])] = {"subject": subject, "versionId": version.alias}
        return {"outcome": "HIRED", "pinnedVersionId": version.alias, "pricePaise": version.value}

    def _do_renew_customer(self, actor: str, params: dict[str, Any]) -> dict[str, Any]:
        customer = self.customers[str(params["customer"])]
        version = self.versions[self.effective[customer["subject"]]]
        customer["versionId"] = version.alias
        return {"outcome": "RENEWED", "pinnedVersionId": version.alias, "pricePaise": version.value}

    def _do_read_customer(self, actor: str, params: dict[str, Any]) -> dict[str, Any]:
        customer = self.customers[str(params["customer"])]
        pinned = self.versions[customer["versionId"]]
        current = self.versions[self.effective[customer["subject"]]]
        return {
            "outcome": "CUSTOMER_READ",
            "pinnedVersionId": pinned.alias,
            "pricePaise": pinned.value,
            "currentVersionId": current.alias,
            "currentPricePaise": current.value,
        }

    def _do_lower_ceiling(self, actor: str, params: dict[str, Any]) -> dict[str, Any]:
        self._require_admin(actor)
        proposed = int(params["maximumPaise"])
        if proposed > self.ceiling:
            raise _Refused(422, "PRICING_CEILING_ABOVE_MAXIMUM", maximumPaise=self.ceiling)
        if proposed < COMMITTED_PAISE:
            raise _Refused(409, "PRICING_CEILING_BELOW_OPEN_RESERVATIONS", blockingPaise=COMMITTED_PAISE)
        self.ceiling = proposed
        self.notifications += 1
        return {"outcome": "CEILING_LOWERED", "direction": "SAFETY", "founderNotified": True, "maximumPaise": proposed}

    def _do_close_package(self, actor: str, params: dict[str, Any]) -> dict[str, Any]:
        self._require_admin(actor)
        subject = str(params.get("subject", STARTER))
        if subject not in self.package_open:
            raise _Refused(404, "PRICING_VERSION_NOT_FOUND")
        self.package_open[subject] = False
        self.notifications += 1
        return {"outcome": "PACKAGE_CLOSED", "direction": "SAFETY", "founderNotified": True}

    def _do_disable_grant(self, actor: str, params: dict[str, Any]) -> dict[str, Any]:
        self._require_admin(actor)
        grant = str(params.get("grant", TRIAL_GRANT))
        if grant not in self.grants:
            raise _Refused(404, "PRICING_VERSION_NOT_FOUND")
        self.grants[grant] = False
        self.notifications += 1
        return {"outcome": "GRANT_DISABLED", "direction": "SAFETY", "founderNotified": True}

    def _do_provider_rate_change(self, actor: str, params: dict[str, Any]) -> dict[str, Any]:
        percent = int(params["percent"])
        self.floors = {subject: floor * (100 + percent) // 100 for subject, floor in self.floors.items()}
        return {"outcome": "RATE_CHANGED", "floors": dict(sorted(self.floors.items()))}

    def _do_live_margin(self, actor: str, params: dict[str, Any]) -> dict[str, Any]:
        self._require_admin(actor)
        breaches = []
        for subject in sorted(self.floors):
            version = self.versions[self.effective[subject]]
            base = base_price_paise(version.value)
            if base < self.floors[subject]:
                breaches.append({"subjectKey": subject, "reason": "BELOW_COST_FLOOR"})
            elif base < minimum_compliant_base_paise(self.floors[subject]):
                breaches.append({"subjectKey": subject, "reason": "BELOW_MINIMUM_MARGIN"})
        if breaches:
            self.notifications += 1
        return {
            "outcome": "LIVE_MARGIN_BREACH" if breaches else "LIVE_MARGIN_OK",
            "breaches": breaches,
            "waooaw_live_margin_floor_breach": len(breaches),
        }

    def _do_export_versions(self, actor: str, params: dict[str, Any]) -> dict[str, Any]:
        self._require_admin(actor)
        self.last_export = [
            {"subjectKey": v.subject, "versionNo": v.version_no, "state": v.state, "value": v.value}
            for v in sorted(self.versions.values(), key=lambda v: v.alias)
            if v.state == "EFFECTIVE" and v.kind == "PACKAGE"
        ]
        digest = hashlib.sha256(repr(self.last_export).encode()).hexdigest()[:16]
        return {"outcome": "EXPORTED", "items": self.last_export, "bodyDigest": digest}

    def _do_import_versions(self, actor: str, params: dict[str, Any]) -> dict[str, Any]:
        self._require_admin(actor)
        items = params["items"]
        if not isinstance(items, list) or not items:
            raise _Refused(422, "PRICING_DRAFT_INVALID")
        for item in items:
            if str(item["id"]) in self.versions:
                raise _Refused(409, "SCENARIO_ALIAS_IN_USE")
            self._validate("PACKAGE", str(item.get("subject", STARTER)), int(item["priceInclGstPaise"]))
        created = [self._new_draft(item, imported=True) for item in items]
        return {"outcome": "IMPORTED_AS_DRAFTS", "imported": len(created), "states": [v.state for v in created]}
