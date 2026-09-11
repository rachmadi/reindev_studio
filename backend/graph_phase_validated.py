"""
Phase-End Validated StateGraph for ReinDev Studio
ReinDev Studio — Iterasi 6 (Phase-End Validation Experiment)

Menghubungkan agen dengan gerbang validasi deterministik berbasis bukti:
- B1: PM Phase-End Validator
- B2: Architect Phase-End Validator (Contract Gate P0-2.1 integration)
- B3: Developer Phase-End Validator (Pre-Execution Gate, consumes Developer loop)
- B4: Oracle Phase-End Validator (1-to-1 SHA-256 verification)
- B5: Executor Iteration Validator (Sandbox execution & regression detection)
- B6: Reviewer Phase-End Validator (Audit validation & causal rehabilitation routing)
"""

from langgraph.graph import StateGraph, START, END
from typing import Dict, Any, List, Optional

try:
    from .state import SquadState
    from .tracer import get_tracer
    from .agents.pm import pm_agent
    from .agents.architect import architect_agent
    from .agents.developer import developer_agent
    from .agents.tester import tester_agent
    from .agents.reviewer import reviewer_agent
    from .graph import (
        contract_validation_node,
        frozen_oracle_node,
        route_after_contract_gate,
        route_after_developer
    )
    from .executor import executor_node
    from .phase_validators import (
        validate_pm_phase,
        validate_architect_phase,
        validate_developer_phase,
        validate_oracle_phase,
        validate_executor_phase,
        validate_reviewer_phase
    )
    from .contextual_evidence import ContextualEvidencePackage, render_repair_directive
except (ImportError, ValueError):
    from state import SquadState
    from tracer import get_tracer
    from agents.pm import pm_agent
    from agents.architect import architect_agent
    from agents.developer import developer_agent
    from agents.tester import tester_agent
    from agents.reviewer import reviewer_agent
    from graph import (
        contract_validation_node,
        frozen_oracle_node,
        route_after_contract_gate,
        route_after_developer
    )
    from executor import executor_node
    from phase_validators import (
        validate_pm_phase,
        validate_architect_phase,
        validate_developer_phase,
        validate_oracle_phase,
        validate_executor_phase,
        validate_reviewer_phase
    )
    try:
        from contextual_evidence import ContextualEvidencePackage, render_repair_directive
    except ImportError:
        ContextualEvidencePackage = None
        render_repair_directive = lambda pkg, **kw: ""


class PhaseValidatedSquadState(SquadState, total=False):
    """
    Subclass SquadState khusus untuk StateGraph phase-validated.
    Mempertahankan field kontrak validator fase & metadata bukti tanpa memodifikasi state.py.
    """
    pm_validator_contract: Optional[Dict[str, Any]]
    architect_validator_contract: Optional[Dict[str, Any]]
    developer_validator_contract: Optional[Dict[str, Any]]
    oracle_validator_contract: Optional[Dict[str, Any]]
    executor_iteration_validator_contract: Optional[Dict[str, Any]]
    reviewer_validator_contract: Optional[Dict[str, Any]]
    review_verdict: Optional[str]
    expected_oracle_sha: Optional[str]
    previous_passed_tests: Optional[List[str]]
    latest_evidence_package: Optional[Dict[str, Any]]
    invariant_regression_history: Optional[Dict[str, Any]]


# ==============================================================================
# Phase Validator Nodes
# ==============================================================================

def pm_validator_node(state: PhaseValidatedSquadState) -> Dict[str, Any]:
    """B1: Mengevaluasi output PM spesifikasi sebelum diteruskan ke Architect."""
    contract = validate_pm_phase(state)
    tracer = get_tracer(state.get("run_id"))
    if tracer:
        tracer.log_event(
            stage="phase_end_validation",
            event_type="pm_validation",
            iteration=0,
            data=contract
        )
    return {
        "pm_validator_contract": contract,
        "logs": state.get("logs", []) + [f"[PM Phase Validator]: Verdict = {contract['verdict']} ({len(contract['violations'])} violations)"]
    }


def route_after_pm_validator(state: PhaseValidatedSquadState) -> str:
    """Routing B1: Jika PASS -> architect; jika FAIL -> END (PM budget = 0)."""
    contract = state.get("pm_validator_contract", {})
    if contract.get("verdict") == "PASS":
        return "architect"
    return END


def architect_validator_node(state: PhaseValidatedSquadState) -> Dict[str, Any]:
    """B2: Mengevaluasi blueprint dan status kontrak setelah Contract Gate."""
    contract = validate_architect_phase(state)
    tracer = get_tracer(state.get("run_id"))
    rev = state.get("contract_revision_count", 0)
    if tracer:
        tracer.log_event(
            stage="phase_end_validation",
            event_type="architect_validation",
            iteration=rev,
            data=contract
        )
    res: Dict[str, Any] = {
        "architect_validator_contract": contract,
        "logs": state.get("logs", []) + [f"[Architect Phase Validator]: Verdict = {contract['verdict']} (Contract Status = {state.get('contract_status')})"]
    }
    if contract.get("verdict") == "FAIL":
        res["contract_revision_count"] = rev + 1
        cep_dict = contract.get("contextual_evidence_package")
        if cep_dict:
            res["latest_evidence_package"] = cep_dict
            if ContextualEvidencePackage is not None and render_repair_directive is not None:
                pkg = ContextualEvidencePackage.from_dict(cep_dict)
                rendered = render_repair_directive(pkg)
                res["contract_feedback"] = rendered
                if tracer:
                    tracer.log_validation_failure(
                        validator="B2_ARCHITECT_PHASE_END",
                        verdict="FAIL",
                        violations_count=len(contract.get("violations", [])),
                        package_hash=pkg.compute_package_hash(),
                        iteration=rev
                    )
                    tracer.log_contextual_evidence_assembled(
                        package_id=pkg.package_id,
                        package_hash=pkg.compute_package_hash(),
                        causal_owner=pkg.causal_owner,
                        size_bytes=len(rendered),
                        iteration=rev
                    )
                    tracer.log_repair_directive_issued(
                        package_id=pkg.package_id,
                        target_agent="architect",
                        length_chars=len(rendered),
                        iteration=rev
                    )
    return res


def route_after_architect_validator(state: PhaseValidatedSquadState) -> str:
    """Routing B2: Evaluasi Contract Gate + Validator B2."""
    val_contract = state.get("architect_validator_contract", {})
    base_decision = route_after_contract_gate(state)
    
    # Jika base decision ke developer tapi validator B2 FAIL, paksakan revisi arsitek jika budget ada
    if base_decision == "developer" and val_contract.get("verdict") != "PASS":
        rev = state.get("contract_revision_count", 0)
        max_rev = state.get("max_contract_revisions", 5)
        if rev < max_rev:
            return "architect"
        return END
        
    return base_decision


def developer_validator_node(state: PhaseValidatedSquadState) -> Dict[str, Any]:
    """B3: Pre-Execution Gate. Mengonsumsi 1 loop Developer jika gagal."""
    contract = validate_developer_phase(state)
    iteration = state.get("iteration_count", 0)
    tracer = get_tracer(state.get("run_id"))
    
    if tracer:
        tracer.log_event(
            stage="phase_end_validation",
            event_type="developer_validation",
            iteration=iteration,
            data=contract
        )

    res: Dict[str, Any] = {
        "developer_validator_contract": contract,
        "logs": state.get("logs", []) + [f"[Developer Phase Validator (Loop {iteration})]: Verdict = {contract['verdict']} ({len(contract['violations'])} violations)"]
    }

    if contract.get("verdict") == "FAIL":
        # Konsumsi 1 loop Developer dari alokasi existing max_iterations = 10
        new_iter = iteration + 1
        cep_dict = contract.get("contextual_evidence_package")
        feedback = ""
        pkg = None
        if cep_dict and ContextualEvidencePackage is not None and render_repair_directive is not None:
            res["latest_evidence_package"] = cep_dict
            pkg = ContextualEvidencePackage.from_dict(cep_dict)
            feedback = render_repair_directive(pkg)
        else:
            violations_str = "\n".join(f"- [{v['severity']}] {v['criterion']}: {v['message']}" for v in contract.get("violations", []))
            feedback = (
                f"[PRE-EXECUTION VALIDATOR REJECTION (Loop {new_iter}/{state.get('max_iterations', 10)})]:\n"
                f"Kode produksi ditolak sebelum eksekusi sandbox karena melanggar invarian kontrak statis:\n"
                f"{violations_str}\n\n"
                "INSTRUKSI PERBAIKAN SEGERA:\n"
                "Perbaiki galat sintaksis/antarmuka di atas pada Target File Authoritative sebelum kode dapat diuji."
            )
        res["iteration_count"] = new_iter
        res["developer_feedback"] = feedback
        res["status"] = "developer_preflight_rejected"

        if tracer and pkg:
            tracer.log_validation_failure(
                validator="B3_DEVELOPER_PRE_EXECUTION",
                verdict="FAIL",
                violations_count=len(contract.get("violations", [])),
                package_hash=pkg.compute_package_hash(),
                iteration=iteration
            )
            tracer.log_contextual_evidence_assembled(
                package_id=pkg.package_id,
                package_hash=pkg.compute_package_hash(),
                causal_owner=pkg.causal_owner,
                size_bytes=len(feedback),
                iteration=iteration
            )
            tracer.log_repair_directive_issued(
                package_id=pkg.package_id,
                target_agent="developer",
                length_chars=len(feedback),
                iteration=iteration
            )

    return res


def route_after_developer_validator(state: PhaseValidatedSquadState) -> str:
    """Routing B3: Jika FAIL & iter < 10 -> developer; jika FAIL & iter >= 10 -> reviewer; jika PASS -> route_after_developer."""
    val_contract = state.get("developer_validator_contract", {})
    iteration = state.get("iteration_count", 0)
    max_iter = state.get("max_iterations", 10)

    if val_contract.get("verdict") == "FAIL":
        if iteration < max_iter:
            return "developer"
        return "reviewer"

    # Jika PASS, gunakan routing normal ke frozen_oracle (loop 0) atau executor (loop > 0)
    return route_after_developer(state)


def oracle_validator_node(state: PhaseValidatedSquadState) -> Dict[str, Any]:
    """B4: Memvalidasi integritas SHA-256 berkas Frozen Oracle yang baru dimuat."""
    expected_sha = state.get("expected_oracle_sha")
    contract = validate_oracle_phase(state, expected_sha=expected_sha)
    tracer = get_tracer(state.get("run_id"))
    if tracer:
        tracer.log_event(
            stage="phase_end_validation",
            event_type="oracle_validation",
            iteration=state.get("iteration_count", 0),
            data=contract
        )
    return {
        "oracle_validator_contract": contract,
        "logs": state.get("logs", []) + [f"[Oracle Phase Validator]: Verdict = {contract['verdict']} (Checksum Verified = {contract['verdict'] == 'PASS'})"]
    }


def route_after_oracle_validator(state: PhaseValidatedSquadState) -> str:
    """Routing B4: Jika PASS -> executor; jika FAIL -> END (Abort immediately)."""
    contract = state.get("oracle_validator_contract", {})
    if contract.get("verdict") == "PASS":
        return "executor"
    return END


def executor_iteration_validator_node(state: PhaseValidatedSquadState) -> Dict[str, Any]:
    """B5: Iteration Validator. Mengevaluasi bukti runtime sandbox dan regresi."""
    prev_tests = state.get("previous_passed_tests", [])
    contract = validate_executor_phase(state, previous_passed_tests=prev_tests)
    iteration = state.get("iteration_count", 0)
    tracer = get_tracer(state.get("run_id"))

    if tracer:
        tracer.log_event(
            stage="iteration_validation",
            event_type="executor_iteration_validation",
            iteration=iteration,
            data=contract
        )

    current_passed = contract.get("current_passed_tests") or state.get("test_results", {}).get("passed_test_names", [])

    # Update permanent invariant regression history
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

    # Cek pemulihan jika tes yang pernah regresi kini lulus kembali
    for t_passed in current_passed:
        clean_name = t_passed.split("::")[-1].strip()
        inv_id = f"INV-BEHAVIOR-{clean_name[:30].replace(' ', '_')}"
        if inv_id in history_map and history_map[inv_id].get("ever_regressed"):
            rh = history_map[inv_id].get("regression_history", [])
            if rh and "recovered_at_iteration" not in rh[-1]:
                rh[-1]["recovered_at_iteration"] = iteration
                rh[-1]["recovery_status"] = "PROVEN_AGAIN"

    res: Dict[str, Any] = {
        "executor_iteration_validator_contract": contract,
        "previous_passed_tests": current_passed,
        "invariant_regression_history": history_map,
        "logs": state.get("logs", []) + [f"[Executor Iteration Validator (Loop {iteration})]: Verdict = {contract['verdict']} ({len(contract['regressions'])} regressions)"]
    }

    if contract.get("verdict") == "FAIL":
        cep_dict = contract.get("contextual_evidence_package")
        if cep_dict:
            res["latest_evidence_package"] = cep_dict
            if ContextualEvidencePackage is not None and render_repair_directive is not None:
                pkg = ContextualEvidencePackage.from_dict(cep_dict)
                feedback = render_repair_directive(pkg)
                res["developer_feedback"] = feedback
                if tracer:
                    tracer.log_validation_failure(
                        validator="B5_EXECUTOR_ITERATION",
                        verdict="FAIL",
                        violations_count=len(contract.get("violations", [])),
                        package_hash=pkg.compute_package_hash(),
                        iteration=iteration
                    )
                    tracer.log_contextual_evidence_assembled(
                        package_id=pkg.package_id,
                        package_hash=pkg.compute_package_hash(),
                        causal_owner=pkg.causal_owner,
                        size_bytes=len(feedback),
                        iteration=iteration
                    )
                    tracer.log_repair_directive_issued(
                        package_id=pkg.package_id,
                        target_agent="developer",
                        length_chars=len(feedback),
                        iteration=iteration
                    )
                    if hasattr(tracer, "log_actionable_prescription"):
                        for rx in getattr(pkg, "actionable_prescriptions", []):
                            tracer.log_actionable_prescription(
                                package_id=pkg.package_id,
                                prescription_id=rx.prescription_id,
                                oracle_call_site=rx.oracle_call_site,
                                implementation_symbol=rx.implementation_symbol,
                                required_change=rx.required_change,
                                iteration=iteration,
                            )

    return res


def route_after_executor_validator(state: PhaseValidatedSquadState) -> str:
    """Routing B5: Jika PASS -> reviewer; jika FAIL & iter < 10 -> developer; jika FAIL & iter >= 10 -> reviewer."""
    contract = state.get("executor_iteration_validator_contract", {})
    iteration = state.get("iteration_count", 0)
    max_iter = state.get("max_iterations", 10)

    if contract.get("verdict") == "PASS":
        return "reviewer"
    if iteration < max_iter:
        return "developer"
    return "reviewer"


def reviewer_validator_node(state: PhaseValidatedSquadState) -> Dict[str, Any]:
    """B6: Memvalidasi keabsahan review_verdict terhadap bukti Layer 1."""
    notes = state.get("review_notes", "")
    # Ekstrak review_verdict dari status atau notes
    status = state.get("status", "").lower()
    if "completed" in status or "[approved]" in notes.lower():
        review_verdict = "APPROVED"
    elif "needs_revision" in status or "[needs_revision]" in notes.lower():
        review_verdict = "NEEDS_REVISION"
    else:
        review_verdict = "FAIL"

    contract = validate_reviewer_phase(state, review_verdict=review_verdict, review_notes=notes)
    iteration = state.get("iteration_count", 0)
    tracer = get_tracer(state.get("run_id"))

    if tracer:
        tracer.log_event(
            stage="phase_end_validation",
            event_type="reviewer_validation",
            iteration=iteration,
            data=contract
        )

    res: Dict[str, Any] = {
        "reviewer_validator_contract": contract,
        "review_verdict": review_verdict,
        "logs": state.get("logs", []) + [f"[Reviewer Phase Validator]: Verdict = {contract['verdict']} (Review Verdict = {review_verdict}, Owner = {contract['repair_owner']})"]
    }

    if contract.get("verdict") == "FAIL":
        cep_dict = contract.get("contextual_evidence_package")
        if cep_dict:
            res["latest_evidence_package"] = cep_dict
            if ContextualEvidencePackage is not None:
                pkg = ContextualEvidencePackage.from_dict(cep_dict)
                if tracer:
                    tracer.log_validation_failure(
                        validator="B6_REVIEWER_PHASE_END",
                        verdict="FAIL",
                        violations_count=len(contract.get("violations", [])),
                        package_hash=pkg.compute_package_hash(),
                        iteration=iteration
                    )

    return res


def route_after_reviewer_validator(state: PhaseValidatedSquadState) -> str:
    """
    Routing B6:
    - Jika Validator PASS & review_verdict == APPROVED -> END (Konvergensi).
    - Jika Validator PASS & review_verdict == NEEDS_REVISION pada kode & remaining_dev_budget > 0 -> developer.
    - Jika Validator FAIL (menuntut unfreeze kontrak, budget habis, atau false approval) -> END (Terminal FAIL).
    """
    val_contract = state.get("reviewer_validator_contract", {})
    if val_contract.get("verdict") != "PASS":
        return END

    rev_verdict = val_contract.get("evaluated_review_verdict")
    if rev_verdict == "APPROVED":
        return END

    if rev_verdict == "NEEDS_REVISION" and val_contract.get("repair_owner") == "DEVELOPER":
        remaining_budget = val_contract.get("remaining_budget", 0)
        if remaining_budget > 0:
            return "developer"
        return END

    return END


# ==============================================================================
# Graph Builder
# ==============================================================================

def build_phase_validated_graph():
    """Membangun StateGraph bervalidasi fase deterministik untuk eksperimen pilot."""
    workflow = StateGraph(PhaseValidatedSquadState)

    # 1. Daftarkan Nodes
    workflow.add_node("pm", pm_agent)
    workflow.add_node("pm_validator", pm_validator_node)
    
    workflow.add_node("architect", architect_agent)
    workflow.add_node("contract_gate", contract_validation_node)
    workflow.add_node("architect_validator", architect_validator_node)
    
    workflow.add_node("developer", developer_agent)
    workflow.add_node("developer_validator", developer_validator_node)
    
    workflow.add_node("frozen_oracle", frozen_oracle_node)
    workflow.add_node("oracle_validator", oracle_validator_node)
    
    workflow.add_node("executor", executor_node)
    workflow.add_node("executor_validator", executor_iteration_validator_node)
    
    workflow.add_node("reviewer", reviewer_agent)
    workflow.add_node("reviewer_validator", reviewer_validator_node)

    # 2. Rangkaikan Alur B1 (PM -> Architect)
    workflow.add_edge(START, "pm")
    workflow.add_edge("pm", "pm_validator")
    workflow.add_conditional_edges(
        "pm_validator",
        route_after_pm_validator,
        {
            "architect": "architect",
            END: END
        }
    )

    # 3. Rangkaikan Alur B2 (Architect -> Developer)
    workflow.add_edge("architect", "contract_gate")
    workflow.add_edge("contract_gate", "architect_validator")
    workflow.add_conditional_edges(
        "architect_validator",
        route_after_architect_validator,
        {
            "developer": "developer",
            "architect": "architect",
            END: END
        }
    )

    # 4. Rangkaikan Alur B3 (Developer -> Oracle/Executor)
    workflow.add_edge("developer", "developer_validator")
    workflow.add_conditional_edges(
        "developer_validator",
        route_after_developer_validator,
        {
            "developer": "developer",
            "frozen_oracle": "frozen_oracle",
            "executor": "executor",
            "reviewer": "reviewer",
            END: END
        }
    )

    # 5. Rangkaikan Alur B4 (Oracle -> Executor)
    workflow.add_edge("frozen_oracle", "oracle_validator")
    workflow.add_conditional_edges(
        "oracle_validator",
        route_after_oracle_validator,
        {
            "executor": "executor",
            END: END
        }
    )

    # 6. Rangkaikan Alur B5 (Executor -> Developer / Reviewer)
    workflow.add_edge("executor", "executor_validator")
    workflow.add_conditional_edges(
        "executor_validator",
        route_after_executor_validator,
        {
            "developer": "developer",
            "reviewer": "reviewer"
        }
    )

    # 7. Rangkaikan Alur B6 (Reviewer -> END / Developer)
    workflow.add_edge("reviewer", "reviewer_validator")
    workflow.add_conditional_edges(
        "reviewer_validator",
        route_after_reviewer_validator,
        {
            "developer": "developer",
            END: END
        }
    )

    return workflow.compile()


phase_validated_squad_graph = build_phase_validated_graph()
