"""Schemathesis generation hooks for REST contract validation."""

from dataclasses import replace

from hypothesis import strategies as st
import schemathesis


def add_idempotency_key(generated, key):
    headers = (generated.value if hasattr(generated, "value") else generated) or {}
    value = {**headers, "Idempotency-Key": str(key)}
    return replace(generated, value=value) if hasattr(generated, "value") else value


@schemathesis.hook
def before_generate_headers(context, strategy):
    return st.tuples(strategy, st.uuids()).map(lambda generated: add_idempotency_key(*generated))
