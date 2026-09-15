# -*- coding: utf-8 -*-
"""
Deterministic Unit Test Suite for Treatment #1.6
Universal Developer Semantic Repair Grounding v1
Gates A through L
"""

import re
import pytest
from typing import Dict, Any, List

from backend.developer_semantic_repair import (
    SemanticComparisonStatus,
    ObservableOutcomeType,
    SemanticDiff,
    NormalizedObservation,
    DeveloperRepairEvidence,
    normalize_runtime_evidence,
    compare_scenario_with_observation,
    sync_developer_semantic_evidence_with_state,
    assemble_developer_semantic_repair_context,
)


class MockCanonicalScenario:
    def __init__(
        self,
        scenario_id: str,
        caller: str,
        stimulus: str,
        expected_outcome: Any,
        is_negative_test: bool = False,
        precondition: str = "default",
        obligation_ref: str = "OBL-001"
    ):
        self.scenario_id = scenario_id
        self.caller = caller
        self.stimulus = stimulus
        self.expected_outcome = expected_outcome
        self.is_negative_test = is_negative_test
        self.precondition = precondition
        self.obligation_ref = obligation_ref
        self.observable_output = None


# ==============================================================================
# Gate A: expected == actual -> MATCH
# ==============================================================================
def test_gate_a_expected_equals_actual_match():
    scenario = MockCanonicalScenario(
        scenario_id="SC-001",
        caller="test_calculate_sum",
        stimulus="calculate_sum(2, 3)",
        expected_outcome={"value": "5"},
        is_negative_test=False
    )
    observation = NormalizedObservation(
        observation_id="OBS-001",
        target_symbol="calculate_sum",
        caller="test_calculate_sum",
        observable_outcome=ObservableOutcomeType.SUCCESS.value,
        actual_properties={"observed_value": "5"},
        raw_runtime_evidence="",
        exit_code=0
    )
    evidence = compare_scenario_with_observation(scenario, observation)
    assert evidence.comparison_status == SemanticComparisonStatus.MATCH.value
    assert evidence.semantic_diff.category == "MATCH"
    assert len(evidence.semantic_diff.mismatched_properties) == 0


# ==============================================================================
# Gate B: expected != actual -> MISMATCH
# ==============================================================================
def test_gate_b_expected_differs_from_actual_mismatch():
    scenario = MockCanonicalScenario(
        scenario_id="SC-002",
        caller="test_delete_missing_item",
        stimulus="DELETE /items/999",
        expected_outcome={"status_code": 404},
        is_negative_test=True
    )
    # Actual runtime returned 204 (success) instead of error
    observation = NormalizedObservation(
        observation_id="OBS-002",
        target_symbol="delete_item",
        caller="test_delete_missing_item",
        observable_outcome=ObservableOutcomeType.SUCCESS.value,
        actual_properties={"observed_value": "204", "status_code": "204"},
        raw_runtime_evidence="assert 204 == 404",
        exit_code=1
    )
    evidence = compare_scenario_with_observation(scenario, observation)
    assert evidence.comparison_status == SemanticComparisonStatus.MISMATCH.value
    assert "observable_outcome" in evidence.semantic_diff.mismatched_properties or "value" in evidence.semantic_diff.mismatched_properties
    assert evidence.semantic_diff.category in ("ERROR_OUTCOME_UNOBSERVED", "PROPERTY_VALUE_MISMATCH")


# ==============================================================================
# Gate C: insufficient evidence -> UNDETERMINED (never forced into MISMATCH)
# ==============================================================================
def test_gate_c_insufficient_evidence_undetermined():
    scenario = MockCanonicalScenario(
        scenario_id="SC-003",
        caller="test_unexecuted_scenario",
        stimulus="execute_task()",
        expected_outcome={"status": "completed"},
        is_negative_test=False
    )
    # Observation is None (no diagnostic evidence captured for this specific scenario)
    evidence = compare_scenario_with_observation(scenario, observation=None)
    assert evidence.comparison_status == SemanticComparisonStatus.UNDETERMINED.value
    assert evidence.semantic_diff.category == "UNDETERMINED"
    assert evidence.comparison_status != SemanticComparisonStatus.MISMATCH.value


# ==============================================================================
# Gate D: semantic comparison across representations (Canonical Equivalence)
# ==============================================================================
def test_gate_d_semantic_comparison_across_representations():
    """
    Menguji kesetaraan semantik pada canonical layer lintas bahasa dan domain:
    Adapter Python & Adapter Dart menghasilkan Canonical NormalizedObservation yang setara.
    """
    # 1. Output Python pytest
    py_raw = "FAILED test_math.py::test_vector_dot - assert 10 == 15"
    py_obs_list = normalize_runtime_evidence(py_raw, exit_code=1, target_language="python")
    assert len(py_obs_list) >= 1
    py_obs = py_obs_list[0]
    assert py_obs.actual_properties.get("observed_value") == "10"

    # 2. Output Dart test
    dart_raw = "FAIL: Vector dot product test\n  Expected: 15\n  Actual: 10\n"
    dart_obs_list = normalize_runtime_evidence(dart_raw, exit_code=1, target_language="dart")
    assert len(dart_obs_list) >= 1
    dart_obs = dart_obs_list[0]
    assert dart_obs.actual_properties.get("observed_value") == "10"

    # 3. Canonical scenario
    sc = MockCanonicalScenario(
        scenario_id="SC-VEC-01",
        caller="test_vector_dot",
        stimulus="vector_dot([1, 2], [3, 4])",
        expected_outcome={"expected_value": "15"}
    )

    ev_py = compare_scenario_with_observation(sc, py_obs)
    ev_dart = compare_scenario_with_observation(sc, dart_obs)

    # Verifikasi ekivalensi pada canonical layer
    assert ev_py.comparison_status == ev_dart.comparison_status == SemanticComparisonStatus.MISMATCH.value
    assert ev_py.semantic_diff.mismatched_properties == ev_dart.semantic_diff.mismatched_properties
    assert ev_py.expected["semantic_properties"] == ev_dart.expected["semantic_properties"]
    assert ev_py.actual["semantic_properties"]["observed_value"] == ev_dart.actual["semantic_properties"]["observed_value"]


# ==============================================================================
# Gate E: preserved invariant remains preserved
# ==============================================================================
def test_gate_e_preserved_invariant_remains_preserved():
    state = {
        "locked_invariants": {
            "INV-001": {
                "invariant_id": "INV-001",
                "description": "test_create_product passes 100%",
                "status": "PROVEN",
                "target_symbol": "create_product"
            }
        },
        "previous_passed_tests": [{"test_name": "test_create_product"}]
    }
    # Unrelated failure in test_delete_product
    sc = MockCanonicalScenario("SC-DEL", "test_delete_product", "DELETE /items/1", {"status_code": 204})
    obs = NormalizedObservation("OBS-DEL", "delete_product", "test_delete_product", "ERROR", {"observed_value": "500"}, "fail", exit_code=1)
    ev = compare_scenario_with_observation(sc, obs)

    active_evs, active_invs, reg_warnings = sync_developer_semantic_evidence_with_state(state, [ev])
    assert len(reg_warnings) == 0
    assert not ev.is_regression
    assert len(active_invs) == 1
    assert active_invs[0]["status"] == "PROVEN"


# ==============================================================================
# Gate F: regression detection
# ==============================================================================
def test_gate_f_regression_detection():
    # Skenario 'test_create_product' sebelumnya PROVEN
    state = {
        "locked_invariants": {
            "INV-001": {
                "invariant_id": "INV-001",
                "description": "test_create_product",
                "status": "PROVEN",
                "target_symbol": "test_create_product"
            }
        },
        "previous_passed_tests": [{"test_name": "test_create_product"}]
    }
    # Namun pada iterasi ini, test_create_product GAGAL!
    sc = MockCanonicalScenario("SC-CREATE", "test_create_product", "POST /items", {"status_code": 201})
    obs = NormalizedObservation("OBS-REG", "create_product", "test_create_product", "ERROR", {"observed_value": "500"}, "error", exit_code=1)
    ev = compare_scenario_with_observation(sc, obs)

    active_evs, active_invs, reg_warnings = sync_developer_semantic_evidence_with_state(state, [ev])
    assert ev.is_regression is True
    assert len(reg_warnings) >= 1
    assert "REGRESSION DETECTED" in reg_warnings[0]


# ==============================================================================
# Gate G: multiple active failures
# ==============================================================================
def test_gate_g_multiple_active_failures():
    state = {"locked_invariants": {}, "previous_passed_tests": []}
    sc1 = MockCanonicalScenario("SC-01", "test_get", "GET /items", {"status_code": 200})
    obs1 = NormalizedObservation("OBS-1", "get_items", "test_get", "ERROR", {"observed_value": "500"}, "error")
    ev1 = compare_scenario_with_observation(sc1, obs1)

    sc2 = MockCanonicalScenario("SC-02", "test_post", "POST /items", {"status_code": 201})
    obs2 = NormalizedObservation("OBS-2", "post_items", "test_post", "ERROR", {"observed_value": "400"}, "error")
    ev2 = compare_scenario_with_observation(sc2, obs2)

    active_evs, active_invs, _ = sync_developer_semantic_evidence_with_state(state, [ev1, ev2])
    # Kedua failure aktif WAJIB dipertahankan, tidak boleh salah satu hilang
    assert len(active_evs) == 2
    scenario_ids = [e.scenario_id for e in active_evs]
    assert "SC-01" in scenario_ids
    assert "SC-02" in scenario_ids


# ==============================================================================
# Gate H: historical evidence does not become active failure
# ==============================================================================
def test_gate_h_historical_evidence_not_active_failure():
    state = {
        "locked_invariants": {},
        "previous_passed_tests": [],
        "historical_validation_evidence": [
            {"scenario_id": "SC-RESOLVED", "resolved_at_iteration": 1, "resolution_evidence": "MATCH"}
        ]
    }
    # Skenario yang baru dievaluasi berstatus MATCH (lulus)
    sc = MockCanonicalScenario("SC-RESOLVED", "test_resolved", "GET /resolved", {"status_code": 200})
    obs = NormalizedObservation("OBS-RES", "get_resolved", "test_resolved", "SUCCESS", {"observed_value": "200"}, "", exit_code=0)
    ev = compare_scenario_with_observation(sc, obs)

    active_evs, _, _ = sync_developer_semantic_evidence_with_state(state, [ev])
    # Skenario MATCH tidak boleh dimasukkan ke active_evidences
    assert len(active_evs) == 0


# ==============================================================================
# Gate I: repair context ordering (Strict 10-Tier Hierarchy)
# ==============================================================================
def test_gate_i_repair_context_ordering():
    state = {
        "contract": {
            "task_intent": {"authoritative_target_file": "main.py"},
            "interface_contracts": [{"identifier": "get_item"}],
            "data_models": [{"model_name": "Item"}]
        },
        "contract_status": "FROZEN",
        "code_files": {"main.py": "def get_item(): pass"}
    }
    sc = MockCanonicalScenario("SC-01", "test_get_item", "GET /item/1", {"status_code": 200})
    obs = NormalizedObservation("OBS-1", "get_item", "test_get_item", "ERROR", {"observed_value": "500"}, "fail", exit_code=1)
    ev = compare_scenario_with_observation(sc, obs)

    ctx, meta = assemble_developer_semantic_repair_context(
        state=state,
        active_evidences=[ev],
        preserved_invariants=[{"invariant_id": "INV-1", "description": "base inv", "status": "PROVEN"}],
        raw_diagnostics="Traceback: line 10\nAssertionError: 500 == 200"
    )

    expected_order = [
        "[1] AUTHORITATIVE ACCEPTANCE EXPECTATION",
        "[2] CURRENT SEMANTIC FAILURE",
        "[3] VIOLATED OBLIGATION",
        "[4] LOCKED / PROVEN INVARIANTS",
        "[5] CURRENT IMPLEMENTATION STATE",
        "[6] REPAIR BOUNDARY",
        "[7] EXPECTED POST-REPAIR STATE",
        "[8] VERIFICATION CRITERIA",
        "[9] SUPPORTING DIAGNOSTIC EVIDENCE",
        "[10] RAW EVIDENCE"
    ]

    last_idx = -1
    for title in expected_order:
        idx = ctx.find(title)
        assert idx != -1, f"Missing mandated section: {title}"
        assert idx > last_idx, f"Section {title} is out of order! Found at {idx}, last section at {last_idx}"
        last_idx = idx


# ==============================================================================
# Gate J: repair boundary preservation
# ==============================================================================
def test_gate_j_repair_boundary_preservation():
    sc = MockCanonicalScenario("SC-01", "test_op", "op()", {"res": "ok"})
    obs = NormalizedObservation("OBS-1", "op", "test_op", "ERROR", {"observed_value": "err"}, "fail", exit_code=1)
    ev = compare_scenario_with_observation(
        sc,
        obs,
        allowed_boundary=["Modify functions in 'main.py'"],
        forbidden_boundary=["Do not modify 'test_main.py'"]
    )
    assert "Modify functions in 'main.py'" in ev.repair_boundary["allowed_changes"]
    assert "Do not modify 'test_main.py'" in ev.repair_boundary["forbidden_changes"]


# ==============================================================================
# Gate K: verification criterion generation (Predicates / Conditions, NOT How-To)
# ==============================================================================
def test_gate_k_verification_criterion_generation():
    sc = MockCanonicalScenario(
        scenario_id="SC-04",
        caller="test_check_status",
        stimulus="GET /status",
        expected_outcome={"status_code": 200},
        is_negative_test=False
    )
    obs = NormalizedObservation("OBS-04", "status", "test_check_status", "ERROR", {"observed_value": "500"}, "fail", exit_code=1)
    ev = compare_scenario_with_observation(sc, obs)

    # Kriteria verifikasi WAJIB berupa kondisi/predikat yang harus benar, BUKAN instruksi perbaikan
    for vc in ev.verification_criteria:
        # Tidak boleh ada instruksi implementasi imperatif
        assert not re.search(r"\b(raise|return|use|add|import|implement)\b", vc, re.IGNORECASE), f"Verification criterion violates condition rule: {vc}"
        # Harus menyebut kondisi yang diobservasi
        assert any(k in vc for k in ("observable_outcome", "observed_properties", "passes")), f"Criterion missing condition predicate: {vc}"


# ==============================================================================
# Gate L: static solver audit (Zero Task-Specific Solvers)
# ==============================================================================
def test_gate_l_static_solver_audit():
    """
    Memverifikasi ketiadaan solver berbasis task/framework hardcoded pada developer_semantic_repair.py.
    DILARANG: if fastapi, if 404, if Matrix, if MetricData, if flutter, etc. sebagai aturan penyelesaian khusus.
    """
    import inspect
    from backend import developer_semantic_repair

    source = inspect.getsource(developer_semantic_repair)

    forbidden_patterns = [
        r"if\s+fastapi\b",
        r"if\s+cli\b",
        r"if\s+.*==\s*['\"]404['\"]",
        r"if\s+.*==\s*404\b",
        r"if\s+.*Matrix\b",
        r"if\s+.*MetricData\b",
        r"if\s+.*==\s*['\"]delete['\"]",
        r"if\s+.*==\s*['\"]pydantic['\"]",
    ]

    for pat in forbidden_patterns:
        match = re.search(pat, source, re.IGNORECASE)
        assert match is None, f"Static audit FAILED: task-specific solver pattern '{pat}' found in developer_semantic_repair.py: {match.group(0)}"
