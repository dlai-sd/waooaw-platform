# Implements: <spec-path> §<section>
# Constitutional basis: C-059 (Implementation Traceability)
from __future__ import annotations

import logging
from uuid import UUID
from typing import Any

logger = logging.getLogger(__name__)


class WhatsAppNotifier:
    """
    WhatsApp notification delivery via 360dialog MCP integration.
    
    Constitutional basis:
    - C-048: Resource Transparency — notifications inform customers of budget status
    - C-051: Alert dispatch mechanism per threshold policy
    - C-059: Implementation traceability via structured logging
    - C-063: PII protection — customer_id not logged, params keys logged only
    
    ADR-023: 360dialog MCP integration (deferred to implementation phase).
    This class stubs the send() method to raise NotImplementedError with TODO.
    Tests must mock this method to inject success/failure responses.
    """

    async def send(
        self,
        customer_id: UUID,
        template_id: str,
        params: dict[str, Any],
    ) -> bool:
        """
        Send a WhatsApp notification via 360dialog MCP.
        
        Args:
            customer_id: Customer UUID (used for routing, not logged as PII per C-063)
            template_id: 360dialog template identifier
            params: Template parameters (safe to log keys only, not values per C-063)
        
        Returns:
            True if message enqueued/sent successfully, False otherwise.
        
        Raises:
            NotImplementedError: Stub pending ADR-023 360dialog MCP integration.
        
        Constitutional:
        - C-048: Proactive notification of budget depletion
        - C-051: Alert dispatch per threshold policy
        - C-059: Traceability — stub location and ADR reference logged
        - C-063: No PII in logs (customer_id not logged; params keys logged only)
        """
        logger.debug(
            "WhatsAppNotifier.send() stub called",
            extra={"template_id": template_id, "param_keys": list(params.keys())},
        )
        raise NotImplementedError(
            "ADR-023: 360dialog MCP integration pending. "
            "Implement via 360dialog API (https://www.360dialog.com/whatsapp-business-api). "
            "TODO: Replace stub with actual MCP call after ADR-023 review."
        )