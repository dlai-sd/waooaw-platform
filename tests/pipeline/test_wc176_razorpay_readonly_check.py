"""WC-176 R015-R018: the billing init file passes the init-chain lint and the Razorpay check reads without leaking."""

from __future__ import annotations

import json
from pathlib import Path

import wc124_init_chain_lint as lint
import wc176_razorpay_readonly_check as check

ROOT = Path(__file__).resolve().parents[2]
INIT_FILE = ROOT / "infrastructure/postgres/init/99zzzzzzzz-wc176-02-billing-capture-invoice.sql"
GST = {
    "GST_LEGAL_NAME": "DLAI Satellite Data (OPC) Pvt Ltd",
    "GST_GSTIN": "27AAKCD8188R1ZH",
    "GST_ADDRESS": "C8, Everest Heights, Park Road, Viman Nagar, Pune 411014, Maharashtra, India",
    "GST_STATE_CODE": "27",
}


def test_the_billing_capture_init_file_is_a_full_class_file_that_passes_the_lint() -> None:
    text = INIT_FILE.read_text(encoding="utf-8")
    assert lint.declared_class(text) == "full"
    assert lint.lint_sql(INIT_FILE.name, text) == []


def test_the_check_passes_good_settings_without_printing_a_secret_and_fails_a_live_key() -> None:
    secret = "never-printed-secret-value"
    good = {**GST, "RAZORPAY_KEY_ID": "rzp_test_abc", "RAZORPAY_KEY_SECRET": secret, "RAZORPAY_WEBHOOK_SECRET": secret}
    results = check.check(good, "https://api.demo.waooaw.com/api/v1/payments/webhooks/razorpay")
    assert [item["status"] for item in results] == ["ok", "ok", "ok", "ok", "ok", "not-checked"]
    assert secret not in json.dumps(results)

    live = {**good, "RAZORPAY_KEY_ID": "rzp_live_abc"}
    assert check.check(live)[0]["status"] == "fail"
    assert check.check({})[0]["status"] == "not-checked"
