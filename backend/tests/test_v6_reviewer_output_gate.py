# -*- coding: utf-8 -*-
"""
Test Suite for V6 Reviewer Output & Evidence Gate Hardening (v1)

Verifies:
1. classify_reviewer_output("") -> EMPTY, V6_OUTPUT_INVALID
2. classify_reviewer_output(None) -> EMPTY, V6_OUTPUT_INVALID
3. classify_reviewer_output whitespace -> EMPTY, V6_OUTPUT_INVALID
4. classify_reviewer_output without tag -> MALFORMED, V6_OUTPUT_INVALID
5. classify_reviewer_output [APPROVED] -> VALID, is_valid=True
6. classify_reviewer_output [NEEDS_REVISION] without evidence markers -> NON_ACTIONABLE, V6_EVIDENCE_INVALID
7. classify_reviewer_output [NEEDS_REVISION] with structural evidence markers -> VALID
8. classify_reviewer_output [NEEDS_REVISION] tag only -> NON_ACTIONABLE, V6_EVIDENCE_INVALID
9. validate_reviewer_phase with NON_ACTIONABLE / V6_EVIDENCE_INVALID -> FAIL, repair_owner=NONE
10. reviewer_validator_node retry state isolation: classification overrules stale status="needs_revision"
11. Controlled Reviewer Retry: GREEN artifact + EMPTY + retry 0/1 -> routes to "reviewer"
12. Controlled Reviewer Retry: repeated EMPTY + retry budget exhausted (1/1) -> terminal_failure_v6_reviewer_output -> END
13. VALID [APPROVED] -> routes to END (success)
14. VALID [NEEDS_REVISION] with evidence -> routes to "developer"
15. GREEN_STATE_PROTECTION telemetry: log contains GREEN_STATE_PROTECTION and BLOCKED
"""

import pytest
from langgraph.graph import END

from backend.state import SquadState
from backend.phase_validators import classify_reviewer_output, validate_reviewer_phase
from backend.graph import (
    reviewer_validator_node as v6_node,
    route_after_reviewer_validator,
)


# ==============================================================================
# 1. Classification Unit Tests (Evidence presence, not text length)
# ==============================================================================

def test_1_classify_empty_string():
    """Test 1: Output string kosong -> EMPTY, V6_OUTPUT_INVALID, is_valid=False."""
    res = classify_reviewer_output("")
    assert res["classification"] == "EMPTY"
    assert res["terminal_status"] == "V6_OUTPUT_INVALID"
    assert res["is_valid"] is False
    assert res["raw_output_length"] == 0
    assert res["evidence_markers_count"] == 0


def test_2_classify_none():
    """Test 2: Output None -> EMPTY, V6_OUTPUT_INVALID, is_valid=False."""
    res = classify_reviewer_output(None)
    assert res["classification"] == "EMPTY"
    assert res["terminal_status"] == "V6_OUTPUT_INVALID"
    assert res["is_valid"] is False
    assert res["raw_output_length"] == 0


def test_3_classify_whitespace_only():
    """Test 3: Output whitespace-only -> EMPTY, V6_OUTPUT_INVALID, is_valid=False."""
    res = classify_reviewer_output("   \n\t  \r\n   ")
    assert res["classification"] == "EMPTY"
    assert res["terminal_status"] == "V6_OUTPUT_INVALID"
    assert res["is_valid"] is False


def test_4_classify_malformed_no_verdict_tag():
    """Test 4: Output ada teks tetapi tanpa tag verdict -> MALFORMED, V6_OUTPUT_INVALID."""
    raw = "Kode ini lumayan bagus tetapi ada beberapa hal yang saya pikirkan tentang arsitektur..."
    res = classify_reviewer_output(raw)
    assert res["classification"] == "MALFORMED"
    assert res["terminal_status"] == "V6_OUTPUT_INVALID"
    assert res["is_valid"] is False
    assert res["has_approved_tag"] is False
    assert res["has_needs_revision_tag"] is False


def test_5_classify_valid_approved():
    """Test 5: Output mengandung [APPROVED] tanpa kontradiksi -> VALID, is_valid=True."""
    raw = "[APPROVED] Seluruh unit test lulus 100% dan implementasi mematuhi kontrak secara ketat."
    res = classify_reviewer_output(raw)
    assert res["classification"] == "VALID"
    assert res["terminal_status"] is None
    assert res["is_valid"] is True
    assert res["has_approved_tag"] is True


def test_6_classify_needs_revision_no_evidence_is_non_actionable():
    """
    Test 6: [NEEDS_REVISION] + teks tanpa structural evidence markers -> NON_ACTIONABLE.
    Prinsip: Evidence presence, not text length, determines whether revision is actionable.
    Bahkan teks panjang tanpa evidence markers tetap NON_ACTIONABLE.
    """
    raw = (
        "[NEEDS_REVISION] Tolong perbaiki kode ini agar lebih rapi dan bersih. "
        "Saya merasa ada beberapa struktur yang kurang optimal dan perlu ditulis ulang "
        "agar mengikuti prinsip-prinsip rekayasa perangkat lunak modern yang baik dan benar."
    )
    res = classify_reviewer_output(raw)
    assert res["classification"] == "NON_ACTIONABLE"
    assert res["terminal_status"] == "V6_EVIDENCE_INVALID"
    assert res["is_valid"] is False
    assert res["evidence_markers_count"] == 0


def test_7_classify_needs_revision_with_structural_evidence_is_valid():
    """Test 7: [NEEDS_REVISION] dengan structural evidence markers -> VALID."""
    raw = (
        "[NEEDS_REVISION]\n"
        "Temuan audit:\n"
        "- main.py:45: fungsi process_item tidak memeriksa nilai None\n"
        "- models.py:12: class UserModel belum mengimplementasikan validate()\n"
        "Rekomendasi: tambahkan guard clause dan exception handling."
    )
    res = classify_reviewer_output(raw)
    assert res["classification"] == "VALID"
    assert res["terminal_status"] is None
    assert res["is_valid"] is True
    assert res["evidence_markers_count"] > 0
    assert "file_reference" in res["evidence_markers_found"]


def test_8_classify_needs_revision_tag_only_is_non_actionable():
    """Test 8: Hanya tag [NEEDS_REVISION] tanpa body temuan -> NON_ACTIONABLE, V6_EVIDENCE_INVALID."""
    res = classify_reviewer_output("[NEEDS_REVISION]")
    assert res["classification"] == "NON_ACTIONABLE"
    assert res["terminal_status"] == "V6_EVIDENCE_INVALID"
    assert res["is_valid"] is False


# ==============================================================================
# 2. Phase Validator Evidence Gate Tests
# ==============================================================================

def test_9_validate_reviewer_phase_blocks_invalid_classification():
    """
    Test 9: validate_reviewer_phase memblokir NON_ACTIONABLE / V6_EVIDENCE_INVALID.
    Menghasilkan FAIL, criterion reviewer_output_validity, dan repair_owner NONE.
    """
    state: SquadState = {
        "test_results": {"passed": True, "exit_code": 0},
        "contract_status": "FROZEN",
        "iteration_count": 1,
        "max_iterations": 10,
        "review_notes": "[NEEDS_REVISION] Perbaiki saja.",
        "status": "needs_revision",
        "logs": []
    }
    contract = validate_reviewer_phase(
        state=state,
        review_verdict="NEEDS_REVISION",
        review_notes="[NEEDS_REVISION] Perbaiki saja.",
        reviewer_output_classification="NON_ACTIONABLE",
        reviewer_terminal_status="V6_EVIDENCE_INVALID",
    )
    assert contract["verdict"] == "FAIL"
    assert contract["repair_owner"] == "NONE"
    assert contract["evaluated_review_verdict"] == "REVIEWER_OUTPUT_INVALID"
    assert any(
        v.get("criterion") == "reviewer_output_validity" and v.get("terminal_status") == "V6_EVIDENCE_INVALID"
        for v in contract["violations"]
    )


# ==============================================================================
# 3. Node & Routing Tests (Retry State Isolation & Green State Protection)
# ==============================================================================

def test_10_retry_state_isolation_classification_overrules_stale_status():
    """
    Test 10: Retry State Isolation.
    Jika state memiliki status lama 'needs_revision', tetapi reviewer_output_classification
    terbaru adalah 'EMPTY', maka klasifikasi terbaru HARUS menang.
    review_verdict menjadi 'REVIEWER_OUTPUT_INVALID', BUKAN 'NEEDS_REVISION'.
    """
    state: SquadState = {
        "test_results": {"passed": True, "exit_code": 0},
        "contract_status": "FROZEN",
        "review_notes": "",
        "status": "needs_revision",  # Stale status from previous loop
        "reviewer_output_classification": {
            "classification": "EMPTY",
            "terminal_status": "V6_OUTPUT_INVALID",
            "is_valid": False,
            "reason": "Raw output empty",
            "raw_output_length": 0,
            "has_approved_tag": False,
            "has_needs_revision_tag": False,
            "evidence_markers_found": [],
            "evidence_markers_count": 0,
        },
        "reviewer_retry_count": 0,
        "reviewer_retry_budget": 1,
        "repair_attempt_counts": {"reviewer": 0, "developer": 0},
        "logs": []
    }
    res = v6_node(state)
    assert res["review_verdict"] == "REVIEWER_OUTPUT_INVALID"
    contract = res["reviewer_validator_contract"]
    assert contract["verdict"] == "FAIL"
    assert contract["repair_owner"] == "NONE"


def test_11_controlled_retry_routes_to_reviewer():
    """
    Test 11: Green artifact + EMPTY classification + retry_count=0 (budget=1) ->
    increment reviewer_retry_count menjadi 1, route kembali ke 'reviewer'.
    TIDAK boleh menyentuh Developer.
    """
    state: SquadState = {
        "test_results": {"passed": True, "exit_code": 0},
        "contract_status": "FROZEN",
        "review_notes": "",
        "status": "V6_OUTPUT_INVALID",
        "reviewer_output_classification": {
            "classification": "EMPTY",
            "terminal_status": "V6_OUTPUT_INVALID",
            "is_valid": False,
        },
        "reviewer_retry_count": 0,
        "reviewer_retry_budget": 1,
        "repair_attempt_counts": {"reviewer": 0, "developer": 0},
        "logs": []
    }
    res = v6_node(state)
    assert res["reviewer_retry_count"] == 1
    assert res.get("status") != "terminal_failure_v6_reviewer_output"

    merged = {**state, **res}
    route = route_after_reviewer_validator(merged)
    assert route == "reviewer", f"Expected route 'reviewer', got '{route}'"


def test_12_controlled_retry_budget_exhaustion_terminates():
    """
    Test 12: Repeated EMPTY output dengan retry budget habis (retry_count=1 >= budget=1) ->
    status menjadi 'terminal_failure_v6_reviewer_output', route ke END.
    TIDAK boleh menyentuh Developer.
    """
    state: SquadState = {
        "test_results": {"passed": True, "exit_code": 0},
        "contract_status": "FROZEN",
        "review_notes": "",
        "status": "V6_OUTPUT_INVALID",
        "reviewer_output_classification": {
            "classification": "EMPTY",
            "terminal_status": "V6_OUTPUT_INVALID",
            "is_valid": False,
        },
        "reviewer_retry_count": 1,  # Already used the 1 retry
        "reviewer_retry_budget": 1,
        "repair_attempt_counts": {"reviewer": 0, "developer": 0},
        "logs": []
    }
    res = v6_node(state)
    assert res["status"] == "terminal_failure_v6_reviewer_output"

    merged = {**state, **res}
    route = route_after_reviewer_validator(merged)
    assert route == END, f"Expected route END, got '{route}'"


def test_13_valid_approved_routes_to_end():
    """Test 13: Reviewer menghasilkan output VALID [APPROVED] -> route ke END (success)."""
    state: SquadState = {
        "test_results": {"passed": True, "exit_code": 0},
        "contract_status": "FROZEN",
        "review_notes": "[APPROVED] Implementasi sangat baik dan lulus semua pengujian.",
        "status": "completed",
        "reviewer_output_classification": {
            "classification": "VALID",
            "terminal_status": None,
            "is_valid": True,
        },
        "reviewer_retry_count": 0,
        "reviewer_retry_budget": 1,
        "repair_attempt_counts": {"reviewer": 0, "developer": 0},
        "logs": []
    }
    res = v6_node(state)
    assert res["review_verdict"] == "APPROVED"
    assert res["reviewer_validator_contract"]["verdict"] == "PASS"

    merged = {**state, **res}
    route = route_after_reviewer_validator(merged)
    assert route == END


def test_14_valid_needs_revision_with_evidence_routes_to_developer():
    """
    Test 14: Reviewer menghasilkan output VALID [NEEDS_REVISION] dengan bukti struktural
    dan budget developer masih ada -> route ke 'developer'.
    """
    notes = (
        "[NEEDS_REVISION]\n"
        "- lib/main.dart:25: method calculateTotal() mengabaikan nilai diskon negatif\n"
        "Rekomendasi: tambahkan validasi input pada calculateTotal()."
    )
    classification = classify_reviewer_output(notes)
    assert classification["classification"] == "VALID"

    state: SquadState = {
        "test_results": {"passed": True, "exit_code": 0},
        "contract_status": "FROZEN",
        "iteration_count": 1,
        "max_iterations": 10,
        "review_notes": notes,
        "status": "needs_revision",
        "reviewer_output_classification": classification,
        "reviewer_retry_count": 0,
        "reviewer_retry_budget": 1,
        "repair_attempt_counts": {"developer": 0, "reviewer": 0},
        "logs": []
    }
    res = v6_node(state)
    assert res["review_verdict"] == "NEEDS_REVISION"
    assert res["reviewer_validator_contract"]["verdict"] == "PASS"
    assert res["reviewer_validator_contract"]["repair_owner"] == "DEVELOPER"

    merged = {**state, **res}
    route = route_after_reviewer_validator(merged)
    assert route == "developer"


def test_15_green_state_protection_telemetry():
    """
    Test 15: GREEN_STATE_PROTECTION log.
    Saat artefak GREEN (tests passed) menerima output EMPTY dari Reviewer,
    log harus secara eksplisit mencatat 'GREEN_STATE_PROTECTION' dan 'BLOCKED'.
    """
    state: SquadState = {
        "test_results": {"passed": True, "exit_code": 0},
        "contract_status": "FROZEN",
        "review_notes": "",
        "status": "V6_OUTPUT_INVALID",
        "reviewer_output_classification": {
            "classification": "EMPTY",
            "terminal_status": "V6_OUTPUT_INVALID",
            "is_valid": False,
        },
        "reviewer_retry_count": 0,
        "reviewer_retry_budget": 1,
        "repair_attempt_counts": {"reviewer": 0, "developer": 0},
        "logs": []
    }
    res = v6_node(state)
    logs_str = "\n".join(res["logs"])
    assert "GREEN_STATE_PROTECTION" in logs_str
    assert "BLOCKED" in logs_str
    assert "GREEN" in logs_str
