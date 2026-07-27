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
    "TaskCategory",
    "QualityGate",
    "FailureClassification",
    "MagicLLMRequest",
    "MagicLLMResponse",
    "MagicLLMDecisionRecord",
    "MagicLLMPipeline",
    "GoalUnderstandingRequest",
    "GoalUnderstandingRecord",
    "RoutingRequest",
    "RoutingDecisionRecord",
    "MonitorSignal",
    "ResearchRecord",
    "FounderDecisionBrief",
]
