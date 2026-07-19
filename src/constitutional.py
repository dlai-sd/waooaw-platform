"""
waooaw/constitutional.py — In-code constitutional traceability annotations.

Constitutional basis: C-073 (Bidirectional Implementation Traceability — RATIFIED)
IB item:             IB-009 (Foundation Implementation)
Spec:                architecture/reference/TRACEABILITY-PROTOCOL.md Section 3.1

Usage:
    from waooaw.constitutional import constitutional, ConstitutionalMeta

    @constitutional(
        claims=["C-041", "C-003"],
        ib_item="IB-009",
        spec="architecture/reference/ce-validate-action-evaluators.md",
    )
    async def evaluate_tool_authorization(ctx: EvaluationContext) -> EvaluationResult:
        ...
"""

from __future__ import annotations

import asyncio
import functools
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


@dataclass(frozen=True)
class ConstitutionalAnnotation:
    """Machine-readable constitutional traceability annotation. C-073."""
    claims: tuple[str, ...]
    ib_item: str
    spec: str

    def __str__(self) -> str:
        return (
            f"claims={self.claims} "
            f"ib_item={self.ib_item!r} "
            f"spec={self.spec!r}"
        )


def constitutional(
    claims: list[str],
    ib_item: str,
    spec: str,
) -> Callable[[F], F]:
    """
    Decorator: annotates a function with its constitutional traceability chain.

    C-073: every function that implements a constitutional principle carries
    machine-readable annotations so the platform can answer:
    - "Which functions implement C-041?"
    - "If C-041 is amended, what code must change?"

    Args:
        claims:  Constitutional claim IDs this function enforces (e.g., ["C-041"])
        ib_item: IB item that authorized this code (e.g., "IB-009")
        spec:    Path to component spec that describes this function's contract
    """
    annotation = ConstitutionalAnnotation(
        claims=tuple(claims),
        ib_item=ib_item,
        spec=spec,
    )

    def decorator(fn: F) -> F:
        # Attach annotation as a function attribute (machine-readable)
        fn.__constitutional__ = annotation  # type: ignore[attr-defined]

        if asyncio.iscoroutinefunction(fn):
            @functools.wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                return await fn(*args, **kwargs)
            async_wrapper.__constitutional__ = annotation  # type: ignore[attr-defined]
            return async_wrapper  # type: ignore[return-value]
        else:
            @functools.wraps(fn)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                return fn(*args, **kwargs)
            sync_wrapper.__constitutional__ = annotation  # type: ignore[attr-defined]
            return sync_wrapper  # type: ignore[return-value]

    return decorator


class ConstitutionalMeta(type):
    """
    Metaclass for classes that implement constitutional principles.
    Allows applying constitutional annotation at the class level.

    Usage:
        class C041Evaluator(metaclass=ConstitutionalMeta,
                             claims=["C-041"],
                             ib_item="IB-009",
                             spec="architecture/reference/ce-validate-action-evaluators.md"):
            ...
    """
    def __new__(
        mcs,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        claims: list[str] | None = None,
        ib_item: str = "",
        spec: str = "",
    ) -> type:
        cls = super().__new__(mcs, name, bases, namespace)
        if claims:
            cls.__constitutional__ = ConstitutionalAnnotation(  # type: ignore[attr-defined]
                claims=tuple(claims),
                ib_item=ib_item,
                spec=spec,
            )
        return cls
