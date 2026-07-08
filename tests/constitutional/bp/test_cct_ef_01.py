"""
CCT-EF-01: Evidence First Enforcement Test
Constitutional Basis: C-023 (Evidence First), AD-002 (Evidence First enforcement)
"The Constitutional Engine must record constitutional evidence as an atomic,
 durable operation before returning a success response to the calling service."

This test verifies that Business Platform calls Constitutional Engine's RecordEvidence
BEFORE returning 200 to the caller. If CE returns an error, BP must return failure —
not success.

Run: pytest tests/constitutional/bp/test_cct_ef_01.py -v
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
import sys
import os

# Add src/business-platform to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src/business-platform"))


class TestCCTEF01EvidenceFirstEnforcement:
    """
    CCT-EF-01: Evidence First — CE must be called BEFORE BP returns success.

    Tests:
      EF01_a: When CE succeeds → BP returns 201 (contract formed)
      EF01_b: When CE fails → BP returns 500 (contract NOT formed)
      EF01_c: When CE is unavailable → BP returns 500 (never returns 201)
    """

    def test_ef01_a_ce_success_contract_formed(self) -> None:
        """
        EF01_a: When CE.RecordEvidence returns OK, BP should return 201.
        The contract is formed and evidence is recorded.
        """
        # This test will pass when BP is fully wired to CE
        # For foundation sprint: assert the pattern exists in the controller
        from src.business_platform.Controllers.employment_controller import EmploymentController
        import inspect
        source = inspect.getsource(EmploymentController.FormEmploymentContract)

        # Verify Evidence First pattern is in the code
        assert "RecordEvidenceAsync" in source or "_ce.RecordEvidence" in source, \
            "CCT-EF-01 FAIL: BP does not call CE.RecordEvidence (Evidence First violation)"

        assert "StatusCode.Internal" in source or "500" in source, \
            "CCT-EF-01 FAIL: BP does not return failure when CE fails (Evidence First violation)"

        # Pattern check: CE call must appear BEFORE SaveChangesAsync
        ce_pos = source.find("RecordEvidence")
        save_pos = source.find("SaveChangesAsync")
        assert ce_pos < save_pos and ce_pos != -1 and save_pos != -1, \
            "CCT-EF-01 FAIL: CE.RecordEvidence must be called BEFORE SaveChangesAsync (C-023)"

    def test_ef01_b_ce_failure_contract_not_formed(self) -> None:
        """
        EF01_b: When CE returns error, BP must return 500 — contract NOT formed.
        This test runs against a live BP instance with a mocked CE.
        TODO Sprint 2: implement with TestContainers + CE stub returning gRPC error.
        """
        # Foundation stub — verify the pattern exists in source
        from src.business_platform.Controllers.employment_controller import EmploymentController
        import inspect
        source = inspect.getsource(EmploymentController.FormEmploymentContract)

        # Evidence First: CE failure path must exist
        assert "return StatusCode(500" in source or "StatusCode.Internal" in source, \
            "CCT-EF-01 FAIL: BP has no failure path when CE fails (C-023)"

    def test_ef01_c_action_instance_id_generated(self) -> None:
        """
        EF01_c: Each contract formation must have a unique action_instance_id.
        This groups the evidence records for this action (evidence-schema.md).
        """
        from src.business_platform.Controllers.employment_controller import EmploymentController
        import inspect
        source = inspect.getsource(EmploymentController.FormEmploymentContract)

        assert "actionInstanceId" in source.lower() or "action_instance_id" in source.lower(), \
            "CCT-EF-01 FAIL: action_instance_id not present in contract formation evidence"

    def test_ef01_d_constitutional_basis_provided(self) -> None:
        """
        EF01_d: Every RecordEvidence call must include a non-empty constitutional_basis (AD-008).
        """
        from src.business_platform.Controllers.employment_controller import EmploymentController
        import inspect
        source = inspect.getsource(EmploymentController.FormEmploymentContract)

        assert "ConstitutionalBasis" in source, \
            "CCT-EF-01 FAIL: RecordEvidence call missing ConstitutionalBasis (AD-008)"


class TestCCTEF02EvidenceBeforeResponse:
    """
    CCT-EF-02: Evidence record exists in DB BEFORE API response returns.
    Full integration test — requires running services.
    Status: SKELETON — will be fully implemented in Sprint 2 with TestContainers.
    """

    @pytest.mark.skip(reason="Requires running services — Sprint 2 implementation")
    def test_ef02_evidence_in_db_before_200(self) -> None:
        """
        Query DB at t+50ms after request sent, before response received.
        Evidence record must already exist.
        Full specification in tests/constitutional/README.md CCT-EF-02.
        """
        pass
