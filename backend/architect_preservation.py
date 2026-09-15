"""
Architect Repair Grounding & Preservation v1
Treatment #1.5 — ReinDev Studio (Iterasi 6)

Core Module for:
1. State Transition Repair Representation (No Blind Regeneration)
2. Immutable Acceptance Ledger ([IMMUTABLE ACCEPTANCE OBLIGATIONS])
3. Repair State Ledger ([CURRENT ARCHITECT STATE])
4. Scaffold Snapshots & Deterministic History
5. Preservation Evaluation & Critical Regression Detection
6. Delivery Validation (Pre-Invocation Guarantee)
"""

import hashlib
import json
import re
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple, Set


class RepairTransitionStatus(str, Enum):
    PRESERVED = "PRESERVED"
    REPAIRED = "REPAIRED"
    CRITICAL_REGRESSION = "CRITICAL_REGRESSION"
    RESOLVED = "RESOLVED"
    UNRESOLVED = "UNRESOLVED"
    NEW_COMPATIBLE = "NEW_COMPATIBLE"
    NEW_INCOMPATIBLE = "NEW_INCOMPATIBLE"
    NEW_UNDETERMINED = "NEW_UNDETERMINED"


@dataclass
class RepairStateItem:
    """
    Represents an individual obligation or scenario within the repair state ledger.
    Certain fields are marked IMMUTABLE and cannot be altered across repair cycles.
    """
    obligation_id: str
    scenario_id: str
    authority: str = "FROZEN_ORACLE"
    source_reference: str = ""
    public_identity: str = ""
    stimulus: str = ""
    preconditions: Dict[str, Any] = field(default_factory=dict)
    expected_outcome: Dict[str, Any] = field(default_factory=dict)
    expected_observable_behavior: str = ""
    acceptance_evidence: str = ""
    previous_status: str = "NONE"      # COMPATIBLE, INCOMPATIBLE, UNDETERMINED, NONE
    current_status: str = "UNDETERMINED"  # COMPATIBLE, INCOMPATIBLE, UNDETERMINED
    transition_status: str = "UNRESOLVED"  # RepairTransitionStatus value
    repair_target: bool = False
    preserved: bool = False
    observed_change: str = ""

    def __setattr__(self, name: str, value: Any) -> None:
        # Enforce immutability for core acceptance authority fields once set
        immutable_fields = {
            "obligation_id", "scenario_id", "authority", "source_reference",
            "public_identity", "stimulus", "preconditions", "expected_outcome",
            "expected_observable_behavior", "acceptance_evidence"
        }
        if hasattr(self, name) and name in immutable_fields and getattr(self, name) not in (None, "", {}):
            curr = getattr(self, name)
            if curr != value:
                raise ValueError(
                    f"IMMUTABLE ACCEPTANCE OBLIGATION VIOLATION: Field '{name}' is read-only and immutable. "
                    f"Attempted to mutate from '{curr}' to '{value}'."
                )
        super().__setattr__(name, value)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RepairStateItem":
        d = dict(data)
        return cls(**d)


@dataclass
class RepairStateLedger:
    """
    Deterministic ledger tracking the complete state transition across Architect attempts.
    Maintains:
    - [IMMUTABLE ACCEPTANCE OBLIGATIONS]
    - [CURRENT ARCHITECT STATE]
    - [REPAIR TARGETS]
    - [REGRESSION EVIDENCE]
    """
    items: List[RepairStateItem] = field(default_factory=list)

    @property
    def regression_count(self) -> int:
        return sum(
            1 for it in self.items
            if it.transition_status == RepairTransitionStatus.CRITICAL_REGRESSION.value
            or it.current_status == "REGRESSION"
        )

    @property
    def repaired_count(self) -> int:
        return sum(
            1 for it in self.items
            if it.transition_status in (
                RepairTransitionStatus.REPAIRED.value,
                RepairTransitionStatus.RESOLVED.value
            )
        )

    @property
    def preserved_count(self) -> int:
        return sum(1 for it in self.items if it.preserved)

    @property
    def target_count(self) -> int:
        return sum(1 for it in self.items if it.repair_target)

    @property
    def has_regression(self) -> bool:
        return self.regression_count > 0

    @property
    def is_fully_compatible(self) -> bool:
        return (
            len(self.items) > 0 and
            not self.has_regression and
            all(it.current_status == "COMPATIBLE" for it in self.items)
        )

    def get_item(self, scenario_id: str) -> Optional[RepairStateItem]:
        for it in self.items:
            if it.scenario_id == scenario_id or it.obligation_id == scenario_id:
                return it
        return None

    def to_immutable_ledger_text(self) -> str:
        """Section [2] IMMUTABLE ACCEPTANCE OBLIGATIONS (Read-only ledger)."""
        lines = [
            "[IMMUTABLE ACCEPTANCE OBLIGATIONS] (READ-ONLY — MUTATION FORBIDDEN)",
            "Authority: FROZEN_ORACLE (Absolute Acceptance Authority)",
            "===================================================================="
        ]
        for idx, it in enumerate(self.items, 1):
            lines.append(f"{idx}. OBLIGATION_ID: {it.obligation_id} | SCENARIO_ID: {it.scenario_id}")
            lines.append(f"   Authority: {it.authority}")
            lines.append(f"   Source Reference: {it.source_reference}")
            lines.append(f"   Public Identity: {it.public_identity}")
            lines.append(f"   Stimulus: {it.stimulus}")
            if it.preconditions:
                lines.append(f"   Preconditions: {json.dumps(it.preconditions, sort_keys=True)}")
            lines.append(f"   Expected Outcome: {json.dumps(it.expected_outcome, sort_keys=True)}")
            if it.expected_observable_behavior:
                lines.append(f"   Expected Observable Behavior: {it.expected_observable_behavior}")
            if it.acceptance_evidence:
                lines.append(f"   Acceptance Evidence: {it.acceptance_evidence}")
            lines.append(f"   Current Compatibility: {it.current_status}")
            lines.append("")
        return "\n".join(lines).strip()

    def to_repair_state_text(self) -> str:
        """Section [4] CURRENT ARCHITECT STATE / REPAIR STATE LEDGER."""
        lines = [
            "[CURRENT ARCHITECT STATE] (Deterministic State Transition)",
            "=========================================================="
        ]
        for idx, it in enumerate(self.items, 1):
            status_flag = f"[{it.transition_status}]"
            pres_flag = "PRESERVED=TRUE" if it.preserved else "PRESERVED=FALSE"
            lines.append(
                f"  {idx}. {status_flag} {it.scenario_id} "
                f"({it.previous_status} -> {it.current_status}) | {pres_flag}"
            )
            if it.observed_change:
                lines.append(f"     Delta: {it.observed_change}")
        return "\n".join(lines).strip()

    def to_repair_targets_text(self) -> str:
        """
        Section [6] EXPLICIT REPAIR TARGETS
        Explicit target scenario, current status, evidence, required transition.
        Lists PRESERVE items for currently compatible scenarios.
        NO 'HOW' prescribed!
        """
        targets = [it for it in self.items if it.repair_target or it.current_status != "COMPATIBLE"]
        preserved = [it for it in self.items if it.current_status == "COMPATIBLE"]

        lines = [
            "[REPAIR TARGETS]",
            "================="
        ]
        if not targets:
            lines.append("No active repair targets. All scenarios currently COMPATIBLE.")
        else:
            lines.append("ACTIVE TARGETS (WHAT must be repaired — NO implementation strategy prescribed):")
            for t in targets:
                req_trans = f"{t.current_status} -> COMPATIBLE"
                lines.append(f"  TARGET: {t.scenario_id}")
                lines.append(f"    CURRENT: {t.current_status}")
                lines.append(f"    EVIDENCE: {t.observed_change or t.acceptance_evidence or 'Incompatible with scenario requirements'}")
                lines.append(f"    REQUIRED TRANSITION: {req_trans}")
                lines.append("")

        if preserved:
            lines.append("PRESERVE (MUST REMAIN COMPATIBLE — DO NOT BREAK):")
            for p in preserved:
                lines.append(f"  - {p.scenario_id} = COMPATIBLE")

        return "\n".join(lines).strip()

    def to_regression_evidence_text(self) -> str:
        """Generates detailed [REGRESSION EVIDENCE] if any critical regression occurred."""
        reg_items = [
            it for it in self.items
            if it.transition_status == RepairTransitionStatus.CRITICAL_REGRESSION.value
            or it.current_status == "REGRESSION"
        ]
        if not reg_items:
            return ""

        lines = [
            "[REGRESSION EVIDENCE — REPAIR REJECTED]",
            "=======================================",
            "CRITICAL REGRESSION DETECTED: The repair attempt broke previously COMPATIBLE acceptance obligations.",
            "Contract freeze is strictly forbidden until all regressions are eliminated.",
            ""
        ]
        for it in reg_items:
            lines.append(f"  - SCENARIO_ID: {it.scenario_id}")
            lines.append(f"    Previous Status: {it.previous_status}")
            lines.append(f"    Current Status: {it.current_status}")
            lines.append(f"    Source Reference: {it.source_reference}")
            lines.append(f"    Observed Change: {it.observed_change}")
            lines.append("")
        return "\n".join(lines).strip()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "items": [it.to_dict() for it in self.items],
            "regression_count": self.regression_count,
            "repaired_count": self.repaired_count,
            "preserved_count": self.preserved_count,
            "target_count": self.target_count,
            "has_regression": self.has_regression,
            "is_fully_compatible": self.is_fully_compatible
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RepairStateLedger":
        items = [RepairStateItem.from_dict(it) for it in data.get("items", [])]
        return cls(items=items)


@dataclass
class ArchitectScaffoldSnapshot:
    """
    Deterministic snapshot captured per Architect attempt.
    Used for preservation tracking, regression detection, and forensic audit.
    """
    scaffold_hash: str
    files: Dict[str, str] = field(default_factory=dict)
    compatibility_matrix: Dict[str, Any] = field(default_factory=dict)
    obligation_coverage: Dict[str, Any] = field(default_factory=dict)
    scenario_coverage: Dict[str, Any] = field(default_factory=dict)
    regression_count: int = 0
    contract_status: str = "DRAFT"
    public_callables: List[str] = field(default_factory=list)
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ArchitectScaffoldSnapshot":
        return cls(**dict(data))


def hash_scaffold_files(scaffold_files: Dict[str, str]) -> str:
    """Computes deterministic SHA-256 hash across normalized scaffold files."""
    hasher = hashlib.sha256()
    for fp in sorted(scaffold_files.keys()):
        hasher.update(fp.encode("utf-8"))
        hasher.update(b"\x00")
        content = scaffold_files[fp] or ""
        normalized = "\n".join(line.rstrip() for line in content.splitlines()).strip()
        hasher.update(normalized.encode("utf-8"))
        hasher.update(b"\x00")
    return hasher.hexdigest()


def extract_scaffold_public_callables(scaffold_files: Dict[str, str]) -> List[str]:
    """Extracts public classes, functions, and endpoints from scaffold files generically."""
    callables = set()
    for fp, code in scaffold_files.items():
        if not code:
            continue
        # Python / Dart class
        for m in re.finditer(r"\bclass\s+([A-Za-z_][A-Za-z0-9_]*)", code):
            callables.add(m.group(1))
        # Python / Dart function
        for m in re.finditer(r"\bdef\s+([A-Za-z_][A-Za-z0-9_]*)", code):
            if not m.group(1).startswith("_"):
                callables.add(m.group(1))
        for m in re.finditer(r"\b(?:void|Future|Widget|String|int|double|bool|[A-Z]\w*)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", code):
            name = m.group(1)
            if not name.startswith("_") and name not in ("if", "for", "while", "switch", "catch"):
                callables.add(name)
        # HTTP routes
        for m in re.finditer(r"""@\w+\.(?:get|post|put|delete|patch)\s*\(\s*["']([^"']+)["']""", code, re.IGNORECASE):
            callables.add(m.group(1))
    return sorted(list(callables))


def generate_scaffold_snapshot(
    scaffold_files: Dict[str, str],
    compatibility_matrix: Optional[Any] = None,
    obligation_coverage: Optional[Dict[str, Any]] = None,
    contract_status: str = "DRAFT",
    timestamp: str = ""
) -> ArchitectScaffoldSnapshot:
    """
    Generates a deterministic ArchitectScaffoldSnapshot from scaffold files and matrix.
    """
    sc_hash = hash_scaffold_files(scaffold_files)
    public_calls = extract_scaffold_public_callables(scaffold_files)

    matrix_dict = {}
    regression_cnt = 0
    scenario_cov = {}

    if compatibility_matrix is not None:
        if hasattr(compatibility_matrix, "to_dict"):
            matrix_dict = compatibility_matrix.to_dict()
        elif isinstance(compatibility_matrix, dict):
            matrix_dict = compatibility_matrix

        if hasattr(compatibility_matrix, "regression_count"):
            regression_cnt = compatibility_matrix.regression_count
        elif isinstance(matrix_dict, dict):
            regression_cnt = matrix_dict.get("regression_count", 0)

        # Scenario coverage summary
        items = matrix_dict.get("items", [])
        for it in items:
            s_id = it.get("scenario_id") if isinstance(it, dict) else getattr(it, "scenario_id", "")
            compat = it.get("compatibility") if isinstance(it, dict) else getattr(it, "compatibility", "")
            if s_id:
                scenario_cov[s_id] = compat

    return ArchitectScaffoldSnapshot(
        scaffold_hash=sc_hash,
        files=dict(scaffold_files),
        compatibility_matrix=matrix_dict,
        obligation_coverage=dict(obligation_coverage or {}),
        scenario_coverage=scenario_cov,
        regression_count=regression_cnt,
        contract_status=contract_status,
        public_callables=public_calls,
        timestamp=timestamp
    )


def compare_scaffold_snapshots(
    prev_snapshot: Optional[ArchitectScaffoldSnapshot],
    curr_snapshot: ArchitectScaffoldSnapshot
) -> Dict[str, Any]:
    """
    Compares two deterministic snapshots and detects:
    - Dropped files/modules
    - Dropped public callables
    - Scenario regressions
    - Hash equality
    """
    if prev_snapshot is None:
        return {
            "is_initial": True,
            "has_dropped_files": False,
            "has_dropped_callables": False,
            "dropped_files": [],
            "dropped_callables": [],
            "scenario_regressions": [],
            "hash_changed": True
        }

    dropped_files = sorted(list(set(prev_snapshot.files.keys()) - set(curr_snapshot.files.keys())))
    dropped_callables = sorted(list(set(prev_snapshot.public_callables) - set(curr_snapshot.public_callables)))

    scenario_regressions = []
    prev_cov = prev_snapshot.scenario_coverage or {}
    curr_cov = curr_snapshot.scenario_coverage or {}

    for sc_id, prev_compat in prev_cov.items():
        curr_compat = curr_cov.get(sc_id, "MISSING")
        if prev_compat == "COMPATIBLE" and curr_compat != "COMPATIBLE":
            scenario_regressions.append({
                "scenario_id": sc_id,
                "previous_status": prev_compat,
                "current_status": curr_compat
            })

    return {
        "is_initial": False,
        "has_dropped_files": len(dropped_files) > 0,
        "has_dropped_callables": len(dropped_callables) > 0,
        "dropped_files": dropped_files,
        "dropped_callables": dropped_callables,
        "scenario_regressions": scenario_regressions,
        "hash_changed": prev_snapshot.scaffold_hash != curr_snapshot.scaffold_hash
    }


def evaluate_preservation_and_regression(
    previous_snapshot: Optional[ArchitectScaffoldSnapshot],
    current_matrix: Any,
    canonical_scenarios: List[Any],
    obligations: Optional[List[Any]] = None,
    scaffold_files: Optional[Dict[str, str]] = None
) -> RepairStateLedger:
    """
    Evaluates preservation and regressions across Architect attempts:
    - Builds state ledger for each canonical scenario / obligation.
    - Flags COMPATIBLE -> COMPATIBLE as PRESERVED.
    - Flags INCOMPATIBLE -> COMPATIBLE as REPAIRED.
    - Flags COMPATIBLE -> INCOMPATIBLE as CRITICAL_REGRESSION.
    - Flags UNDETERMINED -> COMPATIBLE as RESOLVED.
    - Flags dropped previously-compatible callables/files as CRITICAL_REGRESSION (No Blind Regeneration).
    """
    prev_cov: Dict[str, str] = {}
    prev_callables: Set[str] = set()
    prev_files: Set[str] = set()

    if previous_snapshot is not None:
        prev_cov = dict(previous_snapshot.scenario_coverage or {})
        prev_callables = set(previous_snapshot.public_callables or [])
        prev_files = set(previous_snapshot.files.keys() or [])

    curr_cov: Dict[str, Any] = {}
    if current_matrix is not None:
        items = getattr(current_matrix, "items", [])
        if not items and isinstance(current_matrix, dict):
            items = current_matrix.get("items", [])
        for it in items:
            s_id = getattr(it, "scenario_id", None) or (it.get("scenario_id") if isinstance(it, dict) else "")
            if s_id:
                curr_cov[s_id] = it

    ledger_items: List[RepairStateItem] = []

    # Map scenarios
    for sc in canonical_scenarios:
        sc_id = getattr(sc, "scenario_id", "")
        stimulus = getattr(sc, "stimulus", "")
        src_ref = getattr(sc, "source_reference", "")
        caller = getattr(sc, "caller", "")
        precond = getattr(sc, "preconditions", {})
        exp_out = getattr(sc, "expected_outcome", {})
        exp_obs = getattr(sc, "observable_output", "")

        prev_st = prev_cov.get(sc_id, "NONE")
        matrix_it = curr_cov.get(sc_id)

        curr_st = "UNDETERMINED"
        evidence_text = ""
        if matrix_it is not None:
            curr_st = getattr(matrix_it, "compatibility", None) or (
                matrix_it.get("compatibility") if isinstance(matrix_it, dict) else "UNDETERMINED"
            )
            evidence_text = getattr(matrix_it, "evidence", "") or (
                matrix_it.get("evidence", "") if isinstance(matrix_it, dict) else ""
            )

        # Check Blind Regeneration (dropped public callable or file required by this scenario)
        dropped_evidence = ""
        if scaffold_files and previous_snapshot:
            curr_calls = set(extract_scaffold_public_callables(scaffold_files))
            for pc in prev_callables:
                if pc in stimulus or pc in caller:
                    if pc not in curr_calls:
                        dropped_evidence = f"Previously compatible public callable '{pc}' was dropped from scaffold."
                        break

            curr_file_set = set(scaffold_files.keys())
            for pf in prev_files:
                if pf not in curr_file_set:
                    dropped_evidence = f"Previously present module/file '{pf}' was dropped from scaffold."
                    break

        if dropped_evidence and prev_st == "COMPATIBLE":
            curr_st = "INCOMPATIBLE"
            evidence_text = f"[NO BLIND REGENERATION VIOLATION] {dropped_evidence} " + evidence_text

        # Determine transition status
        is_target = (prev_st in ("INCOMPATIBLE", "UNDETERMINED"))
        preserved = False
        obs_change = ""

        if prev_st == "COMPATIBLE" and curr_st == "COMPATIBLE":
            trans_status = RepairTransitionStatus.PRESERVED.value
            preserved = True
            obs_change = "State preserved. Interface and behavior remain fully compatible."
        elif prev_st in ("INCOMPATIBLE", "NONE") and curr_st == "COMPATIBLE":
            trans_status = RepairTransitionStatus.REPAIRED.value
            obs_change = f"Repaired from {prev_st} to COMPATIBLE."
        elif prev_st == "UNDETERMINED" and curr_st == "COMPATIBLE":
            trans_status = RepairTransitionStatus.RESOLVED.value
            obs_change = "Undetermined state resolved to COMPATIBLE."
        elif prev_st == "COMPATIBLE" and curr_st in ("INCOMPATIBLE", "UNDETERMINED"):
            trans_status = RepairTransitionStatus.CRITICAL_REGRESSION.value
            obs_change = f"CRITICAL REGRESSION: Previously COMPATIBLE scenario is now {curr_st}. {evidence_text}"
        elif prev_st == "UNDETERMINED" and curr_st == "UNDETERMINED":
            trans_status = RepairTransitionStatus.UNRESOLVED.value
            obs_change = "Unresolved: Insufficient static evidence remains."
        elif curr_st == "INCOMPATIBLE":
            trans_status = RepairTransitionStatus.NEW_INCOMPATIBLE.value if prev_st == "NONE" else "UNRESOLVED"
            obs_change = f"Incompatible: {evidence_text}"
        else:
            trans_status = RepairTransitionStatus.UNRESOLVED.value
            obs_change = f"Transition from {prev_st} to {curr_st}."

        item = RepairStateItem(
            obligation_id=getattr(sc, "obligation_id", sc_id) or sc_id,
            scenario_id=sc_id,
            authority="FROZEN_ORACLE",
            source_reference=src_ref,
            public_identity=caller or sc_id,
            stimulus=stimulus,
            preconditions=dict(precond or {}),
            expected_outcome=dict(exp_out or {}),
            expected_observable_behavior=exp_obs,
            acceptance_evidence=evidence_text,
            previous_status=prev_st,
            current_status=curr_st,
            transition_status=trans_status,
            repair_target=is_target,
            preserved=preserved,
            observed_change=obs_change
        )
        ledger_items.append(item)

    return RepairStateLedger(items=ledger_items)


def validate_architect_repair_context_delivery(context_str: str) -> Tuple[bool, List[str]]:
    """
    Requirement 10: CONTEXT DELIVERY VALIDATION
    Deterministic pre-invocation check:
    Ensures critical sections are present before invoking the Architect:
    - Immutable acceptance obligations present
    - Current failures present (when failures exist)
    - Repair target present
    - Preserved state present
    - Expected transition present
    - Repair boundary present

    If any critical section is missing due to truncation:
    Returns (False, ["ARCHITECT_CONTEXT_DELIVERY_FAILURE: ..."])
    """
    errors: List[str] = []

    # 1. Immutable acceptance authority / obligations check
    has_authority = bool(
        re.search(r"\[1\]\s+IMMUTABLE ACCEPTANCE AUTHORITY", context_str) or
        re.search(r"\[IMMUTABLE ACCEPTANCE OBLIGATIONS\]", context_str) or
        re.search(r"\[2\]\s+ACCEPTANCE OBLIGATION LEDGER", context_str) or
        "AUTHORITATIVE ACCEPTANCE ORACLE INTERFACES" in context_str
    )
    if not has_authority:
        errors.append("ARCHITECT_CONTEXT_DELIVERY_FAILURE: Missing immutable acceptance authority or obligations ledger.")

    # 2. Current failures / violations check
    has_failures = bool(
        re.search(r"\[3\]\s+CURRENT COMPATIBILITY FAILURES", context_str) or
        re.search(r"\[9\]\s+EVIDENCE/VIOLATIONS", context_str) or
        re.search(r"\[REGRESSION EVIDENCE", context_str) or
        "Violations (" in context_str or
        "CURRENT COMPATIBILITY FAILURES" in context_str or
        "BEHAVIORAL COMPATIBILITY EVIDENCE" in context_str or
        "No active repair targets" in context_str
    )
    if not has_failures:
        errors.append("ARCHITECT_CONTEXT_DELIVERY_FAILURE: Missing current compatibility failures or deterministic evidence.")

    # 3. Locked / Proven / Preserved state check
    has_preserved = bool(
        re.search(r"\[4\]\s+LOCKED/PROVEN STATE", context_str) or
        re.search(r"\[CURRENT ARCHITECT STATE\]", context_str) or
        re.search(r"\[6\]\s+PROVEN INVARIANTS", context_str) or
        "PRESERVE (" in context_str or
        "PRESERVED=" in context_str
    )
    if not has_preserved:
        errors.append("ARCHITECT_CONTEXT_DELIVERY_FAILURE: Missing preserved state or locked proven invariants.")

    # 4. Repair target & expected transition check
    has_target = bool(
        re.search(r"\[6\]\s+REPAIR TARGET", context_str) or
        re.search(r"\[REPAIR TARGETS\]", context_str) or
        "REQUIRED TRANSITION:" in context_str or
        "No active repair targets" in context_str
    )
    if not has_target:
        errors.append("ARCHITECT_CONTEXT_DELIVERY_FAILURE: Missing explicit repair target or required transition.")

    # 5. Repair boundary check
    has_boundary = bool(
        re.search(r"\[7\]\s+REPAIR BOUNDARY", context_str) or
        re.search(r"\[10\]\s+REPAIR BOUNDARY", context_str) or
        "REPAIR BOUNDARY" in context_str
    )
    if not has_boundary:
        errors.append("ARCHITECT_CONTEXT_DELIVERY_FAILURE: Missing repair boundary (ALLOWED vs FORBIDDEN).")

    is_valid = (len(errors) == 0)
    return is_valid, errors
