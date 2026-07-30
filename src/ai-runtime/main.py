# Implements: architecture/reference/components/ai-runtime.md
# constitutional_basis: C-051 (Token Economy), C-062 (AI Security),
#   C-063 (Data Minimisation), C-078 (PII Scrubber), ADR-029 (Multi-provider)

from fastapi import FastAPI

app = FastAPI(
    title="WAOOAW AI Runtime",
    description="Provider Selection Engine + LLM dispatch (ADR-029).",
    version="0.1.0",
)


@app.get("/health")
async def health() -> dict:
    """Health check."""
    return {"status": "ok", "service": "ai-runtime"}
