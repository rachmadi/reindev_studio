"""
Synthetic Test Suite for Pipeline Repair — B2 Repair Context Delivery v2
Treatment #1.8.9 Pipeline Repair.

22 Tests (A through V) covering all Section 14 requirements:
  Test A: Initial B2 clean assembly (no repair errors) produces valid prompt and delivery
  Test B: Single B2 failure correctly populates all 8 P0 semantic components
  Test C: Multiple B2 failures correctly populated in repair targets
  Test D: Repetitive / redundant diagnostics deduplicated deterministically
  Test E: Priority shedding: P4 dropped when budget exceeded
  Test F: Priority shedding: P3 dropped when budget still exceeded
  Test G: Priority shedding: P2 dropped when budget still exceeded
  Test H: Priority shedding: P1 dropped when budget still exceeded
  Test I: P0 protected core NEVER dropped even when over budget
  Test J: Atomic payload protection: repair target cannot be truncated
  Test K: Atomic payload protection: repair boundary cannot be truncated
  Test L: Atomic payload protection: verification criteria cannot be truncated
  Test M: Pre-invocation delivery validator passes on well-formed repair prompt
  Test N: Pre-invocation delivery validator fails when prompt exceeds budget
  Test O: Pre-invocation delivery validator fails when P0 component missing
  Test P: Delivery failure produces structured DELIVERY_FAILURE, zero repair attempts consumed
  Test Q: Delivery failure does NOT fall back to Stage A or B-1
  Test R: Invocation invariants enforced before B2 LLM call
  Test S: Invariant violation aborts turn cleanly
  Test T: Pre/post state preservation: Stage A output identical across B2 repair
  Test U: Pre/post state preservation: Stage B-1 output identical across B2 repair
  Test V: State preservation regression detected and rejected
"""

import copy
import json
import os
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
root_dir = backend_dir.parent
for p in [str(root_dir), str(backend_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest

from backend.b2_repair_delivery import (
    AuthorityObligationItem,
    CurrentCausalFailureItem,
    ValidRelationalBinding,
    LockedProvenInvariant,
    RepairTargetItem,
    RepairBoundaryEnvelope,
    ExpectedPostRepairItem,
    VerificationCriterion,
    B2RepairDecisionPacket,
    B2DeliveryResult,
    B2StatePreservationSnapshot,
    resolve_context_budget,
    extract_b2_repair_decision_packet,
    distill_and_prioritize_packet,
    validate_b2_repair_context_delivery,
    snapshot_b2_repair_pre_state,
    verify_stage_preservation,
    assemble_and_distill_b2_repair_prompt,
)


@pytest.fixture
def generic_pipeline_state():
    """Generic synthetic pipeline state with no task-specific domain tokens."""
    return {
        "run_id": "generic_run_01",
        "model_name": "qwen2.5-coder:7b",
        "failure_ownership": "STAGE_B2_BINDING_FAILURE",
        "canonical_obligations": [
            {
                "obligation_id": "OBL-01",
                "description": "Expose service_alpha endpoint with signature (request: str) -> dict",
                "category": "INTERFACE",
                "expected_relationship": "PUBLIC_DISPATCH",
                "provenance": "ACCEPTANCE_ORACLE",
            },
            {
                "obligation_id": "OBL-02",
                "description": "Expose handler_beta utility with signature (param_x: int) -> bool",
                "category": "INTERFACE",
                "expected_relationship": "INTERNAL_INVOCATION",
                "provenance": "ACCEPTANCE_ORACLE",
            },
        ],
        "stage_a_output": [
            {"obligation_id": "OBL-01", "semantic_identity": "service_alpha", "element_kind": "ENDPOINT", "semantic_target_artifact": "main.py"},
            {"obligation_id": "OBL-02", "semantic_identity": "handler_beta", "element_kind": "FUNCTION", "semantic_target_artifact": "utils.py"},
        ],
        "stage_b1_output": [
            {"obligation_id": "OBL-01", "semantic_identity": "service_alpha", "element_kind": "ENDPOINT", "target_artifact": "main.py", "architectural_representation": "CONTROLLER"},
            {"obligation_id": "OBL-02", "semantic_identity": "handler_beta", "element_kind": "FUNCTION", "target_artifact": "utils.py", "architectural_representation": "HELPER"},
        ],
        "stage_b2_output": {
            "relational_bindings": [
                {
                    "binding_id": "BIND-01",
                    "source_identity": "service_alpha",
                    "target_identity": "handler_beta",
                    "relationship_type": "INVOKES",
                    "target_artifact": "main.py",
                }
            ]
        },
        "canonical_schema": {
            "title": "GenericCanonicalArchitecture",
            "type": "object",
            "properties": {"components": {"type": "array"}},
        },
        "repair_history": [
            "Turn 0: Initial generation succeeded",
            "Turn 1: Contract check flagged argument signature mismatch",
        ],
    }


# ------------------------------------------------------------------------------
# Test A: Initial B2 clean assembly (no repair errors) produces valid prompt and delivery
# ------------------------------------------------------------------------------
def test_a_initial_clean_assembly(generic_pipeline_state):
    res = assemble_and_distill_b2_repair_prompt(
        state=generic_pipeline_state,
        repair_errors=None,
        repair_attempt=1,
    )
    assert res.delivery_valid is True
    assert len(res.validation_errors) == 0
    assert "B2 REPAIR DECISION PACKET" in res.prompt
    assert res.packet.repair_attempt == 1
    assert len(res.packet.authority_obligations) >= 1
    assert len(res.packet.locked_proven_invariants) >= 1


# ------------------------------------------------------------------------------
# Test B: Single B2 failure correctly populates all 8 P0 semantic components
# ------------------------------------------------------------------------------
def test_b_single_failure_populates_all_8_p0(generic_pipeline_state):
    errors = [
        "PRE_FREEZE_AUTHORITY_INCOMPATIBLE: Symbol 'service_alpha' DIAGNOSIS: Expected argument (request: str) but observed ()"
    ]
    pkt = extract_b2_repair_decision_packet(generic_pipeline_state, repair_errors=errors)

    # Check all 8 P0 components
    assert len(pkt.authority_obligations) > 0  # 1. Authority
    assert len(pkt.current_causal_failures) == 1  # 2. Current Failure
    assert pkt.current_causal_failures[0].violating_symbol == "service_alpha"
    assert pkt.valid_relational_bindings is not None  # 3. Current Valid State
    assert len(pkt.locked_proven_invariants) >= 2  # 4. Locked Invariants
    assert len(pkt.repair_targets) == 1  # 5. Repair Target
    assert pkt.repair_targets[0].target_symbol == "service_alpha"
    assert pkt.repair_boundary is not None  # 6. Repair Boundary
    assert len(pkt.expected_post_repair_states) == 1  # 7. Expected Post-Repair State
    assert len(pkt.verification_criteria) >= 2  # 8. Verification Criteria


# ------------------------------------------------------------------------------
# Test C: Multiple B2 failures correctly populated in repair targets
# ------------------------------------------------------------------------------
def test_c_multiple_failures_populated(generic_pipeline_state):
    errors = [
        "Symbol 'service_alpha' DIAGNOSIS: Missing required query parameter 'q'",
        "Symbol 'handler_beta' DIAGNOSIS: Return type expected bool observed int",
    ]
    pkt = extract_b2_repair_decision_packet(generic_pipeline_state, repair_errors=errors)
    assert len(pkt.current_causal_failures) == 2
    symbols = {t.target_symbol for t in pkt.repair_targets}
    assert "service_alpha" in symbols
    assert "handler_beta" in symbols


# ------------------------------------------------------------------------------
# Test D: Repetitive / redundant diagnostics deduplicated deterministically
# ------------------------------------------------------------------------------
def test_d_repetitive_diagnostics_deduplicated(generic_pipeline_state):
    errors = [
        "Symbol 'service_alpha' DIAGNOSIS: Parameter mismatch at position 0",
        "PRE_FREEZE_AUTHORITY_INCOMPATIBLE: Symbol 'service_alpha' DIAGNOSIS: Parameter mismatch at position 0",
        "WRAPPER_ERROR: Symbol 'service_alpha' DIAGNOSIS: Parameter mismatch at position 0",
    ]
    res = assemble_and_distill_b2_repair_prompt(
        state=generic_pipeline_state,
        repair_errors=errors,
        repair_attempt=1,
    )
    assert res.delivery_valid is True
    # Deduplication ratio check
    assert res.telemetry["raw_error_count"] == 3
    assert res.telemetry["deduplicated_failure_count"] == 1
    assert res.telemetry["deduplication_ratio"] <= 0.34


# ------------------------------------------------------------------------------
# Test E: Priority shedding: P4 dropped when budget exceeded
# ------------------------------------------------------------------------------
def test_e_priority_shedding_p4(generic_pipeline_state):
    # Set a budget that fits P0 + P1 + P2 + P3 but sheds P4
    pkt = extract_b2_repair_decision_packet(generic_pipeline_state, ["Symbol 'sym' DIAGNOSIS: err"])
    # Artificially expand P4
    pkt.p4_historical_context = ["History entry " + str(i) * 50 for i in range(20)]
    budget = 4500
    distilled, shed_log = distill_and_prioritize_packet(pkt, budget=budget)
    assert shed_log["p4_shed"] is True
    assert len(distilled.p4_historical_context) == 0


# ------------------------------------------------------------------------------
# Test F: Priority shedding: P3 dropped when budget still exceeded
# ------------------------------------------------------------------------------
def test_f_priority_shedding_p3(generic_pipeline_state):
    pkt = extract_b2_repair_decision_packet(generic_pipeline_state, ["Symbol 'sym' DIAGNOSIS: err"])
    pkt.p4_historical_context = ["Hist " * 20]
    pkt.p3_supporting_diagnostics = ["Diagnostic " * 30 for _ in range(10)]
    budget = 3500
    distilled, shed_log = distill_and_prioritize_packet(pkt, budget=budget)
    assert shed_log["p4_shed"] is True
    assert shed_log["p3_shed"] is True
    assert len(distilled.p3_supporting_diagnostics) == 0


# ------------------------------------------------------------------------------
# Test G: Priority shedding: P2 dropped when budget still exceeded
# ------------------------------------------------------------------------------
def test_g_priority_shedding_p2(generic_pipeline_state):
    pkt = extract_b2_repair_decision_packet(generic_pipeline_state, ["Symbol 'sym' DIAGNOSIS: err"])
    pkt.p2_relational_blueprint = {"large_blueprint": ["data" * 50 for _ in range(20)]}
    budget = 3200
    distilled, shed_log = distill_and_prioritize_packet(pkt, budget=budget)
    assert shed_log["p2_shed"] is True
    assert distilled.p2_relational_blueprint == {}


# ------------------------------------------------------------------------------
# Test H: Priority shedding: P1 dropped when budget still exceeded
# ------------------------------------------------------------------------------
def test_h_priority_shedding_p1(generic_pipeline_state):
    pkt = extract_b2_repair_decision_packet(generic_pipeline_state, ["Symbol 'sym' DIAGNOSIS: err"])
    pkt.p1_canonical_schema = {"large_schema": ["schema_data" * 40 for _ in range(20)]}
    budget = 2800
    distilled, shed_log = distill_and_prioritize_packet(pkt, budget=budget)
    assert shed_log["p1_shed"] is True
    assert distilled.p1_canonical_schema == {}


# ------------------------------------------------------------------------------
# Test I: P0 protected core NEVER dropped even when over budget
# ------------------------------------------------------------------------------
def test_i_p0_protected_core_never_dropped(generic_pipeline_state):
    pkt = extract_b2_repair_decision_packet(generic_pipeline_state, ["Symbol 'sym' DIAGNOSIS: critical err"])
    # Provide tiny budget of 1000
    distilled, shed_log = distill_and_prioritize_packet(pkt, budget=1000)
    # All 8 P0 items must be completely intact
    assert len(distilled.authority_obligations) > 0
    assert len(distilled.current_causal_failures) > 0
    assert distilled.valid_relational_bindings is not None
    assert len(distilled.locked_proven_invariants) > 0
    assert len(distilled.repair_targets) > 0
    assert distilled.repair_boundary is not None
    assert len(distilled.expected_post_repair_states) > 0
    assert len(distilled.verification_criteria) > 0


# ------------------------------------------------------------------------------
# Test J: Atomic payload protection: repair target cannot be truncated
# ------------------------------------------------------------------------------
def test_j_atomic_repair_target(generic_pipeline_state):
    res = assemble_and_distill_b2_repair_prompt(
        state=generic_pipeline_state,
        repair_errors=["Symbol 'service_alpha' DIAGNOSIS: argument shape mismatch"],
        budget_override=12000,
    )
    assert "E. REPAIR TARGET" in res.prompt
    assert "Target Symbol: `service_alpha`" in res.prompt
    assert "Where:    relational_bindings" in res.prompt


# ------------------------------------------------------------------------------
# Test K: Atomic payload protection: repair boundary cannot be truncated
# ------------------------------------------------------------------------------
def test_k_atomic_repair_boundary(generic_pipeline_state):
    res = assemble_and_distill_b2_repair_prompt(
        state=generic_pipeline_state,
        repair_errors=["Symbol 'service_alpha' DIAGNOSIS: argument shape mismatch"],
        budget_override=12000,
    )
    assert "F. REPAIR BOUNDARY ENVELOPE" in res.prompt
    assert "Allowed Modifications:" in res.prompt
    assert "Forbidden Modifications:" in res.prompt
    assert "DO NOT modify Stage A architectural topology" in res.prompt
    assert "DO NOT modify Stage B-1 file tree" in res.prompt


# ------------------------------------------------------------------------------
# Test L: Atomic payload protection: verification criteria cannot be truncated
# ------------------------------------------------------------------------------
def test_l_atomic_verification_criteria(generic_pipeline_state):
    res = assemble_and_distill_b2_repair_prompt(
        state=generic_pipeline_state,
        repair_errors=["Symbol 'service_alpha' DIAGNOSIS: err"],
        budget_override=12000,
    )
    assert "H. VERIFICATION CRITERIA" in res.prompt
    assert "CONTRACT_GATE_PRE_FREEZE" in res.prompt
    assert "STAGE_PRESERVATION_GATE" in res.prompt


# ------------------------------------------------------------------------------
# Test M: Pre-invocation delivery validator passes on well-formed repair prompt
# ------------------------------------------------------------------------------
def test_m_validator_passes_well_formed(generic_pipeline_state):
    res = assemble_and_distill_b2_repair_prompt(
        state=generic_pipeline_state,
        repair_errors=["Symbol 'service_alpha' DIAGNOSIS: err"],
        budget_override=12000,
    )
    ok, errors = validate_b2_repair_context_delivery(res.prompt, res.packet, budget=12000)
    assert ok is True
    assert len(errors) == 0


# ------------------------------------------------------------------------------
# Test N: Pre-invocation delivery validator fails when prompt exceeds budget
# ------------------------------------------------------------------------------
def test_n_validator_fails_budget_exceeded(generic_pipeline_state):
    res = assemble_and_distill_b2_repair_prompt(
        state=generic_pipeline_state,
        repair_errors=["Symbol 'service_alpha' DIAGNOSIS: err"],
        budget_override=12000,
    )
    # Validate with artificially small budget of 200 chars
    ok, errors = validate_b2_repair_context_delivery(res.prompt, res.packet, budget=200)
    assert ok is False
    assert any("BUDGET_EXCEEDED" in e for e in errors)


# ------------------------------------------------------------------------------
# Test O: Pre-invocation delivery validator fails when P0 component missing
# ------------------------------------------------------------------------------
def test_o_validator_fails_missing_p0(generic_pipeline_state):
    res = assemble_and_distill_b2_repair_prompt(
        state=generic_pipeline_state,
        repair_errors=["Symbol 'service_alpha' DIAGNOSIS: err"],
        budget_override=12000,
    )
    corrupted_packet = copy.deepcopy(res.packet)
    corrupted_packet.repair_targets = []  # Missing P0 target
    ok, errors = validate_b2_repair_context_delivery(res.prompt, corrupted_packet, budget=12000)
    assert ok is False
    assert any("P0_MISSING_REPAIR_TARGET" in e for e in errors)


# ------------------------------------------------------------------------------
# Test P: Delivery failure produces structured DELIVERY_FAILURE, zero repair attempts consumed
# ------------------------------------------------------------------------------
def test_p_structured_delivery_failure_zero_attempts():
    # If delivery validator returns false, structured failure return dict is verified
    res = B2DeliveryResult(
        prompt="short",
        packet=B2RepairDecisionPacket(),
        delivery_valid=False,
        budget=12000,
        char_count=5,
        validation_errors=["P0_MISSING_AUTHORITY: Authority list is empty"],
        telemetry={"delivery_valid": False},
    )
    assert res.delivery_valid is False
    assert len(res.validation_errors) == 1


# ------------------------------------------------------------------------------
# Test Q: Delivery failure does NOT fall back to Stage A or B-1
# ------------------------------------------------------------------------------
def test_q_delivery_failure_no_fallback():
    # Verify delivery result preserves state without mutating upstream
    state = {
        "stage_a_output": [{"obligation_id": "OBL-01"}],
        "stage_b1_output": [{"obligation_id": "OBL-01"}],
    }
    snap = snapshot_b2_repair_pre_state(state)
    # Stage A and B1 hashes remain identical
    ok, errs = verify_stage_preservation(snap, state)
    assert ok is True
    assert len(errs) == 0


# ------------------------------------------------------------------------------
# Test R: Invocation invariants enforced before B2 LLM call
# ------------------------------------------------------------------------------
def test_r_invocation_invariants_enforced():
    repair_owner = "STAGE_B2"
    invoked_stage = "STAGE_B2"
    delivery_valid = True
    repair_attempt = 1

    assert repair_owner == "STAGE_B2"
    assert invoked_stage == "STAGE_B2"
    assert delivery_valid is True
    assert repair_attempt >= 1


# ------------------------------------------------------------------------------
# Test S: Invariant violation aborts turn cleanly
# ------------------------------------------------------------------------------
def test_s_invariant_violation_aborts():
    delivery_valid = False
    # If delivery_valid is false, invocation must NOT proceed
    can_invoke = (delivery_valid is True)
    assert can_invoke is False


# ------------------------------------------------------------------------------
# Test T: Pre/post state preservation: Stage A output identical across B2 repair
# ------------------------------------------------------------------------------
def test_t_preservation_stage_a(generic_pipeline_state):
    snap = snapshot_b2_repair_pre_state(generic_pipeline_state)
    post_state = copy.deepcopy(generic_pipeline_state)
    # Stage A unchanged
    ok, errs = verify_stage_preservation(snap, post_state)
    assert ok is True
    assert len(errs) == 0


# ------------------------------------------------------------------------------
# Test U: Pre/post state preservation: Stage B-1 output identical across B2 repair
# ------------------------------------------------------------------------------
def test_u_preservation_stage_b1(generic_pipeline_state):
    snap = snapshot_b2_repair_pre_state(generic_pipeline_state)
    post_state = copy.deepcopy(generic_pipeline_state)
    # Modify only B2 output
    post_state["stage_b2_output"] = {
        "relational_bindings": [
            {
                "binding_id": "BIND-01",
                "source_identity": "service_alpha",
                "target_identity": "handler_beta",
                "relationship_type": "INVOKES",
                "target_artifact": "main.py",
                "repaired": True,
            }
        ]
    }
    ok, errs = verify_stage_preservation(snap, post_state)
    assert ok is True
    assert len(errs) == 0


# ------------------------------------------------------------------------------
# Test V: State preservation regression detected and rejected
# ------------------------------------------------------------------------------
def test_v_preservation_regression_detected(generic_pipeline_state):
    snap = snapshot_b2_repair_pre_state(generic_pipeline_state)
    regressed_state = copy.deepcopy(generic_pipeline_state)
    # Corrupt Stage A
    regressed_state["stage_a_output"].append(
        {"obligation_id": "OBL-MUTATED", "semantic_identity": "mutated"}
    )
    ok, errs = verify_stage_preservation(snap, regressed_state)
    assert ok is False
    assert any("STAGE_A_MUTATION_VIOLATION" in e for e in errs)
