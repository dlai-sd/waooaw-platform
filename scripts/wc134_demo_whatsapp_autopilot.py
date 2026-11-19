#!/usr/bin/env python3
"""Re-activate Demo WhatsApp after a deployment, strictly inside the Founder's standing policy.

Every Demo apply resets the WhatsApp switches. Instead of asking for a fresh per-bundle approval,
the Founder approves ``release/wc134/demo-whatsapp-activation-policy.json`` once by merging it.
This script then rebuilds the activation bundle from that policy plus evidence observed during this
exact run, refuses any bundle that is not inside the policy, activates through the existing
``wc133_whatsapp_operations.py`` tooling, proves the result, and stops WhatsApp again on any failure.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from wc120_whatsapp_activation import activation_configuration_digest

POLICY_SCHEMA = "waooaw.demo-whatsapp-standing-policy/v1"
APPROVER = "dlai-sd"
MAXIMUM_WINDOW_DAYS = 14
MAXIMUM_SPEND_PAISE = 50_000
RESOURCE_GROUP = "waooaw-demo-rg"
VAULT = "kv-waooaw-demo"
RULE_NAME = "waooaw-demo-whatsapp-operations"
ACTION_GROUP = "wc134-demo-operator"
WORKSPACE = "law-waooaw-demo-validation"
API_HOST = "api.demo.waooaw.com"
CALLBACK_HOST = "whatsapp-demo.waooaw.com"
RECEIPTS = (
    "qualification",
    "zero_traffic_deployment",
    "provider_registration",
    "credential_scope",
    "consent",
    "stop",
    "alerts",
    "rollback",
    "pricing",
)
PROVIDER_SECRETS = (
    "whatsapp-provider-binding",
    "whatsapp-verify-token",
    "whatsapp-app-secret",
    "whatsapp-outbound-authority",
    "whatsapp-phone-subject-hmac",
)
TRAFFIC_FLAGS = (
    "IdentityVerification__WhatsApp__Enabled",
    "Wc120Conversation__CallbackAcceptanceEnabled",
    "Wc120Conversation__DispatchEnabled",
    "WhatsAppCapability__Authority__AllowProvisionalOnboarding",
    "WhatsAppCapability__Authority__AllowPublicAdmission",
    "WhatsAppCapability__Authority__AllowRegistrationVerification",
    "WhatsAppCapability__ProviderAvailable",
    "WhatsApp__CallbackAcceptanceEnabled",
    "WhatsApp__DispatchEnabled",
)
REFERENCE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9:._/-]{0,255}$")
UUID_TEXT = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class AutopilotError(RuntimeError):
    """A refusal that must fail the deployment and leave WhatsApp stopped."""


def canonical(document: Any) -> bytes:
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode()


def digest(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _closed(value: Any, keys: set[str], name: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise AutopilotError(f"{name} must contain exactly {sorted(keys)}")
    return value


def _number(value: Any, name: str) -> Decimal:
    if type(value) not in (int, float) or isinstance(value, bool) or value <= 0:
        raise AutopilotError(f"{name} must be a positive number")
    return Decimal(str(value))


def load_policy(raw: bytes) -> dict[str, Any]:
    """Validate the Founder-merged standing policy; anything unexpected fails closed."""
    try:
        policy = json.loads(raw)
    except ValueError as error:
        raise AutopilotError("standing policy is not valid JSON") from error
    _closed(
        policy,
        {"schema", "approval", "cohort", "window_days", "limits", "tenant_id", "references", "policies", "template"},
        "standing policy",
    )
    if policy["schema"] != POLICY_SCHEMA:
        raise AutopilotError("standing policy schema is unsupported")
    approval = _closed(policy["approval"], {"approved_by", "basis"}, "approval")
    if approval["approved_by"] != APPROVER or not isinstance(approval["basis"], str) or not approval["basis"]:
        raise AutopilotError("standing policy must be approved by the Founder")
    cohort = _closed(policy["cohort"], {"allow_public_admission", "allow_provisional_onboarding"}, "cohort")
    if not all(type(value) is bool for value in cohort.values()):
        raise AutopilotError("cohort flags must be booleans")
    if cohort["allow_public_admission"] and not cohort["allow_provisional_onboarding"]:
        raise AutopilotError("public admission requires provisional onboarding")
    days = policy["window_days"]
    if type(days) is not int or not 1 <= days <= MAXIMUM_WINDOW_DAYS:
        raise AutopilotError(f"window_days must be 1 to {MAXIMUM_WINDOW_DAYS}")
    limits = _closed(
        policy["limits"],
        {"maximum_messages", "maximum_messages_per_minute", "maximum_spend_inr", "maximum_cost_per_message_inr"},
        "limits",
    )
    count, rate = limits["maximum_messages"], limits["maximum_messages_per_minute"]
    if type(count) is not int or type(rate) is not int or not 0 < rate <= count <= 1_000_000:
        raise AutopilotError("message limits must be positive integers with rate <= total")
    spend = _number(limits["maximum_spend_inr"], "maximum_spend_inr")
    cost = _number(limits["maximum_cost_per_message_inr"], "maximum_cost_per_message_inr")
    if spend * 100 != int(spend * 100) or not 0 < int(spend * 100) <= MAXIMUM_SPEND_PAISE:
        raise AutopilotError("maximum_spend_inr must be whole paise and at most INR 500")
    if cost > spend:
        raise AutopilotError("per-message cost cannot exceed the spend limit")
    tenant = policy["tenant_id"]
    if not isinstance(tenant, str) or not UUID_TEXT.fullmatch(tenant) or tenant == str(uuid.UUID(int=0)):
        raise AutopilotError("tenant_id must be a nonzero canonical UUID")
    references = _closed(policy["references"], {"consent", "incident_owner", "alert_route"}, "references")
    if not all(isinstance(value, str) and REFERENCE.fullmatch(value) for value in references.values()):
        raise AutopilotError("references must be valid identifiers")
    policies = _closed(
        policy["policies"],
        {"PolicyVersion", "InstitutionalPolicyVersion", "InteractionPolicyVersion", "ChannelRenderingPolicyVersion"},
        "policies",
    )
    if not all(isinstance(value, str) and REFERENCE.fullmatch(value) for value in policies.values()):
        raise AutopilotError("policy versions must be valid identifiers")
    template = _closed(policy["template"], {"Name", "Version", "Locale", "Category", "Body"}, "template")
    if not all(isinstance(value, str) and value for value in template.values()):
        raise AutopilotError("template fields must be non-empty text")
    return policy


def spend_arguments(raw: bytes) -> dict[str, Any]:
    """Provisioner arguments derived from the approved policy."""
    policy = load_policy(raw)
    paise = int(Decimal(str(policy["limits"]["maximum_spend_inr"])) * 100)
    evidence = uuid.uuid5(uuid.NAMESPACE_URL, "waooaw:wc134:demo-spend-authority:" + hashlib.sha256(raw).hexdigest())
    return {"paise": paise, "evidence_id": str(evidence)}


def activation_window(now: datetime, days: int) -> tuple[str, str]:
    starts = (now - timedelta(minutes=1)).replace(second=0, microsecond=0)
    return starts.strftime(TIME_FORMAT), (starts + timedelta(days=days)).strftime(TIME_FORMAT)


def binding_digests(binding: dict[str, Any]) -> dict[str, str]:
    """One-way sender, app and account fingerprints; raw identifiers never leave this function."""

    def field(name: str) -> str:
        value = binding.get(name) or binding.get(name[0].lower() + name[1:])
        if not isinstance(value, str) or not value:
            raise AutopilotError(f"provider binding lacks {name}")
        return value

    def sha(value: str) -> str:
        return hashlib.sha256(value.encode()).hexdigest()

    return {
        "AppBindingDigest": sha(field("AppId")),
        "WabaBindingDigest": sha(field("WabaId")),
        "RecipientBindingDigest": sha(field("PhoneNumberId")),
        "ContactDigest": field("RecipientBindingDigest"),
    }


def render_alert_query(
    template: str, *, starts_at: str, expires_at: str, activation_digest: str, release: str, configuration: str
) -> str:
    values = {
        "starts_at": starts_at,
        "expires_at": expires_at,
        "activation_digest": activation_digest,
        "release_digest": release,
        "configuration_digest": configuration,
    }
    for key, value in values.items():
        template = template.replace("${" + key + "}", value)
    if "${" in template:
        raise AutopilotError("alert query template has unresolved placeholders")
    return template


def build_receipts(facts: dict[str, Any], expires_at: str, run: str) -> tuple[dict[str, bytes], dict[str, dict[str, str]]]:
    """Nine readiness receipts, each digesting only facts observed in this run."""
    documents = {
        "qualification": {
            "kind": "release-qualification",
            "ci_run_id": facts["release_run_id"],
            "release_sha": facts["release_sha"],
            "selected_by": "deploy.yaml authorize job: current main head with a successful CI run and attested release artifact",
            "release_digest": facts["release_digest"],
        },
        "zero_traffic_deployment": {
            "kind": "zero-traffic-deployment",
            "deploy_run": run,
            "traffic_flags_before_activation": facts["traffic_flags_before"],
            "release_digest": facts["release_digest"],
        },
        "provider_registration": {
            "kind": "provider-registration",
            "operation": "status",
            "result": facts["status"],
        },
        "credential_scope": {
            "kind": "credential-scope",
            "identity": facts["business_identity"],
            "assignments": facts["role_assignments"],
        },
        "consent": {
            "kind": "consent",
            "implementation": facts["consent_implementation"],
            "scope": "user-initiated replies only; consent notice before discovery; STOP opts out",
        },
        "stop": {
            "kind": "stop",
            "operator_stop": facts["stop"],
        },
        "alerts": {
            "kind": "alerts",
            "rule": facts["alert_rule"],
            "owner": "Founder dlai-sd",
        },
        "rollback": {
            "kind": "rollback",
            "action": "wc133_whatsapp_operations.py stop",
            "tested_in_this_run": facts["stop"],
            "release_digest": facts["release_digest"],
        },
        "pricing": {
            "kind": "pricing",
            "approved_by": "Founder dlai-sd via standing policy",
            "policy_digest": facts["policy_digest"],
            "limits": facts["limits"],
        },
    }
    raw = {name: canonical(document) for name, document in documents.items()}
    prerequisites = {
        name: {"reference": f"{name.upper().replace('_', '-')}-{run}", "digest": digest(raw[name]), "expires_at": expires_at}
        for name in RECEIPTS
    }
    return raw, prerequisites


def build_profile(
    policy: dict[str, Any],
    bindings: dict[str, str],
    prerequisites: dict[str, dict[str, str]],
    window: tuple[str, str],
    run: str,
) -> dict[str, Any]:
    limits = policy["limits"]
    return {
        "authority": {
            "ActivationReference": f"ACT-WC134-DEMO-{run}",
            "ExternalTrafficReference": f"EXT-WC134-DEMO-{run}",
            "ConsentReference": policy["references"]["consent"],
            "IncidentOwnerReference": policy["references"]["incident_owner"],
            "AlertRouteReference": policy["references"]["alert_route"],
            "RollbackDigest": prerequisites["rollback"]["digest"],
            "TenantId": policy["tenant_id"],
            "RecipientBindingDigest": bindings["ContactDigest"],
            "StartsAt": window[0],
            "ExpiresAt": window[1],
            "MaximumMessages": limits["maximum_messages"],
            "MaximumMessagesPerMinute": limits["maximum_messages_per_minute"],
            "MaximumSpendInr": limits["maximum_spend_inr"],
            "MaximumCostPerMessageInr": limits["maximum_cost_per_message_inr"],
            "AllowProvisionalOnboarding": policy["cohort"]["allow_provisional_onboarding"],
            "AllowPublicAdmission": policy["cohort"]["allow_public_admission"],
        },
        "binding_digests": {key: bindings[key] for key in ("AppBindingDigest", "WabaBindingDigest", "RecipientBindingDigest")},
        "policies": policy["policies"],
        "templates": [policy["template"]],
        "prerequisites": prerequisites,
    }


def verify_candidate(bundle: bytes, policy: dict[str, Any], now: datetime) -> None:
    """Refuse any assembled bundle that is not inside the Founder's standing policy."""
    document = json.loads(bundle)
    authority = document["authority"]
    limits = policy["limits"]
    expected = {
        "TenantId": policy["tenant_id"],
        "MaximumMessages": limits["maximum_messages"],
        "MaximumMessagesPerMinute": limits["maximum_messages_per_minute"],
        "MaximumSpendInr": limits["maximum_spend_inr"],
        "MaximumCostPerMessageInr": limits["maximum_cost_per_message_inr"],
        "AllowProvisionalOnboarding": policy["cohort"]["allow_provisional_onboarding"],
        "AllowPublicAdmission": policy["cohort"]["allow_public_admission"],
        "ConsentReference": policy["references"]["consent"],
        "IncidentOwnerReference": policy["references"]["incident_owner"],
        "AlertRouteReference": policy["references"]["alert_route"],
        "Revoked": False,
        "Environment": "demo",
    }
    for key, value in expected.items():
        if authority.get(key) != value:
            raise AutopilotError(f"candidate differs from the standing policy at {key}")
    if authority.get("AllowRegistrationVerification", False):
        raise AutopilotError("candidate enables registration verification, which the policy does not approve")
    starts = datetime.strptime(authority["StartsAt"], TIME_FORMAT).replace(tzinfo=timezone.utc)
    expires = datetime.strptime(authority["ExpiresAt"], TIME_FORMAT).replace(tzinfo=timezone.utc)
    if not starts <= now < expires or expires - starts > timedelta(days=policy["window_days"]):
        raise AutopilotError("candidate window is outside the standing policy")
    if document["templates"] != [policy["template"]] or document["policies"] != policy["policies"]:
        raise AutopilotError("candidate templates or policy versions differ from the standing policy")
    if set(document["prerequisites"]) != set(RECEIPTS):
        raise AutopilotError("candidate lacks the nine readiness receipts")


class Autopilot:
    """Orchestrates the activation; every external effect goes through an injected callable."""

    def __init__(
        self,
        *,
        policy_bytes: bytes,
        alert_template: str,
        consent_files: dict[str, bytes],
        operation: Callable[[str, bytes, str, str], dict[str, Any]],
        az: Callable[..., Any],
        http_status: Callable[[str], int],
        log_query: Callable[[str], list[Any]],
        clock: Callable[[], datetime],
        sleep: Callable[[float], None],
        run: str,
        release_run_id: str,
        release_sha: str,
        heartbeat_timeout: float = 600.0,
    ) -> None:
        self.policy_bytes = policy_bytes
        self.policy = load_policy(policy_bytes)
        self.alert_template = alert_template
        self.consent_files = consent_files
        self.operation = operation
        self.az = az
        self.http_status = http_status
        self.log_query = log_query
        self.clock = clock
        self.sleep = sleep
        self.run = run
        self.release_run_id = release_run_id
        self.release_sha = release_sha
        self.heartbeat_timeout = heartbeat_timeout
        self.evidence: dict[str, Any] = {}
        self.rule_body: dict[str, Any] | None = None

    def activate(self) -> dict[str, Any]:
        try:
            return self._activate()
        except BaseException:
            # Any refusal leaves WhatsApp stopped rather than half active.
            try:
                self.operation("stop", b"{}", "", self.run)
            finally:
                self._set_rule_enabled(False)
            raise

    def _activate(self) -> dict[str, Any]:
        status = self.operation("status", b"{}", "", self.run)
        if status.get("status") != "PASS" or status.get("registration_runtime_matches") is not True:
            raise AutopilotError("provider registration does not match the deployed runtime")
        if status.get("credential_metadata") != "READY":
            raise AutopilotError("provider credential metadata is not ready")
        stop = self.operation("stop", b"{}", "", self.run)
        flags = stop.get("traffic_flags", {})
        if any(str(flags.get(name, "")).lower() == "true" for name in TRAFFIC_FLAGS):
            raise AutopilotError("stop operation left a traffic switch on")
        registration = status["registration"]
        release = registration["release_digest"]
        bindings = binding_digests(self._binding(status))
        now = self.clock()
        window = activation_window(now, self.policy["window_days"])
        activation_reference = f"ACT-WC134-DEMO-{self.run}"
        activation_digest = hashlib.sha256(activation_reference.encode()).hexdigest()
        configuration = activation_configuration_digest(
            registration["configuration_digest"],
            {key: bindings[key] for key in ("AppBindingDigest", "WabaBindingDigest", "RecipientBindingDigest")},
            self.policy["policies"],
            [self.policy["template"]],
        )
        query = render_alert_query(
            self.alert_template,
            starts_at=window[0],
            expires_at=window[1],
            activation_digest=activation_digest,
            release=release,
            configuration=configuration,
        )
        rule = self._put_rule(query, enabled=False)
        facts = {
            "release_run_id": self.release_run_id,
            "release_sha": self.release_sha,
            "release_digest": release,
            "traffic_flags_before": {name: str(status.get("traffic_flags", {}).get(name, "")) for name in TRAFFIC_FLAGS},
            "status": {
                key: status[key]
                for key in (
                    "status",
                    "registration_runtime_matches",
                    "credential_metadata",
                    "registration",
                    "verification_enabled",
                )
                if key in status
            },
            "business_identity": "id-demo-business-platform",
            "role_assignments": self._role_assignments(),
            "consent_implementation": {name: digest(raw) for name, raw in sorted(self.consent_files.items())},
            "stop": {key: stop[key] for key in ("status", "operation", "traffic_flags") if key in stop},
            "alert_rule": {
                "name": RULE_NAME,
                "query_digest": digest(query.encode()),
                "evaluation_frequency": rule["properties"]["evaluationFrequency"],
                "window_size": rule["properties"]["windowSize"],
                "action_group": ACTION_GROUP,
                "starts_at": window[0],
                "expires_at": window[1],
            },
            "policy_digest": digest(self.policy_bytes),
            "limits": self.policy["limits"],
        }
        documents, prerequisites = build_receipts(facts, window[1], self.run)
        profile = canonical(build_profile(self.policy, bindings, prerequisites, window, self.run))
        candidate = self.operation("assemble", profile, "", self.run)
        bundle = candidate["bundle"]
        verify_candidate(bundle, self.policy, self.clock())
        if json.loads(bundle)["authority"]["ConfigurationDigest"] != configuration:
            raise AutopilotError("assembled configuration digest differs from the alert rule's digest")
        # Approval is the policy's: the digest binds exactly the bytes that just passed verify_candidate.
        approved = digest(bundle)
        self.operation("activate", json.dumps({"candidate_reference": self.run}).encode(), approved, self.run)
        self._set_rule_enabled(True)
        self._prove(activation_digest)
        self.evidence = {
            "schema": "waooaw.demo-whatsapp-autopilot/v1",
            "run": self.run,
            "policy_digest": digest(self.policy_bytes),
            "approved_bundle_digest": approved,
            "activation_reference": activation_reference,
            "window": {"starts_at": window[0], "expires_at": window[1]},
            "receipts": {name: prerequisites[name]["digest"] for name in RECEIPTS},
            "receipt_documents": {name: documents[name].decode() for name in RECEIPTS},
        }
        return self.evidence

    def _binding(self, status: dict[str, Any]) -> dict[str, Any]:
        version = status["provider"]["secret_versions"]["whatsapp-provider-binding"]
        value = self.az(
            "keyvault",
            "secret",
            "show",
            "--vault-name",
            VAULT,
            "--name",
            "whatsapp-provider-binding",
            "--version",
            version,
            "--query",
            "value",
        )
        return json.loads(value)

    def _role_assignments(self) -> list[dict[str, str]]:
        principal = self.az(
            "identity",
            "show",
            "--resource-group",
            RESOURCE_GROUP,
            "--name",
            "id-demo-business-platform",
            "--query",
            "principalId",
        )
        subscription = self.az("account", "show", "--query", "id")
        base = (
            f"/subscriptions/{subscription}/resourceGroups/{RESOURCE_GROUP}/providers/Microsoft.KeyVault/vaults/{VAULT}/secrets"
        )
        found = []
        for secret in PROVIDER_SECRETS:
            scope = f"{base}/{secret}"
            listed = self.az(
                "role",
                "assignment",
                "list",
                "--assignee-object-id",
                principal,
                "--scope",
                scope,
                "--fill-principal-name",
                "false",
            )
            roles = sorted(item["roleDefinitionName"] for item in listed if item["scope"].lower() == scope.lower())
            if roles != ["Key Vault Secrets User"]:
                raise AutopilotError(f"Business Platform does not hold exactly Key Vault Secrets User on {secret}")
            found.append({"secret": secret, "role": roles[0]})
        return found

    def _rule_url(self) -> str:
        subscription = self.az("account", "show", "--query", "id")
        return (
            f"https://management.azure.com/subscriptions/{subscription}/resourceGroups/{RESOURCE_GROUP}"
            f"/providers/Microsoft.Insights/scheduledQueryRules/{RULE_NAME}?api-version=2023-03-15-preview"
        )

    def _put_rule(self, query: str, *, enabled: bool) -> dict[str, Any]:
        subscription = self.az("account", "show", "--query", "id")
        group = f"/subscriptions/{subscription}/resourceGroups/{RESOURCE_GROUP}/providers/microsoft.insights/actionGroups/{ACTION_GROUP}"
        workspace = f"/subscriptions/{subscription}/resourceGroups/{RESOURCE_GROUP}/providers/Microsoft.OperationalInsights/workspaces/{WORKSPACE}"
        self.az("monitor", "action-group", "show", "--resource-group", RESOURCE_GROUP, "--name", ACTION_GROUP, "--query", "id")
        body = {
            "location": "centralindia",
            "tags": {"work_contract": "WC-134"},
            "properties": {
                "description": "WC-134 bounded operational breaches and missing evaluator heartbeat",
                "severity": 1,
                "enabled": enabled,
                "evaluationFrequency": "PT5M",
                "windowSize": "PT5M",
                "scopes": [workspace],
                "autoMitigate": True,
                "criteria": {
                    "allOf": [
                        {
                            "query": query,
                            "timeAggregation": "Count",
                            "operator": "GreaterThan",
                            "threshold": 0,
                            "failingPeriods": {"numberOfEvaluationPeriods": 1, "minFailingPeriodsToAlert": 1},
                        }
                    ]
                },
                "actions": {"actionGroups": [group]},
            },
        }
        self.rule_body = body
        return self.az("rest", "--method", "put", "--url", self._rule_url(), "--body", json.dumps(body))

    def _set_rule_enabled(self, enabled: bool) -> None:
        body = self.rule_body
        if body is None:
            return
        body["properties"]["enabled"] = enabled
        self.az("rest", "--method", "put", "--url", self._rule_url(), "--body", json.dumps(body))

    def _prove(self, activation_digest: str) -> None:
        deadline = self.clock() + timedelta(seconds=self.heartbeat_timeout)
        started = self.clock().strftime(TIME_FORMAT)
        if self.http_status(f"https://{API_HOST}/health/ready") != 200:
            raise AutopilotError("Business Platform readiness is not 200 after activation")
        invalid = uuid.uuid4().hex
        webhook = f"https://{CALLBACK_HOST}/api/v1/channels/whatsapp/webhook?hub.mode=subscribe&hub.challenge=autopilot&hub.verify_token={invalid}"
        if self.http_status(webhook) != 401:
            raise AutopilotError("WhatsApp webhook does not reject an invalid verification token")
        beat = (
            "ContainerAppConsoleLogs_CL | where TimeGenerated > datetime(" + started + ") "
            "and ContainerAppName_s == 'ca-demo-business-platform' "
            f"and Log_s has 'WC134_OBSERVATION' and Log_s has '{activation_digest}' | count"
        )
        broken = (
            "ContainerAppConsoleLogs_CL | where TimeGenerated > datetime(" + started + ") "
            "and ContainerAppName_s == 'ca-demo-business-platform' and Log_s has '42501' | count"
        )
        while True:
            if self._count(self.log_query(broken)):
                raise AutopilotError("Business Platform logged database permission errors after activation")
            if self._count(self.log_query(beat)):
                return
            if self.clock() >= deadline:
                raise AutopilotError("no operations heartbeat for the new activation was observed in time")
            self.sleep(30)

    @staticmethod
    def _count(rows: list[Any]) -> int:
        if not rows:
            return 0
        first = rows[0]
        value = first.get("Count") if isinstance(first, dict) else first
        return int(value or 0)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def provider_failure_summary(stdout: str, stderr: str, evidence_path: Path) -> str:
    """Bounded, credential-free reason for a failed provider phase.

    The provider prints its classified command failure before its generic closing line, so the
    last line alone hides which Azure or Terraform stage failed and why.
    """
    lines = (stdout + "\n" + stderr).strip().splitlines()
    fields: dict[str, Any] = {}
    try:
        evidence = _read_json(evidence_path)
    except (OSError, ValueError):
        evidence = {}
    if isinstance(evidence, dict):
        for key in ("command_failure", "failure_location", "error_type"):
            if key in evidence:
                fields[key] = evidence[key]
    if "command_failure" not in fields:
        for line in lines:
            try:
                failure = json.loads(line).get("provider_command_failure")
            except (ValueError, AttributeError):
                continue
            if failure:
                fields["command_failure"] = failure
    closing = lines[-1] if lines else "no output"
    return f"{closing} {json.dumps(fields, sort_keys=True)}" if fields else closing


def subprocess_operation(base: Path, run: str) -> Callable[[str, bytes, str, str], dict[str, Any]]:
    """Runs the protected provider tool phases (prepare, persist, apply) for one operation."""

    def call(operation: str, document: bytes, approved_digest: str, run_label: str) -> dict[str, Any]:
        directory = base / f"{len(list(base.iterdir())) + 1:02d}-{operation}"
        env = {**os.environ, "PROVIDER_DOCUMENT": document.decode() if document else "{}"}
        phases = ["prepare", "persist", "apply"] if operation == "assemble" else ["prepare", "apply"]
        for phase in phases:
            command = [
                sys.executable,
                "scripts/wc133_whatsapp_operations.py",
                phase,
                "--operation",
                operation,
                "--directory",
                str(directory),
                "--run",
                run_label,
            ]
            if approved_digest:
                command += ["--approved-digest", approved_digest]
            result = subprocess.run(command, env=env, capture_output=True, text=True, check=False)  # noqa: S603
            if result.returncode:
                raise AutopilotError(
                    f"provider operation {operation} failed in {phase}: "
                    + provider_failure_summary(result.stdout, result.stderr, directory / f"evidence-{phase}.json")
                )
        evidence = _read_json(directory / "evidence-apply.json")
        if evidence.get("status") != "PASS":
            raise AutopilotError(f"provider operation {operation} did not pass")
        if operation == "assemble":
            evidence["bundle"] = (directory / "activation.bundle.json").read_bytes()
        if operation == "status":
            # Versions and digests of the registered provider; never a credential value.
            evidence["provider"] = _read_json(directory / "configuration.after.json")["whatsapp_provider"]
        return evidence

    return call


def az_json(*args: str) -> Any:
    result = subprocess.run(["az", *args, "--only-show-errors", "--output", "json"], capture_output=True, text=True, check=False)  # noqa: S603, S607
    if result.returncode:
        raise AutopilotError(f"az {' '.join(args[:3])} failed")
    return json.loads(result.stdout) if result.stdout.strip() else None


def http_status(url: str) -> int:
    try:
        with urllib.request.urlopen(url, timeout=20) as response:  # noqa: S310 - fixed first-party HTTPS hostnames
            return response.status
    except urllib.error.HTTPError as error:
        error.close()
        return error.code
    except urllib.error.URLError:
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    spend = sub.add_parser("spend-args", help="print provisioner spend authority arguments as JSON")
    spend.add_argument("--policy", type=Path, required=True)
    run = sub.add_parser("run", help="re-activate Demo WhatsApp under the standing policy")
    run.add_argument("--policy", type=Path, required=True)
    run.add_argument("--alert-template", type=Path, required=True)
    run.add_argument("--directory", type=Path, required=True)
    run.add_argument("--evidence", type=Path, required=True)
    run.add_argument("--run", required=True, help="workflow run and attempt, e.g. 123-1")
    run.add_argument("--release-run-id", required=True)
    run.add_argument("--release-sha", required=True)
    arguments = parser.parse_args()
    if arguments.command == "spend-args":
        json.dump(spend_arguments(arguments.policy.read_bytes()), sys.stdout)
        sys.stdout.write("\n")
        return 0
    if re.fullmatch(r"[1-9][0-9]*-[1-9][0-9]*", arguments.run) is None:
        raise SystemExit("run must be an exact workflow run and attempt")
    arguments.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    arguments.evidence.mkdir(parents=True, exist_ok=True)
    workspace = az_json(
        "monitor",
        "log-analytics",
        "workspace",
        "show",
        "--resource-group",
        RESOURCE_GROUP,
        "--workspace-name",
        WORKSPACE,
        "--query",
        "customerId",
    )

    def query(kql: str) -> list[Any]:
        return az_json("monitor", "log-analytics", "query", "--workspace", workspace, "--analytics-query", kql) or []

    consent = {
        name: Path(name).read_bytes()
        for name in (
            "src/business-platform/Services/WhatsAppGuestSessionService.cs",
            "src/business-platform/Services/WhatsAppGuestTrafficBudget.cs",
        )
    }
    pilot = Autopilot(
        policy_bytes=arguments.policy.read_bytes(),
        alert_template=arguments.alert_template.read_text(),
        consent_files=consent,
        operation=subprocess_operation(arguments.directory, arguments.run),
        az=az_json,
        http_status=http_status,
        log_query=query,
        clock=lambda: datetime.now(timezone.utc),
        sleep=time.sleep,
        run=arguments.run,
        release_run_id=arguments.release_run_id,
        release_sha=arguments.release_sha,
    )
    try:
        evidence = pilot.activate()
    except Exception as error:  # any refusal must fail the deployment with a bounded message
        print(f"::error title=Demo WhatsApp activation refused::{type(error).__name__}: {error}", file=sys.stderr)
        return 1
    for name, document in evidence.pop("receipt_documents").items():
        (arguments.evidence / f"receipt-{name}.json").write_text(document)
    (arguments.evidence / "autopilot-evidence.json").write_bytes(canonical(evidence))
    print(
        json.dumps(
            {"status": "ACTIVE", "approved_bundle_digest": evidence["approved_bundle_digest"], "window": evidence["window"]}
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
