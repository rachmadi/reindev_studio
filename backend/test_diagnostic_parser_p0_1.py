"""
Unit Test Suite: P0-1 Semantic Diagnostic Guidance
ReinDev Studio — Work Order P0-1 Verification

Menguji seluruh klausul persyaratan Work Order:
1. HTTP 422 status code -> semantic hint muncul.
2. 'Unprocessable Entity' / 'Unprocessable Content' -> hint yang sama muncul.
3. Hint secara eksplisit memandu request/schema validation & field check.
4. Hint TIDAK PERNAH meng-hard-code solusi 'Optional[int] = None' atau solusi kode preskriptif.
5. Dimension mismatch & incompatible dimensions -> hint dimensional validation muncul.
6. ValueError pada operasi matriks ("DID NOT RAISE ValueError") -> hint dimensional validation muncul.
7. Error yang tidak dikenal (misal: ZeroDivisionError, general assertion) -> semantic_hint is None (tanpa hint palsu).
8. Raw error & traceback excerpt tetap dipertahankan 100% pada targeted feedback.
9. Audit Kriptografis Frozen Oracle SHA-256 intak dan tidak berubah.
"""

import hashlib
from pathlib import Path
import pytest

from backend.diagnostic_parser import (
    DiagnosticEvidence,
    FailingTest,
    infer_semantic_hint,
    build_targeted_feedback,
    parse_pytest_output,
    HINT_HTTP_422,
    HINT_MATRIX_DIMENSIONS,
    HINT_DART_BRACKET_CASCADE,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ORACLE_BASE = PROJECT_ROOT / "dokumentasi-pengembangan/experiments/frozen_oracle"

FROZEN_ORACLES = [
    {
        "task_id": "fastapi_t1",
        "path": ORACLE_BASE / "fastapi_t1" / "test_main.py",
        "expected_sha": "a1db9bb1f6eaf47d5cf56e102c4a0f6e1f49d757e9faa1485b36f2972a152d63"
    },
    {
        "task_id": "cli_t1",
        "path": ORACLE_BASE / "cli_t1" / "test_main.py",
        "expected_sha": "0bd5b598afa7ae4c9cdf0e269d13136b51d35a4e0b1ac6548f0a2cf8a8eba124"
    },
    {
        "task_id": "flutter_t1",
        "path": ORACLE_BASE / "flutter_t1" / "card_metric_test.dart",
        "expected_sha": "4589e15cfb8f37ba70642e70623ca143bceee1a44175aefd072f441d9e8a9528"
    }
]


# ===========================================================================
# 1. HTTP 422 Detection & Semantic Hint
# ===========================================================================

def test_semantic_hint_http_422_status_code():
    """HTTP 422 pada actual/message memicu petunjuk semantik HTTP 422."""
    test = FailingTest(
        test_name="test_create_product",
        test_file="test_main.py",
        test_line=15,
        failure_type="assertion_failure",
        message="assert 422 == 201",
        expected="201",
        actual="422",
        traceback_excerpt="> assert response.status_code == 201\nE assert 422 == 201"
    )
    hint = infer_semantic_hint(test)
    assert hint is not None
    assert "[ACTIONABLE HINT]" in hint
    assert "HTTP 422" in hint
    assert hint == HINT_HTTP_422


def test_semantic_hint_unprocessable_entity_text():
    """Teks 'Unprocessable Entity' atau 'Unprocessable Content' memicu hint HTTP 422."""
    test1 = FailingTest(
        test_name="test_create_item",
        test_file="test_main.py",
        test_line=20,
        failure_type="assertion_failure",
        message="assert res.status_code == 201",
        traceback_excerpt="where 422 = <Response [422 Unprocessable Content]>.status_code"
    )
    hint1 = infer_semantic_hint(test1)
    assert hint1 == HINT_HTTP_422

    test2 = FailingTest(
        test_name="test_create_item_entity",
        test_file="test_main.py",
        test_line=25,
        failure_type="assertion_failure",
        message="Response [422 Unprocessable Entity]",
    )
    hint2 = infer_semantic_hint(test2)
    assert hint2 == HINT_HTTP_422


# ===========================================================================
# 2. Content Quality & Anti-Solution-Leak Assertions
# ===========================================================================

def test_semantic_hint_schema_validation_content():
    """Hint HTTP 422 memandu inspeksi schema validation, required fields, dan default."""
    hint = HINT_HTTP_422
    assert "request validation failure" in hint
    assert "Pydantic schema" in hint
    assert "required field(s)" in hint
    assert "optional or have defaults" in hint


def test_semantic_hint_no_hardcoded_solution():
    """Hint HTTP 422 TIDAK PERNAH membocorkan 'Optional[int] = None' atau solusi kode preskriptif."""
    assert "Optional[int] = None" not in HINT_HTTP_422
    assert "id: Optional" not in HINT_HTTP_422
    assert "def " not in HINT_HTTP_422
    assert "class " not in HINT_HTTP_422


# ===========================================================================
# 3. CLI / Matrix Dimensional Validation Hints
# ===========================================================================

def test_semantic_hint_dimension_mismatch():
    """Error dimensional mismatch memicu petunjuk validasi dimensi matriks."""
    test = FailingTest(
        test_name="test_matrix_multiplication_dimension_mismatch",
        test_file="test_main.py",
        test_line=45,
        failure_type="runtime_exception",
        message="ValueError: Incompatible dimensions for matrix multiplication: (2, 3) and (2, 2)",
    )
    hint = infer_semantic_hint(test)
    assert hint is not None
    assert "[ACTIONABLE HINT]" in hint
    assert "incompatible matrix dimensions" in hint
    assert "dimensionality/shape validation" in hint
    assert hint == HINT_MATRIX_DIMENSIONS


def test_semantic_hint_did_not_raise_valueerror():
    """Pytest DID NOT RAISE ValueError pada tes dimensi memicu hint dimensional validation."""
    test = FailingTest(
        test_name="test_matrix_addition_incompatible_dimensions",
        test_file="test_main.py",
        test_line=50,
        failure_type="assertion_failure",
        message="Failed: DID NOT RAISE <class 'ValueError'>",
        traceback_excerpt="> with pytest.raises(ValueError):\nE Failed: DID NOT RAISE ValueError"
    )
    hint = infer_semantic_hint(test)
    assert hint is not None
    assert hint == HINT_MATRIX_DIMENSIONS


def test_semantic_hint_no_hardcoded_matrix_code():
    """Hint matriks TIDAK PERNAH membocorkan implementasi fungsi matriks."""
    assert "def add_matrices" not in HINT_MATRIX_DIMENSIONS
    assert "def multiply_matrices" not in HINT_MATRIX_DIMENSIONS
    assert "__add__" not in HINT_MATRIX_DIMENSIONS
    assert "__matmul__" not in HINT_MATRIX_DIMENSIONS


# ===========================================================================
# 4. Unknown Error & No False Positive Hints
# ===========================================================================

def test_semantic_hint_unknown_error_no_false_hint():
    """Error generik tanpa pola semantik yang dikenali mengembalikan None (tanpa hint palsu)."""
    generic_test = FailingTest(
        test_name="test_simple_calculation",
        test_file="test_main.py",
        test_line=10,
        failure_type="assertion_failure",
        message="assert 1 == 2",
        expected="2",
        actual="1",
        traceback_excerpt="> assert result == 2\nE assert 1 == 2"
    )
    assert infer_semantic_hint(generic_test) is None

    zero_div_test = FailingTest(
        test_name="test_divide",
        test_file="test_main.py",
        test_line=12,
        failure_type="runtime_exception",
        message="ZeroDivisionError: division by zero",
    )
    assert infer_semantic_hint(zero_div_test) is None


# ===========================================================================
# 5. Raw Error & Traceback Preservation in Feedback
# ===========================================================================

def test_raw_error_and_trace_preserved_in_feedback():
    """Pesan galat mentah dan cuplikan traceback tetap utuh berdampingan dengan hint."""
    test = FailingTest(
        test_name="test_create_product",
        test_file="test_main.py",
        test_line=15,
        failure_type="assertion_failure",
        message="assert 422 == 201",
        expected="201",
        actual="422",
        traceback_excerpt="> assert response.status_code == 201\nE assert 422 == 201"
    )
    evidence = DiagnosticEvidence(
        execution_status="failed",
        framework="pytest",
        total_tests=1,
        passed_tests=0,
        failed_tests=1,
        primary_failure_category="assertion_failure",
        failing_tests=[test]
    )

    feedback = build_targeted_feedback(evidence, iteration=1, max_iterations=3)

    # 1. Raw error details tetap ada
    assert "assert 422 == 201" in feedback
    assert "Ekspektasi Pengujian: 201" in feedback
    assert "Hasil Aktual: 422" in feedback
    assert "> assert response.status_code == 201" in feedback

    # 2. Actionable hint hadir terpisah
    assert "[ACTIONABLE HINT]" in feedback
    assert "HTTP 422 indicates request validation failure" in feedback


# ===========================================================================
# 6. Full Integration with parse_pytest_output
# ===========================================================================

def test_parse_pytest_output_attaches_semantic_hint():
    """parse_pytest_output secara otomatis menempelkan semantic_hint pada FailingTest."""
    stdout_422 = """
============================= test session starts =============================
collected 1 item

test_main.py::test_create_product FAILED

================================== FAILURES ===================================
_____________________________ test_create_product _____________________________

    def test_create_product():
        res = client.post("/products", json={"name": "Book"})
>       assert res.status_code == 201
E       assert 422 == 201
E        +  where 422 = <Response [422 Unprocessable Content]>.status_code

test_main.py:15: AssertionError
=========================== short test summary info ===========================
FAILED test_main.py::test_create_product - assert 422 == 201
============================== 1 failed in 0.10s ==============================
"""
    evidence = parse_pytest_output(stdout_422, exit_code=1)
    assert len(evidence.failing_tests) == 1
    t = evidence.failing_tests[0]
    assert t.semantic_hint is not None
    assert "[ACTIONABLE HINT]" in t.semantic_hint
    assert "HTTP 422" in t.semantic_hint


# ===========================================================================
# 6.2. Dart Bracket Cascade Semantic Hint Tests
# ===========================================================================

def test_semantic_hint_dart_bracket_cascade():
    """Error kompilasi Dart cascade mismatch memicu HINT_DART_BRACKET_CASCADE."""
    test1 = FailingTest(
        test_name="compilation_check",
        test_file="test/widget_test.dart",
        failure_type="compilation_error",
        message="lib/card_metric.dart:60:20: Error: Can't find ')' to match '('.",
    )
    hint1 = infer_semantic_hint(test1)
    assert hint1 is not None
    assert hint1 == HINT_DART_BRACKET_CASCADE
    assert "[ACTIONABLE HINT]" in hint1
    assert "cascade errors" in hint1

    test2 = FailingTest(
        test_name="compilation_check",
        test_file="test/widget_test.dart",
        failure_type="compilation_error",
        message="lib/card_metric.dart:124:13: Error: Expected an identifier, but got ']'.",
    )
    hint2 = infer_semantic_hint(test2)
    assert hint2 == HINT_DART_BRACKET_CASCADE


def test_semantic_hint_no_hardcoded_widget_code():
    """Hint Dart bracket cascade TIDAK PERNAH membocorkan kode widget preskriptif."""
    assert "class CardMetric" not in HINT_DART_BRACKET_CASCADE
    assert "Card(" not in HINT_DART_BRACKET_CASCADE
    assert "Column(" not in HINT_DART_BRACKET_CASCADE


# ===========================================================================
# 7. Frozen Oracle Integrity Audit
# ===========================================================================

def test_frozen_oracle_integrity():
    """Memastikan SHA-256 seluruh berkas Frozen Oracle 100% utuh dan tidak tersentuh."""
    for oracle in FROZEN_ORACLES:
        p = Path(oracle["path"])
        assert p.exists(), f"Oracle file missing: {p}"
        sha = hashlib.sha256(p.read_bytes()).hexdigest()
        assert sha == oracle["expected_sha"], (
            f"CORRUPTED ORACLE {oracle['task_id']}: expected {oracle['expected_sha']}, got {sha}"
        )
