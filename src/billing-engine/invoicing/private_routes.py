# Implements: work-contracts/WC-172-safe-to-charge-real-customers.md WC172-R006
# Implements: work-contracts/WC-176-customer-journeys-registration-trial-hire-and-pages.md WC176-R017
# Constitutional basis: C-059, C-063, C-088, ADR-046
"""Private WBE tax-document retrieval for a customer's own tenant, over the workload-identity path used by the wallet
routes: mutually authenticated peer certificate plus a delegated context bound to the route, operation and tenant.
A customer can read only the documents of the tenant the signed context names; the Founder reads across tenants
through the pricing-administration route."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query, Request

from database import get_session_factory
from invoicing.hooks import service_for
from invoicing.render import render_html
from wallet.private_routes import _unauthorized, _verify
from workload_identity import ServiceAuthError

LIST_ROUTE = "/internal/v1/tax-documents"
LIST_OPERATION = "wbeListTaxDocuments"
GET_ROUTE = "/internal/v1/tax-documents/{documentId}"
GET_OPERATION = "wbeGetTaxDocument"

router = APIRouter(prefix="/internal/v1/tax-documents", tags=["Tax Documents Private"])


def _settings() -> Any:
    from config import Settings

    return Settings()


@router.get("")
async def list_tax_documents(
    request: Request,
    tenant_id: Annotated[uuid.UUID, Query(alias="tenantId")],
    relationship_id: Annotated[uuid.UUID | None, Query(alias="relationshipId")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> dict[str, Any]:
    correlation_id = request.headers.get("X-Correlation-ID", "")
    try:
        _verify(
            request,
            LIST_ROUTE,
            LIST_OPERATION,
            None,
            lambda context: context.tenant_id == str(tenant_id)
            and bool(context.actor_subject)
            and context.correlation_id == correlation_id,
        )
    except ServiceAuthError as error:
        raise _unauthorized(LIST_OPERATION, error) from None
    async with get_session_factory()() as session:
        documents = await service_for(session, _settings()).list_documents(
            tenant_id=tenant_id, relationship_id=relationship_id, limit=limit
        )
    return {"schemaVersion": "1.0", "documents": [document.as_public() for document in documents]}


@router.get("/{document_id}")
async def get_tax_document(
    document_id: uuid.UUID,
    request: Request,
    tenant_id: Annotated[uuid.UUID, Query(alias="tenantId")],
) -> dict[str, Any]:
    correlation_id = request.headers.get("X-Correlation-ID", "")
    try:
        _verify(
            request,
            GET_ROUTE,
            GET_OPERATION,
            None,
            lambda context: context.tenant_id == str(tenant_id)
            and bool(context.actor_subject)
            and context.correlation_id == correlation_id,
        )
    except ServiceAuthError as error:
        raise _unauthorized(GET_OPERATION, error) from None
    async with get_session_factory()() as session:
        document = await service_for(session, _settings()).get(document_id, tenant_id=tenant_id)
    if document is None:
        raise HTTPException(status_code=404, detail={"code": "TAX_DOCUMENT_NOT_FOUND"})
    return {
        "schemaVersion": "1.0",
        "document": document.as_public(),
        "readable": {"contentType": "text/html; charset=utf-8", "body": render_html(document)},
    }
