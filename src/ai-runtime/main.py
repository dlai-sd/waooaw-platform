# Implements: architecture/reference/components/ai-runtime.md
# constitutional_basis: C-051 (Token Economy), C-062 (AI Security),
#   C-063 (Data Minimisation), C-078 (PII Scrubber), ADR-029 (Multi-provider)

import os
import ssl
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI
from ctg.governed_inference import GovernedInferenceToolGateway
from conversation_generation import GovernedGenerationService
from conversation_generation import router as conversation_generation_router
from conversation_generation_owner import BusinessPlatformGenerationOwner
from conversation_generation_provider import InstitutionalOllamaProvider
from conversation_generation_store import ConversationGenerationStore

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
    application.state.conversation_generation_service = None
    owner = None
    provider_client = None
    try:
        endpoint = os.getenv("AIR_CONVERSATION_GENERATION_OWNER_URL")
        if endpoint:
            credentials = Path(os.environ["WAOOAW_WORKLOAD_CREDENTIALS"])
            tokenizer_directory = Path(os.environ["AIR_CONVERSATION_TOKENIZER_DIRECTORY"])
            if repository is None:
                raise ValueError("Governed generation requires durable AIR persistence")
            owner = BusinessPlatformGenerationOwner(endpoint, credentials)
            tls = ssl.create_default_context(cafile=str(credentials / "trust" / "ca-bundle.pem"))
            workload = credentials / "workloads" / "ai-runtime"
            tls.load_cert_chain(str(workload / "tls-cert.pem"), str(workload / "tls-key.pem"))
            provider_client = httpx.AsyncClient(verify=tls, timeout=30, follow_redirects=False, trust_env=False)
            application.state.conversation_generation_service = GovernedGenerationService(
                ConversationGenerationStore(repository.pool),
                owner,
                GovernedInferenceToolGateway(InstitutionalOllamaProvider(tokenizer_directory, provider_client)),
            )
        yield
    finally:
        application.state.conversation_generation_service = None
        application.state.employment_patch_repository = None
        if provider_client is not None:
            await provider_client.aclose()
        if owner is not None:
            await owner.close()
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
app.include_router(conversation_generation_router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check."""
    return {"status": "ok", "service": "ai-runtime"}
