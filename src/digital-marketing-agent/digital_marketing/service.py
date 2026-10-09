"""Private Digital Marketing adapter process."""

# Implements: architecture/reference/components/dma-employment-conformance-work-component.md §16, §20
# Constitutional basis: C-035, C-059, C-071, C-079

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from runtime_contract.employment import EmploymentDomainSemantics
from runtime_contract.http import create_app

from .adapter import create_adapter


def create_service_app(
    employment_semantics: EmploymentDomainSemantics | None = None,
    employment_authorizer: Callable[[Request], Awaitable[None]] | None = None,
) -> FastAPI:
    return create_app(
        create_adapter(),
        employment_semantics=employment_semantics,
        employment_authorizer=employment_authorizer,
    )


app = create_service_app()
