"""Private Orchard Advisor adapter process."""

# Implements: work-contracts/WC-174-agent-operation-modes-calendar-and-dma-journey.md WC174-R004, R035
# Constitutional basis: C-035, C-059, C-071, C-079

from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import FastAPI, Request
from runtime_contract.declarative import DeclarativeEmploymentSemantics
from runtime_contract.http import create_app

from .adapter import create_adapter

_CONTRACTS = Path(__file__).resolve().parent / "contracts"


def create_service_app(
    employment_authorizer: Callable[[Request], Awaitable[None]] | None = None,
) -> FastAPI:
    return create_app(
        create_adapter(),
        employment_semantics=DeclarativeEmploymentSemantics(
            _CONTRACTS / "employment-interface-manifest.v1.json",
            _CONTRACTS / "requirements.v1.json",
        ),
        employment_authorizer=employment_authorizer,
    )
