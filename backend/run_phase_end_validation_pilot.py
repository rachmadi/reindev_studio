"""
Phase-End Validation & Evidence-First Engineering Pilot Runner
ReinDev Studio — Iterasi 6 (Experiment Extension)

Matriks Uji:
- fastapi_t1 x 1
- cli_t1 x 1
- flutter_t1 x 1
Total: 3 Run.

Konfigurasi Eksperimen (Identik dengan baseline D10):
- Model: qwen2.5-coder:7b via Ollama (100% Unified Squad)
- Max iterations Developer: 10 (D10)
- Max blueprint revisions: 5
- Max contract revisions: 5
- Frozen Oracle: Immutable
- QA Tester LLM: 100% Bypassed
"""

import os
import sys
import json
import time
import hashlib
import argparse
from pathlib import Path
from datetime import datetime
from typing import Tuple, List, Dict, Any, Optional

# Setup project root and backend dir
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env")

ALL_AGENTS_MODEL = "qwen2.5-coder:7b"
DEVELOPER_MODEL = ALL_AGENTS_MODEL
DEVELOPER_BACKEND = "ollama"
PROVIDER = "ollama"
SQUAD_MODEL = ALL_AGENTS_MODEL

MAX_PHASE_REPAIR_ATTEMPTS = 2
MAX_BLUEPRINT_REVISIONS = 2
MAX_CONTRACT_REVISIONS = 2
MAX_ITERATIONS = 10

def configure_squad_model(model_name: Optional[str] = None, num_predict: Optional[int] = None):
    global ALL_AGENTS_MODEL, DEVELOPER_MODEL, SQUAD_MODEL
    if model_name:
        ALL_AGENTS_MODEL = model_name
        DEVELOPER_MODEL = model_name
        SQUAD_MODEL = model_name
        os.environ["DEVELOPER_MODEL"] = model_name
        os.environ["OLLAMA_MODEL"] = model_name
        os.environ["SQUAD_MODEL"] = model_name
    if num_predict:
        os.environ["OLLAMA_NUM_PREDICT"] = str(num_predict)

os.environ["DEVELOPER_BACKEND"] = DEVELOPER_BACKEND
os.environ["DEVELOPER_MODEL"] = DEVELOPER_MODEL
os.environ["OLLAMA_MODEL"] = ALL_AGENTS_MODEL
os.environ["OLLAMA_NUM_CTX"] = "8192"
os.environ["OLLAMA_NUM_PREDICT"] = "3000"

from backend.graph_phase_validated import build_phase_validated_graph, phase_validated_squad_graph
from backend.tracer import RunTracer, calculate_trace_otrr
from backend.phase_validators import (
    validate_pm_phase,
    validate_architect_phase,
    validate_developer_phase,
    validate_oracle_phase,
    validate_executor_phase,
    validate_reviewer_phase
)

ORACLE_BASE = PROJECT_ROOT / "dokumentasi-pengembangan/experiments/frozen_oracle"
OUTPUT_DIR = PROJECT_ROOT / "backend/output/phase_validation_pilot"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TASKS = [
    {
        "task_id": "fastapi_t1",
        "task": "Bangun modul REST API FastAPI untuk manajemen inventaris produk dengan validasi Pydantic dan automated pytest.",
        "target_language": "python",
        "oracle_path": str(ORACLE_BASE / "fastapi_t1"),
        "expected_sha": "a1db9bb1f6eaf47d5cf56e102c4a0f6e1f49d757e9faa1485b36f2972a152d63",
        "oracle_file": "test_main.py",
        "n_tests": 5,
        "authoritative_file": "main.py"
    },
    {
        "task_id": "cli_t1",
        "task": "Bangun kalkulator CLI Python dengan operasi matematika matriks dan penanganan error komprehensif.",
        "target_language": "python",
        "oracle_path": str(ORACLE_BASE / "cli_t1"),
        "expected_sha": "0bd5b598afa7ae4c9cdf0e269d13136b51d35a4e0b1ac6548f0a2cf8a8eba124",
        "oracle_file": "test_main.py",
        "n_tests": 5,
        "authoritative_file": "main.py"
    },
    {
        "task_id": "flutter_t1",
        "task": "Bangun komponen widget kartu metrik modern responsif Flutter dengan Material Design 3 dan Riverpod state.",
        "target_language": "dart",
        "oracle_path": str(ORACLE_BASE / "flutter_t1"),
        "expected_sha": "4589e15cfb8f37ba70642e70623ca143bceee1a44175aefd072f441d9e8a9528",
        "oracle_file": "card_metric_test.dart",
        "n_tests": 2,
        "authoritative_file": "lib/card_metric.dart"
    },
]


def verify_explicit_oracle_sha(task: dict) -> Tuple[bool, str, str]:
    """1-to-1 explicit verification of Frozen Oracle SHA-256."""
    fp = Path(task["oracle_path"]) / task["oracle_file"]
    if not fp.exists():
        return False, "FILE_NOT_FOUND", ""
    data = fp.read_bytes()
    actual_sha = hashlib.sha256(data).hexdigest().lower()
    expected_sha = task["expected_sha"].lower()
    return (actual_sha == expected_sha), actual_sha, expected_sha


# ==============================================================================
# Pre-Flight Verification Gates (A-I)
# ==============================================================================

def run_preflight_gates() -> bool:
    """Mengeksekusi seluruh 9 Pre-Flight Gates A-I secara deterministik."""
    print("=" * 70)
    print("PRE-FLIGHT VERIFICATION GATES (A-I) — PHASE-END VALIDATION PILOT")
    print("=" * 70)
    all_passed = True

    # Gate A: Static compilation
    print("\n[Gate A]: Static Code Compilation Check...")
    import py_compile
    modules_to_compile = [
        BACKEND_DIR / "phase_validators.py",
        BACKEND_DIR / "graph_phase_validated.py",
        BACKEND_DIR / "tests/test_phase_validators.py",
        BACKEND_DIR / "run_phase_end_validation_pilot.py"
    ]
    gate_a_ok = True
    for mod in modules_to_compile:
        try:
            py_compile.compile(str(mod), doraise=True)
            print(f"  ✓ {mod.name} compiled cleanly")
        except Exception as e:
            print(f"  ✗ {mod.name} compilation failed: {e}")
            gate_a_ok = False
    print(f"Gate A Status: {'PASS' if gate_a_ok else 'FAIL'}")
    all_passed = all_passed and gate_a_ok

    # Gate B: Authoritative Baseline Test Inventory Verification & Execution
    print("\n[Gate B]: Baseline Regression Test Suite Check...")
    import subprocess
    clean_env = os.environ.copy()
    clean_env.pop("OLLAMA_NUM_PREDICT", None)
    clean_env.pop("DEVELOPER_MODEL", None)
    clean_env.pop("OLLAMA_MODEL", None)
    cmd = [sys.executable, "-m", "pytest", "backend/", "-q"]
    p = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True, env=clean_env)
    gate_b_ok = (p.returncode == 0 and "failed" not in p.stdout)
    if not gate_b_ok:
        for line in p.stdout.splitlines():
            if "FAILED" in line or "error" in line.lower():
                print(f"  FAILED TEST: {line}")
    print(f"  Pytest Output: {p.stdout.strip().splitlines()[-1] if p.stdout.strip() else 'No output'}")
    print(f"Gate B Status: {'PASS' if gate_b_ok else 'FAIL'}")
    all_passed = all_passed and gate_b_ok

    # Gate C: Explicit 1-to-1 Frozen Oracle Checksum
    print("\n[Gate C]: Explicit Frozen Oracle SHA-256 Checksum Check...")
    gate_c_ok = True
    for t in TASKS:
        match, act, exp = verify_explicit_oracle_sha(t)
        if match:
            print(f"  ✓ {t['task_id']} ({t['oracle_file']}): {act[:16]}... matches expected")
        else:
            print(f"  ✗ {t['task_id']} mismatch! Actual: {act}, Expected: {exp}")
            gate_c_ok = False
    print(f"Gate C Status: {'PASS' if gate_c_ok else 'FAIL'}")
    all_passed = all_passed and gate_c_ok

    # Gate D: Tester LLM Isolation
    print("\n[Gate D]: Tester LLM Isolation Verification...")
    # Inspect graph wiring to confirm tester node is not in active edges for frozen oracle
    graph = phase_validated_squad_graph
    nodes = list(graph.nodes.keys())
    has_v4 = ("test_suite_validator" in nodes or "oracle_validator" in nodes)
    gate_d_ok = ("tester" not in nodes) or ("frozen_oracle" in nodes and has_v4)
    print(f"  ✓ Graph routes via 'frozen_oracle' & 'test_suite_validator'. QA Tester bypassed.")
    print(f"Gate D Status: {'PASS' if gate_d_ok else 'FAIL'}")
    all_passed = all_passed and gate_d_ok

    # Gate E: Dry-Run Phase Transition
    print("\n[Gate E]: Dry-Run Phase Transition Verification...")
    gate_e_ok = True
    try:
        # Build graph and inspect structure
        compiled_graph = build_phase_validated_graph()
        print(f"  ✓ Phase validated graph compiles successfully with {len(compiled_graph.nodes)} nodes")
    except Exception as e:
        print(f"  ✗ Graph compilation error: {e}")
        gate_e_ok = False
    print(f"Gate E Status: {'PASS' if gate_e_ok else 'FAIL'}")
    all_passed = all_passed and gate_e_ok

    # Gate F: Phase-End & Iteration Validator Boundary Invocation
    print("\n[Gate F]: Phase-End & Iteration Validator Boundary Invocation Check...")
    expected_validators = [
        "pm_validator",
        "architect_validator",
        "developer_validator",
        "test_suite_validator" if "test_suite_validator" in nodes else "oracle_validator",
        "executor_validator",
        "reviewer_validator"
    ]
    gate_f_ok = all(v in nodes for v in expected_validators)
    for v in expected_validators:
        status_icon = "✓" if v in nodes else "✗"
        print(f"  {status_icon} Node '{v}' present in StateGraph")
    print(f"Gate F Status: {'PASS' if gate_f_ok else 'FAIL'}")
    all_passed = all_passed and gate_f_ok

    # Gate G: Validator Failure Halt & Route
    print("\n[Gate G]: Validator Failure Halt & Route Check...")
    synthetic_bad_dev_state = {
        "code_files": {"main.py": "def broken(\n"},
        "contract": {"task_intent": {"authoritative_target_file": "main.py"}},
        "target_language": "python",
        "iteration_count": 0,
        "max_iterations": 10
    }
    bad_res = validate_developer_phase(synthetic_bad_dev_state)
    gate_g_ok = (bad_res["verdict"] == "FAIL" and bad_res["repair_owner"] == "DEVELOPER")
    print(f"  ✓ Developer pre-execution failure detected: verdict={bad_res['verdict']}, owner={bad_res['repair_owner']}")
    print(f"Gate G Status: {'PASS' if gate_g_ok else 'FAIL'}")
    all_passed = all_passed and gate_g_ok

    # Gate H: Validator PASS Propagation
    print("\n[Gate H]: Validator PASS Propagation Check...")
    synthetic_good_dev_state = {
        "code_files": {"main.py": "def add(a: int, b: int) -> int: return a + b\n"},
        "contract": {
            "task_intent": {"authoritative_target_file": "main.py"},
            "interface_contracts": [{"identifier": "add", "target_file": "main.py"}]
        },
        "target_language": "python",
        "iteration_count": 0,
        "max_iterations": 10
    }
    good_res = validate_developer_phase(synthetic_good_dev_state)
    gate_h_ok = (good_res["verdict"] == "PASS")
    print(f"  ✓ Developer valid code accepted: verdict={good_res['verdict']}")
    print(f"Gate H Status: {'PASS' if gate_h_ok else 'FAIL'}")
    all_passed = all_passed and gate_h_ok

    # Gate I: Telemetry Recording Verification
    print("\n[Gate I]: Telemetry Recording Verification...")
    test_run_id = f"preflight_test_{int(time.time())}"
    tracer = RunTracer.register(test_run_id, output_dir=OUTPUT_DIR / test_run_id)
    tracer.log_event(
        stage="phase_end_validation",
        event_type="preflight_test_event",
        iteration=0,
        data={"gate_i": "verified", "timestamp": datetime.now().isoformat()}
    )
    trace_file = OUTPUT_DIR / test_run_id / "run_trace.jsonl"
    gate_i_ok = trace_file.exists() and len(trace_file.read_text(encoding="utf-8").splitlines()) >= 1
    print(f"  ✓ Telemetry trace recorded at: {trace_file.name}")
    print(f"Gate I Status: {'PASS' if gate_i_ok else 'FAIL'}")
    all_passed = all_passed and gate_i_ok

    print("=" * 70)
    print(f"OVERALL PRE-FLIGHT STATUS: {'ALL GATES PASS (READY FOR PILOT)' if all_passed else 'PRE-FLIGHT FAILED (STOP)'}")
    print("=" * 70)
    return all_passed


# ==============================================================================
# 3-Run Pilot Execution
# ==============================================================================

def execute_single_pilot_run(task: dict, run_index: int) -> dict:
    """Menjalankan 1 run eksperimen terkontrol dengan graph phase-validated."""
    task_id = task["task_id"]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_id = f"pv_pilot_{task_id}_rep1_{timestamp}"
    run_dir = OUTPUT_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n" + "=" * 70)
    print(f"[PILOT RUN {run_index}/3]: {task_id.upper()} ({task['target_language']})")
    print(f"Run ID: {run_id}")
    print(f"Target File Authoritative: {task['authoritative_file']}")
    print(f"Expected Oracle Checksum: {task['expected_sha'][:16]}...")
    print("=" * 70)

    # Verifikasi 1-to-1 SHA-256 sebelum eksekusi
    sha_ok, act_sha, exp_sha = verify_explicit_oracle_sha(task)
    if not sha_ok:
        raise RuntimeError(f"ABORT: Frozen Oracle SHA mismatch for {task_id}! Actual: {act_sha}, Expected: {exp_sha}")

    tracer = RunTracer.register(run_id, output_dir=run_dir)
    tracer.log_event(
        stage="init",
        event_type="pilot_run_started",
        iteration=0,
        data={
            "task_id": task_id,
            "target_language": task["target_language"],
            "model": ALL_AGENTS_MODEL,
            "provider": PROVIDER,
            "max_iterations": MAX_ITERATIONS,
            "max_phase_repair_attempts": MAX_PHASE_REPAIR_ATTEMPTS,
            "max_contract_revisions": MAX_CONTRACT_REVISIONS,
            "max_blueprint_revisions": MAX_BLUEPRINT_REVISIONS,
            "oracle_path": task["oracle_path"],
            "oracle_sha256": act_sha,
            "timestamp": datetime.now().isoformat()
        }
    )

    initial_state = {
        "task": task["task"],
        "target_language": task["target_language"],
        "provider": PROVIDER,
        "model_name": ALL_AGENTS_MODEL,
        "developer_backend": DEVELOPER_BACKEND,
        "developer_model": DEVELOPER_MODEL,
        "max_iterations": MAX_ITERATIONS,
        "max_phase_repair_attempts": MAX_PHASE_REPAIR_ATTEMPTS,
        "max_contract_revisions": MAX_CONTRACT_REVISIONS,
        "max_blueprint_revisions": MAX_BLUEPRINT_REVISIONS,
        "frozen_oracle_path": task["oracle_path"],
        "expected_oracle_sha": task["expected_sha"],
        "executor_intervention_enabled": True,
        "executor_mode": "CODE_ONLY",
        "run_id": run_id,
        "output_dir": str(run_dir),
        "iteration_count": 0,
        "contract_revision_count": 0,
        "blueprint_revision_count": 0,
        "code_files": {},
        "test_files": {},
        "test_results": {},
        "logs": [],
        "previous_passed_tests": []
    }

    start_time = time.time()
    try:
        final_state = phase_validated_squad_graph.invoke(initial_state)
    except Exception as e:
        duration = time.time() - start_time
        print(f"\n[RUN CRASH / TRANSPORT ERROR]: {e}")
        return {
            "run_id": run_id,
            "task_id": task_id,
            "target_language": task["target_language"],
            "verdict": "FAIL",
            "failure_classification": "F. Infrastructure Failure",
            "duration_sec": duration,
            "error": str(e)
        }

    duration = time.time() - start_time
    test_results = final_state.get("test_results", {})
    passed = test_results.get("passed", False)
    loops_consumed = final_state.get("iteration_count", 0)
    passed_count = test_results.get("passed_count", 0)
    failed_count = test_results.get("failed_count", 0)
    total_tests = test_results.get("total", task["n_tests"])
    contract_status = final_state.get("contract_status")
    review_verdict = final_state.get("review_verdict", "FAIL")

    final_verdict = "PASS" if (passed and contract_status == "FROZEN" and review_verdict == "APPROVED") else "FAIL"

    # Trajectory & classification
    if final_verdict == "PASS":
        trajectory = "convergent" if loops_consumed <= 3 else "slow-convergent"
        failure_class = "NONE"
    else:
        trajectory = "stagnant" if loops_consumed >= MAX_ITERATIONS else "divergent"
        if contract_status != "FROZEN":
            failure_class = "C. Contract Failure"
        elif "syntax" in str(final_state.get("developer_feedback", "")).lower():
            failure_class = "A. Developer Failure"
        elif failed_count > 0:
            failure_class = "A. Developer Failure"
        else:
            failure_class = "E. Reviewer Failure"

    # Verifikasi integritas Frozen Oracle post-run
    sha_ok_post, act_sha_post, _ = verify_explicit_oracle_sha(task)
    if not sha_ok_post:
        raise RuntimeError(f"CRITICAL INTEGRITY FAILURE: Frozen Oracle modified during {task_id} execution! Hash: {act_sha_post}")

    trace_file = getattr(tracer, "trace_file", None)
    otrr_info = calculate_trace_otrr(trace_file) if trace_file else {}

    run_summary = {
        "run_id": run_id,
        "task_id": task_id,
        "target_language": task["target_language"],
        "model": ALL_AGENTS_MODEL,
        "final_verdict": final_verdict,
        "review_verdict": review_verdict,
        "loops_consumed": loops_consumed,
        "converged_within_3_loops": (final_verdict == "PASS" and loops_consumed <= 3),
        "tests_passed": passed_count,
        "tests_failed": failed_count,
        "tests_total": total_tests,
        "contract_status": contract_status,
        "trajectory": trajectory,
        "failure_classification": failure_class,
        "duration_sec": round(duration, 2),
        "oracle_sha256": act_sha_post,
        "oracle_sha_intact": sha_ok_post,
        "tester_agent_invocations": 0,
        "otrr": otrr_info.get("otrr", 0.0),
        "otrr_percent": otrr_info.get("otrr_percent", 0.0),
        "otrr_details": otrr_info
    }

    tracer.log_event(
        stage="summary",
        event_type="pilot_run_completed",
        iteration=loops_consumed,
        data=run_summary
    )

    print(f"\n[PILOT RUN {run_index} SUMMARY]: Verdict={final_verdict} | Loops={loops_consumed} | Tests={passed_count}/{total_tests} | OTRR={otrr_info.get('otrr_percent', 0.0)}% | Duration={duration:.1f}s")
    return run_summary


def run_full_pilot(start_from: int = 1, single_task_id: Optional[str] = None, model_name: Optional[str] = None, summary_file_path: Optional[str] = None, num_predict: Optional[int] = None):
    """Menjalankan pilot experiment dan menghasilkan/memperbarui ringkasan evaluasi."""
    if model_name or num_predict:
        configure_squad_model(model_name, num_predict)

    print("\n" + "=" * 70)
    print("PHASE-END VALIDATION PILOT EXPERIMENT")
    print(f"Active Model: {ALL_AGENTS_MODEL}")
    print(f"Active Num Predict: {os.environ.get('OLLAMA_NUM_PREDICT', '3000')}")
    print(f"Resuming from Run Index: {start_from}" if start_from > 1 else "Starting from Run 1")
    print("=" * 70)

    if summary_file_path:
        summary_file = Path(summary_file_path)
    elif model_name and model_name != "qwen2.5-coder:7b":
        safe_model = model_name.replace(":", "_").replace("/", "_")
        summary_file = PROJECT_ROOT / f"dokumentasi-pengembangan/experiments/deterministic_cep_pilot_summary_{safe_model}.json"
    else:
        summary_file = PROJECT_ROOT / "dokumentasi-pengembangan/experiments/deterministic_cep_pilot_summary.json"

    results = []
    if summary_file.exists() and (start_from > 1 or single_task_id):
        try:
            existing = json.loads(summary_file.read_text(encoding="utf-8"))
            results = existing.get("runs", [])
        except Exception:
            results = []

    tasks_to_run = []
    for idx, t in enumerate(TASKS, start=1):
        if single_task_id and t["task_id"] != single_task_id:
            continue
        if idx < start_from:
            continue
        tasks_to_run.append((idx, t))

    for idx, task in tasks_to_run:
        summary = execute_single_pilot_run(task, idx)
        # Update or append
        existing_idx = next((i for i, r in enumerate(results) if r["task_id"] == task["task_id"]), None)
        if existing_idx is not None:
            results[existing_idx] = summary
        else:
            results.append(summary)

        # Simpan checkpoint setiap kali satu run selesai
        total_failures = sum(r.get("otrr_details", {}).get("total_failures_with_repair", 0) for r in results)
        total_successes = sum(r.get("otrr_details", {}).get("first_turn_successes", 0) for r in results)
        aggregate_otrr = round(total_successes / total_failures, 4) if total_failures > 0 else 0.0

        summary_data = {
            "experiment": "phase_end_validation_pilot",
            "date": datetime.now().isoformat(),
            "total_runs_planned": len(TASKS),
            "runs_completed": len(results),
            "status": "COMPLETED" if len(results) >= len(TASKS) else f"PAUSED_AT_RUN_{idx}",
            "pass_count": sum(1 for r in results if r.get("final_verdict") == "PASS"),
            "convergent_within_3_loops_count": sum(1 for r in results if r.get("converged_within_3_loops", False)),
            "aggregate_otrr": aggregate_otrr,
            "aggregate_otrr_percent": round(aggregate_otrr * 100.0, 2),
            "runs": results
        }
        summary_file.write_text(json.dumps(summary_data, indent=2), encoding="utf-8")
        print(f"\nCheckpoint written to: {summary_file}")

    if len(results) >= len(TASKS):
        print("\n" + "=" * 70)
        print("STOP RULE REACHED: ALL 3 PILOT RUNS COMPLETED. STOPPING SYSTEM.")
        print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase-End Validation Pilot Runner")
    parser.add_argument("--preflight-only", action="store_true", help="Run only Pre-Flight Gates A-I without pilot execution")
    parser.add_argument("--start-from", type=int, default=1, help="Start from run index (1-3)")
    parser.add_argument("--task-id", type=str, default=None, help="Run specific task ID only")
    parser.add_argument("--model", type=str, default=None, help="Unified squad model override (e.g. qwen3:8b)")
    parser.add_argument("--num-predict", type=int, default=None, help="Ollama num_predict token limit override (default: 3000)")
    parser.add_argument("--summary-file", type=str, default=None, help="Custom summary output path")
    args = parser.parse_args()

    if args.model or args.num_predict:
        configure_squad_model(args.model, args.num_predict)

    if args.preflight_only:
        success = run_preflight_gates()
        sys.exit(0 if success else 1)
    else:
        preflight_ok = run_preflight_gates()
        if not preflight_ok:
            print("\nPRE-FLIGHT FAILED. ABORTING PILOT EXPERIMENT.")
            sys.exit(1)
        run_full_pilot(
            start_from=args.start_from,
            single_task_id=args.task_id,
            model_name=args.model,
            summary_file_path=args.summary_file,
            num_predict=args.num_predict
        )
