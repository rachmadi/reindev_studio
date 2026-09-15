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

try:
    from .canonical_evidence import (
        CanonicalImplementationEvidence,
        ImplementationEvidenceType,
        deduplicate_evidence,
    )
except (ImportError, ValueError):
    try:
        from canonical_evidence import (
            CanonicalImplementationEvidence,
            ImplementationEvidenceType,
            deduplicate_evidence,
        )
    except ImportError:
        CanonicalImplementationEvidence = None
        ImplementationEvidenceType = None
        deduplicate_evidence = lambda l: l



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
    semantic_hint: Optional[str] = None

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
            linked_interface_id=data.get("linked_interface_id"),
            semantic_hint=data.get("semantic_hint")
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
    canonical_evidence: List[Any] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["failing_tests"] = [t.to_dict() for t in self.failing_tests]
        d["canonical_evidence"] = [
            e.to_dict() if hasattr(e, "to_dict") else e
            for e in self.canonical_evidence
        ]
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DiagnosticEvidence:
        failing_tests = [
            FailingTest.from_dict(t) if isinstance(t, dict) else t
            for t in data.get("failing_tests", [])
        ]
        raw_canonical = data.get("canonical_evidence", [])
        canonical_items = []
        if CanonicalImplementationEvidence is not None:
            for item in raw_canonical:
                if isinstance(item, dict):
                    canonical_items.append(CanonicalImplementationEvidence.from_dict(item))
                else:
                    canonical_items.append(item)
        else:
            canonical_items = list(raw_canonical)

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
            environment_warnings=list(data.get("environment_warnings", [])),
            canonical_evidence=canonical_items
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
            if not exc_match:
                exc_match = re.search(r"^\s*([A-Za-z]\w*(?:Error|Exception))(?::\s*(.*))?$", cleaned_text, re.MULTILINE)
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

        canonical_items: List[Any] = []
        if CanonicalImplementationEvidence is not None:
            for ft in failing_tests:
                ev_type = "IMPORT_RESOLUTION_ERROR" if "import" in ft.failure_type else "COMPILATION_ERROR"
                ev_id = CanonicalImplementationEvidence.make_id("pytest_collection", ev_type, ft.test_file, ft.test_line)
                canonical_items.append(CanonicalImplementationEvidence(
                    evidence_id=ev_id,
                    evidence_type=ev_type,
                    source="pytest_collection",
                    file_reference=ft.test_file,
                    line_reference=ft.test_line,
                    diagnostic_message=ft.message,
                    compatibility_status="INCOMPATIBLE",
                    provenance="COMPILER",
                    confidence=ft.confidence,
                    caller_site=ft.test_file,
                    causal_status="PROVEN"
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
            environment_warnings=warnings,
            canonical_evidence=canonical_items
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

        ft = FailingTest(
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
        )
        ft.semantic_hint = infer_semantic_hint(ft)
        failing_tests.append(ft)
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

    canonical_items: List[Any] = []
    if CanonicalImplementationEvidence is not None:
        for ft in failing_tests:
            ev_type = "BEHAVIORAL_ASSERTION"
            compat = "INCOMPATIBLE"
            msg_lower = (ft.message or "").lower()
            tb_lower = (ft.traceback_excerpt or "").lower()
            combined = f"{msg_lower} {tb_lower}"

            if "takes" in combined and "positional argument" in combined:
                if "__init__" in combined or "model" in combined or "constructor" in combined:
                    ev_type = "CONSTRUCTOR_MISMATCH"
                else:
                    ev_type = "SIGNATURE_MISMATCH"
            elif "no attribute" in combined or "not defined" in combined:
                ev_type = "SYMBOL_NOT_FOUND"
                compat = "NOT_FOUND"
            elif "no module named" in combined or "cannot import name" in combined:
                ev_type = "IMPORT_RESOLUTION_FAILURE"
                compat = "NOT_FOUND"
            elif "422" in combined or "validation error" in combined or "unprocessable" in combined:
                ev_type = "SCHEMA_VALIDATION_ERROR"
            elif "typeerror" in combined:
                ev_type = "TYPE_INCOMPATIBILITY"
            elif ft.failure_type == "compilation_error" or "syntaxerror" in combined:
                ev_type = "COMPILATION_ERROR"
            elif ft.failure_type == "assertion_failure":
                ev_type = "BEHAVIORAL_ASSERTION"
            else:
                ev_type = "RUNTIME_EXCEPTION"

            sym = ft.source_symbol
            if not sym:
                m_sym = re.search(r"(?:attribute|name|function|class|symbol)\s*['\"]([^'\"]+)['\"]", ft.message or "")
                if m_sym:
                    sym = m_sym.group(1)

            ref_file = ft.source_file or ft.test_file or "unknown"
            ref_line = ft.source_line or ft.test_line
            ev_id = CanonicalImplementationEvidence.make_id("pytest", ev_type, ref_file, ref_line, sym)

            canonical_items.append(CanonicalImplementationEvidence(
                evidence_id=ev_id,
                evidence_type=ev_type,
                source="pytest",
                file_reference=ref_file,
                line_reference=ref_line,
                symbol_reference=sym,
                observed=ft.actual or ft.message[:150],
                expected=ft.expected or "Valid execution without exception",
                compatibility_status=compat,
                diagnostic_message=ft.message,
                provenance="RUNTIME",
                confidence=ft.confidence,
                caller_site=f"{ft.test_file}:{ft.test_line}" if ft.test_line else None,
                callee_site=f"{ft.source_file}:{ft.source_line}" if ft.source_line else None,
                causal_status="PROVEN" if ft.source_file else "UNKNOWN"
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
        environment_warnings=warnings,
        canonical_evidence=canonical_items
    )


# ===========================================================================
# 6. Dart / Flutter Syntax & Bracket Balance Diagnostic Engine
# ===========================================================================

@dataclass
class DartSyntaxDiagnostic:
    file_path: str
    line: int
    column: int
    offending_token: str
    issue: str  # "orphan_closing_delimiter", "mismatched_closing_delimiter", "unclosed_opening_delimiter"
    expected_opener: Optional[str] = None
    actual_opener: Optional[str] = None
    opener_line: Optional[int] = None
    likely_cause: str = ""

    def format_diagnostic_block(self) -> str:
        lines = [
            "[DART SYNTAX DIAGNOSTIC]",
            f"File: {self.file_path}",
            f"Line: {self.line}",
            f"Token: {self.offending_token}",
            f"Issue: {self.issue.replace('_', ' ')}",
            f"Likely cause: {self.likely_cause}"
        ]
        return "\n".join(lines)


def tokenize_dart_delimiters(code: str) -> List[Tuple[str, int, int, int]]:
    """
    Memindai kode sumber Dart untuk mengekstrak token delimiter '(', ')', '[', ']', '{', '}'.
    Mengabaikan komentar baris (//), komentar blok (/* */ termasuk nested),
    string literal (tunggal, ganda, raw r'...', triple quotes '''/\"\"\"),
    dan menangani string interpolation (${...}) dengan transisi state scope.
    
    Mengembalikan list of (char, line, col, index).
    """
    n = len(code)
    i = 0
    line = 1
    col = 1
    scope_stack: List[Tuple[str, str, bool, int]] = []  # ('STRING'/'INTERP', quote_type, is_raw, interp_depth)
    delimiters: List[Tuple[str, int, int, int]] = []

    while i < n:
        ch = code[i]
        curr_line = line
        curr_col = col

        if ch == '\n':
            line += 1
            col = 1
        else:
            col += 1

        if scope_stack and scope_stack[-1][0] == 'STRING':
            _, quote_type, is_raw, interp_depth = scope_stack[-1]
            q_len = len(quote_type)

            if not is_raw and ch == '\\' and i + 1 < n:
                i += 2
                col += 1
                continue

            if not is_raw and ch == '$' and i + 1 < n and code[i + 1] == '{':
                delimiters.append(('{', curr_line, curr_col, i))
                scope_stack[-1] = ('INTERP', quote_type, is_raw, 1)
                i += 2
                col += 1
                continue

            if code[i:i + q_len] == quote_type:
                scope_stack.pop()
                i += q_len
                col += (q_len - 1)
                continue

            i += 1
            continue

        if scope_stack and scope_stack[-1][0] == 'INTERP':
            _, quote_type, is_raw, interp_depth = scope_stack[-1]
            if ch == '{':
                delimiters.append(('{', curr_line, curr_col, i))
                scope_stack[-1] = ('INTERP', quote_type, is_raw, interp_depth + 1)
                i += 1
                continue
            elif ch == '}':
                delimiters.append(('}', curr_line, curr_col, i))
                if interp_depth == 1:
                    scope_stack[-1] = ('STRING', quote_type, is_raw, 0)
                else:
                    scope_stack[-1] = ('INTERP', quote_type, is_raw, interp_depth - 1)
                i += 1
                continue

        if ch == '/' and i + 1 < n and code[i + 1] == '/':
            i += 2
            col += 1
            while i < n and code[i] != '\n':
                i += 1
                col += 1
            continue

        if ch == '/' and i + 1 < n and code[i + 1] == '*':
            comment_depth = 1
            i += 2
            col += 1
            while i < n and comment_depth > 0:
                if code[i] == '\n':
                    line += 1
                    col = 1
                    i += 1
                elif code[i] == '/' and i + 1 < n and code[i + 1] == '*':
                    comment_depth += 1
                    i += 2
                    col += 2
                elif code[i] == '*' and i + 1 < n and code[i + 1] == '/':
                    comment_depth -= 1
                    i += 2
                    col += 2
                else:
                    i += 1
                    col += 1
            continue

        is_raw = False
        if ch == 'r' and i + 1 < n and code[i + 1] in ("'", '"'):
            is_raw = True
            i += 1
            col += 1
            ch = code[i]

        if ch in ("'", '"'):
            if i + 2 < n and code[i:i + 3] == ch * 3:
                quote_type = ch * 3
                i += 3
                col += 2
                scope_stack.append(('STRING', quote_type, is_raw, 0))
                continue
            else:
                quote_type = ch
                i += 1
                scope_stack.append(('STRING', quote_type, is_raw, 0))
                continue

        if ch in ('(', '[', '{', ')', ']', '}'):
            delimiters.append((ch, curr_line, curr_col, i))

        i += 1

    return delimiters


def analyze_dart_bracket_balance(code_str: str, file_path: str = "") -> List[DartSyntaxDiagnostic]:
    """
    Menganalisis keseimbangan delimiter (), [], {} pada kode Dart.
    Mengembalikan daftar DartSyntaxDiagnostic untuk setiap ketidakseimbangan yang terdeteksi.
    Fokus utama: mendeteksi lokasi pelanggaran pertama secara deterministik.
    """
    delims = tokenize_dart_delimiters(code_str)
    stack: List[Tuple[str, int, int, int]] = []
    matching = {')': '(', ']': '[', '}': '{'}
    matching_rev = {'(': ')', '[': ']', '{': '}'}
    diagnostics: List[DartSyntaxDiagnostic] = []

    for d, l, c, idx in delims:
        if d in ('(', '[', '{'):
            stack.append((d, l, c, idx))
        elif d in (')', ']', '}'):
            expected_open = matching[d]
            if not stack:
                diagnostics.append(DartSyntaxDiagnostic(
                    file_path=file_path,
                    line=l,
                    column=c,
                    offending_token=d,
                    issue="orphan_closing_delimiter",
                    expected_opener=None,
                    actual_opener=None,
                    opener_line=None,
                    likely_cause=f"duplicate or rogue closing delimiter '{d}' with no matching opening delimiter in widget tree"
                ))
            elif stack[-1][0] != expected_open:
                opener, op_line, op_col, _ = stack[-1]
                expected_close = matching_rev.get(opener, "?")
                diagnostics.append(DartSyntaxDiagnostic(
                    file_path=file_path,
                    line=l,
                    column=c,
                    offending_token=d,
                    issue="mismatched_closing_delimiter",
                    expected_opener=opener,
                    actual_opener=None,
                    opener_line=op_line,
                    likely_cause=(
                        f"closing '{d}' encountered while opening '{opener}' (line {op_line}) is still open. "
                        f"Likely duplicate closing bracket in nested widget tree or wrong delimiter type (expected '{expected_close}')."
                    )
                ))
            else:
                stack.pop()

    if not diagnostics and stack:
        for opener, op_line, op_col, _ in stack:
            expected_close = matching_rev.get(opener, "?")
            diagnostics.append(DartSyntaxDiagnostic(
                file_path=file_path,
                line=op_line,
                column=op_col,
                offending_token=opener,
                issue="unclosed_opening_delimiter",
                expected_opener=opener,
                actual_opener=None,
                opener_line=op_line,
                likely_cause=f"opening '{opener}' at line {op_line} was never closed (missing '{expected_close}')"
            ))

    return diagnostics


# ===========================================================================
# 6.2. Dart / Flutter Test Output Parser Engine
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
        # Cek apakah ada delimiter diagnostic pada code_files
        bracket_diags: List[DartSyntaxDiagnostic] = []
        if code_files:
            for c_name, c_content in code_files.items():
                if c_name.endswith(".dart"):
                    diags = analyze_dart_bracket_balance(c_content, file_path=c_name)
                    if diags:
                        bracket_diags.extend(diags)

        failing_tests: List[FailingTest] = []
        canonical_items: List[Any] = []
        default_test_file = list(test_files.keys())[0] if test_files else "test_file.dart"

        for match in compilation_errors:
            f_path = normalize_file_path(match.group(1))
            line_no = int(match.group(2))
            col_no = int(match.group(3))
            err_msg = match.group(4).strip()

            is_test = is_test_file_path(f_path)
            tfile = f_path if is_test else default_test_file
            tline = line_no if is_test else None
            sfile = f_path if not is_test else None
            sline = line_no if not is_test else None

            # Cek apakah error kompilasi berkaitan dengan delimiter / cascade
            is_delimiter_related = any(k in err_msg.lower() for k in (
                "can't find ')'", "can't find ']'", "can't find '}'",
                "expected an identifier, but got ']'", "expected an identifier, but got ')'",
                "expected an identifier, but got '}'", "expected to find ')'", "expected to find ']'",
                "expected to find '}'", "unmatched '("
            ))

            msg = f"Compilation Error: {err_msg}"
            source_l = sline
            hint = None

            # Ekstrak simbol dan klasifikasi kanonikal
            ev_type = "COMPILATION_ERROR"
            ev_sym = None
            if "member not found:" in err_msg.lower():
                ev_type = "SYMBOL_NOT_FOUND"
                m_sym = re.search(r"member not found:\s*'([^']+)'", err_msg, re.IGNORECASE)
                if m_sym:
                    ev_sym = m_sym.group(1)
            elif "no named parameter" in err_msg.lower():
                ev_type = "CONSTRUCTOR_MISMATCH"
                m_param = re.search(r"no named parameter with the name\s*'([^']+)'", err_msg, re.IGNORECASE)
                if m_param:
                    ev_sym = m_param.group(1)

            # Jika ada bracket diagnostic yang cocok dengan file sumber
            matching_diag = None
            if bracket_diags and sfile:
                for bd in bracket_diags:
                    if bd.file_path == sfile or Path(bd.file_path).name == Path(sfile).name:
                        matching_diag = bd
                        break

            if matching_diag:
                source_l = matching_diag.line
                msg += f"\n\n{matching_diag.format_diagnostic_block()}"
                hint = HINT_DART_BRACKET_CASCADE
            elif is_delimiter_related:
                hint = HINT_DART_BRACKET_CASCADE

            t_name_desc = f"compilation_{ev_type.lower()}" if ev_sym is None else f"compilation_{ev_sym}"
            ft = FailingTest(
                test_name=t_name_desc,
                test_file=tfile,
                test_line=tline,
                failure_type="compilation_error",
                message=msg,
                source_file=sfile,
                source_line=source_l,
                source_symbol=ev_sym,
                traceback_excerpt=f"{f_path}:{line_no}:{col_no}: Error: {err_msg}",
                confidence=1.0,
                semantic_hint=hint
            )
            failing_tests.append(ft)

            if CanonicalImplementationEvidence is not None:
                ev_id = CanonicalImplementationEvidence.make_id(
                    "dart_compiler", ev_type, f_path, line_no, ev_sym
                )
                canonical_items.append(CanonicalImplementationEvidence(
                    evidence_id=ev_id,
                    evidence_type=ev_type,
                    source="dart_compiler",
                    file_reference=f_path,
                    line_reference=line_no,
                    symbol_reference=ev_sym,
                    observed=err_msg,
                    expected="Valid symbol and matching constructor parameter in SDK/declaration",
                    compatibility_status="INCOMPATIBLE" if ev_type != "SYMBOL_NOT_FOUND" else "NOT_FOUND",
                    diagnostic_message=err_msg,
                    provenance="COMPILER",
                    confidence=1.0,
                    caller_site=f"{f_path}:{line_no}:{col_no}" if is_test else None,
                    callee_site=f"{f_path}:{line_no}:{col_no}" if not is_test else None,
                    causal_status="PROVEN"
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
            environment_warnings=warnings,
            canonical_evidence=canonical_items
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

    default_test_file = list(test_files.keys())[0] if test_files else "test/widget_test.dart"

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
            test_file=default_test_file,
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
                test_file=default_test_file,
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
            test_file=default_test_file,
            failure_type="unknown",
            message=f"Dart test execution failed with exit code {exit_code}",
            confidence=0.0
        ))

    canonical_items: List[Any] = []
    if CanonicalImplementationEvidence is not None:
        for ft in failing_tests:
            ev_type = "BEHAVIORAL_ASSERTION" if ft.failure_type == "assertion_failure" else "RUNTIME_EXCEPTION"
            ev_id = CanonicalImplementationEvidence.make_id(
                "flutter_test", ev_type, ft.test_file, ft.test_line, ft.source_symbol
            )
            canonical_items.append(CanonicalImplementationEvidence(
                evidence_id=ev_id,
                evidence_type=ev_type,
                source="flutter_test",
                file_reference=ft.test_file,
                line_reference=ft.test_line,
                symbol_reference=ft.source_symbol,
                observed=ft.actual or ft.message,
                expected=ft.expected,
                compatibility_status="INCOMPATIBLE",
                diagnostic_message=ft.message,
                provenance="RUNTIME",
                confidence=ft.confidence,
                caller_site=f"{ft.test_file}:{ft.test_line}" if ft.test_line else None,
                causal_status="CORRELATED"
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
        environment_warnings=warnings,
        canonical_evidence=canonical_items
    )


# ===========================================================================
# 7. Semantic Diagnostic Guidance Engine (P0-1)
# ===========================================================================

HINT_HTTP_422 = (
    "[ACTIONABLE HINT]\n"
    "HTTP 422 indicates request validation failure.\n"
    "Inspect the request payload against the Pydantic schema.\n"
    "Check which required field(s) are absent or incompatible.\n"
    "Consider whether server-generated fields should be optional or have defaults."
)

HINT_MATRIX_DIMENSIONS = (
    "[ACTIONABLE HINT]\n"
    "The failure indicates incompatible matrix dimensions.\n"
    "Inspect the dimensionality/shape validation performed by the\n"
    "operation and compare it with the expected valid and invalid cases.\n"
    "Ensure invalid dimensions are rejected according to the contract."
)

HINT_DART_BRACKET_CASCADE = (
    "[ACTIONABLE HINT]\n"
    "Dart compilation failed due to mismatched delimiters (brackets/parentheses).\n"
    "NOTE: Compiler errors pointing to outer widgets (e.g. \"Can't find ')' to match '('\") "
    "are cascade errors caused by an extra, missing, or wrong delimiter deeper in the widget tree.\n"
    "Check the [DART SYNTAX DIAGNOSTIC] above:\n"
    "1. Inspect the exact line and token flagged.\n"
    "2. Check if a closing delimiter was duplicated (e.g. extra '],') or used instead of '),'.\n"
    "3. Ensure every opening '(' and '[' is closed exactly once with matching ')' and ']'."
)

HINT_GROUNDING_UNDEFINED_SYMBOL = (
    "[GROUNDING HINT]\n"
    "Simbol/API yang digunakan tidak terdefinisi pada versi library/runtime aktif.\n"
    "Tindakan: Periksa ENVIRONMENT FACT CARD dan gunakan pola kanonikal resmi."
)


def infer_semantic_hint(test: FailingTest) -> Optional[str]:
    """
    Menghasilkan petunjuk diagnostik semantik yang deterministik dan rule-based (P0-1).
    Prinsip:
    - Membantu Developer menjawab 'Apa yang harus saya periksa?', BUKAN memberikan solusi kode.
    - Zero Solution Leak: tidak membocorkan patch atau hardcode kode spesifik (misal: Optional[int] = None).
    - Preservasi deterministik: tidak menggunakan LLM, bebas efek samping.
    """
    message_str = test.message or ""
    actual_str = test.actual or ""
    expected_str = test.expected or ""
    trace_str = test.traceback_excerpt or ""
    name_str = test.test_name or ""

    full_corpus = f"{name_str} {message_str} {actual_str} {expected_str} {trace_str}"
    full_lower = full_corpus.lower()

    # 1. FastAPI / HTTP 422 Request Validation Failure
    is_422 = (
        actual_str == "422"
        or "422" in actual_str
        or "assert 422 ==" in message_str
        or "assert 422 ==" in trace_str
        or "where 422 =" in trace_str
        or "status 422" in full_lower
        or "code 422" in full_lower
        or "422 unprocessable" in full_lower
        or "unprocessable entity" in full_lower
        or "unprocessable content" in full_lower
    )
    if is_422:
        return HINT_HTTP_422

    # 2. CLI / Matrix Dimensional Validation Failure
    is_dim_error = (
        "dimension mismatch" in full_lower
        or "shape mismatch" in full_lower
        or "incompatible dimension" in full_lower
        or "incompatible dimensions" in full_lower
        or "incompatible_dimension" in full_lower
        or (
            ("valueerror" in full_lower or "did not raise valueerror" in full_lower)
            and any(k in full_lower for k in ("dimension", "shape", "incompatible", "matrix", "column", "row"))
        )
        or (
            test.failure_type in ("runtime_exception", "assertion_failure")
            and "matrix" in full_lower
            and any(k in full_lower for k in ("incompatible", "dimension", "shape"))
        )
    )
    if is_dim_error:
        return HINT_MATRIX_DIMENSIONS

    # 3. Dart / Flutter Delimiter & Cascade Bracket Compilation Error
    is_dart_bracket_cascade = (
        ("can't find ')'" in full_lower or 'can\'t find ")"' in full_lower)
        or ("can't find ']'" in full_lower or 'can\'t find "]"' in full_lower)
        or ("can't find '}'" in full_lower or 'can\'t find "}"' in full_lower)
        or "expected an identifier, but got ']'" in full_lower
        or "expected an identifier, but got ')'" in full_lower
        or "expected an identifier, but got '}'" in full_lower
        or "expected to find ')'" in full_lower
        or "expected to find ']'" in full_lower
        or "expected to find '}'" in full_lower
        or "unmatched '('" in full_lower
        or "unmatched '['" in full_lower
        or "unmatched '{'" in full_lower
        or "[dart syntax diagnostic]" in full_lower
        or (
            ("bracket" in full_lower or "delimiter" in full_lower or "parenthes" in full_lower)
            and ("mismatch" in full_lower or "unbalanced" in full_lower or "cascade" in full_lower)
        )
    )
    if is_dart_bracket_cascade:
        return HINT_DART_BRACKET_CASCADE

    # 4. Undefined Symbol / Deprecated API / Grounding Mismatch
    is_grounding_issue = (
        ("isn't defined" in full_lower or "isn't a type" in full_lower)
        or ("cannot import name" in full_lower or "has no attribute" in full_lower)
        or ("not defined" in full_lower and "name" in full_lower)
    )
    if is_grounding_issue:
        return HINT_GROUNDING_UNDEFINED_SYMBOL

    return None


# ===========================================================================
# 8. Multi-Failure Top-3 Prioritization & Targeted Feedback Builder
# ===========================================================================

def prioritize_failures(
    failing_tests: List[FailingTest],
    max_selected: int = 3
) -> Tuple[List[FailingTest], List[FailingTest]]:
    """
    Mengurutkan kegagalan berdasarkan hierarki taksonomi keparahan,
    mencegah 'error starvation' dengan memastikan kategori/simbol independen
    terwakili secara beragam, dan memisahkan menjadi selected prioritas serta sisa omitted.
    """
    if not failing_tests:
        return [], []

    sorted_tests = sorted(
        failing_tests,
        key=lambda t: TAXONOMY_PRIORITY.get(t.failure_type, 99)
    )

    selected: List[FailingTest] = []
    omitted: List[FailingTest] = []
    seen_signatures = set()

    # Pass 1: Select distinct (failure_type, source_symbol or source_file, key_message)
    for t in sorted_tests:
        sig_msg = (t.message or "")[:60].strip()
        sig = (t.failure_type, t.source_symbol or t.source_file or "", sig_msg)
        if sig not in seen_signatures:
            seen_signatures.add(sig)
            if len(selected) < max_selected:
                selected.append(t)
            else:
                omitted.append(t)
        else:
            omitted.append(t)

    # Pass 2: If we still have slots under max_selected and omitted has items, fill remaining
    if len(selected) < max_selected and omitted:
        remaining_slots = max_selected - len(selected)
        selected.extend(omitted[:remaining_slots])
        omitted = omitted[remaining_slots:]

    return selected, omitted


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


# ===========================================================================
# 8.5. Improved Repentance & Diagnostic Guidance Engine
# ===========================================================================

def infer_root_cause_and_direction(
    test: FailingTest,
    framework: str = "pytest",
    contract: Optional[Dict[str, Any]] = None
) -> Tuple[str, str, str, str]:
    """
    Menyimpulkan secara deterministik:
    (root_cause, affected_constraint, required_direction, preservation_rule)
    mengikuti Rule 1 (Root-cause aligned), Rule 2 (Terminology aligned),
    Rule 3 (Single-sin focus), dan Rule 4 (Global constraint preservation).
    """
    msg = (test.message or "").strip()
    tb = (test.traceback_excerpt or "").strip()
    full_text = f"{msg}\n{tb}".lower()
    tname = (test.test_name or "").lower()

    # Kontrak referensi jika ada
    contract_ref = ""
    c_aid = test.linked_assertion_id
    c_rid = test.linked_req_id
    c_ifid = test.linked_interface_id
    if not c_aid and contract:
        c_aid, c_rid, c_ifid = map_evidence_to_contract(test, contract)
    if c_aid:
        contract_ref = f" [Kontrak: Assertion {c_aid}"
        if c_rid:
            contract_ref += f" / Req {c_rid}"
        if c_ifid:
            contract_ref += f" / Interface {c_ifid}"
        contract_ref += "]"

    # 1. Missing Type / Class Declaration (Dart MetricData or similar)
    if (
        "method not found: 'metricdata'" in full_text
        or "isn't a type and can't be used as a type" in full_text
        or ("not found" in full_text and "metricdata" in full_text)
        or ("undefined class" in full_text and "metricdata" in full_text)
        or "the getter 'data' isn't defined" in full_text
    ):
        root_cause = "Tipe data 'MetricData' digunakan oleh consumer/widget tetapi deklarasi kelas tersebut belum tersedia atau belum terdefinisi dalam scope file."
        affected_constraint = f"Model data 'MetricData' dan widget 'CardMetric(data: MetricData)'{contract_ref}"
        required_direction = "Deklarasikan kelas 'MetricData' secara lengkap dengan atribut yang dibutuhkan (seperti title, value, change, isPositive) dan pastikan dapat diakses oleh widget 'CardMetric'."
        preservation_rule = "Pertahankan nama kelas 'CardMetric', nama parameter 'data', dan tipe 'MetricData'. DILARANG mengubah konstruktor menjadi CardMetric({super.key}) atau mengganti nama tipe!"
        return root_cause, affected_constraint, required_direction, preservation_rule

    # 2. Dart Constructor Parameter Mismatch (e.g. 'No named parameter with the name color')
    m_named_param = re.search(r"no named parameter with the name ['\"]([a-zA-Z0-9_]+)['\"]", full_text)
    if m_named_param:
        param_name = m_named_param.group(1)
        root_cause = f"Konstruktor dipanggil dengan named parameter '{param_name}', namun deklarasi konstruktor tidak menerima parameter tersebut."
        affected_constraint = f"Parameter konstruktor '{param_name}'{contract_ref}"
        required_direction = f"Tambahkan parameter bernama '{param_name}' ke dalam tanda tangan konstruktor dengan tipe yang sesuai dan simpan ke field instance."
        preservation_rule = f"Pertahankan seluruh parameter konstruktor yang sudah ada sebelumnya. DILARANG menghapus parameter yang sudah didukung!"
        return root_cause, affected_constraint, required_direction, preservation_rule

    # 3. Dart Delimiter / Bracket Cascade
    if (
        "bracket" in full_text or "delimiter" in full_text
        or "can't find '}' to match '{" in full_text
        or "expected to find '}'" in full_text
        or "expected to find ')'" in full_text
        or "unbalanced bracket" in full_text
    ):
        root_cause = "Terdapat ketidakseimbangan tanda kurung (curly braces/parentheses) yang menyebabkan kegagalan kompilasi sintaksis Dart."
        affected_constraint = f"Struktur blok sintaksis kode Dart{contract_ref}"
        required_direction = "Periksa dan hitung kesesuaian setiap kurung pembuka '(', '{', '[' dengan kurung penutup ')', '}', ']'. Tutup semua blok widget dengan presisi."
        preservation_rule = "Pertahankan seluruh implementasi method build dan logika widget tanpa menghapus method/kelas secara sembarangan."
        return root_cause, affected_constraint, required_direction, preservation_rule

    # 4. Python Missing Import (e.g. field_validator, BaseModel, FastAPI)
    m_name_err = re.search(r"name ['\"]([a-zA-Z0-9_]+)['\"] is not defined", full_text)
    if "nameerror" in full_text and m_name_err:
        sym = m_name_err.group(1)
        if sym == "field_validator":
            root_cause = f"Dekorator '@{sym}' digunakan untuk validasi model Pydantic v2, tetapi simbol '{sym}' belum diimpor dari modul 'pydantic'."
            affected_constraint = f"Validasi skema DTO Pydantic v2 (@{sym}){contract_ref}"
            required_direction = f"Tambahkan '{sym}' ke dalam statement impor: 'from pydantic import BaseModel, {sym}, ...'."
            preservation_rule = "Pertahankan seluruh aturan validasi field dan tipe data pada DTO Pydantic tanpa menghapus dekorator validasi."
            return root_cause, affected_constraint, required_direction, preservation_rule
        elif sym in ("app", "fastapi"):
            root_cause = f"Simbol '{sym}' digunakan sebagai instance aplikasi FastAPI tetapi belum diinisialisasi atau diimpor."
            affected_constraint = f"Inisialisasi aplikasi FastAPI{contract_ref}"
            required_direction = "Pastikan 'from fastapi import FastAPI' dan inisialisasi 'app = FastAPI()' berada di level root file sebelum route didefinisikan."
            preservation_rule = "Pertahankan nama instance 'app' dan seluruh route endpoint HTTP yang telah dideklarasikan."
            return root_cause, affected_constraint, required_direction, preservation_rule
        elif sym == "Field":
            root_cause = f"Simbol '{sym}' digunakan untuk mendefinisikan batasan field model Pydantic tetapi belum diimpor."
            affected_constraint = f"Definisi model field Pydantic{contract_ref}"
            required_direction = "Tambahkan 'Field' ke dalam statement import pydantic: 'from pydantic import BaseModel, Field, ...'."
            preservation_rule = "Pertahankan batasan validasi field (misal: gt=0, min_length=1)."
            return root_cause, affected_constraint, required_direction, preservation_rule
        else:
            root_cause = f"Simbol '{sym}' digunakan namun belum diimpor atau dideklarasikan secara lokal."
            affected_constraint = f"Resolusi simbol '{sym}'{contract_ref}"
            required_direction = f"Periksa apakah '{sym}' berasal dari pustaka standar atau kelas lokal, dan tambahkan statement import/deklarasi yang sesuai."
            preservation_rule = f"Pertahankan pemanggilan simbol '{sym}' pada titik kode yang membutuhkannya."
            return root_cause, affected_constraint, required_direction, preservation_rule

    # 5. HTTP 422 Unprocessable Entity (FastAPI Schema Validation Failure)
    if "422" in full_text or "unprocessable" in full_text:
        root_cause = "Data payload JSON yang dikirimkan test runner ditolak oleh validasi skema Pydantic (HTTP 422 Unprocessable Entity)."
        affected_constraint = f"Skema validasi DTO input (Pydantic model) dan deserialisasi request body{contract_ref}"
        required_direction = "Periksa field-field DTO (misal: nama field, tipe integer/float/string, optional vs required). Pastikan payload uji (seperti name, quantity, price) dapat diparse tanpa menimbulkan ValidationError."
        preservation_rule = "Pertahankan path routing endpoint, HTTP status code sukses (201 untuk create, 200 untuk read/update), dan struktur response model."
        return root_cause, affected_constraint, required_direction, preservation_rule

    # 6. Matrix / Dimensional Validation Error (CLI T1)
    if "dimension" in full_text or "shape" in full_text or ("matrix" in full_text and "valueerror" in full_text):
        root_cause = "Operasi matriks gagal memvalidasi kesesuaian dimensi operand (baris vs kolom) atau gagal memicu ValueError pada dimensi yang tidak kompatibel."
        affected_constraint = f"Validasi dimensi aljabar linear pada kelas 'Matrix'{contract_ref}"
        required_direction = "Pastikan perkalian matriks memvalidasi cols(A) == rows(B), dan penjumlahan memvalidasi rows(A) == rows(B) serta cols(A) == cols(B). Naikkan ValueError jika dimensi tidak sesuai."
        preservation_rule = "Pertahankan nama kelas 'Matrix', method dunder (__add__, __mul__, dll.) dan method publik (rows, cols, add, multiply) sesuai kontrak spesifikasi."
        return root_cause, affected_constraint, required_direction, preservation_rule

    # 7. Assertion Failure (Expected vs Actual)
    if test.expected is not None and test.actual is not None:
        root_cause = f"Hasil eksekusi logika fungsi mengembalikan '{test.actual}', padahal nilai yang diekspektasikan adalah '{test.expected}'."
        affected_constraint = f"Logika nilai kembalian pada {test.source_symbol or test.test_name}{contract_ref}"
        required_direction = f"Sesuaikan alur komputasi atau format luaran agar menghasilkan nilai yang tepat sesuai ekspektasi pengujian ('{test.expected}')."
        preservation_rule = "Pertahankan signature fungsi dan penanganan kasus batas (edge cases) yang sudah benar."
        return root_cause, affected_constraint, required_direction, preservation_rule

    # 8. Generic Fallback Root Cause
    root_cause = f"Eksekusi pengujian '{test.test_name}' gagal dengan galat tipe '{test.failure_type}'."
    affected_constraint = f"Pengujian '{test.test_name}'{contract_ref}"
    required_direction = "Analisis pesan galat dan cuplikan traceback berikut untuk mengidentifikasi baris kode yang mengalami kegagalan."
    preservation_rule = "Pertahankan antarmuka publik dan integrasi modul yang sudah sesuai spesifikasi."
    return root_cause, affected_constraint, required_direction, preservation_rule


def build_repentance_guidance(
    evidence: DiagnosticEvidence,
    iteration: int,
    max_iterations: int = 10,
    contract: Optional[Dict[str, Any]] = None,
    repair_history: Optional[List[Dict[str, Any]]] = None,
    known_good_constraints: Optional[List[str]] = None,
    failed_strategies: Optional[List[Dict[str, Any]]] = None,
    run_id: Optional[str] = None
) -> str:
    """
    Menyusun Improved Repentance Guidance 7-langkah:
    1. Actual Error
    2. Root Cause
    3. Affected Constraint
    4. Required Direction
    5. Preservation Rule
    6. Previous Failed Attempt
    7. Verification
    """
    if evidence.execution_status == "passed":
        return ""

    failing_tests = evidence.failing_tests or []
    top_failure = failing_tests[0] if failing_tests else FailingTest(
        test_name="general_execution_failure",
        test_file="unknown",
        message=evidence.summary_line or "Test suite execution failed."
    )

    root_cause, affected_constraint, required_direction, preservation_rule = infer_root_cause_and_direction(
        top_failure,
        framework=evidence.framework,
        contract=contract
    )

    # 1. ACTUAL ERROR
    err_desc = top_failure.message or evidence.summary_line or "Execution failed"
    if len(err_desc) > 300:
        err_desc = err_desc[:290] + "..."

    actual_error_block = (
        f"Uji '{top_failure.test_name}' ({top_failure.test_file}) GAGAL pada framework {evidence.framework}.\n"
        f"Detail: {err_desc}"
    )
    if top_failure.expected is not None and top_failure.actual is not None:
        actual_error_block += f"\nEkspektasi: {top_failure.expected} | Aktual: {top_failure.actual}"

    # 6. PREVIOUS FAILED ATTEMPT
    previous_attempt_block = ""
    if repair_history and len(repair_history) > 0:
        last_rep = repair_history[-1]
        last_loop = last_rep.get("loop", iteration - 1)
        last_res = last_rep.get("result", "FAILED")
        last_err = last_rep.get("error_message", "")

        # Cek apakah ada pengulangan kegagalan yang sama (Rule 5)
        is_repeated = False
        if last_err and (last_err[:50] in err_desc or err_desc[:50] in last_err):
            is_repeated = True
        if last_res == "STAGNANT":
            is_repeated = True

        if is_repeated:
            previous_attempt_block = (
                f"⚠️ PERINGATAN REPETISI / STAGNASI (Loop {last_loop}): Pendekatan yang Anda coba pada "
                f"Loop {last_loop} menghasilkan error/kondisi yang persis sama. Strategi sebelumnya TIDAK "
                f"menyelesaikan masalah. DILARANG mengulangi kode atau pola yang sama persis! Anda WAJIB "
                f"mengubah strategi perbaikan sesuai [REQUIRED DIRECTION] di atas."
            )
        elif last_res == "REGRESSED":
            previous_attempt_block = (
                f"⚠️ PERINGATAN REGRESI (Loop {last_loop}): Perubahan terakhir justru menyebabkan penurunan "
                f"jumlah test yang lolos ({last_rep.get('test_passed_count', 0)} passed -> {evidence.passed_tests} passed). "
                f"Periksa kembali perubahan Anda dan kembalikan bagian yang sebelumnya sudah benar!"
            )
        elif last_res == "IMPROVED":
            previous_attempt_block = (
                f"ℹ️ PROGRES POSITIF (Loop {last_loop}): Terjadi kemajuan ({evidence.passed_tests}/{evidence.total_tests} passed). "
                f"Pertahankan perbaikan yang berhasil dan selesaikan sisa masalah di atas tanpa mengubah fungsionalitas yang sudah hijau."
            )
        else:
            previous_attempt_block = (
                f"ℹ️ Loop {last_loop} belum menyelesaikan seluruh constraint ({evidence.passed_tests}/{evidence.total_tests} passed). "
                f"Evaluasi perbedaan antara ekspektasi dan aktual secara saksama."
            )
    else:
        previous_attempt_block = (
            "ℹ️ Ini adalah putaran perbaikan pertama (Loop 1). Analisis akar masalah secara presisi sebelum menulis kode."
        )

    # 5. PRESERVATION RULE (Tambahkan known-good constraints jika ada)
    preservation_block = preservation_rule
    if known_good_constraints:
        kg_str = ", ".join(known_good_constraints[:3])
        preservation_block += f"\nConstraint/interface yang telah terbukti benar: {kg_str}."

    # 7. VERIFICATION
    verification_block = (
        "- [ ] Apakah seluruh simbol, kelas, fungsi, dan dekorator sudah diimpor dan terdefinisi?\n"
        "- [ ] Apakah tanda tangan konstruktor/fungsi cocok persis dengan pemanggil (caller)?\n"
        "- [ ] Apakah nama antarmuka, kelas, dan Target File Authoritative tetap sesuai spesifikasi?\n"
        "- [ ] Apakah perbaikan lokal ini TIDAK merusak bagian kode lain yang sudah benar (bebas regresi)?"
    )

    feedback_text = f"""[IMPROVED REPENTANCE GUIDANCE - SIKLUS PERBAIKAN {iteration}/{max_iterations}]

1. [ACTUAL ERROR]
{actual_error_block}

2. [ROOT CAUSE]
{root_cause}

3. [AFFECTED CONSTRAINT]
{affected_constraint}

4. [REQUIRED DIRECTION]
{required_direction}

5. [PRESERVATION RULE]
{preservation_block}

6. [PREVIOUS FAILED ATTEMPT]
{previous_attempt_block}

7. [VERIFICATION - CEK MANDIRI SEBELUM OUTPUT]
{verification_block}"""

    return feedback_text.strip()


def build_targeted_feedback(
    evidence: DiagnosticEvidence,
    iteration: int = 1,
    max_iterations: int = 3,
    run_id: Optional[str] = None,
    contract: Optional[Dict[str, Any]] = None,
    repair_history: Optional[List[Dict[str, Any]]] = None,
    known_good_constraints: Optional[List[str]] = None,
    failed_strategies: Optional[List[Dict[str, Any]]] = None,
    use_repentance: bool = True
) -> str:
    """
    Menyusun payload Markdown umpan balik diagnostik yang ringkas, hemat token,
    dan bebas dari kebisingan terminal mentah.
    
    KRUSIAL: Non-preskriptif! Menjelaskan apa yang gagal dan buktinya,
    TIDAK mendikte baris perbaikan kode spesifik.
    Jika mapping kontrak tersedia secara deterministik, sertakan referensi assertion/klausul.
    Jika use_repentance aktif, sertakan Improved Repentance Guidance 7-langkah.
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

        # Semantic Diagnostic Guidance (P0-1)
        hint = test.semantic_hint or infer_semantic_hint(test)
        if hint:
            for h_line in hint.splitlines():
                lines.append(f"   {h_line.strip()}")

        lines.append("")

    if omitted:
        lines.append(
            f"+ {len(omitted)} pengujian lainnya gagal dengan pola serupa. "
            f"Selesaikan 3 masalah prioritas di atas terlebih dahulu."
        )

    # Canonical Implementation Evidence (Layer 1 & 3)
    if evidence.canonical_evidence:
        lines.append("")
        lines.append("[CANONICAL IMPLEMENTATION EVIDENCE - DETERMINISTIC REALITY]")
        lines.append("Fakta berikut diverifikasi oleh tooling/compiler/runtime lingkungan aktif:")
        for cev in evidence.canonical_evidence:
            if hasattr(cev, "format_compact"):
                lines.append(f"  {cev.format_compact()}")
            elif isinstance(cev, dict):
                try:
                    from .canonical_evidence import CanonicalImplementationEvidence
                    obj = CanonicalImplementationEvidence.from_dict(cev)
                    lines.append(f"  {obj.format_compact()}")
                except Exception:
                    lines.append(f"  • {cev}")
            else:
                lines.append(f"  • {cev}")

    # Improved Repentance Guidance (P0-1 & D10)
    if use_repentance and evidence.execution_status != "passed":
        repentance_text = build_repentance_guidance(
            evidence=evidence,
            iteration=iteration,
            max_iterations=max_iterations,
            contract=contract,
            repair_history=repair_history,
            known_good_constraints=known_good_constraints,
            failed_strategies=failed_strategies,
            run_id=run_id
        )
        if repentance_text:
            lines.append("")
            lines.append(repentance_text)

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
    contract: Optional[Dict[str, Any]] = None,
    repair_history: Optional[List[Dict[str, Any]]] = None,
    known_good_constraints: Optional[List[str]] = None,
    failed_strategies: Optional[List[Dict[str, Any]]] = None,
    use_repentance: bool = True
) -> str:
    """Helper untuk menyusun targeted feedback langsung dari dictionary diagnostic_evidence."""
    try:
        evidence = DiagnosticEvidence.from_dict(evidence_dict)
        return build_targeted_feedback(
            evidence,
            iteration=iteration,
            max_iterations=max_iterations,
            run_id=run_id,
            contract=contract,
            repair_history=repair_history,
            known_good_constraints=known_good_constraints,
            failed_strategies=failed_strategies,
            use_repentance=use_repentance
        )
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
