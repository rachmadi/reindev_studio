"""
Test Suite: Validator 1 (PM Phase-End Validator) Deep Hardening & 9-Dimension Matrix
ReinDev Studio — Evaluation Matrix according to Implementation Plan v2.2

Dimensions Tested:
1. Positive Cases: Complete, structured specifications pass with 0 violations.
2. Negative Cases: Empty or garbage text fails with STRUCTURAL_INCOMPLETE.
3. Incomplete Cases: Missing Acceptance Criteria fails with MANDATORY_FIELD_MISSING.
4. Contradictory Cases: Conflicting platform/language fails with CONTRADICTION_WITH_AUTHORITATIVE_SOURCE.
5. Ambiguity Cases: Empty/insufficient user task triggers AMBIGUOUS_OR_INSUFFICIENT_GROUND_TRUTH.
6. Repair-Success (Attempt 1): Revalidation after 1 repair succeeds and routes to Architect.
7. Repair-Success (Attempt 2): Revalidation after 2 repairs succeeds and routes to Architect.
8. Terminal Failure: Fails after max repairs (2) aborts immediately to END (Zero Downstream Leakage).
9. Mission-Diverse Generality: Validates 5 distinct domains (CLI, REST, Algorithm, Flutter, Data Pipeline)
   using the identical general rule engine without task-specific rules.
"""

import pytest
from langgraph.graph import END

from backend.phase_validators import validate_pm_phase
from backend.graph import pm_validator_node, route_after_pm_validator


# ==============================================================================
# Helper Factories
# ==============================================================================

def make_valid_pm_specs(domain: str = "CLI", lang: str = "python") -> str:
    lang_header = "Target Bahasa Pemrograman: DART" if "dart" in lang else "Target Bahasa Pemrograman: PYTHON"
    return f"""{lang_header}
1. Ringkasan Sistem: Sistem ini mengimplementasikan modul layanan {domain.lower()} untuk pemrosesan data.
2. User Stories: Sebagai pengguna sistem, saya ingin memproses permintaan secara andal dan cepat.
3. Acceptance Criteria: Skenario 1: input valid menghasilkan output status 200 dan payload yang sesuai."""


def make_valid_contract(domain: str = "CLI_TOOL") -> dict:
    return {
        "task_intent": {"domain": domain},
        "requirements": [{"req_id": "REQ-01", "description": "Fungsi dasar sistem."}]
    }


# ==============================================================================
# 1. Positive Case
# ==============================================================================

def test_dim1_positive_case():
    state = {
        "task": "Buat modul CLI parser untuk kalkulasi angka.",
        "target_language": "python",
        "specifications": make_valid_pm_specs("CLI", "python"),
        "contract": make_valid_contract("CLI_TOOL"),
    }
    result = validate_pm_phase(state)
    assert result["phase"] == "PM"
    assert result["validator_type"] == "PHASE_END"
    assert result["verdict"] == "PASS"
    assert len(result["violations"]) == 0
    assert result["confidence"] == 1.0


# ==============================================================================
# 2. Negative Case (Corrupt / Empty)
# ==============================================================================

def test_dim2_negative_empty_garbage():
    state = {
        "task": "Buat program kalkulator.",
        "target_language": "python",
        "specifications": "halo ini saja",  # Hanya 3 kata
        "contract": {}
    }
    result = validate_pm_phase(state)
    assert result["verdict"] == "FAIL"
    assert any(v.get("violation_type") == "STRUCTURAL_INCOMPLETE" for v in result["violations"])
    assert result["contextual_evidence_package"] is not None


# ==============================================================================
# 3. Incomplete Case (Missing Acceptance Criteria)
# ==============================================================================

def test_dim3_incomplete_missing_acceptance_criteria():
    specs_without_ac = (
        "1. Ringkasan Sistem: Modul pengolahan string teks secara cepat.\n"
        "2. User Stories: Sebagai pengguna saya ingin membalikkan string dan menghitung panjang kata secara otomatis."
    )
    state = {
        "task": "Buat modul string utility.",
        "target_language": "python",
        "specifications": specs_without_ac,
        "contract": make_valid_contract("ALGORITHM"),
    }
    result = validate_pm_phase(state)
    assert result["verdict"] == "FAIL"
    ac_violations = [v for v in result["violations"] if v.get("violation_type") == "MANDATORY_FIELD_MISSING"]
    assert len(ac_violations) >= 1
    assert "acceptance_criteria_actionable" in [v["criterion"] for v in ac_violations]


# ==============================================================================
# 4. Contradictory Case (Conflicting Target Platform)
# ==============================================================================

def test_dim4_contradictory_platform_intent():
    # Pengguna meminta Python, tetapi spesifikasi PM menargetkan Dart/Flutter
    specs_contradictory = (
        "Target Bahasa Pemrograman: DART\n"
        "1. Ringkasan Sistem: Widget UI Flutter untuk menampilkan daftar inventaris.\n"
        "2. User Stories: Sebagai user saya ingin melihat daftar kartu inventaris.\n"
        "3. Acceptance Criteria: Skenario 1: Widget dirender dengan child text."
    )
    state = {
        "task": "Buat modul CLI Python untuk pemrosesan teks.",
        "target_language": "python",
        "specifications": specs_contradictory,
        "contract": make_valid_contract("CLI_TOOL"),
    }
    result = validate_pm_phase(state)
    assert result["verdict"] == "FAIL"
    contra_violations = [v for v in result["violations"] if v.get("violation_type") == "CONTRADICTION_WITH_AUTHORITATIVE_SOURCE"]
    assert len(contra_violations) >= 1
    assert "DART" in contra_violations[0]["message"]


# ==============================================================================
# 5. Ambiguity Case (Empty / Underspecified User Task)
# ==============================================================================

def test_dim5_ambiguity_insufficient_ground_truth():
    state = {
        "task": "",  # Empty task ground truth
        "target_language": "python",
        "specifications": make_valid_pm_specs("CLI", "python"),
        "contract": make_valid_contract("CLI_TOOL"),
    }
    result = validate_pm_phase(state)
    assert result["verdict"] == "FAIL"
    ambiguity_violations = [v for v in result["violations"] if v.get("violation_type") == "AMBIGUOUS_OR_INSUFFICIENT_GROUND_TRUTH"]
    assert len(ambiguity_violations) >= 1


# ==============================================================================
# 6. Repair-Success Attempt 1
# ==============================================================================

def test_dim6_repair_success_attempt_1():
    # Initial state with failing specs and attempt 0
    state = {
        "task": "Buat service perhitungan angka.",
        "target_language": "python",
        "specifications": "Spesifikasi tidak lengkap dan terlalu pendek.",
        "contract": {},
        "repair_attempt_counts": {"pm": 0},
    }
    
    # Step 1: Validator evaluates initial specs -> FAIL, increments to repair #1
    step1_res = pm_validator_node(state)
    assert step1_res["pm_validator_contract"]["verdict"] == "FAIL"
    assert step1_res["repair_attempt_counts"]["pm"] == 1
    assert "pm_feedback" in step1_res
    
    # Check routing: routes back to PM for repair attempt #1
    state.update(step1_res)
    assert route_after_pm_validator(state) == "pm"

    # Step 2: PM repairs specs on Attempt #1 based on CEP feedback
    state["specifications"] = make_valid_pm_specs("CLI", "python")
    state["contract"] = make_valid_contract("CLI_TOOL")
    
    # Step 3: Revalidation on Attempt #1 -> PASS
    step2_res = pm_validator_node(state)
    assert step2_res["pm_validator_contract"]["verdict"] == "PASS"
    state.update(step2_res)
    
    # Check routing: advances to Architect
    assert route_after_pm_validator(state) == "architect"


# ==============================================================================
# 7. Repair-Success Attempt 2
# ==============================================================================

def test_dim7_repair_success_attempt_2():
    state = {
        "task": "Buat service autentikasi token.",
        "target_language": "python",
        "specifications": "Spesifikasi pendek awal.",
        "contract": {},
        "repair_attempt_counts": {"pm": 0},
    }

    # Attempt 0 -> FAIL -> count becomes 1
    s1 = pm_validator_node(state)
    assert s1["pm_validator_contract"]["verdict"] == "FAIL"
    assert s1["repair_attempt_counts"]["pm"] == 1
    state.update(s1)
    assert route_after_pm_validator(state) == "pm"

    # Attempt 1 -> Still fails (missing AC) -> count becomes 2
    state["specifications"] = (
        "1. Ringkasan Sistem: Modul token auth.\n"
        "2. User Stories: Sebagai user saya ingin login dengan token."
    )
    s2 = pm_validator_node(state)
    assert s2["pm_validator_contract"]["verdict"] == "FAIL"
    assert s2["repair_attempt_counts"]["pm"] == 2
    state.update(s2)
    assert route_after_pm_validator(state) == "pm"

    # Attempt 2 -> Successfully repaired
    state["specifications"] = make_valid_pm_specs("REST", "python")
    state["contract"] = make_valid_contract("REST_API")
    s3 = pm_validator_node(state)
    assert s3["pm_validator_contract"]["verdict"] == "PASS"
    state.update(s3)
    assert route_after_pm_validator(state) == "architect"


# ==============================================================================
# 8. Terminal Failure After Attempt 2 Exhaustion (Zero Downstream Leakage)
# ==============================================================================

def test_dim8_terminal_failure_after_attempt_exhaustion():
    state = {
        "task": "Buat modul parser.",
        "target_language": "python",
        "specifications": "Teks rusak.",
        "contract": {},
        "repair_attempt_counts": {"pm": 2},  # Already exhausted max 2 repairs
    }

    res = pm_validator_node(state)
    assert res["pm_validator_contract"]["verdict"] == "FAIL"
    assert res.get("status") == "terminal_failure_pm_boundary"
    
    state.update(res)
    next_node = route_after_pm_validator(state)
    
    # Must abort immediately to END, zero downstream leakage to architect
    assert next_node == END


# ==============================================================================
# 9. Mission-Diverse Generality Verification
# ==============================================================================

@pytest.mark.parametrize("domain,lang,user_task", [
    ("CLI", "python", "Buat CLI calculator operasi aritmatika."),
    ("REST_API", "python", "Buat FastAPI REST endpoint inventaris barang."),
    ("ALGORITHM", "python", "Buat algoritma graf Dijkstra pathfinding."),
    ("FLUTTER_WIDGET", "dart", "Buat Flutter Widget CardMetric indikator status."),
    ("DATA_PIPELINE", "python", "Buat pipeline ETL transformasi data stream."),
])
def test_dim9_mission_diverse_generality(domain, lang, user_task):
    """
    Verifies that the same general validation mechanism passes diverse missions
    without any domain-specific hardcoded keywords.
    """
    state = {
        "task": user_task,
        "target_language": lang,
        "specifications": make_valid_pm_specs(domain, lang),
        "contract": make_valid_contract(domain),
    }
    result = validate_pm_phase(state)
    assert result["verdict"] == "PASS", f"Failed for domain {domain} with violations: {result['violations']}"
    assert len(result["violations"]) == 0
    assert result["confidence"] == 1.0
