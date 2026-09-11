# -*- coding: utf-8 -*-
"""
Unit Tests for Restored Universal StateGraph Topology (Tahap 1 Verification)
ReinDev Studio — v2.2 (End-Phase Validated Engine)

Memverifikasi secara deterministik:
1. Keberadaan seluruh 6 End-Phase Quality Boundaries pada StateGraph otoritatif.
2. Penegakan Universal Two-Repair Policy (repair_attempt_count 0 -> 1 -> 2 -> TERMINAL FAILURE).
3. Penegakan mutlak Zero Downstream Leakage pada setiap fase (V1 s.d. V6).
4. Eliminasi kebocoran V5 -> Reviewer pada saat FAIL.
5. Preservasi Causal Return dan eliminasi bypass Reviewer.
"""

import pytest
from langgraph.graph import END
from backend.graph import (
    build_squad_graph,
    squad_graph,
    pm_validator_node,
    route_after_pm_validator,
    architect_validator_node,
    route_after_architect_validator,
    developer_validator_node,
    route_after_developer_validator,
    test_suite_validator_node as v4_test_suite_validator_node,
    route_after_test_suite_validator,
    executor_validator_node,
    route_after_executor_validator,
    reviewer_validator_node,
    route_after_reviewer_validator
)
from backend.contract import ContractStatus


# ==============================================================================
# 1. StateGraph Compilation & Node Registration Tests
# ==============================================================================

def test_squad_graph_nodes_registration():
    """Memverifikasi bahwa seluruh 6 produser dan 6 validator terdaftar di StateGraph."""
    graph = build_squad_graph()
    nodes = set(graph.nodes.keys())
    
    expected_producers = {"pm", "architect", "developer", "tester", "frozen_oracle", "executor", "reviewer"}
    expected_validators = {
        "pm_validator",
        "architect_validator",
        "developer_validator",
        "test_suite_validator",
        "executor_validator",
        "reviewer_validator"
    }
    
    for p in expected_producers:
        assert p in nodes, f"Producer node '{p}' tidak ditemukan pada StateGraph"
        
    for v in expected_validators:
        assert v in nodes, f"Validator boundary '{v}' tidak ditemukan pada StateGraph"


# ==============================================================================
# 2. V1: PM Phase Boundary & Two-Repair Routing Tests
# ==============================================================================

def test_v1_pm_boundary_pass():
    state = {
        "pm_validator_contract": {"verdict": "PASS", "violations": []},
        "repair_attempt_counts": {"pm": 0}
    }
    assert route_after_pm_validator(state) == "architect"


def test_v1_pm_boundary_repair_attempt_1():
    state = {
        "specifications": "",
        "contract": {},
        "repair_attempt_counts": {"pm": 0}
    }
    res = pm_validator_node(state)
    assert res["pm_validator_contract"]["verdict"] == "FAIL"
    assert res["repair_attempt_counts"]["pm"] == 1
    
    state.update(res)
    assert route_after_pm_validator(state) == "pm"


def test_v1_pm_boundary_repair_attempt_2():
    state = {
        "specifications": "",
        "contract": {},
        "repair_attempt_counts": {"pm": 1}
    }
    res = pm_validator_node(state)
    assert res["pm_validator_contract"]["verdict"] == "FAIL"
    assert res["repair_attempt_counts"]["pm"] == 2
    
    state.update(res)
    assert route_after_pm_validator(state) == "pm"


def test_v1_pm_boundary_terminal_failure_zero_leakage():
    state = {
        "specifications": "",
        "contract": {},
        "repair_attempt_counts": {"pm": 2}
    }
    res = pm_validator_node(state)
    assert res["pm_validator_contract"]["verdict"] == "FAIL"
    assert res["status"] == "terminal_failure_pm_boundary"
    
    state.update(res)
    decision = route_after_pm_validator(state)
    assert decision == END, f"Kebocoran downstream terdeteksi! V1 gagal setelah 2 perbaikan diarahkan ke: {decision}"


# ==============================================================================
# 3. V2: Architect Boundary & Two-Repair Routing Tests
# ==============================================================================

def test_v2_architect_boundary_pass():
    state = {
        "architect_validator_contract": {"verdict": "PASS"},
        "contract_status": ContractStatus.FROZEN.value,
        "repair_attempt_counts": {"architect": 0}
    }
    assert route_after_architect_validator(state) == "developer"


def test_v2_architect_boundary_repair_cycle():
    state = {
        "architecture_plan": "",
        "contract": {},
        "repair_attempt_counts": {"architect": 0}
    }
    res = architect_validator_node(state)
    assert res["repair_attempt_counts"]["architect"] == 1
    state.update(res)
    assert route_after_architect_validator(state) == "architect"
    
    res2 = architect_validator_node(state)
    assert res2["repair_attempt_counts"]["architect"] == 2
    state.update(res2)
    assert route_after_architect_validator(state) == "architect"
    
    res3 = architect_validator_node(state)
    assert res3["status"] == "terminal_failure_architect_boundary"
    state.update(res3)
    decision = route_after_architect_validator(state)
    assert decision == END, f"Kebocoran downstream terdeteksi! V2 gagal setelah 2 perbaikan diarahkan ke: {decision}"


# ==============================================================================
# 4. V3: Developer Pre-Execution Boundary Tests (Zero Leakage to Reviewer/Sandbox)
# ==============================================================================

def test_v3_developer_boundary_pass():
    state = {
        "developer_validator_contract": {"verdict": "PASS"},
        "frozen_oracle_path": "some/path",
        "repair_attempt_counts": {"developer": 0}
    }
    assert route_after_developer_validator(state) == "frozen_oracle"


def test_v3_developer_boundary_terminal_failure_zero_leakage():
    state = {
        "code_files": {"main.py": "def syntax_error("},
        "contract": {"task_intent": {"authoritative_target_file": "main.py"}},
        "target_language": "python",
        "repair_attempt_counts": {"developer": 2}
    }
    res = developer_validator_node(state)
    assert res["status"] == "terminal_failure_developer_boundary"
    state.update(res)
    decision = route_after_developer_validator(state)
    assert decision == END, f"Kebocoran terdeteksi! V3 gagal diarahkan ke: {decision} (harus END, bukan reviewer/executor)"


# ==============================================================================
# 5. V4: Test Suite Boundary Tests (Frozen Oracle Corrupt -> Immediate Abort)
# ==============================================================================

def test_v4_frozen_oracle_corrupt_immediate_abort():
    state = {
        "frozen_oracle_path": "experiments/frozen_oracle/cli_t1",
        "expected_oracle_sha": "wrong_hash_to_trigger_fail",
        "test_files": {"test_main.py": "def test_dummy(): pass"}
    }
    res = v4_test_suite_validator_node(state)
    assert res["test_suite_validator_contract"]["verdict"] == "FAIL"
    assert res["status"] == "terminal_failure_frozen_oracle_corrupt"
    state.update(res)
    assert route_after_test_suite_validator(state) == END


# ==============================================================================
# 6. V5: Behavioral Execution Boundary Tests (KOREKSI MUTLAK: ZERO LEAK TO REVIEWER)
# ==============================================================================

def test_v5_behavioral_boundary_pass_routes_to_reviewer():
    state = {
        "executor_iteration_validator_contract": {"verdict": "PASS"},
        "repair_attempt_counts": {"executor": 0}
    }
    assert route_after_executor_validator(state) == "reviewer"


def test_v5_behavioral_boundary_repair_attempt_routes_to_developer():
    state = {
        "executor_iteration_validator_contract": {"verdict": "FAIL"},
        "status": "executing",
        "repair_attempt_counts": {"executor": 0}
    }
    decision = route_after_executor_validator(state)
    assert decision == "developer"


def test_v5_behavioral_boundary_terminal_failure_ZERO_LEAK_TO_REVIEWER():
    # KRITIKAL: Jika eksekusi gagal setelah 2 perbaikan, WAJIB STOP DI END!
    # DILARANG KERAS ROUTE KE REVIEWER!
    state = {
        "executor_iteration_validator_contract": {"verdict": "FAIL"},
        "status": "terminal_failure_behavioral_boundary",
        "repair_attempt_counts": {"executor": 2}
    }
    decision = route_after_executor_validator(state)
    assert decision == END, f"DEFECT TERDETEKSI: V5 gagal setelah repair_count 2 dialirkan ke '{decision}' alih-alih END!"


def test_v5_causal_return_to_architect():
    state = {
        "executor_iteration_validator_contract": {"verdict": "FAIL"},
        "causal_owner_phase": "architect",
        "repair_attempt_counts": {"executor": 1, "architect": 0},
        "status": "executing"
    }
    decision = route_after_executor_validator(state)
    assert decision == "architect", f"Causal return gagal diarahkan ke architect: {decision}"


# ==============================================================================
# 7. V6: Reviewer Boundary & Causal Loop Tests
# ==============================================================================

def test_v6_reviewer_boundary_approved_ends_success():
    state = {
        "reviewer_validator_contract": {
            "verdict": "PASS",
            "evaluated_review_verdict": "APPROVED"
        }
    }
    assert route_after_reviewer_validator(state) == END


def test_v6_reviewer_boundary_false_approval_terminal_fail():
    state = {
        "reviewer_validator_contract": {"verdict": "FAIL"}
    }
    assert route_after_reviewer_validator(state) == END
