"""
Unit Tests for Part 5: Preservation & Regression Protection
ReinDev Studio — Architectural Hardening v1

Validates:
1. Invariant lifecycle: PROVEN -> LOCKED -> mutation FORBIDDEN
2. Revalidation & Regression Detection: When a proven test fails, flag REGRESSION immediately
3. Recovery Tracking: Status restored to PROVEN while keeping regression_history intact
4. Prompt Separation: Clear isolation between PROVEN invariants, active failures, and regressions
5. Green State Protection: Formerly passing behaviors remain protected across repair turns
"""

import pytest
from backend.locked_invariants import (
    LockedInvariant,
    discover_newly_proven_invariants,
    revalidate_locked_invariants,
    format_separated_repair_context,
)


def test_invariant_proven_locked_lifecycle():
    """
    A newly discovered passing test is marked PROVEN, state LOCKED, with mutation FORBIDDEN.
    """
    inv = LockedInvariant(
        invariant_id="INV-TEST-001",
        category="PASSING_TEST",
        description="test_addition passes",
        target_symbol="test_addition",
        target_file="main.py",
        condition="Unit test passes",
        status="PROVEN",
        state="LOCKED",
        mutation="FORBIDDEN",
    )

    assert inv.status == "PROVEN"
    assert inv.state == "LOCKED"
    assert inv.mutation == "FORBIDDEN"
    assert inv.ever_regressed is False
    assert inv.regression_count == 0


def test_revalidate_detects_broken_proven_test():
    """
    If a previously PROVEN test is absent from passed_test_names and exit_code != 0,
    it MUST transition to REGRESSION, record failure evidence, and appear in newly_regressed.
    """
    locked_dict = {
        "INV-001": {
            "invariant_id": "INV-001",
            "category": "PASSING_TEST",
            "description": "test_auth passes",
            "target_symbol": "test_auth",
            "target_file": "main.py",
            "status": "PROVEN",
            "state": "LOCKED",
        }
    }

    # Turn 1: test_auth fails (not in passed_test_names)
    test_results = {
        "exit_code": 1,
        "passed_test_names": ["test_health"],
        "failed_test_names": ["test_auth"],
    }

    reg, newly_regressed, maintained = revalidate_locked_invariants(
        locked_invariants=locked_dict,
        code_files={"main.py": ""},
        test_results=test_results,
        target_lang="python",
        turn=1,
    )

    assert len(newly_regressed) == 1
    assert newly_regressed[0].invariant_id == "INV-001"
    assert newly_regressed[0].status == "REGRESSION"
    assert newly_regressed[0].ever_regressed is True
    assert newly_regressed[0].regression_count == 1
    assert len(newly_regressed[0].regression_history) == 1
    assert len(maintained) == 0


def test_revalidate_recovery_preserves_history():
    """
    If a regressed invariant is fixed in a subsequent turn, status becomes PROVEN again,
    but ever_regressed remains True and regression_history is preserved.
    """
    inv = LockedInvariant(
        invariant_id="INV-001",
        category="PASSING_TEST",
        description="test_auth passes",
        target_symbol="test_auth",
        target_file="main.py",
        condition="test_auth passes in pytest",
        status="REGRESSION",
        state="VIOLATED",
        ever_regressed=True,
        regression_count=1,
        regression_history=[{"turn": 1, "failure_evidence": "failed in turn 1"}],
    )

    # Turn 2: test_auth passes again
    test_results = {
        "exit_code": 0,
        "passed_test_names": ["test_auth", "test_health"],
        "failed_test_names": [],
    }

    reg, newly_regressed, maintained = revalidate_locked_invariants(
        locked_invariants={"INV-001": inv},
        code_files={"main.py": ""},
        test_results=test_results,
        target_lang="python",
        turn=2,
    )

    assert len(newly_regressed) == 0
    assert len(maintained) == 1
    rec_inv = maintained[0]
    assert rec_inv.status == "PROVEN"
    assert rec_inv.ever_regressed is True
    assert rec_inv.regression_count == 1
    assert len(rec_inv.regression_history) == 1


def test_format_separated_repair_context_structure():
    """
    format_separated_repair_context cleanly separates:
    - [LOCKED / PROVEN INVARIANTS]
    - [CURRENT FAILURES] (with CRITICAL REGRESSIONS callout)
    - [REPAIR BOUNDARY] (ALLOWED vs FORBIDDEN)
    - [EXPECTED POST-REPAIR STATE]
    """
    proven_inv = LockedInvariant(
        invariant_id="INV-001",
        category="PASSING_TEST",
        description="test_health returns 200",
        target_symbol="test_health",
        target_file="main.py",
        condition="health endpoint returns 200",
        status="PROVEN",
    )
    regressed_inv = LockedInvariant(
        invariant_id="INV-002",
        category="PASSING_TEST",
        description="test_auth passes",
        target_symbol="test_auth",
        target_file="main.py",
        condition="test_auth passes in pytest",
        status="REGRESSION",
        regression_history=[{"failure_evidence": "401 Unauthorized instead of 200"}],
    )

    current_failures = [{"message": "test_profile timed out"}]

    ctx = format_separated_repair_context(
        locked_invariants=[proven_inv],
        current_failures=current_failures,
        regressions=[regressed_inv],
        repair_boundary_allowed=["Fix profile query in main.py"],
        repair_boundary_forbidden=["Do not break auth middleware", "Do not alter test_api.py"],
        target_file="main.py",
    )

    assert "[LOCKED / PROVEN INVARIANTS" in ctx
    assert "INV-001" in ctx
    assert "[CURRENT FAILURES" in ctx
    assert "CRITICAL REGRESSIONS" in ctx
    assert "INV-002" in ctx
    assert "ACTIVE FAILURES" in ctx
    assert "test_profile timed out" in ctx
    assert "[REPAIR BOUNDARY]" in ctx
    assert "ALLOWED CHANGES" in ctx
    assert "FORBIDDEN CHANGES" in ctx
    assert "[EXPECTED POST-REPAIR STATE]" in ctx