# Implements: architecture/reference/magic-llm/architecture.md (package entry point)
# Constitutional basis: C-059, C-069, C-070
"""MagicLLM — Universal Constitutional AI Execution Layer."""

from .types import (
    FailureClassification,
    MagicLLMDecisionRecord,
    MagicLLMRequest,
    MagicLLMResponse,
    QualityGate,
    TaskCategory,
)
from .pipeline import MagicLLMPipeline
from .orchestration import (
    FounderDecisionBrief,
    GoalUnderstandingRecord,
    GoalUnderstandingRequest,
    MonitorSignal,
    ResearchRecord,
    RoutingDecisionRecord,
    RoutingRequest,
)

__all__ = [
    "FailureClassification",
    "FounderDecisionBrief",
    "GoalUnderstandingRecord",
    "GoalUnderstandingRequest",
    "MagicLLMDecisionRecord",
    "MagicLLMPipeline",
    "MagicLLMRequest",
    "MagicLLMResponse",
    "MonitorSignal",
    "QualityGate",
    "ResearchRecord",
    "RoutingDecisionRecord",
    "RoutingRequest",
    "TaskCategory",
]
