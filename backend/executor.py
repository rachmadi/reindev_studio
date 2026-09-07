import os
import re
import sys
import time
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any

try:
    from .state import SquadState
except (ImportError, ValueError):
    from state import SquadState

SANDBOX_DIR = Path(__file__).parent / "sandbox"

def run_sandbox_tests(code_files: Dict[str, str], test_files: Dict[str, str], target_language: str = "python", timeout: int = 30) -> Dict[str, Any]:
    """
    Mengeksekusi kode dan test files di lingkungan sandbox subprocess terisolasi.
    Mendukung Python (pytest) dengan auto-scaffolding package (__init__.py) dan resolusi PYTHONPATH.
    """
    start_time = time.time()
    
    # 1. Siapkan folder sandbox bersih
    if SANDBOX_DIR.exists():
        shutil.rmtree(SANDBOX_DIR, ignore_errors=True)
    SANDBOX_DIR.mkdir(parents=True, exist_ok=True)
    
    # 2. Tulis semua file kode ke sandbox
    for fname, content in code_files.items():
        fpath = SANDBOX_DIR / fname
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.write_text(content, encoding="utf-8")
        
    # 3. Tulis semua file test ke sandbox
    for fname, content in test_files.items():
        fpath = SANDBOX_DIR / fname
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.write_text(content, encoding="utf-8")

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
        
    # 5. Siapkan Environment dengan PYTHONPATH mencakup root sandbox dan seluruh subpackage
    subdirs = [str(p.resolve()) for p in SANDBOX_DIR.rglob("*") if p.is_dir() and p.name != "__pycache__"]
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(SANDBOX_DIR.resolve())] + subdirs)
    
    cmd = [sys.executable, "-m", "pytest", "-v", "--color=no"]
    
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(SANDBOX_DIR),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout
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
            "output": f"Timeout pengujian melampaui {timeout} detik.",
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
    
    # 6. Parsing output pytest (misal: "4 passed in 0.12s", "1 failed, 2 passed")
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
        "failed_count": failed_count + error_count,
        "output": full_output,
        "exit_code": exit_code,
        "duration_sec": duration
    }

def executor_node(state: SquadState) -> dict:
    code_files = state.get("code_files", {})
    test_files = state.get("test_files", {})
    target_lang = state.get("target_language", "python")
    iteration = state.get("iteration_count", 0)
    
    results = run_sandbox_tests(code_files, test_files, target_language=target_lang)
    
    current_logs = state.get("logs", [])
    if results["passed"]:
        log_msg = f"[Sandbox Executor]: Pengujian SUKSES ✅ ({results['passed_count']} passed dalam {results['duration_sec']}s)."
        new_status = "tests_passed"
        new_iteration = iteration
    else:
        new_iteration = iteration + 1
        log_msg = f"[Sandbox Executor]: Pengujian GAGAL ❌ ({results['failed_count']} failed / exit code {results['exit_code']}). Putaran iterasi perbaikan: {new_iteration}."
        new_status = "tests_failed"
        
    return {
        "test_results": results,
        "iteration_count": new_iteration,
        "status": new_status,
        "logs": current_logs + [log_msg]
    }
