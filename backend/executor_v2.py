"""
Executor v2: Pre-Flight Validation Layer for ReinDev Studio.

Desain Arsitektur & Prinsip Pengoperasian:
1. Mempertahankan kompatibilitas penuh (backward compatibility) dengan mode legasi:
   - 'OFF': Nol transformasi (verbatim), kode dan test tidak dimutasi sama sekali.
   - 'CODE_ONLY': Mode eksperimen Phase 2 legasi (mutasi kode, test immutable).
   - 'ON': Mode legasi penuh dengan auto-healing kode dan relaksasi test suite.
2. Memperkenalkan mode baru 'SAFE' sebagai kandidat default:
   - Menggantikan heuristik regex string rewriting global dengan analisis AST (Abstract Syntax Tree).
   - Hanya melakukan syntax validation dan safe missing-import resolution yang dapat
     dibuktikan secara deterministik dari struktur simbol/AST (e.g. BaseModel, typing, sibling classes).
   - DILARANG KERAS melakukan business-logic repair.
   - DILARANG KERAS melakukan model/schema rewriting (mencegah regresi Run 10).
   - DILARANG KERAS melakukan endpoint injection (POST/GET/DELETE).
   - DILARANG KERAS melakukan parser replacement (parse_matrix).
   - DILARANG KERAS melakukan arithmetic implementation repair (__truediv__).
   - Test files / Frozen Oracle 100% strictly immutable.
3. Observabilitas & Rollback:
   - Setiap transformasi mencatat file, before_hash, after_hash, dan alasan logis.
   - Transformasi divalidasi ulang: jika hasil pengujian memburuk atau tidak membaik,
     transformasi di-rollback secara otomatis ke artefak asli Developer.
"""

import os
import re
import sys
import time
import copy
import shutil
import subprocess
import ast
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional, Set

try:
    from .state import SquadState
    from .tracer import get_tracer, compute_dict_hashes, compute_object_hash, compute_sha256
except (ImportError, ValueError):
    try:
        from state import SquadState
        from tracer import get_tracer, compute_dict_hashes, compute_object_hash, compute_sha256
    except ImportError:
        def get_tracer(run_id=None): return None
        def compute_dict_hashes(f): return {}
        def compute_object_hash(o): return ""
        def compute_sha256(s):
            import hashlib
            return hashlib.sha256(s.encode("utf-8") if isinstance(s, str) else s).hexdigest()

try:
    from .executor import run_sandbox_tests as run_sandbox_tests_legacy, SANDBOX_DIR
except (ImportError, ValueError):
    from executor import run_sandbox_tests as run_sandbox_tests_legacy, SANDBOX_DIR

try:
    from .diagnostic_parser import parse_diagnostic, build_targeted_feedback, analyze_dart_bracket_balance, DartSyntaxDiagnostic
except (ImportError, ValueError):
    try:
        from diagnostic_parser import parse_diagnostic, build_targeted_feedback, analyze_dart_bracket_balance, DartSyntaxDiagnostic
    except ImportError:
        def parse_diagnostic(*args, **kwargs): return None
        def build_targeted_feedback(*args, **kwargs): return ""
        def analyze_dart_bracket_balance(*args, **kwargs): return []
        class DartSyntaxDiagnostic: pass


# ===========================================================================
# 1. AST & Pre-Flight Syntax Validation Engine
# ===========================================================================

def validate_python_syntax(code_str: str) -> Tuple[bool, Optional[str]]:
    """Memvalidasi integritas sintaksis Python menggunakan parser AST standar."""
    try:
        ast.parse(code_str)
        return True, None
    except SyntaxError as e:
        return False, f"SyntaxError line {e.lineno}, col {e.offset}: {e.msg}"


class PythonSymbolCollector(ast.NodeVisitor):
    """
    Mengumpulkan simbol-simbol yang didefinisikan (imported, class, function, variable)
    dan simbol-simbol yang digunakan (loaded) dalam satu file Python.
    """
    def __init__(self):
        self.defined: Set[str] = set()
        self.loaded: Set[str] = set()

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            name = alias.asname or alias.name.split(".")[0]
            self.defined.add(name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        for alias in node.names:
            name = alias.asname or alias.name
            self.defined.add(name)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        self.defined.add(node.name)
        for base in node.bases:
            if isinstance(base, ast.Name):
                self.loaded.add(base.id)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.defined.add(node.name)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.defined.add(node.name)
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name):
        if isinstance(node.ctx, ast.Store):
            self.defined.add(node.id)
        elif isinstance(node.ctx, ast.Load):
            self.loaded.add(node.id)
        self.generic_visit(node)


def detect_missing_python_imports(code_str: str, sibling_classes: Dict[str, str] = None) -> Tuple[List[str], List[str]]:
    """
    Mendeteksi impor yang hilang berdasarkan analisis AST murni.
    Hanya menyelesaikan simbol standar terverifikasi atau kelas sibling yang terbukti ada.
    Mengembalikan (missing_import_statements, explanation_reasons).
    """
    sibling_classes = sibling_classes or {}
    try:
        tree = ast.parse(code_str)
    except SyntaxError:
        return [], []

    collector = PythonSymbolCollector()
    collector.visit(tree)

    builtins_set = set(dir(__builtins__))
    PYDANTIC_SYMBOLS = {"BaseModel", "Field"}
    FASTAPI_SYMBOLS = {"FastAPI", "HTTPException", "Depends", "status", "Query", "Path", "Header", "Cookie", "Request", "Response"}
    TESTCLIENT_SYMBOLS = {"TestClient"}
    TYPING_SYMBOLS = {"List", "Dict", "Optional", "Union", "Any", "Tuple", "Set", "Callable", "Sequence", "Iterable"}

    undefined = {name for name in collector.loaded if name not in collector.defined and name not in builtins_set}

    missing_imports = []
    reasons = []

    # Resolusi simbol Pydantic
    needed_pydantic = sorted(undefined & PYDANTIC_SYMBOLS)
    if needed_pydantic:
        missing_imports.append(f"from pydantic import {', '.join(needed_pydantic)}")
        reasons.append(f"Simbol {needed_pydantic} digunakan namun belum diimpor dari pydantic")

    # Resolusi simbol FastAPI
    needed_fastapi = sorted(undefined & FASTAPI_SYMBOLS)
    if needed_fastapi:
        missing_imports.append(f"from fastapi import {', '.join(needed_fastapi)}")
        reasons.append(f"Simbol {needed_fastapi} digunakan dalam routing/handler namun belum diimpor dari fastapi")

    # Resolusi TestClient
    if undefined & TESTCLIENT_SYMBOLS:
        missing_imports.append("from fastapi.testclient import TestClient")
        reasons.append("Simbol TestClient digunakan namun belum diimpor dari fastapi.testclient")

    # Resolusi modul Typing
    needed_typing = sorted(undefined & TYPING_SYMBOLS)
    if needed_typing:
        missing_imports.append(f"from typing import {', '.join(needed_typing)}")
        reasons.append(f"Simbol type annotation {needed_typing} digunakan namun belum diimpor dari typing")

    # Resolusi sibling class imports antar-file modul
    for cls_name, mod_name in sorted(sibling_classes.items()):
        if cls_name in undefined:
            missing_imports.append(f"from {mod_name} import {cls_name}")
            reasons.append(f"Kelas sibling '{cls_name}' dideklarasikan di '{mod_name}.py' dan direferensikan tanpa impor")

    return missing_imports, reasons


def apply_safe_python_imports(code_str: str, missing_imports: List[str]) -> str:
    """
    Menyisipkan pernyataan impor aman di awal file kode Python dengan menjaga docstring modul.
    """
    if not missing_imports:
        return code_str

    import_block = "\n".join(missing_imports) + "\n"
    try:
        tree = ast.parse(code_str)
        docstring = ast.get_docstring(tree)
    except SyntaxError:
        docstring = None

    if docstring:
        lines = code_str.splitlines(keepends=True)
        doc_end = 0
        in_doc = False
        quote_type = None
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not in_doc:
                if stripped.startswith(('"""', "'''")):
                    in_doc = True
                    quote_type = stripped[:3]
                    if stripped.count(quote_type) >= 2 and len(stripped) > 3:
                        doc_end = i + 1
                        break
            else:
                if quote_type in stripped:
                    doc_end = i + 1
                    break
        head = "".join(lines[:doc_end])
        tail = "".join(lines[doc_end:])
        return head + "\n" + import_block + tail
    else:
        return import_block + code_str


# ===========================================================================
# 2. Dart / Flutter Pre-Flight Safe Resolution Helpers
# ===========================================================================

def resolve_dart_sibling_imports(code_files: Dict[str, str]) -> Tuple[Dict[str, str], List[Dict[str, Any]]]:
    """
    Menyelesaikan impor sibling pada proyek Dart/Flutter berdasarkan file yang ada di lib/.
    """
    declared_dart_classes = {}
    for fname, content in code_files.items():
        if fname.endswith(".dart"):
            bare_name = Path(fname).name
            found_classes = re.findall(r'(?:class|enum|mixin)\s+([A-Z][a-zA-Z0-9_]+)', content)
            for cls in found_classes:
                declared_dart_classes[cls] = bare_name

    candidate_code_files = copy.deepcopy(code_files)
    tx_list = []

    for fname, content in list(code_files.items()):
        if fname.endswith(".dart"):
            bare_name = Path(fname).name
            missing_imports = []
            for cls, source_file in declared_dart_classes.items():
                if source_file != bare_name and re.search(r'\b' + re.escape(cls) + r'\b', content):
                    if source_file not in content:
                        missing_imports.append(f"import '{source_file}';")
            if missing_imports:
                patched = "\n".join(missing_imports) + "\n" + content
                candidate_code_files[fname] = patched
                tx_list.append({
                    "file": fname,
                    "before_hash": compute_sha256(content),
                    "after_hash": compute_sha256(patched),
                    "reasons": [f"Missing Dart sibling imports: {missing_imports}"],
                    "added_imports": missing_imports,
                    "rolled_back": False
                })

    return candidate_code_files, tx_list


# ===========================================================================
# 3. Main Sandbox Test Runner (v2)
# ===========================================================================

def run_sandbox_tests_v2(
    code_files: Dict[str, str],
    test_files: Dict[str, str],
    target_language: str = "python",
    timeout: int = 30,
    executor_intervention_enabled: bool = True,
    executor_mode: str = "SAFE"
) -> Dict[str, Any]:
    """
    Eksekutor pengujian sandbox v2.
    Mendukung mode legasi ('ON', 'OFF', 'CODE_ONLY') dan mode kandidat default 'SAFE'.
    """
    if executor_mode:
        effective_mode = executor_mode.upper()
    elif not executor_intervention_enabled:
        effective_mode = "OFF"
    else:
        effective_mode = "SAFE"

    if effective_mode not in ("SAFE", "ON", "OFF", "CODE_ONLY"):
        effective_mode = "SAFE"

    # Backward Compatibility: delegasi langsung ke implementasi legasi
    if effective_mode in ("OFF", "CODE_ONLY", "ON"):
        legacy_res = run_sandbox_tests_legacy(
            code_files,
            test_files,
            target_language=target_language,
            timeout=timeout,
            executor_intervention_enabled=executor_intervention_enabled,
            executor_mode=effective_mode
        )
        if parse_diagnostic:
            try:
                diag = parse_diagnostic(
                    legacy_res,
                    code_files=code_files,
                    test_files=test_files,
                    target_language=target_language
                )
                if diag:
                    legacy_res["diagnostic_evidence"] = diag.to_dict()
            except Exception:
                pass
        return legacy_res

    # -----------------------------------------------------------------------
    # MODE 'SAFE': Pre-Flight Validation Layer
    # -----------------------------------------------------------------------
    code_files = copy.deepcopy(code_files)
    test_files = copy.deepcopy(test_files)
    test_before_hashes = compute_dict_hashes(test_files)
    code_before_hashes = compute_dict_hashes(code_files)

    is_dart = (
        "dart" in target_language.lower()
        or "flutter" in target_language.lower()
        or any(f.endswith(".dart") for f in list(code_files.keys()) + list(test_files.keys()))
    )

    transformations: List[Dict[str, Any]] = []
    candidate_code_files = copy.deepcopy(code_files)

    if not is_dart:
        # A. Temukan deklarasi kelas sibling pada Python
        sibling_classes = {}
        for fname, content in code_files.items():
            if fname.endswith(".py"):
                mod_name = str(Path(fname).with_suffix("")).replace("\\", "/").replace("/", ".")
                try:
                    tree = ast.parse(content)
                    for node in tree.body:
                        if isinstance(node, ast.ClassDef):
                            sibling_classes[node.name] = mod_name
                except SyntaxError:
                    pass

        # B. Deteksi dan aplikasikan missing imports aman via AST
        for fname, content in list(code_files.items()):
            if fname.endswith(".py"):
                is_valid, err_msg = validate_python_syntax(content)
                if not is_valid:
                    # Kode memiliki kesalahan sintaks asli: jangan ubah logika, biarkan compiler/test melaporkan
                    continue

                curr_mod = str(Path(fname).with_suffix("")).replace("\\", "/").replace("/", ".")
                local_siblings = {cls: mod for cls, mod in sibling_classes.items() if mod != curr_mod}

                missing_imports, reasons = detect_missing_python_imports(content, local_siblings)
                if missing_imports:
                    patched = apply_safe_python_imports(content, missing_imports)
                    if validate_python_syntax(patched)[0]:
                        candidate_code_files[fname] = patched
                        transformations.append({
                            "file": fname,
                            "before_hash": compute_sha256(content),
                            "after_hash": compute_sha256(patched),
                            "reasons": reasons,
                            "added_imports": missing_imports,
                            "rolled_back": False
                        })
    else:
        # Dart Sibling Resolution
        candidate_code_files, dart_txs = resolve_dart_sibling_imports(code_files)
        transformations.extend(dart_txs)

    # -----------------------------------------------------------------------
    # Eksekusi Sandbox & Mekanisme Re-Validation / Rollback
    # -----------------------------------------------------------------------
    if not transformations:
        # Tidak ada transformasi yang diperlukan: eksekusi verbatim apa adanya
        results = run_sandbox_tests_legacy(
            code_files,
            test_files,
            target_language=target_language,
            timeout=timeout,
            executor_intervention_enabled=False,
            executor_mode="OFF"
        )
    else:
        # Eksekusi kode kandidat yang telah diselesaikan impor amannya
        candidate_results = run_sandbox_tests_legacy(
            candidate_code_files,
            test_files,
            target_language=target_language,
            timeout=timeout,
            executor_intervention_enabled=False,
            executor_mode="OFF"
        )

        if candidate_results["passed"]:
            results = candidate_results
            results["code_files"] = candidate_code_files
        else:
            # Kandidat gagal: Uji kode asli untuk memastikan transformasi tidak menyebabkan degradasi
            original_results = run_sandbox_tests_legacy(
                code_files,
                test_files,
                target_language=target_language,
                timeout=timeout,
                executor_intervention_enabled=False,
                executor_mode="OFF"
            )
            # Jika hasil asli lebih baik atau sama, lakukan ROLLBACK
            if original_results["passed_count"] >= candidate_results["passed_count"]:
                for tx in transformations:
                    tx["rolled_back"] = True
                    tx["rollback_reason"] = (
                        f"Transformasi kandidat ({candidate_results['passed_count']}/{candidate_results['total']}) "
                        f"tidak meningkatkan hasil uji terhadap kode asli ({original_results['passed_count']}/{original_results['total']}). "
                        f"Rollback otomatis diaktifkan."
                    )
                results = original_results
                results["code_files"] = code_files
            else:
                # Kandidat mencatatkan peningkatan kelulusan uji parsial: pertahankan kandidat
                results = candidate_results
                results["code_files"] = candidate_code_files

    # -----------------------------------------------------------------------
    # Verifikasi Integritas Test Files (Strict Immutability)
    # -----------------------------------------------------------------------
    test_after_hashes = compute_dict_hashes(test_files)
    if test_before_hashes != test_after_hashes:
        raise RuntimeError(
            f"Instrumentation error: Executor SAFE mode modified test files! "
            f"Before: {test_before_hashes}, After: {test_after_hashes}"
        )

    results["transformations"] = transformations
    results["executor_mode"] = "SAFE"
    if parse_diagnostic:
        try:
            diag = parse_diagnostic(
                results,
                code_files=candidate_code_files,
                test_files=test_files,
                target_language=target_language
            )
            if diag:
                results["diagnostic_evidence"] = diag.to_dict()
        except Exception:
            pass
    return results


# ===========================================================================
# 4. LangGraph Executor Node (v2)
# ===========================================================================

def executor_node_v2(state: SquadState) -> dict:
    code_files = state.get("code_files", {})
    test_files = state.get("test_files", {})
    target_lang = state.get("target_language", "python")
    iteration = state.get("iteration_count", 0)

    raw_mode = state.get("executor_mode")
    if raw_mode and raw_mode.upper() in ("SAFE", "ON", "OFF", "CODE_ONLY"):
        executor_mode = raw_mode.upper()
    elif not state.get("executor_intervention_enabled", True):
        executor_mode = "OFF"
    else:
        executor_mode = "SAFE"
    executor_intervention_enabled = (executor_mode != "OFF")

    # Observability: Simpan snapshot BEFORE eksekusi
    code_files_before = copy.deepcopy(code_files)
    test_files_before = copy.deepcopy(test_files)
    code_before_hashes = compute_dict_hashes(code_files_before)
    test_before_hashes = compute_dict_hashes(test_files_before)

    exec_input_snapshot = {
        "iteration_count": iteration,
        "target_language": target_lang,
        "executor_mode": executor_mode,
        "executor_intervention_enabled": executor_intervention_enabled,
        "status": state.get("status", ""),
        "code_files": code_files_before,
        "test_files": test_files_before,
        "test_results": copy.deepcopy(state.get("test_results", {})),
        "logs": copy.deepcopy(state.get("logs", []))
    }
    exec_input_hashes = {
        "code_files_hashes": code_before_hashes,
        "test_files_hashes": test_before_hashes,
        "input_snapshot_sha256": compute_object_hash(exec_input_snapshot)
    }

    tracer = get_tracer(state.get("run_id"))
    if tracer:
        tracer.log_event(
            stage="executor",
            event_type="input",
            iteration=iteration,
            data={
                "executor_input": exec_input_snapshot,
                "executor_input_hashes": exec_input_hashes,
                "iteration": iteration
            }
        )

    results = run_sandbox_tests_v2(
        code_files,
        test_files,
        target_language=target_lang,
        executor_intervention_enabled=executor_intervention_enabled,
        executor_mode=executor_mode
    )

    code_files_after = results.get("code_files", code_files)
    test_files_after = results.get("test_files", test_files)
    code_after_hashes = compute_dict_hashes(code_files_after)
    test_after_hashes = compute_dict_hashes(test_files_after)

    # Catat mutasi file
    code_modified = [f for f in code_files_after if f in code_files_before and code_files_after[f] != code_files_before[f]]
    code_added = [f for f in code_files_after if f not in code_files_before]
    test_modified = [f for f in test_files_after if f in test_files_before and test_files_after[f] != test_files_before[f]]
    test_added = [f for f in test_files_after if f not in test_files_before]

    # Validasi ketat integritas test untuk mode CODE_ONLY dan SAFE
    if executor_mode in ("CODE_ONLY", "SAFE"):
        if test_before_hashes != test_after_hashes or test_modified or test_added:
            raise RuntimeError(
                f"Instrumentation error: Executor {executor_mode} mode modified test files! "
                f"Before hashes: {test_before_hashes}, After hashes: {test_after_hashes}"
            )

    # Observability Trace Logging
    if tracer:
        tracer.log_event(
            stage="executor",
            event_type="execution",
            iteration=iteration,
            data={
                "executor_mode": executor_mode,
                "executor_intervention_enabled": executor_intervention_enabled,
                "code_files_before": code_files_before,
                "code_files_before_hashes": code_before_hashes,
                "test_files_before": test_files_before,
                "test_files_before_hashes": test_before_hashes,
                "code_files_after": code_files_after,
                "code_files_after_hashes": code_after_hashes,
                "test_files_after": test_files_after,
                "test_files_after_hashes": test_after_hashes,
                "transformations": {
                    "code_files_modified": code_modified,
                    "code_files_added": code_added,
                    "test_files_modified": test_modified,
                    "test_files_added": test_added,
                    "total_transformations": len(code_modified) + len(code_added) + len(test_modified) + len(test_added),
                    "detailed_transformations": results.get("transformations", [])
                },
                "command": results.get("command"),
                "working_directory": results.get("working_dir", str(SANDBOX_DIR.resolve())),
                "stdout": results.get("raw_stdout", results.get("stdout", "")),
                "stderr": results.get("raw_stderr", ""),
                "exit_code": results.get("exit_code"),
                "parsed_results": {
                    "passed": results["passed"],
                    "total": results["total"],
                    "passed_count": results["passed_count"],
                    "failed_count": results["failed_count"],
                    "framework": results.get("framework")
                },
                "pass_fail": results["passed"],
                "duration_sec": results.get("duration_sec"),
                "iteration": iteration
            }
        )

    mode_label = f"Executor-{executor_mode}"
    current_logs = state.get("logs", [])
    developer_feedback = ""

    # P0-1 & Improved Repentance: Structured Diagnostic Parser, History & Targeted Error Feedback
    code_hashes = compute_dict_hashes(code_files_after)
    current_code_hash = compute_sha256("".join(f"{k}:{code_hashes[k]}" for k in sorted(code_hashes.keys())))[:16]

    repair_history = list(state.get("repair_history") or [])
    failed_strategies = list(state.get("failed_strategies") or [])
    known_good_constraints = list(state.get("known_good_constraints") or [])
    contract = state.get("contract")
    max_iterations = state.get("max_iterations") if state.get("max_iterations") is not None else 10

    diag = None
    if parse_diagnostic:
        try:
            diag = parse_diagnostic(
                results,
                code_files=code_files_after,
                test_files=test_files_after,
                target_language=target_lang,
                run_id=state.get("run_id"),
                iteration=iteration,
                contract=contract
            )
            if diag:
                results["diagnostic_evidence"] = diag.to_dict()
        except Exception:
            pass

    passed_count = results.get("passed_count", 0)
    failed_count = results.get("failed_count", 0)
    is_passed = results.get("passed", False)
    curr_err_msg = ""
    curr_cat = "unknown"
    if diag and diag.failing_tests:
        curr_err_msg = diag.failing_tests[0].message
        curr_cat = diag.primary_failure_category
    elif not is_passed:
        curr_err_msg = results.get("summary_line") or "Execution failed"

    if repair_history:
        prev_entry = repair_history[-1]
        prev_hash = prev_entry.get("code_hash", "")
        prev_passed = prev_entry.get("test_passed_count", 0)
        prev_cat = prev_entry.get("primary_category", "unknown")
        prev_err = prev_entry.get("error_message", "")

        is_valid_test_run = curr_cat not in ("compilation_error", "syntax_parse_error", "collection_test_discovery_error")
        prev_valid_run = prev_cat not in ("compilation_error", "syntax_parse_error", "collection_test_discovery_error")

        if current_code_hash == prev_hash and not is_passed:
            transition = "STAGNANT"
        elif is_passed:
            transition = "PASSED"
        elif is_valid_test_run and passed_count > prev_passed:
            transition = "IMPROVED"
        elif is_valid_test_run and prev_valid_run and passed_count < prev_passed:
            transition = "REGRESSED"
        elif curr_err_msg and prev_err and (curr_err_msg[:40] == prev_err[:40]):
            transition = "STAGNANT"
        else:
            transition = "FAILED"
    else:
        transition = "PASSED" if is_passed else "FAILED"

    # Record loop history
    history_entry = {
        "loop": iteration + 1,
        "code_hash": current_code_hash,
        "result": transition,
        "test_passed_count": passed_count,
        "test_failed_count": failed_count,
        "error_message": curr_err_msg,
        "primary_category": curr_cat
    }
    repair_history.append(history_entry)

    if transition in ("STAGNANT", "REGRESSED"):
        failed_strategies.append({
            "loop": iteration + 1,
            "code_hash": current_code_hash,
            "reason": transition,
            "error": curr_err_msg
        })

    # Populate known_good_constraints strictly based on validated execution evidence (Principle 2)
    # Never infer known-good if no tests passed or if the suite crashed at compilation/collection
    if contract and isinstance(contract, dict):
        failing_aids = set()
        if diag and diag.failing_tests:
            for ft in diag.failing_tests:
                if ft.linked_assertion_id:
                    failing_aids.add(ft.linked_assertion_id)

        # Evict any constraint that has now failed (regression detection)
        known_good_constraints = [
            c for c in known_good_constraints
            if not any(f_aid in c for f_aid in failing_aids)
        ]

        # Only add new known-good constraints if the test suite actually ran and tests passed
        is_valid_test_run = (
            passed_count > 0
            and curr_cat not in ("compilation_error", "syntax_parse_error", "collection_test_discovery_error")
        )
        if is_valid_test_run:
            for a in contract.get("testable_assertions", []):
                aid = a.get("assertion_id")
                if aid and aid not in failing_aids:
                    desc = a.get("description") or aid
                    entry_str = f"{aid} ({desc})"
                    if entry_str not in known_good_constraints:
                        known_good_constraints.append(entry_str)

    if not is_passed and build_targeted_feedback and diag:
        try:
            developer_feedback = build_targeted_feedback(
                diag,
                iteration=iteration + 1,
                max_iterations=max_iterations,
                run_id=state.get("run_id"),
                contract=contract,
                repair_history=repair_history,
                known_good_constraints=known_good_constraints,
                failed_strategies=failed_strategies,
                use_repentance=True
            )
        except Exception:
            pass

    if is_passed:
        log_msg = f"[Sandbox Executor ({mode_label})]: Pengujian SUKSES ✅ ({results['passed_count']} passed dalam {results['duration_sec']}s)."
        new_status = "tests_passed"
        new_iteration = iteration
    else:
        new_iteration = iteration + 1
        log_msg = f"[Sandbox Executor ({mode_label})]: Pengujian GAGAL ❌ ({results['failed_count']} failed / exit code {results['exit_code']}). Putaran iterasi perbaikan: {new_iteration} (Transisi: {transition})."
        new_status = "tests_failed"

    res = {
        "test_results": results,
        "iteration_count": new_iteration,
        "status": new_status,
        "logs": current_logs + [log_msg],
        "executor_intervention_enabled": executor_intervention_enabled,
        "executor_mode": executor_mode,
        "developer_feedback": developer_feedback,
        "repair_history": repair_history,
        "failed_strategies": failed_strategies,
        "known_good_constraints": known_good_constraints
    }
    if results.get("code_files"):
        res["code_files"] = results["code_files"]
    if results.get("test_files"):
        res["test_files"] = results["test_files"]
    return res


# Backward-compatible aliases
run_sandbox_tests = run_sandbox_tests_v2
executor_node = executor_node_v2
