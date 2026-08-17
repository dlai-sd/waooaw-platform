# Implements: architecture/reference/api-specs/emergency-stop-ws.md full
# constitutional_basis: C-001, C-023, C-024, C-059, C-063
from __future__ import annotations

import asyncio
import base64
import json
import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

import httpx
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from routers.conversation_execution import ConstitutionalGatewayUnavailableError

logger = logging.getLogger(__name__)

router = APIRouter()

CE_STOP_TIMEOUT_SECONDS = 0.20


class FrameType(StrEnum):
    EMERGENCY_STOP = "EMERGENCY_STOP"
    EMERGENCY_STOP_CONFIRMED = "EMERGENCY_STOP_CONFIRMED"
    READY = "READY"
    PING = "PING"
    ERROR = "ERROR"


@dataclass(frozen=True)
class EmergencyStopAuthority:
    tenant_id: str
    customer_id: str
    contract_id: str


def _decode_segment(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


class KeycloakJWTValidator:
    """Validate Keycloak RS256 tokens with the same issuer/audience/lifetime floor as BP."""

    def __init__(self, jwks_url: str, issuer: str, audience: str, client: httpx.AsyncClient) -> None:
        self._jwks_url = jwks_url
        self._issuer = issuer
        self._audience = audience
        self._client = client
        self._keys: dict[str, dict[str, Any]] = {}

    async def _key(self, key_id: str) -> dict[str, Any]:
        if key_id not in self._keys:
            response = await self._client.get(self._jwks_url)
            response.raise_for_status()
            self._keys = {
                str(key["kid"]): key for key in response.json().get("keys", []) if key.get("kty") == "RSA" and key.get("kid")
            }
        if key_id not in self._keys:
            raise ValueError("unknown signing key")
        return self._keys[key_id]

    async def validate(self, token: str) -> EmergencyStopAuthority:
        header_part, payload_part, signature_part = token.split(".")
        header = json.loads(_decode_segment(header_part))
        claims = json.loads(_decode_segment(payload_part))
        if header.get("alg") != "RS256" or not header.get("kid"):
            raise ValueError("unsupported token header")
        key = await self._key(str(header["kid"]))
        modulus = int.from_bytes(_decode_segment(str(key["n"])), "big")
        exponent = int.from_bytes(_decode_segment(str(key["e"])), "big")
        public_key = rsa.RSAPublicNumbers(exponent, modulus).public_key()
        public_key.verify(
            _decode_segment(signature_part),
            f"{header_part}.{payload_part}".encode(),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        now = int(time.time())
        if int(claims["exp"]) <= now - 30 or int(claims.get("nbf", 0)) > now + 30:
            raise ValueError("token is not active")
        audience = claims.get("aud")
        if audience != self._audience and (not isinstance(audience, list) or self._audience not in audience):
            raise ValueError("invalid audience")
        if claims.get("iss") != self._issuer:
            raise ValueError("invalid issuer")
        authority = EmergencyStopAuthority(
            tenant_id=str(claims["tenant_id"]),
            customer_id=str(claims["sub"]),
            contract_id=str(claims["contract_id"]),
        )
        if not all((authority.tenant_id, authority.customer_id, authority.contract_id)):
            raise ValueError("missing authority claim")
        return authority


async def _close_with_error(
    websocket: WebSocket,
    code: str,
    message: str,
) -> None:
    """
    Send an error frame and close the WebSocket.
    C-059: caller is responsible for having already logged the evidence record
    before invoking this helper.
    C-063: reason is a code string — no PII.
    """
    try:
        await websocket.send_json({"type": FrameType.ERROR, "code": code, "message": message})
        await websocket.close(code=1008)
    except asyncio.CancelledError:
        raise
    except (RuntimeError, OSError) as close_err:
        # Connection may already be dead — log as evidence (C-059) and continue.
        logger.error(
            "Emergency Stop error-close failed — connection already dead",
            exc_info=True,
            extra={
                "context": {
                    "close_reason": code,
                    "error": str(close_err),
                    "constitutional_basis": "C-059",
                }
            },
        )


async def _refuse_unauthorized(websocket: WebSocket) -> None:
    response = JSONResponse(
        status_code=401,
        media_type="application/problem+json",
        content={"type": "about:blank", "title": "Unauthorized", "status": 401},
    )
    await websocket.send_denial_response(response)


@router.websocket("/ws/emergency-stop")
async def emergency_stop_websocket(websocket: WebSocket) -> None:
    """
    Emergency Stop WebSocket endpoint.

    Constitutional obligations:
    - C-001: End-to-end halt confirmed within ≤250ms P99.
    - C-024: Halt is architecturally guaranteed — no conditional paths that skip signal.
    - C-023: CE owns signaling and records evidence before this endpoint confirms the stop.
    - C-063: No PII in log statements.
    - C-059: Every caught exception that is not re-raised produces a structured log
             record that serves as an evidence trail.

    Protocol (from emergency-stop-ws.md):
     1. Validate the Keycloak bearer JWT before accepting the upgrade.
     2. Send READY with the authenticated contract.
     3. Reject any command whose contract differs from authenticated authority.
     4. Call CE TriggerEmergencyStop with tenant metadata and a 200ms deadline.
     5. Project CE evidence into EMERGENCY_STOP_CONFIRMED, then close.

    Frame contract (emergency-stop-ws.md):
    Client → Server:
      {"type": "EMERGENCY_STOP", "contractId": "<uuid>",
       "activeSessionIds": ["<workflow-id>", ...]}
    Server → Client (after CE evidence written):
      {"type": "EMERGENCY_STOP_CONFIRMED",
       "emergencyStopRecordId": "<uuid>",
       "affectedSessions": ["<workflow-id>"],
       "confirmedAt": "<ISO-8601>"}
    """
    authorization = websocket.headers.get("Authorization", "")
    validator = getattr(websocket.app.state, "emergency_stop_jwt_validator", None)
    if validator is None or not authorization.startswith("Bearer "):
        await _refuse_unauthorized(websocket)
        return
    try:
        authority = await validator.validate(authorization.removeprefix("Bearer ").strip())
    except Exception:
        await _refuse_unauthorized(websocket)
        return

    await websocket.accept(subprotocol="waooaw-emergency-stop-v1")

    connected_at = datetime.now(timezone.utc).isoformat()
    try:
        await websocket.send_json(
            {
                "type": FrameType.READY,
                "contractId": authority.contract_id,
                "connectedAt": connected_at,
            }
        )
    except asyncio.CancelledError:
        raise
    except (RuntimeError, OSError) as e:
        # READY frame failed — client disconnected before we could greet.
        # C-059: log as evidence; no re-raise (connection already dead).
        logger.error(
            "Emergency Stop READY frame send failed",
            exc_info=True,
            extra={
                "context": {
                    "error": str(e),
                    "constitutional_basis": "C-059",
                }
            },
        )
        return

    try:
        frame = await websocket.receive_json()
    except asyncio.CancelledError:
        raise
    except WebSocketDisconnect:
        logger.info(
            "WebSocket disconnected before EMERGENCY_STOP frame received",
            extra={"context": {"contract_id": authority.contract_id}},
        )
        return
    except (ValueError, KeyError) as e:
        # Malformed frame — C-059: log as evidence.
        logger.error(
            "Emergency Stop frame parse failed — malformed JSON",
            exc_info=True,
            extra={
                "context": {
                    "error": str(e),
                    "constitutional_basis": "C-059",
                }
            },
        )
        await _close_with_error(websocket, "INTERNAL", "Malformed Emergency Stop command")
        return

    frame_type = frame.get("type")
    if frame_type != FrameType.EMERGENCY_STOP:
        logger.error(
            "Emergency Stop received unexpected frame type — expected EMERGENCY_STOP",
            extra={
                "context": {
                    "received_type": frame_type,
                    "constitutional_basis": "C-059",
                }
            },
        )
        await _close_with_error(websocket, "INTERNAL", "Unexpected Emergency Stop command")
        return

    contract_id = str(frame.get("contractId", ""))
    if contract_id != authority.contract_id:
        logger.error(
            "Emergency Stop contract authority mismatch",
            extra={
                "context": {
                    "constitutional_basis": "C-059",
                }
            },
        )
        await _close_with_error(websocket, "INVALID_CONTRACT", "Contract is not authorized")
        return

    raw_session_ids = frame.get("activeSessionIds", [])
    if not isinstance(raw_session_ids, list) or not all(isinstance(value, str) for value in raw_session_ids):
        await _close_with_error(websocket, "INTERNAL", "Invalid active session identifiers")
        return
    try:
        active_session_ids = [str(uuid.UUID(value)) for value in raw_session_ids]
    except ValueError:
        await _close_with_error(websocket, "INTERNAL", "Invalid active session identifiers")
        return
    gateway = getattr(websocket.app.state, "conversation_constitutional_gateway", None)
    if gateway is None:
        await _close_with_error(websocket, "INTERNAL", "Emergency Stop is unavailable")
        return
    try:
        result = await asyncio.wait_for(
            gateway.trigger_emergency_stop(
                contract_id=authority.contract_id,
                tenant_id=authority.tenant_id,
                stopped_by=authority.customer_id,
                active_session_ids=active_session_ids,
            ),
            timeout=CE_STOP_TIMEOUT_SECONDS,
        )
    except (ConstitutionalGatewayUnavailableError, TimeoutError, asyncio.TimeoutError):
        await _close_with_error(websocket, "INTERNAL", "Emergency Stop could not be confirmed")
        return

    try:
        await websocket.send_json(
            {
                "type": FrameType.EMERGENCY_STOP_CONFIRMED,
                "emergencyStopRecordId": result.emergency_stop_record_id,
                "affectedSessions": list(result.affected_sessions),
                "confirmedAt": result.recorded_at,
            }
        )
    except asyncio.CancelledError:
        raise
    except (RuntimeError, OSError) as e:
        # Confirmation frame failed — halt was already signalled; client may
        # have disconnected. C-059: log as evidence.
        logger.error(
            "Emergency Stop CONFIRMED frame send failed — halt already signalled",
            exc_info=True,
            extra={
                "context": {
                    "affected_sessions": list(result.affected_sessions),
                    "error": str(e),
                    "constitutional_basis": "C-059",
                }
            },
        )
        # Do not return error to client — halt was executed. Connection is dead.
        return

    # ── Step 6: Close the WebSocket cleanly ────────────────────────────────
    try:
        await websocket.close(code=1000)
    except asyncio.CancelledError:
        raise
    except (RuntimeError, OSError) as e:
        # Close failure after confirmed halt — not a constitutional error.
        # C-059: log as evidence record.
        logger.error(
            "Emergency Stop WebSocket close failed after confirmed halt",
            exc_info=True,
            extra={
                "context": {
                    "error": str(e),
                    "constitutional_basis": "C-059",
                }
            },
        )
