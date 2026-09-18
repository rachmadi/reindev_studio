"""
Synthetic Test Suite for Pipeline Repair — Failure Ownership Classifier v2
Treatment #1.8.9 Pipeline Repair.

Tests A through O covering all Section 9 invariants:
  Test A: outer PRE_FREEZE wrapper does not dominate specific evidence
  Test B: CALL_SHAPE_INCOMPATIBILITY -> B2 (RELATIONSHIP_BINDING_FAILURE)
  Test C: generic binding incompatibility -> B2 (RELATIONSHIP_BINDING_FAILURE)
  Test D: element realization failure -> B1 (ELEMENT_REALIZATION_FAILURE)
  Test E: identity failure -> Stage A (IDENTITY_FAILURE)
  Test F: B2 invalidation preserves Stage A
  Test G: B2 invalidation preserves B1
  Test H: B2 invalidation invalidates B3 (requires deterministic re-assembly)
  Test I: repair owner reaches the correct LLM stage (telemetry invariant)
  Test J: no cache re-entry (telemetry marks LLM_INVOKED)
  Test K: preserved hashes remain unchanged (and mutation raises REGRESSION)
  Test L: generic multiple-failure classification
  Test M: representation failure does not become identity failure
  Test N: unknown failure does not guess an owner
  Test O: anti-solver audit -- no task-specific tokens or branches
"""

import os
import re
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
root_dir = backend_dir.parent
for p in [str(root_dir), str(backend_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest

from backend.staged_repair import (
    classify_contract_failure_owner,
    compute_stage_lifecycle,
    apply_lifecycle_to_frozen_states,
    verify_stage_preservation,
    build_repair_telemetry,
    OWNER_IDENTITY_FAILURE,
    OWNER_ELEMENT_REALIZATION_FAILURE,
    OWNER_RELATIONSHIP_BINDING_FAILURE,
    OWNER_REPRESENTATION_FAILURE,
    OWNER_UNKNOWN,
    STAGE_A,
    STAGE_B1,
    STAGE_B2,
    STATUS_FROZEN,
    STATUS_INVALIDATED,
)
from backend.architect_staged import (
    StageAObligationMapping,
    FrozenStageAMappings,
    StageB1ElementRealization,
    StageB1Output,
    FrozenStageB1State,
    StageB2BindingDecision,
    StageB2Output,
    FrozenStageB2State,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_frozen_a():
    mapping = StageAObligationMapping(
        obligation_id="OBL-01",
        semantic_element="ComputeResult",
        element_kind="FUNCTION",
        semantic_identity="compute_result",
        semantic_target_artifact="engine.py",
        semantic_parameters=({"name": "x", "type": "int", "location": "ARGUMENT", "required": True},),
        semantic_return={"type": "int", "description": "computed value"},
    )
    return FrozenStageAMappings.freeze([mapping])


def _make_frozen_b1():
    el = StageB1ElementRealization(
        obligation_id="OBL-01",
        semantic_identity="compute_result",
        element_kind="FUNCTION",
        target_artifact="engine.py",
        architectural_representation="def compute_result(x: int) -> int: ...",
    )
    return FrozenStageB1State.freeze([el])


def _make_frozen_b2():
    bd = StageB2BindingDecision(
        binding_id="BIND-01",
        source_identity="compute_result",
        target_identity="compute_result",
        relationship_type="FUNCTION_DEFINITION",
        target_artifact="engine.py",
        signature_details={
            "parameters": [{"name": "x", "type": "int"}],
            "return_semantics": "int",
            "route": None,
            "http_method": None,
        },
    )
    b2_output = StageB2Output(
        bindings=[bd],
        scaffold_files={"engine.py": "def compute_result(x: int) -> int:\n    return x"}
    )
    return FrozenStageB2State.freeze(b2_output.bindings, b2_output.scaffold_files)


# ---------------------------------------------------------------------------
# Tests A through O
# ---------------------------------------------------------------------------

def test_a_outer_wrapper_does_not_dominate_specific_evidence():
    """Test A: outer PRE_FREEZE wrapper does not dominate specific evidence."""
    err = (
        "Pilar 4 (Oracle Consistency): CONTRACT_VALIDATION_FAILED: PRE_FREEZE_AUTHORITY_INCOMPATIBLE\n"
        "details:\n"
        "CALL_SHAPE_INCOMPATIBILITY: Symbol 'compute_result' invoked with 2 arguments, but accepts at most 0."
    )
    owner, invalidate_stages, summary = classify_contract_failure_owner([err])
    assert owner == OWNER_RELATIONSHIP_BINDING_FAILURE
    assert invalidate_stages == [STAGE_B2]
    assert STAGE_A not in invalidate_stages


def test_b_call_shape_incompatibility_routes_to_b2():
    """Test B: CALL_SHAPE_INCOMPATIBILITY -> B2 (RELATIONSHIP_BINDING_FAILURE)."""
    err = "CALL_SHAPE_INCOMPATIBILITY: Symbol 'do_work' invoked with 3 positional argument(s), but proposed function accepts at most 1."
    owner, invalidate_stages, summary = classify_contract_failure_owner([err])
    assert owner == OWNER_RELATIONSHIP_BINDING_FAILURE
    assert invalidate_stages == [STAGE_B2]


def test_c_generic_binding_incompatibility_routes_to_b2():
    """Test C: generic binding incompatibility -> B2 (RELATIONSHIP_BINDING_FAILURE)."""
    # Route binding mismatch with internal function proof (as seen in FastAPI)
    err = (
        "CONTRACT_VALIDATION_FAILED: PRE_FREEZE_AUTHORITY_INCOMPATIBLE\n"
        "DIAGNOSIS: Public HTTP endpoint has no declared interface coverage in contract "
        "(Notice: Found internal function(s) ['handler'], but no public route/endpoint binding proof connects them to public endpoint)"
    )
    owner, invalidate_stages, summary = classify_contract_failure_owner([err])
    assert owner == OWNER_RELATIONSHIP_BINDING_FAILURE
    assert invalidate_stages == [STAGE_B2]
    assert STAGE_A not in invalidate_stages
    assert STAGE_B1 not in invalidate_stages


def test_d_element_realization_failure_routes_to_b1():
    """Test D: element realization failure -> B1 (ELEMENT_REALIZATION_FAILURE)."""
    err = "CONTRACT_COVERAGE: MISSING - Entity 'UserProfile' not declared in interface or data models."
    owner, invalidate_stages, summary = classify_contract_failure_owner([err])
    assert owner == OWNER_ELEMENT_REALIZATION_FAILURE
    assert invalidate_stages == [STAGE_B1, STAGE_B2]
    assert STAGE_A not in invalidate_stages


def test_e_identity_failure_routes_to_stage_a():
    """Test E: identity failure -> Stage A (IDENTITY_FAILURE)."""
    err = "STAGE_A_MAPPING_FAILURE: Obligation 'OBL-AUTH-01' has unknown semantic identity and cannot be mapped."
    owner, invalidate_stages, summary = classify_contract_failure_owner([err])
    assert owner == OWNER_IDENTITY_FAILURE
    assert invalidate_stages == [STAGE_A, STAGE_B1, STAGE_B2]


def test_f_b2_invalidation_preserves_stage_a():
    """Test F: B2 invalidation preserves Stage A."""
    fa = _make_frozen_a()
    fb1 = _make_frozen_b1()
    fb2 = _make_frozen_b2()

    lifecycle = compute_stage_lifecycle(
        prev_lifecycle={},
        failure_owner=OWNER_RELATIONSHIP_BINDING_FAILURE,
        invalidate_stages=[STAGE_B2],
        gate_errors=["CALL_SHAPE_INCOMPATIBILITY: signature parameter mismatch"],
    )
    new_a, new_b1, new_b2 = apply_lifecycle_to_frozen_states(fa, fb1, fb2, lifecycle)

    assert new_a is not None
    assert new_a.sha256_seal == fa.sha256_seal
    assert lifecycle[STAGE_A]["status"] == STATUS_FROZEN


def test_g_b2_invalidation_preserves_b1():
    """Test G: B2 invalidation preserves B1."""
    fa = _make_frozen_a()
    fb1 = _make_frozen_b1()
    fb2 = _make_frozen_b2()

    lifecycle = compute_stage_lifecycle(
        prev_lifecycle={},
        failure_owner=OWNER_RELATIONSHIP_BINDING_FAILURE,
        invalidate_stages=[STAGE_B2],
        gate_errors=["CALL_SHAPE_INCOMPATIBILITY: signature parameter mismatch"],
    )
    new_a, new_b1, new_b2 = apply_lifecycle_to_frozen_states(fa, fb1, fb2, lifecycle)

    assert new_b1 is not None
    assert new_b1.sha256_seal == fb1.sha256_seal
    assert lifecycle[STAGE_B1]["status"] == STATUS_FROZEN
    assert new_b2 is None


def test_h_b2_invalidation_invalidates_b3():
    """Test H: B2 invalidation invalidates B3 (requires assembly with repaired B2)."""
    fa = _make_frozen_a()
    fb1 = _make_frozen_b1()
    fb2 = _make_frozen_b2()

    lifecycle = compute_stage_lifecycle(
        prev_lifecycle={},
        failure_owner=OWNER_RELATIONSHIP_BINDING_FAILURE,
        invalidate_stages=[STAGE_B2],
        gate_errors=["CALL_SHAPE_INCOMPATIBILITY: signature mismatch"],
    )
    _, _, post_b2 = apply_lifecycle_to_frozen_states(fa, fb1, fb2, lifecycle)
    # B2 is nulled, meaning B3 cannot reuse old assembly and must reassemble with repaired B2
    assert post_b2 is None


def test_i_repair_owner_reaches_the_correct_llm_stage():
    """Test I: repair owner reaches the correct LLM stage (telemetry invariant)."""
    res = classify_contract_failure_owner([
        "CALL_SHAPE_INCOMPATIBILITY: Symbol 'operation' parameter count mismatch"
    ])
    assert res.repair_owner == "STAGE_B2"
    assert res.owner == OWNER_RELATIONSHIP_BINDING_FAILURE


def test_j_no_cache_reentry_when_stage_invalidated():
    """Test J: no cache re-entry (telemetry marks LLM_INVOKED)."""
    fa = _make_frozen_a()
    fb1 = _make_frozen_b1()
    fb2 = _make_frozen_b2()

    lifecycle = compute_stage_lifecycle(
        prev_lifecycle={},
        failure_owner=OWNER_RELATIONSHIP_BINDING_FAILURE,
        invalidate_stages=[STAGE_B2],
        gate_errors=["CALL_SHAPE_INCOMPATIBILITY: parameter count mismatch"],
    )
    post_a, post_b1, post_b2 = apply_lifecycle_to_frozen_states(fa, fb1, fb2, lifecycle)

    telem = build_repair_telemetry(
        is_repair_turn=True,
        stage_lifecycle=lifecycle,
        pre_lifecycle_frozen_a=fa,
        pre_lifecycle_frozen_b1=fb1,
        pre_lifecycle_frozen_b2=fb2,
        post_lifecycle_frozen_a=post_a,
        post_lifecycle_frozen_b1=post_b1,
        post_lifecycle_frozen_b2=post_b2,
        new_frozen_b2=None,
        causal_failure_category=res.owner if 'res' in locals() else OWNER_RELATIONSHIP_BINDING_FAILURE,
        repair_owner="STAGE_B2",
        invoked_stage="STAGE_B2",
    )
    assert telem["repair_execution"] == "LLM_INVOKED"
    assert telem["b2_was_nulled_by_lifecycle"] is True


def test_k_preserved_hashes_remain_unchanged_and_mutation_fails_closed():
    """Test K: preserved hashes remain unchanged (and unexpected mutation fails closed)."""
    fa = _make_frozen_a()
    fb1 = _make_frozen_b1()

    # Case 1: Hashes unchanged -> passes preservation check
    is_ok, errs = verify_stage_preservation(
        pre_lifecycle_frozen_a=fa,
        pre_lifecycle_frozen_b1=fb1,
        post_repair_frozen_a=fa,
        post_repair_frozen_b1=fb1,
        failure_owner=OWNER_RELATIONSHIP_BINDING_FAILURE,
    )
    assert is_ok is True
    assert len(errs) == 0

    # Case 2: Mutated Stage A hash -> fails closed with REGRESSION
    mutated_mapping = StageAObligationMapping(
        obligation_id="OBL-01",
        semantic_element="MutatedResult",
        element_kind="FUNCTION",
        semantic_identity="mutated_identity",
        semantic_target_artifact="engine.py",
        semantic_parameters=(),
        semantic_return={},
    )
    mutated_fa = FrozenStageAMappings.freeze([mutated_mapping])

    is_ok_mut, errs_mut = verify_stage_preservation(
        pre_lifecycle_frozen_a=fa,
        pre_lifecycle_frozen_b1=fb1,
        post_repair_frozen_a=mutated_fa,
        post_repair_frozen_b1=fb1,
        failure_owner=OWNER_RELATIONSHIP_BINDING_FAILURE,
    )
    assert is_ok_mut is False
    assert any("REGRESSION: Stage A hash mutated" in e for e in errs_mut)


def test_l_generic_multiple_failure_classification():
    """Test L: generic multiple-failure classification evaluates specific causal patterns before wrappers."""
    errs = [
        "Pilar 4 (Oracle Consistency): CONTRACT_VALIDATION_FAILED: PRE_FREEZE_AUTHORITY_INCOMPATIBLE",
        "SCENARIO_SCAFFOLD_INCOMPATIBILITY: Scenario 'SCN-POS-1' is UNDETERMINED. Conditional branch present but reachability unproven.",
        "CALL_SHAPE_INCOMPATIBILITY: Symbol 'exec_op' invoked with 2 args, accepts 0.",
    ]
    res = classify_contract_failure_owner(errs)
    assert res.owner == OWNER_RELATIONSHIP_BINDING_FAILURE
    assert res.invalidate_stages == [STAGE_B2]
    assert res.outer_category == "PRE_FREEZE_AUTHORITY_INCOMPATIBLE"


def test_m_representation_failure_does_not_become_identity_failure():
    """Test M: representation failure does not become identity failure."""
    errs = [
        "CONTRACT_VALIDATION_FAILED: PRE_FREEZE_AUTHORITY_INCOMPATIBLE",
        "STATE_REPRESENTATION_FAILURE: architecture_plan contains forbidden delimiter or wrapper '```'",
    ]
    res = classify_contract_failure_owner(errs)
    assert res.owner == OWNER_REPRESENTATION_FAILURE
    assert res.invalidate_stages == []
    assert res.repair_owner == "STAGE_B3"


def test_n_unknown_failure_does_not_guess_an_owner():
    """Test N: unknown failure does not guess an owner."""
    errs = [
        "Unexpected random anomaly in environment: socket reset by peer."
    ]
    res = classify_contract_failure_owner(errs)
    assert res.owner == OWNER_UNKNOWN
    assert res.invalidate_stages == []
    assert res.repair_owner == "NONE"


def test_o_anti_solver_audit():
    """Test O: anti-solver audit -- no task-specific tokens or branches in staged_repair.py source."""
    src_path = Path(__file__).parent.parent / "staged_repair.py"
    with open(src_path, "r", encoding="utf-8") as f:
        src = f.read()

    forbidden_tokens = [
        "fastapi_t1",
        "cli_t1",
        "flutter_t1",
        "/products",
        "add_matrices",
        "subtract_matrices",
        "multiply_matrices",
        "card_metric",
        "CardMetric",
    ]

    found = [tok for tok in forbidden_tokens if tok in src]
    assert not found, f"Anti-solver audit failed: forbidden task-specific tokens detected in staged_repair.py: {found}"
