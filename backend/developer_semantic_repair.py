# -*- coding: utf-8 -*-
"""
Universal Developer Semantic Repair Grounding v1
ReinDev Studio — Treatment #1.6

Provides a generic, cross-language, cross-domain, model-agnostic, and
deterministic semantic repair grounding layer for the Developer agent.

Foundational Principle (Arsitektur Otoritatif IA):
    Oracle    -> Menentukan EXPECTED (Acceptance Scenario & Obligation)
    Executor  -> Menentukan ACTUAL (Normalized Runtime Observation)
    Comparator-> Menentukan SEMANTIC DIFF (Deterministic Comparison)
    Developer -> Menentukan HOW TO REPAIR (Bebas memilih implementasi)

    DILARANG KERAS memberikan resep implementasi atau instruksi spesifik kepada Developer.
"""

from __future__ import annotations

import re
import ast
import json
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional, Tuple, Set


# ===========================================================================
# 1. Enums & Canonical State Constants
# ===========================================================================

class SemanticComparisonStatus(str, Enum):
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    UNDETERMINED = "UNDETERMINED"


class ObservableOutcomeType(str, Enum):
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    OUTPUT_PRODUCED = "OUTPUT_PRODUCED"
    EXCEPTION_RAISED = "EXCEPTION_RAISED"
    TIMEOUT = "TIMEOUT"
    UNDETERMINED = "UNDETERMINED"


# ===========================================================================
# 2. Canonical Developer Repair Evidence Data Structures
# ===========================================================================

@dataclass
class SemanticDiff:
    """
    Representasi perbedaan semantik antara ekspektasi dan observasi aktual.
    Koreksi IA #1: Menggunakan skema terbuka (open/extensible) dengan category dan details,
    tanpa ontologi tertutup yang kaku. State epistemik default adalah UNDETERMINED.
    """
    category: str = "UNDETERMINED"         # e.g., "ERROR_OUTCOME_UNOBSERVED", "UNEXPECTED_ERROR_OBSERVED", "PROPERTY_VALUE_MISMATCH", "UNDETERMINED"
    details: Dict[str, Any] = field(default_factory=dict)
    mismatched_properties: List[str] = field(default_factory=list)
    expected_properties: Dict[str, Any] = field(default_factory=dict)
    actual_properties: Dict[str, Any] = field(default_factory=dict)

    @property
    def classification(self) -> str:
        return self.category

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> SemanticDiff:
        return cls(**d)


@dataclass
class NormalizedObservation:
    """
    Observasi runtime yang telah dinormalisasi secara deterministik dari eksekusi.
    Koreksi IA #2: Hanya mencatat WHAT ACTUALLY HAPPENED (ACTUAL).
    TIDAK membaca atau menetapkan ekspektasi dari teks assertion runner.
    """
    observation_id: str
    target_symbol: str
    caller: str
    observable_outcome: str                # ObservableOutcomeType: SUCCESS | ERROR | EXCEPTION_RAISED | UNDETERMINED
    actual_properties: Dict[str, Any]      # {'observed_value': ..., 'exception_type': ..., 'observed_output': ...}
    raw_runtime_evidence: str              # Log/traceback asli
    source_location: str = ""
    exit_code: Optional[int] = None
    confidence: float = 1.0

    @property
    def semantic_properties(self) -> Dict[str, Any]:
        return self.actual_properties

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> NormalizedObservation:
        return cls(**d)


@dataclass
class DeveloperRepairEvidence:
    """
    Canonical Developer Repair Evidence Package (Treatment #1.6).
    Mewakili satu kegagalan semantik objektif lengkap tanpa bias sintaksis atau implementasi.
    """
    scenario_id: str
    obligation_id: str
    invariant_id: str

    stimulus: str
    precondition: str

    expected: Dict[str, Any]               # {'observable_outcome': str, 'semantic_properties': dict} (Sumber: Oracle)
    actual: Dict[str, Any]                 # {'observable_outcome': str, 'semantic_properties': dict, 'raw_runtime_evidence': str} (Sumber: Executor)

    semantic_diff: SemanticDiff

    violated_obligation: str
    preserved_invariants: List[str]

    repair_boundary: Dict[str, List[str]]  # {'allowed_changes': list, 'forbidden_changes': list}

    expected_post_repair_state: str
    verification_criteria: List[str]       # Kriteria berupa KONDISI (predikat), BUKAN instruksi perbaikan

    comparison_status: str = SemanticComparisonStatus.UNDETERMINED.value
    is_regression: bool = False
    caller_test: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if isinstance(self.semantic_diff, SemanticDiff):
            d["semantic_diff"] = self.semantic_diff.to_dict()
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> DeveloperRepairEvidence:
        data = dict(d)
        if isinstance(data.get("semantic_diff"), dict):
            data["semantic_diff"] = SemanticDiff.from_dict(data["semantic_diff"])
        return cls(**data)

    def to_prompt_block(self) -> str:
        """
        Format seksi failure semantik untuk diinjeksikan ke Developer repair context.
        Menyajikan FAKTA objektif tanpa membocorkan atau mendikte solusi implementasi.
        """
        lines = [
            f"• [SEMANTIC FAILURE: {self.scenario_id}]",
            f"  Caller Test: {self.caller_test or 'N/A'}",
            f"  Stimulus: {self.stimulus or 'N/A'}",
            f"  Precondition: {self.precondition or 'default'}",
            f"  Expected Outcome: {self.expected.get('observable_outcome', 'N/A')}",
            f"  Actual Observed Outcome: {self.actual.get('observable_outcome', 'N/A')}",
            f"  Semantic Mismatch Classification: {self.semantic_diff.category}",
        ]
        if self.semantic_diff.details:
            lines.append(f"  Mismatch Details: {self.semantic_diff.details}")
        if self.semantic_diff.mismatched_properties:
            lines.append(f"  Mismatched Properties: {', '.join(self.semantic_diff.mismatched_properties)}")
            for prop in self.semantic_diff.mismatched_properties:
                exp_v = self.semantic_diff.expected_properties.get(prop)
                act_v = self.semantic_diff.actual_properties.get(prop)
                lines.append(f"    - {prop}: expected '{exp_v}', but observed '{act_v}'")
        if self.violated_obligation:
            lines.append(f"  Violated Obligation: {self.violated_obligation}")
        if self.is_regression:
            lines.append("  ⚠️ CRITICAL REGRESSION: This behavior was previously PROVEN passing and has now regressed!")
        if self.expected_post_repair_state:
            lines.append(f"  Expected Post-Repair State: {self.expected_post_repair_state}")
        if self.verification_criteria:
            lines.append("  Verification Criteria:")
            for vc in self.verification_criteria:
                lines.append(f"    - {vc}")
        return "\n".join(lines)


# ===========================================================================
# 3. Generic Runtime Evidence Normalization
# ===========================================================================

def normalize_runtime_evidence(
    raw_output: str,
    exit_code: Optional[int] = None,
    stderr: str = "",
    diagnostic_evidence: Optional[Dict[str, Any]] = None,
    target_language: str = "python"
) -> List[NormalizedObservation]:
    """
    Menormalisasi output eksekusi mentah menjadi daftar NormalizedObservation terstruktur.
    Koreksi IA #2: Hanya menjawab WHAT ACTUALLY HAPPENED (ACTUAL).
    DILARANG membaca teks assertion untuk menyimpulkan ekspektasi.
    """
    observations: List[NormalizedObservation] = []
    combined = f"{raw_output}\n{stderr}".strip()
    if not combined and exit_code is None and not diagnostic_evidence:
        return observations

    is_dart = any(k in target_language.lower() for k in ("dart", "flutter")) or ".dart" in combined
    obs_idx = 1

    # 1. Ekstraksi dari diagnostic_evidence terstruktur (jika tersedia)
    if diagnostic_evidence and isinstance(diagnostic_evidence, dict):
        failing_tests = diagnostic_evidence.get("failing_tests") or []
        for ft in failing_tests:
            if not isinstance(ft, dict):
                continue
            t_name = ft.get("test_name", f"test_{obs_idx}")
            msg = ft.get("message", "")
            raw_tb = ft.get("traceback_excerpt") or msg
            target_sym = ft.get("target_symbol") or t_name

            props, outcome = _extract_semantic_properties_from_message(msg, raw_tb, is_dart)
            obs = NormalizedObservation(
                observation_id=f"NORM-OBS-{obs_idx:03d}",
                target_symbol=target_sym,
                caller=t_name,
                observable_outcome=outcome,
                actual_properties=props,
                raw_runtime_evidence=msg[:1000],
                source_location=ft.get("location", ""),
                exit_code=exit_code,
                confidence=1.0
            )
            observations.append(obs)
            obs_idx += 1

    # 2. Parsing Fallback untuk Python (Pytest output pattern)
    if not observations and not is_dart and raw_output:
        py_fails = re.findall(
            r"FAILED\s+([^\s:]+)::([^\s]+)\s*-\s*([^\n\r]+)",
            raw_output
        )
        for f_path, t_name, msg in py_fails:
            props, outcome = _extract_semantic_properties_from_message(msg, msg, is_dart=False)
            obs = NormalizedObservation(
                observation_id=f"NORM-OBS-{obs_idx:03d}",
                target_symbol=t_name,
                caller=t_name,
                observable_outcome=outcome,
                actual_properties=props,
                raw_runtime_evidence=msg.strip()[:1000],
                source_location=f"{f_path}::{t_name}",
                exit_code=exit_code,
                confidence=0.9
            )
            observations.append(obs)
            obs_idx += 1

    # 3. Parsing Fallback untuk Dart / Flutter (flutter test output pattern)
    if not observations and is_dart and raw_output:
        dart_blocks = re.split(r"(?:FAIL|EXCEPTION|Error|Exception)[\s:]+", raw_output, flags=re.IGNORECASE)
        if len(dart_blocks) > 1:
            for block in dart_blocks[1:]:
                clean_blk = block.strip()
                if not clean_blk:
                    continue
                first_line = clean_blk.splitlines()[0]
                props, outcome = _extract_semantic_properties_from_message(first_line, clean_blk, is_dart=True)
                obs = NormalizedObservation(
                    observation_id=f"NORM-OBS-{obs_idx:03d}",
                    target_symbol=first_line[:40],
                    caller=first_line[:40],
                    observable_outcome=outcome,
                    actual_properties=props,
                    raw_runtime_evidence=clean_blk[:1000],
                    source_location="",
                    exit_code=exit_code,
                    confidence=0.85
                )
                observations.append(obs)
                obs_idx += 1

    return observations


def _extract_semantic_properties_from_message(
    msg: str,
    raw_trace: str,
    is_dart: bool
) -> Tuple[Dict[str, Any], str]:
    """
    Koreksi IA #2: Hanya mengekstrak fakta observasi aktual (WHAT ACTUALLY HAPPENED).
    DILARANG membaca teks assertion untuk menyimpulkan ekspektasi.
    """
    actual_props: Dict[str, Any] = {}
    outcome = ObservableOutcomeType.ERROR.value

    # Pola 1: assert <actual_expression> == <expected_expression>
    # Ekstrak HANYA nilai actual yang diobservasi pada runtime
    eq_match = re.search(r"assert\s+([^=!\s]+(?:\s+[^=!\s]+)*)\s*==\s*([^=\s]+.*)", msg)
    if eq_match:
        actual_val = eq_match.group(1).strip()
        actual_props["observed_value"] = actual_val
        actual_props["comparison_operator"] = "=="
        outcome = ObservableOutcomeType.SUCCESS.value if (actual_val.isdigit() and int(actual_val) < 400) or not actual_val.isdigit() else ObservableOutcomeType.ERROR.value

    # Pola 2: Actual value terpisah (Dart / general test runners)
    act_match = re.search(r"Actual:\s*([^\n\r]+)", raw_trace)
    if act_match:
        actual_val = act_match.group(1).strip()
        actual_props["observed_value"] = actual_val
        outcome = ObservableOutcomeType.SUCCESS.value if (actual_val.isdigit() and int(actual_val) < 400) or not actual_val.isdigit() else ObservableOutcomeType.ERROR.value

    # Pola 3: Exception / Error Type generic
    exc_match = re.search(r"([A-Za-z0-9_]+Error|[A-Za-z0-9_]+Exception):\s*([^\n\r]+)", raw_trace)
    if exc_match:
        actual_props["exception_type"] = exc_match.group(1)
        actual_props["exception_message"] = exc_match.group(2).strip()
        outcome = ObservableOutcomeType.EXCEPTION_RAISED.value

    if not actual_props:
        actual_props["raw_message"] = msg.strip()[:200]
        outcome = ObservableOutcomeType.UNDETERMINED.value

    return actual_props, outcome


# ===========================================================================
# 4. Deterministic Semantic Comparison Engine
# ===========================================================================

def compare_scenario_with_observation(
    scenario: Any,
    observation: Optional[NormalizedObservation],
    obligation_id: str = "",
    invariant_id: str = "",
    preserved_invariants: Optional[List[str]] = None,
    allowed_boundary: Optional[List[str]] = None,
    forbidden_boundary: Optional[List[str]] = None,
) -> DeveloperRepairEvidence:
    """
    Koreksi IA #2 & #3:
    - EXPECTED berasal murni dari Canonical Acceptance Scenario (Oracle Authority).
    - ACTUAL berasal murni dari NormalizedObservation (Executor Reality).
    - Comparator menentukan SEMANTIC DIFF (category & details terbuka).
    - Verification Criteria berupa KONDISI (predikat observasi), BUKAN instruksi perbaikan.
    """
    sc_id = getattr(scenario, "scenario_id", str(scenario))
    stimulus = getattr(scenario, "stimulus", "")
    precondition = getattr(scenario, "precondition", "default")
    caller = getattr(scenario, "caller", "")
    expected_outcome = getattr(scenario, "expected_outcome", None)
    observable_output = getattr(scenario, "observable_output", None)
    obligation_ref = getattr(scenario, "obligation_ref", obligation_id)
    is_negative = bool(getattr(scenario, "is_negative_test", False))

    # Sumber Otoritatif EXPECTED: Canonical Acceptance Scenario
    expected_props: Dict[str, Any] = {}
    if isinstance(expected_outcome, dict):
        expected_props.update(expected_outcome)
    elif expected_outcome is not None:
        expected_props["outcome_value"] = str(expected_outcome)
    elif observable_output:
        expected_props["observable_output"] = str(observable_output)

    expected_outcome_type = ObservableOutcomeType.ERROR.value if is_negative else ObservableOutcomeType.SUCCESS.value

    # Kasus 1: Observasi tidak ada atau tidak cukup
    if observation is None:
        diff = SemanticDiff(
            category="UNDETERMINED",
            details={"reason": "No execution observation matched for scenario", "scenario_id": sc_id},
            mismatched_properties=[],
            expected_properties=expected_props,
            actual_properties={}
        )
        verif_criteria = [
            f"observable_outcome == '{expected_outcome_type}'",
            f"observable_properties == {expected_props}" if expected_props else "observable_properties match acceptance expectations",
            f"caller test '{caller}' passes without errors"
        ]
        return DeveloperRepairEvidence(
            scenario_id=sc_id,
            obligation_id=obligation_ref,
            invariant_id=invariant_id,
            stimulus=stimulus,
            precondition=precondition,
            expected={"observable_outcome": expected_outcome_type, "semantic_properties": expected_props},
            actual={"observable_outcome": ObservableOutcomeType.UNDETERMINED.value, "semantic_properties": {}, "raw_runtime_evidence": ""},
            semantic_diff=diff,
            violated_obligation=obligation_ref,
            preserved_invariants=preserved_invariants or [],
            repair_boundary={
                "allowed_changes": allowed_boundary or ["Modify implementation code to satisfy acceptance scenario"],
                "forbidden_changes": forbidden_boundary or ["Do not modify Frozen Oracle tests", "Do not regress locked invariants"]
            },
            expected_post_repair_state=f"Satisfy acceptance scenario '{sc_id}' for stimulus '{stimulus}'",
            verification_criteria=verif_criteria,
            comparison_status=SemanticComparisonStatus.UNDETERMINED.value,
            caller_test=caller
        )

    # Kasus 2: Observasi ada, bandingkan EXPECTED (Oracle) vs ACTUAL (Executor)
    act_props = dict(observation.actual_properties)
    act_outcome = observation.observable_outcome
    raw_ev = observation.raw_runtime_evidence

    mismatched_keys: List[str] = []
    category = "UNDETERMINED"
    diff_details: Dict[str, Any] = {}

    # 1. Bandingkan Observable Outcome
    if is_negative and act_outcome == ObservableOutcomeType.SUCCESS.value:
        category = "ERROR_OUTCOME_UNOBSERVED"
        diff_details["reason"] = "Negative scenario expected error outcome, but operation returned success without error."
        mismatched_keys.append("observable_outcome")
    elif not is_negative and act_outcome in (ObservableOutcomeType.ERROR.value, ObservableOutcomeType.EXCEPTION_RAISED.value):
        category = "UNEXPECTED_ERROR_OBSERVED"
        diff_details["reason"] = "Positive scenario expected success, but execution failed with error or exception."
        mismatched_keys.append("observable_outcome")

    # 2. Bandingkan properti nilai
    exp_val = expected_props.get("status_code") or expected_props.get("outcome_value") or expected_props.get("expected_value")
    act_val = act_props.get("observed_value") or act_props.get("status_code")

    if exp_val is not None and act_val is not None:
        if str(exp_val).strip() != str(act_val).strip():
            if category == "UNDETERMINED":
                category = "PROPERTY_VALUE_MISMATCH"
            diff_details["value_mismatch"] = {"expected": str(exp_val), "actual": str(act_val)}
            mismatched_keys.append("value")

    # 3. Tentukan comparison_status secara deterministik
    if mismatched_keys or category not in ("UNDETERMINED", "MATCH"):
        comp_status = SemanticComparisonStatus.MISMATCH.value
    elif observation.exit_code == 0 and not observation.raw_runtime_evidence and not mismatched_keys:
        comp_status = SemanticComparisonStatus.MATCH.value
        category = "MATCH"
    else:
        comp_status = SemanticComparisonStatus.UNDETERMINED.value

    diff = SemanticDiff(
        category=category,
        details=diff_details,
        mismatched_properties=sorted(list(set(mismatched_keys))),
        expected_properties=expected_props,
        actual_properties=act_props
    )

    # Koreksi IA #3: Kriteria verifikasi harus berupa KONDISI/PREDIKAT (WHAT must become true), BUKAN instruksi perbaikan
    verif_criteria = [
        f"observable_outcome == '{expected_outcome_type}'",
        f"observed_properties match expected {expected_props}" if expected_props else "observed_properties match acceptance expectations",
        f"caller test '{caller}' passes with exit_code == 0"
    ]

    return DeveloperRepairEvidence(
        scenario_id=sc_id,
        obligation_id=obligation_ref,
        invariant_id=invariant_id,
        stimulus=stimulus,
        precondition=precondition,
        expected={"observable_outcome": expected_outcome_type, "semantic_properties": expected_props},
        actual={"observable_outcome": act_outcome, "semantic_properties": act_props, "raw_runtime_evidence": raw_ev},
        semantic_diff=diff,
        violated_obligation=f"Acceptance obligation '{obligation_ref}' breached on scenario '{sc_id}'",
        preserved_invariants=preserved_invariants or [],
        repair_boundary={
            "allowed_changes": allowed_boundary or ["Modify implementation code in authoritative target file to reach expected state"],
            "forbidden_changes": forbidden_boundary or ["Do not modify Frozen Oracle tests", "Do not mutate locked invariants"]
        },
        expected_post_repair_state=f"Deterministic observable state matches expected properties {expected_props}",
        verification_criteria=verif_criteria,
        comparison_status=comp_status,
        caller_test=caller
    )


# ===========================================================================
# 5. Preservation & Authoritative State Synchronization
# ===========================================================================

def sync_developer_semantic_evidence_with_state(
    state: Dict[str, Any],
    current_evidences: List[DeveloperRepairEvidence]
) -> Tuple[List[DeveloperRepairEvidence], List[Dict[str, Any]], List[str]]:
    """
    Koreksi IA #4: Mengonsumsi langsung state lifecycle otoritatif Treatment #1.5
    (locked_invariants, previous_passed_tests, active_validation_errors, historical_validation_evidence).
    TIDAK membuat state management atau lifecycle paralel.
    """
    locked_dict = state.get("locked_invariants") or {}
    prev_passed = state.get("previous_passed_tests") or []
    regression_warnings: List[str] = []

    proven_test_names: Set[str] = set()
    for pt in prev_passed:
        tname = pt.get("test_name") if isinstance(pt, dict) else str(pt)
        if tname:
            proven_test_names.add(tname)

    for l_id, l_data in locked_dict.items():
        if isinstance(l_data, dict) and l_data.get("status") in ("PROVEN", "LOCKED"):
            desc = l_data.get("description", "")
            target = l_data.get("target_symbol", "")
            if desc:
                proven_test_names.add(desc)
            if target:
                proven_test_names.add(target)

    # Deteksi regresi terhadap invariant yang telah berstatus PROVEN
    for ev in current_evidences:
        caller = ev.caller_test
        stim = ev.stimulus
        is_reg = False
        for p_name in proven_test_names:
            if p_name and (p_name in caller or caller in p_name or p_name in stim):
                is_reg = True
                break

        if is_reg and ev.comparison_status == SemanticComparisonStatus.MISMATCH.value:
            ev.is_regression = True
            warn = (
                f"[REGRESSION DETECTED]: Skenario '{ev.scenario_id}' ({caller}) "
                f"sebelumnya berstatus PROVEN namun mengalami regresi pada iterasi ini!"
            )
            regression_warnings.append(warn)

    active_invariants: List[Dict[str, Any]] = []
    for l_id, l_data in locked_dict.items():
        if isinstance(l_data, dict):
            active_invariants.append(l_data)
        else:
            active_invariants.append({"invariant_id": l_id, "description": str(l_data), "status": "PROVEN"})

    active_evidences: List[DeveloperRepairEvidence] = []
    for ev in current_evidences:
        if ev.comparison_status in (SemanticComparisonStatus.MISMATCH.value, SemanticComparisonStatus.UNDETERMINED.value):
            active_evidences.append(ev)

    return active_evidences, active_invariants, regression_warnings


# Backward compatibility aliases for existing imports
evaluate_developer_preservation = sync_developer_semantic_evidence_with_state
def update_developer_failure_ledger(state: Dict[str, Any], current_evidences: List[DeveloperRepairEvidence]):
    # Delegates directly to authoritative state lifecycle
    active, _, _ = sync_developer_semantic_evidence_with_state(state, current_evidences)
    return active, list(state.get("historical_validation_evidence") or [])


# ===========================================================================
# 6. 10-Tier Developer Repair Context Assembler
# ===========================================================================

def assemble_developer_semantic_repair_context(
    state: Dict[str, Any],
    active_evidences: List[DeveloperRepairEvidence],
    preserved_invariants: List[Dict[str, Any]],
    raw_diagnostics: str = "",
    max_chars: int = 7000
) -> Tuple[str, Dict[str, Any]]:
    """
    Merakit konteks perbaikan Developer dengan urutan 10-tier prioritas mandatori:
      [1] AUTHORITATIVE ACCEPTANCE EXPECTATION
      [2] CURRENT SEMANTIC FAILURE
      [3] VIOLATED OBLIGATION
      [4] LOCKED / PROVEN INVARIANTS
      [5] CURRENT IMPLEMENTATION STATE
      [6] REPAIR BOUNDARY
      [7] EXPECTED POST-REPAIR STATE
      [8] VERIFICATION CRITERIA
      [9] SUPPORTING DIAGNOSTIC EVIDENCE
      [10] RAW EVIDENCE
    """
    sections: Dict[str, str] = {}
    contract = state.get("contract") or {}
    auth_file = state.get("authoritative_file") or "main.py"
    if isinstance(contract, dict):
        ti = contract.get("task_intent", {})
        if isinstance(ti, dict) and ti.get("authoritative_target_file"):
            auth_file = ti["authoritative_target_file"]

    code_files = state.get("code_files") or {}
    current_code = code_files.get(auth_file, "")
    if not current_code and code_files:
        for _, c in code_files.items():
            current_code = c
            break

    # [1] AUTHORITATIVE ACCEPTANCE EXPECTATION
    interfaces: List[str] = []
    models: List[str] = []
    if isinstance(contract, dict):
        for ifc in contract.get("interface_contracts", []):
            if isinstance(ifc, dict) and ifc.get("identifier"):
                interfaces.append(ifc["identifier"])
        for dm in contract.get("data_models", []):
            if isinstance(dm, dict) and dm.get("model_name"):
                models.append(dm["model_name"])

    sec1_lines = [
        f"Status: {state.get('contract_status', 'FROZEN')} (Immutable Authority)",
        f"Authoritative Target File: {auth_file}",
    ]
    if interfaces:
        sec1_lines.append(f"Required Interfaces: {', '.join(interfaces)}")
    if models:
        sec1_lines.append(f"Required Models: {', '.join(models)}")
    sections["[1] AUTHORITATIVE ACCEPTANCE EXPECTATION"] = "\n".join(sec1_lines)

    # [2] CURRENT SEMANTIC FAILURE
    if active_evidences:
        sec2_blocks = [ev.to_prompt_block() for ev in active_evidences]
        sections["[2] CURRENT SEMANTIC FAILURE"] = "\n\n".join(sec2_blocks)
    else:
        sections["[2] CURRENT SEMANTIC FAILURE"] = "(No active semantic mismatch identified)"

    # [3] VIOLATED OBLIGATION
    violated_list = []
    for ev in active_evidences:
        if ev.violated_obligation:
            violated_list.append(f"• {ev.obligation_id}: {ev.violated_obligation}")
    sections["[3] VIOLATED OBLIGATION"] = "\n".join(violated_list) if violated_list else "(None)"

    # [4] LOCKED / PROVEN INVARIANTS
    inv_lines = []
    for inv in preserved_invariants:
        iid = inv.get("invariant_id", "?")
        desc = inv.get("description", "")
        status = inv.get("status", "PROVEN")
        inv_lines.append(f"• [{status}] {iid}: {desc} — MUTATION FORBIDDEN")
    prev_passed = state.get("previous_passed_tests") or []
    for pt in prev_passed:
        tname = pt.get("test_name", str(pt)) if isinstance(pt, dict) else str(pt)
        inv_lines.append(f"• [PROVEN] {tname} — DO NOT BREAK")
    sections["[4] LOCKED / PROVEN INVARIANTS"] = "\n".join(inv_lines) if inv_lines else "(None currently locked)"

    # [5] CURRENT IMPLEMENTATION STATE
    code_excerpt = current_code.strip()[:2000] if current_code else "(No implementation code provided)"
    if len(current_code.strip()) > 2000:
        code_excerpt += "\n...(remaining code omitted for brevity)"
    sections["[5] CURRENT IMPLEMENTATION STATE"] = f"Authoritative Target: '{auth_file}'\n{code_excerpt}"

    # [6] REPAIR BOUNDARY
    allowed = ["Modify implementation code in authoritative target file to reach expected observable state"]
    forbidden = ["Do NOT modify Frozen Oracle test files", "Do NOT alter external contract signatures", "Do NOT regress locked invariants"]
    if active_evidences:
        for ev in active_evidences:
            allowed.extend(ev.repair_boundary.get("allowed_changes", []))
            forbidden.extend(ev.repair_boundary.get("forbidden_changes", []))
    allowed = sorted(list(set(allowed)))[:5]
    forbidden = sorted(list(set(forbidden)))[:5]
    boundary_text = (
        "ALLOWED CHANGES:\n" + "\n".join(f"  + {a}" for a in allowed) +
        "\nFORBIDDEN CHANGES:\n" + "\n".join(f"  x {f}" for f in forbidden)
    )
    sections["[6] REPAIR BOUNDARY"] = boundary_text

    # [7] EXPECTED POST-REPAIR STATE
    exp_states = []
    for ev in active_evidences:
        if ev.expected_post_repair_state:
            exp_states.append(f"✓ {ev.expected_post_repair_state}")
    sections["[7] EXPECTED POST-REPAIR STATE"] = "\n".join(exp_states) if exp_states else "✓ All tests pass and all acceptance scenarios satisfied"

    # [8] VERIFICATION CRITERIA
    verif_criteria = []
    for ev in active_evidences:
        for vc in ev.verification_criteria:
            verif_criteria.append(f"• {vc}")
    verif_criteria = sorted(list(set(verif_criteria)))
    sections["[8] VERIFICATION CRITERIA"] = "\n".join(verif_criteria) if verif_criteria else "• All test executions complete with exit_code == 0"

    # [9] SUPPORTING DIAGNOSTIC EVIDENCE
    diag_lines = []
    if raw_diagnostics:
        for ln in raw_diagnostics.splitlines():
            s = ln.strip()
            if s and any(k in s.lower() for k in ("error", "failed", "exception", "assert", "traceback")):
                diag_lines.append(f"  {s}")
    sections["[9] SUPPORTING DIAGNOSTIC EVIDENCE"] = "\n".join(diag_lines[:20]) if diag_lines else "(No additional diagnostic notes)"

    # [10] RAW EVIDENCE
    sections["[10] RAW EVIDENCE"] = (raw_diagnostics[:1200] + ("..." if len(raw_diagnostics) > 1200 else "")) if raw_diagnostics else "(No raw output)"

    final_parts = []
    for title, content in sections.items():
        sep = "=" * len(title)
        final_parts.append(f"{title}\n{sep}\n{content}")

    assembled_text = "\n\n".join(final_parts)
    if len(assembled_text) > max_chars:
        assembled_text = assembled_text[:max_chars - 50] + "\n\n...(context compressed to fit token budget)"

    telemetry_metadata = {
        "section_count": len(sections),
        "active_failure_count": len(active_evidences),
        "locked_invariant_count": len(preserved_invariants),
        "assembled_chars": len(assembled_text),
        "delivery_valid": True,
        "delivery_errors": []
    }
    return assembled_text, telemetry_metadata
