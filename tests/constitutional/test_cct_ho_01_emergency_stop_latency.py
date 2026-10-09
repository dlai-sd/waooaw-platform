"""CCT-HO-01: Emergency Stop WebSocket round-trip acceptance."""

# Implements: WC110-R006, WC110-R009; emergency-stop-ws.md latency budget
# Constitutional basis: C-001, C-023, C-024, C-059, C-063

import importlib.util
import os
from pathlib import Path
import sys
import time
from typing import Any

from starlette.testclient import TestClient


ROOT = Path(__file__).resolve().parents[2]
PROFESSIONAL_RUNTIME = ROOT / "src/professional-runtime"
sys.path.insert(0, str(PROFESSIONAL_RUNTIME))
sys.path.insert(0, str(ROOT / "src/agent-adapters"))
sys.path.insert(0, str(ROOT / "src/digital-marketing-agent"))
os.environ.setdefault("DMA_ARTIFACT_DIGEST", "sha256:" + "ab" * 32)
os.environ.setdefault("DMA_ADMISSION_CONTENT_DIGEST", "sha256:" + "cd" * 32)
os.environ.setdefault("PR_SERVICE_JWT_SECRET", "test-service-assertion")
sys.modules.pop("relationship_workspace", None)

module_spec = importlib.util.spec_from_file_location(
    "professional_runtime_main",
    PROFESSIONAL_RUNTIME / "main.py",
)
if module_spec is None or module_spec.loader is None:
    raise ImportError("Professional Runtime main module could not be loaded")
professional_runtime_main = importlib.util.module_from_spec(module_spec)
sys.modules["professional_runtime_main"] = professional_runtime_main
module_spec.loader.exec_module(professional_runtime_main)

from constitutional_gateway import EmergencyStopResult  # noqa: E402
from routers.emergency_stop import EmergencyStopAuthority  # noqa: E402


app = professional_runtime_main.app


class SyntheticAuthorityValidator:
    async def validate(self, _token: str) -> EmergencyStopAuthority:
        return EmergencyStopAuthority(
            tenant_id="tenant-synthetic",
            customer_id="customer-synthetic",
            contract_id="contract-synthetic",
        )


class EvidenceBackedEmergencyStopGateway:
    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []

    async def trigger_emergency_stop(self, **request: Any) -> EmergencyStopResult:
        self.requests.append(request)
        return EmergencyStopResult(
            emergency_stop_record_id="EMERGENCY_STOP:11111111-1111-1111-1111-111111111111",
            affected_sessions=("22222222-2222-2222-2222-222222222222",),
            recorded_at="2026-09-30T00:00:00Z",
        )


def test_e2e_emergency_stop_websocket_confirms_evidence_within_250ms() -> None:
    gateway = EvidenceBackedEmergencyStopGateway()
    app.state.emergency_stop_jwt_validator = SyntheticAuthorityValidator()
    app.state.conversation_constitutional_gateway = gateway

    with TestClient(app).websocket_connect(
        "/ws/emergency-stop",
        headers={"Authorization": "Bearer synthetic"},
        subprotocols=["waooaw-emergency-stop-v1"],
    ) as websocket:
        ready = websocket.receive_json()
        assert ready["type"] == "READY"
        started = time.perf_counter_ns()
        websocket.send_json(
            {
                "type": "EMERGENCY_STOP",
                "contractId": "contract-synthetic",
                "activeSessionIds": ["22222222-2222-2222-2222-222222222222"],
            }
        )
        confirmation = websocket.receive_json()
        elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000

    assert elapsed_ms <= 250
    assert confirmation == {
        "type": "EMERGENCY_STOP_CONFIRMED",
        "emergencyStopRecordId": "EMERGENCY_STOP:11111111-1111-1111-1111-111111111111",
        "affectedSessions": ["22222222-2222-2222-2222-222222222222"],
        "confirmedAt": "2026-09-30T00:00:00Z",
    }
    assert gateway.requests == [
        {
            "contract_id": "contract-synthetic",
            "tenant_id": "tenant-synthetic",
            "stopped_by": "customer-synthetic",
            "active_session_ids": ["22222222-2222-2222-2222-222222222222"],
        },
    ]
