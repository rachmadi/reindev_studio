"""
Suite Pengujian Komprehensif P0-1: Structured Diagnostic Parser & Targeted Error Feedback
ReinDev Studio — Unit & Integration Tests

Menguji 16 aspek inti sesuai spesifikasi desain v1.0.0:
1. Pytest assertion failure
2. Pytest syntax error
3. Pytest import error
4. Pytest collection error
5. Runtime exception
6. Dart compilation error
7. Dart assertion failure
8. Expected vs actual extraction & anti-hallucination
9. Source and test location extraction (Bottom-Up Frame Scanner)
10. Top-3 multi-failure prioritization & omitted summary
11. ANSI stripping & environment noise sanitization
12. Fallback parser (Level 1 Partial & Level 2 Total)
13. Immutability code_files
14. Immutability test_files
15. Raw evidence preservation
16. Developer receives targeted feedback, not raw dump
17. Real Phase 2 trace fixture validation
"""

import json
import copy
from pathlib import Path
import pytest

from backend.diagnostic_parser import (
    DiagnosticEvidence,
    FailingTest,
    strip_ansi,
    extract_environment_warnings,
    parse_pytest_output,
    parse_dart_output,
    prioritize_failures,
    build_targeted_feedback,
    build_targeted_feedback_from_dict,
    parse_diagnostic,
    TAXONOMY_PRIORITY
)
from backend.tracer import compute_dict_hashes, compute_sha256
from backend.agents.developer import developer_agent


# ===========================================================================
# 1. Pytest Assertion Failure Test
# ===========================================================================

def test_pytest_assertion_parsing():
    sample_stdout = """
============================= test session starts =============================
collected 3 items

test_main.py::test_create_product PASSED
test_main.py::test_get_all_products FAILED
test_main.py::test_delete_product PASSED

================================== FAILURES ===================================
____________________________ test_get_all_products ____________________________

    def test_get_all_products():
        res = client.get("/products")
>       assert res.status_code == 200
E       assert 405 == 200
E        +  where 405 = <Response [405 Method Not Allowed]>.status_code

test_main.py:28: AssertionError
=========================== short test summary info ===========================
FAILED test_main.py::test_get_all_products - assert 405 == 200
========================= 1 failed, 2 passed in 0.25s =========================
"""
    evidence = parse_pytest_output(sample_stdout, exit_code=1, duration_sec=0.25)

    assert evidence.execution_status == "failed"
    assert evidence.framework == "pytest"
    assert evidence.total_tests == 3
    assert evidence.passed_tests == 2
    assert evidence.failed_tests == 1
    assert evidence.primary_failure_category == "assertion_failure"
    assert len(evidence.failing_tests) == 1

    t = evidence.failing_tests[0]
    assert t.test_name == "test_get_all_products"
    assert t.test_file == "test_main.py"
    assert t.test_line == 28
    assert t.failure_type == "assertion_failure"
    assert t.expected == "200"
    assert t.actual == "405"
    assert "assert 405 == 200" in t.message


# ===========================================================================
# 2. Pytest Syntax Error Test
# ===========================================================================

def test_pytest_syntax_error_parsing():
    sample_stdout = """
============================= test session starts =============================
collected 1 item

test_main.py F

================================== FAILURES ===================================
________________________________ test_syntax __________________________________

    def test_syntax():
>       import main
E         File "main.py", line 12
E           def broken_syntax(
E                            ^
E       SyntaxError: '(' was never closed

test_main.py:10: SyntaxError
=========================== short test summary info ===========================
FAILED test_main.py::test_syntax - SyntaxError: '(' was never closed
============================== 1 failed in 0.10s ===============================
"""
    evidence = parse_pytest_output(sample_stdout, exit_code=1, duration_sec=0.10)

    assert evidence.primary_failure_category == "syntax_parse_error"
    assert len(evidence.failing_tests) == 1
    t = evidence.failing_tests[0]
    assert t.failure_type == "syntax_parse_error"
    assert "SyntaxError" in t.message


# ===========================================================================
# 3. Pytest Import Error Test
# ===========================================================================

def test_pytest_import_error_parsing():
    sample_stdout = """
============================= test session starts =============================
collected 1 item

test_main.py F

================================== FAILURES ===================================
_________________________________ test_import _________________________________

    def test_import():
>       import nonexistent_module
E       ModuleNotFoundError: No module named 'nonexistent_module'

test_main.py:5: ModuleNotFoundError
=========================== short test summary info ===========================
FAILED test_main.py::test_import - ModuleNotFoundError: No module named 'nonexistent_module'
============================== 1 failed in 0.08s ===============================
"""
    evidence = parse_pytest_output(sample_stdout, exit_code=1, duration_sec=0.08)

    assert evidence.primary_failure_category == "import_module_error"
    assert len(evidence.failing_tests) == 1
    t = evidence.failing_tests[0]
    assert t.failure_type == "import_module_error"
    assert "ModuleNotFoundError" in t.message


# ===========================================================================
# 4. Pytest Collection Error Test
# ===========================================================================

def test_pytest_collection_error_parsing():
    sample_stdout = """
============================= test session starts =============================
collecting ... 
=================================== ERRORS ====================================
________________ ERROR collecting test_suite.py ________________
ImportError while importing test module 'test_suite.py'.
Traceback:
test_suite.py:2: in <module>
    import missing_package
E   ModuleNotFoundError: No module named 'missing_package'
=========================== short test summary info ===========================
ERROR test_suite.py
!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
============================== 1 error in 0.15s ===============================
"""
    evidence = parse_pytest_output(sample_stdout, exit_code=2, duration_sec=0.15)

    assert evidence.execution_status == "error"
    assert evidence.error_count >= 1
    assert evidence.primary_failure_category in ("import_module_error", "collection_test_discovery_error")
    assert len(evidence.failing_tests) >= 1
    assert "missing_package" in evidence.failing_tests[0].message or "test_suite.py" in evidence.failing_tests[0].test_file


# ===========================================================================
# 5. Runtime Exception Test
# ===========================================================================

def test_runtime_exception_parsing():
    sample_stdout = """
============================= test session starts =============================
collected 1 item

test_main.py F

================================== FAILURES ===================================
_____________________________ test_divide_by_zero _____________________________

    def test_divide_by_zero():
>       res = 10 / 0
E       ZeroDivisionError: division by zero

test_main.py:15: ZeroDivisionError
=========================== short test summary info ===========================
FAILED test_main.py::test_divide_by_zero - ZeroDivisionError: division by zero
============================== 1 failed in 0.05s ===============================
"""
    evidence = parse_pytest_output(sample_stdout, exit_code=1, duration_sec=0.05)

    assert evidence.primary_failure_category == "runtime_exception"
    assert len(evidence.failing_tests) == 1
    t = evidence.failing_tests[0]
    assert t.failure_type == "runtime_exception"
    assert "ZeroDivisionError" in t.message


# ===========================================================================
# 6. Dart Compilation Error Test
# ===========================================================================

def test_dart_compilation_error_parsing():
    sample_stderr = """
lib/card_metric.dart:14:28: Error: Method not found: 'StateProvider'.
final metricDataProvider = StateProvider<MetricData>((ref) {
                           ^^^^^^^^^^^^^
test/card_metric_test.dart:14:32: Error: No named parameter with the name 'title'.
              data: MetricData(title: 'Revenue', value: '1000', color: Colors.blue),
                               ^^^^^
"""
    sample_stdout = "00:00 +0 -1: Some tests failed."

    evidence = parse_dart_output(sample_stdout, stderr=sample_stderr, exit_code=1, duration_sec=1.1)

    assert evidence.execution_status == "error"
    assert evidence.framework == "flutter test"
    assert evidence.primary_failure_category == "compilation_error"
    assert len(evidence.failing_tests) == 2

    t1 = evidence.failing_tests[0]
    assert t1.failure_type == "compilation_error"
    assert t1.source_file == "lib/card_metric.dart"
    assert t1.source_line == 14
    assert "StateProvider" in t1.message

    t2 = evidence.failing_tests[1]
    assert t2.failure_type == "compilation_error"
    assert t2.test_file == "test/card_metric_test.dart"
    assert t2.test_line == 14
    assert "title" in t2.message


# ===========================================================================
# 7. Dart Assertion Test
# ===========================================================================

def test_dart_assertion_parsing():
    sample_stdout = """
00:01 +1 -1: Counter displays correct initial value [E]
  Expected: <200>
    Actual: <404>
     Which: was <404> instead of <200>

00:01 +1 -1: Some tests failed.
"""
    evidence = parse_dart_output(sample_stdout, exit_code=1, duration_sec=1.0)

    assert evidence.execution_status == "failed"
    assert evidence.primary_failure_category == "assertion_failure"
    assert len(evidence.failing_tests) == 1

    t = evidence.failing_tests[0]
    assert t.failure_type == "assertion_failure"
    assert t.expected == "<200>"
    assert t.actual == "<404>"
    assert "Expected <200>, got <404>" in t.message


# ===========================================================================
# 8. Expected/Actual Extraction & Anti-Hallucination Test
# ===========================================================================

def test_expected_actual_extraction_and_anti_hallucination():
    # Case A: Deterministic equality
    clean_stdout = """
================================== FAILURES ===================================
__________________________________ test_eq ____________________________________
>       assert result == 42
E       assert 10 == 42
test_main.py:10: AssertionError
=========================== short test summary info ===========================
FAILED test_main.py::test_eq - assert 10 == 42
"""
    ev_a = parse_pytest_output(clean_stdout, exit_code=1)
    assert ev_a.failing_tests[0].expected == "42"
    assert ev_a.failing_tests[0].actual == "10"

    # Case B: Ambiguous boolean check (Anti-hallucination rule)
    ambiguous_stdout = """
================================== FAILURES ===================================
_________________________________ test_bool ___________________________________
>       assert is_valid_payload(data)
E       assert False
test_main.py:20: AssertionError
=========================== short test summary info ===========================
FAILED test_main.py::test_bool - assert False
"""
    ev_b = parse_pytest_output(ambiguous_stdout, exit_code=1)
    # Parser must NOT hallucinate expected=True or arbitrary values
    assert ev_b.failing_tests[0].expected is None
    assert ev_b.failing_tests[0].actual is None
    assert "assert False" in ev_b.failing_tests[0].message


# ===========================================================================
# 9. Source Location Resolution (Bottom-Up Frame Scanner)
# ===========================================================================

def test_source_and_test_location_resolution():
    sample_stdout = """
================================== FAILURES ===================================
____________________________ test_get_all_products ____________________________

Traceback (most recent call last):
  File "C:\\Users\\rachm\\.venv\\lib\\site-packages\\starlette\\routing.py", line 68, in app
    response = await func(request)
  File "main.py", line 19, in get_products
    return {"items": products}
  File "test_main.py", line 28, in test_get_all_products
    response = client.get("/products")
E   assert 405 == 200

test_main.py:28: AssertionError
=========================== short test summary info ===========================
FAILED test_main.py::test_get_all_products - assert 405 == 200
"""
    evidence = parse_pytest_output(sample_stdout, exit_code=1)
    assert len(evidence.failing_tests) == 1
    t = evidence.failing_tests[0]

    # Test location
    assert t.test_file == "test_main.py"
    assert t.test_line == 28

    # Source application location (resolved from innermost app frame, ignoring starlette)
    assert t.source_file == "main.py"
    assert t.source_line == 19
    assert t.source_symbol == "get_products"


# ===========================================================================
# 10. Multi-Failure Top-3 Prioritization & Omitted Summary
# ===========================================================================

def test_top_3_prioritization_and_omitted_summary():
    # Buat 5 kegagalan dengan kategori berbeda
    failures = [
        FailingTest(test_name="t_assert_1", test_file="test_a.py", failure_type="assertion_failure"),
        FailingTest(test_name="t_syntax", test_file="test_b.py", failure_type="syntax_parse_error"),
        FailingTest(test_name="t_assert_2", test_file="test_c.py", failure_type="assertion_failure"),
        FailingTest(test_name="t_runtime", test_file="test_d.py", failure_type="runtime_exception"),
        FailingTest(test_name="t_import", test_file="test_e.py", failure_type="import_module_error"),
    ]

    top_3, omitted = prioritize_failures(failures)

    assert len(top_3) == 3
    assert len(omitted) == 2

    # Urutan prioritas taksonomi: syntax (2) > import (3) > runtime (5) > assertion (6)
    assert top_3[0].failure_type == "syntax_parse_error"
    assert top_3[1].failure_type == "import_module_error"
    assert top_3[2].failure_type == "runtime_exception"
    assert omitted[0].failure_type == "assertion_failure"
    assert omitted[1].failure_type == "assertion_failure"

    # Verifikasi payload markdown menyertakan ringkasan omitted
    evidence = DiagnosticEvidence(
        execution_status="failed",
        framework="pytest",
        total_tests=5,
        passed_tests=0,
        failed_tests=5,
        primary_failure_category="syntax_parse_error",
        failing_tests=failures
    )
    feedback = build_targeted_feedback(evidence, iteration=1, max_iterations=3)

    assert "1. [SYNTAX PARSE ERROR]" in feedback
    assert "2. [IMPORT MODULE ERROR]" in feedback
    assert "3. [RUNTIME EXCEPTION]" in feedback
    assert "+ 2 pengujian lainnya gagal dengan pola serupa" in feedback


# ===========================================================================
# 11. ANSI Stripping & Environment Noise Sanitization
# ===========================================================================

def test_ansi_and_noise_stripping():
    dirty_text = (
        "\x1B[31mFAILED\x1B[0m test_main.py::test_fn\n"
        "backend\\.venv\\Lib\\site-packages\\starlette\\testclient.py:53: "
        "DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated\n"
        "  _PortalFactoryType = Callable\n"
        "E   assert 1 == 2\n"
    )

    clean = strip_ansi(dirty_text)
    assert "\x1B[" not in clean
    assert "FAILED test_main.py::test_fn" in clean

    cleaned_body, warnings = extract_environment_warnings(clean)
    assert len(warnings) >= 1
    assert "BlockingPortal alias is deprecated" in warnings[0]
    assert "DeprecationWarning" not in cleaned_body


# ===========================================================================
# 12. Fallback Parser (Level 1 Partial & Level 2 Total)
# ===========================================================================

def test_fallback_mechanisms_partial_and_total(monkeypatch):
    # Level 1: Output tidak memiliki pola assertion atau traceback standar, tetapi exit_code=1
    garbled_output = "Fatal process crash without standard summary format"
    res_partial = {
        "stdout": garbled_output,
        "stderr": "",
        "exit_code": 1,
        "duration_sec": 0.5,
        "framework": "pytest"
    }
    ev_partial = parse_diagnostic(res_partial)
    assert ev_partial.execution_status == "failed"
    assert ev_partial.primary_failure_category == "unknown"
    assert len(ev_partial.failing_tests) == 1
    assert ev_partial.failing_tests[0].confidence == 0.0

    # Level 2: Simulasi exception unhandled pada internal parser
    from backend import diagnostic_parser
    def crashing_parser(*args, **kwargs):
        raise RuntimeError("Simulated unexpected internal parser crash")
    monkeypatch.setattr(diagnostic_parser, "parse_pytest_output", crashing_parser)

    res_corrupted = {
        "stdout": "Line 1\nLine 2\nLine 3\nFatal crash traceback",
        "stderr": "",
        "exit_code": 139,
        "framework": "pytest"
    }
    ev_total = parse_diagnostic(res_corrupted)
    assert ev_total.execution_status == "error"
    assert ev_total.primary_failure_category == "unknown"
    assert len(ev_total.failing_tests) == 1
    assert "[DIAGNOSTIC FALLBACK - UNPARSED TERMINAL OUTPUT]" in ev_total.failing_tests[0].message
    assert "Fatal crash traceback" in ev_total.failing_tests[0].message


# ===========================================================================
# 13. Immutability of code_files
# ===========================================================================

def test_immutability_code_files():
    code_files = {
        "main.py": "def add(a, b): return a + b",
        "models.py": "class Item: id: int"
    }
    hashes_before = compute_dict_hashes(code_files)

    res = {
        "stdout": "FAILED test_main.py::test_add - assert 3 == 4",
        "exit_code": 1,
        "framework": "pytest"
    }
    ev = parse_diagnostic(res, code_files=code_files)

    hashes_after = compute_dict_hashes(code_files)
    assert hashes_before == hashes_after, "Diagnostic parser MUST NEVER mutate code_files!"


# ===========================================================================
# 14. Immutability of test_files
# ===========================================================================

def test_immutability_test_files():
    test_files = {
        "test_main.py": "def test_add(): assert add(1, 2) == 4",
    }
    hashes_before = compute_dict_hashes(test_files)

    res = {
        "stdout": "FAILED test_main.py::test_add - assert 3 == 4",
        "exit_code": 1,
        "framework": "pytest"
    }
    ev = parse_diagnostic(res, test_files=test_files)

    hashes_after = compute_dict_hashes(test_files)
    assert hashes_before == hashes_after, "Diagnostic parser MUST NEVER mutate test_files!"


# ===========================================================================
# 15. Raw Evidence Preservation Test
# ===========================================================================

def test_raw_evidence_preservation():
    raw_stdout = "================== FAILURES ==================\n... 4000 chars of terminal noise ...\n"
    raw_stderr = "DeprecationWarning: foo\n"
    original_output = raw_stdout + "\n" + raw_stderr

    results = {
        "passed": False,
        "total": 5,
        "failed_count": 3,
        "raw_stdout": raw_stdout,
        "raw_stderr": raw_stderr,
        "output": original_output,
        "exit_code": 1,
        "framework": "pytest"
    }

    diag = parse_diagnostic(results)
    results["diagnostic_evidence"] = diag.to_dict()

    # Raw evidence must remain 100% identical and unmutated
    assert results["raw_stdout"] == raw_stdout
    assert results["raw_stderr"] == raw_stderr
    assert results["output"] == original_output
    assert "diagnostic_evidence" in results


# ===========================================================================
# 16. Developer Receives Targeted Feedback (Not Raw Dump)
# ===========================================================================

def test_developer_receives_targeted_feedback_not_raw_dump(monkeypatch):
    raw_noisy_dump = "=== RAW NOISY TERMINAL DUMP (3500 CHARACTERS) ===\n" * 70
    targeted_feedback = (
        "[TARGETED DIAGNOSTIC EVIDENCE - ITERASI PERBAIKAN 1/3]\n"
        "Ringkasan: 1 dari 1 pengujian GAGAL (Framework: pytest | Exit Code: 1 | Durasi: 0.20s)\n"
        "Kategori Kegagalan Utama: assertion_failure\n\n"
        "DAFTAR MASALAH PRIORITAS:\n"
        "1. [ASSERTION FAILURE] dalam test: test_add\n"
        "   - Berkas Pengujian: test_main.py (baris 10)\n"
        "   - Ekspektasi Pengujian: 4\n"
        "   - Hasil Aktual: 3\n"
        "   - Pesan Galat: assert 3 == 4"
    )

    captured_prompt = {}

    class MockModel:
        def invoke(self, messages):
            captured_prompt["prompt"] = messages[1].content if len(messages) > 1 else messages[0].content
            class MockResp:
                content = "=== FILE: main.py ===\ndef add(a, b): return a + b + 1\n=== END FILE ==="
            return MockResp()

    from backend import config
    from backend.agents import developer
    monkeypatch.setattr(config, "get_llm", lambda *args, **kwargs: MockModel())
    monkeypatch.setattr(developer, "get_llm", lambda *args, **kwargs: MockModel())

    state = {
        "task": "Fix addition bug",
        "iteration_count": 1,
        "max_iterations": 3,
        "code_files": {"main.py": "def add(a, b): return a + b"},
        "test_files": {"test_main.py": "def test_add(): assert add(1, 2) == 4"},
        "test_results": {
            "passed": False,
            "output": raw_noisy_dump,
            "diagnostic_evidence": {"primary_failure_category": "assertion_failure"}
        },
        "developer_feedback": targeted_feedback,
        "logs": []
    }

    developer_agent(state)

    prompt = captured_prompt["prompt"]
    # Verifikasi bahwa Developer menerima targeted feedback dan BUKAN raw noisy dump
    assert targeted_feedback in prompt
    assert raw_noisy_dump not in prompt
    assert "DAFTAR MASALAH PRIORITAS" in prompt
    assert "assert 3 == 4" in prompt


# ===========================================================================
# 17. Real Phase 2 Trace Fixture Validation
# ===========================================================================

def test_phase2_real_trace_fixtures():
    pytest_trace_path = Path("backend/output/project_20260909_082354/run_trace.jsonl")
    if pytest_trace_path.exists():
        with open(pytest_trace_path, "r", encoding="utf-8") as f:
            for line in f:
                ev = json.loads(line)
                if ev.get("stage") == "executor" and ev.get("event_type") == "execution":
                    stdout = ev["data"].get("stdout", "")
                    stderr = ev["data"].get("stderr", "")
                    res = {
                        "stdout": stdout,
                        "stderr": stderr,
                        "exit_code": 1,
                        "duration_sec": 0.35,
                        "framework": "pytest"
                    }
                    diag = parse_diagnostic(res, target_language="python")
                    assert diag.execution_status == "failed"
                    assert diag.primary_failure_category == "assertion_failure"
                    assert len(diag.failing_tests) == 3
                    break

    dart_trace_path = Path("backend/output/project_20260909_091035/run_trace.jsonl")
    if dart_trace_path.exists():
        with open(dart_trace_path, "r", encoding="utf-8") as f:
            for line in f:
                ev = json.loads(line)
                if ev.get("stage") == "executor" and ev.get("event_type") == "execution":
                    stdout = ev["data"].get("stdout", "")
                    stderr = ev["data"].get("stderr", "")
                    res = {
                        "stdout": stdout,
                        "stderr": stderr,
                        "exit_code": 1,
                        "duration_sec": 1.2,
                        "framework": "flutter test"
                    }
                    diag = parse_diagnostic(res, target_language="dart")
                    assert diag.execution_status == "error"
                    assert diag.primary_failure_category == "compilation_error"
                    assert len(diag.failing_tests) >= 2
                    break
