from pathlib import Path
from langgraph.graph import StateGraph, START, END
try:
    from .state import SquadState
    from .agents.pm import pm_agent
    from .agents.architect import architect_agent
    from .agents.developer import developer_agent
    from .agents.tester import tester_agent
    from .agents.reviewer import reviewer_agent
    from .executor_v2 import executor_node_v2 as executor_node
    from .tracer import get_tracer, compute_dict_hashes
    from .contract import seal_and_freeze_contract, verify_contract_checkpoint, ContractStatus
except (ImportError, ValueError):
    from state import SquadState
    from agents.pm import pm_agent
    from agents.architect import architect_agent
    from agents.developer import developer_agent
    from agents.tester import tester_agent
    from agents.reviewer import reviewer_agent
    from executor_v2 import executor_node_v2 as executor_node
    try:
        from tracer import get_tracer, compute_dict_hashes
    except ImportError:
        def get_tracer(run_id=None): return None
        def compute_dict_hashes(f): return {}
    try:
        from contract import seal_and_freeze_contract, verify_contract_checkpoint, ContractStatus
    except ImportError:
        def seal_and_freeze_contract(c): return True, c, [], []
        def verify_contract_checkpoint(c, name): pass
        class ContractStatus: FROZEN = "FROZEN"; REJECTED = "REJECTED"


def frozen_oracle_node(state: SquadState) -> dict:
    """
    Memuat seluruh test suite artifact statis immutable dari direktori frozen oracle yang telah divalidasi,
    mendukung multi-file test artifact secara deterministik dan melewati node QA Tester LLM.
    """
    oracle_path_str = state.get("frozen_oracle_path")
    if not oracle_path_str:
        raise ValueError("frozen_oracle_node dipanggil namun state['frozen_oracle_path'] kosong")
    
    oracle_dir = Path(oracle_path_str)
    if not oracle_dir.exists():
        raise FileNotFoundError(f"Direktori frozen oracle tidak ditemukan: {oracle_dir}")
        
    test_files = {}
    # Eksklusi berkas non-test seperti metadata, checksum, markdown, json konfigurasi, dan file tersembunyi
    EXCLUDED_NAMES = {"metadata.json", "checksums.sha256"}
    EXCLUDED_EXTS = {".json", ".sha256", ".md", ".txt"}
    
    for f in sorted(oracle_dir.glob("*")):
        if not f.is_file():
            continue
        if f.name in EXCLUDED_NAMES or f.suffix.lower() in EXCLUDED_EXTS or f.name.startswith("."):
            continue
        fname = f.name
        target_lang = state.get("target_language", "").lower()
        is_dart = "dart" in target_lang or "flutter" in target_lang or f.suffix.lower() == ".dart"
        if is_dart and not fname.startswith("test/"):
            fname = f"test/{fname}"
            
        test_files[fname] = f.read_text(encoding="utf-8")
            
    if not test_files:
        raise ValueError(f"Tidak ada berkas test artifact ditemukan di direktori frozen oracle: {oracle_dir}")
        
    test_hashes = compute_dict_hashes(test_files)
    
    # Observability Trace Logging: Rekam seluruh test artifact dan SHA-256 masing-masing
    tracer = get_tracer(state.get("run_id"))
    if tracer:
        tracer.log_event(
            stage="frozen_oracle",
            event_type="loaded",
            iteration=state.get("iteration_count", 0),
            data={
                "frozen_oracle_path": str(oracle_dir),
                "test_files": list(test_files.keys()),
                "test_files_hashes": test_hashes,
                "total_files": len(test_files),
                "oracle_type": "immutable_validated_suite"
            }
        )
        
    file_summary = ", ".join([f"{fname} ({h[:10]}...)" for fname, h in test_hashes.items()])
    return {
        "test_files": test_files,
        "logs": [f"[Frozen Oracle]: Berhasil memuat {len(test_files)} berkas test immutable dari {oracle_dir.name}: {file_summary}"]
    }

def route_after_developer(state: SquadState) -> str:
    """
    Menentukan apakah alur kerja perlu menyusun test suite baru via QA Tester (putaran awal),
    menggunakan frozen oracle jika dikonfigurasikan, atau langsung ke Sandbox Executor
    (putaran perbaikan/self-healing) dengan menggunakan test suite yang sudah ada sebagai
    tolok ukur pengujian regresi.
    """
    iteration = state.get("iteration_count", 0)
    has_tests = bool(state.get("test_files"))
    use_frozen = bool(state.get("frozen_oracle_path"))
    
    # Jika Developer mengalami MODEL_TRANSPORT_ERROR, segera hentikan pipeline ke END
    if state.get("status") == "transport_error":
        decision = END
        reason = "model_transport_error_abort"
    # Putaran awal (iteration == 0) atau belum ada file test
    elif iteration == 0 or not has_tests:
        if use_frozen:
            decision = "frozen_oracle"
            reason = "initial_run_frozen_oracle_loaded"
        else:
            decision = "tester"
            reason = "initial_run_or_no_tests"
    elif state.get("tests_need_update", False) and not use_frozen:
        decision = "tester"
        reason = "developer_requested_test_update"
    else:
        decision = "executor"
        reason = "self_healing_regression_retest"

    # Observability: Catat keputusan routing
    tracer = get_tracer(state.get("run_id"))
    if tracer:
        tracer.log_event(
            stage="routing",
            event_type="decision",
            iteration=iteration,
            data={
                "previous_stage": "developer",
                "target_node": decision,
                "reason": reason,
                "has_tests": has_tests,
                "iteration": iteration,
                "use_frozen_oracle": use_frozen
            }
        )
        
    return decision

def route_after_executor(state: SquadState) -> str:
    """
    Menentukan apakah alur kerja perlu berputar kembali ke Developer (Self-Healing Loop)
    jika pengujian gagal dan batas iterasi belum tercapai, atau lanjut ke Code Reviewer.
    """
    test_results = state.get("test_results", {})
    passed = test_results.get("passed", False)
    iteration = state.get("iteration_count", 0)
    max_it = state.get("max_iterations")
    max_iter = 3 if max_it is None else int(max_it)

    
    if not passed and iteration < max_iter:
        decision = "developer"
        reason = "test_failed_retry"
    elif not passed and iteration >= max_iter:
        decision = "reviewer"
        reason = "max_iterations_reached"
    else:
        decision = "reviewer"
        reason = "tests_passed"

    # Observability: Catat keputusan routing
    tracer = get_tracer(state.get("run_id"))
    if tracer:
        tracer.log_event(
            stage="routing",
            event_type="decision",
            iteration=iteration,
            data={
                "previous_stage": "executor",
                "target_node": decision,
                "reason": reason,
                "tests_passed": passed,
                "current_iteration": iteration,
                "max_iterations": max_iter
            }
        )
        
    return decision

def contract_validation_node(state: SquadState) -> dict:
    """
    Mengeksekusi Deterministic Contract Validation Gate (P0-2 & P0-2.1) antara Architect dan Developer.
    Jika ada kontrak pada state:
    1. Validasi 4 pilar (Schema, Referential Integrity, Requirement Coverage & Mandatory Interface, Consistency).
    2. Jika lulus: hitung canonical SHA-256 (RFC 8785 anti-circular) dan segel status ke FROZEN.
    3. Jika gagal: tetapkan status REJECTED, catat feedback terstruktur, dan naikkan contract_revision_count.
    Jika tidak ada kontrak (legacy test/mock): lewati secara aman tanpa blocking.
    """
    contract = state.get("contract")
    if not contract:
        return {"status": "contract_gate_skipped"}

    tracer = get_tracer(state.get("run_id"))
    if tracer:
        tracer.log_event(
            stage="contract_gate",
            event_type="contract_validation_started",
            iteration=state.get("contract_revision_count", 0),
            data={
                "contract_id": contract.get("contract_id"),
                "status_before": contract.get("status")
            }
        )

    frozen_oracle_path = state.get("frozen_oracle_path")
    user_task = state.get("task", "")

    success, frozen_contract, errors, warnings = seal_and_freeze_contract(
        contract,
        frozen_oracle_path=frozen_oracle_path,
        task_text=user_task
    )

    if success:
        sha256_seal = frozen_contract.get("provenance", {}).get("contract_sha256", "")
        if tracer:
            tracer.log_event(
                stage="contract_gate",
                event_type="contract_frozen",
                iteration=state.get("contract_revision_count", 0),
                data={
                    "contract_id": frozen_contract.get("contract_id"),
                    "contract_sha256": sha256_seal,
                    "warnings_count": len(warnings)
                }
            )

        new_log = f"[Contract Validation Gate]: Kontrak divalidasi 100% dan TERKUNCI (FROZEN) dengan segel SHA-256 {sha256_seal[:12]}..."
        return {
            "contract": frozen_contract,
            "contract_version": frozen_contract.get("contract_version", "1.0.1"),
            "contract_status": ContractStatus.FROZEN.value,
            "contract_sha256": sha256_seal,
            "contract_validation_errors": [],
            "contract_feedback": None,
            "logs": state.get("logs", []) + [new_log]
        }
    else:
        revision_count = state.get("contract_revision_count", 0) + 1
        feedback_str = "\n\n".join(errors)

        if tracer:
            tracer.log_event(
                stage="contract_gate",
                event_type="contract_validation_failed",
                iteration=revision_count,
                data={
                    "contract_id": contract.get("contract_id"),
                    "errors": errors,
                    "warnings": warnings,
                    "contract_revision_count": revision_count
                }
            )

        max_cr = state.get("max_contract_revisions")
        max_contract_rev = 2 if max_cr is None else int(max_cr)
        new_log = (
            f"[Contract Validation Gate]: Validasi kontrak DITOLAK (REJECTED) dengan {len(errors)} galat deterministik "
            f"(Putaran revisi {revision_count}/{max_contract_rev})."
        )
        result = {
            "contract": frozen_contract,
            "contract_status": ContractStatus.REJECTED.value,
            "contract_validation_errors": errors,
            "contract_feedback": feedback_str,
            "contract_revision_count": revision_count,
            "logs": state.get("logs", []) + [new_log]
        }
        if revision_count >= max_contract_rev:
            result["status"] = "contract_validation_failed"
        return result


def route_after_contract_gate(state: SquadState) -> str:
    """
    Menentukan routing pasca Deterministic Contract Validation Gate (P0-2.1):
    1. Kontrak FROZEN (atau gate dilewati/tidak ada kontrak): lanjut ke Developer.
    2. Kontrak REJECTED dan revision_count < max_contract_revisions: rute kembali ke Architect untuk revisi.
    3. Kontrak REJECTED dan revision_count >= max_contract_revisions: STOP di END (FAIL). Developer TIDAK BOLEH dieksekusi.
    """
    contract_status = state.get("contract_status")
    revision_count = state.get("contract_revision_count", 0)
    max_cr = state.get("max_contract_revisions")
    max_contract_rev = 2 if max_cr is None else int(max_cr)

    if contract_status == ContractStatus.FROZEN.value or contract_status is None:
        decision = "developer"
        reason = "contract_frozen_or_absent"
    elif contract_status == ContractStatus.REJECTED.value and revision_count < max_contract_rev:
        decision = "architect"
        reason = f"contract_rejected_revision_{revision_count}"
    else:
        # REJECTED dan batas revisi (>= max_contract_rev) tercapai: FAIL / STOP langsung ke END
        decision = END
        reason = "contract_rejected_revision_limit_reached_abort"

    tracer = get_tracer(state.get("run_id"))
    if tracer:
        tracer.log_event(
            stage="routing",
            event_type="decision",
            iteration=revision_count,
            data={
                "previous_stage": "contract_gate",
                "target_node": str(decision),
                "reason": reason,
                "contract_status": contract_status,
                "contract_revision_count": revision_count
            }
        )

    return decision


def build_squad_graph():
    """Membangun StateGraph lengkap untuk virtual software squad ReinDev Studio."""
    workflow = StateGraph(SquadState)
    
    # 1. Daftarkan seluruh Node Spesialis
    workflow.add_node("pm", pm_agent)
    workflow.add_node("architect", architect_agent)
    workflow.add_node("contract_gate", contract_validation_node)
    workflow.add_node("developer", developer_agent)
    workflow.add_node("tester", tester_agent)
    workflow.add_node("frozen_oracle", frozen_oracle_node)
    workflow.add_node("executor", executor_node)
    workflow.add_node("reviewer", reviewer_agent)
    
    # 2. Rangkaikan Edges Sekuensial & Conditional Contract Gate (P0-2.1)
    workflow.add_edge(START, "pm")
    workflow.add_edge("pm", "architect")
    workflow.add_edge("architect", "contract_gate")
    
    # Conditional edge dari contract_gate: rute ke developer jika FROZEN,
    # rute ke architect jika REJECTED (revisi < 2), atau STOP ke END jika revisi >= 2
    workflow.add_conditional_edges(
        "contract_gate",
        route_after_contract_gate,
        {
            "developer": "developer",
            "architect": "architect",
            END: END
        }
    )
    
    # Conditional edge dari developer: panggil tester atau frozen_oracle pada loop 0
    workflow.add_conditional_edges(
        "developer",
        route_after_developer,
        {
            "tester": "tester",
            "frozen_oracle": "frozen_oracle",
            "executor": "executor",
            END: END
        }
    )
    workflow.add_edge("tester", "executor")
    workflow.add_edge("frozen_oracle", "executor")
    
    # 3. Rangkaikan Conditional Edge (Cyclic Self-Healing Loop)
    workflow.add_conditional_edges(
        "executor",
        route_after_executor,
        {
            "developer": "developer",
            "reviewer": "reviewer"
        }
    )
    
    # 4. Finalisasi Alur
    workflow.add_edge("reviewer", END)
    
    return workflow.compile()

# Instance default yang siap digunakan
squad_graph = build_squad_graph()

