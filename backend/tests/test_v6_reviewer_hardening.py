# -*- coding: utf-8 -*-
"""
Test Suite Hardening for VALIDATOR 6 (Reviewer Phase-End Validator)
Memverifikasi 9-Dimensi Matrix & Invarian Mutlak:
1. Valid Approval: Tests passed, contract FROZEN, reviewer approved -> PASS -> END.
2. False Approval Rejection: Tests failed, reviewer approved -> FAIL (False Approval Prevention).
3. Valid Needs Revision: Code repair requested, dev budget available, no unfreeze -> PASS -> route to developer.
4. Contract Unfreeze Forbidden: Reviewer demands 'ubah kontrak' -> FAIL (Contract immutability).
5. Budget Exhaustion Rejection: Reviewer demands revision but dev budget = 0 -> FAIL.
6. Causal Return Integrity: Return to developer traverses cascade revalidation (V3 -> V4 -> V5 -> Reviewer).
7. Universal Two-Repair Policy: Attempt 1, Attempt 2, Exhaustion to terminal_failure_reviewer_boundary.
8. Multi-domain Generality: CLI, FastAPI, Flutter, Data Pipeline, System.
9. Deterministic Release Gate: Reviewer validator acts as immutable gatekeeper before release.
"""

import pytest
from langgraph.graph import END
from backend.state import SquadState
from backend.graph import (
    reviewer_validator_node as v6_node,
    route_after_reviewer_validator,
    _get_repair_count,
    _get_max_repairs
)
from backend.phase_validators import validate_reviewer_phase, classify_contract_mutation_demand


# ==============================================================================
# Test Cases
# ==============================================================================

def test_dim1_valid_approval_ends_successfully():
    """Dimensi 1: Seluruh pengujian lulus, kontrak FROZEN, reviewer APPROVED -> PASS -> END."""
    state: SquadState = {
        "test_results": {"passed": True, "exit_code": 0},
        "contract_status": "FROZEN",
        "review_notes": "[APPROVED] Implementasi sangat bersih dan memenuhi kontrak.",
        "status": "completed",
        "repair_attempt_counts": {"reviewer": 0},
        "logs": []
    }
    res = v6_node(state)
    contract = res["reviewer_validator_contract"]
    assert contract["verdict"] == "PASS"
    assert contract["evaluated_review_verdict"] == "APPROVED"

    merged = {**state, **res}
    assert route_after_reviewer_validator(merged) == END


def test_dim2_false_approval_rejected():
    """Dimensi 2: Tes gagal tapi Reviewer menerbitkan APPROVED -> validator FAIL -> abort ke END."""
    state: SquadState = {
        "test_results": {"passed": False, "exit_code": 1},
        "contract_status": "FROZEN",
        "review_notes": "[APPROVED] Walaupun tes gagal, kode terlihat bagus.",
        "status": "completed",
        "repair_attempt_counts": {"reviewer": 0},
        "logs": []
    }
    res = v6_node(state)
    contract = res["reviewer_validator_contract"]
    assert contract["verdict"] == "FAIL"
    assert any(v["criterion"] == "review_approval_integrity" for v in contract["violations"])

    merged = {**state, **res}
    # False approval dilarang tembus release -> router mengembalikan END (atau terminal)
    assert route_after_reviewer_validator(merged) == END


def test_dim3_valid_needs_revision_routes_to_developer():
    """Dimensi 3: Reviewer meminta revisi kode teknis dan budget masih tersedia -> PASS -> route ke developer."""
    state: SquadState = {
        "test_results": {"passed": True, "exit_code": 0},
        "contract_status": "FROZEN",
        "iteration_count": 2,
        "max_iterations": 10,
        "review_notes": "[NEEDS_REVISION] Perbaiki penamaan variabel dan dokumentasi docstring.",
        "status": "needs_revision",
        "repair_attempt_counts": {"developer": 0, "reviewer": 0},
        "logs": []
    }
    res = v6_node(state)
    contract = res["reviewer_validator_contract"]
    assert contract["verdict"] == "PASS"
    assert contract["evaluated_review_verdict"] == "NEEDS_REVISION"
    assert contract["repair_owner"] == "DEVELOPER"

    merged = {**state, **res}
    assert route_after_reviewer_validator(merged) == "developer"


def test_dim4_unfreeze_contract_attempt_rejected():
    """Dimensi 4: Reviewer meminta unfreeze / ubah kontrak -> validator FAIL."""
    state: SquadState = {
        "test_results": {"passed": True, "exit_code": 0},
        "contract_status": "FROZEN",
        "iteration_count": 2,
        "max_iterations": 10,
        "review_notes": "[NEEDS_REVISION] Mohon ubah kontrak untuk menambah parameter endpoint.",
        "status": "needs_revision",
        "repair_attempt_counts": {"reviewer": 0},
        "logs": []
    }
    res = v6_node(state)
    contract = res["reviewer_validator_contract"]
    assert contract["verdict"] == "FAIL"
    assert any(v["criterion"] == "frozen_contract_immutability" for v in contract["violations"])

    merged = {**state, **res}
    assert route_after_reviewer_validator(merged) == END


def test_dim5_budget_exhaustion_rejected():
    """Dimensi 5: Reviewer meminta revisi tetapi alokasi budget Developer habis -> FAIL."""
    state: SquadState = {
        "test_results": {"passed": True, "exit_code": 0},
        "contract_status": "FROZEN",
        "iteration_count": 10,
        "max_iterations": 10,
        "review_notes": "[NEEDS_REVISION] Mohon perbaiki refactoring.",
        "status": "needs_revision",
        "repair_attempt_counts": {"reviewer": 0},
        "logs": []
    }
    res = v6_node(state)
    contract = res["reviewer_validator_contract"]
    assert contract["verdict"] == "FAIL"
    assert any(v["criterion"] == "authorized_budget_availability" for v in contract["violations"])

    merged = {**state, **res}
    assert route_after_reviewer_validator(merged) == END


def test_dim6_causal_return_no_shortcut():
    """Dimensi 6: Saat route_after_reviewer_validator mengembalikan developer, developer TIDAK langsung ke reviewer."""
    # Verifikasi ini dibuktikan lewat topology graph: developer -> developer_validator
    from backend.graph import build_squad_graph
    graph = build_squad_graph()
    edges = graph.builder.edges
    dev_targets = [dst for src, dst in edges if src == "developer"]
    assert dev_targets == ["developer_validator"], f"Expected ['developer_validator'], got {dev_targets}"


def test_dim7_universal_two_repair_policy_exhaustion():
    """Dimensi 7: Dua percobaan perbaikan reviewer terlampaui -> terminal_failure_reviewer_boundary."""
    state: SquadState = {
        "test_results": {"passed": False, "exit_code": 1},
        "contract_status": "FROZEN",
        "review_notes": "[APPROVED] False approval attempt 3",
        "status": "completed",
        "repair_attempt_counts": {"reviewer": 2},
        "logs": []
    }
    res = v6_node(state)
    assert res["reviewer_validator_contract"]["verdict"] == "FAIL"
    assert res["status"] == "terminal_failure_reviewer_boundary"

    merged = {**state, **res}
    assert route_after_reviewer_validator(merged) == END


def test_dim8_generality_across_five_domains():
    """Dimensi 8: General across 5 domains: CLI, FastAPI, Flutter, Data Pipeline, System."""
    domains = ["cli", "fastapi", "flutter", "data_pipeline", "system"]
    for d in domains:
        state: SquadState = {
            "test_results": {"passed": True, "exit_code": 0},
            "contract_status": "FROZEN",
            "review_notes": f"[APPROVED] Domain {d} code complies with all specifications.",
            "status": "completed",
            "repair_attempt_counts": {"reviewer": 0},
            "logs": []
        }
        res = v6_node(state)
        assert res["reviewer_validator_contract"]["verdict"] == "PASS", f"Failed for domain {d}"
        merged = {**state, **res}
        assert route_after_reviewer_validator(merged) == END


def test_dim9_deterministic_release_gatekeeper():
    """Dimensi 9: Reviewer validator bertindak sebagai gatekeeper mutlak sebelum release."""
    # Status selain APPROVED/NEEDS_REVISION dievaluasi sebagai FAIL
    state: SquadState = {
        "test_results": {"passed": True, "exit_code": 0},
        "contract_status": "FROZEN",
        "review_notes": "Catatan tidak jelas tanpa tag keputusan",
        "status": "unknown",
        "repair_attempt_counts": {"reviewer": 0},
        "logs": []
    }
    res = v6_node(state)
    contract = res["reviewer_validator_contract"]
    assert contract["evaluated_review_verdict"] == "FAIL"
    merged = {**state, **res}
    assert route_after_reviewer_validator(merged) == END


# ==============================================================================
# Hardening: Intent Distinction Tests (Mandated IA Cases)
# ==============================================================================

def test_v6_contract_mutation_classification_cases():
    """
    Memverifikasi 5 kasus spesifik klasifikasi tuntutan mutasi kontrak:
    1. 'Implementasi ini mengubah kontrak antarmuka secara fundamental.' -> DESCRIPTIVE (False)
    2. 'Ubah kontrak antarmuka.' -> DEMAND (True)
    3. 'Revisi kontrak agar endpoint menjadi ...' -> DEMAND (True)
    4. 'Kontrak harus di-unfreeze.' -> DEMAND (True)
    5. 'Implementasi tidak boleh mengubah frozen contract.' -> DESCRIPTIVE (False)
    """
    cases = [
        ("Implementasi ini mengubah kontrak antarmuka secara fundamental.", "DESCRIPTIVE", False),
        ("Ubah kontrak antarmuka.", "DEMAND", True),
        ("Revisi kontrak agar endpoint menjadi ...", "DEMAND", True),
        ("Kontrak harus di-unfreeze.", "DEMAND", True),
        ("Implementasi tidak boleh mengubah frozen contract.", "DESCRIPTIVE", False),
    ]
    for text, expected_cls, expected_demand in cases:
        res = classify_contract_mutation_demand(text)
        assert res["classification"] == expected_cls, f"Expected {expected_cls} for '{text}', got {res['classification']}"
        assert res["is_mutation_demand"] == expected_demand, f"Expected is_mutation_demand={expected_demand} for '{text}'"


def test_v6_descriptive_contract_observation_does_not_fail_gate():
    """
    Kasus 1 & 5: Reviewer menulis kalimat deskriptif atau larangan perubahan kontrak.
    Gate V6 TIDAK boleh false-positive memvonis FAIL frozen_contract_immutability.
    Jika ada sisa budget, harus PASS dan route ke developer.
    """
    descriptive_notes = [
        "[NEEDS_REVISION] Implementasi ini mengubah kontrak antarmuka secara fundamental. Mohon perbaiki implementasi widget.",
        "[NEEDS_REVISION] Implementasi tidak boleh mengubah frozen contract. Perbaiki method yang ada.",
    ]
    for notes in descriptive_notes:
        state: SquadState = {
            "test_results": {"passed": True, "exit_code": 0},
            "contract_status": "FROZEN",
            "iteration_count": 1,
            "max_iterations": 10,
            "review_notes": notes,
            "status": "needs_revision",
            "repair_attempt_counts": {"developer": 0, "reviewer": 0},
            "logs": []
        }
        res = v6_node(state)
        contract = res["reviewer_validator_contract"]
        assert contract["verdict"] == "PASS", f"Failed for notes: {notes}"
        assert contract["repair_owner"] == "DEVELOPER"
        assert not any(v["criterion"] == "frozen_contract_immutability" for v in contract["violations"])

        merged = {**state, **res}
        assert route_after_reviewer_validator(merged) == "developer"


def test_v6_actionable_contract_mutation_demands_fail_gate():
    """
    Kasus 2, 3 & 4: Reviewer secara imperatif menuntut ubah/revisi kontrak atau unfreeze.
    Gate V6 WAJIB memvonis FAIL frozen_contract_immutability dan router abort ke END.
    """
    demand_notes = [
        "[NEEDS_REVISION] Ubah kontrak antarmuka.",
        "[NEEDS_REVISION] Revisi kontrak agar endpoint menjadi ...",
        "[NEEDS_REVISION] Kontrak harus di-unfreeze.",
    ]
    for notes in demand_notes:
        state: SquadState = {
            "test_results": {"passed": True, "exit_code": 0},
            "contract_status": "FROZEN",
            "iteration_count": 1,
            "max_iterations": 10,
            "review_notes": notes,
            "status": "needs_revision",
            "repair_attempt_counts": {"reviewer": 0},
            "logs": []
        }
        res = v6_node(state)
        contract = res["reviewer_validator_contract"]
        assert contract["verdict"] == "FAIL", f"Expected FAIL for notes: {notes}"
        assert any(v["criterion"] == "frozen_contract_immutability" for v in contract["violations"])

        merged = {**state, **res}
        assert route_after_reviewer_validator(merged) == END

