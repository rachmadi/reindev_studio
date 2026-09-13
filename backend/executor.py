import os
import re
import sys
import time
import copy
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any

try:
    from .state import SquadState
    from .tracer import get_tracer, compute_dict_hashes, compute_object_hash
except (ImportError, ValueError):
    from state import SquadState
    try:
        from tracer import get_tracer, compute_dict_hashes, compute_object_hash
    except ImportError:
        def get_tracer(run_id=None): return None
        def compute_dict_hashes(f): return {}
        def compute_object_hash(o): return ""

SANDBOX_DIR = Path(__file__).parent / "sandbox"

def run_sandbox_tests(code_files: Dict[str, str], test_files: Dict[str, str], target_language: str = "python", timeout: int = 30, executor_intervention_enabled: bool = True, executor_mode: str = None) -> Dict[str, Any]:
    """
    Mengeksekusi kode dan test files di lingkungan sandbox subprocess terisolasi.
    Mendukung Python (pytest) dengan auto-scaffolding package (__init__.py) dan resolusi PYTHONPATH.
    Mode:
    - 'ON': Transformasi & auto-healing penuh pada code_files dan test_files.
    - 'OFF': Nol transformasi (verbatim) pada code_files dan test_files.
    - 'CODE_ONLY': Transformasi penuh pada code_files, test_files DILARANG KERAS diubah.
    """
    start_time = time.time()
    code_files = copy.deepcopy(code_files)
    test_files = copy.deepcopy(test_files)
    
    # Resolusi mode eksekusi efektif
    if executor_mode:
        effective_mode = executor_mode.upper()
    elif not executor_intervention_enabled:
        effective_mode = "OFF"
    else:
        effective_mode = "ON"
    if effective_mode not in ("ON", "OFF", "CODE_ONLY"):
        effective_mode = "ON"

    initial_test_files = copy.deepcopy(test_files)
    tests_before_hash = compute_dict_hashes(initial_test_files)
    
    is_dart = "dart" in target_language.lower() or "flutter" in target_language.lower() or any(f.endswith(".dart") for f in list(code_files.keys()) + list(test_files.keys()))
    is_flutter = is_dart and ("flutter" in target_language.lower() or any("package:flutter" in c for c in list(code_files.values()) + list(test_files.values())))
    env = os.environ.copy()

    # 1. Siapkan folder sandbox bersih
    if SANDBOX_DIR.exists():
        shutil.rmtree(SANDBOX_DIR, ignore_errors=True)
    SANDBOX_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1.5. Deteksi nama package Dart jika stack adalah Dart/Flutter
    dart_pkg_name = "sandbox_project"
    if is_dart:
        std_packages = {"flutter", "flutter_test", "test", "flutter_riverpod", "meta", "vector_math", "path", "collection"}
        for c in list(test_files.values()) + list(code_files.values()):
            matches = re.findall(r"import\s+['\"]package:([a-zA-Z0-9_]+)/", c)
            for m in matches:
                if m not in std_packages:
                    dart_pkg_name = m
                    break
            if dart_pkg_name != "sandbox_project":
                break

    # 2. STERILE SANDBOX MATERIALIZATION (PURGED ALL LEGACY SOURCE MUTATIONS & REGEX SOLVERS):
    # Developer artifact & test suite materialize unchanged directly to sandbox.
    for fname, content_str in code_files.items():
        fpath = SANDBOX_DIR / fname
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.write_text(content_str, encoding="utf-8")

    for fname, content_str in test_files.items():
        fpath = SANDBOX_DIR / fname
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.write_text(content_str, encoding="utf-8")

    # Verifikasi integritas orakel test (Strict Immutability)
    tests_after_hash = compute_dict_hashes(test_files)
    if tests_before_hash != tests_after_hash:
        raise RuntimeError(
            f"Instrumentation error: Executor {effective_mode} mode modified test files! "
            f"Before: {tests_before_hash}, After: {tests_after_hash}"
        )

    # 4. Auto-scaffold: Pastikan setiap subdirektori memiliki __init__.py agar dapat diimpor sebagai package
    for subdir in SANDBOX_DIR.rglob("*"):
        if subdir.is_dir() and subdir.name != "__pycache__":
            init_file = subdir / "__init__.py"
            if not init_file.exists():
                init_file.write_text("# auto-generated package init\n", encoding="utf-8")
        
    # Jika tidak ada file test yang dibuat, kembalikan status kegagalan pengujian
    if not test_files:
        return {
            "passed": False,
            "total": 0,
            "passed_count": 0,
            "failed_count": 0,
            "output": "Tidak ada file unit test yang tersedia untuk dieksekusi.",
            "exit_code": 1,
            "duration_sec": round(time.time() - start_time, 2)
        }

    is_win = (sys.platform == "win32")
    if is_dart:
        pubspec = SANDBOX_DIR / "pubspec.yaml"
        if is_flutter:
            pubspec.write_text(f"""name: {dart_pkg_name}
description: Sandbox test project
environment:
  sdk: '>=3.0.0 <4.0.0'
dependencies:
  flutter:
    sdk: flutter
  flutter_riverpod: any
dev_dependencies:
  flutter_test:
    sdk: flutter
  test: ^1.24.0
flutter:
  uses-material-design: true
""", encoding="utf-8")
            runner_bin = shutil.which("flutter") or "flutter"
        else:
            pubspec.write_text(f"""name: {dart_pkg_name}
description: Sandbox test project
environment:
  sdk: '>=3.0.0 <4.0.0'
dev_dependencies:
  test: ^1.24.0
""", encoding="utf-8")
            runner_bin = shutil.which("dart") or "dart"
        
        # Jalankan pub get untuk mengunduh package config
        try:
            subprocess.run(
                [runner_bin, "pub", "get"],
                cwd=str(SANDBOX_DIR),
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                shell=is_win,
                timeout=45
            )
        except Exception:
            pass
                
        cmd = [runner_bin, "test"]
    else:
        is_win = False
        # 5. Siapkan Environment dengan PYTHONPATH mencakup root sandbox dan seluruh subpackage
        subdirs = [str(p.resolve()) for p in SANDBOX_DIR.rglob("*") if p.is_dir() and p.name != "__pycache__"]
        backend_dir = str(Path(__file__).resolve().parent)
        env["PYTHONPATH"] = os.pathsep.join([str(SANDBOX_DIR.resolve()), backend_dir] + subdirs)
        cmd = [sys.executable, "-m", "pytest", "-v", "--color=no", "-p", "conftest_runtime_enricher", "--import-mode=importlib", "-o", "python_files=test_*.py *_test.py"]
    
    effective_timeout = 90 if (is_flutter or is_dart) else timeout
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(SANDBOX_DIR),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=is_win,
            timeout=effective_timeout
        )
        stdout = proc.stdout
        stderr = proc.stderr
        exit_code = proc.returncode
        full_output = (stdout + "\n" + stderr).strip()
    except subprocess.TimeoutExpired:
        return {
            "passed": False,
            "total": 0,
            "passed_count": 0,
            "failed_count": 1,
            "output": f"Timeout pengujian melampaui {effective_timeout} detik.",
            "exit_code": -1,
            "duration_sec": round(time.time() - start_time, 2)
        }
    except Exception as e:
        return {
            "passed": False,
            "total": 0,
            "passed_count": 0,
            "failed_count": 1,
            "output": f"Subprocess Runner Error: {str(e)}",
            "exit_code": -1,
            "duration_sec": round(time.time() - start_time, 2)
        }
        
    duration = round(time.time() - start_time, 2)
    
    # 6. Parsing output test runner
    if is_dart:
        passed_match = re.search(r"\+(\d+):\s+All tests passed", full_output)
        if passed_match:
            passed_count = int(passed_match.group(1))
            failed_count = 0
            is_passed = True
        else:
            plus_matches = re.findall(r"\+(\d+)", full_output)
            minus_matches = re.findall(r"-(\d+)", full_output)
            passed_count = int(plus_matches[-1]) if plus_matches else 0
            failed_count = int(minus_matches[-1]) if minus_matches else (0 if exit_code == 0 else 1)
            is_passed = (exit_code == 0 and failed_count == 0 and passed_count > 0)
        total = max(passed_count + failed_count, 1 if not is_passed else passed_count)
    else:
        passed_match = re.search(r"(\d+)\s+passed", full_output)
        failed_match = re.search(r"(\d+)\s+failed", full_output)
        error_match = re.search(r"(\d+)\s+error", full_output)
        
        passed_count = int(passed_match.group(1)) if passed_match else 0
        failed_count = int(failed_match.group(1)) if failed_match else 0
        error_count = int(error_match.group(1)) if error_match else 0
        
        total = passed_count + failed_count + error_count
        is_passed = (exit_code == 0 and failed_count == 0 and error_count == 0 and passed_count > 0)
    
    return {
        "passed": is_passed,
        "total": total,
        "passed_count": passed_count,
        "failed_count": failed_count,
        "output": full_output,
        "stdout": full_output,
        "raw_stdout": stdout,
        "raw_stderr": stderr,
        "command": cmd,
        "working_dir": str(SANDBOX_DIR.resolve()),
        "exit_code": exit_code,
        "duration_sec": duration,
        "framework": "flutter test" if is_flutter else ("dart test" if is_dart else "pytest"),
        "code_files": code_files,
        "test_files": test_files
    }

def executor_node(state: SquadState) -> dict:
    code_files = state.get("code_files", {})
    test_files = state.get("test_files", {})
    target_lang = state.get("target_language", "python")
    iteration = state.get("iteration_count", 0)
    
    # Resolusi executor_mode
    raw_mode = state.get("executor_mode")
    if raw_mode and raw_mode.upper() in ("ON", "OFF", "CODE_ONLY"):
        executor_mode = raw_mode.upper()
    elif not state.get("executor_intervention_enabled", True):
        executor_mode = "OFF"
    else:
        executor_mode = "ON"
    executor_intervention_enabled = (executor_mode != "OFF")
    
    # Observability: Simpan snapshot eksplisit BEFORE transformasi
    code_files_before = copy.deepcopy(code_files)
    test_files_before = copy.deepcopy(test_files)
    code_before_hashes = compute_dict_hashes(code_files_before)
    test_before_hashes = compute_dict_hashes(test_files_before)
    
    # Observability: Catat snapshot INPUT AKTUAL yang diterima Executor
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
    
    results = run_sandbox_tests(
        code_files,
        test_files,
        target_language=target_lang,
        executor_intervention_enabled=executor_intervention_enabled,
        executor_mode=executor_mode
    )
    
    code_files_after = results.get("code_files", {})
    test_files_after = results.get("test_files", {})
    code_after_hashes = compute_dict_hashes(code_files_after)
    test_after_hashes = compute_dict_hashes(test_files_after)

    # Deteksi mutasi/transformasi yang dilakukan
    code_modified = [f for f in code_files_after if f in code_files_before and code_files_after[f] != code_files_before[f]]
    code_added = [f for f in code_files_after if f not in code_files_before]
    test_modified = [f for f in test_files_after if f in test_files_before and test_files_after[f] != test_files_before[f]]
    test_added = [f for f in test_files_after if f not in test_files_before]

    # Validasi ketat integritas test untuk mode CODE_ONLY (Fail Loudly jika ada mutasi)
    if executor_mode == "CODE_ONLY":
        if test_before_hashes != test_after_hashes or test_modified or test_added:
            raise RuntimeError(
                f"Instrumentation error: Executor CODE_ONLY mode modified test files! "
                f"Before hashes: {test_before_hashes}, After hashes: {test_after_hashes}, "
                f"Modified: {test_modified}, Added: {test_added}"
            )

    # Observability Trace Logging
    tracer = get_tracer(state.get("run_id"))
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
                    "total_transformations": len(code_modified) + len(code_added) + len(test_modified) + len(test_added)
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
    if results["passed"]:
        log_msg = f"[Sandbox Executor ({mode_label})]: Pengujian SUKSES ✅ ({results['passed_count']} passed dalam {results['duration_sec']}s)."
        new_status = "tests_passed"
        new_iteration = iteration
    else:
        new_iteration = iteration + 1
        log_msg = f"[Sandbox Executor ({mode_label})]: Pengujian GAGAL ❌ ({results['failed_count']} failed / exit code {results['exit_code']}). Putaran iterasi perbaikan: {new_iteration}."
        new_status = "tests_failed"
        
    res = {
        "test_results": results,
        "iteration_count": new_iteration,
        "status": new_status,
        "logs": current_logs + [log_msg],
        "executor_intervention_enabled": executor_intervention_enabled,
        "executor_mode": executor_mode
    }
    if results.get("code_files"):
        res["code_files"] = results["code_files"]
    if results.get("test_files"):
        res["test_files"] = results["test_files"]
    return res

