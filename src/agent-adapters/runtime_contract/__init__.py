"""Agent Runtime Adapter Contract v1 reference implementation."""

# Implements: architecture/agent-runtime-adapter-contract-v1-execution-plan.md §5
# Constitutional basis: C-023, C-035, C-059, C-065, C-071, C-079, C-080

from .adapter import AdapterContractError, ReferenceAdapter
from .models import (
    AdapterDescriptorV1,
    AdapterEventV1,
    AdapterInvocationEnvelopeV1,
    AdapterInvocationV1,
    AdapterResultV1,
    InvocationState,
)

__all__ = [
    "AdapterContractError",
    "AdapterDescriptorV1",
    "AdapterEventV1",
    "AdapterInvocationEnvelopeV1",
    "AdapterInvocationV1",
    "AdapterResultV1",
    "InvocationState",
    "ReferenceAdapter",
]