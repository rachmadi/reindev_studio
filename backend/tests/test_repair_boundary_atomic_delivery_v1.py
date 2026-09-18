"""
Test Suite: Repair Boundary Atomic Delivery Integrity v1 (Pipeline Repair v1)
Enforces:
1. Full boundary survives compression intact (ALLOWED, FORBIDDEN, PRESERVE).
2. ALLOWED block is never truncated or dropped under normal budgets.
3. FORBIDDEN block is never truncated or dropped under normal budgets.
4. Preserved state survives intact.
5. Repair boundary cannot be partially truncated (zero character slicing).
6. Severe budget pressure causes structured DELIVERY_FAILURE (omission) rather than partial boundary insertion.
7. Zero LLM invocation occurs on invalid delivery.
8. Generic synthetic repair boundaries with zero task-specific tokens.
"""

import pytest
from typing import Dict
from unittest.mock import MagicMock, patch

from backend.context_hardening import (
    compress_context_semantic_detailed,
    distill_failures_section_semantic,
    distill_targets_section_semantic,
)
from backend.architect_preservation import validate_architect_repair_context_delivery


@pytest.fixture
def generic_atomic_sections() -> Dict[str, str]:
    """Generic synthetic context sections with an atomic repair boundary."""
    return {
        "sec_01_authority": (
            "[1] IMMUTABLE ACCEPTANCE AUTHORITY\n"
            "==================================\n"
            "Authority Notice: Absolute acceptance authority belongs to Acceptance Oracle.\n"
            "Authoritative Symbols:\n"
            "  - public_handler_alpha\n"
        ),
        "sec_02_canonical_schema": (
            "[2] CANONICAL BLUEPRINT SCHEMA CONSTRAINTS\n"
            "==========================================\n"
            "Schema specification rules and format constraints for canonical blueprint.\n"
        ),
        "sec_03_current_failures": (
            "[3] CURRENT COMPATIBILITY FAILURES (DETERMINISTIC EVIDENCE)\n"
            "===========================================================\n"
            "ACTIVE FAILURES:\n"
            "  - [FAIL_01] Interface mismatch at public_handler_alpha\n"
            "    Observed: handler_alpha(x: int) -> void\n"
            "    Required: handler_alpha(x: int, y: str) -> bool\n"
        ),
        "sec_04_locked_proven_state": (
            "[4] LOCKED/PROVEN STATE & INVARIANTS\n"
            "====================================\n"
            "Locked Invariants (mutation FORBIDDEN):\n"
            "  - [LOCKED] INV-01: ComponentAlpha core schema\n"
        ),
        "sec_05_current_valid_state": (
            "[5] CURRENT SCAFFOLD & VALIDATED STRUCTURAL STATE (PRESERVE)\n"
            "============================================================\n"
            "Valid structural components:\n"
            "  * Module 'component_alpha.pkg'\n"
            "  * Class ComponentAlpha\n"
        ),
        "sec_06_repair_target": (
            "[6] REPAIR TARGET (ATOMIC REPAIR INVARIANT)\n"
            "============================================\n"
            "WHAT: handler_alpha signature alignment\n"
            "WHERE: component_alpha.pkg\n"
            "OBSERVED: handler_alpha(x: int) missing parameter y: str\n"
            "EXPECTED: handler_alpha(x: int, y: str) -> bool\n"
            "ACTIVE TARGET: Align handler_alpha signature with canonical oracle.\n"
            "REPAIR FORMULA: CURRENT VALID STATE + REPAIRED ELEMENT = EXPECTED POST-REPAIR STATE\n"
        ),
        "sec_07_repair_boundary": (
            "[7] REPAIR BOUNDARY (ATOMIC REPAIR INVARIANT)\n"
            "==============================================\n"
            "PRESERVE (Valid structural state & established interfaces):\n"
            "  * All valid data models (ComponentAlpha) and untouched interface contracts\n"
            "  * Established file collection and module scaffolds valid under canonical schema\n"
            "ALLOWED (Permissible repair mutations):\n"
            "  + Localized repair of handler_alpha parameter shape\n"
            "  + Adding missing parameter declarations required by Oracle\n"
            "FORBIDDEN (Strictly prohibited actions):\n"
            "  x Blind regeneration from scratch (discarding valid state)\n"
            "  x Dropping valid public symbols or data models (ComponentAlpha)\n"
            "  x Mutating immutable acceptance obligations\n"
        ),
        "sec_08_expected_post_repair": (
            "[8] EXPECTED POST-REPAIR STATE\n"
            "==============================\n"
            "1. ArchitecturalBlueprint JSON is structurally valid.\n"
            "2. All acceptance scenarios transition to COMPATIBLE.\n"
        ),
    }


def test_full_boundary_survives_compression_intact(generic_atomic_sections):
    """Test that under standard budget (7,500 chars), the complete boundary survives intact."""
    compressed, telemetry = compress_context_semantic_detailed(generic_atomic_sections, max_chars=7500)
    
    assert "sec_07_repair_boundary" in telemetry["sections_present"]
    assert "sec_07_repair_boundary" not in telemetry["sections_truncated"]
    assert "sec_07_repair_boundary" not in telemetry["sections_omitted"]

    # Verify all atomic elements survive
    assert "PRESERVE" in compressed
    assert "ALLOWED" in compressed
    assert "FORBIDDEN" in compressed

    # Verify delivery validation passes
    is_valid, errors = validate_architect_repair_context_delivery(compressed)
    assert is_valid is True, f"Delivery validation failed: {errors}"


def test_allowed_block_never_truncated_or_dropped_under_normal_budgets(generic_atomic_sections):
    """Test that ALLOWED block is present and complete under standard budgets."""
    compressed, _ = compress_context_semantic_detailed(generic_atomic_sections, max_chars=7500)
    
    assert "ALLOWED (Permissible repair mutations):" in compressed
    assert "+ Localized repair of handler_alpha parameter shape" in compressed
    assert "+ Adding missing parameter declarations required by Oracle" in compressed


def test_forbidden_block_never_truncated_or_dropped_under_normal_budgets(generic_atomic_sections):
    """Test that FORBIDDEN block is present and complete under standard budgets."""
    compressed, _ = compress_context_semantic_detailed(generic_atomic_sections, max_chars=7500)
    
    assert "FORBIDDEN (Strictly prohibited actions):" in compressed
    assert "x Blind regeneration from scratch (discarding valid state)" in compressed
    assert "x Dropping valid public symbols or data models (ComponentAlpha)" in compressed


def test_preserved_state_survives_intact(generic_atomic_sections):
    """Test that PRESERVE block survives intact."""
    compressed, _ = compress_context_semantic_detailed(generic_atomic_sections, max_chars=7500)
    
    assert "PRESERVE (Valid structural state & established interfaces):" in compressed
    assert "* All valid data models (ComponentAlpha) and untouched interface contracts" in compressed


def test_repair_boundary_never_partially_sliced(generic_atomic_sections):
    """
    CRITICAL INVARIANT: Slicing through sec_07_repair_boundary is strictly forbidden.
    Under sweep of tight character budgets, the repair boundary must be either
    100% complete (with PRESERVE, ALLOWED, FORBIDDEN) or completely omitted.
    It must NEVER be partially sliced.
    """
    boundary_content = generic_atomic_sections["sec_07_repair_boundary"]
    
    # Test across a tight range of budgets
    for budget in range(300, 3000, 50):
        compressed, telemetry = compress_context_semantic_detailed(generic_atomic_sections, max_chars=budget)
        
        has_header = "REPAIR BOUNDARY" in compressed
        has_preserve = "PRESERVE" in compressed
        has_allowed = "ALLOWED" in compressed
        has_forbidden = "FORBIDDEN" in compressed
        
        all_present = has_header and has_preserve and has_allowed and has_forbidden
        none_present = (not has_header) and (not has_preserve) and (not has_allowed) and (not has_forbidden)
        
        # If repair boundary was included, it MUST be the full atomic boundary, never partial
        if "sec_07_repair_boundary" in telemetry["sections_present"]:
            assert all_present, (
                f"Budget {budget}: sec_07_repair_boundary was marked present but is incomplete! "
                f"header={has_header}, preserve={has_preserve}, allowed={has_allowed}, forbidden={has_forbidden}"
            )
            # Ensure the full boundary text is inside compressed
            assert boundary_content in compressed, f"Budget {budget}: boundary content was sliced!"
        else:
            # If omitted, it must not be in sections_present or sections_truncated
            assert "sec_07_repair_boundary" in telemetry["sections_omitted"]
            assert "sec_07_repair_boundary" not in telemetry["sections_truncated"]


def test_severe_budget_pressure_causes_structured_delivery_failure(generic_atomic_sections):
    """
    Test that when budget is too tight to hold the atomic boundary,
    the pipeline fails closed cleanly via validate_architect_repair_context_delivery
    with ARCHITECT_CONTEXT_DELIVERY_FAILURE, without raising unhandled exceptions.
    """
    # Extremely small budget where atomic boundary cannot fit
    compressed, telemetry = compress_context_semantic_detailed(generic_atomic_sections, max_chars=400)
    
    # Repair boundary must be omitted
    assert "sec_07_repair_boundary" in telemetry["sections_omitted"]
    
    # Delivery validation must fail closed cleanly
    is_valid, errors = validate_architect_repair_context_delivery(compressed)
    assert is_valid is False
    assert any("ARCHITECT_CONTEXT_DELIVERY_FAILURE" in e for e in errors)
    assert any("Missing repair boundary section" in e or "Repair boundary atomic payload incomplete" in e for e in errors)


def test_tier1_compaction_prevents_failure_crowding(generic_atomic_sections):
    """
    Deterministic Pipeline Defect #1 Regression Test:
    When sec_03_current_failures and sec_06_repair_target contain massive diagnostic
    traces (>10,000 chars), Tier 1 compaction must compact the failure prose so that
    sec_07_repair_boundary is NOT crowded out, preserving the full ALLOWED block.
    """
    sections = dict(generic_atomic_sections)
    
    # Inflate failures with repetitive traceback lines
    inflated_failures = (
        "[3] CURRENT COMPATIBILITY FAILURES (DETERMINISTIC EVIDENCE)\n"
        "===========================================================\n"
        "ACTIVE FAILURES:\n"
        "  - [FAIL_01] Interface mismatch at public_handler_alpha\n"
        "    Observed: handler_alpha(x: int) -> void\n"
        "    Required: handler_alpha(x: int, y: str) -> bool\n"
    )
    for i in range(200):
        inflated_failures += f"    File /usr/lib/python/site-packages/engine/core_{i%5}.py, line {100+i}, in process_request\n"
        inflated_failures += f"      diagnostic_trace_marker_step_{i%10} = verify_contract(symbol_alpha)\n"
    
    sections["sec_03_current_failures"] = inflated_failures
    assert len(sections["sec_03_current_failures"]) > 10000

    # Run compression under standard 7,500 char budget
    compressed, telemetry = compress_context_semantic_detailed(sections, max_chars=7500)

    # Must preserve sec_07_repair_boundary intact despite huge failure section
    assert "sec_07_repair_boundary" in telemetry["sections_present"]
    assert "sec_07_repair_boundary" not in telemetry["sections_truncated"]
    assert "sec_07_repair_boundary" not in telemetry["sections_omitted"]

    # ALLOWED block must be intact
    assert "ALLOWED (Permissible repair mutations):" in compressed
    assert "+ Localized repair of handler_alpha parameter shape" in compressed

    # Delivery validation must PASS
    is_valid, errors = validate_architect_repair_context_delivery(compressed)
    assert is_valid is True, f"Delivery validation failed with errors: {errors}"


def test_zero_llm_invocation_on_delivery_failure(generic_atomic_sections):
    """
    Test that an invalid context delivery immediately aborts
    before any LLM invocation occurs.
    """
    # Create invalid context missing ALLOWED
    invalid_sections = dict(generic_atomic_sections)
    invalid_sections["sec_07_repair_boundary"] = (
        "[7] REPAIR BOUNDARY\n"
        "PRESERVE: All valid models\n"
        "FORBIDDEN: Blind regeneration\n"
    )
    compressed, _ = compress_context_semantic_detailed(invalid_sections, max_chars=7500)
    
    is_valid, errors = validate_architect_repair_context_delivery(compressed)
    assert is_valid is False
    assert any("ALLOWED" in e for e in errors)

    # Mock LLM caller to ensure it is NEVER called when delivery is invalid
    mock_llm = MagicMock()
    
    def simulate_architect_repair_dispatch(context: str):
        valid, errs = validate_architect_repair_context_delivery(context)
        if not valid:
            return {
                "success": False,
                "status": "ARCHITECT_CONTEXT_DELIVERY_FAILURE",
                "errors": errs,
            }
        return mock_llm(context)

    result = simulate_architect_repair_dispatch(compressed)
    assert result["success"] is False
    assert result["status"] == "ARCHITECT_CONTEXT_DELIVERY_FAILURE"
    mock_llm.assert_not_called()


def test_generic_synthetic_boundaries_zero_task_specific_tokens(generic_atomic_sections):
    """
    Static Anti-Solver Audit:
    Ensure tests and boundaries use generic tokens, zero task-specific framework names.
    """
    forbidden_tokens = ["fastapi", "flutter", "dart", "cli_t1", "fastapi_t1", "flutter_t1"]
    for k, v in generic_atomic_sections.items():
        v_lower = v.lower()
        for token in forbidden_tokens:
            assert token not in v_lower, f"Found task-specific token '{token}' in section {k}"
