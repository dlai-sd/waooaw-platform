# Implements: architecture/reference/components/ai-runtime.md
# constitutional_basis: C-051 (Token Economy), C-062 (AI Security),
#   C-063 (Data Minimisation), C-078 (PII Scrubber), ADR-029 (Multi-provider)

from fastapi import FastAPI

from transcription import DisabledTranscriptionProvider
from transcription import router as transcription_router

app = FastAPI(
    title="WAOOAW AI Runtime",
    description="Provider Selection Engine + LLM dispatch (ADR-029).",
    version="0.1.0",
)
app.state.pr_service_jwt_secret = None
app.state.transcription_provider = DisabledTranscriptionProvider()
app.state.transcription_store = {}
app.include_router(transcription_router)


@app.get("/health")
async def health() -> dict:
    """Health check."""
    return {"status": "ok", "service": "ai-runtime"}
