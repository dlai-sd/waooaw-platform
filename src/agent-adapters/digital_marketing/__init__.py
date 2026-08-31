"""Digital Marketing fixture for Adapter Contract v1 conformance."""

# Implements: architecture/agent-runtime-adapter-contract-v1-execution-plan.md §8 ARA-06
# Constitutional basis: C-035, C-059, C-071, C-079

from .adapter import create_adapter

__all__ = ["create_adapter"]