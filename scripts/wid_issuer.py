#!/usr/bin/env python3
"""ADR-046 cloud workload credential issuer: ca, leaf, revoke and status modes against Azure Key Vault."""

# Implements: ADR-046 sections 3.1, 4.1, 4.2, 12.2 (Amendment 1); workload-identity-cloud-issuance-contract.md section 8
# constitutional_basis: C-026, C-059, C-063, C-083, C-084, C-085

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from workload_identity_issuance import (
    IssuanceError,
    KeyVaultClient,
    ManagedIdentityTokenProvider,
    VaultClient,
    load_certificate,
    load_registry,
    parse_workloads,
    read_ca_state,
    run_ca,
    run_leaf,
    run_revoke,
    run_status,
    utc_now,
)


CLOUD_ENVIRONMENTS = ("demo", "uat", "prod")
DEFAULT_REGISTRY = Path(__file__).resolve().parents[1] / "infrastructure/workload-identity/registry.yaml"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    modes.add_parser("ca", help="bootstrap or renew root and intermediate, publish the trust bundle")
    leaf = modes.add_parser("leaf", help="issue leaf and delegation certificates and publish workload bundles")
    leaf.add_argument("--force", action="store_true", help="reissue even when the current leaf is fresh")
    revoke = modes.add_parser("revoke", help="revoke serials or identity URIs, suspend or resume a workload")
    revoke.add_argument("--serial", action="append", default=[], help="decimal certificate serial to revoke")
    revoke.add_argument("--identity-uri", action="append", default=[], help="registered workload identity URI to revoke")
    revoke.add_argument("--suspend", metavar="WORKLOAD", help="revoke the workload identity and stop reissuing")
    revoke.add_argument("--resume", metavar="WORKLOAD", help="lift a suspension; the workload is reissued on the next leaf run")
    modes.add_parser("status", help="print a secret-free JSON summary; non-zero when a bundle is missing or under 4 hours")
    return parser


def _vault(environ: Mapping[str, str]) -> VaultClient:
    vault_url = environ.get("WID_VAULT_URL", "")
    if not vault_url:
        raise IssuanceError("WID_VAULT_URL is required")
    token_provider = ManagedIdentityTokenProvider(environ.get("WID_MANAGED_IDENTITY_CLIENT_ID") or None, dict(environ))
    return KeyVaultClient(vault_url, token_provider)


def _ca_line(vault: VaultClient, now: datetime) -> list[str]:
    state = read_ca_state(vault)
    if state is None:
        return []
    days = {
        field: max(0, int((load_certificate(state[f"{field}_pem"]).not_valid_after_utc - now).total_seconds() // 86400))
        for field in ("root", "intermediate")
    }
    return [f"wid_status ca intermediate_days={days['intermediate']} root_days={days['root']}"]


def _status_lines(summary: Mapping[str, object]) -> list[str]:
    """Secret-free console lines that the Log Analytics alerts parse (contract section 8)."""
    lines: list[str] = []
    for workload, entry in summary.get("workloads", {}).items():  # type: ignore[union-attr]
        if "remaining_seconds" in entry:
            remaining = max(0, int(entry["remaining_seconds"]))
            lines.append(
                f"wid_status workload={workload} remaining_seconds={remaining} bundle_version={int(entry['bundle_version'])}"
            )
    if "root" in summary and "intermediate" in summary:
        intermediate = max(0, int(summary["intermediate"]["days_left"]))  # type: ignore[index]
        root = max(0, int(summary["root"]["days_left"]))  # type: ignore[index]
        lines.append(f"wid_status ca intermediate_days={intermediate} root_days={root}")
    return lines


def main(
    argv: list[str] | None = None,
    environ: Mapping[str, str] | None = None,
    vault: VaultClient | None = None,
    now: datetime | None = None,
) -> int:
    environ = os.environ if environ is None else environ
    args = _parser().parse_args(argv)
    status_lines: list[str] = []
    try:
        environment = environ.get("WID_ENVIRONMENT", "")
        if environment not in CLOUD_ENVIRONMENTS:
            raise IssuanceError(f"WID_ENVIRONMENT must be one of {', '.join(CLOUD_ENVIRONMENTS)}")
        try:
            registry = load_registry(Path(environ.get("WID_REGISTRY_PATH") or DEFAULT_REGISTRY))
        except ValueError as error:
            raise IssuanceError(f"Workload registry is invalid: {error}") from None
        except OSError:
            raise IssuanceError("Workload registry cannot be read") from None
        workloads = parse_workloads(registry, environ.get("WID_WORKLOADS") or None)
        vault = vault or _vault(environ)
        moment = now or utc_now()
        healthy = True
        if args.mode == "ca":
            summary = run_ca(vault, registry, environment, moment)
            status_lines = _ca_line(vault, moment)
        elif args.mode == "leaf":
            summary = run_leaf(vault, registry, environment, workloads, moment, force=args.force)
            status_lines = _status_lines(run_status(vault, registry, environment, workloads, moment)[0])
        elif args.mode == "revoke":
            summary = run_revoke(vault, registry, environment, moment, args.serial, args.identity_uri, args.suspend, args.resume)
        else:
            summary, healthy = run_status(vault, registry, environment, workloads, moment)
            status_lines = _status_lines(summary)
    except IssuanceError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        print(f"wid_issuer mode={args.mode} result=failed reason=issuance-error")
        return 1
    except Exception as error:  # only the type is reported so no key material can leak
        print(f"ERROR: unexpected {type(error).__name__}", file=sys.stderr)
        print(f"wid_issuer mode={args.mode} result=failed reason=unexpected-error")
        return 1
    for line in status_lines:
        print(line)
    print(f"wid_issuer mode={args.mode} result=ok" if healthy else f"wid_issuer mode={args.mode} result=failed reason=unhealthy")
    print(json.dumps(summary, sort_keys=True))
    return 0 if healthy else 1


if __name__ == "__main__":
    raise SystemExit(main())
