#!/usr/bin/env python3
"""Read-only check of the Razorpay and GST settings before a Test Mode run (WC-176 R018).

Reports each check as ok, fail or not-checked and never prints a secret value. Nothing is changed at Razorpay: the
only provider call, made only with --online and credentials in the environment, is one GET of the payments list.

Reads ACCEPTANCE_RAZORPAY_KEY_ID, ACCEPTANCE_RAZORPAY_KEY_SECRET and ACCEPTANCE_RAZORPAY_WEBHOOK_SECRET (the
acceptance names), else RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET and RAZORPAY_WEBHOOK_SECRET, plus the GST_* settings.
"""

# Implements: work-contracts/WC-176-customer-journeys-registration-trial-hire-and-pages.md WC176-R018
# Constitutional basis: C-023, C-059, C-063

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from collections.abc import Mapping
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "billing-engine"))

from invoicing.identity import TaxIdentityNotConfigured, supplier_from

WEBHOOK_PATH = "/api/v1/payments/webhooks/razorpay"
WEBHOOK_EVENTS = ("payment.captured", "payment.failed", "refund.processed")
PAYMENTS_URL = "https://api.razorpay.com/v1/payments?count=1"
OK, FAIL, NOT_CHECKED = "ok", "fail", "not-checked"


def _first(environ: Mapping[str, str], *names: str) -> str:
    return next((environ[name].strip() for name in names if environ.get(name, "").strip()), "")


def check(environ: Mapping[str, str], webhook_url: str = "", online: bool = False) -> list[dict[str, str]]:
    key_id = _first(environ, "ACCEPTANCE_RAZORPAY_KEY_ID", "RAZORPAY_KEY_ID")
    key_secret = _first(environ, "ACCEPTANCE_RAZORPAY_KEY_SECRET", "RAZORPAY_KEY_SECRET")
    results = [
        {
            "check": "key id is a test key",
            "status": OK if key_id.startswith("rzp_test_") else FAIL if key_id else NOT_CHECKED,
            "detail": "present" if key_id else "not provided",
        },
        {
            "check": "key secret present",
            "status": OK if key_secret else NOT_CHECKED,
            "detail": "present" if key_secret else "not provided",
        },
        {
            "check": "webhook secret present",
            "status": OK if _first(environ, "ACCEPTANCE_RAZORPAY_WEBHOOK_SECRET", "RAZORPAY_WEBHOOK_SECRET") else NOT_CHECKED,
            "detail": "present or not provided; the value is never shown",
        },
    ]
    if webhook_url:
        good = webhook_url.startswith("https://") and webhook_url.endswith(WEBHOOK_PATH)
        results.append(
            {"check": "webhook address", "status": OK if good else FAIL, "detail": f"must be https and end {WEBHOOK_PATH}"}
        )
    else:
        results.append({"check": "webhook address", "status": NOT_CHECKED, "detail": "pass --webhook-url"})
    try:
        supplier_from(
            environ.get("GST_LEGAL_NAME", ""),
            environ.get("GST_GSTIN", ""),
            environ.get("GST_ADDRESS", ""),
            environ.get("GST_STATE_CODE", ""),
            environ.get("GST_SAC_CODE", "") or "9984",
        )
        results.append({"check": "GST identity", "status": OK, "detail": "complete, GSTIN checksum valid"})
    except TaxIdentityNotConfigured as error:
        results.append(
            {"check": "GST identity", "status": FAIL if environ.get("GST_GSTIN") else NOT_CHECKED, "detail": str(error)}
        )
    results.append(_provider_check(key_id, key_secret, online))
    return results


def _provider_check(key_id: str, key_secret: str, online: bool) -> dict[str, str]:
    check_name = "provider accepts the keys (GET only)"
    if not (online and key_id.startswith("rzp_test_") and key_secret):
        return {"check": check_name, "status": NOT_CHECKED, "detail": "needs --online and test credentials in the environment"}
    token = base64.b64encode(f"{key_id}:{key_secret}".encode()).decode()
    request = urllib.request.Request(PAYMENTS_URL, headers={"Authorization": f"Basic {token}"}, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=15) as response:  # noqa: S310 - fixed https URL
            return {"check": check_name, "status": OK if response.status == 200 else FAIL, "detail": f"HTTP {response.status}"}
    except urllib.error.HTTPError as error:
        return {"check": check_name, "status": FAIL, "detail": f"HTTP {error.code}"}
    except OSError:
        return {"check": check_name, "status": NOT_CHECKED, "detail": "provider not reachable"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--webhook-url", default="", help="the webhook address registered in Razorpay Test Mode")
    parser.add_argument("--online", action="store_true", help="also make one read-only GET to Razorpay")
    args = parser.parse_args(argv)
    results = check(os.environ, args.webhook_url, args.online)
    print(json.dumps({"events_expected": list(WEBHOOK_EVENTS), "results": results}, indent=2))
    return 1 if any(item["status"] == FAIL for item in results) else 0


if __name__ == "__main__":
    sys.exit(main())
