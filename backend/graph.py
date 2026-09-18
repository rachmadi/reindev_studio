# -*- coding: utf-8 -*-
"""
StateGraph Otoritatif ReinDev Studio — v2.2 (End-Phase Validated Engine)

Mengintegrasikan 6 End-Phase Quality Boundaries formal dengan penegakan mutlak:
1. Zero Downstream Leakage (No FAIL artifact crosses a phase boundary).
2. Universal Two-Repair Policy berbasis state counter integer non-negatif.
3. Causal Return phase-agnostic dengan revalidasi bertingkat (cascade revalidation).
4. Eliminasi shortcut Reviewer -> Developer -> Reviewer.
5. Eliminasi double gate redundancy pada Architect.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
import ast

from langgraph.graph import StateGraph, START, END

try:
    from .state import SquadState
    from .agents.v0 import v0_agent
    from .agents.pm import pm_agent
    from .agents.architect import architect_agent
    from .agents.developer import developer_agent
    from .agents.tester import tester_agent
    from .agents.reviewer import reviewer_agent
    from .executor_v2 import executor_node_v2 as executor_node
    from .tracer import get_tracer, compute_dict_hashes
    from .contract import seal_and_freeze_contract, verify_contract_checkpoint, ContractStatus
    from .phase_validators import (
        validate_v0_phase,
        validate_pm_phase,
        validate_architect_phase,
        validate_developer_phase,
        validate_dart_syntax_structural,
        validate_oracle_phase,
        validate_executor_phase,
        validate_reviewer_phase
    )
    from .contextual_evidence import ContextualEvidencePackage, render_repair_directive
except (ImportError, ValueError):
    from state import SquadState
    try:
        from agents.v0 import v0_agent
    except ImportError:
        def v0_agent(s): return s
    from agents.pm import pm_agent
    from agents.architect import architect_agent
    from agents.developer import developer_agent
    from agents.tester import tester_agent
    from agents.reviewer import reviewer_agent
    try:
        from executor_v2 import executor_node_v2 as executor_node
    except ImportError:
        from executor import executor_node
    try:
        from tracer import get_tracer, compute_dict_hashes
    except ImportError:
        def get_tracer(run_id=None): return None
        def compute_dict_hashes(f): return {}
    try:
        from contract import seal_and_freeze_contract, verify_contract_checkpoint, ContractStatus
    except ImportError:
        def seal_and_freeze_contract(c, **kw): return True, c, [], []
        def verify_contract_checkpoint(c, name): pass
        class ContractStatus: FROZEN = "FROZEN"; REJECTED = "REJECTED"
    try:
        from phase_validators import (
            validate_v0_phase,
            validate_pm_phase,
            validate_architect_phase,
            validate_developer_phase,
            validate_dart_syntax_structural,
            validate_oracle_phase,
            validate_executor_phase,
            validate_reviewer_phase
        )
    except ImportError:
        pass
    try:
        from contextual_evidence import ContextualEvidencePackage, render_repair_directive
    except ImportError:
        ContextualEvidencePackage = None
        render_repair_directive = lambda pkg, **kw: ""


# ==============================================================================
# Helper Functions for Counter & Repair Budget
# ==============================================================================

def _get_repair_count(state: SquadState, phase_name: str) -> int:
    counts = state.get("repair_attempt_counts") or {}
    if phase_name in counts:
        return counts[phase_name]
    if phase_name == "architect":
        return int(state.get("contract_revision_count") or 0)
    return 0


def _get_max_repairs(state: SquadState) -> int:
    val = state.get("max_phase_repair_attempts")
    return int(val) if val is not None else 2



def _increment_repair_count(state: SquadState, phase_name: str) -> Dict[str, int]:
    counts = dict(state.get("repair_attempt_counts") or {})
    counts[phase_name] = counts.get(phase_name, 0) + 1
    return counts


# ==============================================================================
# Node 0: V0 Requirement Interpreter & V0 Boundary
# ==============================================================================

def v0_validator_node(state: SquadState) -> Dict[str, Any]:
    """V0: Memvalidasi Structured Application Requirement Model sebelum melangkah ke PM."""
    contract = validate_v0_phase(state)
    tracer = get_tracer(state.get("run_id"))
    count = _get_repair_count(state, "v0")
    max_repairs = _get_max_repairs(state)

    if tracer:
        tracer.log_event(
            stage="phase_end_validation",
            event_type="v0_validation",
            iteration=count,
            data=contract
        )

    verdict = contract.get("verdict", "FAIL")
    logs = list(state.get("logs") or [])
    logs.append(f"[V0 Validator (Repair {count}/{max_repairs})]: Verdict = {verdict} ({len(contract.get('violations', []))} violations)")

    res: Dict[str, Any] = {
        "v0_validator_contract": contract,
        "logs": logs
    }

    if verdict == "FAIL":
        if count < max_repairs:
            new_counts = _increment_repair_count(state, "v0")
            res["repair_attempt_counts"] = new_counts
            cep_dict = contract.get("contextual_evidence_package")
            if cep_dict:
                res["latest_evidence_package"] = cep_dict
                if ContextualEvidencePackage is not None and render_repair_directive is not None:
                    pkg = ContextualEvidencePackage.from_dict(cep_dict)
                    rendered = render_repair_directive(pkg)
                    res["v0_feedback"] = rendered
        else:
            res["status"] = "terminal_failure_v0_boundary"

    return res


def route_after_v0_validator(state: SquadState) -> str:
    """Routing V0: Zero downstream leakage on FAIL."""
    contract = state.get("v0_validator_contract") or {}
    verdict = contract.get("verdict")
    count = _get_repair_count(state, "v0")
    max_repairs = _get_max_repairs(state)

    if verdict == "PASS":
        return "pm"

    if count <= max_repairs and state.get("status") != "terminal_failure_v0_boundary":
        return "v0"

    return END


# ==============================================================================
# Node 1: Product Manager & V1 Boundary
# ==============================================================================

def pm_validator_node(state: SquadState) -> Dict[str, Any]:
    """V1: Memvalidasi artefak spesifikasi PM sebelum melangkah ke Architect."""
    contract = validate_pm_phase(state)
    tracer = get_tracer(state.get("run_id"))
    count = _get_repair_count(state, "pm")
    max_repairs = _get_max_repairs(state)

    if tracer:
        tracer.log_event(
            stage="phase_end_validation",
            event_type="pm_validation",
            iteration=count,
            data=contract
        )

    verdict = contract.get("verdict", "FAIL")
    logs = list(state.get("logs") or [])
    logs.append(f"[V1 PM Validator (Repair {count}/{max_repairs})]: Verdict = {verdict} ({len(contract.get('violations', []))} violations)")

    res: Dict[str, Any] = {
        "pm_validator_contract": contract,
        "logs": logs
    }

    if verdict == "FAIL":
        if count < max_repairs:
            new_counts = _increment_repair_count(state, "pm")
            res["repair_attempt_counts"] = new_counts
            cep_dict = contract.get("contextual_evidence_package")
            if cep_dict:
                res["latest_evidence_package"] = cep_dict
                if ContextualEvidencePackage is not None and render_repair_directive is not None:
                    pkg = ContextualEvidencePackage.from_dict(cep_dict)
                    rendered = render_repair_directive(pkg)
                    res["pm_feedback"] = rendered
        else:
            res["status"] = "terminal_failure_pm_boundary"

    return res


def route_after_pm_validator(state: SquadState) -> str:
    """Routing V1: Zero downstream leakage on FAIL."""
    contract = state.get("pm_validator_contract") or {}
    verdict = contract.get("verdict")
    count = _get_repair_count(state, "pm")
    max_repairs = _get_max_repairs(state)

    if verdict == "PASS":
        return "architect"

    if count <= max_repairs and state.get("status") != "terminal_failure_pm_boundary":
        return "pm"

    return END


# ==============================================================================
# Node 2: System Architect & V2 Boundary (Single Consolidated Gate)
# ==============================================================================

def architect_validator_node(state: SquadState) -> Dict[str, Any]:
    """V2: Gerbang tunggal terpadu konsolidasi Contract Gate dan Architect Phase Validator."""
    if state.get("status") in ("DELIVERY_FAILURE", "STATE_REPRESENTATION_FAILURE"):
        fail_status = state.get("status")
        logs = list(state.get("logs") or [])
        logs.append(f"[V2 Architect Validator]: Halted due to {fail_status} (repair turn NOT consumed).")
        return {
            "status": fail_status,
            "contract_status": fail_status,
            "contract_validation_errors": state.get("contract_validation_errors", []),
            "delivery_valid": False,
            "delivery_errors": state.get("delivery_errors", []),
            "delivery_failure_reason": state.get("delivery_failure_reason", ""),
            "logs": logs
        }

    count = _get_repair_count(state, "architect")
    max_repairs = _get_max_repairs(state)
    tracer = get_tracer(state.get("run_id"))

    contract = state.get("contract")
    frozen_oracle_path = state.get("frozen_oracle_path")
    user_task = state.get("task", "")

    # 1. Deterministic Contract Seal
    success = False
    frozen_contract = contract
    errors = []
    warnings = []
    sha256_seal = ""

    bp = state.get("architectural_blueprint")
    if contract:
        success, frozen_contract, errors, warnings = seal_and_freeze_contract(
            contract,
            frozen_oracle_path=frozen_oracle_path,
            task_text=user_task,
            blueprint=bp,
            state=state
        )
        if success:
            sha256_seal = frozen_contract.get("provenance", {}).get("contract_sha256", "")

    # 2. Evaluate Architect Phase Contract & Blueprint
    temp_state = dict(state)
    temp_state["contract_validation_errors"] = errors
    temp_state["contract_validation_warnings"] = warnings
    if success:
        temp_state["contract"] = frozen_contract
        temp_state["contract_status"] = ContractStatus.FROZEN.value
        temp_state["contract_sha256"] = sha256_seal
    else:
        temp_state["contract"] = frozen_contract
        temp_state["contract_status"] = ContractStatus.REJECTED.value

    val_contract = validate_architect_phase(temp_state)

    if success and val_contract.get("verdict") == "PASS":
        verdict = "PASS"
    else:
        verdict = "FAIL"

    cov_matrix_data = None
    if isinstance(frozen_contract, dict):
        cov_matrix_data = (
            frozen_contract.get("provenance", {}).get("coverage_matrix")
            or frozen_contract.get("coverage_matrix")
        )

    if tracer:
        current_active_errors = list(errors)
        prov = frozen_contract.get("provenance", {}) if isinstance(frozen_contract, dict) else {}
        val_history = list(prov.get("validation_history", [])) if isinstance(prov, dict) else []
        historical_errs = set()
        for h in val_history:
            if isinstance(h, dict) and "errors" in h and isinstance(h["errors"], list):
                historical_errs.update(h["errors"])
        resolved_errors = list(historical_errs - set(current_active_errors))

        tracer.log_event(
            stage="phase_end_validation",
            event_type="architect_validation",
            iteration=count,
            data={
                "verdict": verdict,
                "seal_success": success,
                "val_contract": val_contract,
                "coverage_matrix": cov_matrix_data,
                "telemetry": {
                    "turn_id": count,
                    "phase": "ARCHITECT",
                    "current_validation_errors": current_active_errors,
                    "active_error_count": len(current_active_errors),
                    "historical_error_count": len(val_history),
                    "resolved_error_count": len(resolved_errors),
                    "resolved_failures": resolved_errors,
                    "repair_attempt": count
                }
            }
        )

    logs = list(state.get("logs") or [])
    logs.append(f"[V2 Architect Validator (Repair {count}/{max_repairs})]: Verdict = {verdict} (FROZEN={success})")

    snaps = (
        frozen_contract.get("provenance", {}).get("scaffold_snapshots")
        if isinstance(frozen_contract, dict)
        else (state.get("scaffold_snapshots") or [])
    )

    res: Dict[str, Any] = {
        "architect_validator_contract": val_contract,
        "contract_validation_errors": errors,
        "contract_validation_warnings": warnings,
        "contract_revision_count": count + 1,
        "scaffold_snapshots": snaps or list(state.get("scaffold_snapshots") or []),
        "latest_scaffold_matrix": state.get("latest_scaffold_matrix"),
        "logs": logs
    }

    if verdict == "PASS":
        res.update({
            "contract": frozen_contract,
            "contract_version": frozen_contract.get("contract_version", "1.0.1"),
            "contract_status": ContractStatus.FROZEN.value,
            "contract_sha256": sha256_seal,
            "contract_validation_errors": [],
            "contract_feedback": None
        })
    else:
        res["contract"] = frozen_contract
        if count < max_repairs:
            new_counts = _increment_repair_count(state, "architect")
            res["repair_attempt_counts"] = new_counts
            res["contract_revision_count"] = new_counts.get("architect", 1)

            cep_dict = val_contract.get("contextual_evidence_package")
            feedback_str = "\n\n".join(errors) if errors else ""
            if cep_dict:
                res["latest_evidence_package"] = cep_dict
                if ContextualEvidencePackage is not None and render_repair_directive is not None:
                    pkg = ContextualEvidencePackage.from_dict(cep_dict)
                    rendered = render_repair_directive(pkg)
                    feedback_str = (rendered + "\n\n" + feedback_str).strip()

            res["contract_status"] = ContractStatus.REJECTED.value
            res["contract_validation_errors"] = errors
            res["contract_feedback"] = feedback_str
        else:
            res["contract_status"] = ContractStatus.REJECTED.value
            res["status"] = "terminal_failure_architect_boundary"

    return res


def route_after_architect_validator(state: SquadState) -> str:
    """Routing V2: Zero downstream leakage on FAIL."""
    if state.get("status") in ("DELIVERY_FAILURE", "STATE_REPRESENTATION_FAILURE"):
        return END

    contract = state.get("architect_validator_contract") or {}
    verdict = contract.get("verdict")
    status = state.get("contract_status")
    count = _get_repair_count(state, "architect")
    max_repairs = _get_max_repairs(state)
    decision = END
    if verdict == "PASS" and status == ContractStatus.FROZEN.value:
        decision = "developer"
    elif count <= max_repairs and state.get("status") != "terminal_failure_architect_boundary":
        decision = "architect"

    tracer = get_tracer(state.get("run_id"))
    if tracer:
        tracer.log_event(
            stage="routing",
            event_type="decision",
            iteration=count,
            data={
                "previous_stage": "architect_validator",
                "target_node": str(decision),
                "verdict": verdict,
                "contract_status": status
            }
        )

    return decision


# ==============================================================================
# Node 3: Software Developer & V3 Boundary (Pre-Execution Gate)
# ==============================================================================

def developer_validator_node(state: SquadState) -> Dict[str, Any]:
    """V3: Pre-Execution Gate. Memvalidasi kepatuhan AST sintaks dan kontrak statis."""
    contract = validate_developer_phase(state)
    count = _get_repair_count(state, "developer")
    max_repairs = _get_max_repairs(state)
    tracer = get_tracer(state.get("run_id"))

    verdict = contract.get("verdict", "FAIL")
    if tracer:
        tracer.log_event(
            stage="phase_end_validation",
            event_type="developer_validation",
            iteration=count,
            data=contract
        )

    logs = list(state.get("logs") or [])
    logs.append(f"[V3 Developer Validator (Repair {count}/{max_repairs})]: Verdict = {verdict} ({len(contract.get('violations', []))} violations)")

    res: Dict[str, Any] = {
        "developer_validator_contract": contract,
        "logs": logs
    }

    if verdict == "FAIL":
        if count < max_repairs:
            new_counts = _increment_repair_count(state, "developer")
            res["repair_attempt_counts"] = new_counts
            cep_dict = contract.get("contextual_evidence_package")
            feedback = ""
            if cep_dict and ContextualEvidencePackage is not None and render_repair_directive is not None:
                res["latest_evidence_package"] = cep_dict
                pkg = ContextualEvidencePackage.from_dict(cep_dict)
                feedback = render_repair_directive(pkg)
            else:
                violations_str = "\n".join(f"- [{v.get('severity')}] {v.get('criterion')}: {v.get('message')}" for v in contract.get("violations", []))
                feedback = f"[PRE-EXECUTION VALIDATOR REJECTION (Repair {count+1}/{max_repairs})]:\n{violations_str}"
            res["developer_feedback"] = feedback
            res["status"] = "developer_preflight_rejected"
        else:
            res["status"] = "terminal_failure_developer_boundary"

    return res


def route_after_developer_validator(state: SquadState) -> str:
    """Routing V3: Zero downstream leakage to executor on FAIL."""
    contract = state.get("developer_validator_contract") or {}
    verdict = contract.get("verdict")
    count = _get_repair_count(state, "developer")
    max_repairs = _get_max_repairs(state)

    if verdict == "PASS":
        if state.get("frozen_oracle_path"):
            return "frozen_oracle"
        return "tester"

    if count <= max_repairs and state.get("status") != "terminal_failure_developer_boundary":
        return "developer"

    return END


# ==============================================================================
# Node 4: Test Suite Provisioner & V4 Boundary
# ==============================================================================

def frozen_oracle_node(state: SquadState) -> dict:
    """Memuat seluruh test suite statis immutable dari direktori frozen oracle."""
    oracle_path_str = state.get("frozen_oracle_path")
    if not oracle_path_str:
        raise ValueError("frozen_oracle_node dipanggil namun state['frozen_oracle_path'] kosong")

    oracle_dir = Path(oracle_path_str)
    if not oracle_dir.exists():
        raise FileNotFoundError(f"Direktori frozen oracle tidak ditemukan: {oracle_dir}")

    test_files = {}
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


def test_suite_validator_node(state: SquadState) -> Dict[str, Any]:
    """V4: Memvalidasi integritas Frozen Oracle atau struktur AST test suite QA Tester."""
    tracer = get_tracer(state.get("run_id"))
    use_frozen = bool(state.get("frozen_oracle_path"))

    if use_frozen:
        expected_sha = (
            state.get("expected_oracle_sha")
            or state.get("expected_frozen_oracle_sha")
        )
        if not expected_sha:
            contract_data = state.get("contract") or {}
            task_intent = contract_data.get("task_intent", {}) if isinstance(contract_data, dict) else {}
            expected_sha = task_intent.get("expected_oracle_sha") or contract_data.get("oracle_sha256")

        contract = validate_oracle_phase(state, expected_sha=expected_sha)
        verdict = contract.get("verdict", "FAIL")

        if tracer:
            tracer.log_event(
                stage="phase_end_validation",
                event_type="oracle_validation",
                iteration=0,
                data=contract
            )

        logs = list(state.get("logs") or [])
        logs.append(f"[V4 Test Suite Validator (Frozen Oracle)]: Verdict = {verdict}")

        res: Dict[str, Any] = {
            "test_suite_validator_contract": contract,
            "oracle_validator_contract": contract,
            "logs": logs
        }
        if verdict != "PASS":
            res["status"] = "terminal_failure_frozen_oracle_corrupt"
        return res
    else:
        count = _get_repair_count(state, "tester")
        max_repairs = _get_max_repairs(state)
        test_files = state.get("test_files") or {}
        target_lang = state.get("target_language", "python").strip()
        is_dart = "dart" in target_lang.lower() or "flutter" in target_lang.lower()

        violations = []
        if not test_files:
            violations.append({"criterion": "test_files_presence", "severity": "CRITICAL", "message": "No test files generated"})
        for fname, content in test_files.items():
            if fname.endswith(".py"):
                try:
                    ast.parse(content, filename=fname)
                except SyntaxError as e:
                    violations.append({
                        "criterion": "test_syntax",
                        "severity": "CRITICAL",
                        "message": f"SyntaxError in {fname}: {e}",
                        "location": f"{fname}:{e.lineno}"
                    })
            elif is_dart or fname.endswith(".dart"):
                is_valid_dart, dart_errs = validate_dart_syntax_structural(content)
                if not is_valid_dart:
                    violations.append({
                        "criterion": "test_syntax",
                        "severity": "CRITICAL",
                        "message": f"Dart structural syntax error in {fname}: {dart_errs}",
                        "location": fname
                    })

        verdict = "PASS" if not violations else "FAIL"
        contract = {
            "phase": "TEST_SUITE",
            "validator_type": "PHASE_END",
            "verdict": verdict,
            "violations": violations
        }

        if tracer:
            tracer.log_event(
                stage="phase_end_validation",
                event_type="test_suite_validation",
                iteration=count,
                data=contract
            )

        logs = list(state.get("logs") or [])
        logs.append(f"[V4 Test Suite Validator (QA Tester Repair {count}/{max_repairs})]: Verdict = {verdict}")

        res = {
            "test_suite_validator_contract": contract,
            "logs": logs
        }
        if verdict == "FAIL":
            if count < max_repairs:
                new_counts = _increment_repair_count(state, "tester")
                res["repair_attempt_counts"] = new_counts
                res["tester_feedback"] = violations
            else:
                res["status"] = "terminal_failure_tester_boundary"
        return res


def route_after_test_suite_validator(state: SquadState) -> str:
    """Routing V4: Zero downstream leakage to executor on FAIL."""
    contract = state.get("test_suite_validator_contract") or {}
    verdict = contract.get("verdict")
    use_frozen = bool(state.get("frozen_oracle_path"))

    if verdict == "PASS":
        return "executor"

    if not use_frozen:
        count = _get_repair_count(state, "tester")
        max_repairs = _get_max_repairs(state)
        if count <= max_repairs and state.get("status") != "terminal_failure_tester_boundary":
            return "tester"

    return END


# ==============================================================================
# Node 5: Sandbox Execution & V5 Boundary (Behavioral Execution Validator)
# ==============================================================================

def executor_validator_node(state: SquadState) -> Dict[str, Any]:
    """V5: Mengevaluasi bukti eksekusi sandbox, assertions, dan permanent regression history."""
    prev_tests = state.get("previous_passed_tests") or []
    contract = validate_executor_phase(state, previous_passed_tests=prev_tests)
    count = _get_repair_count(state, "executor")
    max_repairs = _get_max_repairs(state)
    tracer = get_tracer(state.get("run_id"))
    iteration = state.get("iteration_count", 0)

    if tracer:
        tracer.log_event(
            stage="iteration_validation",
            event_type="executor_iteration_validation",
            iteration=iteration,
            data=contract
        )

    current_passed = contract.get("current_passed_tests") or state.get("test_results", {}).get("passed_test_names", [])

    # Permanent Invariant Regression History Update
    history_map = dict(state.get("invariant_regression_history") or {})
    for reg in contract.get("regressions", []):
        t_name = reg.get("test_or_invariant", "")
        clean_name = t_name.split("::")[-1].strip()
        inv_id = f"INV-BEHAVIOR-{clean_name[:30].replace(' ', '_')}"
        if inv_id not in history_map:
            history_map[inv_id] = {
                "ever_regressed": True,
                "regression_count": 1,
                "regression_history": [{
                    "iteration": iteration,
                    "failure_evidence": reg.get("message", ""),
                }]
            }
        else:
            history_map[inv_id]["ever_regressed"] = True
            history_map[inv_id]["regression_count"] += 1
            history_map[inv_id]["regression_history"].append({
                "iteration": iteration,
                "failure_evidence": reg.get("message", ""),
            })

    for t_passed in current_passed:
        clean_name = t_passed.split("::")[-1].strip()
        inv_id = f"INV-BEHAVIOR-{clean_name[:30].replace(' ', '_')}"
        if inv_id in history_map and history_map[inv_id].get("ever_regressed"):
            rh = history_map[inv_id].get("regression_history", [])
            if rh and "recovered_at_iteration" not in rh[-1]:
                rh[-1]["recovered_at_iteration"] = iteration
                rh[-1]["recovery_status"] = "PROVEN_AGAIN"

    verdict = contract.get("verdict", "FAIL")
    logs = list(state.get("logs") or [])
    logs.append(f"[V5 Behavioral Validator (Repair {count}/{max_repairs})]: Verdict = {verdict} ({len(contract.get('regressions', []))} regressions)")

    res: Dict[str, Any] = {
        "executor_iteration_validator_contract": contract,
        "previous_passed_tests": current_passed,
        "invariant_regression_history": history_map,
        "locked_invariants": contract.get("locked_invariants", {}),
        "oscillation_history": contract.get("oscillation_history", []),
        "logs": logs,
        # Simpan evidence turn SAAT INI sebagai "previous" untuk turn berikutnya.
        # Digunakan oleh discover_newly_proven_invariants sebagai sumber kandidat saja
        # (bukan sebagai bukti PROVEN langsung — dual gate tetap menentukan status PROVEN).
        "previous_diagnostic_evidence": (state.get("test_results") or {}).get("diagnostic_evidence") or {},
        "previous_executor_stderr": (state.get("test_results") or {}).get("stderr") or "",
    }

    if verdict == "FAIL":
        if count < max_repairs:
            new_counts = _increment_repair_count(state, "executor")
            res["repair_attempt_counts"] = new_counts
            res["iteration_count"] = iteration + 1

            cep_dict = contract.get("contextual_evidence_package")
            if cep_dict:
                res["latest_evidence_package"] = cep_dict
                if ContextualEvidencePackage is not None and render_repair_directive is not None:
                    pkg = ContextualEvidencePackage.from_dict(cep_dict)
                    feedback = render_repair_directive(pkg)
                    c_owner = pkg.causal_owner.lower() if pkg.causal_owner else "developer"
                    res["causal_owner_phase"] = c_owner
                    res["developer_feedback"] = feedback
                    if c_owner == "architect":
                        res["architect_feedback"] = feedback
        else:
            res["status"] = "terminal_failure_behavioral_boundary"

    return res


def route_after_executor_validator(state: SquadState) -> str:
    """Routing V5: Zero downstream leakage to Reviewer on FAIL."""
    contract = state.get("executor_iteration_validator_contract") or {}
    verdict = contract.get("verdict")
    count = _get_repair_count(state, "executor")
    max_repairs = _get_max_repairs(state)

    if verdict == "PASS":
        return "reviewer"

    if count <= max_repairs and state.get("status") != "terminal_failure_behavioral_boundary":
        causal_owner = (state.get("causal_owner_phase") or "").lower()
        if causal_owner == "architect" and _get_repair_count(state, "architect") < max_repairs:
            return "architect"
        return "developer"

    # PENERAPAN MUTLAK ZERO LEAKAGE: FAIL TIDAK BOLEH KE REVIEWER!
    return END


# ==============================================================================
# Node 6: Code Reviewer & V6 Boundary
# ==============================================================================

def reviewer_validator_node(state: SquadState) -> Dict[str, Any]:
    """V6: Memvalidasi keabsahan keputusan Reviewer terhadap bukti Layer 1."""
    notes = state.get("review_notes", "")
    output_classification = state.get("reviewer_output_classification")
    classification = output_classification.get("classification") if output_classification else None
    terminal_status = output_classification.get("terminal_status") if output_classification else None

    # Jika output_classification belum ada di state tetapi notes kosong/whitespace,
    # deteksi secara deterministik sebagai EMPTY
    if not classification and (notes is None or not str(notes).strip()):
        classification = "EMPTY"
        terminal_status = "V6_OUTPUT_INVALID"

    # PRIORITAS 1: Jika reviewer_output_classification tersedia dan INVALID,
    # langsung tetapkan review_verdict tanpa membaca status field lama
    if classification in ("EMPTY", "MALFORMED", "NON_ACTIONABLE"):
        review_verdict = "REVIEWER_OUTPUT_INVALID"
    # PRIORITAS 2: classification VALID atau tidak ada classification -> baca dari output
    else:
        status = state.get("status", "").lower()
        if "completed" in status or "[approved]" in str(notes).lower():
            review_verdict = "APPROVED"
        elif "needs_revision" in status or "[needs_revision]" in str(notes).lower():
            review_verdict = "NEEDS_REVISION"
        else:
            review_verdict = "FAIL"

    contract = validate_reviewer_phase(
        state,
        review_verdict=review_verdict,
        review_notes=notes,
        reviewer_output_classification=classification,
        reviewer_terminal_status=terminal_status,
    )
    count = _get_repair_count(state, "reviewer")
    max_repairs = _get_max_repairs(state)
    tracer = get_tracer(state.get("run_id"))

    verdict = contract.get("verdict", "FAIL")
    if tracer:
        tracer.log_event(
            stage="phase_end_validation",
            event_type="reviewer_validation",
            iteration=count,
            data=contract
        )

    logs = list(state.get("logs") or [])
    logs.append(f"[V6 Reviewer Validator]: Verdict = {verdict} (Review Verdict = {review_verdict})")

    res: Dict[str, Any] = {
        "reviewer_validator_contract": contract,
        "review_verdict": review_verdict,
        "logs": logs
    }

    test_results = state.get("test_results") or {}
    is_test_passed = bool(test_results.get("passed", False))
    artifact_state = "GREEN" if is_test_passed else "RED"

    if review_verdict == "REVIEWER_OUTPUT_INVALID":
        retry_count = state.get("reviewer_retry_count") or 0
        retry_budget = state.get("reviewer_retry_budget")
        if retry_budget is None:
            retry_budget = 1

        if retry_count < retry_budget:
            new_retry_count = retry_count + 1
            res["reviewer_retry_count"] = new_retry_count
            logs.append(
                f"[V6 GREEN_STATE_PROTECTION]: Reviewer output {classification} -> {terminal_status}. "
                f"Artifact state: {artifact_state}. "
                f"Retry {new_retry_count}/{retry_budget}. "
                f"Developer routing: BLOCKED."
            )
        else:
            res["status"] = "terminal_failure_v6_reviewer_output"
            logs.append(
                f"[V6 GREEN_STATE_PROTECTION]: Reviewer output {classification} -> {terminal_status}. "
                f"Artifact state: {artifact_state}. "
                f"Retry budget exhausted ({retry_count}/{retry_budget}). "
                f"Terminal failure triggered. Developer routing: BLOCKED."
            )
    elif verdict == "FAIL":
        if count < max_repairs:
            new_counts = _increment_repair_count(state, "reviewer")
            res["repair_attempt_counts"] = new_counts
        else:
            res["status"] = "terminal_failure_reviewer_boundary"
    elif verdict == "PASS" and review_verdict == "NEEDS_REVISION":
        repair_owner = (contract.get("repair_owner") or "").lower()
        if repair_owner == "developer":
            dev_repairs = _get_repair_count(state, "developer")
            if dev_repairs < max_repairs:
                new_counts = _increment_repair_count(state, "developer")
                res["repair_attempt_counts"] = new_counts
                iteration = state.get("iteration_count", 0)
                res["iteration_count"] = iteration + 1
            else:
                res["status"] = "terminal_failure_reviewer_boundary"

    return res


def route_after_reviewer_validator(state: SquadState) -> str:
    """Routing V6: Konvergensi release gatekeeper."""
    contract = state.get("reviewer_validator_contract") or {}
    verdict = contract.get("verdict")
    eval_verdict = contract.get("evaluated_review_verdict")

    if verdict != "PASS":
        # Cek apakah ini adalah REVIEWER_OUTPUT_INVALID dengan retry tersisa
        if eval_verdict == "REVIEWER_OUTPUT_INVALID":
            retry_count = state.get("reviewer_retry_count", 0)
            retry_budget = state.get("reviewer_retry_budget")
            if retry_budget is None:
                retry_budget = 1
            term = state.get("status", "")
            if retry_count <= retry_budget and term != "terminal_failure_v6_reviewer_output":
                return "reviewer"   # Retry terkontrol
        return END

    if eval_verdict == "APPROVED":
        return END  # Success convergence

    if eval_verdict == "NEEDS_REVISION":
        repair_owner = (contract.get("repair_owner") or "").lower()
        if (
            repair_owner == "developer"
            and _get_repair_count(state, "developer") <= _get_max_repairs(state)
            and state.get("status") != "terminal_failure_reviewer_boundary"
        ):
            # Causal return ke developer: WAJIB lewat developer -> developer_validator -> test_suite -> executor -> reviewer
            return "developer"
        return END

    return END


# ==============================================================================
# Legacy Compatibility Aliases & Helpers
# ==============================================================================

def contract_validation_node(state: SquadState) -> dict:
    """Mengeksekusi Deterministic Contract Validation Gate (P0-2 & P0-2.1) secara mandiri untuk kompatibilitas."""
    contract = state.get("contract")
    if not contract:
        return {"status": "contract_gate_skipped"}

    revision_count = state.get("contract_revision_count", 0) + 1
    max_cr = state.get("max_phase_repair_attempts")
    if max_cr is None:
        max_cr = state.get("max_contract_revisions")
    max_contract_rev = 2 if max_cr is None else int(max_cr)

    frozen_oracle_path = state.get("frozen_oracle_path")
    user_task = state.get("task", "")

    bp = state.get("architectural_blueprint")
    success, frozen_contract, errors, warnings = seal_and_freeze_contract(
        contract,
        frozen_oracle_path=frozen_oracle_path,
        task_text=user_task,
        blueprint=bp
    )

    if success:
        sha256_seal = frozen_contract.get("provenance", {}).get("contract_sha256", "")
        return {
            "contract": frozen_contract,
            "contract_version": frozen_contract.get("contract_version", "1.0.1"),
            "contract_status": ContractStatus.FROZEN.value,
            "contract_sha256": sha256_seal,
            "contract_validation_errors": [],
            "contract_feedback": None,
            "contract_revision_count": revision_count,
            "logs": (state.get("logs") or []) + [f"[Contract Gate]: Kontrak FROZEN disahkan (SHA: {sha256_seal[:12]}...)."]
        }
    else:
        feedback_str = "\n".join(f"- {e}" for e in errors)
        result = {
            "contract_status": ContractStatus.REJECTED.value,
            "contract_revision_count": revision_count,
            "contract_validation_errors": errors,
            "contract_feedback": feedback_str,
            "logs": (state.get("logs") or []) + [f"[Contract Gate]: Kontrak REJECTED (Revisi {revision_count}/{max_contract_rev})."]
        }
        if revision_count >= max_contract_rev:
            result["status"] = "contract_validation_failed"
        return result


def route_after_contract_gate(state: SquadState) -> str:
    """Menentukan routing pasca Deterministic Contract Validation Gate (P0-2.1)."""
    contract_status = state.get("contract_status")
    revision_count = state.get("contract_revision_count", 0)
    max_cr = state.get("max_phase_repair_attempts")
    if max_cr is None:
        max_cr = state.get("max_contract_revisions")
    max_contract_rev = 2 if max_cr is None else int(max_cr)

    if contract_status == ContractStatus.FROZEN.value or contract_status is None:
        return "developer"
    elif contract_status == ContractStatus.REJECTED.value and revision_count < max_contract_rev:
        return "architect"
    else:
        return END


def route_after_developer(state: SquadState) -> str:
    """Legacy routing helper (backwards compatible with early unit tests)."""
    status = state.get("status")
    if status in ("transport_error", "terminal_failure_developer_boundary"):
        return END

    if state.get("developer_validator_contract"):
        return route_after_developer_validator(state)

    iter_count = state.get("iteration_count", 0)
    has_test_files = bool(state.get("test_files"))
    needs_update = state.get("tests_need_update", False)
    frozen_oracle = state.get("frozen_oracle_path")
    if iter_count == 0:
        if frozen_oracle:
            return "frozen_oracle"
        return "tester"
    if needs_update:
        return "tester"
    if has_test_files:
        return "executor"
    return "tester"


def route_after_executor(state: SquadState) -> str:
    """Legacy routing helper (backwards compatible with early unit tests)."""
    if state.get("executor_iteration_validator_contract"):
        return route_after_executor_validator(state)

    test_results = state.get("test_results", {})
    passed = test_results.get("passed", False)
    iteration = state.get("iteration_count", 0)
    max_it = state.get("max_iterations")
    max_iter = 3 if max_it is None else int(max_it)

    if not passed and iteration < max_iter:
        return "developer"
    return "reviewer"


# ==============================================================================
# Complete Authoritative StateGraph Builder
# ==============================================================================

def build_squad_graph():
    """Membangun StateGraph otoritatif tunggal ReinDev Studio dengan 6 End-Phase Quality Boundaries."""
    workflow = StateGraph(SquadState)

    # 1. Daftarkan seluruh Node Produser dan End-Phase Validator
    workflow.add_node("v0", v0_agent)
    workflow.add_node("v0_validator", v0_validator_node)

    workflow.add_node("pm", pm_agent)
    workflow.add_node("pm_validator", pm_validator_node)

    workflow.add_node("architect", architect_agent)
    workflow.add_node("architect_validator", architect_validator_node)

    workflow.add_node("developer", developer_agent)
    workflow.add_node("developer_validator", developer_validator_node)

    workflow.add_node("frozen_oracle", frozen_oracle_node)
    workflow.add_node("tester", tester_agent)
    workflow.add_node("test_suite_validator", test_suite_validator_node)

    workflow.add_node("executor", executor_node)
    workflow.add_node("executor_validator", executor_validator_node)

    workflow.add_node("reviewer", reviewer_agent)
    workflow.add_node("reviewer_validator", reviewer_validator_node)

    # 2. Rangkaikan Edges & Conditional Quality Boundaries

    # Boundary V0: START -> V0 -> V0 Validator
    workflow.add_edge(START, "v0")
    workflow.add_edge("v0", "v0_validator")
    workflow.add_conditional_edges(
        "v0_validator",
        route_after_v0_validator,
        {
            "pm": "pm",
            "v0": "v0",
            END: END
        }
    )

    # Boundary V1: PM -> PM Validator
    workflow.add_edge("pm", "pm_validator")
    workflow.add_conditional_edges(
        "pm_validator",
        route_after_pm_validator,
        {
            "architect": "architect",
            "pm": "pm",
            END: END
        }
    )

    # Boundary V2: Architect -> Architect Validator (Consolidated Gate)
    workflow.add_edge("architect", "architect_validator")
    workflow.add_conditional_edges(
        "architect_validator",
        route_after_architect_validator,
        {
            "developer": "developer",
            "architect": "architect",
            END: END
        }
    )

    # Boundary V3: Developer -> Developer Pre-Execution Validator
    workflow.add_edge("developer", "developer_validator")
    workflow.add_conditional_edges(
        "developer_validator",
        route_after_developer_validator,
        {
            "frozen_oracle": "frozen_oracle",
            "tester": "tester",
            "developer": "developer",
            END: END
        }
    )

    # Boundary V4: Test Suite -> Test Suite Validator
    workflow.add_edge("frozen_oracle", "test_suite_validator")
    workflow.add_edge("tester", "test_suite_validator")
    workflow.add_conditional_edges(
        "test_suite_validator",
        route_after_test_suite_validator,
        {
            "executor": "executor",
            "tester": "tester",
            END: END
        }
    )

    # Boundary V5: Sandbox Executor -> Behavioral Execution Validator
    workflow.add_edge("executor", "executor_validator")
    workflow.add_conditional_edges(
        "executor_validator",
        route_after_executor_validator,
        {
            "reviewer": "reviewer",
            "developer": "developer",
            "architect": "architect",
            END: END
        }
    )

    # Boundary V6: Reviewer -> Reviewer Phase-End Validator
    workflow.add_edge("reviewer", "reviewer_validator")
    workflow.add_conditional_edges(
        "reviewer_validator",
        route_after_reviewer_validator,
        {
            "reviewer": "reviewer",
            "developer": "developer",
            END: END
        }
    )

    return workflow.compile()


# Instance default otoritatif
squad_graph = build_squad_graph()
phase_validated_squad_graph = squad_graph
build_phase_validated_graph = build_squad_graph
