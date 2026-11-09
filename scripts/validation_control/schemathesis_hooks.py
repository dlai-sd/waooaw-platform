"""Schemathesis generation hooks for REST contract validation."""

from dataclasses import replace

from hypothesis import strategies as st
import schemathesis


def add_idempotency_key(generated, key):
    headers = (generated.value if hasattr(generated, "value") else generated) or {}
    value = {**headers, "Idempotency-Key": str(key)}
    return replace(generated, value=value) if hasattr(generated, "value") else value


def add_callback_host(generated):
    headers = (generated.value if hasattr(generated, "value") else generated) or {}
    value = {**headers, "Host": "whatsapp-callback"}
    return replace(generated, value=value) if hasattr(generated, "value") else value


def align_dependent_fields(generated):
    body = generated.value if hasattr(generated, "value") else generated
    if not isinstance(body, dict):
        return generated
    value = dict(body)
    if "clientIntentId" in value and "evaluationIntentId" in value:
        value["clientIntentId"] = value["evaluationIntentId"]
    align_operational_mandate(value.get("operationalMandate"))
    for source in value.get("sources", []):
        if isinstance(source, dict):
            align_operational_mandate(source.get("operationalMandate"))
    return replace(generated, value=value) if hasattr(generated, "value") else value


def align_operational_mandate(mandate):
    if not isinstance(mandate, dict):
        return
    operation = mandate.get("conversationOperation")
    if not isinstance(operation, dict):
        return
    operation["inputSchemaDigest"] = mandate.get("inputSchemaDigest")
    operation["outputSchemaDigest"] = mandate.get("outputSchemaDigest")
    prompt = operation.get("promptPolicy")
    if isinstance(prompt, dict):
        prompt["version"] = mandate.get("promptVersion")
        prompt["digest"] = mandate.get("promptDigest")
    governed_action = operation.get("governedAction")
    permitted = mandate.get("permittedActions")
    if governed_action is not None and isinstance(permitted, list) and governed_action not in permitted:
        permitted.append(governed_action)
    exclusions = mandate.get("exclusions")
    if isinstance(exclusions, list):
        mandate["exclusions"] = [value for value in exclusions if value != governed_action]


@schemathesis.hook
def before_generate_headers(context, strategy):
    headers = st.tuples(strategy, st.uuids()).map(lambda generated: add_idempotency_key(*generated))
    if context is not None and context.operation.path == "/api/v1/channels/whatsapp/webhook":
        return headers.map(add_callback_host)
    return headers


@schemathesis.hook
def map_body(context, body):
    return align_dependent_fields(body)
