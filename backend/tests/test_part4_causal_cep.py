"""
Unit Tests for Part 4: Causal Evidence Repair
ReinDev Studio — Architectural Hardening v1

Validates:
1. Contextual Evidence Package (CEP) rendering with all canonical sections
2. Causal trace & raw failure traceback inclusion in Section 1B/7
3. Non-solver guarantee in Actionable Prescriptions (WHAT vs HOW)
4. Strict Repair Boundary rendering (ALLOWED vs FORBIDDEN)
5. Multi-pass semantic compactification preserving invariants & prescriptions
"""

import pytest
from backend.contextual_evidence import (
    ContextualEvidencePackage,
    ViolationItem,
    PreservedInvariant,
    RepairBoundary,
    ActionableRepairPrescription,
    RequiredChange,
    render_repair_directive,
)
from backend.context_hardening import (
    build_developer_repair_context,
)


@pytest.fixture
def sample_cep():
    pkg = ContextualEvidencePackage(
        package_id="CEP-TEST-001",
        timestamp="2026-09-14T00:00:00Z",
        validator="SANDBOX_EXECUTOR",
        phase="DEVELOPER",
        validator_type="ITERATION",
        verdict="FAIL",
        causal_owner="DEVELOPER",
        failure_summary="1 of 3 tests failed: test_get_users raised 404 Not Found",
        root_causes=[
            "Endpoint /users method GET is missing in implementation routing table",
        ],
        violations=[
            ViolationItem(
                violation_id="VIO-001",
                criterion="http_endpoint_availability",
                severity="CRITICAL",
                location="main.py:app",
                observed_state="HTTP 404 Not Found",
                expected_state="HTTP 200 OK with List[User]",
                source_detector="PYTEST_TESTCLIENT",
                observed_symbol="/users",
            )
        ],
        violation_dependencies=[],
        authoritative_context={"contract_id": "CNT-001"},
        active_constraints={"max_files": 2},
        preserved_invariants=[
            PreservedInvariant(
                invariant_id="INV-001",
                category="PASSING_TEST",
                description="test_health_check returns 200",
                evidence_value="HTTP 200",
                status="PROVEN",
                target="behavior:test_health_check",
                state="LOCKED",
                mutation="FORBIDDEN",
            )
        ],
        repair_boundary=RepairBoundary(
            allowed_changes=["Implement GET /users handler in main.py"],
            forbidden_changes=["Do not mutate GET /health handler", "Do not alter frozen oracle test_api.py"],
        ),
        forbidden_changes=["Do not mutate GET /health handler"],
        required_changes=[
            RequiredChange(
                change_id="REQ-001",
                target="main.py:app",
                violation_ref="VIO-001",
                deterministic_requirement="Route GET /users must return status 200 with list of user models",
                preserve_refs=["INV-001"],
                forbidden_refs=[],
            )
        ],
        expected_post_repair_state=["All pytest test cases pass with exit code 0"],
        verification_criteria=["pytest tests/test_api.py exit_code == 0"],
        source_of_truth="FROZEN_ORACLE_TESTS",
        evidence=[
            {
                "item": "sandbox_failing_tests",
                "observed": [
                    {
                        "test_name": "test_get_users",
                        "failure_type": "AssertionError",
                        "message": "assert 404 == 200",
                        "expected": "200",
                        "actual": "404",
                        "source_file": "tests/test_api.py",
                        "source_line": 28,
                        "traceback_excerpt": "res = client.get('/users')\nassert res.status_code == 200",
                    }
                ],
            },
            {
                "item": "sandbox_error_excerpt",
                "observed": "FAILED tests/test_api.py::test_get_users - assert 404 == 200",
            },
        ],
        remaining_budget=3,
        actionable_prescriptions=[
            ActionableRepairPrescription(
                prescription_id="RX-001",
                evidence_ref="VIO-001",
                observed_failure="HTTP 404 on GET /users",
                oracle_call_site="tests/test_api.py:28 -> client.get('/users')",
                implementation_symbol="main.py:app",
                evidence_basis="PYTEST_EXECUTION_TRACE",
                required_change="Contract requires route GET /users returning 200 OK with list of users",
                repair_boundary_allowed=["main.py"],
                repair_boundary_forbidden=["tests/test_api.py"],
                expected_post_repair_state="GET /users responds with HTTP 200",
                verification_evidence="test_get_users passes",
            )
        ],
    )
    return pkg


def test_render_repair_directive_all_sections_present(sample_cep):
    """
    render_repair_directive MUST render:
    - Failure Summary
    - Sandbox Failure Evidence (failing tests, location, traceback)
    - Derived Diagnosis / Root Cause
    - Violation Roster
    - Actionable Repair Prescriptions
    - Preserved Invariants (LOCKED — mutation FORBIDDEN)
    - Repair Boundary (ALLOWED vs FORBIDDEN)
    - Verification Criteria
    """
    rendered = render_repair_directive(sample_cep)

    assert "DETERMINISTIC FACTS & FAILURE SUMMARY" in rendered
    assert "DETERMINISTIC SANDBOX FAILURE EVIDENCE" in rendered
    assert "test_get_users" in rendered
    assert "assert 404 == 200" in rendered
    assert "DERIVED DETERMINISTIC DIAGNOSIS (ROOT CAUSE)" in rendered
    assert "COMPLETE VIOLATION ROSTER" in rendered
    assert "ACTIONABLE REPAIR PRESCRIPTIONS" in rendered
    assert "RX-001" in rendered
    assert "PRESERVED INVARIANTS & LOCKED INVARIANTS" in rendered
    assert "INV-001" in rendered
    assert "REPAIR BOUNDARIES & ACTIVE CONSTRAINTS" in rendered
    assert "ALLOWED CHANGES:" in rendered
    assert "FORBIDDEN CHANGES" in rendered
    assert "VERIFICATION CRITERIA" in rendered


def test_causal_trace_includes_exact_location_and_traceback(sample_cep):
    """
    Evidence section MUST contain exact source file, line, and traceback excerpt.
    """
    rendered = render_repair_directive(sample_cep)
    assert "tests/test_api.py:28" in rendered
    assert "client.get('/users')" in rendered


def test_actionable_prescriptions_non_solver_guarantee(sample_cep):
    """
    Actionable prescriptions MUST describe WHAT must be true according to contract,
    NOT code implementation hacks (e.g. no '@app.get("/users") def get_users(): return []').
    """
    rendered = render_repair_directive(sample_cep)
    # Prescriptions section exists
    assert "ACTIONABLE REPAIR PRESCRIPTIONS" in rendered
    # Non-solver check on prescriptions
    rx_section = rendered[rendered.find("ACTIONABLE REPAIR PRESCRIPTIONS"):]
    rx_block = rx_section[:rx_section.find("[5. PRESERVED INVARIANTS")]
    assert "def " not in rx_block
    assert "return " not in rx_block


def test_compactification_preserves_prescriptions_and_invariants(sample_cep):
    """
    When max_chars is constrained, multi-pass compactification drops raw trace details
    first while strictly preserving Actionable Prescriptions and Preserved Invariants.
    """
    # Restrict max_chars to force Pass 2 compactification
    compact = render_repair_directive(sample_cep, max_chars=3000)

    assert "RX-001" in compact
    assert "INV-001" in compact
    assert "ALLOWED CHANGES:" in compact
    assert "FORBIDDEN CHANGES" in compact


def test_build_developer_repair_context_integration(sample_cep):
    """
    build_developer_repair_context integrates the CEP into the 11-section prompt,
    correctly including locked invariants, validator results, and repair boundaries.
    """
    state = {
        "target_language": "python",
        "contract": {
            "task_intent": {"domain": "REST_API"},
            "interface_contracts": [{"identifier": "/users"}],
        },
        "contract_status": "FROZEN",
        "contract_sha256": "abcdef1234567890" * 4,
        "code_files": {"main.py": "# initial code"},
        "locked_invariants": {
            "INV-001": {
                "status": "PROVEN",
                "description": "test_health_check returns 200",
                "regression_count": 0,
            }
        },
    }

    ctx, telemetry = build_developer_repair_context(state, pkg=sample_cep)

    assert "[1] FROZEN CONTRACT" in ctx
    assert "[3] LOCKED INVARIANTS" in ctx
    assert "INV-001" in ctx
    assert "[5] VALIDATOR RESULT" in ctx
    assert "[8] PRESCRIPTION" in ctx
    assert "[9] REPAIR BOUNDARY" in ctx
    assert "[10] FORBIDDEN REGRESSIONS" in ctx
    assert "[11] VERIFICATION CRITERIA" in ctx
    assert telemetry["locked_invariants"] >= 1