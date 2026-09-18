"""
B2 Repair Context Delivery v2 (Treatment lineage: #1.8.9)

Deterministic delivery mechanism for Stage B-2 repair in the staged architecture pipeline.
Provides a compact, semantically complete Repair Decision Packet containing all
information required to perform targeted B2 semantic repair within a strict context budget,
preventing context bloat, duplicate diagnostics, and delivery failures.

Key Architectural Invariants:
1. 8 P0 semantic components strictly protected (never dropped).
2. Priority ordering: P0 > P1 > P2 > P3 > P4 (P4 shed first, P0 protected).
3. Deterministic causal deduplication of repetitive diagnostics.
4. Adaptive context budget resolution (default: 12000 chars).
5. Atomic payload protection (no partial truncation of critical sections).
6. Pre-invocation delivery validation (structured DELIVERY_FAILURE, zero model repair attempts consumed).
7. Invocation invariants (repair_owner, invoked_stage, delivery_valid, repair_attempt).
8. Pre/post repair state preservation snapshot and verification.
9. Structured telemetry logging.
"""

import copy
import hashlib
import json
import logging
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# ==============================================================================
# 1. P0 SEMANTIC COMPONENTS (Section 3)
# ==============================================================================

@dataclass
class AuthorityObligationItem:
    """A. Authority / Ground Truth: what MUST be satisfied."""
    obligation_id: str
    description: str
    category: str
    expected_relationship: str
    provenance: str = "ACCEPTANCE_ORACLE"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CurrentCausalFailureItem:
    """B. Current Failure (Causal): exact root cause, not outer wrapper."""
    causal_category: str
    affected_obligations: List[str]
    root_cause_diagnostic: str
    violating_symbol: str
    expected_interface: str
    observed_interface: str
    difference: str = ""
    relationship_type: str = "INTERFACE"
    sources: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ValidRelationalBinding:
    """C. Current Valid State: what is already correct and MUST NOT be broken."""
    binding_id: str
    source_identity: str
    target_identity: str
    relationship_type: str
    target_artifact: str
    is_preserved: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LockedProvenInvariant:
    """D. Locked / Proven Invariants: upstream sealed states and unaffected B2 state."""
    invariant_id: str
    category: str
    description: str
    seal_hash: str = ""
    status: str = "LOCKED"
    mutation: str = "FORBIDDEN"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RepairTargetItem:
    """E. Repair Target: atomic semantic decision allowed to change."""
    target_id: str
    target_symbol: str
    affected_obligations: List[str]
    what: str
    where: str
    observed: str
    expected: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RepairBoundaryEnvelope:
    """F. Repair Boundary: exact permitted modification scope."""
    allowed_modifications: List[str]
    forbidden_modifications: List[str]
    boundary_hash: str = ""
    preserved_upstream: List[str] = field(default_factory=lambda: ["Stage A topology", "Stage B-1 file tree"])
    preserved_relationships: List[str] = field(default_factory=lambda: ["All valid relational bindings"])

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExpectedPostRepairItem:
    """G. Expected Post-Repair State: precise structural / relational criteria."""
    item_id: str
    target_symbol: str
    expected_state: str
    verification_rule: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class VerificationCriterion:
    """H. Verification Criteria: how post-repair state will be evaluated."""
    criterion_id: str
    gate_name: str
    rule_description: str
    evaluator: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class B2RepairDecisionPacket:
    """
    Structured Repair Decision Packet containing all 8 P0 semantic components
    plus optional P1-P4 context layers.
    """
    authority_obligations: List[AuthorityObligationItem] = field(default_factory=list)
    current_causal_failures: List[CurrentCausalFailureItem] = field(default_factory=list)
    valid_relational_bindings: List[ValidRelationalBinding] = field(default_factory=list)
    locked_proven_invariants: List[LockedProvenInvariant] = field(default_factory=list)
    repair_targets: List[RepairTargetItem] = field(default_factory=list)
    repair_boundary: Optional[RepairBoundaryEnvelope] = None
    expected_post_repair_states: List[ExpectedPostRepairItem] = field(default_factory=list)
    verification_criteria: List[VerificationCriterion] = field(default_factory=list)
    preserved_elements: List[Dict[str, Any]] = field(default_factory=list)

    # Context layers
    p1_canonical_schema: Dict[str, Any] = field(default_factory=dict)
    p2_relational_blueprint: Dict[str, Any] = field(default_factory=dict)
    p3_supporting_diagnostics: List[str] = field(default_factory=list)
    p4_historical_context: List[str] = field(default_factory=list)

    # Metadata
    repair_attempt: int = 1
    total_allowed_repairs: int = 3
    causal_category: str = "B2_DECISION_ERROR"
    contract_hash: str = ""
    stage_a_seal: str = ""
    stage_b1_seal: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "authority_obligations": [x.to_dict() for x in self.authority_obligations],
            "current_causal_failures": [x.to_dict() for x in self.current_causal_failures],
            "valid_relational_bindings": [x.to_dict() for x in self.valid_relational_bindings],
            "locked_proven_invariants": [x.to_dict() for x in self.locked_proven_invariants],
            "repair_targets": [x.to_dict() for x in self.repair_targets],
            "repair_boundary": self.repair_boundary.to_dict() if self.repair_boundary else None,
            "expected_post_repair_states": [x.to_dict() for x in self.expected_post_repair_states],
            "verification_criteria": [x.to_dict() for x in self.verification_criteria],
            "preserved_elements": self.preserved_elements,
            "p1_canonical_schema": self.p1_canonical_schema,
            "p2_relational_blueprint": self.p2_relational_blueprint,
            "p3_supporting_diagnostics": self.p3_supporting_diagnostics,
            "p4_historical_context": self.p4_historical_context,
            "repair_attempt": self.repair_attempt,
            "total_allowed_repairs": self.total_allowed_repairs,
            "causal_category": self.causal_category,
            "contract_hash": self.contract_hash,
            "stage_a_seal": self.stage_a_seal,
            "stage_b1_seal": self.stage_b1_seal,
        }


@dataclass
class B2DeliveryResult:
    """Result of B2 repair context delivery assembly and validation."""
    prompt: str
    packet: B2RepairDecisionPacket
    delivery_valid: bool
    budget: int
    char_count: int
    validation_errors: List[str] = field(default_factory=list)
    telemetry: Dict[str, Any] = field(default_factory=dict)


@dataclass
class B2StatePreservationSnapshot:
    """Pre-repair snapshot to ensure Stage A and B-1 states are immutable across B2 repair."""
    stage_a_hash: str
    stage_b1_hash: str
    unaffected_b2_symbols_hash: str
    scaffold_tree_hash: str
    contract_hash: str


# ==============================================================================
# 2. BUDGET RESOLUTION (Section 7)
# ==============================================================================

def resolve_context_budget(state: Dict[str, Any], default: int = 12000) -> int:
    """
    Resolves the B2 repair context budget deterministically.
    State override > environment override > default.
    Default is 12,000 chars.
    """
    if not isinstance(state, dict):
        return default

    # Check state config
    cfg = state.get("b2_delivery_config") or {}
    if isinstance(cfg, dict) and "context_budget" in cfg:
        try:
            val = int(cfg["context_budget"])
            if val > 0:
                return val
        except (ValueError, TypeError):
            pass

    # Check state direct field
    if "b2_context_budget" in state:
        try:
            val = int(state["b2_context_budget"])
            if val > 0:
                return val
        except (ValueError, TypeError):
            pass

    return default


# ==============================================================================
# 3. EXTRACTION OF B2 REPAIR DECISION PACKET (Section 3 & 6)
# ==============================================================================

def _compute_hash(data: Any) -> str:
    """Deterministic MD5 hash of JSON-serializable data."""
    try:
        s = json.dumps(data, sort_keys=True)
    except Exception:
        s = str(data)
    return hashlib.md5(s.encode("utf-8")).hexdigest()[:12]


def _normalize_diagnostic_to_semantic_tuples(
    raw_error: str,
    default_source: str = "contract_gate",
) -> List[Dict[str, Any]]:
    """
    Deterministically normalizes diagnostic strings into semantic failure tuples.
    Extracts violating_symbol, relationship_type, expected, actual, difference, sources.
    Splits composite diagnostic blocks (e.g. separated by ';' or 'ORACLE_OBLIGATION:').
    """
    results: List[Dict[str, Any]] = []

    # 1. Split multi-block diagnostic text
    chunks: List[str] = []
    if "ORACLE_OBLIGATION:" in raw_error:
        parts = raw_error.split("ORACLE_OBLIGATION:")
        for p in parts:
            p_strip = p.strip()
            if p_strip:
                chunks.append("ORACLE_OBLIGATION:\n" + p_strip)
    elif "; STAGE_" in raw_error:
        chunks = [c.strip() for c in raw_error.split("; ") if c.strip()]
    elif "; " in raw_error and ("mismatch" in raw_error.lower() or "missing" in raw_error.lower()):
        chunks = [c.strip() for c in raw_error.split("; ") if c.strip()]
    else:
        chunks = [raw_error]

    for chunk in chunks:
        # Determine source
        source = default_source
        if "SCHEMA_VIOLATION" in chunk or "parse failure" in chunk or "STAGE_B2_" in chunk:
            source = "validator"
        elif "CONTRACT_VALIDATION_FAILED" in chunk or "Pilar" in chunk or "PRE_FREEZE" in chunk:
            source = "contract_gate"

        # Symbol extraction
        sym_match = (
            re.search(r"""Symbol ['"]([^'"]+)['"]""", chunk)
            or re.search(r"""symbol ['"]([^'"]+)['"]""", chunk)
            or re.search(r"""Widget/Model ['"]([^'"]+)['"]""", chunk)
            or re.search(r"""Data model / entity ['"]([^'"]+)['"]""", chunk)
            or re.search(r"""Binding for ['"]([^'"]+)['"]""", chunk)
            or re.search(r"""Validated element ['"]([^'"]+)['"]""", chunk)
            or re.search(r"""component/widget ['"]([^'"]+)['"]""", chunk)
            or re.search(r"""class ['"]([^'"]+)['"]""", chunk)
        )
        sym_name = sym_match.group(1) if sym_match else ""

        # Relationship type extraction
        rel_type = "INTERFACE"
        if any(k in chunk.lower() for k in ["constructor", "named argument", "positional argument", "arity", "call_shape", "callable"]):
            rel_type = "CALL_SHAPE"
        elif any(k in chunk.lower() for k in ["route", "endpoint", "path", "http"]):
            rel_type = "ROUTE_BINDING"
        elif any(k in chunk.lower() for k in ["target_artifact", "artifact_mismatch"]):
            rel_type = "ARTIFACT_BINDING"
        elif any(k in chunk.lower() for k in ["interface_contracts", "data_models", "missing_binding"]):
            rel_type = "INTERFACE_DECLARATION"

        # Arity / cardinality mismatch pattern
        arity_match = re.search(r"""accepts at most (\d+)[^,]*called with (\d+)""", chunk, re.IGNORECASE)
        named_arg_match = re.search(r"""missing named argument\(s\): (\[[^\]]+\])""", chunk)
        artifact_match = re.search(r"""references target_artifact ['"]([^'"]+)['"], which does not match validated B-1 artifact ['"]([^'"]+)['"]""", chunk)
        undeclared_match = re.search(r"""['"]([^'"]+)['"] is not declared in (interface_contracts|data_models)""", chunk)

        if arity_match:
            act_arity, exp_arity = arity_match.group(1), arity_match.group(2)
            exp_str = f"arity={exp_arity}"
            act_str = f"arity={act_arity}"
            diff_str = f"arity_mismatch: accepts {act_arity}, expected {exp_arity}"
            diag_summary = f"Symbol '{sym_name}' argument cardinality mismatch: expected {exp_arity}, accepts {act_arity}"
        elif named_arg_match:
            missing_args = named_arg_match.group(1)
            exp_str = f"named_args: {missing_args}"
            act_str = f"missing: {missing_args}"
            diff_str = f"missing named argument(s): {missing_args}"
            diag_summary = f"Symbol '{sym_name}' constructor missing named argument(s): {missing_args}"
        elif artifact_match:
            act_art, exp_art = artifact_match.group(1), artifact_match.group(2)
            exp_str = f"target_artifact: {exp_art}"
            act_str = f"target_artifact: {act_art}"
            diff_str = f"artifact_mismatch: {act_art} != {exp_art}"
            diag_summary = f"Binding for '{sym_name}' references '{act_art}', expected '{exp_art}'"
        elif undeclared_match:
            decl_target = undeclared_match.group(2)
            exp_str = f"declared in {decl_target}"
            act_str = "not declared"
            diff_str = f"undeclared_in_{decl_target}"
            diag_summary = f"Component '{sym_name}' is not declared in {decl_target}"
        else:
            diag_m = re.search(r"""DIAGNOSIS:[ \t]*([^\r\n]+)""", chunk)
            diag_line = diag_m.group(1).strip() if diag_m else chunk.strip().split("\n")[0][:120]
            exp_m = re.search(r"""expected[ \t]*([^\r\n,]+)""", chunk, re.IGNORECASE) or re.search(r"""Expected:[ \t]*([^\r\n]+)""", chunk)
            act_m = re.search(r"""observed[ \t]*([^\r\n,]+)""", chunk, re.IGNORECASE) or re.search(r"""Observed:[ \t]*([^\r\n]+)""", chunk)
            exp_str = exp_m.group(1).strip() if exp_m else "Compatible argument and interface shape demanded by Acceptance Oracle"
            act_str = act_m.group(1).strip() if act_m else diag_line
            diff_str = diag_line
            diag_summary = diag_line

        if not sym_name:
            sym_name = "contract_target"

        results.append({
            "violating_symbol": sym_name,
            "relationship_type": rel_type,
            "expected_interface": exp_str,
            "observed_interface": act_str,
            "difference": diff_str,
            "root_cause_diagnostic": diag_summary,
            "source": source,
        })

    return results


def extract_b2_repair_decision_packet(
    state: Dict[str, Any],
    repair_errors: Optional[List[str]] = None,
    repair_attempt: int = 1,
) -> B2RepairDecisionPacket:
    """
    Deterministically extracts all 8 P0 semantic components from pipeline state.
    """
    packet = B2RepairDecisionPacket(repair_attempt=repair_attempt)

    # 1. Authority Obligations (from canonical obligations / test contract)
    authority_items: List[AuthorityObligationItem] = []
    canonical_obligations = state.get("canonical_obligations") or []
    if isinstance(canonical_obligations, list):
        for idx, ob in enumerate(canonical_obligations):
            if isinstance(ob, dict):
                ob_id = ob.get("obligation_id") or f"OBL-{idx + 1:02d}"
                desc = ob.get("description") or ob.get("rule") or str(ob)
                cat = ob.get("category") or "INTERFACE"
                prov = ob.get("provenance") or "ACCEPTANCE_ORACLE"
                authority_items.append(
                    AuthorityObligationItem(
                        obligation_id=ob_id,
                        description=desc,
                        category=cat,
                        expected_relationship=ob.get("expected_relationship", "Public interface match"),
                        provenance=prov,
                    )
                )

    if not authority_items:
        # Fallback from oracle tests or requirements if no canonical obligations present
        test_content = state.get("test_file_content") or ""
        syms = state.get("oracle_symbols") or []
        for s_idx, sym in enumerate(syms):
            authority_items.append(
                AuthorityObligationItem(
                    obligation_id=f"OBL-SYM-{s_idx + 1:02d}",
                    description=f"Public interface for `{sym}` must conform to test criteria",
                    category="INTERFACE",
                    expected_relationship="Exact signature, method name, and parameter shape match",
                    provenance="ACCEPTANCE_ORACLE",
                )
            )

    if not authority_items:
        authority_items.append(
            AuthorityObligationItem(
                obligation_id="OBL-AUTH-01",
                description="Conform public callable interfaces and bindings to acceptance criteria",
                category="INTERFACE",
                expected_relationship="Authoritative acceptance binding",
                provenance="ACCEPTANCE_ORACLE",
            )
        )

    # 2. Current Failure (Deduplicated, Causal)
    current_failures: List[CurrentCausalFailureItem] = []
    raw_errors = list(repair_errors or [])
    state_errs = list(state.get("contract_validation_errors") or [])
    for se in state_errs:
        if se not in raw_errors:
            raw_errors.append(se)

    causal_category = state.get("failure_ownership") or "B2_DECISION_ERROR"
    seen_failure_map: Dict[Tuple[str, str], CurrentCausalFailureItem] = {}

    for err_idx, raw_err in enumerate(raw_errors):
        tuples = _normalize_diagnostic_to_semantic_tuples(raw_err)
        for t in tuples:
            sym_name = t["violating_symbol"] or f"binding_{err_idx + 1}"
            rel_type = t["relationship_type"]
            key = (sym_name, rel_type)
            if key in seen_failure_map:
                existing = seen_failure_map[key]
                if t["source"] not in existing.sources:
                    existing.sources.append(t["source"])
                # Prefer more specific diagnostic summary
                if "DIAGNOSIS:" in existing.root_cause_diagnostic and "DIAGNOSIS:" not in t["root_cause_diagnostic"]:
                    existing.root_cause_diagnostic = t["root_cause_diagnostic"]
                    existing.difference = t["difference"]
                    existing.expected_interface = t["expected_interface"]
                    existing.observed_interface = t["observed_interface"]
            else:
                item = CurrentCausalFailureItem(
                    causal_category=causal_category,
                    affected_obligations=[f"OBL-{sym_name}"],
                    root_cause_diagnostic=t["root_cause_diagnostic"],
                    violating_symbol=sym_name,
                    expected_interface=t["expected_interface"],
                    observed_interface=t["observed_interface"],
                    difference=t["difference"],
                    relationship_type=rel_type,
                    sources=[t["source"]],
                )
                seen_failure_map[key] = item
                current_failures.append(item)

    if not current_failures:
        if raw_errors:
            first_err = raw_errors[0]
            current_failures.append(
                CurrentCausalFailureItem(
                    causal_category=causal_category,
                    affected_obligations=["OBL-PRIMARY"],
                    root_cause_diagnostic=first_err[:120],
                    violating_symbol="contract_target",
                    expected_interface="Satisfy acceptance criteria",
                    observed_interface="Contract validation failure",
                    difference="contract_validation_failure",
                    relationship_type="INTERFACE",
                    sources=["contract_gate"],
                )
            )
        else:
            current_failures.append(
                CurrentCausalFailureItem(
                    causal_category="CLEAN_INITIAL_STATE",
                    affected_obligations=[],
                    root_cause_diagnostic="No active failures detected. Clean relational assembly.",
                    violating_symbol="NONE",
                    expected_interface="Satisfy canonical obligations",
                    observed_interface="Clean initial state",
                    difference="none",
                    relationship_type="NONE",
                    sources=["provenance"],
                )
            )

    # 3. Valid Relational Bindings (State already correct)
    valid_bindings: List[ValidRelationalBinding] = []
    b2_output = state.get("stage_b2_output") or {}
    rel_bindings = []
    if isinstance(b2_output, dict):
        rel_bindings = b2_output.get("relational_bindings") or b2_output.get("bindings") or []
    if not rel_bindings and isinstance(state.get("relational_bindings"), list):
        rel_bindings = state.get("relational_bindings")

    violating_symbols = {f.violating_symbol for f in current_failures}
    if isinstance(rel_bindings, list):
        for b_idx, rb in enumerate(rel_bindings):
            if isinstance(rb, dict):
                src = rb.get("source_identity") or rb.get("source") or ""
                tgt = rb.get("target_identity") or rb.get("target") or ""
                rtype = rb.get("relationship_type") or rb.get("type") or "INVOKES"
                art = rb.get("target_artifact") or rb.get("file") or ""
                # If neither source nor target is violating, it's valid and preserved
                is_affected = any(vs in src or vs in tgt for vs in violating_symbols)
                if not is_affected:
                    valid_bindings.append(
                        ValidRelationalBinding(
                            binding_id=rb.get("binding_id") or f"BIND-{b_idx + 1:02d}",
                            source_identity=src or f"comp_{b_idx + 1}",
                            target_identity=tgt or f"target_{b_idx + 1}",
                            relationship_type=rtype,
                            target_artifact=art or "main",
                            is_preserved=True,
                        )
                    )

    stage_a_out = state.get("stage_a_output") or {}
    stage_b1_out = state.get("stage_b1_output") or {}
    contract_data = state.get("contract") or {}

    stage_a_hash = _compute_hash(stage_a_out)
    stage_b1_hash = _compute_hash(stage_b1_out)
    contract_hash = _compute_hash(contract_data)

    # Preserved B-1 elements
    preserved_elements: List[Dict[str, Any]] = []
    b1_items = stage_b1_out if isinstance(stage_b1_out, list) else (stage_b1_out.get("components") or []) if isinstance(stage_b1_out, dict) else []
    for b1_item in b1_items:
        if isinstance(b1_item, dict):
            sym = b1_item.get("semantic_identity") or ""
            if sym and sym not in violating_symbols:
                preserved_elements.append({
                    "id": sym,
                    "role": b1_item.get("architectural_representation", "COMPONENT"),
                    "file": b1_item.get("target_artifact", ""),
                    "kind": b1_item.get("element_kind", "ELEMENT"),
                })

    # 4. Locked / Proven Invariants
    locked_invariants: List[LockedProvenInvariant] = []

    locked_invariants.append(
        LockedProvenInvariant(
            invariant_id="INV-STAGE-A",
            category="UPSTREAM_STAGE_A",
            description="High-level architecture topology and component roles are sealed and immutable",
            seal_hash=stage_a_hash,
            status="LOCKED",
            mutation="FORBIDDEN",
        )
    )
    locked_invariants.append(
        LockedProvenInvariant(
            invariant_id="INV-STAGE-B1",
            category="UPSTREAM_STAGE_B1",
            description="Directory scaffolding, target file paths, and manifest are sealed and immutable",
            seal_hash=stage_b1_hash,
            status="LOCKED",
            mutation="FORBIDDEN",
        )
    )
    locked_invariants.append(
        LockedProvenInvariant(
            invariant_id="INV-UNAFFECTED-B2",
            category="UNAFFECTED_B2_BINDINGS",
            description=f"All valid relational bindings ({len(valid_bindings)} bindings) must remain intact",
            seal_hash=_compute_hash([b.to_dict() for b in valid_bindings]),
            status="LOCKED",
            mutation="FORBIDDEN",
        )
    )

    # 5. Repair Targets (Atomic semantic decision allowed to change)
    repair_targets: List[RepairTargetItem] = []
    for f_idx, fail in enumerate(current_failures):
        repair_targets.append(
            RepairTargetItem(
                target_id=f"TARGET-{f_idx + 1:02d}",
                target_symbol=fail.violating_symbol,
                affected_obligations=fail.affected_obligations,
                what=f"Interface signature and argument binding for {fail.violating_symbol}",
                where=f"relational_bindings defining {fail.violating_symbol}",
                observed=fail.observed_interface,
                expected=fail.expected_interface,
            )
        )

    if not repair_targets:
        repair_targets.append(
            RepairTargetItem(
                target_id="TARGET-01",
                target_symbol="contract_target",
                affected_obligations=["OBL-PRIMARY"],
                what="Public interface compatibility",
                where="relational_bindings",
                observed="Validation failure",
                expected="Full compatibility with acceptance criteria",
            )
        )

    # 6. Repair Boundary Envelope (Permitted scope)
    allowed_mods = [
        "Modify argument list, types, return types, or method names in Stage B-2 relational_bindings for the identified Repair Targets",
        "Adjust component interface definitions to match Acceptance Oracle contract expectations",
    ]
    forbidden_mods = [
        "DO NOT modify Stage A architectural topology, component count, or component identities",
        "DO NOT modify Stage B-1 file tree, directory layout, or manifest paths",
        "DO NOT modify or remove any Valid Relational Bindings listed in Current Valid State",
        "DO NOT add extraneous files, speculative abstractions, or out-of-scope libraries",
    ]
    repair_boundary = RepairBoundaryEnvelope(
        allowed_modifications=allowed_mods,
        forbidden_modifications=forbidden_mods,
        boundary_hash=_compute_hash({"allowed": allowed_mods, "forbidden": forbidden_mods}),
        preserved_upstream=["Stage A topology", "Stage B-1 file tree"],
        preserved_relationships=["All valid relational bindings"],
    )

    # 7. Expected Post-Repair State
    expected_states: List[ExpectedPostRepairItem] = []
    for rt_idx, rt in enumerate(repair_targets):
        obl_str = rt.affected_obligations[0] if rt.affected_obligations else "authoritative_obligation"
        expected_states.append(
            ExpectedPostRepairItem(
                item_id=f"EXPECT-{rt_idx + 1:02d}",
                target_symbol=rt.target_symbol,
                expected_state=f"relationship({rt.target_symbol}) satisfies({obl_str}): {rt.expected}",
                verification_rule="Contract Gate pre-freeze authority compatibility check",
            )
        )

    # 8. Verification Criteria
    verif_criteria: List[VerificationCriterion] = [
        VerificationCriterion(
            criterion_id="CRIT-GATE-01",
            gate_name="CONTRACT_GATE_PRE_FREEZE",
            rule_description="All public symbols, methods, and parameters in relational_bindings match Oracle interface expectations exactly",
            evaluator="deterministic_contract_gate_validator",
        ),
        VerificationCriterion(
            criterion_id="CRIT-STAGE-PRES-02",
            gate_name="STAGE_PRESERVATION_GATE",
            rule_description="Stage A and Stage B-1 hashes match pre-repair snapshots exactly (zero drift)",
            evaluator="verify_stage_preservation",
        ),
        VerificationCriterion(
            criterion_id="CRIT-VALID-BIND-03",
            gate_name="VALID_BINDINGS_PRESERVED_GATE",
            rule_description="All valid relational bindings present before repair remain present and intact",
            evaluator="verify_relational_binding_integrity",
        ),
    ]

    # Context layers P1-P4
    p1_schema = state.get("canonical_schema") or {}
    p2_blueprint = {}
    if isinstance(b2_output, dict):
        p2_blueprint = {
            "component_bindings": b2_output.get("relational_bindings") or b2_output.get("bindings") or [],
            "interface_summary": b2_output.get("interface_summary") or {},
        }
    p3_diag = [raw_err for raw_err in raw_errors[:5]]
    p4_hist = []
    if "repair_history" in state and isinstance(state["repair_history"], list):
        p4_hist = [str(h)[:150] for h in state["repair_history"][:3]]

    packet.authority_obligations = authority_items
    packet.current_causal_failures = current_failures
    packet.valid_relational_bindings = valid_bindings
    packet.locked_proven_invariants = locked_invariants
    packet.repair_targets = repair_targets
    packet.repair_boundary = repair_boundary
    packet.expected_post_repair_states = expected_states
    packet.verification_criteria = verif_criteria
    packet.preserved_elements = preserved_elements
    packet.p1_canonical_schema = p1_schema if isinstance(p1_schema, dict) else {}
    packet.p2_relational_blueprint = p2_blueprint
    packet.p3_supporting_diagnostics = p3_diag
    packet.p4_historical_context = p4_hist
    packet.causal_category = causal_category
    packet.contract_hash = contract_hash
    packet.stage_a_seal = stage_a_hash
    packet.stage_b1_seal = stage_b1_hash

    return packet


# ==============================================================================
# ==============================================================================
# 4. COMPACT CANONICAL SERIALIZATION & EQUIVALENCE (Section 3 & 12)
# ==============================================================================

def serialize_compact_p0_json(packet: B2RepairDecisionPacket) -> Dict[str, Any]:
    """
    Serializes the 8 P0 semantic components into a canonical compact machine-readable dictionary.
    Keys are unambiguous and standard:
      authority, failures, preserved, invariants, target, boundary, post, verify
    """
    authority = [
        {
            "obl": a.obligation_id,
            "cat": a.category,
            "desc": a.description,
            "rel": a.expected_relationship,
            "auth": a.provenance,
        }
        for a in packet.authority_obligations
    ]

    failures = [
        {
            "id": f"FAIL-{idx + 1:02d}",
            "target": f.violating_symbol,
            "obl": f.affected_obligations,
            "cat": f.causal_category,
            "rel": f.relationship_type,
            "exp": f.expected_interface,
            "act": f.observed_interface,
            "diff": f.difference or f.root_cause_diagnostic,
            "src": f.sources or ["contract_gate"],
        }
        for idx, f in enumerate(packet.current_causal_failures)
    ]

    preserved_rels = [
        {
            "id": b.binding_id,
            "src": b.source_identity,
            "tgt": b.target_identity,
            "rel": b.relationship_type,
            "file": b.target_artifact,
            "preserved": b.is_preserved,
        }
        for b in packet.valid_relational_bindings
    ]

    preserved = {
        "elements": packet.preserved_elements,
        "relationships": preserved_rels,
    }

    invariants = [
        {
            "id": inv.invariant_id,
            "cat": inv.category,
            "desc": inv.description,
            "seal": inv.seal_hash,
            "status": inv.status,
            "mut": inv.mutation,
        }
        for inv in packet.locked_proven_invariants
    ]

    targets = [
        {
            "id": rt.target_id,
            "sym": rt.target_symbol,
            "obl": rt.affected_obligations,
            "what": rt.what,
            "where": rt.where,
            "act": rt.observed,
            "exp": rt.expected,
        }
        for rt in packet.repair_targets
    ]

    boundary = {}
    if packet.repair_boundary:
        boundary = {
            "allowed": packet.repair_boundary.allowed_modifications,
            "forbidden": packet.repair_boundary.forbidden_modifications,
            "preserved_upstream": packet.repair_boundary.preserved_upstream,
            "preserved_relationships": packet.repair_boundary.preserved_relationships,
            "hash": packet.repair_boundary.boundary_hash,
        }

    post = [
        {
            "id": exp.item_id,
            "sym": exp.target_symbol,
            "condition": exp.expected_state,
            "rule": exp.verification_rule,
        }
        for exp in packet.expected_post_repair_states
    ]

    verify = [
        {
            "id": vc.criterion_id,
            "gate": vc.gate_name,
            "rule": vc.rule_description,
            "eval": vc.evaluator,
        }
        for vc in packet.verification_criteria
    ]

    return {
        "authority": authority,
        "failures": failures,
        "preserved": preserved,
        "invariants": invariants,
        "target": targets,
        "boundary": boundary,
        "post": post,
        "verify": verify,
    }


def expand_compact_p0_json(data: Dict[str, Any]) -> B2RepairDecisionPacket:
    """
    Deterministically expands a canonical compact P0 dictionary back into a B2RepairDecisionPacket.
    Fulfills two-way semantic equivalence: semantic(expanded(compact(P0))) == semantic(original P0).
    """
    packet = B2RepairDecisionPacket()

    # Authority
    for a in data.get("authority", []):
        packet.authority_obligations.append(
            AuthorityObligationItem(
                obligation_id=a.get("obl", ""),
                description=a.get("desc", ""),
                category=a.get("cat", "INTERFACE"),
                expected_relationship=a.get("rel", ""),
                provenance=a.get("auth", "ACCEPTANCE_ORACLE"),
            )
        )

    # Failures
    for f in data.get("failures", []):
        diff = f.get("diff", "")
        diag = diff or f.get("exp", "")
        packet.current_causal_failures.append(
            CurrentCausalFailureItem(
                causal_category=f.get("cat", "B2_DECISION_ERROR"),
                affected_obligations=f.get("obl", []),
                root_cause_diagnostic=diag,
                violating_symbol=f.get("target", ""),
                expected_interface=f.get("exp", ""),
                observed_interface=f.get("act", ""),
                difference=diff,
                relationship_type=f.get("rel", "INTERFACE"),
                sources=f.get("src", ["contract_gate"]),
            )
        )

    # Preserved
    pres = data.get("preserved", {})
    if isinstance(pres, dict):
        packet.preserved_elements = pres.get("elements", [])
        for r in pres.get("relationships", []):
            packet.valid_relational_bindings.append(
                ValidRelationalBinding(
                    binding_id=r.get("id", ""),
                    source_identity=r.get("src", ""),
                    target_identity=r.get("tgt", ""),
                    relationship_type=r.get("rel", "INVOKES"),
                    target_artifact=r.get("file", ""),
                    is_preserved=r.get("preserved", True),
                )
            )

    # Invariants
    for inv in data.get("invariants", []):
        packet.locked_proven_invariants.append(
            LockedProvenInvariant(
                invariant_id=inv.get("id", ""),
                category=inv.get("cat", ""),
                description=inv.get("desc", ""),
                seal_hash=inv.get("seal", ""),
                status=inv.get("status", "LOCKED"),
                mutation=inv.get("mut", "FORBIDDEN"),
            )
        )

    # Targets
    for t in data.get("target", []):
        packet.repair_targets.append(
            RepairTargetItem(
                target_id=t.get("id", ""),
                target_symbol=t.get("sym", ""),
                affected_obligations=t.get("obl", []),
                what=t.get("what", ""),
                where=t.get("where", ""),
                observed=t.get("act", ""),
                expected=t.get("exp", ""),
            )
        )

    # Boundary
    b = data.get("boundary", {})
    if b:
        packet.repair_boundary = RepairBoundaryEnvelope(
            allowed_modifications=b.get("allowed", []),
            forbidden_modifications=b.get("forbidden", []),
            boundary_hash=b.get("hash", ""),
            preserved_upstream=b.get("preserved_upstream", []),
            preserved_relationships=b.get("preserved_relationships", []),
        )

    # Post
    for p in data.get("post", []):
        packet.expected_post_repair_states.append(
            ExpectedPostRepairItem(
                item_id=p.get("id", ""),
                target_symbol=p.get("sym", ""),
                expected_state=p.get("condition", ""),
                verification_rule=p.get("rule", ""),
            )
        )

    # Verify
    for v in data.get("verify", []):
        packet.verification_criteria.append(
            VerificationCriterion(
                criterion_id=v.get("id", ""),
                gate_name=v.get("gate", ""),
                rule_description=v.get("rule", ""),
                evaluator=v.get("eval", ""),
            )
        )

    return packet


def verify_semantic_equivalence(
    original: B2RepairDecisionPacket,
    expanded: B2RepairDecisionPacket,
) -> Tuple[bool, List[str]]:
    """
    Two-way semantic equivalence validator (Section 12).
    Verifies that every semantic relationship, authority, failure, boundary,
    target, expected state, and preserved state in original is present and
    equivalent in expanded.
    """
    errors: List[str] = []

    # 1. Authority
    if len(original.authority_obligations) != len(expanded.authority_obligations):
        errors.append(
            f"AUTHORITY_COUNT_MISMATCH: {len(original.authority_obligations)} != {len(expanded.authority_obligations)}"
        )
    else:
        for o_auth, e_auth in zip(original.authority_obligations, expanded.authority_obligations):
            if o_auth.obligation_id != e_auth.obligation_id:
                errors.append(f"AUTHORITY_ID_MISMATCH: {o_auth.obligation_id} != {e_auth.obligation_id}")
            if o_auth.expected_relationship != e_auth.expected_relationship:
                errors.append(f"AUTHORITY_REL_MISMATCH: {o_auth.expected_relationship} != {e_auth.expected_relationship}")
            if o_auth.provenance != e_auth.provenance:
                errors.append(f"AUTHORITY_PROV_MISMATCH: {o_auth.provenance} != {e_auth.provenance}")

    # 2. Failures
    if len(original.current_causal_failures) != len(expanded.current_causal_failures):
        errors.append(
            f"FAILURE_COUNT_MISMATCH: {len(original.current_causal_failures)} != {len(expanded.current_causal_failures)}"
        )
    else:
        for o_f, e_f in zip(original.current_causal_failures, expanded.current_causal_failures):
            if o_f.violating_symbol != e_f.violating_symbol:
                errors.append(f"FAILURE_SYMBOL_MISMATCH: {o_f.violating_symbol} != {e_f.violating_symbol}")
            if o_f.expected_interface != e_f.expected_interface:
                errors.append(f"FAILURE_EXPECTED_MISMATCH: {o_f.expected_interface} != {e_f.expected_interface}")
            if o_f.observed_interface != e_f.observed_interface:
                errors.append(f"FAILURE_OBSERVED_MISMATCH: {o_f.observed_interface} != {e_f.observed_interface}")

    # 3. Preserved Bindings
    if len(original.valid_relational_bindings) != len(expanded.valid_relational_bindings):
        errors.append(
            f"PRESERVED_BINDINGS_MISMATCH: {len(original.valid_relational_bindings)} != {len(expanded.valid_relational_bindings)}"
        )
    else:
        for o_b, e_b in zip(original.valid_relational_bindings, expanded.valid_relational_bindings):
            if o_b.binding_id != e_b.binding_id:
                errors.append(f"BINDING_ID_MISMATCH: {o_b.binding_id} != {e_b.binding_id}")
            if (o_b.source_identity, o_b.target_identity) != (e_b.source_identity, e_b.target_identity):
                errors.append(f"BINDING_EDGE_MISMATCH: ({o_b.source_identity}->{o_b.target_identity}) != ({e_b.source_identity}->{e_b.target_identity})")

    # 4. Invariants
    if len(original.locked_proven_invariants) != len(expanded.locked_proven_invariants):
        errors.append(
            f"INVARIANTS_COUNT_MISMATCH: {len(original.locked_proven_invariants)} != {len(expanded.locked_proven_invariants)}"
        )
    else:
        for o_inv, e_inv in zip(original.locked_proven_invariants, expanded.locked_proven_invariants):
            if o_inv.invariant_id != e_inv.invariant_id:
                errors.append(f"INVARIANT_ID_MISMATCH: {o_inv.invariant_id} != {e_inv.invariant_id}")
            if o_inv.seal_hash != e_inv.seal_hash:
                errors.append(f"INVARIANT_SEAL_MISMATCH: {o_inv.seal_hash} != {e_inv.seal_hash}")

    # 5. Targets
    if len(original.repair_targets) != len(expanded.repair_targets):
        errors.append(
            f"TARGETS_COUNT_MISMATCH: {len(original.repair_targets)} != {len(expanded.repair_targets)}"
        )
    else:
        for o_t, e_t in zip(original.repair_targets, expanded.repair_targets):
            if o_t.target_symbol != e_t.target_symbol:
                errors.append(f"TARGET_SYMBOL_MISMATCH: {o_t.target_symbol} != {e_t.target_symbol}")
            if o_t.expected != e_t.expected:
                errors.append(f"TARGET_EXPECTED_MISMATCH: {o_t.expected} != {e_t.expected}")

    # 6. Boundary
    if (original.repair_boundary is None) != (expanded.repair_boundary is None):
        errors.append("BOUNDARY_PRESENCE_MISMATCH")
    elif original.repair_boundary and expanded.repair_boundary:
        if set(original.repair_boundary.allowed_modifications) != set(expanded.repair_boundary.allowed_modifications):
            errors.append("BOUNDARY_ALLOWED_MISMATCH")
        if set(original.repair_boundary.forbidden_modifications) != set(expanded.repair_boundary.forbidden_modifications):
            errors.append("BOUNDARY_FORBIDDEN_MISMATCH")

    # 7. Post-state
    if len(original.expected_post_repair_states) != len(expanded.expected_post_repair_states):
        errors.append(
            f"POST_STATE_COUNT_MISMATCH: {len(original.expected_post_repair_states)} != {len(expanded.expected_post_repair_states)}"
        )
    else:
        for o_p, e_p in zip(original.expected_post_repair_states, expanded.expected_post_repair_states):
            if o_p.target_symbol != e_p.target_symbol:
                errors.append(f"POST_SYMBOL_MISMATCH: {o_p.target_symbol} != {e_p.target_symbol}")

    # 8. Verification criteria
    if len(original.verification_criteria) != len(expanded.verification_criteria):
        errors.append(
            f"VERIFICATION_CRITERIA_COUNT_MISMATCH: {len(original.verification_criteria)} != {len(expanded.verification_criteria)}"
        )
    else:
        for o_v, e_v in zip(original.verification_criteria, expanded.verification_criteria):
            if o_v.criterion_id != e_v.criterion_id:
                errors.append(f"CRITERIA_ID_MISMATCH: {o_v.criterion_id} != {e_v.criterion_id}")
            if o_v.gate_name != e_v.gate_name:
                errors.append(f"GATE_NAME_MISMATCH: {o_v.gate_name} != {e_v.gate_name}")

    return len(errors) == 0, errors


def _format_p0_components_uncompressed(packet: B2RepairDecisionPacket) -> str:
    """Uncompressed verbose format used as baseline for compression metrics."""
    lines = [
        "================================================================================",
        "B2 REPAIR DECISION PACKET (PROTECTED CORE - P0)",
        "================================================================================",
        f"Repair Attempt: {packet.repair_attempt} of {packet.total_allowed_repairs}",
        f"Failure Ownership: {packet.causal_category}",
        f"Contract Seal: {packet.contract_hash} | Stage A Seal: {packet.stage_a_seal} | Stage B1 Seal: {packet.stage_b1_seal}",
        "",
        "--------------------------------------------------------------------------------",
        "A. AUTHORITY / GROUND TRUTH (Acceptance Criteria)",
        "--------------------------------------------------------------------------------",
    ]
    for auth in packet.authority_obligations:
        lines.append(f"  [{auth.obligation_id}] ({auth.category}) {auth.description}")
        lines.append(f"    Expected: {auth.expected_relationship} [Provenance: {auth.provenance}]")

    lines.extend([
        "",
        "--------------------------------------------------------------------------------",
        "B. CURRENT FAILURE (Causal Root Cause)",
        "--------------------------------------------------------------------------------",
    ])
    for fail in packet.current_causal_failures:
        lines.append(f"  Target Symbol: `{fail.violating_symbol}` (Category: {fail.causal_category})")
        lines.append(f"    Root Cause: {fail.root_cause_diagnostic}")
        lines.append(f"    Observed:   {fail.observed_interface}")
        lines.append(f"    Expected:   {fail.expected_interface}")

    lines.extend([
        "",
        "--------------------------------------------------------------------------------",
        "C. CURRENT VALID STATE (Preserved Bindings)",
        "--------------------------------------------------------------------------------",
    ])
    if packet.valid_relational_bindings:
        for vb in packet.valid_relational_bindings:
            lines.append(f"  [{vb.binding_id}] {vb.source_identity} --({vb.relationship_type})--> {vb.target_identity} ({vb.target_artifact}) [PRESERVED]")
    else:
        lines.append("  (No prior valid relational bindings isolated)")

    lines.extend([
        "",
        "--------------------------------------------------------------------------------",
        "D. LOCKED / PROVEN INVARIANTS (Sealed - Mutation Strictly Forbidden)",
        "--------------------------------------------------------------------------------",
    ])
    for inv in packet.locked_proven_invariants:
        lines.append(f"  [{inv.invariant_id}] {inv.category}: {inv.description}")
        lines.append(f"    Status: {inv.status} | Mutation: {inv.mutation} | Seal: {inv.seal_hash}")

    lines.extend([
        "",
        "--------------------------------------------------------------------------------",
        "E. REPAIR TARGET (Atomic Semantic Decision Allowed to Change)",
        "--------------------------------------------------------------------------------",
    ])
    for rt in packet.repair_targets:
        lines.append(f"  [{rt.target_id}] Target Symbol: `{rt.target_symbol}`")
        lines.append(f"    What:     {rt.what}")
        lines.append(f"    Where:    {rt.where}")
        lines.append(f"    Observed: {rt.observed}")
        lines.append(f"    Expected: {rt.expected}")

    lines.extend([
        "",
        "--------------------------------------------------------------------------------",
        "F. REPAIR BOUNDARY ENVELOPE",
        "--------------------------------------------------------------------------------",
        "Allowed Modifications:",
    ])
    if packet.repair_boundary:
        for am in packet.repair_boundary.allowed_modifications:
            lines.append(f"  + {am}")
        lines.append("Forbidden Modifications:")
        for fm in packet.repair_boundary.forbidden_modifications:
            lines.append(f"  - {fm}")

    lines.extend([
        "",
        "--------------------------------------------------------------------------------",
        "G. EXPECTED POST-REPAIR STATE",
        "--------------------------------------------------------------------------------",
    ])
    for exp in packet.expected_post_repair_states:
        lines.append(f"  [{exp.item_id}] `{exp.target_symbol}`: {exp.expected_state}")
        lines.append(f"    Verification Rule: {exp.verification_rule}")

    lines.extend([
        "",
        "--------------------------------------------------------------------------------",
        "H. VERIFICATION CRITERIA",
        "--------------------------------------------------------------------------------",
    ])
    for vc in packet.verification_criteria:
        lines.append(f"  [{vc.criterion_id}] Gate: {vc.gate_name}")
        lines.append(f"    Rule:      {vc.rule_description}")
        lines.append(f"    Evaluator: {vc.evaluator}")

    return "\n".join(lines)


def _format_p0_components(packet: B2RepairDecisionPacket) -> str:
    """
    Formats the protected P0 semantic components deterministically using
    the canonical compact representation.
    """
    lines = [
        "================================================================================",
        "B2 REPAIR DECISION PACKET (COMPACT CORE - P0)",
        "================================================================================",
        f"Repair Attempt: {packet.repair_attempt} of {packet.total_allowed_repairs} | Ownership: {packet.causal_category}",
        f"Contract Seal: {packet.contract_hash} | Stage A Seal: {packet.stage_a_seal} | Stage B1 Seal: {packet.stage_b1_seal}",
        "",
        "--------------------------------------------------------------------------------",
        "A. AUTHORITY / GROUND TRUTH (Acceptance Criteria)",
        "--------------------------------------------------------------------------------",
    ]
    for auth in packet.authority_obligations:
        lines.append(f"  [{auth.obligation_id}] ({auth.category}) {auth.expected_relationship}: {auth.description}")

    lines.extend([
        "",
        "--------------------------------------------------------------------------------",
        "B. CURRENT FAILURE (Causal Root Cause)",
        "--------------------------------------------------------------------------------",
    ])
    for fail in packet.current_causal_failures:
        src_str = ", ".join(fail.sources) if fail.sources else "contract_gate"
        lines.append(f"  Target Symbol: `{fail.violating_symbol}` (Category: {fail.causal_category})")
        lines.append(f"    Relation:   {fail.relationship_type} | Root Cause: {fail.root_cause_diagnostic}")
        lines.append(f"    Observed:   {fail.observed_interface} | Expected: {fail.expected_interface}")
        if fail.difference:
            lines.append(f"    Difference: {fail.difference} | Sources: {src_str}")

    lines.extend([
        "",
        "--------------------------------------------------------------------------------",
        "C. CURRENT VALID STATE (Preserved Bindings)",
        "--------------------------------------------------------------------------------",
    ])
    if packet.valid_relational_bindings:
        for vb in packet.valid_relational_bindings:
            lines.append(f"  [{vb.binding_id}] {vb.source_identity} --({vb.relationship_type})--> {vb.target_identity} ({vb.target_artifact}) [PRESERVED]")
    else:
        lines.append("  (No prior valid relational bindings isolated)")

    lines.extend([
        "",
        "--------------------------------------------------------------------------------",
        "D. LOCKED / PROVEN INVARIANTS (Sealed - Mutation Strictly Forbidden)",
        "--------------------------------------------------------------------------------",
    ])
    for inv in packet.locked_proven_invariants:
        lines.append(f"  [{inv.invariant_id}] {inv.category}: {inv.description} [Status: {inv.status}, Seal: {inv.seal_hash}]")

    lines.extend([
        "",
        "--------------------------------------------------------------------------------",
        "E. REPAIR TARGET (Atomic Semantic Decision Allowed to Change)",
        "--------------------------------------------------------------------------------",
    ])
    for rt in packet.repair_targets:
        lines.append(f"  [{rt.target_id}] Target Symbol: `{rt.target_symbol}`")
        lines.append(f"    Where:    {rt.where}")
        lines.append(f"    Observed: {rt.observed} | Expected: {rt.expected}")

    lines.extend([
        "",
        "--------------------------------------------------------------------------------",
        "F. REPAIR BOUNDARY ENVELOPE",
        "--------------------------------------------------------------------------------",
        "Allowed Modifications:",
    ])
    if packet.repair_boundary:
        for am in packet.repair_boundary.allowed_modifications:
            lines.append(f"  + {am}")
        lines.append("Forbidden Modifications:")
        for fm in packet.repair_boundary.forbidden_modifications:
            lines.append(f"  - {fm}")
        if packet.repair_boundary.preserved_upstream:
            lines.append("Preserved Upstream:")
            for pu in packet.repair_boundary.preserved_upstream:
                lines.append(f"  * {pu}")
        if packet.repair_boundary.preserved_relationships:
            lines.append("Preserved Relationships:")
            for pr in packet.repair_boundary.preserved_relationships:
                lines.append(f"  * {pr}")

    lines.extend([
        "",
        "--------------------------------------------------------------------------------",
        "G. EXPECTED POST-REPAIR STATE",
        "--------------------------------------------------------------------------------",
    ])
    for exp in packet.expected_post_repair_states:
        lines.append(f"  [{exp.item_id}] `{exp.target_symbol}`: {exp.expected_state}")

    lines.extend([
        "",
        "--------------------------------------------------------------------------------",
        "H. VERIFICATION CRITERIA",
        "--------------------------------------------------------------------------------",
    ])
    for vc in packet.verification_criteria:
        lines.append(f"  [{vc.criterion_id}] Gate: {vc.gate_name} ({vc.evaluator}): {vc.rule_description}")

    return "\n".join(lines)


def _format_p1_schema(packet: B2RepairDecisionPacket) -> str:
    """Formats P1 canonical schema."""
    if not packet.p1_canonical_schema:
        return ""
    schema_str = json.dumps(packet.p1_canonical_schema, indent=2)
    return (
        "\n--------------------------------------------------------------------------------\n"
        "CANONICAL SCHEMA (P1)\n"
        "--------------------------------------------------------------------------------\n"
        f"{schema_str}\n"
    )


def _format_p2_blueprint(packet: B2RepairDecisionPacket) -> str:
    """Formats P2 relational blueprint."""
    if not packet.p2_relational_blueprint:
        return ""
    bp_str = json.dumps(packet.p2_relational_blueprint, indent=2)
    return (
        "\n--------------------------------------------------------------------------------\n"
        "RELATIONAL BLUEPRINT (P2)\n"
        "--------------------------------------------------------------------------------\n"
        f"{bp_str}\n"
    )


def _format_p3_diagnostics(packet: B2RepairDecisionPacket) -> str:
    """Formats P3 supporting diagnostics."""
    if not packet.p3_supporting_diagnostics:
        return ""
    lines = [
        "\n--------------------------------------------------------------------------------",
        "SUPPORTING DIAGNOSTICS (P3)",
        "--------------------------------------------------------------------------------",
    ]
    for d in packet.p3_supporting_diagnostics:
        lines.append(f"- {d}")
    return "\n".join(lines) + "\n"


def _format_p4_history(packet: B2RepairDecisionPacket) -> str:
    """Formats P4 historical context."""
    if not packet.p4_historical_context:
        return ""
    lines = [
        "\n--------------------------------------------------------------------------------",
        "HISTORICAL REPAIR CONTEXT (P4)",
        "--------------------------------------------------------------------------------",
    ]
    for h in packet.p4_historical_context:
        lines.append(f"- {h}")
    return "\n".join(lines) + "\n"


def distill_and_prioritize_packet(
    packet: B2RepairDecisionPacket,
    budget: int,
) -> Tuple[B2RepairDecisionPacket, Dict[str, Any]]:
    """
    Applies strict priority order: P0 > P1 > P2 > P3 > P4.
    If total size exceeds budget, sheds from P4 first, then P3, then P2, then P1.
    P0 is protected and NEVER dropped or partially truncated.
    """
    p0_text = _format_p0_components(packet)
    p0_len = len(p0_text)

    # Base instruction overhead estimate
    instruction_overhead = 1500
    available = budget - p0_len - instruction_overhead

    working_packet = copy.deepcopy(packet)
    shed_log: Dict[str, Any] = {
        "p4_shed": False,
        "p3_shed": False,
        "p2_shed": False,
        "p1_shed": False,
        "p0_bytes": p0_len,
        "budget": budget,
    }

    # Format remaining layers
    p1_text = _format_p1_schema(working_packet)
    p2_text = _format_p2_blueprint(working_packet)
    p3_text = _format_p3_diagnostics(working_packet)
    p4_text = _format_p4_history(working_packet)

    remaining_len = len(p1_text) + len(p2_text) + len(p3_text) + len(p4_text)

    # If exceeding budget, progressively shed lowest priority
    if remaining_len > available:
        # Shed P4
        working_packet.p4_historical_context = []
        shed_log["p4_shed"] = True
        p4_text = ""
        remaining_len = len(p1_text) + len(p2_text) + len(p3_text)

    if remaining_len > available:
        # Shed P3
        working_packet.p3_supporting_diagnostics = []
        shed_log["p3_shed"] = True
        p3_text = ""
        remaining_len = len(p1_text) + len(p2_text)

    if remaining_len > available:
        # Shed P2
        working_packet.p2_relational_blueprint = {}
        shed_log["p2_shed"] = True
        p2_text = ""
        remaining_len = len(p1_text)

    if remaining_len > available:
        # Compact or shed P1
        working_packet.p1_canonical_schema = {}
        shed_log["p1_shed"] = True
        p1_text = ""

    return working_packet, shed_log


# ==============================================================================
# 5. DELIVERY VALIDATOR (Section 9)
# ==============================================================================

def validate_b2_repair_context_delivery(
    prompt: str,
    packet: B2RepairDecisionPacket,
    budget: int,
) -> Tuple[bool, List[str]]:
    """
    Validates B2 repair context delivery right before LLM invocation.
    Fails if:
    - prompt exceeds context budget
    - missing any of the 8 required P0 semantic components
    - prompt is empty or malformed
    - repair target or boundary is missing / partial
    - duplicate diagnostic strings detected in delivery payload
    """
    errors: List[str] = []

    if not prompt or not prompt.strip():
        errors.append("PROMPT_EMPTY_OR_MALFORMED: Prompt is empty or whitespace")
        return False, errors

    if len(prompt) > budget:
        errors.append(
            f"BUDGET_EXCEEDED: Prompt length ({len(prompt)}) exceeds resolved budget ({budget})"
        )

    # Check 8 required P0 components in packet
    if not packet.authority_obligations:
        errors.append("P0_MISSING_AUTHORITY: Authority obligations list is empty")
    if not packet.current_causal_failures:
        errors.append("P0_MISSING_CURRENT_FAILURE: Current causal failures list is empty")
    # Note: valid_relational_bindings can be empty on first turn or if all broken, but must be non-None
    if packet.valid_relational_bindings is None:
        errors.append("P0_MISSING_VALID_STATE: Valid relational bindings field is None")
    if not packet.locked_proven_invariants:
        errors.append("P0_MISSING_LOCKED_INVARIANTS: Locked proven invariants list is empty")
    if not packet.repair_targets:
        errors.append("P0_MISSING_REPAIR_TARGET: Repair targets list is empty")
    if not packet.repair_boundary:
        errors.append("P0_MISSING_REPAIR_BOUNDARY: Repair boundary envelope is None")
    if not packet.expected_post_repair_states:
        errors.append("P0_MISSING_EXPECTED_POST_REPAIR: Expected post-repair states list is empty")
    if not packet.verification_criteria:
        errors.append("P0_MISSING_VERIFICATION_CRITERIA: Verification criteria list is empty")

    # Verify atomic payload protection in prompt text
    required_prompt_sections = [
        "B2 REPAIR DECISION PACKET",
        "A. AUTHORITY / GROUND TRUTH",
        "B. CURRENT FAILURE",
        "D. LOCKED / PROVEN INVARIANTS",
        "E. REPAIR TARGET",
        "F. REPAIR BOUNDARY ENVELOPE",
        "G. EXPECTED POST-REPAIR STATE",
        "H. VERIFICATION CRITERIA",
    ]
    for sec in required_prompt_sections:
        if sec not in prompt:
            errors.append(f"ATOMIC_PAYLOAD_VIOLATION: Required section '{sec}' missing from prompt")

    # Verify repair boundary explicitly defines allowed and forbidden modifications
    if packet.repair_boundary:
        if not packet.repair_boundary.allowed_modifications:
            errors.append("BOUNDARY_INVALID: Allowed modifications list is empty")
        if not packet.repair_boundary.forbidden_modifications:
            errors.append("BOUNDARY_INVALID: Forbidden modifications list is empty")

    # Verify no un-deduplicated identical failure lines in prompt
    lines = [ln.strip() for ln in prompt.split("\n") if ln.strip()]
    failure_lines = [ln for ln in lines if ln.startswith("Target Symbol:") or ln.startswith("Root Cause:")]
    seen_lines = set()
    for fl in failure_lines:
        if fl in seen_lines:
            errors.append(f"DUPLICATE_DIAGNOSTIC_DETECTED: Redundant diagnostic line in delivery: {fl[:60]}")
            break
        seen_lines.add(fl)

    # Verify two-way semantic equivalence (Section 12)
    compact_dict = serialize_compact_p0_json(packet)
    expanded = expand_compact_p0_json(compact_dict)
    equiv_ok, equiv_errors = verify_semantic_equivalence(packet, expanded)
    if not equiv_ok:
        for ee in equiv_errors:
            errors.append(f"SEMANTIC_EQUIVALENCE_VIOLATION: {ee}")

    is_valid = len(errors) == 0
    return is_valid, errors


# ==============================================================================
# 6. STATE PRESERVATION & INVARIANT ENFORCEMENT (Section 10 & 11)
# ==============================================================================

def snapshot_b2_repair_pre_state(state: Dict[str, Any]) -> B2StatePreservationSnapshot:
    """Creates a snapshot of upstream state before B2 repair invocation."""
    stage_a = state.get("stage_a_output") or {}
    stage_b1 = state.get("stage_b1_output") or {}
    tree = state.get("scaffold_tree") or state.get("directory_layout") or {}
    contract = state.get("contract") or {}
    b2_out = state.get("stage_b2_output") or {}

    return B2StatePreservationSnapshot(
        stage_a_hash=_compute_hash(stage_a),
        stage_b1_hash=_compute_hash(stage_b1),
        unaffected_b2_symbols_hash=_compute_hash(b2_out),
        scaffold_tree_hash=_compute_hash(tree),
        contract_hash=_compute_hash(contract),
    )


def verify_stage_preservation(
    pre_snapshot: B2StatePreservationSnapshot,
    post_state: Dict[str, Any],
) -> Tuple[bool, List[str]]:
    """
    Verifies that Stage A and Stage B-1 states are unchanged after B2 repair.
    """
    errors: List[str] = []

    post_a_hash = _compute_hash(post_state.get("stage_a_output") or {})
    if post_a_hash != pre_snapshot.stage_a_hash:
        errors.append(
            f"STAGE_A_MUTATION_VIOLATION: Stage A hash drifted ({pre_snapshot.stage_a_hash} -> {post_a_hash})"
        )

    post_b1_hash = _compute_hash(post_state.get("stage_b1_output") or {})
    if post_b1_hash != pre_snapshot.stage_b1_hash:
        errors.append(
            f"STAGE_B1_MUTATION_VIOLATION: Stage B-1 hash drifted ({pre_snapshot.stage_b1_hash} -> {post_b1_hash})"
        )

    post_tree_hash = _compute_hash(post_state.get("scaffold_tree") or post_state.get("directory_layout") or {})
    if post_tree_hash != pre_snapshot.scaffold_tree_hash:
        errors.append(
            f"SCAFFOLD_MUTATION_VIOLATION: Scaffold tree drifted across B2 repair"
        )

    post_contract_hash = _compute_hash(post_state.get("contract") or {})
    if post_contract_hash != pre_snapshot.contract_hash:
        errors.append(
            f"CONTRACT_MUTATION_VIOLATION: Upstream contract drifted across B2 repair"
        )

    return len(errors) == 0, errors


# ==============================================================================
# 7. PROMPT ASSEMBLY & DELIVERY ENTRYPOINT
# ==============================================================================

def assemble_and_distill_b2_repair_prompt(
    state: Dict[str, Any],
    repair_errors: Optional[List[str]] = None,
    repair_attempt: int = 1,
    budget_override: Optional[int] = None,
) -> B2DeliveryResult:
    """
    Primary entry point: extracts, distills, and validates B2 repair prompt.
    Produces a complete B2DeliveryResult.
    """
    budget = budget_override if budget_override is not None else resolve_context_budget(state)

    # 1. Extract complete semantic packet
    raw_packet = extract_b2_repair_decision_packet(state, repair_errors, repair_attempt)

    # Measure uncompressed baseline P0 size
    orig_p0_text = _format_p0_components_uncompressed(raw_packet)
    orig_p0_chars = len(orig_p0_text)

    # 2. Prioritize and distill packet within budget
    distilled_packet, shed_log = distill_and_prioritize_packet(raw_packet, budget)

    # 3. Assemble prompt string
    p0_text = _format_p0_components(distilled_packet)
    compact_p0_chars = len(p0_text)
    compression_ratio = round(compact_p0_chars / max(orig_p0_chars, 1), 4)

    p1_text = _format_p1_schema(distilled_packet)
    p2_text = _format_p2_blueprint(distilled_packet)
    p3_text = _format_p3_diagnostics(distilled_packet)
    p4_text = _format_p4_history(distilled_packet)

    instructions = (
        "\n================================================================================\n"
        "STAGE B-2 REPAIR INSTRUCTION:\n"
        "You are repairing Stage B-2 (Component Relational Bindings).\n"
        "Your task is strictly limited to resolving the errors in REPAIR TARGET.\n"
        "You MUST NOT modify Stage A topology or Stage B-1 file tree.\n"
        "You MUST preserve all items in CURRENT VALID STATE.\n"
        "Output ONLY a valid JSON object matching the Stage B-2 schema:\n"
        "{\n"
        '  "relational_bindings": [\n'
        '    {\n'
        '      "binding_id": "...",\n'
        '      "source_identity": "...",\n'
        '      "target_identity": "...",\n'
        '      "relationship_type": "...",\n'
        '      "target_artifact": "..."\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "================================================================================"
    )

    prompt_parts = [p0_text]
    if p1_text:
        prompt_parts.append(p1_text)
    if p2_text:
        prompt_parts.append(p2_text)
    if p3_text:
        prompt_parts.append(p3_text)
    if p4_text:
        prompt_parts.append(p4_text)
    prompt_parts.append(instructions)

    full_prompt = "\n".join(prompt_parts)

    # 4. Validate delivery
    delivery_valid, validation_errors = validate_b2_repair_context_delivery(
        full_prompt, distilled_packet, budget
    )

    # 5. Build telemetry (Section 12 & 13)
    components_included = ["P0"]
    if distilled_packet.p1_canonical_schema:
        components_included.append("P1")
    if distilled_packet.p2_relational_blueprint:
        components_included.append("P2")
    if distilled_packet.p3_supporting_diagnostics:
        components_included.append("P3")
    if distilled_packet.p4_historical_context:
        components_included.append("P4")

    raw_err_cnt = len(repair_errors or [])
    dedup_fail_cnt = len(distilled_packet.current_causal_failures)

    telemetry = {
        "delivery_method": "b2_compact_packet_v1",
        "budget": budget,
        "char_count": len(full_prompt),
        "delivery_valid": delivery_valid,
        "repair_attempt": repair_attempt,
        "components_included": components_included,
        "raw_error_count": raw_err_cnt,
        "deduplicated_failure_count": dedup_fail_cnt,
        "deduplication_ratio": round(dedup_fail_cnt / max(raw_err_cnt, 1), 2),
        "validation_errors": validation_errors,
        "shed_log": shed_log,
        "p0_authority_count": len(distilled_packet.authority_obligations),
        "p0_current_failure_count": dedup_fail_cnt,
        "p0_valid_bindings_count": len(distilled_packet.valid_relational_bindings),
        "p0_locked_invariants_count": len(distilled_packet.locked_proven_invariants),
        "p0_repair_targets_count": len(distilled_packet.repair_targets),
        "original_p0_chars": orig_p0_chars,
        "compact_p0_chars": compact_p0_chars,
        "compression_ratio": compression_ratio,
        "p0_semantic_equivalence_valid": not any("SEMANTIC_EQUIVALENCE_VIOLATION" in e for e in validation_errors),
    }

    return B2DeliveryResult(
        prompt=full_prompt,
        packet=distilled_packet,
        delivery_valid=delivery_valid,
        budget=budget,
        char_count=len(full_prompt),
        validation_errors=validation_errors,
        telemetry=telemetry,
    )
