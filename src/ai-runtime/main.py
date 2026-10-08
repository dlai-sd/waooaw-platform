# Implements: architecture/reference/components/ai-runtime.md
# constitutional_basis: C-051 (Token Economy), C-062 (AI Security),
#   C-063 (Data Minimisation), C-078 (PII Scrubber), ADR-029 (Multi-provider)

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from employment_patch import configure_employment_patch
from employment_patch import router as employment_patch_router
from employment_persistence import EmploymentPatchRepository
from transcription import DisabledTranscriptionProvider
from transcription import router as transcription_router


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    database_url = os.getenv("DATABASE_URL")
    repository = await EmploymentPatchRepository.connect(database_url) if database_url else None
    application.state.employment_patch_repository = repository
    try:
        yield
    finally:
        application.state.employment_patch_repository = None
        if repository is not None:
            await repository.close()


app = FastAPI(
    title="WAOOAW AI Runtime",
    description="Provider Selection Engine + LLM dispatch (ADR-029).",
    version="0.1.0",
    lifespan=lifespan,
)
app.state.pr_service_jwt_secret = None
app.state.transcription_provider = DisabledTranscriptionProvider()
app.state.transcription_store = {}
configure_employment_patch(app)
app.include_router(transcription_router)
app.include_router(employment_patch_router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check."""
    return {"status": "ok", "service": "ai-runtime"}
