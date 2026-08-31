"""Private Trading adapter process."""

# Implements: architecture/agent-runtime-adapter-contract-v1-execution-plan.md §8 ARA-06
# Constitutional basis: C-035, C-059, C-071, C-079

from runtime_contract.http import create_app

from .adapter import create_adapter

app = create_app(create_adapter())