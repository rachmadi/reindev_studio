#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
run_repair_depth_a5_d5_ablation.py — 9-Run Controlled Ablation Runner
Repair-Depth Experiment: Architect 5 + Developer 5
Model: qwen2.5-coder:7b (100% Unified Local Squad via Ollama)

Independent Depth Budgets:
- Architect Blueprint Validator: max_blueprint_revisions = 5
- Architect Contract Gate: max_contract_revisions = 5
- Developer Self-Healing Loop: max_iterations = 5

Metrics Tracked:
- architect_blueprint_repair_depth
- architect_contract_repair_depth
- developer_repair_depth
- repair_trajectory (convergent, slow-convergent, stagnant, oscillating, regressive, gated)
"""

import os
import sys
import json
import time
import shutil
import hashlib
from datetime import datetime
from pathlib import Path

# Paths
SCRATCH_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = Path("D:/Pekerjaan/Antigravity/reindev_studio").resolve()
BACKEND_DIR = PROJECT_ROOT / "backend"

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(BACKEND_DIR))

# Fix Windows console UTF-8 encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Load .env
from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env")

# 100% Unified Squad: qwen2.5-coder:7b
ALL_AGENTS_MODEL = "qwen2.5-coder:7b"
DEVELOPER_MODEL = ALL_AGENTS_MODEL
DEVELOPER_BACKEND = "ollama"
PROVIDER = "ollama"
SQUAD_MODEL = ALL_AGENTS_MODEL
EXECUTOR_MODE = "SAFE"

# Repair-Depth parameters (Separate Independent Budgets)
MAX_BLUEPRINT_REVISIONS = 5  # Architect internal AST check
MAX_CONTRACT_REVISIONS = 5   # Architect Contract Gate check
MAX_ITERATIONS = 5           # Developer self-healing loops
N_REPS = 3

os.environ["DEVELOPER_BACKEND"] = DEVELOPER_BACKEND
os.environ["DEVELOPER_MODEL"] = DEVELOPER_MODEL
os.environ["OLLAMA_MODEL"] = ALL_AGENTS_MODEL
os.environ["OLLAMA_NUM_CTX"] = "8192"
os.environ["OLLAMA_NUM_PREDICT"] = "3000"

from backend.graph import build_squad_graph
from backend.tracer import RunTracer
from backend.developer_gateway import DeveloperGateway

ORACLE_BASE = PROJECT_ROOT / "dokumentasi-pengembangan/experiments/frozen_oracle"
OUTPUT_DIR = PROJECT_ROOT / "backend/output"
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
    },
    {
        "task_id": "cli_t1",
        "task": "Bangun kalkulator CLI Python dengan operasi matematika matriks dan penanganan error komprehensif.",
        "target_language": "python",
        "oracle_path": str(ORACLE_BASE / "cli_t1"),
        "expected_sha": "0bd5b598afa7ae4c9cdf0e269d13136b51d35a4e0b1ac6548f0a2cf8a8eba124",
        "oracle_file": "test_main.py",
        "n_tests": 5,
    },
    {
        "task_id": "flutter_t1",
        "task": "Bangun komponen widget kartu metrik modern responsif Flutter dengan Material Design 3 dan Riverpod state.",
        "target_language": "dart",
        "oracle_path": str(ORACLE_BASE / "flutter_t1"),
        "expected_sha": "4589e15cfb8f37ba70642e70623ca143bceee1a44175aefd072f441d9e8a9528",
        "oracle_file": "card_metric_test.dart",
        "n_tests": 2,
    },
]


def verify_sha(task):
    fp = Path(task["oracle_path"]) / task["oracle_file"]
    if not fp.exists():
        return False, "FILE_NOT_FOUND"
    content = fp.read_bytes()
    actual_sha = hashlib.sha256(content).hexdigest().lower()
    return (actual_sha == task["expected_sha"].lower()), actual_sha


def pre_flight_check():
    print("=" * 70)
    print("PRE-FLIGHT CHECK — REPAIR-DEPTH EXPERIMENT (Architect 5 + Developer 5)")
    print("======================================================================")
    print(f"[PASS] Environment: DEVELOPER_BACKEND={DEVELOPER_BACKEND}")
    print(f"[PASS] Environment: ALL_AGENTS_MODEL={ALL_AGENTS_MODEL}")
    print(f"[PASS] Environment: OLLAMA_NUM_CTX=8192, OLLAMA_NUM_PREDICT=3000")
    print(f"[PASS] Environment: EXECUTOR_MODE={EXECUTOR_MODE}")
    print(f"[PASS] Repair-Depth: Architect BP Revs={MAX_BLUEPRINT_REVISIONS}, Gate Revs={MAX_CONTRACT_REVISIONS}")
    print(f"[PASS] Repair-Depth: Developer Max Loops={MAX_ITERATIONS}")

    adapter = DeveloperGateway.create_adapter(backend=DEVELOPER_BACKEND, model=DEVELOPER_MODEL)
    print(f"[PASS] DeveloperGateway adapter initialized: model={adapter.model}")

    print("[*] Verifying all Frozen Oracles SHA-256 integrity...")
    for t in TASKS:
        ok, sha = verify_sha(t)
        assert ok, f"FATAL: Oracle SHA mismatch for {t['task_id']}: {sha} != {t['expected_sha']}"
        print(f"    - {t['task_id']}: OK ({sha[:16]}...)")
    print("[PASS] All Frozen Oracles verified 100% immutable!")
    print("=" * 70)
    print()


def extract_trace_metrics(trace_path: Path) -> dict:
    if not trace_path.exists():
        return {
            "gateway_latency_s": 0.0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "semantic_hint": None,
            "blueprint_revisions": 0,
            "blueprint_errors": [],
            "parse_events": [],
        }

    lines = trace_path.read_text(encoding="utf-8", errors="replace").strip().splitlines()
    events = [json.loads(l) for l in lines if l.strip()]

    gw_latency = 0.0
    prompt_tokens = 0
    completion_tokens = 0
    semantic_hint = None
    bp_revisions = 0
    bp_errors = []
    parse_events = []

    for ev in events:
        event_type = ev.get("event_type")
        data = ev.get("data", {})

        if event_type == "gateway_call_completed":
            gw_latency += float(data.get("latency_s", 0.0))
            usage = data.get("usage") or {}
            p_tok = usage.get("prompt_eval_count") or usage.get("prompt_tokens") or 0
            c_tok = usage.get("eval_count") or usage.get("completion_tokens") or 0
            prompt_tokens += p_tok
            completion_tokens += c_tok

        elif event_type == "blueprint_validation_failed":
            bp_revisions = max(bp_revisions, int(ev.get("iteration", 0)))
            errs = data.get("errors", [])
            bp_errors.extend(errs)

        elif event_type == "developer_feedback_generated":
            if data.get("semantic_hint"):
                semantic_hint = data.get("semantic_hint")

        elif event_type == "diagnostic_parse_complete":
            parse_events.append(ev)

    return {
        "gateway_latency_s": round(gw_latency, 3),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "semantic_hint": semantic_hint,
        "blueprint_revisions": bp_revisions,
        "blueprint_errors": bp_errors,
        "parse_events": parse_events,
    }


def classify_trajectory(loops: int, verdict: str, parse_events: list) -> str:
    """
    Mengklasifikasikan pola perbaikan sepanjang loop:
    - gated: Berhenti di Contract Gate (loops == 0)
    - convergent: Lulus cepat (loop <= 3) atau error menurun secara monoton
    - slow-convergent: Lulus pada loop 4–5
    - stagnant: Error count dan signature identik persis di seluruh iterasi
    - oscillating: Error berayun/bergantian antara isu berbeda
    - regressive: Error bertambah parah seiring iterasi
    """
    if loops == 0:
        return "gated"
    if verdict == "PASS":
        return "convergent" if loops <= 3 else "slow-convergent"

    if len(parse_events) <= 1:
        return "stagnant"

    err_counts = []
    signatures = []
    for ev in parse_events:
        d = ev.get("data", {})
        err_counts.append(d.get("failed_tests", 0) + d.get("error_count", 0))
        f_tests = tuple(sorted(t.get("test_name", "") for t in d.get("failing_tests", [])))
        signatures.append((d.get("primary_failure_category"), f_tests))

    # Semua signature identik tanpa perubahan
    if len(set(signatures)) == 1:
        return "stagnant"

    # Penurunan galat monoton
    if len(err_counts) >= 2 and all(err_counts[i] > err_counts[i + 1] for i in range(len(err_counts) - 1)):
        return "convergent"

    # Perburukan galat monoton
    if len(err_counts) >= 2 and all(err_counts[i] < err_counts[i + 1] for i in range(len(err_counts) - 1)):
        return "regressive"

    return "oscillating"


def make_verdict(final_state, task, rep, run_id, duration, trace_path):
    status = final_state.get("status", "unknown")
    tr = final_state.get("test_results", {})
    passed = tr.get("passed", False)
    t_pass = tr.get("passed_count", 0)
    t_total = tr.get("total_count", 0)
    iteration = final_state.get("iteration_count", 0)
    notes = final_state.get("review_notes", "")

    contract = final_state.get("contract") or {}
    c_id = contract.get("contract_id", "N/A")
    c_ver = final_state.get("contract_version", "N/A")
    c_sha = final_state.get("contract_sha256", "N/A")
    c_status = final_state.get("contract_status", "N/A")
    c_errors = final_state.get("contract_validation_errors", [])
    c_rev_cnt = final_state.get("contract_revision_count", 0)
    c_feedback = final_state.get("contract_feedback")
    diag = final_state.get("diagnostic_evidence")

    approved_raw = final_state.get("is_approved")
    if approved_raw is True:
        reviewer = "APPROVED"
    elif approved_raw is False:
        reviewer = "NEEDS_REVISION"
    elif status == "tests_passed":
        reviewer = "APPROVED"
    else:
        reviewer = "NEEDS_REVISION" if not passed else "APPROVED"

    sha_ok, sha_actual = verify_sha(task)
    oracle_pass = passed and (t_pass >= task["n_tests"])
    contract_ok = (not c_errors) and (c_status == "FROZEN")
    loops_ok = iteration <= MAX_ITERATIONS
    verdict = "PASS" if (oracle_pass and contract_ok and loops_ok) else "FAIL"

    metrics = extract_trace_metrics(trace_path)
    trajectory = classify_trajectory(iteration, verdict, metrics.get("parse_events", []))

    # Repair Depths eksplisit
    architect_blueprint_repair_depth = final_state.get("blueprint_revision_count") or metrics["blueprint_revisions"]
    architect_contract_repair_depth = c_rev_cnt
    developer_repair_depth = iteration

    failure_category = "None"
    failure_error = "None"
    if verdict == "FAIL":
        if status == "transport_error":
            failure_category = "Infrastructure / Transport"
            failure_error = str(final_state.get("error", {}))
        elif c_status == "REJECTED" or c_errors:
            failure_category = "Contract / Specification"
            failure_error = "; ".join(c_errors) if c_errors else "Contract rejected"
        elif not oracle_pass:
            failure_category = "Developer Reasoning"
            out = tr.get("output", "")
            first_err = [line for line in out.splitlines() if "FAILED" in line or "Error" in line]
            failure_error = first_err[0] if first_err else out[:200]
        elif reviewer == "NEEDS_REVISION":
            failure_category = "Reviewer"
            failure_error = notes[:200]
        else:
            failure_category = "State / Loop"
            failure_error = f"Exceeded max loops ({iteration})"

    return {
        "run_id": run_id,
        "task_id": task["task_id"],
        "replication": rep,
        "developer_backend": DEVELOPER_BACKEND,
        "developer_model": DEVELOPER_MODEL,
        "squad_model": SQUAD_MODEL,
        "executor_mode": EXECUTOR_MODE,
        "duration_s": round(duration, 1),
        "loops": iteration,
        "max_loops": MAX_ITERATIONS,
        "architect_blueprint_repair_depth": architect_blueprint_repair_depth,
        "architect_contract_repair_depth": architect_contract_repair_depth,
        "developer_repair_depth": developer_repair_depth,
        "repair_trajectory": trajectory,
        "oracle_tests_pass": t_pass,
        "oracle_tests_total": t_total,
        "oracle_all_pass": oracle_pass,
        "oracle_sha_intact": sha_ok,
        "oracle_sha_actual": sha_actual[:16] + "...",
        "contract_id": c_id,
        "contract_version": c_ver,
        "contract_sha256": (c_sha[:16] + "...") if c_sha and c_sha != "N/A" else "N/A",
        "contract_status": c_status,
        "contract_errors": c_errors,
        "contract_revision_count": c_rev_cnt,
        "has_contract_feedback": bool(c_feedback),
        "blueprint_revisions": metrics["blueprint_revisions"],
        "blueprint_errors": metrics["blueprint_errors"],
        "reviewer_decision": reviewer,
        "pipeline_status": status,
        "has_p01_evidence": bool(diag),
        "gateway_latency_s": metrics["gateway_latency_s"],
        "prompt_tokens": metrics["prompt_tokens"],
        "completion_tokens": metrics["completion_tokens"],
        "total_tokens": metrics["total_tokens"],
        "semantic_hint": metrics["semantic_hint"],
        "failure_category": failure_category,
        "failure_error": failure_error[:300],
        "final_verdict": verdict,
        "raw_review_notes": notes[:500] if notes else "",
    }


def run_single_ablation(task, rep, run_idx, total_runs):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_id = f"project_repair_depth_a5_d5_{task['task_id']}_rep{rep}_{ts}"

    print(f"\n{'=' * 70}")
    print(f"RUN {run_idx}/{total_runs} | TASK: {task['task_id']} (Rep {rep}) | ID: {run_id}")
    print(f"DEPTH BUDGETS: Blueprint={MAX_BLUEPRINT_REVISIONS} | Contract Gate={MAX_CONTRACT_REVISIONS} | Developer Loops={MAX_ITERATIONS}")
    print(f"{'=' * 70}")

    proj_dir = OUTPUT_DIR / run_id
    proj_dir.mkdir(parents=True, exist_ok=True)
    trace_path = proj_dir / "run_trace.jsonl"

    tracer = RunTracer.register(run_id, proj_dir)
    tracer.log_event("run_lifecycle", "run_start", 0, {
        "task_id": task["task_id"],
        "replication": rep,
        "developer_backend": DEVELOPER_BACKEND,
        "developer_model": DEVELOPER_MODEL,
        "squad_model": SQUAD_MODEL,
        "executor_mode": EXECUTOR_MODE,
        "max_iterations": MAX_ITERATIONS,
        "max_blueprint_revisions": MAX_BLUEPRINT_REVISIONS,
        "max_contract_revisions": MAX_CONTRACT_REVISIONS,
    })

    initial_state = {
        "task": task["task"],
        "provider": PROVIDER,
        "model_name": SQUAD_MODEL,
        "developer_backend": DEVELOPER_BACKEND,
        "developer_model": DEVELOPER_MODEL,
        "target_language": task["target_language"],
        "specifications": "",
        "architecture_plan": "",
        "code_files": {},
        "test_files": {},
        "test_results": {},
        "iteration_count": 0,
        "max_iterations": MAX_ITERATIONS,
        "max_blueprint_revisions": MAX_BLUEPRINT_REVISIONS,
        "max_contract_revisions": MAX_CONTRACT_REVISIONS,
        "blueprint_revision_count": 0,
        "review_notes": "",
        "status": "in_progress",
        "logs": [],
        "run_id": run_id,
        "output_dir": str(proj_dir.resolve()),
        "executor_intervention_enabled": True,
        "executor_mode": EXECUTOR_MODE,
        "frozen_oracle_path": task["oracle_path"],
        "contract": None,
        "contract_status": None,
        "contract_version": None,
        "contract_revision_count": 0,
    }

    t0 = time.time()
    try:
        squad_graph = build_squad_graph()
        final_state = squad_graph.invoke(initial_state)
        duration = time.time() - t0
        summary = make_verdict(final_state, task, rep, run_id, duration, trace_path)

        tracer.log_event("run_lifecycle", "run_end", final_state.get("iteration_count", 0), {
            "verdict": summary["final_verdict"],
            "oracle_pass": summary["oracle_all_pass"],
            "loops": summary["loops"],
            "duration_s": summary["duration_s"],
            "contract_status": summary["contract_status"],
            "blueprint_revisions": summary["architect_blueprint_repair_depth"],
            "contract_revisions": summary["architect_contract_repair_depth"],
            "developer_depth": summary["developer_repair_depth"],
            "repair_trajectory": summary["repair_trajectory"],
            "failure_category": summary["failure_category"]
        })

    except Exception as e:
        duration = time.time() - t0
        print(f"[!] EXCEPTION during execution: {e}")
        summary = {
            "run_id": run_id,
            "task_id": task["task_id"],
            "replication": rep,
            "developer_backend": DEVELOPER_BACKEND,
            "developer_model": DEVELOPER_MODEL,
            "squad_model": SQUAD_MODEL,
            "executor_mode": EXECUTOR_MODE,
            "duration_s": round(duration, 1),
            "loops": 0,
            "max_loops": MAX_ITERATIONS,
            "architect_blueprint_repair_depth": 0,
            "architect_contract_repair_depth": 0,
            "developer_repair_depth": 0,
            "repair_trajectory": "exception",
            "oracle_tests_pass": 0,
            "oracle_tests_total": 0,
            "oracle_all_pass": False,
            "oracle_sha_intact": False,
            "oracle_sha_actual": "ERROR",
            "contract_id": "ERROR",
            "contract_version": "N/A",
            "contract_sha256": "N/A",
            "contract_status": "ERROR",
            "contract_errors": [str(e)],
            "contract_revision_count": 0,
            "has_contract_feedback": False,
            "blueprint_revisions": 0,
            "blueprint_errors": [],
            "reviewer_decision": "ERROR",
            "pipeline_status": "exception",
            "has_p01_evidence": False,
            "gateway_latency_s": 0.0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "semantic_hint": None,
            "failure_category": "Exception",
            "failure_error": str(e)[:300],
            "final_verdict": "FAIL",
            "raw_review_notes": "",
        }

    status_icon = "[PASS]" if summary["final_verdict"] == "PASS" else "[FAIL]"
    print(f"\n{status_icon} VERDICT: {summary['final_verdict']} | Task: {task['task_id']} Rep {rep}")
    print(f"    - Tests Pass    : {summary['oracle_tests_pass']}/{summary['oracle_tests_total']}")
    print(f"    - Duration      : {summary['duration_s']}s")
    print(f"    - Depths        : BP={summary['architect_blueprint_repair_depth']}/{MAX_BLUEPRINT_REVISIONS} | Gate={summary['architect_contract_repair_depth']}/{MAX_CONTRACT_REVISIONS} | Dev={summary['developer_repair_depth']}/{MAX_ITERATIONS}")
    print(f"    - Trajectory    : {summary['repair_trajectory']}")
    print(f"    - Contract      : {summary['contract_status']}")
    print(f"    - Failure Cat   : {summary['failure_category']}")
    print(f"    - Reviewer      : {summary['reviewer_decision']}")

    return summary


def main():
    pre_flight_check()

    total_runs = len(TASKS) * N_REPS
    print(f"[*] Starting Repair-Depth Experiment: Architect (BP={MAX_BLUEPRINT_REVISIONS}, Gate={MAX_CONTRACT_REVISIONS}) + Developer {MAX_ITERATIONS}")
    print(f"    Total tasks: {len(TASKS)}, Repetitions: {N_REPS}, Total runs: {total_runs}\n")

    all_results = []
    run_idx = 1
    t_start_all = time.time()

    for task in TASKS:
        for rep in range(1, N_REPS + 1):
            res = run_single_ablation(task, rep, run_idx, total_runs)
            all_results.append(res)
            run_idx += 1

    t_total_all = time.time() - t_start_all

    # Aggregate Statistics
    n_pass = sum(1 for r in all_results if r["final_verdict"] == "PASS")
    pass_rate = (n_pass / total_runs) * 100.0

    task_stats = {}
    for task in TASKS:
        tid = task["task_id"]
        t_runs = [r for r in all_results if r["task_id"] == tid]
        t_pass = sum(1 for r in t_runs if r["final_verdict"] == "PASS")
        task_stats[tid] = {
            "passed": t_pass,
            "total": len(t_runs),
            "pass_rate_pct": round((t_pass / len(t_runs)) * 100.0, 1),
            "avg_duration_s": round(sum(r["duration_s"] for r in t_runs) / len(t_runs), 1),
            "total_bp_depth": sum(r["architect_blueprint_repair_depth"] for r in t_runs),
            "total_gate_depth": sum(r["architect_contract_repair_depth"] for r in t_runs),
            "avg_dev_depth": round(sum(r["developer_repair_depth"] for r in t_runs) / len(t_runs), 1),
        }

    summary_data = {
        "experiment_name": "repair_depth_a5_d5_9run",
        "developer_model": DEVELOPER_MODEL,
        "squad_model": SQUAD_MODEL,
        "architect_blueprint_budget": MAX_BLUEPRINT_REVISIONS,
        "architect_contract_budget": MAX_CONTRACT_REVISIONS,
        "developer_depth_budget": MAX_ITERATIONS,
        "total_runs": total_runs,
        "total_pass": n_pass,
        "pass_rate_pct": round(pass_rate, 1),
        "total_duration_s": round(t_total_all, 1),
        "timestamp": datetime.now().isoformat(),
        "task_statistics": task_stats,
        "runs": all_results,
    }

    # Save JSON
    json_path = PROJECT_ROOT / "dokumentasi-pengembangan/experiments/repair_depth_a5_d5_summary.json"
    json_path.write_text(json.dumps(summary_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[PASS] Summary JSON written to: {json_path}")

    # Generate Markdown Report
    md_path = PROJECT_ROOT / "dokumentasi-pengembangan/experiments/repair_depth_a5_d5_result.md"
    md_content = f"""# Laporan Eksperimen: Repair-Depth (Architect 5 + Developer 5)

**Model Squad & Developer:** `{ALL_AGENTS_MODEL}` (100% Unified Local Squad)  
**Architect Depth Budget:** Blueprint = `{MAX_BLUEPRINT_REVISIONS}`, Contract Gate = `{MAX_CONTRACT_REVISIONS}`  
**Developer Depth Budget:** Max Loops = `{MAX_ITERATIONS}`  
**Tanggal Eksekusi:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} WIB  
**Total Durasi:** {t_total_all:.1f}s (~{t_total_all / 60:.1f} menit)  
**Gross Pass Rate:** **{n_pass} / {total_runs} ({pass_rate:.1f}%)**  

---

## 1. Ringkasan Eksekutif & Komparasi Repair-Depth

> **Hipotesis Netral:**  
> *Apakah peningkatan repair-depth dari A2/D3 menjadi A5/D5 meningkatkan kemampuan recovery Qwen 7B, dan apakah terdapat titik diminishing returns atau stagnation ketika jumlah iterasi diperbesar?*

| Dimensi Evaluasi | Baseline (A2 / D3) | Repair-Depth (A5 / D5) | Perubahan |
|---|---|---|---|
| **FastAPI T1 Pass Rate** | 0 / 3 (0.0%) | {task_stats['fastapi_t1']['passed']} / 3 ({task_stats['fastapi_t1']['pass_rate_pct']}%) | - |
| **CLI T1 Pass Rate** | 0 / 3 (0.0%) | {task_stats['cli_t1']['passed']} / 3 ({task_stats['cli_t1']['pass_rate_pct']}%) | - |
| **Flutter T1 Pass Rate** | 0 / 3 (0.0%) | {task_stats['flutter_t1']['passed']} / 3 ({task_stats['flutter_t1']['pass_rate_pct']}%) | - |
| **Total Pass Rate** | **0 / 9 (0.0%)** | **{n_pass} / {total_runs} ({pass_rate:.1f}%)** | - |
| **Rata-rata Durasi** | ~272 s / run | {t_total_all / total_runs:.1f} s / run | - |

---

## 2. Rincian Eksekusi & Metrik Repair-Depth per Run

| Run | Task | Rep | Status | Tests Pass | BP Depth | Gate Depth | Dev Depth | Trajectory | Contract | Failure Category | Detail Error |
|---|---|---|---|---|---|---|---|---|---|---|---|
"""
    for idx, r in enumerate(all_results, 1):
        err_short = r["failure_error"][:60].replace("\n", " ")
        md_content += f"| {idx} | {r['task_id']} | {r['replication']} | **{r['final_verdict']}** | {r['oracle_tests_pass']}/{r['oracle_tests_total']} | {r['architect_blueprint_repair_depth']}/{MAX_BLUEPRINT_REVISIONS} | {r['architect_contract_repair_depth']}/{MAX_CONTRACT_REVISIONS} | {r['developer_repair_depth']}/{MAX_ITERATIONS} | `{r['repair_trajectory']}` | {r['contract_status']} | {r['failure_category']} | `{err_short}` |\n"

    md_content += """
---
*Laporan ini dihasilkan secara otomatis oleh runner eksperimen terkontrol ReinDev Studio.*
"""
    md_path.write_text(md_content, encoding="utf-8")
    print(f"[PASS] Report Markdown written to: {md_path}")

    print("\n" + "=" * 70)
    print(f"REPAIR-DEPTH EXPERIMENT COMPLETED: {n_pass}/{total_runs} ({pass_rate:.1f}%) in {t_total_all:.1f}s")
    print("=" * 70)


if __name__ == "__main__":
    main()
