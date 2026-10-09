"""DMA Release 1 and Package A employment semantics."""

# Implements: architecture/reference/components/dma-employment-conformance-work-component.md §4-20
# Constitutional basis: C-035, C-059, C-071, C-079

from .adapter import create_adapter
from .employment import (
    DmaEmploymentSemantics,
    MaterialChangeContext,
    PlanContext,
    RelationshipContext,
    resolve_compatibility_tuple,
)

__all__ = [
    "DmaEmploymentSemantics",
    "MaterialChangeContext",
    "PlanContext",
    "RelationshipContext",
    "create_adapter",
    "resolve_compatibility_tuple",
]