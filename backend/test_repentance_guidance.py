"""
Unit Tests for Improved Repentance & Diagnostic Guidance Engine
Verifies:
1. 7-step sequence: Actual Error, Root Cause, Affected Constraint, Required Direction, Preservation Rule, Previous Failed Attempt, Verification.
2. 6 Critical Rules: Root-cause aligned, Terminology aligned, Single-sin focus, Anti-destructive local repair, Remind previous failed attempts, Global re-evaluation.
3. Rehabilitation State integration in executor_v2 and diagnostic_parser.
"""

import pytest
from typing import Dict, Any, List
from backend.diagnostic_parser import (
    DiagnosticEvidence,
    FailingTest,
    infer_root_cause_and_direction,
    build_repentance_guidance,
    build_targeted_feedback,
    build_targeted_feedback_from_dict
)


# ===========================================================================
# 1. Deterministic Root Cause Inference Tests
# ===========================================================================

def test_infer_root_cause_dart_metricdata():
    t = FailingTest(
        test_name="test_card_metric",
        test_file="test/card_metric_test.dart",
        failure_type="compilation_error",
        message="Error: Method not found: 'MetricData'."
    )
    rc, ac, rd, pr = infer_root_cause_and_direction(t, framework="flutter test")
    assert "MetricData" in rc
    assert "CardMetric" in ac
    assert "Deklarasikan kelas 'MetricData'" in rd
    assert "Pertahankan nama kelas 'CardMetric'" in pr
    assert "DILARANG mengubah konstruktor" in pr


def test_infer_root_cause_dart_named_param():
    t = FailingTest(
        test_name="test_custom_badge",
        test_file="test/badge_test.dart",
        failure_type="compilation_error",
        message="Error: No named parameter with the name 'color'."
    )
    rc, ac, rd, pr = infer_root_cause_and_direction(t, framework="flutter test")
    assert "color" in rc
    assert "parameter" in ac.lower()
    assert "Tambahkan parameter bernama 'color'" in rd
    assert "Pertahankan seluruh parameter konstruktor" in pr


def test_infer_root_cause_dart_bracket_cascade():
    t = FailingTest(
        test_name="test_syntax",
        test_file="test/app_test.dart",
        failure_type="syntax_parse_error",
        message="Can't find '}' to match '{"
    )
    rc, ac, rd, pr = infer_root_cause_and_direction(t, framework="flutter test")
    assert "kurung" in rc.lower() or "bracket" in rc.lower()
    assert "Periksa dan hitung kesesuaian" in rd
    assert "Pertahankan" in pr


def test_infer_root_cause_python_field_validator():
    t = FailingTest(
        test_name="test_create_product",
        test_file="test_main.py",
        failure_type="runtime_exception",
        message="E   NameError: name 'field_validator' is not defined"
    )
    rc, ac, rd, pr = infer_root_cause_and_direction(t, framework="pytest")
    assert "field_validator" in rc
    assert "pydantic" in rc.lower()
    assert "from pydantic import BaseModel, field_validator" in rd
    assert "Pertahankan" in pr


def test_infer_root_cause_python_fastapi_app():
    t = FailingTest(
        test_name="test_read_root",
        test_file="test_main.py",
        failure_type="runtime_exception",
        message="E   NameError: name 'app' is not defined"
    )
    rc, ac, rd, pr = infer_root_cause_and_direction(t, framework="pytest")
    assert "app" in rc
    assert "FastAPI" in rc or "fastapi" in rd.lower()
    assert "app = FastAPI()" in rd
    assert "Pertahankan" in pr


def test_infer_root_cause_http_422():
    t = FailingTest(
        test_name="test_post_product",
        test_file="test_main.py",
        failure_type="assertion_failure",
        message="assert 422 == 201"
    )
    rc, ac, rd, pr = infer_root_cause_and_direction(t, framework="pytest")
    assert "422" in rc
    assert "skema" in ac.lower() or "dto" in ac.lower()
    assert "Periksa field-field DTO" in rd
    assert "Pertahankan path routing" in pr


def test_infer_root_cause_matrix_dimension():
    t = FailingTest(
        test_name="test_matrix_multiply",
        test_file="test_main.py",
        failure_type="assertion_failure",
        message="ValueError: Matrix dimension mismatch for multiplication (2x3 and 2x2)"
    )
    rc, ac, rd, pr = infer_root_cause_and_direction(t, framework="pytest")
    assert "dimensi" in rc.lower() or "matriks" in rc.lower()
    assert "Matrix" in ac
    assert "ValueError" in rd
    assert "Pertahankan nama kelas 'Matrix'" in pr


# ===========================================================================
# 2. 7-Step Sequence & Rule 5 / Rule 6 Warning Tests
# ===========================================================================

def test_build_repentance_guidance_7_steps():
    t = FailingTest(
        test_name="test_example",
        test_file="test_main.py",
        failure_type="assertion_failure",
        message="assert 'expected' == 'actual'",
        expected="'expected'",
        actual="'actual'"
    )
    ev = DiagnosticEvidence(
        execution_status="failed",
        framework="pytest",
        total_tests=1,
        passed_tests=0,
        failed_tests=1,
        failing_tests=[t]
    )

    guidance = build_repentance_guidance(ev, iteration=1, max_iterations=10)

    # Verifikasi 7 langkah ada secara lengkap
    assert "1. [ACTUAL ERROR]" in guidance
    assert "2. [ROOT CAUSE]" in guidance
    assert "3. [AFFECTED CONSTRAINT]" in guidance
    assert "4. [REQUIRED DIRECTION]" in guidance
    assert "5. [PRESERVATION RULE]" in guidance
    assert "6. [PREVIOUS FAILED ATTEMPT]" in guidance
    assert "7. [VERIFICATION - CEK MANDIRI SEBELUM OUTPUT]" in guidance

    # Verifikasi checklist mandiri
    assert "- [ ]" in guidance
    assert "bebas regresi" in guidance


def test_rule_5_stagnation_warning():
    t = FailingTest(
        test_name="test_field_validator",
        test_file="test_main.py",
        failure_type="runtime_exception",
        message="NameError: name 'field_validator' is not defined"
    )
    ev = DiagnosticEvidence(
        execution_status="failed",
        framework="pytest",
        total_tests=3,
        passed_tests=0,
        failed_tests=3,
        failing_tests=[t]
    )

    # Simulasi loop 2 dengan riwayat kegagalan yang sama persis
    history = [
        {
            "loop": 1,
            "code_hash": "a1b2c3d4e5f60000",
            "result": "STAGNANT",
            "test_passed_count": 0,
            "error_message": "NameError: name 'field_validator' is not defined"
        }
    ]

    guidance = build_repentance_guidance(ev, iteration=2, max_iterations=10, repair_history=history)

    assert "PERINGATAN REPETISI / STAGNASI" in guidance
    assert "Loop 1" in guidance
    assert "DILARANG mengulangi kode atau pola yang sama persis" in guidance


def test_rule_6_regression_warning():
    t = FailingTest(
        test_name="test_regression",
        test_file="test_main.py",
        failure_type="assertion_failure",
        message="assert 1 == 2"
    )
    ev = DiagnosticEvidence(
        execution_status="failed",
        framework="pytest",
        total_tests=5,
        passed_tests=2,
        failed_tests=3,
        failing_tests=[t]
    )

    # Simulasi loop 2 dengan regresi (sebelumnya 4 passed, sekarang 2 passed)
    history = [
        {
            "loop": 1,
            "code_hash": "abc12345",
            "result": "REGRESSED",
            "test_passed_count": 4,
            "error_message": "Some minor assertion"
        }
    ]

    guidance = build_repentance_guidance(ev, iteration=2, max_iterations=10, repair_history=history)

    assert "PERINGATAN REGRESI" in guidance
    assert "Loop 1" in guidance
    assert "4 passed -> 2 passed" in guidance


def test_positive_progress_guidance():
    t = FailingTest(
        test_name="test_remaining",
        test_file="test_main.py",
        failure_type="assertion_failure",
        message="assert False is True"
    )
    ev = DiagnosticEvidence(
        execution_status="failed",
        framework="pytest",
        total_tests=5,
        passed_tests=4,
        failed_tests=1,
        failing_tests=[t]
    )

    history = [
        {
            "loop": 1,
            "code_hash": "abc12345",
            "result": "IMPROVED",
            "test_passed_count": 2,
            "error_message": "Some previous failure"
        }
    ]

    guidance = build_repentance_guidance(ev, iteration=2, max_iterations=10, repair_history=history)

    assert "PROGRES POSITIF" in guidance
    assert "Loop 1" in guidance
    assert "4/5 passed" in guidance


# ===========================================================================
# 3. Integration with build_targeted_feedback & build_targeted_feedback_from_dict
# ===========================================================================

def test_build_targeted_feedback_includes_repentance():
    t = FailingTest(
        test_name="test_product_flow",
        test_file="test_main.py",
        failure_type="runtime_exception",
        message="NameError: name 'field_validator' is not defined"
    )
    ev = DiagnosticEvidence(
        execution_status="failed",
        framework="pytest",
        total_tests=2,
        passed_tests=0,
        failed_tests=2,
        primary_failure_category="runtime_exception",
        failing_tests=[t]
    )

    feedback = build_targeted_feedback(ev, iteration=1, max_iterations=10)

    # Harus mengandung header targeted evidence DAN repentance guidance
    assert "[TARGETED DIAGNOSTIC EVIDENCE" in feedback
    assert "[IMPROVED REPENTANCE GUIDANCE" in feedback
    assert "[ACTUAL ERROR]" in feedback
    assert "[ROOT CAUSE]" in feedback
    assert "[REQUIRED DIRECTION]" in feedback


def test_build_targeted_feedback_from_dict_with_history():
    ev_dict = {
        "execution_status": "failed",
        "framework": "pytest",
        "total_tests": 2,
        "passed_tests": 1,
        "failed_tests": 1,
        "primary_failure_category": "assertion_failure",
        "failing_tests": [
            {
                "test_name": "test_add",
                "test_file": "test_calc.py",
                "failure_type": "assertion_failure",
                "message": "assert 3 == 4"
            }
        ]
    }

    history = [
        {"loop": 1, "result": "IMPROVED", "test_passed_count": 1, "error_message": "assert 3 == 4"}
    ]

    feedback = build_targeted_feedback_from_dict(
        ev_dict,
        iteration=2,
        max_iterations=10,
        repair_history=history
    )

    assert "[IMPROVED REPENTANCE GUIDANCE" in feedback
    assert "PROGRES POSITIF" in feedback or "Loop 1" in feedback
