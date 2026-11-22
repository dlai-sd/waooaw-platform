# Implements: architecture/reference/components/ai-runtime.md
# constitutional_basis: C-051 (Token Economy), C-062 (AI Security),
#   C-063 (Data Minimisation), C-078 (PII Scrubber), ADR-029 (Multi-provider)

import asyncio
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
from conversation_generation_provider import AdapterRoutingProvider, HostedGovernedProvider, InstitutionalOllamaProvider
from cloud_workload import DEFAULT_KEY_TMPFS, HotReloadClientTls, SnapshotWorkloadAuth
from conversation_generation_store import ConversationGenerationStore

from employment_auth import EmploymentWorkloadAuth
from employment_patch import configure_employment_patch
from employment_patch import router as employment_patch_router
from employment_persistence import EmploymentPatchRepository
from provider_generation_probe import ProviderGenerationProbeService
from provider_generation_probe import router as provider_generation_probe_router
from providers.credential_resolver import ProviderCredentialResolver
from providers.hosted.base import new_hosted_client
from runtime_workload_credentials import credential_holder_from_environment, register_holder
from transcription import DisabledTranscriptionProvider
from transcription import router as transcription_router


def _probe_auth(credentials: Path) -> EmploymentWorkloadAuth | None:
    # Only the Business Platform delegation key is trusted on the probe route; absent material leaves the route at 503.
    try:
        return EmploymentWorkloadAuth.from_credentials(credentials, "business-platform")
    except (OSError, KeyError, ValueError):
        return None


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    database_url = os.getenv("DATABASE_URL")
    repository = await EmploymentPatchRepository.connect(database_url) if database_url else None
    application.state.employment_patch_repository = repository
    application.state.conversation_generation_service = None
    application.state.provider_generation_probe_service = None
    application.state.provider_probe_auth = None
    owner = None
    provider_client = None
    hosted_client = None
    holder = getattr(application.state, "workload_credentials", None)
    credential_stop = asyncio.Event()
    credential_task = (
        asyncio.create_task(holder.run(credential_stop), name="workload-credential-refresh")
        if holder is not None and holder.refreshable
        else None
    )
    try:
        endpoint = os.getenv("AIR_CONVERSATION_GENERATION_OWNER_URL")
        credential_directory = os.getenv("WAOOAW_WORKLOAD_CREDENTIALS")
        if endpoint and (holder is not None or credential_directory):
            # The probe needs only workload credentials, the BP resolve client and the vault reader; it never depends on
            # persistence, tokenizers or a published binding.
            probe_auth: object | None
            if holder is not None:
                tls = HotReloadClientTls(holder, Path(os.getenv("WAOOAW_WID_KEY_TMPFS", DEFAULT_KEY_TMPFS))).context
                owner = BusinessPlatformGenerationOwner.from_holder(endpoint, holder, tls)
                probe_auth = SnapshotWorkloadAuth(holder, "business-platform")
            else:
                credentials = Path(credential_directory or "")
                owner = BusinessPlatformGenerationOwner(endpoint, credentials)
                tls = ssl.create_default_context(cafile=str(credentials / "trust" / "ca-bundle.pem"))
                workload = credentials / "workloads" / "ai-runtime"
                tls.load_cert_chain(str(workload / "tls-cert.pem"), str(workload / "tls-key.pem"))
                probe_auth = _probe_auth(credentials)
            # Hosted provider traffic never carries the workload client certificate.
            hosted_client = new_hosted_client()
            keys = ProviderCredentialResolver(ref_fetcher=lambda provider: owner.resolve_provider_credential(provider))
            if keys.vault_configured():
                application.state.provider_probe_auth = probe_auth
                application.state.provider_generation_probe_service = ProviderGenerationProbeService(keys, hosted_client)
            tokenizer_setting = os.getenv("AIR_CONVERSATION_TOKENIZER_DIRECTORY")
            if tokenizer_setting:
                if repository is None:
                    raise ValueError("Governed generation requires durable AIR persistence")
                provider_client = httpx.AsyncClient(verify=tls, timeout=30, follow_redirects=False, trust_env=False)
                application.state.conversation_generation_service = GovernedGenerationService(
                    ConversationGenerationStore(repository.pool),
                    owner,
                    GovernedInferenceToolGateway(
                        AdapterRoutingProvider(
                            InstitutionalOllamaProvider(Path(tokenizer_setting), provider_client),
                            HostedGovernedProvider(keys, hosted_client),
                        )
                    ),
                )
        yield
    finally:
        application.state.conversation_generation_service = None
        application.state.provider_generation_probe_service = None
        application.state.provider_probe_auth = None
        application.state.employment_patch_repository = None
        credential_stop.set()
        if credential_task is not None:
            await credential_task
        if provider_client is not None:
            await provider_client.aclose()
        if hosted_client is not None:
            await hosted_client.aclose()
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
app.state.workload_credentials = credential_holder_from_environment()
register_holder(app.state.workload_credentials)
if app.state.workload_credentials is not None:
    app.state.employment_workload_auth = SnapshotWorkloadAuth(app.state.workload_credentials, "professional-runtime")
app.include_router(transcription_router)
app.include_router(employment_patch_router)
app.include_router(conversation_generation_router)
app.include_router(provider_generation_probe_router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check."""
    return {"status": "ok", "service": "ai-runtime"}
