"""
Test Suite: Context Delivery Integrity & Repair-Critical Information Preservation v1
Pipeline Integrity Verification (Properties A through P)

Five Mandatory Invariants Enforced:
1. Structured DELIVERY_FAILURE (No ValueError, No LLM invocation, No repair turn consumed)
2. Configurable Budget (7,500 is configuration, not an architectural invariant)
3. Relational Preservation in Valid State (Model -> target_file -> interface -> scaffold -> obligation -> scenario)
4. Atomic Semantic Payload (Target: what, where, observed, expected; Boundary: PRESERVE, ALLOWED, FORBIDDEN)
5. Generalization & Behavioral Multi-Task Verification (Task Alpha & Task Beta with distinct vocabulary)
"""

import ast
import json
import re
from typing import Dict, Any, List
import pytest

from backend.context_hardening import (
    ARCHITECT_REPAIR_PRIORITY_ORDER,
    DEFAULT_PRIORITY_ORDER,
    ContextTelemetry,
    compress_context_semantic,
    compress_context_semantic_detailed,
    compress_valid_state_semantic,
    build_architect_repair_context,
    build_architect_decision_context,
)
from backend.architect_preservation import (
    validate_architect_repair_context_delivery,
    RepairStateLedger,
    RepairStateItem,
    RepairTransitionStatus,
)
from backend.agents.architect import architect_agent
from backend.graph import architect_validator_node, route_after_architect_validator


@pytest.fixture
def generic_synthetic_sections() -> Dict[str, str]:
    """Provides a realistic set of synthetic repair context sections without domain hardcoding."""
    return {
        "sec_01_authority": (
            "[1] IMMUTABLE ACCEPTANCE AUTHORITY (ORACLE_FACT — verified test suite)\n"
            "======================================================================\n"
            "Authority Notice: Absolute acceptance authority belongs to Acceptance Oracle test suite.\n"
            "Authoritative Oracle Symbols:\n"
            "  - public_handler_alpha\n"
            "  - public_model_beta\n"
        ),
        "sec_02_canonical_schema": (
            "[2] ACCEPTANCE OBLIGATION LEDGER & CANONICAL BLUEPRINT SCHEMA CONSTRAINTS\n"
            "========================================================================\n"
            "Canonical Schema and Acceptance Obligations determine structural reality.\n"
            + ("Schema specification rule verbose line item detail.\n" * 40)
            + "ACCEPTANCE OBLIGATION LEDGER (READ-ONLY):\n"
            "1. SCENARIO: SCN-GEN-01 | Stimulus: call_alpha()\n"
            "2. SCENARIO: SCN-GEN-02 | Stimulus: call_beta()\n"
        ),
        "sec_03_current_failures": (
            "[3] CURRENT COMPATIBILITY FAILURES (DETERMINISTIC EVIDENCE)\n"
            "===========================================================\n"
            "ACTIVE FAILURES (Multi-failure representation):\n"
            "  - [COMPATIBILITY_FAIL_01] Interface signature mismatch\n"
            "    Observed: handler_alpha(x: int) -> void\n"
            "    Required: handler_alpha(x: int, y: str) -> bool\n"
        ),
        "sec_04_locked_proven_state": (
            "[4] LOCKED/PROVEN STATE & INVARIANTS (State Transition Ledger — PRESERVED=TRUE)\n"
            "================================================================================\n"
            "Locked Invariants (mutation FORBIDDEN):\n"
            "  - [LOCKED] INV-GEN-01: public_model_beta schema invariant\n"
        ),
        "sec_05_current_valid_state": (
            "[5] CURRENT SCAFFOLD & VALIDATED STRUCTURAL STATE (CURRENT ARCHITECT STATE — PRESERVE)\n"
            "======================================================================================\n"
            "Authority Notice: VALID != REPAIR TARGET. Therefore, VALID MUST BE PRESERVED.\n"
            "Repair Formula: CURRENT VALID STATE + REPAIRED ELEMENT = EXPECTED POST-REPAIR STATE.\n"
            "Relational Invariant: Preserve structural links (Model -> target_file -> interface -> scaffold -> obligation -> scenario).\n"
            "Established File Collection (file_tree): ['module_alpha.pkg']\n"
            "Established Interface Contracts: ['public_handler_alpha']\n"
            "Established Data Models: ['ComponentAlpha']\n"
            "Established Module Scaffolds & Semantic Relationships:\n"
            "  * Module 'module_alpha.pkg':\n"
            "      Target File: module_alpha.pkg\n"
            "      Associated Interfaces: ['public_handler_alpha']\n"
            "      Associated Data Models: ['ComponentAlpha']\n"
            "      Linked Scenarios: ['SCN-GEN-01']\n"
            "      Scaffold Interface Signatures (450 chars):\n"
            "```\n"
            "class ComponentAlpha:\n"
            "    def handler_alpha(self, x: int):\n"
            + ("        # internal calculation step\n        pass\n" * 30)
            + "```\n"
        ),
        "sec_06_repair_target": (
            "[6] REPAIR TARGET (ATOMIC REPAIR INVARIANT)\n"
            "============================================\n"
            "WHAT (Target element requiring repair): handler_alpha signature alignment\n"
            "WHERE (Target file / artifact location): module_alpha.pkg\n"
            "OBSERVED (Identified failure or incompatibility state):\n"
            "  Observed handler_alpha(x: int) missing parameter y: str\n"
            "EXPECTED (Required transition / post-repair state):\n"
            "  handler_alpha(x: int, y: str) -> bool\n"
            "\nACTIVE TARGET: Localized repair of compatibility failures (INCOMPATIBLE -> COMPATIBLE).\n"
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
            "1. ArchitecturalBlueprint JSON is structurally valid per canonical schema.\n"
            "2. All acceptance scenarios transition to COMPATIBLE (0 regressions).\n"
            "3. All valid structural elements from prior state are preserved.\n"
            "4. Contract status transitions to FROZEN with canonical SHA-256 seal.\n"
        ),
        "sec_09_relational_blueprint": (
            "[9] IMPLEMENTATION GROUNDING & RELATIONAL BLUEPRINT STATE [F]\n"
            "============================================================\n"
            "User Task Intent:\n"
            "Build generic component alpha service.\n"
            + ("Symbol relation mapping narrative details.\n" * 20)
        ),
        "sec_10_raw_diagnostics": (
            "[10] RAW DIAGNOSTICS (Bounded to prevent displacement of priority context)\n"
            "=========================================================================\n"
            "Traceback (most recent call last):\n"
            "  File 'test_runner.pkg', line 42, in test_handler_alpha\n"
            "    TypeError: handler_alpha() missing 1 required positional argument: 'y'\n"
            + ("  Internal stack frame details line\n" * 25)
        ),
    }


# ===========================================================================
# Property A: Context below budget -> all sections survive intact
# ===========================================================================
def test_property_a_context_below_budget_all_survive(generic_synthetic_sections):
    total_len = sum(len(v) for v in generic_synthetic_sections.values()) + 1000
    compressed, meta = compress_context_semantic_detailed(
        generic_synthetic_sections,
        max_chars=total_len,
        priority_order=ARCHITECT_REPAIR_PRIORITY_ORDER
    )
    assert meta["compression_applied"] is False
    assert len(meta["sections_omitted"]) == 0
    for k in generic_synthetic_sections:
        assert k in meta["sections_present"]
        assert generic_synthetic_sections[k].splitlines()[0] in compressed


# ===========================================================================
# Property B: Context above budget -> critical sections protected
# ===========================================================================
def test_property_b_context_above_budget_critical_sections_protected(generic_synthetic_sections):
    compressed, meta = compress_context_semantic_detailed(
        generic_synthetic_sections,
        max_chars=5500,
        priority_order=ARCHITECT_REPAIR_PRIORITY_ORDER
    )
    assert meta["compression_applied"] is True
    tier1_keys = [
        "sec_01_authority",
        "sec_03_current_failures",
        "sec_06_repair_target",
        "sec_07_repair_boundary",
        "sec_05_current_valid_state",
        "sec_04_locked_proven_state",
    ]
    for k in tier1_keys:
        assert k in meta["sections_present"], f"Critical section {k} was dropped under budget pressure!"
        assert generic_synthetic_sections[k].splitlines()[0] in compressed


# ===========================================================================
# Property C: Repair target atomic payload (what, where, observed, expected)
# ===========================================================================
def test_property_c_repair_target_atomic_payload_preservation(generic_synthetic_sections):
    compressed, _ = compress_context_semantic_detailed(
        generic_synthetic_sections,
        max_chars=5000,
        priority_order=ARCHITECT_REPAIR_PRIORITY_ORDER
    )
    assert "[6] REPAIR TARGET" in compressed
    # Validate the 4 semantic payload elements required by Invariant 4
    assert "WHAT" in compressed
    assert "WHERE" in compressed
    assert "OBSERVED" in compressed
    assert "EXPECTED" in compressed


# ===========================================================================
# Property D: Repair boundary atomic payload (PRESERVE, ALLOWED, FORBIDDEN)
# ===========================================================================
def test_property_d_repair_boundary_atomic_payload_preservation(generic_synthetic_sections):
    compressed, _ = compress_context_semantic_detailed(
        generic_synthetic_sections,
        max_chars=5000,
        priority_order=ARCHITECT_REPAIR_PRIORITY_ORDER
    )
    assert "[7] REPAIR BOUNDARY" in compressed
    # Validate the 3 semantic payload elements required by Invariant 4
    assert "PRESERVE" in compressed
    assert "ALLOWED" in compressed
    assert "FORBIDDEN" in compressed


# ===========================================================================
# Property E: Current failures survive compression
# ===========================================================================
def test_property_e_current_failures_preservation(generic_synthetic_sections):
    compressed, _ = compress_context_semantic_detailed(
        generic_synthetic_sections,
        max_chars=5000,
        priority_order=ARCHITECT_REPAIR_PRIORITY_ORDER
    )
    assert "[3] CURRENT COMPATIBILITY FAILURES" in compressed
    assert "COMPATIBILITY_FAIL_01" in compressed
    assert "Observed:" in compressed
    assert "Required:" in compressed


# ===========================================================================
# Property F: Relational preservation in valid state (Correction 3)
# ===========================================================================
def test_property_f_current_valid_state_preserves_relationships(generic_synthetic_sections):
    """Verifies that compression preserves structural relationships, not just bare strings."""
    compressed, _ = compress_context_semantic_detailed(
        generic_synthetic_sections,
        max_chars=5000,
        priority_order=ARCHITECT_REPAIR_PRIORITY_ORDER
    )
    assert "[5] CURRENT SCAFFOLD & VALIDATED STRUCTURAL STATE" in compressed
    # Relational chain must survive: Model -> target_file -> interface -> scaffold -> obligation -> scenario
    assert "Target File: module_alpha.pkg" in compressed
    assert "Associated Interfaces:" in compressed
    assert "Associated Data Models:" in compressed
    assert "ComponentAlpha" in compressed
    assert "def handler_alpha" in compressed


# ===========================================================================
# Property G: Locked invariants survive compression
# ===========================================================================
def test_property_g_locked_invariants_preservation(generic_synthetic_sections):
    compressed, _ = compress_context_semantic_detailed(
        generic_synthetic_sections,
        max_chars=5000,
        priority_order=ARCHITECT_REPAIR_PRIORITY_ORDER
    )
    assert "[4] LOCKED/PROVEN STATE & INVARIANTS" in compressed
    assert "INV-GEN-01" in compressed


# ===========================================================================
# Property H: Lower-priority compression compresses Tier 2 and Tier 3
# ===========================================================================
def test_property_h_lower_priority_sections_compressed(generic_synthetic_sections):
    compressed, meta = compress_context_semantic_detailed(
        generic_synthetic_sections,
        max_chars=5000,
        priority_order=ARCHITECT_REPAIR_PRIORITY_ORDER
    )
    truncated_or_compressed = meta["sections_truncated"]
    assert any(k in truncated_or_compressed for k in ("sec_10_raw_diagnostics", "sec_02_canonical_schema", "sec_09_relational_blueprint", "sec_05_current_valid_state"))


# ===========================================================================
# Property I: Critical section omission is never silent
# ===========================================================================
def test_property_i_critical_section_omission_is_never_silent(generic_synthetic_sections):
    compressed, meta = compress_context_semantic_detailed(
        generic_synthetic_sections,
        max_chars=800,
        priority_order=ARCHITECT_REPAIR_PRIORITY_ORDER
    )
    assert len(meta["sections_omitted"]) > 0
    is_valid, errs = validate_architect_repair_context_delivery(compressed)
    assert is_valid is False
    assert any("ARCHITECT_CONTEXT_DELIVERY_FAILURE" in e for e in errs)


# ===========================================================================
# Property J: Delivery validator rejects when atomic payload is incomplete (Correction 4)
# ===========================================================================
def test_property_j_delivery_validator_rejection_on_missing_payload_elements():
    # Scenario 1: Missing FORBIDDEN from boundary (only 2 of 3 elements present)
    partial_boundary = (
        "[1] IMMUTABLE ACCEPTANCE AUTHORITY\nAuthority: FROZEN_ORACLE\n"
        "[3] CURRENT COMPATIBILITY FAILURES\nNo active static failures detected.\n"
        "[5] CURRENT SCAFFOLD\nVALID != REPAIR TARGET\n"
        "[6] REPAIR TARGET\nWHAT: Fix x\nWHERE: f.ext\nOBSERVED: err\nEXPECTED: ok\n"
        "[7] REPAIR BOUNDARY\nPRESERVE: All models\nALLOWED: Localized fix\n"  # FORBIDDEN missing!
    )
    is_v1, errs1 = validate_architect_repair_context_delivery(partial_boundary)
    assert is_v1 is False
    assert any("FORBIDDEN" in e for e in errs1)

    # Scenario 2: Missing WHERE from target (only 3 of 4 elements present)
    partial_target = (
        "[1] IMMUTABLE ACCEPTANCE AUTHORITY\nAuthority: FROZEN_ORACLE\n"
        "[3] CURRENT COMPATIBILITY FAILURES\nNo active static failures detected.\n"
        "[5] CURRENT SCAFFOLD\nVALID != REPAIR TARGET\n"
        "[6] REPAIR TARGET\nWHAT: Fix x\nOBSERVED: err\nEXPECTED: ok\n"  # WHERE missing!
        "[7] REPAIR BOUNDARY\nPRESERVE: All\nALLOWED: Fix\nFORBIDDEN: Drop\n"
    )
    is_v2, errs2 = validate_architect_repair_context_delivery(partial_target)
    assert is_v2 is False
    assert any("where" in e for e in errs2)


# ===========================================================================
# Property K: Delivery validator inspects final rendered prompt
# ===========================================================================
def test_property_k_delivery_validator_inspects_final_prompt(generic_synthetic_sections):
    full_text = "\n\n".join(generic_synthetic_sections.values())
    is_valid, errs = validate_architect_repair_context_delivery(full_text)
    assert is_valid is True
    assert len(errs) == 0

    truncated = full_text[:1200]
    is_val_trunc, errs_trunc = validate_architect_repair_context_delivery(truncated)
    assert is_val_trunc is False
    assert len(errs_trunc) > 0


# ===========================================================================
# Property L: Configurable Budget (Correction 2: 7,500 is config, not invariant)
# ===========================================================================
def test_property_l_configurable_budget_not_architectural_invariant(generic_synthetic_sections):
    for budget in [4500, 6000, 7500, 10000, 15000]:
        state = {
            "task": "Build generic component",
            "contract_status": "REJECTED",
            "contract_revision_count": 1,
            "context_budget": budget,
            "contract_validation_errors": ["Active failure"],
        }
        ctx, telem = build_architect_repair_context(state)
        assert telem["context_budget"] == budget
        # Invariant: repair-critical semantic info survives final delivery regardless of budget
        assert telem["delivery_valid"] is True
        assert "[6] REPAIR TARGET" in ctx
        assert "[7] REPAIR BOUNDARY" in ctx
        assert "ALLOWED" in ctx
        assert "FORBIDDEN" in ctx


# ===========================================================================
# Property M: AST inspection + Behavioral Multi-Task Generalization (Correction 5)
# ===========================================================================
def test_property_m_behavioral_generalization_across_disjoint_vocabularies():
    # 1. AST Keyword Audit: verify 0 domain solver keywords
    import inspect
    import backend.context_hardening as ch
    import backend.architect_preservation as ap

    src_ch = inspect.getsource(ch.compress_context_semantic_detailed)
    src_ap = inspect.getsource(ap.validate_architect_repair_context_delivery)

    forbidden_terms = [
        "fastapi", "matrix", "metricdata", "card_metric", "flutter",
        "router", "status_code", "statuscode", "test_main"
    ]
    for term in forbidden_terms:
        assert term not in src_ch.lower(), f"Forbidden task-specific keyword '{term}' found in context_hardening!"
        assert term not in src_ap.lower(), f"Forbidden task-specific keyword '{term}' found in architect_preservation!"

    # 2. Behavioral Generalization Test:
    # Task Alpha: Streaming Data Pipeline (Vocabulary: StreamBuffer, PipelineStage, transform_stream, stream_engine.pipeline)
    task_alpha_sections = {
        "sec_01_authority": "[1] IMMUTABLE ACCEPTANCE AUTHORITY\nSymbols: transform_stream, StreamBuffer",
        "sec_03_current_failures": "[3] CURRENT COMPATIBILITY FAILURES\nActive: StreamBuffer buffer_size type mismatch",
        "sec_06_repair_target": (
            "[6] REPAIR TARGET (ATOMIC REPAIR INVARIANT)\n"
            "WHAT: PipelineStage stream buffer parameter\n"
            "WHERE: stream_engine.pipeline\n"
            "OBSERVED: buffer_size expected int, got float\n"
            "EXPECTED: buffer_size: int\n"
        ),
        "sec_07_repair_boundary": (
            "[7] REPAIR BOUNDARY (ATOMIC REPAIR INVARIANT)\n"
            "PRESERVE: StreamBuffer class and transform_stream callable\n"
            "ALLOWED: Correct parameter type annotation\n"
            "FORBIDDEN: Dropping PipelineStage interface or mutating stream contracts\n"
        ),
        "sec_05_current_valid_state": (
            "[5] CURRENT SCAFFOLD & VALIDATED STRUCTURAL STATE\n"
            "Relational Invariant: StreamBuffer -> stream_engine.pipeline -> transform_stream\n"
            "Established File Collection: ['stream_engine.pipeline']\n"
            "Established Interface Contracts: ['transform_stream']\n"
        ),
        "sec_04_locked_proven_state": "[4] LOCKED/PROVEN STATE\nLocked: INV-STREAM-01",
        "sec_08_expected_post_repair": "[8] EXPECTED POST-REPAIR STATE\n0 regressions",
        "sec_02_canonical_schema": "[2] ACCEPTANCE OBLIGATION LEDGER & CANONICAL BLUEPRINT SCHEMA CONSTRAINTS\n" + ("Schema rule\n" * 30),
        "sec_09_relational_blueprint": "[9] IMPLEMENTATION GROUNDING\nUser task: Stream processing\n" + ("Relation details\n" * 20),
        "sec_10_raw_diagnostics": "[10] RAW DIAGNOSTICS\nError: buffer_size mismatch\n" + ("Trace frame\n" * 20),
    }

    # Task Beta: Document Search Index (Vocabulary: InvertedIndex, query_catalog, DocRecord, index_engine.catalog)
    task_beta_sections = {
        "sec_01_authority": "[1] IMMUTABLE ACCEPTANCE AUTHORITY\nSymbols: query_catalog, InvertedIndex",
        "sec_03_current_failures": "[3] CURRENT COMPATIBILITY FAILURES\nActive: InvertedIndex search parameter missing",
        "sec_06_repair_target": (
            "[6] REPAIR TARGET (ATOMIC REPAIR INVARIANT)\n"
            "WHAT: query_catalog search filter signature\n"
            "WHERE: index_engine.catalog\n"
            "OBSERVED: query_catalog() missing filter argument\n"
            "EXPECTED: query_catalog(query: str, filter_tags: list)\n"
        ),
        "sec_07_repair_boundary": (
            "[7] REPAIR BOUNDARY (ATOMIC REPAIR INVARIANT)\n"
            "PRESERVE: InvertedIndex data model and DocRecord schema\n"
            "ALLOWED: Add optional filter_tags parameter\n"
            "FORBIDDEN: Dropping InvertedIndex or deleting index_engine.catalog\n"
        ),
        "sec_05_current_valid_state": (
            "[5] CURRENT SCAFFOLD & VALIDATED STRUCTURAL STATE\n"
            "Relational Invariant: DocRecord -> index_engine.catalog -> query_catalog\n"
            "Established File Collection: ['index_engine.catalog']\n"
            "Established Interface Contracts: ['query_catalog']\n"
        ),
        "sec_04_locked_proven_state": "[4] LOCKED/PROVEN STATE\nLocked: INV-INDEX-01",
        "sec_08_expected_post_repair": "[8] EXPECTED POST-REPAIR STATE\n0 regressions",
        "sec_02_canonical_schema": "[2] ACCEPTANCE OBLIGATION LEDGER & CANONICAL BLUEPRINT SCHEMA CONSTRAINTS\n" + ("Schema rule\n" * 30),
        "sec_09_relational_blueprint": "[9] IMPLEMENTATION GROUNDING\nUser task: Search index catalog\n" + ("Relation details\n" * 20),
        "sec_10_raw_diagnostics": "[10] RAW DIAGNOSTICS\nError: missing argument\n" + ("Trace frame\n" * 20),
    }

    # Run both tasks under identical tight compression budget (5,000 chars)
    comp_alpha, meta_alpha = compress_context_semantic_detailed(task_alpha_sections, max_chars=5000, priority_order=ARCHITECT_REPAIR_PRIORITY_ORDER)
    comp_beta, meta_beta = compress_context_semantic_detailed(task_beta_sections, max_chars=5000, priority_order=ARCHITECT_REPAIR_PRIORITY_ORDER)

    val_alpha_ok, errs_alpha = validate_architect_repair_context_delivery(comp_alpha)
    val_beta_ok, errs_beta = validate_architect_repair_context_delivery(comp_beta)

    # Both must cleanly pass delivery validation with identical generic preservation
    assert val_alpha_ok is True, f"Task Alpha failed generic delivery validation: {errs_alpha}"
    assert val_beta_ok is True, f"Task Beta failed generic delivery validation: {errs_beta}"
    assert "StreamBuffer" in comp_alpha
    assert "InvertedIndex" in comp_beta


# ===========================================================================
# Property N: Non-repair context assembly remains valid and unaffected
# ===========================================================================
def test_property_n_non_repair_context_assembly_unaffected():
    turn0_state = {
        "task": "Build generic utility microservice",
        "specifications": "Provide public computation endpoints.",
        "contract_revision_count": 0,
        "contract_status": "DRAFT",
    }
    ctx, telem = build_architect_decision_context(turn0_state)
    assert "[1] USER INTENT" in ctx
    assert "Build generic utility microservice" in ctx
    assert len(ctx) > 0


# ===========================================================================
# Property O: Structured DELIVERY_FAILURE (Correction 1: No ValueError, No Repair Turn Consumed)
# ===========================================================================
def test_property_o_structured_delivery_failure_consumes_no_repair_turn(monkeypatch):
    """
    Verifies that when context delivery validation fails:
    1. architect_agent returns structured status="DELIVERY_FAILURE"
    2. No LLM invocation occurs
    3. contract_revision_count / repair turn is NOT incremented
    4. architect_validator_node halts to END without consuming repair count
    """
    # Defective state where prompt context delivery validation will fail
    broken_repair_state = {
        "task": "Build generic utility",
        "target_language": "python",
        "contract_status": "REJECTED",
        "contract_revision_count": 1,
        "contract_validation_errors": ["Some static failure"],
        "context_budget": 500,  # Impossibly small budget to trigger delivery failure
        "logs": []
    }

    # Execute architect_agent directly
    # MUST NOT raise ValueError! Must return structured dictionary.
    res = architect_agent(broken_repair_state)

    assert isinstance(res, dict)
    assert res["status"] == "DELIVERY_FAILURE"
    assert res["contract_status"] == "DELIVERY_FAILURE"
    assert res["delivery_valid"] is False
    assert len(res["delivery_errors"]) > 0
    # Blueprint revision count must not be incremented
    assert res["blueprint_revision_count"] == 0

    # Pass the result into architect_validator_node
    val_res = architect_validator_node(res)
    assert val_res["status"] == "DELIVERY_FAILURE"
    # Repair count must NOT be incremented
    assert "contract_revision_count" not in val_res or val_res.get("contract_revision_count") == 1

    # Route decision must be END
    route_decision = route_after_architect_validator(val_res)
    assert route_decision == "end" or route_decision == "__end__"
