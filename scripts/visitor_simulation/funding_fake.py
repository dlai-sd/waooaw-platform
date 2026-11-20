# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C7-01
# Constitutional basis: C-048, C-049, C-059, C-063
"""Deterministic loopback fake of the spend resolver, wallet and customer-visible outcomes (funding scenario target).

It mirrors the account resolution table of ``SpendAccountResolver`` (C3-04), the fail-closed rules (C3-05), the platform
accounts (C4-04), component units (C4-08) and the proactive-message allowance (C4-12) with small fabricated amounts, so
the funding scenarios can run without a database, a provider or the Demo environment. Customer-facing texts here are
loopback placeholders: the scenarios assert outcome codes, account classes and the absence of money words, never copy.
"""

import hashlib
from dataclasses import dataclass, field
from typing import Any

from visitor_simulation.policy import ProtocolPolicy, load_protocol_policy

SIMULATOR_ROLE = "visitor-simulator"
CLASS_HEADER = "X-Spend-Account-Class"
ROLES_HEADER = "X-Actor-Roles"

VISITOR_TURN_PAISE = 40
WORK_TURN_PAISE = 100
ONBOARDING_TURN_PAISE = 100
FLOOR_USE_PAISE = 60
TRIAL_GRANT_PAISE = 500
SETUP_GRANT_PAISE = 300
PERIOD_CREDIT_PAISE = 1000
TOPUP_PAISE = 500
TENANT_ACQUISITION_CAP_PAISE = 1000
ENVIRONMENT_ACQUISITION_CAP_PAISE = 5000
SIMULATION_CAP_PAISE = 2000
PROACTIVE_ALLOWANCE = 30
SLOT_MAXIMUM = 1
INITIAL_PRICE_PAISE = 200000
COMPONENT_QUANTITY = {"TRIAL": 2, "HIRED": 4}
NOTICE_THRESHOLDS = (("CAPACITY_50", 50), ("CAPACITY_85", 85), ("CAPACITY_EMPTY", 100))

LIMITATION_TEXT = "I can't take that on with my full abilities right now, so I'm giving you limited help."
FREE_PATH_TEXT = "Some of my abilities are unavailable at the moment, so I'm answering without them."
SCRIPTED_TEXT = "Thanks for asking. Here is the short version of what I can do."
BENEFICIARY_TEXT = "That isn't available right now. The account holder has been told."
CAPACITY_TEXT = {
    "CAPACITY_50": "Half of this agent's work allowance is used.",
    "CAPACITY_85": "Most of this agent's work allowance is used.",
    "CAPACITY_EMPTY": "This agent's work allowance is used up.",
}

PURPOSE_BY_ACTION = {
    "visitor_turn": "PRESALES_OR_MARKETPLACE",
    "web_handoff": "PRESALES_OR_MARKETPLACE",
    "marketplace_turn": "PRESALES_OR_MARKETPLACE",
    "flood": "PRESALES_OR_MARKETPLACE",
    "start_trial": "NONE",
    "hire": "NONE",
    "convert_trial": "NONE",
    "renew": "NONE",
    "expire_trial": "NONE",
    "wbe_fault": "NONE",
    "publish_pricing": "NONE",
    "read_relationship": "NONE",
    "read_telemetry": "NONE",
    "work_turn": "AGENT_WORK",
    "reconcile": "AGENT_WORK",
    "time_access_session": "AGENT_WORK",
    "voice_note": "AGENT_WORK",
    "onboarding_turn": "ONBOARDING",
    "acknowledge_setup_exhaustion": "ONBOARDING",
    "connect_account": "ONBOARDING",
    "switch_request": "PLATFORM_SUPPORT",
    "pause_skill": "PLATFORM_SUPPORT",
    "render_for": "PLATFORM_SUPPORT",
    "request_topup": "PLATFORM_SUPPORT",
    "goodwill": "PLATFORM_SUPPORT",
    "start_message": "PLATFORM_SUPPORT",
    "emergency_stop": "SAFETY_FLOOR",
    "simulation_turn": "SIMULATION",
}
PROACTIVE_PURPOSE = {"AGENT_ALERT": "AGENT_WORK", "CAPACITY_NOTICE": "SAFETY_FLOOR", "EMERGENCY_ALERT": "SAFETY_FLOOR"}


class _Refused(Exception):  # noqa: N818 - a typed spend refusal, mirrors SpendRefusedException
    def __init__(self, status: int, code: str, message: str = "", account_class: str | None = None) -> None:
        super().__init__(code)
        self.status = status
        self.code = code
        self.message = message
        self.account_class = account_class


@dataclass
class _Account:
    balance: int = 0
    reserved: int = 0
    credited: int = 0

    @property
    def available(self) -> int:
        return self.balance - self.reserved

    def credit(self, paise: int) -> None:
        self.balance += paise
        self.credited += paise

    def used_percent(self) -> int:
        return 0 if self.credited == 0 else (self.credited - self.balance) * 100 // self.credited


@dataclass
class _Relationship:
    alias: str
    relationship_id: str
    customer: str
    agent: str
    version: str
    state: str
    authority: str
    pricing_version: str
    price_paise: int
    accounts: dict[str, _Account] = field(
        default_factory=lambda: {"TRIAL": _Account(), "SETUP_GRANT": _Account(), "SUBSCRIPTION": _Account()}
    )
    used: dict[str, int] = field(default_factory=dict)
    reservations: list[dict[str, Any]] = field(default_factory=list)
    proactive_used: int = 0
    slots: int = 0
    setup_told: bool = False
    setup_acknowledged: bool = False


@dataclass
class _Ctx:
    actor: str
    channel: str
    state: str
    purpose: str
    params: dict[str, Any]


def resolve_account_class(purpose: str, authority: str | None, simulated: bool) -> str:
    """The resolution table of ``SpendAccountResolver`` (C3-04); ``authority`` is None without a relationship."""
    if purpose == "SAFETY_FLOOR":
        return "PLATFORM_FLOOR"
    if purpose == "SIMULATION" or simulated:
        return "SIMULATION"
    if purpose in ("PRESALES_OR_MARKETPLACE", "PLATFORM_SUPPORT") or authority is None:
        return "ACQUISITION"
    if purpose == "ONBOARDING":
        return "SETUP_GRANT"
    if purpose == "AGENT_WORK" and authority == "TRIAL":
        return "TRIAL"
    if purpose == "AGENT_WORK" and authority == "ACCEPTED_OFFERING":
        return "SUBSCRIPTION"
    raise _Refused(403, "SPEND_AUTHORITY_UNAVAILABLE")


class FundingFake:
    """Scenario target: ``handle`` serves ``POST /scenario/reset`` and ``POST /scenario/step``."""

    def __init__(self, *, simulator_headers_enabled: bool = True, policy: ProtocolPolicy | None = None) -> None:
        self.simulator_headers_enabled = simulator_headers_enabled
        self._policy = policy or load_protocol_policy()
        self._actions = {name[4:]: getattr(self, name) for name in dir(self) if name.startswith("_do_")}
        self.seed = 0
        self.reset(0)

    @classmethod
    def action_names(cls) -> tuple[str, ...]:
        return tuple(sorted(name[4:] for name in dir(cls) if name.startswith("_do_")))

    def reset(self, seed: int) -> None:
        self.seed = seed
        self.relationships: dict[str, _Relationship] = {}
        self.tenant_spent: dict[str, int] = {}
        self.environment_spent = 0
        self.simulation_spent = 0
        self.floor_spent = 0
        self.trial_keys: set[tuple[str, str, str]] = set()
        self.identity_claims: dict[tuple[str, str, str], str] = {}
        self.leads: dict[str, str] = {}
        self.stopped = False
        self.stop_acknowledgements = 0
        self.wbe_available = True
        self.current_pricing = "price-v1"
        self.prices = {"price-v1": INITIAL_PRICE_PAISE}
        self.telemetry: list[dict[str, Any]] = []
        self.coupons: list[str] = []

    def handle(
        self, method: str, path: str, headers: dict[str, str], body: dict[str, Any] | None
    ) -> tuple[int, dict[str, str], dict[str, Any]]:
        lowered = {name.lower(): value for name, value in headers.items()}
        roles = {role.strip() for role in lowered.get(ROLES_HEADER.lower(), "").split(",") if role.strip()}
        if method == "GET" and path == "/scenario/health":
            return 200, {}, {"status": "ok", "target": "funding-fake"}
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
        status, payload, account_class = self._step(body)
        response_headers: dict[str, str] = {}
        if account_class and self.simulator_headers_enabled and SIMULATOR_ROLE in roles:
            response_headers[CLASS_HEADER] = account_class
        return status, response_headers, payload

    @staticmethod
    def _problem(code: str, message: str = "") -> dict[str, Any]:
        return {"outcome": code, "code": code, "message": message}

    def _step(self, body: dict[str, Any]) -> tuple[int, dict[str, Any], str | None]:
        action = body.get("action")
        handler = self._actions.get(action) if isinstance(action, str) else None
        params = body.get("params")
        if handler is None or not isinstance(params, dict):
            return 400, self._problem("SCENARIO_ACTION_UNKNOWN"), None
        ctx = _Ctx(
            actor=str(body.get("actor", "")),
            channel=str(body.get("channel", "")),
            state=str(body.get("relationshipState", "")),
            purpose=str(body.get("purpose", "")),
            params=params,
        )
        actual_state = self._state_of(params.get("relationship"))
        if ctx.state != actual_state:
            return 409, self._problem("SCENARIO_STATE_MISMATCH", f"declared {ctx.state}, actual {actual_state}"), None
        expected_purpose = self._purpose(action, params)
        if ctx.purpose != expected_purpose:
            return 409, self._problem("SCENARIO_PURPOSE_MISMATCH", f"declared {ctx.purpose}, actual {expected_purpose}"), None
        try:
            status, payload, account_class = handler(ctx)
        except _Refused as refusal:
            status, payload, account_class = refusal.status, self._problem(refusal.code, refusal.message), refusal.account_class
        except (KeyError, TypeError, ValueError):
            return 400, self._problem("SCENARIO_PARAMS_INVALID"), None
        payload["balances"] = self._balances()
        return status, payload, account_class

    @staticmethod
    def _purpose(action: str, params: dict[str, Any]) -> str:
        if action == "proactive_send":
            return PROACTIVE_PURPOSE.get(str(params.get("kind")), "NONE")
        return PURPOSE_BY_ACTION[action]

    def _state_of(self, alias: Any) -> str:
        rel = self.relationships.get(alias) if isinstance(alias, str) else None
        return rel.state if rel else "NONE"

    def _ref(self, kind: str, label: str) -> str:
        digest = hashlib.sha256(f"{self.seed}:{kind}:{label}".encode()).hexdigest()
        return f"{kind}-{digest[:12]}"

    def _balances(self) -> dict[str, Any]:
        relationships = {
            alias: {
                "TRIAL": rel.accounts["TRIAL"].balance,
                "SETUP_GRANT": rel.accounts["SETUP_GRANT"].balance,
                "SUBSCRIPTION": rel.accounts["SUBSCRIPTION"].balance,
                "reservedPaise": sum(account.reserved for account in rel.accounts.values()),
                "openReservations": len(rel.reservations),
            }
            for alias, rel in sorted(self.relationships.items())
        }
        return {
            "ACQUISITION": self.environment_spent,
            "ACQUISITION_TENANTS": dict(sorted(self.tenant_spent.items())),
            "SIMULATION": self.simulation_spent,
            "PLATFORM_FLOOR": self.floor_spent,
            "breaker": {"open": self.environment_spent >= ENVIRONMENT_ACQUISITION_CAP_PAISE},
            "relationships": relationships,
        }

    def _rel(self, ctx: _Ctx, key: str = "relationship") -> _Relationship:
        alias = ctx.params.get(key)
        rel = self.relationships.get(alias) if isinstance(alias, str) else None
        if rel is None:
            raise _Refused(404, "RELATIONSHIP_NOT_FOUND")
        return rel

    @staticmethod
    def _reply(
        outcome: str,
        message: str = "",
        *,
        status: int = 200,
        account_class: str | None = None,
        movement: tuple[str, str, int] | None = None,
        **extra: Any,
    ) -> tuple[int, dict[str, Any], str | None]:
        body: dict[str, Any] = {"outcome": outcome, "message": message, "silent": message == ""}
        if movement and movement[2] != 0:
            body["movement"] = {"account": movement[0], "unit": movement[1], "delta": movement[2]}
        body.update(extra)
        return status, body, account_class

    def _classify(self, ctx: _Ctx, purpose: str, rel: _Relationship | None) -> str:
        account_class = resolve_account_class(purpose, rel.authority if rel else None, ctx.channel == "SIMULATION")
        if account_class != "PLATFORM_FLOOR" and not self.wbe_available:
            raise _Refused(503, "SPEND_COMMERCIAL_UNAVAILABLE", FREE_PATH_TEXT, account_class)
        return account_class

    def _charge(
        self, account_class: str, rel: _Relationship | None, tenant: str, cost: int, lead: str | None = None
    ) -> str | None:
        """Debits one call from the pinned account; returns the refusal code or None. Floor use is never refused."""
        refusal = None
        if account_class == "PLATFORM_FLOOR":
            self.floor_spent += cost
        elif account_class == "ACQUISITION":
            if self.tenant_spent.get(tenant, 0) + cost > TENANT_ACQUISITION_CAP_PAISE:
                refusal = "ACQUISITION_BUDGET_EXHAUSTED"
            elif self.environment_spent + cost > ENVIRONMENT_ACQUISITION_CAP_PAISE:
                refusal = "ACQUISITION_BUDGET_EXHAUSTED"
            else:
                self.tenant_spent[tenant] = self.tenant_spent.get(tenant, 0) + cost
                self.environment_spent += cost
        elif account_class == "SIMULATION":
            if self.simulation_spent + cost > SIMULATION_CAP_PAISE:
                refusal = "SIMULATION_BUDGET_EXHAUSTED"
            else:
                self.simulation_spent += cost
        elif rel is not None:
            account = rel.accounts[account_class]
            if account.available < cost:
                refusal = "SETUP_GRANT_EXHAUSTED" if account_class == "SETUP_GRANT" else "WALLET_EMPTY_FREE_PATH"
            else:
                account.balance -= cost
        event: dict[str, Any] = {
            "event": "spend_denied" if refusal else "spend_settled",
            "accountClass": account_class,
            "tenantId": tenant,
            "paise": 0 if refusal else cost,
        }
        if refusal:
            event["reasonCode"] = refusal
        if rel is not None:
            event["relationshipId"] = rel.relationship_id
        if lead:
            event["leadRef"] = lead
        self.telemetry.append(event)
        return refusal

    def _new_relationship(self, ctx: _Ctx, state: str, authority: str) -> _Relationship:
        params = ctx.params
        alias = str(params.get("relationship", ""))
        if not alias or alias in self.relationships:
            raise _Refused(409, "SCENARIO_ALIAS_IN_USE")
        rel = _Relationship(
            alias=alias,
            relationship_id=self._ref("rel", alias),
            customer=str(params.get("customer", "")),
            agent=str(params.get("agent", "")),
            version=str(params.get("version", "1.0.0")),
            state=state,
            authority=authority,
            pricing_version=self.current_pricing,
            price_paise=self.prices[self.current_pricing],
        )
        rel.accounts["SETUP_GRANT"].credit(SETUP_GRANT_PAISE)
        self.relationships[alias] = rel
        return rel

    @staticmethod
    def _notices(account: _Account, before: int) -> list[str]:
        after = account.used_percent()
        return [name for name, threshold in NOTICE_THRESHOLDS if before < threshold <= after]

    def _work_message(self, outcome: str, notices: list[str], actor: str) -> str:
        if actor == "BENEFICIARY":
            return BENEFICIARY_TEXT if outcome != "WORK_DONE" or notices else "Done."
        if outcome == "WORK_DONE":
            return " ".join(["Done.", *(CAPACITY_TEXT[name] for name in notices)])
        if outcome == "WORK_UNCONFIRMED":
            return "I can't confirm that finished yet; I'll tell you as soon as I know."
        return LIMITATION_TEXT

    def _do_visitor_turn(self, ctx: _Ctx) -> tuple[int, dict[str, Any], str | None]:
        if self.stopped:
            return self._reply("SUPPRESSED_AFTER_STOP")
        tenant = str(ctx.params.get("tenant", "marketplace-a"))
        lead = self._ref("lead", str(ctx.params.get("lead", "anonymous")))
        account_class = self._classify(ctx, "PRESALES_OR_MARKETPLACE", None)
        refusal = self._charge(account_class, None, tenant, VISITOR_TURN_PAISE, lead)
        if refusal:
            return self._reply(refusal, SCRIPTED_TEXT, account_class=account_class)
        return self._reply(
            "VISITOR_REPLIED",
            "Here is what I can do for you.",
            account_class=account_class,
            movement=(account_class, "PAISE", -VISITOR_TURN_PAISE),
            leadRef=lead,
        )

    def _do_web_handoff(self, ctx: _Ctx) -> tuple[int, dict[str, Any], str | None]:
        lead = self._ref("lead", str(ctx.params.get("lead", "anonymous")))
        customer = str(ctx.params.get("customer", ""))
        self.leads[customer] = lead
        return self._reply(
            "LEAD_ATTRIBUTED",
            "Welcome. Let's continue where we left off.",
            account_class=self._classify(ctx, "PRESALES_OR_MARKETPLACE", None),
            leadRef=lead,
            linkedSubject=self._ref("subj", customer),
        )

    def _do_marketplace_turn(self, ctx: _Ctx) -> tuple[int, dict[str, Any], str | None]:
        rel = self._rel(ctx)
        tenant = str(ctx.params.get("tenant", "marketplace-a"))
        account_class = self._classify(ctx, "PRESALES_OR_MARKETPLACE", rel)
        refusal = self._charge(account_class, rel, tenant, VISITOR_TURN_PAISE, self.leads.get(rel.customer))
        if refusal:
            return self._reply(refusal, SCRIPTED_TEXT, account_class=account_class)
        return self._reply(
            "MARKETPLACE_REPLIED",
            "Here is how that other agent could help.",
            account_class=account_class,
            movement=(account_class, "PAISE", -VISITOR_TURN_PAISE),
        )

    def _do_flood(self, ctx: _Ctx) -> tuple[int, dict[str, Any], str | None]:
        tenant = str(ctx.params.get("tenant", "marketplace-a"))
        account_class = self._classify(ctx, "PRESALES_OR_MARKETPLACE", None)
        served = refused = 0
        for index in range(int(ctx.params.get("visitors", 1))):
            if self._charge(account_class, None, tenant, VISITOR_TURN_PAISE, self._ref("lead", f"flood-{index}")):
                refused += 1
            else:
                served += 1
        return self._reply(
            "FLOOD_ABSORBED" if refused else "FLOOD_SERVED",
            SCRIPTED_TEXT if refused else "",
            account_class=account_class,
            movement=(account_class, "PAISE", -served * VISITOR_TURN_PAISE),
            served=served,
            refused=refused,
            exhaustedLevel="TENANT" if refused else None,
        )

    def _do_simulation_turn(self, ctx: _Ctx) -> tuple[int, dict[str, Any], str | None]:
        account_class = self._classify(ctx, "SIMULATION", None)
        refusal = self._charge(account_class, None, "simulation", VISITOR_TURN_PAISE)
        if refusal:
            return self._reply(refusal, SCRIPTED_TEXT, account_class=account_class)
        return self._reply(
            "SIMULATED_REPLIED",
            "Simulated reply.",
            account_class=account_class,
            movement=(account_class, "PAISE", -VISITOR_TURN_PAISE),
        )

    def _do_start_trial(self, ctx: _Ctx) -> tuple[int, dict[str, Any], str | None]:
        params = ctx.params
        customer, agent = str(params.get("customer", "")), str(params.get("agent", ""))
        version = str(params.get("version", "1.0.0"))
        key = (customer, agent, version)
        identity_key = (str(params.get("identity", customer)), agent, version)
        if key in self.trial_keys:
            return self._reply("TRIAL_ALREADY_USED", "You have already tried this agent.", status=409)
        claimed_by = self.identity_claims.get(identity_key)
        if claimed_by is not None and claimed_by != customer:
            return self._reply("TRIAL_ALREADY_USED_BY_IDENTITY", "This agent's trial has already been used.", status=409)
        rel = self._new_relationship(ctx, "TRIAL", "TRIAL")
        self.trial_keys.add(key)
        self.identity_claims[identity_key] = customer
        rel.accounts["TRIAL"].credit(TRIAL_GRANT_PAISE)
        return self._reply(
            "TRIAL_STARTED",
            "Your trial has started.",
            account_class="TRIAL",
            movement=("TRIAL", "PAISE", TRIAL_GRANT_PAISE),
            relationshipId=rel.relationship_id,
        )

    def _do_hire(self, ctx: _Ctx) -> tuple[int, dict[str, Any], str | None]:
        rel = self._new_relationship(ctx, "HIRED", "ACCEPTED_OFFERING")
        rel.accounts["SUBSCRIPTION"].credit(PERIOD_CREDIT_PAISE)
        return self._reply(
            "HIRED",
            "Welcome aboard.",
            account_class="SUBSCRIPTION",
            movement=("SUBSCRIPTION", "PAISE", PERIOD_CREDIT_PAISE),
            relationshipId=rel.relationship_id,
            pinnedPricingVersion=rel.pricing_version,
        )

    def _do_convert_trial(self, ctx: _Ctx) -> tuple[int, dict[str, Any], str | None]:
        rel = self._rel(ctx)
        lapsed = {}
        for name in ("TRIAL", "SETUP_GRANT"):
            account = rel.accounts[name]
            lapsed[name] = account.available
            account.balance -= account.available
        rel.state, rel.authority = "HIRED", "ACCEPTED_OFFERING"
        rel.pricing_version = self.current_pricing
        rel.price_paise = self.prices[self.current_pricing]
        rel.accounts["SUBSCRIPTION"].credit(PERIOD_CREDIT_PAISE)
        return self._reply(
            "TRIAL_CONVERTED",
            "You're now hired.",
            account_class="SUBSCRIPTION",
            movement=("SUBSCRIPTION", "PAISE", PERIOD_CREDIT_PAISE),
            relationshipId=rel.relationship_id,
            lapsed=lapsed,
            pinnedPricingVersion=rel.pricing_version,
        )

    def _do_expire_trial(self, ctx: _Ctx) -> tuple[int, dict[str, Any], str | None]:
        rel = self._rel(ctx)
        for account in rel.accounts.values():
            account.balance -= account.available
        rel.state, rel.authority = "ENDED", "NONE"
        return self._reply("TRIAL_EXPIRED", "Your trial has ended.")

    def _do_renew(self, ctx: _Ctx) -> tuple[int, dict[str, Any], str | None]:
        rel = self._rel(ctx)
        account = rel.accounts["SUBSCRIPTION"]
        lapsed = account.available
        account.balance -= lapsed
        account.credited = 0
        account.credit(PERIOD_CREDIT_PAISE)
        rel.pricing_version = self.current_pricing
        rel.price_paise = self.prices[self.current_pricing]
        return self._reply(
            "RENEWED",
            "Renewed for the next period.",
            account_class="SUBSCRIPTION",
            movement=("SUBSCRIPTION", "PAISE", PERIOD_CREDIT_PAISE),
            lapsedPaise=lapsed,
            pinnedPricingVersion=rel.pricing_version,
            pricePaise=rel.price_paise,
        )

    def _do_work_turn(self, ctx: _Ctx) -> tuple[int, dict[str, Any], str | None]:
        rel = self._rel(ctx)
        account_class = self._classify(ctx, "AGENT_WORK", rel)
        component = ctx.params.get("component")
        fault = ctx.params.get("fault")
        tenant = str(ctx.params.get("tenant", "marketplace-a"))
        account = rel.accounts.get(account_class)
        before = account.used_percent() if account else 0
        served, outcome = 0, "WORK_DONE"
        for _ in range(int(ctx.params.get("repeat", 1))):
            if component and rel.used.get(component, 0) >= COMPONENT_QUANTITY.get(rel.state, 0):
                outcome = "COMPONENT_LIMIT_REACHED"
                break
            if fault == "TIMEOUT" and account is not None:
                if account.available < WORK_TURN_PAISE:
                    outcome = "WALLET_EMPTY_FREE_PATH"
                    break
                account.reserved += WORK_TURN_PAISE
                rel.reservations.append({"class": account_class, "paise": WORK_TURN_PAISE})
                outcome = "WORK_UNCONFIRMED"
                break
            refusal = self._charge(account_class, rel, tenant, WORK_TURN_PAISE)
            if refusal:
                outcome = refusal
                break
            served += 1
            if component:
                rel.used[component] = rel.used.get(component, 0) + 1
        notices = self._notices(account, before) if account and served else []
        extra: dict[str, Any] = {}
        if notices:
            extra.update(notices=notices, noticeDelivery="NEXT_TURN")
        if rel.reservations:
            extra["reservation"] = {"open": len(rel.reservations), "pinnedClass": rel.reservations[0]["class"]}
        if component:
            extra["componentUnitsUsed"] = rel.used.get(component, 0)
        return self._reply(
            outcome,
            self._work_message(outcome, notices, ctx.actor),
            account_class=account_class,
            movement=(account_class, "PAISE", -served * WORK_TURN_PAISE),
            served=served,
            **extra,
        )

    def _do_reconcile(self, ctx: _Ctx) -> tuple[int, dict[str, Any], str | None]:
        rel = self._rel(ctx)
        if not rel.reservations:
            raise _Refused(409, "NO_OPEN_RESERVATION")
        reservation = rel.reservations.pop(0)
        account = rel.accounts[reservation["class"]]
        account.reserved -= reservation["paise"]
        account.balance -= reservation["paise"]
        return self._reply(
            "WORK_CONFIRMED",
            "That finished.",
            account_class=reservation["class"],
            movement=(reservation["class"], "PAISE", -reservation["paise"]),
            pinnedClass=reservation["class"],
        )

    def _do_time_access_session(self, ctx: _Ctx) -> tuple[int, dict[str, Any], str | None]:
        self._rel(ctx)
        return self._reply(
            "SESSION_RECORDED",
            "Session recorded.",
            ticks=int(ctx.params.get("ticks", 0)),
            reservationsCreated=0,
            unitsConsumed=0,
        )

    def _do_voice_note(self, ctx: _Ctx) -> tuple[int, dict[str, Any], str | None]:
        self._rel(ctx)
        return self._reply("VOICE_UNAVAILABLE", LIMITATION_TEXT, catalogueStatus="PENDING_FOUNDER_AUTH")

    def _do_onboarding_turn(self, ctx: _Ctx) -> tuple[int, dict[str, Any], str | None]:
        rel = self._rel(ctx)
        account_class = self._classify(ctx, "ONBOARDING", rel)
        tenant = str(ctx.params.get("tenant", "marketplace-a"))
        used_class, served, outcome = account_class, 0, "ONBOARDING_DONE"
        for _ in range(int(ctx.params.get("repeat", 1))):
            used_class = account_class
            exhausted = account_class == "SETUP_GRANT" and rel.accounts["SETUP_GRANT"].available < ONBOARDING_TURN_PAISE
            if exhausted and rel.setup_acknowledged and rel.state == "HIRED":
                used_class = "SUBSCRIPTION"
            refusal = self._charge(used_class, rel, tenant, ONBOARDING_TURN_PAISE)
            if refusal == "SETUP_GRANT_EXHAUSTED":
                rel.setup_told = True
            if refusal:
                outcome = refusal
                break
            served += 1
        message = LIMITATION_TEXT if outcome != "ONBOARDING_DONE" else "Setup step done."
        return self._reply(
            outcome,
            message,
            account_class=used_class,
            movement=(used_class, "PAISE", -served * ONBOARDING_TURN_PAISE),
            served=served,
            continuesOnSubscription=outcome == "ONBOARDING_DONE" and used_class == "SUBSCRIPTION",
        )

    def _do_acknowledge_setup_exhaustion(self, ctx: _Ctx) -> tuple[int, dict[str, Any], str | None]:
        rel = self._rel(ctx)
        if not rel.setup_told:
            raise _Refused(409, "SETUP_EXHAUSTION_NOT_DISCLOSED")
        rel.setup_acknowledged = True
        return self._reply("SETUP_EXHAUSTION_ACKNOWLEDGED", "Understood; we'll carry on setting up.")

    def _do_connect_account(self, ctx: _Ctx) -> tuple[int, dict[str, Any], str | None]:
        rel = self._rel(ctx)
        if ctx.params.get("result") != "VERIFIED":
            return self._reply("CONNECTION_FAILED", "That connection didn't work, so nothing was used up.", slotsUsed=rel.slots)
        if rel.slots >= SLOT_MAXIMUM:
            return self._reply("SLOT_LIMIT_REACHED", LIMITATION_TEXT, slotsUsed=rel.slots)
        rel.slots += 1
        return self._reply("CONNECTION_VERIFIED", "Connected.", slotsUsed=rel.slots)

    def _do_switch_request(self, ctx: _Ctx) -> tuple[int, dict[str, Any], str | None]:
        self._rel(ctx)
        self._rel(ctx, "requested")
        return self._reply(
            "FOCUS_SWITCH_OFFERED",
            "I'm focused on a different agent right now. Would you like to switch?",
            agentWorkCharged=False,
            focusedRelationship=ctx.params.get("relationship"),
        )

    def _do_pause_skill(self, ctx: _Ctx) -> tuple[int, dict[str, Any], str | None]:
        self._rel(ctx)
        share = int(ctx.params["feeSharePaise"])
        remaining = int(ctx.params["remainingSeconds"])
        period = int(ctx.params["periodSeconds"])
        refund = (share * remaining * 2 + period) // (2 * period)
        return self._reply(
            "SKILL_PAUSED",
            "That skill is paused.",
            billingAdjustment={"refundFeePaise": refund, "mode": "BILLING_ADJUSTMENT"},
            walletRefund=False,
        )

    def _do_emergency_stop(self, ctx: _Ctx) -> tuple[int, dict[str, Any], str | None]:
        account_class = self._classify(ctx, "SAFETY_FLOOR", None)
        self._charge(account_class, None, "platform", FLOOR_USE_PAISE)
        first = not self.stopped
        self.stopped = True
        message = ""
        if first and self._policy.stop_acknowledges:
            message = self._policy.stop_acknowledgement
            self.stop_acknowledgements += 1
        return self._reply(
            "STOP_ACKNOWLEDGED" if first else "STOP_ALREADY_ACKNOWLEDGED",
            message,
            account_class=account_class,
            movement=(account_class, "PAISE", -FLOOR_USE_PAISE),
            acknowledgements=self.stop_acknowledgements,
        )

    def _do_start_message(self, ctx: _Ctx) -> tuple[int, dict[str, Any], str | None]:
        self.stopped = False
        return self._reply(
            "START_NOTICE_SENT", self._policy.start_notice, consentRequiredAgain=self._policy.start_requires_consent
        )

    def _do_wbe_fault(self, ctx: _Ctx) -> tuple[int, dict[str, Any], str | None]:
        self.wbe_available = bool(ctx.params.get("available", True))
        return self._reply("FAULT_SET", wbeAvailable=self.wbe_available)

    def _do_proactive_send(self, ctx: _Ctx) -> tuple[int, dict[str, Any], str | None]:
        rel = self._rel(ctx)
        kind, count = str(ctx.params.get("kind")), int(ctx.params.get("count", 1))
        if kind != "AGENT_ALERT":
            account_class = self._classify(ctx, "SAFETY_FLOOR", rel)
            for _ in range(count):
                self._charge(account_class, rel, "platform", FLOOR_USE_PAISE)
            return self._reply(
                "PROACTIVE_SENT",
                "Alert sent.",
                account_class=account_class,
                movement=(account_class, "PAISE", -count * FLOOR_USE_PAISE),
                counted=False,
            )
        account_class = self._classify(ctx, "AGENT_WORK", rel)
        allowance = PROACTIVE_ALLOWANCE if rel.state == "HIRED" else 0
        sent = max(0, min(count, allowance - rel.proactive_used))
        rel.proactive_used += sent
        outcome = "PROACTIVE_SENT" if sent == count else "PROACTIVE_ALLOWANCE_EXHAUSTED"
        return self._reply(
            outcome,
            "Alert sent." if sent == count else "I'll tell you in the portal and in our next chat instead.",
            account_class=account_class,
            movement=(account_class, "MESSAGES", -sent),
            sent=sent,
            proactive={"used": rel.proactive_used, "allowance": allowance},
            deliveredIn=None if sent == count else "PORTAL_AND_NEXT_TURN",
        )

    def _do_goodwill(self, ctx: _Ctx) -> tuple[int, dict[str, Any], str | None]:
        self._rel(ctx)
        if ctx.actor != "SUPPORT":
            raise _Refused(403, "GOODWILL_FORBIDDEN")
        if ctx.params.get("kind") != "COUPON":
            raise _Refused(403, "GOODWILL_WALLET_CREDIT_FORBIDDEN")
        code = f"GOODWILL-{self._ref('c', str(len(self.coupons)))[2:10].upper()}"
        self.coupons.append(code)
        return self._reply("COUPON_ISSUED", "We've sent you a coupon for the next hire.", couponCode=code)

    def _do_request_topup(self, ctx: _Ctx) -> tuple[int, dict[str, Any], str | None]:
        rel = self._rel(ctx)
        if ctx.actor == "BENEFICIARY":
            raise _Refused(403, "TOPUP_NOT_PERMITTED", BENEFICIARY_TEXT)
        rel.accounts["SUBSCRIPTION"].credit(TOPUP_PAISE)
        return self._reply(
            "TOPUP_APPLIED",
            "This agent's work allowance has been topped up.",
            account_class="SUBSCRIPTION",
            movement=("SUBSCRIPTION", "PAISE", TOPUP_PAISE),
        )

    def _do_publish_pricing(self, ctx: _Ctx) -> tuple[int, dict[str, Any], str | None]:
        if ctx.actor != "FOUNDER":
            raise _Refused(403, "PRICING_FORBIDDEN")
        version = str(ctx.params["versionId"])
        self.prices[version] = int(ctx.params["priceInclGstPaise"])
        self.current_pricing = version
        return self._reply("PRICING_EFFECTIVE", currentVersion=version)

    def _do_read_relationship(self, ctx: _Ctx) -> tuple[int, dict[str, Any], str | None]:
        rel = self._rel(ctx)
        return self._reply(
            "RELATIONSHIP_READ",
            pinnedPricingVersion=rel.pricing_version,
            pricePaise=rel.price_paise,
            currentPricingVersion=self.current_pricing,
            relationshipId=rel.relationship_id,
        )

    def _do_render_for(self, ctx: _Ctx) -> tuple[int, dict[str, Any], str | None]:
        rel = self._rel(ctx)
        if ctx.params.get("audience") == "BENEFICIARY":
            return self._reply("RENDERED_FOR_BENEFICIARY", "Your session is ready.", controls=[])
        account = rel.accounts["SUBSCRIPTION" if rel.state == "HIRED" else "TRIAL"]
        component = str(ctx.params.get("component", "POSTS"))
        remaining = COMPONENT_QUANTITY.get(rel.state, 0) - rel.used.get(component, 0)
        percent = account.used_percent()
        return self._reply(
            "RENDERED_FOR_OWNER",
            f"{remaining} {component.lower()} left; the work allowance is {percent}% used.",
            controls=["TOPUP_THIS_AGENT"] if percent >= 85 else [],
        )

    def _do_read_telemetry(self, ctx: _Ctx) -> tuple[int, dict[str, Any], str | None]:
        return self._reply("TELEMETRY_READ", telemetry=list(self.telemetry[-5:]), count=len(self.telemetry))
