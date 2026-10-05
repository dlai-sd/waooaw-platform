#!/usr/bin/env python3
"""Select REST contract paths from an exact changed-file manifest."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path
import shlex


BP_CONTROLLER_SCOPES = {
    "AcquisitionController.cs": {"product": (r"^/api/v1/acquisition/continuations(?:/|$)",)},
    "AgentAdmissionsController.cs": {"service": (r"^/api/v1/professionals/.*/admission(?:/|$)",)},
    "ConversationController.cs": {
        "product": (r"^/api/v1/employment/relationships/[^/]+/conversation(?:/|$)",),
    },
    "EmploymentRelationshipsController.cs": {"product": ("*",), "service": ("*",)},
    "IdentityController.cs": {"identity": (r"^/api/v1/identity(?:/|$)",)},
    "IdentityProvidersController.cs": {"identity": (r"^/api/v1/identity/providers(?:/|$)",)},
    "NotificationsController.cs": {"service": (r"^/api/v1/notifications/alerts(?:/|$)",)},
    "OfferabilityController.cs": {
        "service": (r"^/api/v1/employment/relationships/[^/]+/offerability(?:/|$)",),
    },
    "PortalInteractionsController.cs": {
        "product": (r"^/api/v1/customer-portal/interactions/portal/messages(?:/|$)",),
    },
    "ProfessionalsController.cs": {
        "product": (r"^/api/v1/professionals/marketplace(?:/|$)",),
        "service": (r"^/api/v1/professionals(?:/|$)",),
    },
    "RelationshipEvaluationController.cs": {
        "product": (r"^/api/v1/employment/relationships/[^/]+/evaluation(?:/|$)",),
    },
    "RelationshipWorkspaceController.cs": {
        "product": (r"^/api/v1/employment/relationships/[^/]+/workspace(?:/|$)",),
    },
    "VoiceContributionsController.cs": {
        "product": (r"^/api/v1/employment/relationships/[^/]+/voice-contributions(?:/|$)",),
    },
    "WhatsAppJourneyController.cs": {"service": (r"^/api/v1/whatsapp/webhook$",)},
}

PR_ROUTE_SCOPES = {
    "src/professional-runtime/relationship_workspace.py": r"^/api/v1/internal/relationships(?:/|$)",
    "src/professional-runtime/routers/conversation_execution.py": r"^/api/v1/internal/conversations(?:/|$)",
    "src/professional-runtime/routers/emergency_stop.py": r"^/api/v1/emergency-stop$",
    "src/professional-runtime/routers/sessions.py": r"^/api/v1/paas/sessions(?:/|$)",
    "src/professional-runtime/routers/voice_orchestration.py": r"^/api/v1/internal/relationships(?:/|$)",
}

FULL_SCOPE_PATHS = {
    "docker-compose.yml",
    "scripts/validation_control/bootstrap_rest_identity.py",
    "scripts/validation_control/merge_junit_reports.py",
    "scripts/validation_control/rest_contract_scope.py",
    "scripts/validation_control/run_docker_build.sh",
    "scripts/validation_control/run_rest_contract_gate.sh",
    "scripts/validation_control/schemathesis_hooks.py",
    "validation/schemathesis.toml",
}

BP_IDENTITY_ALL = r"^/api/v1/identity(?:/|$)"
BP_PRODUCT_ALL = (
    r"^/api/v1/(acquisition/continuations(?:/|$)|customer-portal/interactions/portal/messages(?:/|$)|"
    r"professionals/marketplace(?:/|$)|employment/relationships(?:$|/(?![^/]+/(?:transitions|offerability)(?:/|$))))"
)
BP_CUSTOMER_ALL = (
    r"^/api/v1/(identity(?:/|$)|acquisition/continuations(?:/|$)|"
    r"customer-portal/interactions/portal/messages(?:/|$)|professionals/marketplace(?:/|$)|"
    r"employment/relationships(?:$|/(?![^/]+/(?:transitions|offerability)(?:/|$))))"
)
BP_SERVICE_ALL = rf"^(?!{BP_CUSTOMER_ALL.removeprefix('^')}).*"
PR_ALL = r"^/.*"


@dataclass
class RestScope:
    bp_identity: set[str] = field(default_factory=set)
    bp_product: set[str] = field(default_factory=set)
    bp_service: set[str] = field(default_factory=set)
    pr_service: set[str] = field(default_factory=set)
    reasons: set[str] = field(default_factory=set)

    def broaden_bp(self, reason: str) -> None:
        self.bp_identity = {BP_IDENTITY_ALL}
        self.bp_product = {BP_PRODUCT_ALL}
        self.bp_service = {BP_SERVICE_ALL}
        self.reasons.add(reason)

    def broaden_pr(self, reason: str) -> None:
        self.pr_service = {PR_ALL}
        self.reasons.add(reason)

    def broaden_all(self, reason: str) -> None:
        self.broaden_bp(reason)
        self.broaden_pr(reason)

    @property
    def run_bp(self) -> bool:
        return bool(self.bp_identity or self.bp_product or self.bp_service)

    @property
    def run_pr(self) -> bool:
        return bool(self.pr_service)


def add_patterns(target: set[str], patterns: tuple[str, ...], broad_pattern: str) -> None:
    if "*" in patterns:
        target.clear()
        target.add(broad_pattern)
    elif broad_pattern not in target:
        target.update(patterns)


def scope_for_changes(changed_files: list[str] | None) -> RestScope:
    scope = RestScope()
    if not changed_files:
        scope.broaden_all("missing-or-empty-change-manifest")
        return scope

    for changed_file in changed_files:
        path = changed_file.strip().removeprefix("./")
        if not path:
            continue
        if (
            path in FULL_SCOPE_PATHS
            or path.startswith("architecture/reference/dockerfiles/Dockerfile.test-runner")
            or path.startswith("architecture/reference/proto/")
            or path.startswith("infrastructure/keycloak/")
            or path.startswith("infrastructure/temporal/")
            or path.startswith("src/constitutional-engine/")
        ):
            scope.broaden_all(f"shared:{path}")
            continue
        if path == "architecture/reference/api-specs/business-platform.openapi.yaml" or path.startswith("src/business-platform/"):
            if path.startswith("src/business-platform/Controllers/"):
                controller = path.rsplit("/", maxsplit=1)[-1]
                ownership = BP_CONTROLLER_SCOPES.get(controller)
                if ownership is not None:
                    add_patterns(scope.bp_identity, ownership.get("identity", ()), BP_IDENTITY_ALL)
                    add_patterns(scope.bp_product, ownership.get("product", ()), BP_PRODUCT_ALL)
                    add_patterns(scope.bp_service, ownership.get("service", ()), BP_SERVICE_ALL)
                    scope.reasons.add(f"business-platform-controller:{controller}")
                    continue
            scope.broaden_bp(f"business-platform-shared:{path}")
            continue
        if path == "architecture/reference/api-specs/professional-runtime.openapi.yaml" or path.startswith(
            "src/professional-runtime/"
        ):
            route_pattern = PR_ROUTE_SCOPES.get(path)
            if route_pattern is not None:
                add_patterns(scope.pr_service, (route_pattern,), PR_ALL)
                scope.reasons.add(f"professional-runtime-route:{path}")
            else:
                scope.broaden_pr(f"professional-runtime-shared:{path}")
            continue
        if path.startswith("infrastructure/postgres/"):
            scope.broaden_all(f"shared:{path}")

    return scope


def combined_regex(patterns: set[str]) -> str:
    if not patterns:
        return ""
    if len(patterns) == 1:
        return next(iter(patterns))
    return "(?:" + ")|(?:".join(sorted(patterns)) + ")"


def write_environment(scope: RestScope, output: Path) -> None:
    values = {
        "REST_RUN_BP": "true" if scope.run_bp else "false",
        "REST_RUN_PR": "true" if scope.run_pr else "false",
        "REST_BP_IDENTITY_REGEX": combined_regex(scope.bp_identity),
        "REST_BP_PRODUCT_REGEX": combined_regex(scope.bp_product),
        "REST_BP_SERVICE_REGEX": combined_regex(scope.bp_service),
        "REST_PR_SERVICE_REGEX": combined_regex(scope.pr_service),
        "REST_SCOPE_REASON": ",".join(sorted(scope.reasons)) or "unrelated-change-set",
    }
    output.write_text("".join(f"{name}={shlex.quote(value)}\n" for name, value in values.items()), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--changed-files", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    changed_files = None
    if arguments.changed_files is not None and arguments.changed_files.is_file():
        changed_files = arguments.changed_files.read_text(encoding="utf-8").splitlines()
    scope = scope_for_changes(changed_files)
    write_environment(scope, arguments.output)
    print(
        f"rest_scope business-platform={str(scope.run_bp).lower()} "
        f"professional-runtime={str(scope.run_pr).lower()} reason={','.join(sorted(scope.reasons)) or 'unrelated-change-set'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
