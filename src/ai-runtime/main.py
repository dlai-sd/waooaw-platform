"""
AI Runtime — main.py
LLM gateway, Tool Registry (MCP client), RAG pipeline, Creative Standard Enforcer.
Constitutional Basis: C-003 (no authority), C-004 (AI is capability not authority),
                      C-040 (domain specialization), C-041 (tool calls governed),
                      ADR-019 (RAG), ADR-020 (MCP)
"""
import logging
import os
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def setup_telemetry() -> None:
    resource = Resource.create({"service.name": "ai-runtime"})
    provider = TracerProvider(resource=resource)
    otlp_endpoint = os.getenv("OTLP_ENDPOINT", "http://jaeger:4317")
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint))
    )
    trace.set_tracer_provider(provider)


tracer = trace.get_tracer("ai-runtime")


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_telemetry()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.info("AI Runtime starting — no governance authority, execution capability only")
    yield
    logging.info("AI Runtime shutting down")


app = FastAPI(
    title="WAOOAW AI Runtime",
    description=(
        "LLM gateway, Tool Registry (MCP), RAG pipeline, Creative Standard Enforcer. "
        "This service has no governance authority — it executes within the Decision Space "
        "provided by Professional Runtime."
    ),
    lifespan=lifespan,
)


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "healthy",
        "llmProvider": os.getenv("LLM_PROVIDER", "openai"),
        "ragTiersAvailable": ["domain", "customer", "platform"],
        "mcpServersRegistered": 0,  # TODO Sprint 2: count registered MCP servers
    }


@app.post("/api/v1/inference")
async def inference(body: dict[str, Any]) -> dict[str, Any]:
    """
    LLM inference endpoint.
    Called by Professional Runtime with: prompt, Decision Space context, tool list.
    RAG retrieval happens here before calling LLM (ADR-019).
    C-041: tool calls are validated against decision_space.authorized_tools BEFORE execution.
    """
    decision_space = body.get("decisionSpace", {})
    task = body.get("task", "")
    professional_type = decision_space.get("professionalType", "UNKNOWN")

    with tracer.start_as_current_span("ai.inference") as span:
        span.set_attribute("professional_type", professional_type)
        span.set_attribute("task_length", len(task))

        # TODO Sprint 2: RAG retrieval (ADR-019)
        # 1. Retrieve from Tier 1 (Domain Knowledge — institutional schema)
        # 2. Retrieve from Tier 2 (Customer Context — professional.creative_standard_embeddings)
        # 3. Retrieve from Tier 3 (Platform Intelligence — institutional schema)

        # TODO Sprint 2: LLM call via provider-agnostic gateway
        # TODO Sprint 2: Creative Standard validation (Amendment A-005)

        logging.info(
            "AI inference requested: professional_type=%s task=%s (stub)",
            professional_type, task[:50]
        )

        return {
            "generatedContent": f"[Foundation stub] Task: {task[:100]}",
            "ragContextUsed": False,  # will be True in Sprint 2
            "mcpToolsCalled": [],
        }


@app.post("/api/v1/tools/execute")
async def execute_tool(body: dict[str, Any]) -> dict[str, Any]:
    """
    MCP tool execution (ADR-020).
    Called by Professional Runtime AFTER CE.ValidateAction returns ALLOW (C-041).
    Default deny: if tool is not in decision_space.authorized_tools, rejects immediately.
    """
    tool_name = body.get("toolName", "")
    decision_space = body.get("decisionSpace", {})
    authorized_tools = decision_space.get("authorizedTools", [])

    # C-041: default deny — reject if not authorized
    if tool_name not in authorized_tools:
        logging.warning("Tool call rejected (C-041): %s not in authorized_tools", tool_name)
        return {"success": False, "error": f"Tool '{tool_name}' not in authorized Decision Space (C-041)"}

    with tracer.start_as_current_span("ai.mcp_tool_call") as span:
        span.set_attribute("tool_name", tool_name)
        # TODO Sprint 2: Route to appropriate MCP server via MCP client (ADR-020)
        logging.info("MCP tool call (stub): %s", tool_name)
        return {"success": True, "result": f"[Foundation stub] Tool {tool_name} executed"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5004, log_level="info")
