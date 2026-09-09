"""
Structured Diagnostic Parser & Targeted Error Feedback (P0-1)
ReinDev Studio — Deterministic Diagnostic Engine

Modul ini bertugas mengurai output mentah subproses sandbox (pytest & dart test),
mengekstrak bukti diagnostik terstruktur, mengklasifikasikan kategori kegagalan,
menyelesaikan lokasi kode sumber, dan menyusun umpan balik hemat token (<600 karakter)
untuk Developer pada siklus perbaikan (self-healing loop).

Prinsip Utama:
1. READ-ONLY: Tidak mengubah code_files, test_files, atau Frozen Oracle.
2. DETERMINISTIK & ANTI-HALUSINASI: Expected/actual hanya diekstrak jika terbukti secara sintaksis.
3. NON-PRESKRIPTIF: Menyatakan APA yang gagal dan BUKTINYA, bukan mendikte solusi kode.
4. FAIL-SAFE: Tidak pernah melempar eksepsi yang menghentikan pipeline eksekusi.
"""

from __future__ import annotations

import re
import copy
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional, Tuple

try:
    from .tracer import get_tracer
except (ImportError, ValueError):
    try:
        from tracer import get_tracer
    except ImportError:
        def get_tracer(run_id: Optional[str] = None):
            return None


# ===========================================================================
# 1. Failure Taxonomy & Priority Hierarchy
# ===========================================================================

TAXONOMY_PRIORITY: Dict[str, int] = {
    "collection_test_discovery_error": 1,
    "syntax_parse_error": 2,
    "import_module_error": 3,
    "compilation_error": 4,
    "runtime_exception": 5,
    "assertion_failure": 6,
    "timeout": 7,
    "unknown": 8,
}

VALID_TAXONOMY_CATEGORIES = set(TAXONOMY_PRIORITY.keys())


# ===========================================================================
# 2. Schema / Data Models (DiagnosticEvidence Contract)
# ===========================================================================

@dataclass
class FailingTest:
    test_name: str
    test_file: str
    test_line: Optional[int] = None
    failure_type: str = "unknown"
    message: str = ""
    expected: Optional[str] = None
    actual: Optional[str] = None
    source_file: Optional[str] = None
    source_line: Optional[int] = None
    source_symbol: Optional[str] = None
    traceback_excerpt: Optional[str] = None
    confidence: float = 1.0
    linked_assertion_id: Optional[str] = None
    linked_req_id: Optional[str] = None
    linked_interface_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> FailingTest:
        return cls(
            test_name=data.get("test_name", "unknown_test"),
            test_file=data.get("test_file", "unknown_file"),
            test_line=data.get("test_line"),
            failure_type=data.get("failure_type", "unknown"),
            message=data.get("message", ""),
            expected=data.get("expected"),
            actual=data.get("actual"),
            source_file=data.get("source_file"),
            source_line=data.get("source_line"),
            source_symbol=data.get("source_symbol"),
            traceback_excerpt=data.get("traceback_excerpt"),
            confidence=float(data.get("confidence", 1.0)),
            linked_assertion_id=data.get("linked_assertion_id"),
            linked_req_id=data.get("linked_req_id"),
            linked_interface_id=data.get("linked_interface_id")
        )



@dataclass
class DiagnosticEvidence:
    execution_status: str  # "passed", "failed", "error", "timeout"
    framework: str  # "pytest", "dart test", "flutter test"
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    error_count: int = 0
    duration_sec: float = 0.0
    exit_code: int = 0
    summary_line: Optional[str] = None
    primary_failure_category: str = "unknown"
    failing_tests: List[FailingTest] = field(default_factory=list)
    environment_warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["failing_tests"] = [t.to_dict() for t in self.failing_tests]
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DiagnosticEvidence:
        failing_tests = [
            FailingTest.from_dict(t) if isinstance(t, dict) else t
            for t in data.get("failing_tests", [])
        ]
        return cls(
            execution_status=data.get("execution_status", "failed"),
            framework=data.get("framework", "pytest"),
            total_tests=int(data.get("total_tests", 0)),
            passed_tests=int(data.get("passed_tests", 0)),
            failed_tests=int(data.get("failed_tests", 0)),
            error_count=int(data.get("error_count", 0)),
            duration_sec=float(data.get("duration_sec", 0.0)),
            exit_code=int(data.get("exit_code", 0)),
            summary_line=data.get("summary_line"),
            primary_failure_category=data.get("primary_failure_category", "unknown"),
            failing_tests=failing_tests,
            environment_warnings=list(data.get("environment_warnings", []))
        )


# ===========================================================================
# 3. ANSI & Noise Sanitizer
# ===========================================================================

ANSI_ESCAPE_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

def strip_ansi(text: str) -> str:
    """Menghapus kode ANSI escape sequence untuk visualisasi terminal bersih."""
    if not text:
        return ""
    return ANSI_ESCAPE_RE.sub("", text)


def extract_environment_warnings(raw_text: str) -> Tuple[str, List[str]]:
    """
    Memisahkan peringatan lingkungan/deprecations (misal: AnyIO BlockingPortal)
    dari output utama agar tidak mendistraksi Developer LLM.
    """
    cleaned_lines = []
    warnings = []
    
    in_warning_block = False
    warning_buffer = []

    for line in raw_text.splitlines():
        line_clean = line.strip()
        if "DeprecationWarning:" in line or "UserWarning:" in line or "FutureWarning:" in line:
            in_warning_block = True
            warning_buffer.append(line_clean)
        elif in_warning_block:
            if line_clean == "" or line_clean.startswith("=") or line_clean.startswith("FAILED") or line_clean.startswith("ERROR"):
                in_warning_block = False
                if warning_buffer:
                    warnings.append(" ".join(warning_buffer))
                    warning_buffer = []
                cleaned_lines.append(line)
            else:
                warning_buffer.append(line_clean)
        else:
            cleaned_lines.append(line)

    if warning_buffer:
        warnings.append(" ".join(warning_buffer))

    return "\n".join(cleaned_lines), warnings


# ===========================================================================
# 4. Helper Normalization & Frame Filter
# ===========================================================================

FRAMEWORK_NOISE_SUBSTRINGS = (
    "site-packages",
    "lib/python",
    "starlette/",
    "anyio/",
    "pytest/",
    "_pytest/",
    "pluggy/",
    "packages/flutter/",
    "packages/flutter_test/",
    "packages/matcher/",
    "packages/test_api/",
    "AppData/Local/Programs/Python",
    "appdata\\local\\programs\\python"
)

def is_framework_path(path: str) -> bool:
    """Mengecek apakah path file merupakan internal framework / library."""
    p_norm = path.replace("\\", "/").lower()
    return any(sub in p_norm for sub in FRAMEWORK_NOISE_SUBSTRINGS)


def is_test_file_path(path: str) -> bool:
    """Mengecek apakah path merujuk pada berkas pengujian."""
    p_norm = path.replace("\\", "/").lower()
    name = p_norm.split("/")[-1]
    return (
        name.startswith("test_")
        or name.endswith("_test.py")
        or name.endswith("_test.dart")
        or "/test/" in p_norm
        or p_norm.startswith("test/")
        or "/tests/" in p_norm
        or p_norm.startswith("tests/")
    )


def normalize_file_path(path: str) -> str:
    """Membersihkan path file dari prefix Windows/relatif agar bersih dan seragam."""
    p = path.replace("\\", "/").strip()
    if p.startswith("./"):
        p = p[2:]
    return p


# ===========================================================================
# 5. Pytest Parser Engine
# ===========================================================================

RE_PYTEST_SUMMARY = re.compile(
    r"=+\s*(?:(\d+)\s+failed)?(?:,\s*)?(?:(\d+)\s+passed)?(?:,\s*)?(?:(\d+)\s+errors?)?.*?in\s+([\d\.]+)s\s*=+",
    re.MULTILINE
)
RE_PYTEST_FAILED_ITEM = re.compile(r"^FAILED\s+([\w\.\/\\]+)::(\w+)\s*-\s*(.+)$", re.MULTILINE)
RE_PYTEST_ERROR_COLLECT = re.compile(r"^ERROR\s+collecting\s+([\w\.\/\\]+)", re.MULTILINE)
RE_PYTEST_FAIL_HEADER = re.compile(r"^_{10,}\s+(\w+)\s+_{10,}$", re.MULTILINE)
RE_PYTEST_ASSERT_EQUAL = re.compile(r"^\s*E\s+assert\s+(.+?)\s*==\s*(.+)$", re.MULTILINE)
RE_PYTEST_EXCEPTION = re.compile(r"^\s*E\s+([A-Za-z]\w*(?:Error|Exception))(?::\s*(.*))?$", re.MULTILINE)
RE_PYTEST_FILE_LINE = re.compile(r"^([\w\.\/\\]+\.py):(\d+):\s*([A-Za-z]\w*)", re.MULTILINE)
RE_PYTEST_TRACE_FRAME = re.compile(r'^\s*File\s+"([^"]+)",\s*line\s+(\d+)(?:,\s*in\s+([^\n\r]+))?', re.MULTILINE)


def parse_pytest_output(
    stdout: str,
    stderr: str = "",
    exit_code: int = 0,
    duration_sec: float = 0.0,
    code_files: Optional[Dict[str, str]] = None,
    test_files: Optional[Dict[str, str]] = None
) -> DiagnosticEvidence:
    """
    Parser deterministik untuk output pengujian pytest.
    """
    full_text = strip_ansi(f"{stdout}\n{stderr}").strip()
    cleaned_text, warnings = extract_environment_warnings(full_text)

    # 1. Ekstrak baris ringkasan tes
    failed_count = 0
    passed_count = 0
    error_count = 0
    dur = duration_sec
    summary_line = None

    for match in RE_PYTEST_SUMMARY.finditer(cleaned_text):
        f_str, p_str, e_str, d_str = match.groups()
        failed_count = int(f_str) if f_str else 0
        passed_count = int(p_str) if p_str else 0
        error_count = int(e_str) if e_str else 0
        if d_str and dur == 0.0:
            dur = float(d_str)
        summary_line = match.group(0).strip("=").strip()

    total_tests = passed_count + failed_count + error_count

    # 2. Cek apakah ada Collection Error (exit code 2 atau ERROR collecting)
    collection_errors = list(RE_PYTEST_ERROR_COLLECT.finditer(cleaned_text))
    if collection_errors or ("Interrupted: " in cleaned_text and "error" in cleaned_text.lower()):
        failing_tests: List[FailingTest] = []
        for match in collection_errors:
            err_file = normalize_file_path(match.group(1))
            # Cari pesan exception di sekitar error collecting
            exc_match = RE_PYTEST_EXCEPTION.search(cleaned_text)
            if exc_match:
                exc_type = exc_match.group(1)
                exc_msg = exc_match.group(2) or ""
                msg = f"{exc_type}: {exc_msg}"
                if "SyntaxError" in exc_type or "IndentationError" in exc_type:
                    ftype = "syntax_parse_error"
                elif "ModuleNotFoundError" in exc_type or "ImportError" in exc_type:
                    ftype = "import_module_error"
                else:
                    ftype = "collection_test_discovery_error"
            else:
                ftype = "collection_test_discovery_error"
                msg = f"Collection error when loading {err_file}"

            failing_tests.append(FailingTest(
                test_name=f"collecting_{err_file}",
                test_file=err_file,
                test_line=None,
                failure_type=ftype,
                message=msg,
                confidence=1.0
            ))

        if not failing_tests and ("ModuleNotFoundError" in cleaned_text or "ImportError" in cleaned_text):
            exc_match = RE_PYTEST_EXCEPTION.search(cleaned_text)
            msg = exc_match.group(0).strip("E ") if exc_match else "Import module error during collection"
            failing_tests.append(FailingTest(
                test_name="module_import",
                test_file="conftest.py",
                failure_type="import_module_error",
                message=msg,
                confidence=0.9
            ))

        return DiagnosticEvidence(
            execution_status="error",
            framework="pytest",
            total_tests=max(total_tests, len(failing_tests)),
            passed_tests=passed_count,
            failed_tests=failed_count,
            error_count=max(error_count, len(failing_tests)),
            duration_sec=dur,
            exit_code=exit_code if exit_code != 0 else 2,
            summary_line=summary_line,
            primary_failure_category=failing_tests[0].failure_type if failing_tests else "collection_test_discovery_error",
            failing_tests=failing_tests,
            environment_warnings=warnings
        )

    # 3. Ekstrak daftar tes yang gagal dari 'short test summary info'
    short_summary_failures: Dict[str, Tuple[str, str]] = {}  # {test_name: (test_file, message)}
    for match in RE_PYTEST_FAILED_ITEM.finditer(cleaned_text):
        tfile = normalize_file_path(match.group(1))
        tname = match.group(2)
        tmsg = match.group(3).strip()
        short_summary_failures[tname] = (tfile, tmsg)

    # 4. Potong blok FAILURES menjadi per-test section
    failures_section_match = re.search(r"={10,}\s+FAILURES\s+={10,}(.*?)(?:={10,}|$)", cleaned_text, re.DOTALL)
    failures_text = failures_section_match.group(1) if failures_section_match else cleaned_text

    # Pisahkan blok berdasarkan header '_______ test_name _______'
    header_indices = [m.start() for m in RE_PYTEST_FAIL_HEADER.finditer(failures_text)]
    header_matches = list(RE_PYTEST_FAIL_HEADER.finditer(failures_text))

    test_blocks: Dict[str, str] = {}
    for i, m in enumerate(header_matches):
        tname = m.group(1)
        start_pos = m.start()
        end_pos = header_indices[i + 1] if i + 1 < len(header_indices) else len(failures_text)
        test_blocks[tname] = failures_text[start_pos:end_pos]

    failing_tests: List[FailingTest] = []
    seen_tests = set()

    # Prioritaskan item yang ada di short_summary atau test_blocks
    all_failing_names = list(short_summary_failures.keys())
    for name in test_blocks.keys():
        if name not in all_failing_names:
            all_failing_names.append(name)

    for tname in all_failing_names:
        block = test_blocks.get(tname, "")
        summary_info = short_summary_failures.get(tname)
        tfile = summary_info[0] if summary_info else "unknown_test.py"
        raw_msg = summary_info[1] if summary_info else ""

        # Default classification
        failure_type = "assertion_failure"
        expected = None
        actual = None
        test_line = None
        source_file = None
        source_line = None
        source_symbol = None
        traceback_excerpt = None
        confidence = 0.95

        # Cari assert equality
        assert_eq_match = RE_PYTEST_ASSERT_EQUAL.search(block)
        if assert_eq_match:
            actual_cand = assert_eq_match.group(1).strip()
            expected_cand = assert_eq_match.group(2).strip()
            actual = actual_cand
            expected = expected_cand
            failure_type = "assertion_failure"
            if not raw_msg:
                raw_msg = f"assert {actual} == {expected}"
        else:
            # Cek eksepsi runtime / syntax
            exc_match = RE_PYTEST_EXCEPTION.search(block)
            if exc_match:
                exc_type = exc_match.group(1)
                exc_detail = exc_match.group(2) or ""
                raw_msg = f"{exc_type}: {exc_detail}".strip()
                if "SyntaxError" in exc_type or "IndentationError" in exc_type:
                    failure_type = "syntax_parse_error"
                elif "ModuleNotFoundError" in exc_type or "ImportError" in exc_type:
                    failure_type = "import_module_error"
                elif exc_type == "AssertionError":
                    failure_type = "assertion_failure"
                    # Cek jika ada raw_msg dari summary
                    if summary_info and "assert " in summary_info[1]:
                        raw_msg = summary_info[1]
                else:
                    failure_type = "runtime_exception"
            elif "assert " in raw_msg:
                failure_type = "assertion_failure"
                eq_m = re.search(r"assert\s+(.+?)\s*==\s*(.+)", raw_msg)
                if eq_m:
                    actual = eq_m.group(1).strip()
                    expected = eq_m.group(2).strip()

        # Ekstrak test_file dan test_line dari baris penutup block
        # Contoh: test_main.py:20: AssertionError
        end_line_match = RE_PYTEST_FILE_LINE.search(block)
        if end_line_match:
            tfile_cand = normalize_file_path(end_line_match.group(1))
            if is_test_file_path(tfile_cand):
                tfile = tfile_cand
                test_line = int(end_line_match.group(2))

        # Bottom-up traceback frame scanning untuk menemukan source_file & source_line
        frames = list(RE_PYTEST_TRACE_FRAME.finditer(block))
        app_frames = []
        test_frames = []

        for f in frames:
            f_path = normalize_file_path(f.group(1))
            f_line = int(f.group(2))
            f_symbol = f.group(3).strip() if f.group(3) else None

            if is_framework_path(f_path):
                continue

            if is_test_file_path(f_path):
                test_frames.append((f_path, f_line, f_symbol))
            else:
                app_frames.append((f_path, f_line, f_symbol))

        if app_frames:
            # Innermost application frame
            innermost = app_frames[-1]
            source_file = innermost[0]
            source_line = innermost[1]
            source_symbol = innermost[2]
        if test_frames and not test_line:
            innermost_test = test_frames[-1]
            tfile = innermost_test[0]
            test_line = innermost_test[1]

        # Buat traceback excerpt ringkas (2-3 baris penting)
        e_lines = [l.strip() for l in block.splitlines() if l.strip().startswith("E ") or l.strip().startswith("> ")]
        if e_lines:
            traceback_excerpt = "\n".join(e_lines[:3])

        failing_tests.append(FailingTest(
            test_name=tname,
            test_file=tfile,
            test_line=test_line,
            failure_type=failure_type,
            message=raw_msg or f"{failure_type} in {tname}",
            expected=expected,
            actual=actual,
            source_file=source_file,
            source_line=source_line,
            source_symbol=source_symbol,
            traceback_excerpt=traceback_excerpt,
            confidence=confidence
        ))
        seen_tests.add(tname)

    # 5. Tentukan status eksekusi & kategori kegagalan utama
    if exit_code == 0 and (failed_count == 0 and error_count == 0) and not failing_tests:
        execution_status = "passed"
        primary_category = "passed"
    else:
        execution_status = "failed" if exit_code == 1 else "error"
        # Pilih kategori kegagalan dengan prioritas tertinggi dari daftar failing_tests
        if failing_tests:
            sorted_fails = sorted(failing_tests, key=lambda x: TAXONOMY_PRIORITY.get(x.failure_type, 99))
            primary_category = sorted_fails[0].failure_type
        else:
            primary_category = "unknown"

    # Fallback Level 1 jika ada tanda gagal tapi failing_tests kosong
    if execution_status in ("failed", "error") and not failing_tests:
        failing_tests.append(FailingTest(
            test_name="pytest_execution",
            test_file="test_main.py",
            failure_type="unknown",
            message=summary_line or f"Pytest exited with code {exit_code}",
            confidence=0.0
        ))

    return DiagnosticEvidence(
        execution_status=execution_status,
        framework="pytest",
        total_tests=max(total_tests, len(failing_tests)),
        passed_tests=passed_count,
        failed_tests=max(failed_count, len([t for t in failing_tests if t.failure_type == "assertion_failure"])),
        error_count=max(error_count, len([t for t in failing_tests if t.failure_type != "assertion_failure"])),
        duration_sec=dur,
        exit_code=exit_code,
        summary_line=summary_line,
        primary_failure_category=primary_category,
        failing_tests=failing_tests,
        environment_warnings=warnings
    )


# ===========================================================================
# 6. Dart / Flutter Test Parser Engine
# ===========================================================================

RE_DART_COMPILATION_ERROR = re.compile(
    r"^([\w\.\/\\]+\.dart):(\d+):(\d+):\s*Error:\s*(.+)$",
    re.MULTILINE
)
RE_DART_TEST_HEADER = re.compile(r"^(?:\d\d:\d\d\s+)?\+\d+\s+-\d+:\s*(.+?)\s*\[E\]", re.MULTILINE)
RE_DART_EXPECTED_ACTUAL = re.compile(
    r"Expected:\s*(.+?)[\r\n]+\s*Actual:\s*(.+?)(?:[\r\n]+\s*Which:\s*(.+?))?(?=[\r\n]+\s*\S|\Z)",
    re.DOTALL
)
RE_DART_SUMMARY = re.compile(r"(\d+)\s+passed(?:,\s*(\d+)\s+failed)?", re.IGNORECASE)
RE_DART_PLUS_MINUS = re.compile(r"\+(\d+)\s+-\s*(\d+):", re.MULTILINE)


def parse_dart_output(
    stdout: str,
    stderr: str = "",
    exit_code: int = 0,
    duration_sec: float = 0.0,
    code_files: Optional[Dict[str, str]] = None,
    test_files: Optional[Dict[str, str]] = None
) -> DiagnosticEvidence:
    """
    Parser deterministik untuk output pengujian dart test / flutter test.
    """
    full_text = strip_ansi(f"{stdout}\n{stderr}").strip()
    cleaned_text, warnings = extract_environment_warnings(full_text)

    # 1. Deteksi Compilation Errors (Error: ...)
    compilation_errors = list(RE_DART_COMPILATION_ERROR.finditer(cleaned_text))
    if compilation_errors:
        failing_tests: List[FailingTest] = []
        for match in compilation_errors:
            f_path = normalize_file_path(match.group(1))
            line_no = int(match.group(2))
            col_no = int(match.group(3))
            err_msg = match.group(4).strip()

            is_test = is_test_file_path(f_path)
            tfile = f_path if is_test else "test/widget_test.dart"
            tline = line_no if is_test else None
            sfile = f_path if not is_test else None
            sline = line_no if not is_test else None

            failing_tests.append(FailingTest(
                test_name="compilation_check",
                test_file=tfile,
                test_line=tline,
                failure_type="compilation_error",
                message=f"Compilation Error: {err_msg}",
                source_file=sfile,
                source_line=sline,
                traceback_excerpt=f"{f_path}:{line_no}:{col_no}: Error: {err_msg}",
                confidence=1.0
            ))

        return DiagnosticEvidence(
            execution_status="error",
            framework="flutter test",
            total_tests=len(failing_tests),
            passed_tests=0,
            failed_tests=0,
            error_count=len(failing_tests),
            duration_sec=duration_sec,
            exit_code=exit_code if exit_code != 0 else 1,
            summary_line="Compilation failed before test execution",
            primary_failure_category="compilation_error",
            failing_tests=failing_tests,
            environment_warnings=warnings
        )

    # 2. Deteksi Assertion & Runtime Exceptions pada Flutter Test
    passed_count = 0
    failed_count = 0
    # Cek pattern '+X -Y:'
    plus_minus_matches = list(RE_DART_PLUS_MINUS.finditer(cleaned_text))
    if plus_minus_matches:
        last_pm = plus_minus_matches[-1]
        passed_count = int(last_pm.group(1))
        failed_count = int(last_pm.group(2))

    total_tests = passed_count + failed_count
    test_headers = list(RE_DART_TEST_HEADER.finditer(cleaned_text))

    failing_tests: List[FailingTest] = []

    # Cek Expected vs Actual
    ea_matches = list(RE_DART_EXPECTED_ACTUAL.finditer(cleaned_text))
    for i, match in enumerate(ea_matches):
        expected_raw = match.group(1).strip()
        actual_raw = match.group(2).strip()
        which_raw = match.group(3).strip() if match.group(3) else None

        tname = test_headers[i].group(1).strip() if i < len(test_headers) else f"flutter_test_{i+1}"
        msg = f"Expected {expected_raw}, got {actual_raw}"
        if which_raw:
            msg += f" (Which: {which_raw})"

        failing_tests.append(FailingTest(
            test_name=tname,
            test_file="test/widget_test.dart",
            failure_type="assertion_failure",
            message=msg,
            expected=expected_raw,
            actual=actual_raw,
            confidence=0.95
        ))

    # Jika ada test header [E] tapi belum tertangkap di expected/actual
    if not failing_tests and test_headers:
        for th in test_headers:
            tname = th.group(1).strip()
            failing_tests.append(FailingTest(
                test_name=tname,
                test_file="test/widget_test.dart",
                failure_type="runtime_exception",
                message=f"Test failed: {tname}",
                confidence=0.8
            ))

    if exit_code == 0 and failed_count == 0 and not failing_tests:
        execution_status = "passed"
        primary_category = "passed"
    else:
        execution_status = "failed"
        primary_category = failing_tests[0].failure_type if failing_tests else "unknown"

    # Fallback Level 1
    if execution_status == "failed" and not failing_tests:
        failing_tests.append(FailingTest(
            test_name="dart_test_execution",
            test_file="test/widget_test.dart",
            failure_type="unknown",
            message=f"Dart test execution failed with exit code {exit_code}",
            confidence=0.0
        ))

    return DiagnosticEvidence(
        execution_status=execution_status,
        framework="flutter test",
        total_tests=max(total_tests, len(failing_tests)),
        passed_tests=passed_count,
        failed_tests=max(failed_count, len(failing_tests)),
        error_count=0,
        duration_sec=duration_sec,
        exit_code=exit_code,
        summary_line=f"+{passed_count} -{failed_count}",
        primary_failure_category=primary_category,
        failing_tests=failing_tests,
        environment_warnings=warnings
    )


# ===========================================================================
# 7. Multi-Failure Top-3 Prioritization & Targeted Feedback Builder
# ===========================================================================

def prioritize_failures(failing_tests: List[FailingTest]) -> Tuple[List[FailingTest], List[FailingTest]]:
    """
    Mengurutkan kegagalan berdasarkan hierarki taksonomi keparahan dan
    memisahkan menjadi Top-3 Prioritas serta sisa kegagalan yang diringkas.
    """
    if not failing_tests:
        return [], []

    sorted_tests = sorted(
        failing_tests,
        key=lambda t: TAXONOMY_PRIORITY.get(t.failure_type, 99)
    )

    top_3 = sorted_tests[:3]
    omitted = sorted_tests[3:]
    return top_3, omitted


def map_evidence_to_contract(
    test: FailingTest,
    contract: Optional[Dict[str, Any]]
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Memetakan bukti kegagalan (FailingTest) ke klausul kontrak (assertion_id, req_id, interface_id)
    hanya jika mapping dapat ditentukan secara deterministik dan tidak ambigu:
    1. Exact match pada assertion_id di nama test (contoh: AST-01, ast_01, ast01).
    2. Unambiguous match pada target_symbol unik (contoh: get_products).
    3. Unambiguous match pada linked_interface_id unik (contoh: IFC-01).

    Jika tidak dapat dipetakan secara pasti: mengembalikan (None, None, None) tanpa halusinasi.
    """
    if not contract or not isinstance(contract, dict):
        return None, None, None

    assertions = contract.get("testable_assertions", [])
    if not assertions:
        return None, None, None

    test_name = (test.test_name or "").strip()
    test_name_lower = test_name.lower()

    # 1. Exact match pada assertion_id di nama test
    for a in assertions:
        aid = (a.get("assertion_id") or "").strip()
        if not aid:
            continue
        aid_norm = aid.lower().replace("-", "_")
        aid_compact = aid.lower().replace("-", "")
        if (
            re.search(rf"(?:_|\b){re.escape(aid_norm)}(?:_|\b)", test_name_lower)
            or re.search(rf"(?:_|\b){re.escape(aid.lower())}(?:_|\b)", test_name_lower)
            or re.search(rf"(?:_|\b){re.escape(aid_compact)}(?:_|\b)", test_name_lower)
        ):
            return a.get("assertion_id"), a.get("linked_req_id"), a.get("linked_interface_id")

    # 2. Match pada target_symbol yang unik
    source_sym = (test.source_symbol or "").strip().lower()
    candidate_matches = []
    for a in assertions:
        tsym = (a.get("target_symbol") or "").strip().lower()
        if not tsym:
            continue
        if source_sym and source_sym == tsym:
            candidate_matches.append(a)
        elif re.search(rf"\b{re.escape(tsym)}\b", test_name_lower):
            candidate_matches.append(a)

    if len(candidate_matches) == 1:
        matched = candidate_matches[0]
        return matched.get("assertion_id"), matched.get("linked_req_id"), matched.get("linked_interface_id")

    # 3. Match pada linked_interface_id yang unik
    interface_matches = []
    for a in assertions:
        liface = (a.get("linked_interface_id") or "").strip().lower()
        if not liface:
            continue
        liface_norm = liface.replace("-", "_")
        if re.search(rf"\b{re.escape(liface_norm)}\b", test_name_lower) or re.search(rf"\b{re.escape(liface)}\b", test_name_lower):
            interface_matches.append(a)

    if len(interface_matches) == 1:
        matched = interface_matches[0]
        return matched.get("assertion_id"), matched.get("linked_req_id"), matched.get("linked_interface_id")

    # Tidak dapat ditentukan secara pasti (unresolved) -> jangan halusinasi!
    return None, None, None


def build_targeted_feedback(
    evidence: DiagnosticEvidence,
    iteration: int = 1,
    max_iterations: int = 3,
    run_id: Optional[str] = None,
    contract: Optional[Dict[str, Any]] = None
) -> str:
    """
    Menyusun payload Markdown umpan balik diagnostik yang ringkas, hemat token (<600 karakter),
    dan bebas dari kebisingan terminal mentah.
    
    KRUSIAL: Non-preskriptif! Menjelaskan apa yang gagal dan buktinya,
    TIDAK mendikte baris perbaikan kode spesifik.
    Jika mapping kontrak tersedia secara deterministik, sertakan referensi assertion/klausul.
    """
    if evidence.execution_status == "passed":
        return ""

    top_3, omitted = prioritize_failures(evidence.failing_tests)

    lines = [
        f"[TARGETED DIAGNOSTIC EVIDENCE - ITERASI PERBAIKAN {iteration}/{max_iterations}]",
        f"Ringkasan: {evidence.failed_tests + evidence.error_count} dari {evidence.total_tests} pengujian GAGAL "
        f"(Framework: {evidence.framework} | Exit Code: {evidence.exit_code} | Durasi: {evidence.duration_sec:.2f}s)",
        f"Kategori Kegagalan Utama: {evidence.primary_failure_category}",
        "",
        "DAFTAR MASALAH PRIORITAS (Fokus pada investigasi bukti berikut):"
    ]

    for idx, test in enumerate(top_3, 1):
        type_label = test.failure_type.replace("_", " ").upper()
        lines.append(f"{idx}. [{type_label}] dalam test: {test.test_name}")
        
        # Mapping deterministik ke kontrak jika tersedia
        c_aid = test.linked_assertion_id
        c_rid = test.linked_req_id
        c_ifid = test.linked_interface_id
        if not c_aid and contract:
            c_aid, c_rid, c_ifid = map_evidence_to_contract(test, contract)

        if c_aid:
            mapping_str = f"Assertion {c_aid}"
            if c_rid:
                mapping_str += f" (Klausul: {c_rid})"
            lines.append(f"   - Pemetaan Kontrak: {mapping_str}")
            if c_ifid:
                lines.append(f"   - Antarmuka Terkait: {c_ifid}")

        test_loc = test.test_file
        if test.test_line:
            test_loc += f" (baris {test.test_line})"
        lines.append(f"   - Berkas Pengujian: {test_loc}")

        if test.source_file:
            source_loc = test.source_file
            details = []
            if test.source_line:
                details.append(f"baris {test.source_line}")
            if test.source_symbol:
                details.append(f"simbol: {test.source_symbol}")
            if details:
                source_loc += f" ({', '.join(details)})"
            lines.append(f"   - Berkas Kode Aplikasi: {source_loc}")

        if test.expected is not None and test.actual is not None:
            lines.append(f"   - Ekspektasi Pengujian: {test.expected}")
            lines.append(f"   - Hasil Aktual: {test.actual}")

        if test.message:
            lines.append(f"   - Pesan Galat: {test.message}")

        if test.traceback_excerpt:
            lines.append("   - Cuplikan Bukti:")
            for tb_line in test.traceback_excerpt.splitlines():
                lines.append(f"     {tb_line.strip()}")

        lines.append("")

    if omitted:
        lines.append(
            f"+ {len(omitted)} pengujian lainnya gagal dengan pola serupa. "
            f"Selesaikan 3 masalah prioritas di atas terlebih dahulu."
        )

    feedback_text = "\n".join(lines).strip()

    # Observability event logging
    tracer = get_tracer(run_id)
    if tracer:
        tracer.log_event(
            stage="diagnostic_parser",
            event_type="developer_feedback_generated",
            iteration=iteration,
            data={
                "feedback_char_length": len(feedback_text),
                "prioritized_failures_count": len(top_3),
                "omitted_failures_count": len(omitted),
                "primary_failure_category": evidence.primary_failure_category
            }
        )

    return feedback_text


def build_targeted_feedback_from_dict(
    evidence_dict: Dict[str, Any],
    iteration: int = 1,
    max_iterations: int = 3,
    run_id: Optional[str] = None,
    contract: Optional[Dict[str, Any]] = None
) -> str:
    """Helper untuk menyusun targeted feedback langsung dari dictionary diagnostic_evidence."""
    try:
        evidence = DiagnosticEvidence.from_dict(evidence_dict)
        return build_targeted_feedback(evidence, iteration, max_iterations, run_id, contract)
    except Exception:
        # Fail-safe jika deserialisasi dictionary gagal
        return ""



# ===========================================================================
# 8. Main Public Entrypoint & Level 2 Total Fallback
# ===========================================================================

def parse_diagnostic(
    results: Dict[str, Any],
    code_files: Optional[Dict[str, str]] = None,
    test_files: Optional[Dict[str, str]] = None,
    target_language: str = "python",
    run_id: Optional[str] = None,
    iteration: int = 0,
    contract: Optional[Dict[str, Any]] = None
) -> DiagnosticEvidence:
    """
    Titik masuk utama untuk menganalisis hasil sandbox runner secara deterministik.
    
    Menjamin:
    - 100% Read-only boundary: code_files dan test_files tidak dimodifikasi.
    - Fail-safe Level 2: jika terjadi unhandled error, kembalikan tail 15 lines terminal bersih.
    - Pencatatan event observabilitas ke tracer.
    """
    raw_stdout = results.get("raw_stdout", results.get("stdout", ""))
    raw_stderr = results.get("raw_stderr", results.get("stderr", ""))
    exit_code = results.get("exit_code", 0)
    duration_sec = results.get("duration_sec", 0.0)
    framework = results.get("framework", "").lower()

    if not framework:
        if "dart" in target_language.lower() or "flutter" in target_language.lower():
            framework = "flutter test"
        else:
            framework = "pytest"

    tracer = get_tracer(run_id)
    if tracer:
        tracer.log_event(
            stage="diagnostic_parser",
            event_type="diagnostic_parse_start",
            iteration=iteration,
            data={
                "framework": framework,
                "raw_output_bytes": len(raw_stdout) + len(raw_stderr),
                "iteration": iteration
            }
        )

    try:
        if "dart" in framework or "flutter" in framework:
            evidence = parse_dart_output(
                stdout=raw_stdout,
                stderr=raw_stderr,
                exit_code=exit_code,
                duration_sec=duration_sec,
                code_files=code_files,
                test_files=test_files
            )
        else:
            evidence = parse_pytest_output(
                stdout=raw_stdout,
                stderr=raw_stderr,
                exit_code=exit_code,
                duration_sec=duration_sec,
                code_files=code_files,
                test_files=test_files
            )

        # Pemetaan deterministik bukti ke klausul kontrak jika kontrak disediakan
        if contract:
            for t in evidence.failing_tests:
                if not t.linked_assertion_id:
                    aid, rid, ifid = map_evidence_to_contract(t, contract)
                    t.linked_assertion_id = aid
                    t.linked_req_id = rid
                    t.linked_interface_id = ifid

        if tracer:
            tracer.log_event(
                stage="diagnostic_parser",
                event_type="diagnostic_parse_complete",
                iteration=iteration,
                data={
                    "execution_status": evidence.execution_status,
                    "total_tests": evidence.total_tests,
                    "failed_tests": evidence.failed_tests,
                    "error_count": evidence.error_count,
                    "primary_failure_category": evidence.primary_failure_category,
                    "parsed_failing_count": len(evidence.failing_tests),
                    "duration_ms": int(evidence.duration_sec * 1000)
                }
            )

        return evidence

    except Exception as exc:
        # Fallback Level 2: Total Fallback (Clean Tail Dump)
        if tracer:
            tracer.log_event(
                stage="diagnostic_parser",
                event_type="diagnostic_parse_failed",
                iteration=iteration,
                data={
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                    "fallback_strategy_used": "tail_15_clean_lines"
                }
            )

        # Ambil 15 baris terakhir dari stdout / stderr mentah
        combined = strip_ansi(f"{raw_stdout}\n{raw_stderr}").strip()
        lines = [l for l in combined.splitlines() if l.strip()]
        tail_lines = lines[-15:] if len(lines) >= 15 else lines
        clean_tail = "\n".join(tail_lines)

        fallback_fail = FailingTest(
            test_name="unparsed_execution_error",
            test_file="unknown",
            failure_type="unknown",
            message="[DIAGNOSTIC FALLBACK - UNPARSED TERMINAL OUTPUT]\n" + clean_tail,
            confidence=0.0
        )

        return DiagnosticEvidence(
            execution_status="error",
            framework=framework,
            total_tests=1,
            passed_tests=0,
            failed_tests=1,
            error_count=1,
            duration_sec=duration_sec,
            exit_code=exit_code if exit_code != 0 else 1,
            summary_line="Fallback due to parser exception",
            primary_failure_category="unknown",
            failing_tests=[fallback_fail],
            environment_warnings=[]
        )
