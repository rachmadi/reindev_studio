# -*- coding: utf-8 -*-
"""
Unit Tests for V0 Deterministic Phase Validator & Universal Two-Repair Engine
ReinDev Studio — v2.3 (Upstream Requirement Interpretation & Constructibility Gate)
"""

import pytest
from langgraph.graph import END

from backend.phase_validators import validate_v0_phase
from backend.graph import v0_validator_node, route_after_v0_validator
from backend.v0_schema import (
    V0RequirementOutput,
    V0Metadata,
    EpistemicItem,
    EpistemicStatus,
    RequirementCategory,
    ConstructibilityAssessment,
    ConstructibilityStatus,
    DetectedArchetype,
    ApplicationRequirementModel
)


def _make_valid_v0_state(task="Bangun modul REST API inventaris produk"):
    out = V0RequirementOutput(
        metadata=V0Metadata(
            source_text=task,
            detected_language="python",
            detected_archetype=DetectedArchetype.REST_API
        ),
        epistemic_ledger=[
            EpistemicItem(
                id="FACT-01",
                category=RequirementCategory.FUNCTIONAL,
                epistemic_status=EpistemicStatus.FACT,
                statement="Modul REST API inventaris produk",
                basis="Bangun modul REST API inventaris produk",
                confidence=1.0
            ),
            EpistemicItem(
                id="INT-01",
                category=RequirementCategory.INTERACTION,
                epistemic_status=EpistemicStatus.INTERPRETATION,
                statement="Implementasi endpoint CRUD REST",
                basis="REST API mengimplikasikan operasi CRUD standar",
                confidence=0.9
            )
        ],
        application_requirement_model=ApplicationRequirementModel(
            functional_requirements=["Manajemen inventaris produk"],
            constraints=["Python"]
        ),
        constructibility=ConstructibilityAssessment(
            status=ConstructibilityStatus.WORKABLE,
            rationale="Kebutuhan terstruktur dan constructible.",
            blocking_gaps=[],
            minimal_viable_interpretation="Solusi minimal REST API"
        )
    )
    return {
        "task": task,
        "target_language": "python",
        "v0_requirement_model": out.model_dump(),
        "repair_attempt_counts": {"v0": 0}
    }


def test_v0_validator_pass_clean():
    """Memverifikasi validasi sukses untuk model kebutuhan V0 yang sah."""
    state = _make_valid_v0_state()
    contract = validate_v0_phase(state)
    assert contract["verdict"] == "PASS"
    assert len(contract["violations"]) == 0


def test_v0_validator_fail_missing_model():
    """Memverifikasi kegagalan CRITICAL jika v0_requirement_model tidak ada."""
    state = {"task": "Bangun aplikasi", "repair_attempt_counts": {"v0": 0}}
    contract = validate_v0_phase(state)
    assert contract["verdict"] == "FAIL"
    assert any(v["violation_type"] == "MANDATORY_FIELD_MISSING" for v in contract["violations"])


def test_v0_validator_fail_hallucinated_fact():
    """Memverifikasi deteksi fakta palsu/halusinasi yang tidak ada pada task pengguna."""
    state = _make_valid_v0_state(task="Bangun kalkulator CLI")
    # Sisipkan fakta halusinasi yang sama sekali tidak ada di task
    state["v0_requirement_model"]["epistemic_ledger"].append({
        "id": "FACT-99",
        "category": "DATA",
        "epistemic_status": "FACT",
        "statement": "Entitas database PostgreSQL dengan kolom uuid dan bcrypt password",
        "basis": "Kebutuhan database relasional PostgreSQL",
        "confidence": 1.0
    })
    contract = validate_v0_phase(state)
    assert contract["verdict"] == "FAIL"
    assert any(v["violation_type"] == "HALLUCINATED_FACT_VIOLATION" for v in contract["violations"])


def test_v0_validator_fail_insufficient_basis():
    """Memverifikasi kegagalan jika INTERPRETATION memiliki basis kosong atau tidak memadai."""
    state = _make_valid_v0_state()
    state["v0_requirement_model"]["epistemic_ledger"][1]["basis"] = "ok"  # < 5 karakter
    contract = validate_v0_phase(state)
    assert contract["verdict"] == "FAIL"
    assert any(v["violation_type"] == "EMPTY_OR_INSUFFICIENT_BASIS" for v in contract["violations"])


def test_v0_validator_fail_contradiction_paradox():
    """Memverifikasi penolakan status WORKABLE jika task mengandung kontradiksi langsung."""
    paradox_task = "Buat endpoint CRUD tapi read-only tanpa modifikasi data"
    state = _make_valid_v0_state(task=paradox_task)
    contract = validate_v0_phase(state)
    assert contract["verdict"] == "FAIL"
    assert any(v["violation_type"] == "UNRESOLVED_CONTRADICTION" for v in contract["violations"])


def test_v0_node_two_repair_lifecycle():
    """Memverifikasi siklus Two-Repair V0: Attempt 0 -> 1 -> 2 -> Terminal Failure."""
    invalid_state = {
        "task": "test",
        "v0_requirement_model": None,  # Memicu FAIL
        "repair_attempt_counts": {"v0": 0}
    }

    # Turn 1: Attempt 0 -> 1
    res1 = v0_validator_node(invalid_state)
    assert res1["v0_validator_contract"]["verdict"] == "FAIL"
    assert res1["repair_attempt_counts"]["v0"] == 1
    assert "v0_feedback" in res1
    invalid_state.update(res1)
    assert route_after_v0_validator(invalid_state) == "v0"

    # Turn 2: Attempt 1 -> 2
    res2 = v0_validator_node(invalid_state)
    assert res2["v0_validator_contract"]["verdict"] == "FAIL"
    assert res2["repair_attempt_counts"]["v0"] == 2
    invalid_state.update(res2)
    assert route_after_v0_validator(invalid_state) == "v0"

    # Turn 3: Attempt 2 -> Terminal Failure
    res3 = v0_validator_node(invalid_state)
    assert res3["v0_validator_contract"]["verdict"] == "FAIL"
    assert res3.get("status") == "terminal_failure_v0_boundary"
    invalid_state.update(res3)
    assert route_after_v0_validator(invalid_state) == END


def test_v0_zero_downstream_leakage():
    """Memverifikasi bahwa saat V0 Validator FAIL, route tidak pernah mengarah ke 'pm'."""
    failing_state = {
        "v0_validator_contract": {"verdict": "FAIL"},
        "repair_attempt_counts": {"v0": 0}
    }
    assert route_after_v0_validator(failing_state) != "pm"

    passing_state = {
        "v0_validator_contract": {"verdict": "PASS"},
        "repair_attempt_counts": {"v0": 0}
    }
    assert route_after_v0_validator(passing_state) == "pm"
