# Implements: architecture/reference/components/professional-runtime.md
# constitutional_basis: C-025 (PAAS exclusive), C-001 (Emergency Stop ≤250ms),
#   ADR-015 (Temporal), ADR-018 (Emergency Stop signal)

from fastapi import FastAPI

app = FastAPI(
    title="WAOOAW Professional Runtime",
    description="PAAS execution engine (C-025). All professional work runs here.",
    version="0.1.0",
)


@app.get("/health")
async def health() -> dict:
    """Health check."""
    return {"status": "ok", "service": "professional-runtime"}
