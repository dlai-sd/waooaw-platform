# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-03
# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-04
# Constitutional basis: C-059, C-088
"""Counters of the wallet convergence and platform-account paths; recording never fails a request."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_METER_NAME = "waooaw.billing_engine.wallet"
_counters: dict[str, object] = {}


def count(name: str, amount: int = 1, **attributes: str) -> None:
    """Add to the named counter; attributes must be low-cardinality and never personal data."""
    try:
        from opentelemetry import metrics

        counter = _counters.get(name)
        if counter is None:
            counter = metrics.get_meter(_METER_NAME).create_counter(name)
            _counters[name] = counter
        counter.add(amount, attributes)
    except Exception:
        logger.warning("wallet metric %s was not recorded", name)
