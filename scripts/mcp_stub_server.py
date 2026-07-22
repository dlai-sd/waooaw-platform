#!/usr/bin/env python3
"""
mcp_stub_server.py
constitutional_basis: C-059 (Implementation Traceability), C-070 (Third Instinct)
ib_item: IB-009 (Sprint 011 — Infrastructure Foundation)
spec: architecture/reference/mcp-tool-catalogues.md

Generic MCP stub server for local development and CI.
Reads all configuration from environment variables — no hardcoded service logic.
All 23 MCP services in docker-compose.yml share this single script.

Environment variables:
    MCP_SERVICE_NAME   — FastAPI app title (e.g. 'instagram-mcp-stub')
    MCP_TOOLS          — JSON array of tool names (e.g. '["post.publish","get_insights"]')
    MCP_PORT           — Port to listen on (default: 8100)
    MCP_STUB_MESSAGE   — Response message for /call endpoint
                         (default: 'STUB — not yet implemented')

Usage (in docker-compose.yml):
    image: python:3.12-slim
    command: sh -c "pip install fastapi uvicorn --quiet && python /stub/mcp_stub_server.py"
    volumes:
      - ./scripts/mcp_stub_server.py:/stub/mcp_stub_server.py:ro
    environment:
      MCP_SERVICE_NAME: instagram-mcp-stub
      MCP_TOOLS: '["post.publish","story.publish","get_insights"]'
      MCP_PORT: "8106"
      MCP_STUB_MESSAGE: "STUB — Meta credentials required"
"""
from __future__ import annotations

import json
import os
import sys


def main() -> None:
    service_name = os.environ.get("MCP_SERVICE_NAME", "unnamed-mcp-stub")
    tools_json = os.environ.get("MCP_TOOLS", '[]')
    port = int(os.environ.get("MCP_PORT", "8100"))
    stub_message = os.environ.get("MCP_STUB_MESSAGE", "STUB — not yet implemented")

    try:
        tools: list[str] = json.loads(tools_json)
    except json.JSONDecodeError:
        print(f"WARNING: MCP_TOOLS is not valid JSON: {tools_json!r}. Defaulting to [].")
        tools = []

    try:
        import uvicorn  # type: ignore[import]
        from fastapi import FastAPI  # type: ignore[import]
    except ImportError:
        print("ERROR: fastapi and uvicorn are required. Run: pip install fastapi uvicorn")
        sys.exit(1)

    app = FastAPI(
        title=service_name,
        description=f"Development stub for {service_name}. All responses are synthetic.",
        version="0.1.0-stub",
    )

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "stub": True, "service": service_name}

    @app.get("/tools")
    def get_tools() -> dict:
        return {"tools": tools, "stub": True}

    @app.post("/call/{tool_name}")
    def call_tool(tool_name: str, body: dict = {}) -> dict:  # noqa: B006
        if tool_name not in tools:
            return {
                "tool": tool_name,
                "error": f"Unknown tool '{tool_name}'. Available: {tools}",
                "stub": True,
            }
        return {
            "tool": tool_name,
            "result": stub_message,
            "stub": True,
            "note": "Replace stub with real API integration before production use.",
        }

    print(f"Starting MCP stub: {service_name} on port {port} with {len(tools)} tools")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")


if __name__ == "__main__":
    main()
