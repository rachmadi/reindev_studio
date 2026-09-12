# -*- coding: utf-8 -*-
"""
Test Suite Hardening for VALIDATOR 5 (Behavioral Execution Validator)
Memverifikasi 9-Dimensi Matrix & Invarian Mutlak:
1. Positive Case: Exit code 0, passed_count > 0, 0 failed, 0 regressions -> PASS -> route to reviewer.
2. Negative Case: Test failure, failed_count > 0, exit_code != 0 -> FAIL -> route to developer.
3. Regression Detection: Previously passed test fails -> FAIL (zero_regression_invariant violated).
4. Invariant Recovery: Regressed test recovered in subsequent run -> marked PROVEN_AGAIN.
5. Causal Routing: Causal owner is Architect -> routes to architect (re-architecting).
6. Repair-Success Attempt 1 -> PASS -> route to reviewer.
7. Repair-Success Attempt 2 -> PASS -> route to reviewer.
8. Terminal Failure Attempt 2 Exhaustion -> terminal_failure_behavioral_boundary -> END (MUTLAK ZERO LEAKAGE KE REVIEWER).
9. Generality across 5 domains: CLI, FastAPI, Flutter, Data Pipeline, System.
10. Dynamic Causal Evidence Package: CEP assembled with non-empty root causes & repair boundary.
11. Absolute Zero Downstream Leakage: route_after_executor_validator NEVER returns reviewer on FAIL.
"""

import pytest
from langgraph.graph import END
from backend.state import SquadState
from backend.graph import (
    executor_validator_node as v5_node,
    route_after_executor_validator,
    _get_repair_count,
    _get_max_repairs
)
from backend.phase_validators import validate_executor_phase


# ==============================================================================
# Test Cases
# ==============================================================================

def test_dim1_positive_execution_clean_pass():
    """Dimensi 1: Eksekusi bersih (exit code 0, 0 failed, 0 regressions) -> PASS -> route ke reviewer."""
    state: SquadState = {
        "test_results": {
            "passed": True,
            "exit_code": 0,
            "passed_count": 5,
            "failed_count": 0,
            "total": 5,
            "passed_test_names": ["test_a", "test_b", "test_c"],
            "output": "3 passed in 0.12s"
        },
        "repair_attempt_counts": {"executor": 0},
        "logs": []
    }
    res = v5_node(state)
    assert res["executor_iteration_validator_contract"]["verdict"] == "PASS"

    merged = {**state, **res}
    assert route_after_executor_validator(merged) == "reviewer"


def test_dim2_negative_test_failure():
    """Dimensi 2: Kegagalan tes sandbox -> FAIL -> route ke developer untuk perbaikan."""
    state: SquadState = {
        "test_results": {
            "passed": False,
            "exit_code": 1,
            "passed_count": 2,
            "failed_count": 1,
            "total": 3,
            "passed_test_names": ["test_a", "test_b"],
            "output": "FAILED test_c - AssertionError: expected 42 but got 0"
        },
        "repair_attempt_counts": {"executor": 0},
        "logs": []
    }
    res = v5_node(state)
    assert res["executor_iteration_validator_contract"]["verdict"] == "FAIL"
    assert res["repair_attempt_counts"]["executor"] == 1

    merged = {**state, **res}
    assert route_after_executor_validator(merged) == "developer"


def test_dim3_regression_detection():
    """Dimensi 3: Regresi terdeteksi (tes yang sebelumnya lulus kini gagal) -> FAIL."""
    state: SquadState = {
        "previous_passed_tests": ["test_legacy_feature", "test_core_math"],
        "test_results": {
            "passed": False,
            "exit_code": 1,
            "passed_count": 1,
            "failed_count": 1,
            "total": 2,
            "passed_test_names": ["test_core_math"],  # test_legacy_feature missing!
            "output": "FAILED test_legacy_feature - AssertionError"
        },
        "repair_attempt_counts": {"executor": 0},
        "logs": []
    }
    res = v5_node(state)
    contract = res["executor_iteration_validator_contract"]
    assert contract["verdict"] == "FAIL"
    assert len(contract["regressions"]) == 1
    assert contract["regressions"][0]["test_or_invariant"] == "test_legacy_feature"
    assert any(v["criterion"] == "zero_regression_invariant" for v in contract["violations"])


def test_dim4_permanent_invariant_recovery():
    """Dimensi 4: Regresi dipulihkan pada iterasi berikutnya -> status PROVEN_AGAIN."""
    # Iterasi 1: regresi terjadi
    state_iter1: SquadState = {
        "iteration_count": 1,
        "previous_passed_tests": ["test_feature_x"],
        "test_results": {
            "passed": False,
            "exit_code": 1,
            "passed_count": 0,
            "failed_count": 1,
            "total": 1,
            "passed_test_names": [],
            "output": "FAILED test_feature_x"
        },
        "repair_attempt_counts": {"executor": 0},
        "invariant_regression_history": {},
        "logs": []
    }
    res1 = v5_node(state_iter1)
    history = res1["invariant_regression_history"]
    inv_key = [k for k in history.keys() if "test_feature_x" in k][0]
    assert history[inv_key]["ever_regressed"] is True

    # Iterasi 2: test_feature_x lulus kembali
    state_iter2: SquadState = {
        "iteration_count": 2,
        "previous_passed_tests": [],
        "test_results": {
            "passed": True,
            "exit_code": 0,
            "passed_count": 1,
            "failed_count": 0,
            "total": 1,
            "passed_test_names": ["test_feature_x"],
            "output": "1 passed"
        },
        "repair_attempt_counts": {"executor": 1},
        "invariant_regression_history": history,
        "logs": []
    }
    res2 = v5_node(state_iter2)
    history2 = res2["invariant_regression_history"]
    assert history2[inv_key]["regression_history"][-1]["recovery_status"] == "PROVEN_AGAIN"


def test_dim5_causal_routing_to_architect():
    """Dimensi 5: Causal routing ke Architect jika causal_owner terbukti Architect."""
    state: SquadState = {
        "causal_owner_phase": "architect",
        "test_results": {
            "passed": False,
            "exit_code": 1,
            "passed_count": 0,
            "failed_count": 1,
            "total": 1,
            "passed_test_names": [],
            "output": "FAILED test_contract_spec - SpecificationMismatchError"
        },
        "repair_attempt_counts": {"executor": 0, "architect": 0},
        "logs": []
    }
    res = v5_node(state)
    assert res["executor_iteration_validator_contract"]["verdict"] == "FAIL"
    assert res.get("causal_owner_phase") == "architect"

    merged = {**state, **res}
    next_node = route_after_executor_validator(merged)
    assert next_node == "architect"


def test_dim6_repair_success_attempt_1():
    """Dimensi 6: Repair-Success Attempt 1 -> PASS -> route ke reviewer."""
    state: SquadState = {
        "test_results": {
            "passed": True,
            "exit_code": 0,
            "passed_count": 3,
            "failed_count": 0,
            "total": 3,
            "passed_test_names": ["test_1", "test_2", "test_3"],
            "output": "3 passed"
        },
        "repair_attempt_counts": {"executor": 1},
        "logs": []
    }
    res = v5_node(state)
    assert res["executor_iteration_validator_contract"]["verdict"] == "PASS"

    merged = {**state, **res}
    assert route_after_executor_validator(merged) == "reviewer"


def test_dim7_repair_success_attempt_2():
    """Dimensi 7: Repair-Success Attempt 2 -> PASS -> route ke reviewer."""
    state: SquadState = {
        "test_results": {
            "passed": True,
            "exit_code": 0,
            "passed_count": 4,
            "failed_count": 0,
            "total": 4,
            "passed_test_names": ["test_1", "test_2", "test_3", "test_4"],
            "output": "4 passed"
        },
        "repair_attempt_counts": {"executor": 2},
        "logs": []
    }
    res = v5_node(state)
    assert res["executor_iteration_validator_contract"]["verdict"] == "PASS"

    merged = {**state, **res}
    assert route_after_executor_validator(merged) == "reviewer"


def test_dim8_terminal_failure_attempt_exhaustion():
    """Dimensi 8: Terminal Failure Attempt 2 Exhaustion -> terminal_failure_behavioral_boundary -> END (Zero Leakage ke Reviewer!)."""
    state: SquadState = {
        "test_results": {
            "passed": False,
            "exit_code": 1,
            "passed_count": 1,
            "failed_count": 2,
            "total": 3,
            "passed_test_names": ["test_1"],
            "output": "FAILED test_2, FAILED test_3"
        },
        "repair_attempt_counts": {"executor": 2},
        "logs": []
    }
    res = v5_node(state)
    assert res["executor_iteration_validator_contract"]["verdict"] == "FAIL"
    assert res["status"] == "terminal_failure_behavioral_boundary"

    merged = {**state, **res}
    # MUTLAK: Pada kegagalan terminal, router V5 HARUS mengembalikan END, TIDAK BOLEH KE REVIEWER!
    assert route_after_executor_validator(merged) == END


def test_dim9_generality_across_five_domains():
    """Dimensi 9: General across 5 domains: CLI, FastAPI, Flutter, Data Pipeline, System."""
    domains = [
        ("cli", "3 passed in 0.05s"),
        ("fastapi", "5 passed in 0.15s"),
        ("flutter", "+3: All tests passed!"),
        ("data_pipeline", "4 passed in 0.20s"),
        ("system", "2 passed in 0.08s"),
    ]
    for domain, out in domains:
        state: SquadState = {
            "test_results": {
                "passed": True,
                "exit_code": 0,
                "passed_count": 3,
                "failed_count": 0,
                "total": 3,
                "passed_test_names": ["test_a", "test_b", "test_c"],
                "output": out
            },
            "repair_attempt_counts": {"executor": 0},
            "logs": []
        }
        res = v5_node(state)
        assert res["executor_iteration_validator_contract"]["verdict"] == "PASS", f"Failed for domain {domain}"
        merged = {**state, **res}
        assert route_after_executor_validator(merged) == "reviewer"


def test_dim10_dynamic_causal_evidence_package():
    """Dimensi 10: CEP dirakit secara deterministik dengan root causes & feedback terarah."""
    state: SquadState = {
        "target_language": "python",
        "code_files": {"main.py": "def add(a, b): return 0"},
        "contract": {
            "task_intent": {"authoritative_target_file": "main.py"},
            "data_models": [{"model_name": "DataRecord"}],
            "interface_contracts": [{"function_name": "process_record", "target_file": "main.py"}]
        },
        "test_results": {
            "passed": False,
            "exit_code": 1,
            "passed_count": 0,
            "failed_count": 1,
            "total": 1,
            "passed_test_names": [],
            "output": "FAILED test_main.py::test_process - TypeError: takes 1 positional argument but 2 were given"
        },
        "repair_attempt_counts": {"executor": 0},
        "logs": []
    }
    res = v5_node(state)
    contract = res["executor_iteration_validator_contract"]
    assert contract["verdict"] == "FAIL"
    cep = contract.get("contextual_evidence_package")
    assert cep is not None
    assert len(cep["root_causes"]) >= 1
    assert "developer_feedback" in res
    assert len(res["developer_feedback"]) > 0


def test_dim11_absolute_zero_leakage_on_any_failure():
    """Dimensi 11: Zero Downstream Leakage Mutlak: route_after_executor_validator TIDAK BOLEH mengembalikan reviewer jika FAIL."""
    fail_state: SquadState = {
        "executor_iteration_validator_contract": {"verdict": "FAIL"},
        "status": "terminal_failure_behavioral_boundary"
    }
    assert route_after_executor_validator(fail_state) != "reviewer"
    assert route_after_executor_validator(fail_state) == END


# ==============================================================================
# Integration Test: Cross-Turn Data-Flow
# Membuktikan jalur:
#   executor_node (Turn N) → previous_diagnostic_evidence
#   → executor_validator_node (Turn N+1) → validate_executor_phase
#   → discover_newly_proven_invariants → locked_invariants
# ==============================================================================

def test_cross_turn_dataflow_diagnostic_evidence_to_locked_invariants():
    """
    Integration test: Verifikasi bahwa previous_diagnostic_evidence yang disimpan
    v5_node di Turn N benar-benar menghasilkan locked_invariants di Turn N+1.

    Ini membuktikan jalur data-flow lengkap:
        Turn N: test_results["diagnostic_evidence"] tersedia (compiler error)
            → v5_node menyimpan previous_diagnostic_evidence ke return dict
        Turn N+1: previous_diagnostic_evidence tersedia di state
            → validate_executor_phase mengirimnya ke discover_newly_proven_invariants
            → simbol yang sebelumnya gagal kini PROVEN karena ada di AST + compiler bersih
            → locked_invariants non-empty
    """
    DART_CODE_WITH_METRIC_DATA = (
        "class MetricData { final String title; MetricData({required this.title}); }"
    )

    # ------- Turn N: Eksekusi GAGAL, MetricData belum ada / tidak dikenali --------
    turn_n_state: SquadState = {
        "test_results": {
            "passed": False,
            "exit_code": 1,
            "passed_count": 0,
            "failed_count": 1,
            "total": 1,
            "output": "Error: Method not found: 'MetricData'.\n",
            "passed_test_names": [],
            "diagnostic_evidence": {
                "failing_tests": [
                    {
                        "message": "Method not found: 'MetricData'",
                        "source_symbol": "MetricData",
                        "test_name": "test_card_widget",
                        "failure_type": "METHOD_NOT_FOUND"
                    }
                ]
            }
        },
        "repair_attempt_counts": {"executor": 0},
        "target_language": "dart",
        "code_files": {"lib/card_metric.dart": "// belum ada MetricData"},
        "logs": []
    }
    res_n = v5_node(turn_n_state)

    # Verifikasi bahwa v5_node menyimpan evidence untuk turn berikutnya
    assert "previous_diagnostic_evidence" in res_n, (
        "v5_node harus menyimpan previous_diagnostic_evidence di return dict"
    )
    prev_diag = res_n["previous_diagnostic_evidence"]
    failing_tests = prev_diag.get("failing_tests", [])
    assert len(failing_tests) >= 1, (
        "previous_diagnostic_evidence harus berisi failing_tests dari turn N"
    )
    assert any(ft.get("source_symbol") == "MetricData" for ft in failing_tests), (
        "MetricData harus ada sebagai source_symbol di previous_diagnostic_evidence"
    )

    # ------- Turn N+1: Developer menambahkan MetricData, eksekusi SUKSES --------
    # Gabungkan state Turn N dengan return Turn N (simulasi LangGraph state merge)
    turn_n1_state: SquadState = {
        **turn_n_state,
        **res_n,  # previous_diagnostic_evidence ada di sini
        "test_results": {
            "passed": True,
            "exit_code": 0,
            "passed_count": 1,
            "failed_count": 0,
            "total": 1,
            "output": "1 passed in 0.15s",
            "passed_test_names": ["test_card_widget"],
            "diagnostic_evidence": {}
        },
        # MetricData sekarang ADA di kode
        "code_files": {"lib/card_metric.dart": DART_CODE_WITH_METRIC_DATA},
        "repair_attempt_counts": {"executor": 1},
    }
    res_n1 = v5_node(turn_n1_state)

    locked = res_n1.get("locked_invariants", {})

    # MetricData HARUS terkunci karena:
    # - Kandidat dari previous_diagnostic_evidence["failing_tests"] (Source B)
    # - Gate 1: ada di AST kode Turn N+1 ✓
    # - Gate 2: compiler_output Turn N+1 bersih dari "Method not found: 'MetricData'" ✓
    assert len(locked) >= 1, (
        f"Setelah Turn N+1 sukses, harus ada ≥1 locked invariant. "
        f"Ditemukan: {list(locked.keys())}"
    )
    metric_locked = [k for k in locked if "MetricData" in k]
    assert metric_locked, (
        f"INV-SYM-MetricData harus terkunci. locked_invariants: {list(locked.keys())}"
    )
    inv = locked[metric_locked[0]]
    assert inv.get("status") == "PROVEN", f"Status harus PROVEN, bukan {inv.get('status')}"
    assert inv.get("state") == "LOCKED", f"State harus LOCKED, bukan {inv.get('state')}"
