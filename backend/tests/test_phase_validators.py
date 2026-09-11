"""
Unit Tests for Phase-End & Iteration Validators
ReinDev Studio — Iterasi 6 (Phase-End Validation Pilot)
"""

import pytest
from backend.phase_validators import (
    validate_pm_phase,
    validate_architect_phase,
    validate_developer_phase,
    validate_oracle_phase,
    validate_executor_phase,
    validate_reviewer_phase,
    scan_code_symbols,
    validate_dart_syntax_structural
)


def test_pm_phase_validator_valid():
    state = {
        "specifications": (
            "1. Ringkasan Sistem: Modul kalkulator sederhana.\n"
            "2. User Stories: Sebagai pengguna saya ingin menjumlahkan angka.\n"
            "3. Acceptance Criteria: Skenario 1: input 2 dan 3 menghasilkan 5."
        ),
        "contract": {
            "task_intent": {"domain": "CLI_TOOL"},
            "requirements": [{"req_id": "REQ-01"}]
        }
    }
    result = validate_pm_phase(state)
    assert result["phase"] == "PM"
    assert result["validator_type"] == "PHASE_END"
    assert result["verdict"] == "PASS"
    assert len(result["violations"]) == 0


def test_pm_phase_validator_empty_fails():
    state = {
        "specifications": "",
        "contract": {}
    }
    result = validate_pm_phase(state)
    assert result["verdict"] == "FAIL"
    assert any(v["criterion"] == "specifications_present" for v in result["violations"])


def test_architect_phase_validator_valid():
    state = {
        "architecture_plan": (
            "File Tree:\n=== FILE: main.py ===\ndef add(a: int, b: int) -> int:\n    return a + b\n=== END FILE ==="
        ),
        "contract": {
            "interface_contracts": [{"identifier": "add", "target_file": "main.py"}]
        },
        "contract_status": "FROZEN",
        "contract_sha256": "a" * 64,
        "target_language": "python"
    }
    result = validate_architect_phase(state)
    assert result["phase"] == "ARCHITECT"
    assert result["validator_type"] == "PHASE_END"
    assert result["verdict"] == "PASS"


def test_architect_phase_validator_not_frozen_fails():
    state = {
        "architecture_plan": "Valid plan with sufficient characters to pass length check easily.",
        "contract": {"interface_contracts": [{"identifier": "run"}]},
        "contract_status": "ALIGNED",
        "contract_sha256": "",
        "target_language": "python"
    }
    result = validate_architect_phase(state)
    assert result["verdict"] == "FAIL"
    assert any(v["criterion"] == "contract_frozen_status" for v in result["violations"])


def test_developer_phase_validator_valid():
    state = {
        "code_files": {
            "main.py": (
                "class Product:\n"
                "    def __init__(self, name: str):\n"
                "        self.name = name\n\n"
                "def get_product(id: int) -> Product:\n"
                "    return Product('test')\n"
            )
        },
        "contract": {
            "task_intent": {"authoritative_target_file": "main.py"},
            "data_models": [{"model_name": "Product"}],
            "interface_contracts": [{"identifier": "get_product", "target_file": "main.py"}],
            "constraints": {"max_files": 2}
        },
        "target_language": "python",
        "iteration_count": 0,
        "max_iterations": 10
    }
    result = validate_developer_phase(state)
    assert result["phase"] == "DEVELOPER"
    assert result["validator_type"] == "PHASE_END"
    assert result["verdict"] == "PASS"


def test_developer_phase_validator_syntax_error_fails():
    state = {
        "code_files": {
            "main.py": "def broken_syntax(\n"
        },
        "contract": {
            "task_intent": {"authoritative_target_file": "main.py"}
        },
        "target_language": "python",
        "iteration_count": 1,
        "max_iterations": 10
    }
    result = validate_developer_phase(state)
    assert result["verdict"] == "FAIL"
    assert any(v["criterion"] == "ast_syntax_validity" for v in result["violations"])
    assert result["repair_owner"] == "DEVELOPER"
    assert result["remaining_budget"] == 9


def test_developer_phase_validator_wrong_target_file_fails():
    state = {
        "code_files": {
            "app.py": "print('hello')"
        },
        "contract": {
            "task_intent": {"authoritative_target_file": "main.py"}
        },
        "target_language": "python",
        "iteration_count": 0,
        "max_iterations": 10
    }
    result = validate_developer_phase(state)
    assert result["verdict"] == "FAIL"
    assert any(v["criterion"] == "authoritative_target_file_compliance" for v in result["violations"])


def test_developer_phase_validator_dart_syntax():
    valid_dart = "class CardMetric extends StatelessWidget { Widget build(BuildContext context) { return Container(); } }"
    is_valid, errs = validate_dart_syntax_structural(valid_dart)
    assert is_valid is True

    invalid_dart = "class CardMetric { Widget build(BuildContext context) { return Container(; } }"
    is_valid_inv, errs_inv = validate_dart_syntax_structural(invalid_dart)
    assert is_valid_inv is False


def test_oracle_phase_validator_valid():
    state = {
        "test_files": {"test_main.py": "def test_ok(): pass\n"},
        "frozen_oracle_path": "some/path"
    }
    import hashlib
    sha = hashlib.sha256("def test_ok(): pass\n".encode("utf-8")).hexdigest()
    result = validate_oracle_phase(state, expected_sha=sha)
    assert result["phase"] == "ORACLE"
    assert result["validator_type"] == "PHASE_END"
    assert result["verdict"] == "PASS"


def test_oracle_phase_validator_hash_mismatch_fails():
    state = {
        "test_files": {"test_main.py": "def test_ok(): pass\n"},
        "frozen_oracle_path": "some/path"
    }
    result = validate_oracle_phase(state, expected_sha="deadbeef" * 8)
    assert result["verdict"] == "FAIL"
    assert any(v["criterion"] == "oracle_sha256_checksum_verified" for v in result["violations"])


def test_executor_iteration_validator_pass():
    state = {
        "test_results": {
            "passed": True,
            "exit_code": 0,
            "passed_count": 5,
            "failed_count": 0,
            "total": 5,
            "passed_test_names": ["t1", "t2", "t3", "t4", "t5"]
        },
        "iteration_count": 0,
        "max_iterations": 10
    }
    result = validate_executor_phase(state, previous_passed_tests=["t1", "t2"])
    assert result["phase"] == "EXECUTOR"
    assert result["validator_type"] == "ITERATION"
    assert result["verdict"] == "PASS"


def test_executor_iteration_validator_regression_fails():
    state = {
        "test_results": {
            "passed": False,
            "exit_code": 1,
            "passed_count": 1,
            "failed_count": 1,
            "total": 2,
            "passed_test_names": ["t1"]
        },
        "iteration_count": 1,
        "max_iterations": 10
    }
    # t2 was passed in previous loop, now missing in passed_test_names
    result = validate_executor_phase(state, previous_passed_tests=["t1", "t2"])
    assert result["verdict"] == "FAIL"
    assert len(result["regressions"]) == 1
    assert result["regressions"][0]["test_or_invariant"] == "t2"


def test_reviewer_phase_validator_approved_valid():
    state = {
        "test_results": {"passed": True, "exit_code": 0},
        "contract_status": "FROZEN",
        "iteration_count": 2,
        "max_iterations": 10
    }
    result = validate_reviewer_phase(state, review_verdict="APPROVED", review_notes="Audit PASS: All tests pass")
    assert result["phase"] == "REVIEWER"
    assert result["validator_type"] == "PHASE_END"
    assert result["verdict"] == "PASS"
    assert result["evaluated_review_verdict"] == "APPROVED"


def test_reviewer_phase_validator_false_approval_fails():
    state = {
        "test_results": {"passed": False, "exit_code": 1},
        "contract_status": "FROZEN",
        "iteration_count": 2,
        "max_iterations": 10
    }
    # Reviewer gives APPROVED even though tests failed
    result = validate_reviewer_phase(state, review_verdict="APPROVED", review_notes="Looks fine to me")
    assert result["verdict"] == "FAIL"
    assert any(v["criterion"] == "review_approval_integrity" for v in result["violations"])


def test_reviewer_phase_validator_needs_revision_developer():
    state = {
        "test_results": {"passed": False, "exit_code": 1},
        "contract_status": "FROZEN",
        "iteration_count": 3,
        "max_iterations": 10
    }
    result = validate_reviewer_phase(state, review_verdict="NEEDS_REVISION", review_notes="Perbaiki bug pada kalkulasi diskon")
    assert result["verdict"] == "PASS"
    assert result["repair_owner"] == "DEVELOPER"
    assert result["remaining_budget"] == 7


def test_reviewer_phase_validator_unfreeze_contract_attempt_fails():
    state = {
        "test_results": {"passed": False, "exit_code": 1},
        "contract_status": "FROZEN",
        "iteration_count": 3,
        "max_iterations": 10
    }
    # Reviewer attempts to demand contract unfreeze
    result = validate_reviewer_phase(state, review_verdict="NEEDS_REVISION", review_notes="Tolong ubah kontrak dan unfreeze endpoint")
    assert result["verdict"] == "FAIL"
    assert any(v["criterion"] == "frozen_contract_immutability" for v in result["violations"])
