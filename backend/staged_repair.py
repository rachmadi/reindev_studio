"""
staged_repair.py — Failure Ownership Classifier v2 & Selective Stage-B Unfreeze
Treatment #1.8.9 Pipeline Repair.

Provides generic (task-agnostic) utilities for:
  1. Classifying which staged decision is responsible for a Contract Gate failure (Classifier v2).
  2. Computing / updating the stage_lifecycle provenance sub-dict.
  3. Applying lifecycle invalidations to frozen state objects before restoration.
  4. Verifying state preservation invariants (Section 7).
  5. Building repair-turn telemetry records (Section 8).

NO task-specific routing. NO hardcoded symbol names, routes, or class names.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants — failure owner labels (generic)
# ---------------------------------------------------------------------------

OWNER_REPRESENTATION_FAILURE = "REPRESENTATION_FAILURE"
OWNER_RELATIONSHIP_BINDING_FAILURE = "RELATIONSHIP_BINDING_FAILURE"
OWNER_ELEMENT_REALIZATION_FAILURE = "ELEMENT_REALIZATION_FAILURE"
OWNER_IDENTITY_FAILURE = "IDENTITY_FAILURE"
OWNER_UNKNOWN = "UNKNOWN"

# Stage names used in lifecycle dict keys
STAGE_A = "stage_a"
STAGE_B1 = "stage_b1"
STAGE_B2 = "stage_b2"

# Lifecycle status values
STATUS_FROZEN = "FROZEN"
STATUS_INVALIDATED = "INVALIDATED"
STATUS_REPAIRED = "REPAIRED"
STATUS_DRAFT = "DRAFT"

# Invalidation sets per owner (order matters for dependency cascade)
_OWNER_TO_INVALIDATE: Dict[str, List[str]] = {
    OWNER_REPRESENTATION_FAILURE: [],  # assembly-only; semantic stages preserved
    OWNER_RELATIONSHIP_BINDING_FAILURE: [STAGE_B2],
    OWNER_ELEMENT_REALIZATION_FAILURE: [STAGE_B1, STAGE_B2],
    OWNER_IDENTITY_FAILURE: [STAGE_A, STAGE_B1, STAGE_B2],
    OWNER_UNKNOWN: [],  # do not guess an owner
}

_OWNER_TO_REPAIR_OWNER: Dict[str, str] = {
    OWNER_REPRESENTATION_FAILURE: "STAGE_B3",
    OWNER_RELATIONSHIP_BINDING_FAILURE: "STAGE_B2",
    OWNER_ELEMENT_REALIZATION_FAILURE: "STAGE_B1",
    OWNER_IDENTITY_FAILURE: "STAGE_A",
    OWNER_UNKNOWN: "NONE",
}


# ---------------------------------------------------------------------------
# Classification Result Wrapper
# ---------------------------------------------------------------------------

class FailureClassificationResult(tuple):
    """
    Subclass of tuple (owner, invalidate_stages, evidence_summary)
    providing backward-compatible 3-element unpacking alongside named v2 attributes.
    """
    owner: str
    invalidate_stages: List[str]
    evidence_summary: str
    causal_category: str
    outer_category: str
    repair_owner: str

    def __new__(
        cls,
        owner: str,
        invalidate_stages: List[str],
        evidence_summary: str,
        causal_category: str,
        outer_category: str,
        repair_owner: str,
    ):
        return super().__new__(cls, (owner, invalidate_stages, evidence_summary))

    def __init__(
        self,
        owner: str,
        invalidate_stages: List[str],
        evidence_summary: str,
        causal_category: str,
        outer_category: str,
        repair_owner: str,
    ):
        self.owner = owner
        self.invalidate_stages = invalidate_stages
        self.evidence_summary = evidence_summary
        self.causal_category = causal_category
        self.outer_category = outer_category
        self.repair_owner = repair_owner


# ---------------------------------------------------------------------------
# 1. Failure Ownership Classifier v2
# ---------------------------------------------------------------------------

# Outer wrappers that must NOT by themselves imply IDENTITY_FAILURE (Section 2)
_PATTERNS_OUTER_WRAPPER: List[str] = [
    r"PRE_FREEZE_AUTHORITY_INCOMPATIBLE",
    r"CONTRACT_VALIDATION_FAILED",
    r"Pilar 4",
    r"Oracle Consistency",
]

# Priority 1: Representation / assembly failure
_PATTERNS_REPRESENTATION: List[str] = [
    r"STATE_REPRESENTATION_FAILURE",
    r"REPRESENTATION_FAILURE",
    r"STAGE_B3_ASSEMBLY_FAILURE",
    r"assembly.{0,30}failure",
    r"serialization.{0,30}failure",
    r"forbidden.{0,30}delimiter",
    r"architecture_plan.{0,30}contains",
    r"architecture_plan.{0,30}violates",
    r"architecture_plan.{0,30}is not valid JSON",
    r"SCHEMA_VIOLATION:\s*Blueprint JSON parse failure",
]

# Priority 2: Relationship / binding decisions (Stage B-2)
_PATTERNS_RELATIONSHIP_BINDING: List[str] = [
    # Call shape & signature parameter cardinality/types
    r"CALL_SHAPE_INCOMPATIBILITY",
    r"invoked with \d+ positional argument",
    r"accepts at most \d+",
    r"positional.{0,30}argument",
    r"parameter.{0,30}incompatib",
    r"parameter.{0,30}count",
    r"wrong.{0,30}param",
    r"expected.{0,30}\d+.{0,30}param",
    r"signature.{0,30}mismatch",
    r"signature.{0,30}incompatib",

    # Route, endpoint, HTTP method & route-to-symbol binding proof
    r"route.{0,30}mismatch",
    r"endpoint.{0,30}mismatch",
    r"http.{0,30}method.{0,30}mismatch",
    r"public.{0,30}route",
    r"public.{0,30}endpoint",
    r"route.{0,30}binding",
    r"endpoint.{0,30}binding",
    r"binding proof connects them",
    r"Found internal function.*no public route",
    r"target.{0,30}linkage.{0,30}incompatib",
    r"interface.{0,30}binding.{0,30}failure",
    r"binding.{0,30}incompatib",
    r"RELATIONSHIP_BINDING_FAILURE",
    r"STAGE_B2_BINDING_FAILURE",

    # Scenario scaffold & error-path reachability
    r"SCENARIO_SCAFFOLD_INCOMPATIBILITY.*UNDETERMINED",
    r"scaffold.{0,30}undetermined",
    r"absence of error path",
    r"conditional branch or error path",
    r"CONTRACT_COVERAGE:\s*INCOMPATIBLE",
]

# Priority 3: Element realization decisions (Stage B-1)
_PATTERNS_ELEMENT_REALIZATION: List[str] = [
    r"CONTRACT_COVERAGE:\s*MISSING",
    r"coverage:\s*missing",
    r"not.{0,30}declared.{0,30}in.{0,30}interface",
    r"missing.{0,30}from.{0,30}interface",
    r"element.{0,30}not.{0,30}realized",
    r"realization.{0,30}failure",
    r"STAGE_B1_REALIZATION_FAILURE",
    r"ELEMENT_REALIZATION_FAILURE",
]

# Priority 4: Abstract obligation / identity decisions (Stage A)
_PATTERNS_IDENTITY: List[str] = [
    r"STAGE_A_MAPPING_FAILURE",
    r"STAGE_A_JSON_PARSE_ERROR",
    r"semantic.{0,30}identity.{0,30}wrong",
    r"identity.{0,30}mismatch",
    r"obligation.{0,30}not.{0,30}found",
    r"unknown.{0,30}obligation",
    r"unauthorized.{0,30}obligation",
    r"SCENARIO_SCAFFOLD_INCOMPATIBILITY.*INCOMPATIBLE",
]


def _matches_any(text: str, patterns: List[str]) -> bool:
    for pat in patterns:
        if re.search(pat, text, re.IGNORECASE):
            return True
    return False


def classify_contract_failure_owner(
    gate_errors: List[str],
    violations: Optional[List[Dict[str, Any]]] = None,
    coverage_matrix: Optional[Dict[str, Any]] = None,
) -> FailureClassificationResult:
    """
    Classify which staged decision is responsible for a Contract Gate failure (Classifier v2).

    Enforces the Specificity Order (Section 2 & 3):
      specific causal evidence > semantic failure category > generic wrapper
      Order:
        1. REPRESENTATION_FAILURE
        2. RELATIONSHIP_BINDING_FAILURE
        3. ELEMENT_REALIZATION_FAILURE
        4. IDENTITY_FAILURE
        5. UNKNOWN

    The outer wrapper `PRE_FREEZE_AUTHORITY_INCOMPATIBLE` NEVER by itself implies `IDENTITY_FAILURE`.

    Args:
        gate_errors:      List of string error messages from state["contract_validation_errors"].
        violations:       Optional list of violation dicts from validate_architect_phase.
        coverage_matrix:  Optional coverage_matrix dict from CEP.

    Returns:
        FailureClassificationResult tuple with attributes:
          .owner              -- one of OWNER_* constants
          .invalidate_stages  -- list of stages to invalidate
          .evidence_summary   -- human-readable summary for provenance
          .causal_category    -- specific causal category identified
          .outer_category     -- detected outer error envelope
          .repair_owner       -- target agent/stage for repair ("STAGE_B2", etc.)
    """
    if violations is None:
        violations = []
    if coverage_matrix is None:
        coverage_matrix = {}

    # Combine all text evidence for a single scan pass
    all_texts: List[str] = list(gate_errors)
    for v in violations:
        msg = v.get("message", "")
        if msg:
            all_texts.append(str(msg))
        crit = v.get("criterion", "")
        if crit:
            all_texts.append(str(crit))

    combined = " \n ".join(all_texts)

    # 0. Identify outer error envelope (for telemetry, does NOT dictate causal category)
    outer_category = "NONE"
    if _matches_any(combined, [r"PRE_FREEZE_AUTHORITY_INCOMPATIBLE"]):
        outer_category = "PRE_FREEZE_AUTHORITY_INCOMPATIBLE"
    elif _matches_any(combined, [r"CONTRACT_VALIDATION_FAILED"]):
        outer_category = "CONTRACT_VALIDATION_FAILED"

    # Evaluate specific causal patterns FIRST in mandated order:
    if _matches_any(combined, _PATTERNS_REPRESENTATION):
        owner = OWNER_REPRESENTATION_FAILURE
        causal_category = OWNER_REPRESENTATION_FAILURE
        evidence_summary = (
            "Contract Gate: representation/assembly failure -- semantic stages valid, "
            "deterministic assembly or schema representation needs repair"
        )
    elif _matches_any(combined, _PATTERNS_RELATIONSHIP_BINDING):
        owner = OWNER_RELATIONSHIP_BINDING_FAILURE
        causal_category = OWNER_RELATIONSHIP_BINDING_FAILURE
        evidence_summary = (
            "Contract Gate: relationship/binding failure -- call shape, route, "
            "parameter cardinality, or endpoint binding mismatch"
        )
    elif _matches_any(combined, _PATTERNS_ELEMENT_REALIZATION):
        owner = OWNER_ELEMENT_REALIZATION_FAILURE
        causal_category = OWNER_ELEMENT_REALIZATION_FAILURE
        evidence_summary = (
            "Contract Gate: element realization failure -- element missing from interface "
            "without route/binding proof"
        )
    elif _matches_any(combined, _PATTERNS_IDENTITY):
        owner = OWNER_IDENTITY_FAILURE
        causal_category = OWNER_IDENTITY_FAILURE
        evidence_summary = (
            "Contract Gate: identity-level failure -- semantic identity or obligation "
            "mapping contradiction"
        )
    else:
        # Section 9 Rule N: Unknown failure does not guess an owner
        owner = OWNER_UNKNOWN
        causal_category = OWNER_UNKNOWN
        evidence_summary = "Contract Gate: unrecognized failure diagnostic; no owner guessed"

    invalidate_stages = list(_OWNER_TO_INVALIDATE.get(owner, []))
    repair_owner = _OWNER_TO_REPAIR_OWNER.get(owner, "NONE")

    return FailureClassificationResult(
        owner=owner,
        invalidate_stages=invalidate_stages,
        evidence_summary=evidence_summary,
        causal_category=causal_category,
        outer_category=outer_category,
        repair_owner=repair_owner,
    )


# ---------------------------------------------------------------------------
# 2. Stage Lifecycle Computation
# ---------------------------------------------------------------------------

_OWNER_TO_REASON: Dict[str, str] = {
    OWNER_IDENTITY_FAILURE: (
        "Semantic identity contradiction: Stage A semantic mapping was inconsistent "
        "with oracle acceptance call sites."
    ),
    OWNER_ELEMENT_REALIZATION_FAILURE: (
        "Element realization contradiction: Stage B1 element mapping was missing "
        "or inconsistent with contract coverage."
    ),
    OWNER_RELATIONSHIP_BINDING_FAILURE: (
        "Relationship/binding contradiction: Stage B2 binding decisions produced "
        "incorrect call-shapes, routes, or parameter signatures."
    ),
    OWNER_REPRESENTATION_FAILURE: (
        "Representation failure: Stage B3 deterministic assembly produced malformed "
        "blueprint; semantic stages are valid."
    ),
    OWNER_UNKNOWN: "Unknown failure: no specific staged owner identified.",
}


def compute_stage_lifecycle(
    prev_lifecycle: Dict[str, Any],
    failure_owner: str,
    invalidate_stages: List[str],
    gate_errors: List[str],
) -> Dict[str, Any]:
    """
    Compute an updated stage_lifecycle dict given the current failure classification.
    """
    now = datetime.now().isoformat()
    new_lifecycle: Dict[str, Any] = {}

    all_stages = [STAGE_A, STAGE_B1, STAGE_B2]
    for stage_key in all_stages:
        prev_entry = prev_lifecycle.get(stage_key, {})
        prev_attempts = int(prev_entry.get("repair_attempt", 0))
        prev_sha = prev_entry.get("sha256", "")
        prev_status = prev_entry.get("status", STATUS_FROZEN)

        if stage_key in invalidate_stages:
            new_lifecycle[stage_key] = {
                "status": STATUS_INVALIDATED,
                "invalidated_by": failure_owner,
                "invalidation_reason": _OWNER_TO_REASON.get(failure_owner, ""),
                "invalidation_evidence": gate_errors[:5],
                "invalidation_owner": failure_owner,
                "invalidated_at": now,
                "repair_attempt": prev_attempts + 1,
                "sha256": prev_sha,
                "previous_status": prev_status,
            }
        else:
            effective_status = prev_status if prev_status != STATUS_INVALIDATED else STATUS_FROZEN
            new_lifecycle[stage_key] = {
                "status": effective_status,
                "invalidated_by": prev_entry.get("invalidated_by"),
                "invalidation_reason": prev_entry.get("invalidation_reason"),
                "invalidation_evidence": prev_entry.get("invalidation_evidence", []),
                "invalidation_owner": prev_entry.get("invalidation_owner"),
                "invalidated_at": prev_entry.get("invalidated_at"),
                "repair_attempt": prev_attempts,
                "sha256": prev_sha,
                "previous_status": prev_entry.get("previous_status"),
            }

    return new_lifecycle


# ---------------------------------------------------------------------------
# 3. Apply Lifecycle to Frozen States
# ---------------------------------------------------------------------------

def apply_lifecycle_to_frozen_states(
    frozen_stage_a: Optional[Any],
    frozen_stage_b1: Optional[Any],
    frozen_stage_b2: Optional[Any],
    stage_lifecycle: Dict[str, Any],
) -> Tuple[Optional[Any], Optional[Any], Optional[Any]]:
    """
    Apply stage lifecycle invalidations to the three frozen state objects.

    Any stage whose lifecycle status is INVALIDATED is replaced with None.
    Dependency cascade:
      - If Stage A is invalidated -> B1 and B2 are also nulled.
      - If Stage B1 is invalidated -> B2 is also nulled.
    """
    if not stage_lifecycle:
        return frozen_stage_a, frozen_stage_b1, frozen_stage_b2

    entry_a = stage_lifecycle.get(STAGE_A, {})
    entry_b1 = stage_lifecycle.get(STAGE_B1, {})
    entry_b2 = stage_lifecycle.get(STAGE_B2, {})

    if entry_a.get("status") == STATUS_INVALIDATED:
        frozen_stage_a = None

    if entry_b1.get("status") == STATUS_INVALIDATED:
        frozen_stage_b1 = None

    if entry_b2.get("status") == STATUS_INVALIDATED:
        frozen_stage_b2 = None

    if frozen_stage_a is None:
        frozen_stage_b1 = None
        frozen_stage_b2 = None

    if frozen_stage_b1 is None:
        frozen_stage_b2 = None

    return frozen_stage_a, frozen_stage_b1, frozen_stage_b2


# ---------------------------------------------------------------------------
# 4. State Preservation Verification (Section 7)
# ---------------------------------------------------------------------------

def verify_stage_preservation(
    pre_lifecycle_frozen_a: Optional[Any],
    pre_lifecycle_frozen_b1: Optional[Any],
    post_repair_frozen_a: Optional[Any],
    post_repair_frozen_b1: Optional[Any],
    failure_owner: str,
) -> Tuple[bool, List[str]]:
    """
    Verify Section 7 Invariant:
    When RELATIONSHIP_BINDING_FAILURE occurs, Stage A and Stage B-1 must remain
    identical to their pre-repair states. Any unexpected mutation is REGRESSION.

    Returns:
        (is_preserved, regression_errors)
    """
    errors: List[str] = []
    if failure_owner == OWNER_RELATIONSHIP_BINDING_FAILURE:
        if pre_lifecycle_frozen_a is not None and post_repair_frozen_a is not None:
            pre_a_sha = getattr(pre_lifecycle_frozen_a, "sha256_seal", "")
            post_a_sha = getattr(post_repair_frozen_a, "sha256_seal", "")
            if pre_a_sha and post_a_sha and pre_a_sha != post_a_sha:
                errors.append(
                    f"REGRESSION: Stage A hash mutated during Stage B-2 repair! "
                    f"Expected {pre_a_sha}, observed {post_a_sha}"
                )
        if pre_lifecycle_frozen_b1 is not None and post_repair_frozen_b1 is not None:
            pre_b1_sha = getattr(pre_lifecycle_frozen_b1, "sha256_seal", "")
            post_b1_sha = getattr(post_repair_frozen_b1, "sha256_seal", "")
            if pre_b1_sha and post_b1_sha and pre_b1_sha != post_b1_sha:
                errors.append(
                    f"REGRESSION: Stage B-1 hash mutated during Stage B-2 repair! "
                    f"Expected {pre_b1_sha}, observed {post_b1_sha}"
                )
    return len(errors) == 0, errors


# ---------------------------------------------------------------------------
# 5. Repair Telemetry Builder (Section 8)
# ---------------------------------------------------------------------------

def build_repair_telemetry(
    is_repair_turn: bool,
    stage_lifecycle: Dict[str, Any],
    pre_lifecycle_frozen_a: Optional[Any],
    pre_lifecycle_frozen_b1: Optional[Any],
    pre_lifecycle_frozen_b2: Optional[Any],
    post_lifecycle_frozen_a: Optional[Any],
    post_lifecycle_frozen_b1: Optional[Any],
    post_lifecycle_frozen_b2: Optional[Any],
    new_frozen_b1: Optional[Any] = None,
    new_frozen_b2: Optional[Any] = None,
    causal_failure_category: Optional[str] = None,
    outer_error_category: Optional[str] = None,
    repair_owner: Optional[str] = None,
    invoked_stage: Optional[str] = None,
    repair_attempt: int = 0,
) -> Dict[str, Any]:
    """
    Build the repair telemetry dict recording all Section 8 fields.
    """
    if not is_repair_turn:
        return {"repair_execution": "NOT_A_REPAIR_TURN"}

    a_was_nulled = (pre_lifecycle_frozen_a is not None) and (post_lifecycle_frozen_a is None)
    b1_was_nulled = (pre_lifecycle_frozen_b1 is not None) and (post_lifecycle_frozen_b1 is None)
    b2_was_nulled = (pre_lifecycle_frozen_b2 is not None) and (post_lifecycle_frozen_b2 is None)

    inferred_invoked = (
        invoked_stage
        or ("STAGE_B2" if b2_was_nulled and not (a_was_nulled or b1_was_nulled)
            else ("STAGE_B1" if b1_was_nulled and not a_was_nulled
                  else ("STAGE_A" if a_was_nulled else "NONE")))
    )
    llm_invoked = inferred_invoked in ("STAGE_A", "STAGE_B1", "STAGE_B2") or a_was_nulled or b1_was_nulled or b2_was_nulled

    repair_execution = "LLM_INVOKED" if llm_invoked else "SKIPPED_CACHE_REENTRY"

    # Hashes
    prev_h_a = getattr(pre_lifecycle_frozen_a, "sha256_seal", None) if pre_lifecycle_frozen_a else None
    prev_h_b1 = getattr(pre_lifecycle_frozen_b1, "sha256_seal", None) if pre_lifecycle_frozen_b1 else None
    prev_h_b2 = getattr(pre_lifecycle_frozen_b2, "sha256_seal", None) if pre_lifecycle_frozen_b2 else None

    new_h_a = getattr(post_lifecycle_frozen_a, "sha256_seal", None) if post_lifecycle_frozen_a else None
    new_h_b1 = getattr(new_frozen_b1 or post_lifecycle_frozen_b1, "sha256_seal", None) if (new_frozen_b1 or post_lifecycle_frozen_b1) else None
    new_h_b2 = getattr(new_frozen_b2 or post_lifecycle_frozen_b2, "sha256_seal", None) if (new_frozen_b2 or post_lifecycle_frozen_b2) else None

    invalidated_stages = [
        k for k in [STAGE_A, STAGE_B1, STAGE_B2]
        if stage_lifecycle.get(k, {}).get("status") == STATUS_INVALIDATED
    ]
    preserved_stages = [
        k for k in [STAGE_A, STAGE_B1, STAGE_B2]
        if stage_lifecycle.get(k, {}).get("status") == STATUS_FROZEN
    ]

    effective_repair_owner = repair_owner or (
        "STAGE_B2" if STAGE_B2 in invalidated_stages and STAGE_B1 not in invalidated_stages
        else ("STAGE_B1" if STAGE_B1 in invalidated_stages and STAGE_A not in invalidated_stages
              else ("STAGE_A" if STAGE_A in invalidated_stages else "NONE"))
    )

    effective_causal = causal_failure_category or (
        OWNER_RELATIONSHIP_BINDING_FAILURE if effective_repair_owner == "STAGE_B2"
        else (OWNER_ELEMENT_REALIZATION_FAILURE if effective_repair_owner == "STAGE_B1"
              else (OWNER_IDENTITY_FAILURE if effective_repair_owner == "STAGE_A" else OWNER_UNKNOWN))
    )

    return {
        "repair_execution": repair_execution,
        "causal_failure_category": effective_causal,
        "outer_error_category": outer_error_category or "NONE",
        "repair_owner": effective_repair_owner,
        "invalidated_stages": invalidated_stages,
        "preserved_stages": preserved_stages,
        "llm_invoked": llm_invoked,
        "invoked_stage": inferred_invoked,
        "repair_attempt": repair_attempt,
        "previous_hashes": {
            "stage_a": prev_h_a,
            "stage_b1": prev_h_b1,
            "stage_b2": prev_h_b2,
        },
        "new_hashes": {
            "stage_a": new_h_a,
            "stage_b1": new_h_b1,
            "stage_b2": new_h_b2,
        },
        # Legacy-compatible hash fields
        "preserved_stage_a_hash": new_h_a,
        "preserved_b1_hash": new_h_b1,
        "previous_b1_hash": prev_h_b1,
        "previous_b2_hash": prev_h_b2,
        "repaired_b2_hash": getattr(new_frozen_b2, "sha256_seal", None) if new_frozen_b2 else None,
        "a_was_nulled_by_lifecycle": a_was_nulled,
        "b1_was_nulled_by_lifecycle": b1_was_nulled,
        "b2_was_nulled_by_lifecycle": b2_was_nulled,
    }
