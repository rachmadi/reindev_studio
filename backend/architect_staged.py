"""
Staged Architectural Decision Engine (v1.0.0)
Treatment #1.8.6 — Staged Architectural Decision v1

Decomposes the System Architect's work into two distinct semantic stages:
1. STAGE A: Acceptance Obligation Mapping (LLM)
   -> Deterministic Stage-A Check (Pure Python)
   -> Freeze Validated Semantic State (Immutable)
2. STAGE B: Architectural Assembly (LLM)
   -> Stage-B Preservation & Assembly Check (Pure Python)
   -> Deterministic Serialization (#1.8.5 Engine)
   -> Canonical ArchitecturalBlueprint

CORE INVARIANTS:
- Python stores state, validates structure, forwards results, detects missing/duplicate/conflict,
  and executes deterministic serialization. Python NEVER picks architecture.
- Once Stage A produces VALIDATED SEMANTIC MAPPING, Stage B receives that exact semantic state.
- Stage B cannot silently rename, delete, reinterpret, or duplicate validated obligation mappings.
- Explicit Stage A revision requests are formally parsed and returned to Stage A.
- Zero task-specific branching (no if fastapi, no if flutter, etc.).
"""

from __future__ import annotations
import json
import re
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple, Set, Union

try:
    from .blueprint_schema import (
        ArchitecturalBlueprint,
        BlueprintInterfaceContract,
        BlueprintDataModel,
        BlueprintFileModule,
        BlueprintModelField,
        decode_canonical_architectural_json
    )
    from .semantic_serializer import (
        SemanticParameter,
        SemanticReturn,
        SemanticArchitecturalDecision,
        SemanticArchitecturalPlan,
        serialize_semantic_decision_to_blueprint
    )
except (ImportError, ValueError):
    try:
        from blueprint_schema import (
            ArchitecturalBlueprint,
            BlueprintInterfaceContract,
            BlueprintDataModel,
            BlueprintFileModule,
            BlueprintModelField,
            decode_canonical_architectural_json
        )
        from semantic_serializer import (
            SemanticParameter,
            SemanticReturn,
            SemanticArchitecturalDecision,
            SemanticArchitecturalPlan,
            serialize_semantic_decision_to_blueprint
        )
    except ImportError:
        ArchitecturalBlueprint = None
        BlueprintInterfaceContract = None
        BlueprintDataModel = None
        BlueprintFileModule = None
        BlueprintModelField = None
        SemanticParameter = None
        SemanticReturn = None
        SemanticArchitecturalDecision = None
        SemanticArchitecturalPlan = None
        serialize_semantic_decision_to_blueprint = None


# ============================================================================
# 1. Stage A Data Models & Formats
# ============================================================================

VALID_ELEMENT_KINDS = {
    "CALLABLE", "FUNCTION", "CLASS", "COMPONENT",
    "ENDPOINT", "HTTP_ENDPOINT", "DATA_MODEL", "MODEL", "WIDGET", "METHOD"
}


@dataclass(frozen=True)
class StageAObligationMapping:
    """
    Abstract semantic architectural decision for a single acceptance obligation.
    Produced exclusively in Stage A.
    Contains NO file_tree, NO scaffold code, NO canonical Pydantic field syntax.
    Retains full obligation traceability (Treatment #1.8.7).
    """
    obligation_id: str
    semantic_element: str
    element_kind: str
    semantic_identity: str
    semantic_target_artifact: str
    semantic_parameters: Tuple[Dict[str, Any], ...] = field(default_factory=tuple)
    semantic_return: Dict[str, Any] = field(default_factory=dict)
    description: Optional[str] = None
    source_authority: str = "ACCEPTANCE_ORACLE"
    evidence_basis: str = ""

    @property
    def mapped_element(self) -> str:
        return self.semantic_element

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "obligation_id": self.obligation_id,
            "semantic_element": self.semantic_element,
            "mapped_element": self.semantic_element,
            "element_kind": self.element_kind,
            "semantic_identity": self.semantic_identity,
            "semantic_target_artifact": self.semantic_target_artifact,
            "semantic_parameters": list(self.semantic_parameters),
            "semantic_return": dict(self.semantic_return),
            "source_authority": self.source_authority,
            "evidence_basis": self.evidence_basis
        }
        if self.description:
            d["description"] = self.description
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> StageAObligationMapping:
        ob_id = str(data.get("obligation_id") or data.get("id") or "").strip()
        elem = str(data.get("semantic_element") or data.get("mapped_element") or data.get("element") or "").strip()
        kind = str(data.get("element_kind") or data.get("kind") or "").strip().upper()
        ident = str(data.get("semantic_identity") or data.get("identity") or data.get("identifier") or "").strip()
        art = str(data.get("semantic_target_artifact") or data.get("target_artifact") or data.get("target_file") or "").strip().replace("\\", "/")
        
        raw_params = data.get("semantic_parameters") or data.get("parameters") or []
        params_list = []
        if isinstance(raw_params, list):
            for p in raw_params:
                if isinstance(p, dict):
                    params_list.append(dict(p))
                elif isinstance(p, str):
                    params_list.append({"name": p.strip(), "type": "str", "location": "ARGUMENT", "required": True})
        
        raw_ret = data.get("semantic_return") or data.get("return") or data.get("return_semantics") or {}
        ret_dict = {}
        if isinstance(raw_ret, dict):
            ret_dict = dict(raw_ret)
        elif isinstance(raw_ret, str) and raw_ret.strip():
            ret_dict = {"type": raw_ret.strip()}

        desc = data.get("description") or data.get("desc")
        src_auth = str(data.get("source_authority") or data.get("authority") or "ACCEPTANCE_ORACLE").strip()
        ev_basis = str(data.get("evidence_basis") or data.get("rationale") or data.get("evidence") or "").strip()

        return cls(
            obligation_id=ob_id,
            semantic_element=elem,
            element_kind=kind,
            semantic_identity=ident,
            semantic_target_artifact=art,
            semantic_parameters=tuple(params_list),
            semantic_return=ret_dict,
            description=desc,
            source_authority=src_auth,
            evidence_basis=ev_basis
        )


@dataclass(frozen=True)
class FrozenStageAMappings:
    """
    Immutable sealed container for validated Stage A mappings.
    Guarantees state immutability between Stage A and Stage B.
    """
    mappings: Tuple[StageAObligationMapping, ...]
    sha256_seal: str
    validated_at: str

    @classmethod
    def freeze(cls, mappings: List[StageAObligationMapping], timestamp: Optional[str] = None) -> FrozenStageAMappings:
        from datetime import datetime
        ts = timestamp or datetime.now().isoformat()
        sorted_mappings = sorted(mappings, key=lambda m: m.obligation_id)
        raw_data = [m.to_dict() for m in sorted_mappings]
        canonical_json = json.dumps(raw_data, sort_keys=True)
        seal = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
        return cls(
            mappings=tuple(sorted_mappings),
            sha256_seal=seal,
            validated_at=ts
        )

    def get_mapping(self, obligation_id: str) -> Optional[StageAObligationMapping]:
        for m in self.mappings:
            if m.obligation_id == obligation_id:
                return m
        return None

    def get_all_obligation_ids(self) -> Set[str]:
        return {m.obligation_id for m in self.mappings}

    def to_dict_list(self) -> List[Dict[str, Any]]:
        return [m.to_dict() for m in self.mappings]


@dataclass
class StageARevisionRequest:
    """
    Formal, explicit request from Stage B to revise a Stage A mapping.
    Prevents silent renaming, deletion, or reinterpretation.
    """
    obligation_id: str
    reason: str
    requested_change: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "obligation_id": self.obligation_id,
            "reason": self.reason,
            "requested_change": self.requested_change
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> StageARevisionRequest:
        return cls(
            obligation_id=str(data.get("obligation_id", "")).strip(),
            reason=str(data.get("reason", "")).strip(),
            requested_change=dict(data.get("requested_change", {}))
        )


@dataclass
class StageBAssemblyOutput:
    """
    Assembled architectural structure produced in Stage B.
    Treatment #1.8.8: Supports decoupled representation (decisions + raw scaffold files).
    """
    target_file: str
    files: Dict[str, str] = field(default_factory=dict)
    scaffold_code: str = ""
    semantic_decisions: List[SemanticArchitecturalDecision] = field(default_factory=list)
    stage_a_revision_requests: List[StageARevisionRequest] = field(default_factory=list)
    raw_text: str = ""
    decoder_telemetry: Dict[str, Any] = field(default_factory=dict)
    is_decoupled: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_file": self.target_file,
            "files": dict(self.files),
            "scaffold_code": self.scaffold_code,
            "semantic_decisions": [d.to_dict() if hasattr(d, "to_dict") else asdict(d) for d in self.semantic_decisions],
            "stage_a_revision_requests": [r.to_dict() for r in self.stage_a_revision_requests],
            "raw_text": self.raw_text,
            "decoder_telemetry": dict(self.decoder_telemetry),
            "is_decoupled": self.is_decoupled
        }


# ============================================================================
# 1B. Stage B-1 & Stage B-2 Data Models (Treatment #1.8.9)
# ============================================================================

@dataclass(frozen=True)
class StageB1ElementRealization:
    """
    Treatment #1.8.9: Concrete architectural realization for a single Stage A element.
    Contains NO source code. Bounded explicitly to:
    - obligation_id
    - semantic_identity
    - element_kind
    - target_artifact
    - architectural_representation (e.g. REST_CONTROLLER, CLI_HANDLER, DOMAIN_ENTITY, UI_WIDGET)
    """
    obligation_id: str
    semantic_identity: str
    element_kind: str
    target_artifact: str
    architectural_representation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "obligation_id": self.obligation_id,
            "semantic_identity": self.semantic_identity,
            "element_kind": self.element_kind,
            "target_artifact": self.target_artifact,
            "architectural_representation": self.architectural_representation,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> StageB1ElementRealization:
        return cls(
            obligation_id=str(data.get("obligation_id") or data.get("id") or "").strip(),
            semantic_identity=str(data.get("semantic_identity") or data.get("identity") or data.get("identifier") or "").strip(),
            element_kind=str(data.get("element_kind") or data.get("kind") or "").strip().upper(),
            target_artifact=str(data.get("target_artifact") or data.get("artifact") or data.get("target_file") or "").strip().replace("\\", "/"),
            architectural_representation=str(data.get("architectural_representation") or data.get("representation") or data.get("role") or "").strip()
        )


@dataclass
class StageB1Output:
    """Container for Stage B-1 output."""
    elements: List[StageB1ElementRealization] = field(default_factory=list)
    stage_a_revision_requests: List[StageARevisionRequest] = field(default_factory=list)
    raw_text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "elements": [e.to_dict() for e in self.elements],
            "stage_a_revision_requests": [r.to_dict() for r in self.stage_a_revision_requests],
            "raw_text": self.raw_text
        }


@dataclass(frozen=True)
class FrozenStageB1State:
    """Immutable sealed container for validated Stage B-1 state."""
    elements: Tuple[StageB1ElementRealization, ...]
    sha256_seal: str
    validated_at: str

    @classmethod
    def freeze(cls, elements: List[StageB1ElementRealization], timestamp: Optional[str] = None) -> FrozenStageB1State:
        from datetime import datetime
        ts = timestamp or datetime.now().isoformat()
        sorted_elements = sorted(elements, key=lambda e: e.obligation_id)
        raw_data = [e.to_dict() for e in sorted_elements]
        canonical_json = json.dumps(raw_data, sort_keys=True)
        seal = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
        return cls(
            elements=tuple(sorted_elements),
            sha256_seal=seal,
            validated_at=ts
        )

    def get_element(self, obligation_id: str) -> Optional[StageB1ElementRealization]:
        for e in self.elements:
            if e.obligation_id == obligation_id:
                return e
        return None

    def get_by_identity(self, identity: str) -> Optional[StageB1ElementRealization]:
        for e in self.elements:
            if e.semantic_identity == identity:
                return e
        return None

    def to_dict_list(self) -> List[Dict[str, Any]]:
        return [e.to_dict() for e in self.elements]


@dataclass
class StageB2BindingDecision:
    """
    Treatment #1.8.9: Relationship and binding decision for an architectural element.
    Defines how identified elements relate:
    - binding_id
    - source_identity (references a validated B1 element)
    - target_identity (target route, parent model, callable, or dependency)
    - relationship_type (BINDS_ROUTE, IMPLEMENTS_INTERFACE, CALLS_DELEGATE, USES_MODEL, EXPOSES_WIDGET)
    - target_artifact
    - signature_details (parameters, return type, HTTP method/path)
    """
    binding_id: str
    source_identity: str
    target_identity: str
    relationship_type: str
    target_artifact: str
    signature_details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "binding_id": self.binding_id,
            "source_identity": self.source_identity,
            "target_identity": self.target_identity,
            "relationship_type": self.relationship_type,
            "target_artifact": self.target_artifact,
            "signature_details": dict(self.signature_details)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> StageB2BindingDecision:
        b_id = str(data.get("binding_id") or data.get("id") or "").strip()
        src = str(data.get("source_identity") or data.get("source") or data.get("identifier") or "").strip()
        tgt = str(data.get("target_identity") or data.get("target") or data.get("route") or data.get("bound_to") or "").strip()
        rel = str(data.get("relationship_type") or data.get("relationship") or data.get("type") or "IMPLEMENTS_INTERFACE").strip().upper()
        art = str(data.get("target_artifact") or data.get("target_file") or data.get("artifact") or "").strip().replace("\\", "/")
        sig = data.get("signature_details") or data.get("signature") or {}
        if not isinstance(sig, dict):
            sig = {}
        if "parameters" in data and "parameters" not in sig:
            sig["parameters"] = data["parameters"]
        if "return_semantics" in data and "return_semantics" not in sig:
            sig["return_semantics"] = data["return_semantics"]
        elif "return" in data and "return" not in sig:
            sig["return"] = data["return"]
        if "route" in data and "route" not in sig:
            sig["route"] = data["route"]
        if "http_method" in data and "http_method" not in sig:
            sig["http_method"] = data["http_method"]
        elif "method" in data and "method" not in sig:
            sig["method"] = data["method"]

        return cls(
            binding_id=b_id,
            source_identity=src,
            target_identity=tgt,
            relationship_type=rel,
            target_artifact=art,
            signature_details=sig
        )


@dataclass
class StageB2Output:
    """Container for Stage B-2 output."""
    bindings: List[StageB2BindingDecision] = field(default_factory=list)
    scaffold_files: Dict[str, str] = field(default_factory=dict)
    stage_a_revision_requests: List[StageARevisionRequest] = field(default_factory=list)
    raw_text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bindings": [b.to_dict() for b in self.bindings],
            "scaffold_files": dict(self.scaffold_files),
            "stage_a_revision_requests": [r.to_dict() for r in self.stage_a_revision_requests],
            "raw_text": self.raw_text
        }


@dataclass(frozen=True)
class FrozenStageB2State:
    """Immutable sealed container for validated Stage B-2 state."""
    bindings: Tuple[StageB2BindingDecision, ...]
    scaffold_files: Tuple[Tuple[str, str], ...]
    sha256_seal: str
    validated_at: str

    @classmethod
    def freeze(cls, bindings: List[StageB2BindingDecision], scaffold_files: Dict[str, str], timestamp: Optional[str] = None) -> FrozenStageB2State:
        from datetime import datetime
        ts = timestamp or datetime.now().isoformat()
        sorted_bindings = sorted(bindings, key=lambda b: (b.source_identity, b.binding_id))
        raw_b = [b.to_dict() for b in sorted_bindings]
        sorted_files = sorted(list(scaffold_files.items()), key=lambda x: x[0])
        payload = {"bindings": raw_b, "files": sorted_files}
        canonical_json = json.dumps(payload, sort_keys=True)
        seal = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
        return cls(
            bindings=tuple(sorted_bindings),
            scaffold_files=tuple(sorted_files),
            sha256_seal=seal,
            validated_at=ts
        )

    def to_dict_list(self) -> List[Dict[str, Any]]:
        return [b.to_dict() for b in self.bindings]



# ============================================================================
# 2. Pure Python Deterministic Stage-A Check
# ============================================================================

def parse_stage_a_mappings(text: str) -> Tuple[Optional[List[StageAObligationMapping]], List[str]]:
    """
    Parses Stage A obligation mapping output from LLM response text.
    Accepts text inside === STAGE A: OBLIGATION MAPPING === ... === END STAGE A ===
    or raw JSON fallback containing obligation_mappings array.
    """
    errors = []
    if not text or not str(text).strip():
        return None, ["EMPTY_STAGE_A_RESPONSE: Architect produced no output for Stage A."]

    json_str = None
    marker_match = re.search(
        r"===\s*STAGE A(?::\s*OBLIGATION MAPPING)?\s*===\s*([\s\S]*?)\s*===\s*END STAGE A\s*===",
        text,
        re.IGNORECASE
    )
    if marker_match:
        json_str = marker_match.group(1).strip()
    else:
        code_block = re.search(r"```(?:json)?\s*(\{[\s\S]*?\"obligation_mappings\"[\s\S]*?\})\s*```", text, re.IGNORECASE)
        if code_block:
            json_str = code_block.group(1).strip()
        else:
            raw_match = re.search(r"(\{[\s\S]*?\"obligation_mappings\"[\s\S]*?\})", text)
            if raw_match:
                json_str = raw_match.group(1).strip()

    if not json_str:
        return None, ["STAGE_A_MARKER_MISSING: Could not find '=== STAGE A: OBLIGATION MAPPING ===' or 'obligation_mappings' JSON block."]

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        return None, [f"STAGE_A_JSON_PARSE_ERROR: Invalid JSON in Stage A output: {e}"]

    if not isinstance(data, dict):
        return None, ["STAGE_A_STRUCTURE_ERROR: Stage A root must be a JSON object."]

    raw_mappings = data.get("obligation_mappings")
    if raw_mappings is None:
        raw_mappings = data.get("mappings")
    if not isinstance(raw_mappings, list):
        return None, ["STAGE_A_SCHEMA_ERROR: 'obligation_mappings' must be a list of mapping objects."]

    parsed = []
    for idx, item in enumerate(raw_mappings, 1):
        if not isinstance(item, dict):
            errors.append(f"STAGE_A_ITEM_ERROR: Item #{idx} in obligation_mappings is not a dict.")
            continue
        try:
            m = StageAObligationMapping.from_dict(item)
            parsed.append(m)
        except Exception as ex:
            errors.append(f"STAGE_A_MAPPING_DESERIALIZATION_ERROR: Failed to parse item #{idx}: {ex}")

    if errors:
        return None, errors

    return parsed, []


def validate_stage_a_mappings(
    mappings: List[StageAObligationMapping],
    authoritative_obligations: List[Any]
) -> Tuple[bool, List[str]]:
    """
    Pure Python Deterministic Stage-A Check.
    Checks:
    1. obligation coverage (100% of authoritative obligations covered)
    2. duplicate mapping (no conflicting/contradictory mappings for same obligation_id)
    3. missing mapping (uncovered obligations detected)
    4. unresolved mapping (missing semantic_identity or semantic_target_artifact or invalid kind)
    5. contradictory mapping (conflicting types or identities for same element)
    6. required semantic fields (obligation_id, semantic_element, element_kind, semantic_identity, semantic_target_artifact, semantic_parameters, semantic_return)
    7. no obligation invention (cannot invent obligation_ids not in authoritative ledger)

    PYTHON NEVER FIXES THE MAPPING. Returns (is_valid, errors).
    """
    errors: List[str] = []
    if not mappings:
        return False, ["STAGE_A_EMPTY_MAPPINGS: No obligation mappings provided."]

    auth_ids: Set[str] = set()
    for item in authoritative_obligations:
        if isinstance(item, str):
            auth_ids.add(item.strip())
        elif isinstance(item, dict):
            oid = item.get("obligation_id") or item.get("id")
            if oid:
                auth_ids.add(str(oid).strip())
        elif hasattr(item, "obligation_id"):
            auth_ids.add(str(getattr(item, "obligation_id")).strip())

    mapped_obligations: Dict[str, List[StageAObligationMapping]] = {}
    seen_elements: Dict[str, StageAObligationMapping] = {}

    for idx, m in enumerate(mappings, 1):
        if not m.obligation_id:
            errors.append(f"STAGE_A_MISSING_FIELD: Mapping #{idx} is missing required 'obligation_id'.")
            continue
        if not m.semantic_element:
            errors.append(f"STAGE_A_MISSING_FIELD: Obligation '{m.obligation_id}' is missing 'semantic_element'.")
        if not m.element_kind:
            errors.append(f"STAGE_A_MISSING_FIELD: Obligation '{m.obligation_id}' is missing 'element_kind'.")
        elif m.element_kind.upper() not in VALID_ELEMENT_KINDS:
            errors.append(
                f"STAGE_A_INVALID_KIND: Obligation '{m.obligation_id}' specifies invalid element_kind '{m.element_kind}'. "
                f"Valid kinds are: {sorted(list(VALID_ELEMENT_KINDS))}."
            )
        if not m.semantic_identity:
            errors.append(f"STAGE_A_UNRESOLVED_IDENTITY: Obligation '{m.obligation_id}' has empty 'semantic_identity'.")
        if not m.semantic_target_artifact:
            errors.append(f"STAGE_A_UNRESOLVED_ARTIFACT: Obligation '{m.obligation_id}' has empty 'semantic_target_artifact'.")

        if auth_ids and (m.obligation_id not in auth_ids):
            errors.append(
                f"STAGE_A_INVENTED_OBLIGATION: Obligation ID '{m.obligation_id}' does not exist in authoritative obligations: {sorted(list(auth_ids))}."
            )

        if m.obligation_id not in mapped_obligations:
            mapped_obligations[m.obligation_id] = []
        mapped_obligations[m.obligation_id].append(m)

        if m.semantic_identity:
            if m.semantic_identity in seen_elements:
                prev = seen_elements[m.semantic_identity]
                if prev.element_kind.upper() != m.element_kind.upper():
                    errors.append(
                        f"STAGE_A_CONTRADICTORY_MAPPING: Symbol '{m.semantic_identity}' declared as '{m.element_kind}' in '{m.obligation_id}' "
                        f"contradicts previous declaration as '{prev.element_kind}' in '{prev.obligation_id}'."
                    )
                if prev.semantic_target_artifact != m.semantic_target_artifact:
                    errors.append(
                        f"STAGE_A_CONTRADICTORY_MAPPING: Symbol '{m.semantic_identity}' assigned to multiple target files: "
                        f"'{prev.semantic_target_artifact}' vs '{m.semantic_target_artifact}'."
                    )
            else:
                seen_elements[m.semantic_identity] = m

    for oid, maps in mapped_obligations.items():
        if len(maps) > 1:
            first = maps[0]
            for later in maps[1:]:
                if (first.semantic_identity != later.semantic_identity or
                        first.element_kind.upper() != later.element_kind.upper() or
                        first.semantic_target_artifact != later.semantic_target_artifact):
                    errors.append(
                        f"STAGE_A_DUPLICATE_CONFLICT: Obligation '{oid}' is mapped {len(maps)} times with conflicting identities/kinds/files: "
                        f"'{first.semantic_identity}' vs '{later.semantic_identity}'."
                    )

    if auth_ids:
        covered = set(mapped_obligations.keys())
        missing = auth_ids - covered
        if missing:
            errors.append(
                f"STAGE_A_MISSING_OBLIGATIONS: The following mandatory acceptance obligations are unmapped: {sorted(list(missing))}."
            )

    is_valid = len(errors) == 0
    return is_valid, errors


# ============================================================================
# 3. Stage B Output Parsing & Preservation Invariant Gate
# ============================================================================

def extract_stage_b_scaffold_payload(text: str) -> Dict[str, str]:
    """
    Deterministically extracts raw file scaffold artifacts from Stage B output.
    Treatment #1.8.8: Separates raw source code from JSON architectural decisions.
    
    Supports:
    1. === FILE: <path> === ... === END FILE ===
    2. === ARTIFACT: <path> === ... === END ARTIFACT ===
    3. Sections enclosed in === STAGE B: SCAFFOLD ARTIFACTS === ... === END STAGE B SCAFFOLD ===
    4. Markdown code blocks specifying file path e.g. ```python file=main.py ... ```
    
    Guarantees 100% character/byte preservation (quotes, newlines, docstrings, braces).
    """
    files: Dict[str, str] = {}
    if not text or not str(text).strip():
        return files

    clean_text = text.replace("\r\n", "\n")

    # Pattern 1: === FILE: <path> === ... === END FILE === or === ARTIFACT: <path> === ... === END ARTIFACT ===
    file_pattern = re.compile(
        r"===\s*(?:FILE|ARTIFACT):\s*([^\n=]+?)\s*===\s*\n([\s\S]*?)(?:\n\s*===\s*END\s+(?:FILE|ARTIFACT)\s*===|(?=\n\s*===\s*(?:FILE|ARTIFACT))|\Z)",
        re.IGNORECASE
    )
    for m in file_pattern.finditer(clean_text):
        fpath = m.group(1).strip().replace("\\", "/")
        code = m.group(2).rstrip()
        if fpath:
            files[fpath] = code

    # Pattern 2: Nested inside === STAGE B: SCAFFOLD ARTIFACTS === ... === END STAGE B SCAFFOLDS ===
    scaffold_section_m = re.search(
        r"===\s*STAGE B:\s*SCAFFOLD ARTIFACTS\s*===\s*\n([\s\S]*?)(?:\n\s*===\s*END STAGE B SCAFFOLDS?\s*===|\Z)",
        clean_text,
        re.IGNORECASE
    )
    if scaffold_section_m:
        inner = scaffold_section_m.group(1)
        for m in file_pattern.finditer(inner):
            fpath = m.group(1).strip().replace("\\", "/")
            code = m.group(2).rstrip()
            if fpath:
                files[fpath] = code
        
        # If no === FILE: === blocks were found inside the section, check for labeled markdown code blocks
        if not files:
            md_blocks = re.finditer(
                r"```(?:[a-zA-Z0-9_\-]+)?\s*(?:(?:file|path)=([^\n\r]+))?\n([\s\S]*?)\n```",
                inner
            )
            for mb in md_blocks:
                fpath_tag = mb.group(1)
                code_content = mb.group(2)
                if fpath_tag and fpath_tag.strip():
                    fpath = fpath_tag.strip().replace("\\", "/")
                    files[fpath] = code_content
                else:
                    lines = code_content.splitlines()
                    if lines:
                        first_line = lines[0].strip()
                        comment_m = re.match(r"^(?:#|//|/\*)\s*([a-zA-Z0-9_\-./]+\.[a-zA-Z0-9]+)", first_line)
                        if comment_m:
                            fpath = comment_m.group(1).replace("\\", "/")
                            files[fpath] = code_content

    return files


def parse_stage_b_assembly(text: str) -> Tuple[Optional[StageBAssemblyOutput], List[str]]:
    """
    Parses Stage B architectural assembly output from LLM response text.
    Treatment #1.8.8: Supports decoupled representation:
    - Decisions: === STAGE B: ARCHITECTURAL DECISIONS === ... === END STAGE B DECISIONS ===
    - Scaffolds: === STAGE B: SCAFFOLD ARTIFACTS === (or === FILE: ... === blocks)
    Also supports backward compatibility with legacy === STAGE B: ARCHITECTURAL ASSEMBLY ===.
    """
    errors = []
    if not text or not str(text).strip():
        return None, ["EMPTY_STAGE_B_RESPONSE: Architect produced no output for Stage B."]

    json_str = None
    is_decoupled = False

    # Priority 1: Decoupled decisions marker
    decisions_match = re.search(
        r"===\s*STAGE B:\s*ARCHITECTURAL DECISIONS\s*===\s*([\s\S]*?)\s*===\s*END STAGE B DECISIONS\s*===",
        text,
        re.IGNORECASE
    )
    if decisions_match:
        json_str = decisions_match.group(1).strip()
        is_decoupled = True
    else:
        # Priority 2: Legacy assembly marker
        marker_match = re.search(
            r"===\s*STAGE B(?::\s*ARCHITECTURAL ASSEMBLY)?\s*===\s*([\s\S]*?)\s*===\s*END STAGE B\s*===",
            text,
            re.IGNORECASE
        )
        if marker_match:
            json_str = marker_match.group(1).strip()
        else:
            # Priority 3: Fallback semantic decision block
            sem_match = re.search(
                r"===\s*SEMANTIC DECISION JSON\s*===\s*([\s\S]*?)\s*===\s*END SEMANTIC DECISION JSON\s*===",
                text,
                re.IGNORECASE
            )
            if sem_match:
                json_str = sem_match.group(1).strip()
            else:
                code_block = re.search(r"```(?:json)?\s*(\{[\s\S]*?\"semantic_decisions\"[\s\S]*?\})\s*```", text, re.IGNORECASE)
                if code_block:
                    json_str = code_block.group(1).strip()
                else:
                    raw_match = re.search(r"(\{[\s\S]*?\"semantic_decisions\"[\s\S]*?\})", text)
                    if raw_match:
                        json_str = raw_match.group(1).strip()

    if not json_str:
        return None, ["STAGE_B_MARKER_MISSING: Could not find '=== STAGE B: ARCHITECTURAL DECISIONS ===' or '=== STAGE B: ARCHITECTURAL ASSEMBLY ===' block."]

    # Extract raw scaffold payload (Decoupled representation)
    raw_scaffold_files = extract_stage_b_scaffold_payload(text)
    if raw_scaffold_files:
        is_decoupled = True

    data, decode_err, telem = decode_canonical_architectural_json(json_str, stage="STAGE_B")
    if decode_err or data is None:
        return None, [f"STAGE_B_JSON_PARSE_ERROR: Invalid JSON in Stage B output: {decode_err}"]

    tgt_file = str(data.get("target_file") or data.get("authoritative_target_file") or "").strip().replace("\\", "/")
    json_scaffold = str(data.get("scaffold_code") or data.get("scaffold") or data.get("code_scaffold") or "")
    files_raw = data.get("files") or {}
    files_dict: Dict[str, str] = {}

    # 1. Populate from JSON if present (legacy fallback)
    if isinstance(files_raw, dict):
        for k, v in files_raw.items():
            k_norm = str(k).strip().replace("\\", "/")
            if isinstance(v, dict):
                code = str(v.get("scaffold_code") or v.get("code") or "")
            else:
                code = str(v)
            files_dict[k_norm] = code

    if tgt_file and json_scaffold and tgt_file not in files_dict:
        files_dict[tgt_file] = json_scaffold

    # 2. Overlay with raw scaffold files (Decoupled priority: raw text unescaped files take precedence)
    for k, v in raw_scaffold_files.items():
        files_dict[k] = v

    if not tgt_file and files_dict:
        tgt_file = next(iter(files_dict.keys()))

    scaffold = files_dict.get(tgt_file, "")
    if not scaffold and files_dict:
        scaffold = next(iter(files_dict.values()))

    raw_decisions = data.get("semantic_decisions") or data.get("decisions") or []
    if not isinstance(raw_decisions, list):
        return None, ["STAGE_B_SCHEMA_ERROR: 'semantic_decisions' must be a list."]

    decisions = []
    for idx, d in enumerate(raw_decisions, 1):
        if not isinstance(d, dict):
            errors.append(f"STAGE_B_DECISION_ERROR: Item #{idx} is not a dict.")
            continue
        try:
            dec = SemanticArchitecturalDecision.from_dict(d)
            if not dec.target_file and tgt_file:
                dec.target_file = tgt_file
            decisions.append(dec)
        except Exception as ex:
            errors.append(f"STAGE_B_DECISION_PARSE_ERROR: Failed to parse decision #{idx}: {ex}")

    rev_requests = []
    raw_revs = data.get("stage_a_revision_requests") or data.get("revision_requests") or []
    if isinstance(raw_revs, list):
        for r in raw_revs:
            if isinstance(r, dict):
                rev_requests.append(StageARevisionRequest.from_dict(r))

    if errors:
        return None, errors

    assembly = StageBAssemblyOutput(
        target_file=tgt_file,
        files=files_dict,
        scaffold_code=scaffold,
        semantic_decisions=decisions,
        stage_a_revision_requests=rev_requests,
        raw_text=text,
        decoder_telemetry=telem,
        is_decoupled=is_decoupled
    )
    return assembly, []


def validate_stage_b_preservation(
    frozen_stage_a: FrozenStageAMappings,
    assembly: StageBAssemblyOutput
) -> Tuple[bool, List[str], List[StageARevisionRequest]]:
    """
    CRITICAL PRESERVATION INVARIANT GATE (Pure Python).
    Verifies that Stage B preserved all validated mappings from Stage A without:
    - silent renaming of semantic_identity
    - deletion of mapped obligations
    - reinterpretation of element_kind / target_structure
    - relocation of target artifact without revision
    - duplication of contradictory decisions
    """
    errors: List[str] = []
    
    if assembly.stage_a_revision_requests:
        reasons = [
            f"REVISION_REQUEST: Obligation '{r.obligation_id}' requested revision: {r.reason}"
            for r in assembly.stage_a_revision_requests
        ]
        return False, reasons, assembly.stage_a_revision_requests

    if not assembly.target_file:
        errors.append("STAGE_B_MISSING_TARGET_FILE: Stage B must specify an authoritative 'target_file'.")
    if not assembly.scaffold_code and not assembly.files:
        errors.append("STAGE_B_MISSING_SCAFFOLD: Stage B must provide concrete 'scaffold_code' or 'files' dictionary.")

    b_decisions_by_ob: Dict[str, List[SemanticArchitecturalDecision]] = {}
    for d in assembly.semantic_decisions:
        if not d.obligation_id:
            errors.append(f"STAGE_B_DECISION_MISSING_OBLIGATION: Decision for '{d.identifier}' is missing 'obligation_id'.")
            continue
        if d.obligation_id not in b_decisions_by_ob:
            b_decisions_by_ob[d.obligation_id] = []
        b_decisions_by_ob[d.obligation_id].append(d)

    for a_map in frozen_stage_a.mappings:
        ob_id = a_map.obligation_id
        if ob_id not in b_decisions_by_ob:
            errors.append(
                f"STAGE_B_SILENT_DELETION: Obligation '{ob_id}' (identity: '{a_map.semantic_identity}') was validated in Stage A "
                f"but is completely missing from Stage B assembly."
            )
            continue

        b_decs = b_decisions_by_ob[ob_id]
        if len(b_decs) > 1:
            errors.append(
                f"STAGE_B_DUPLICATE_DECISION: Obligation '{ob_id}' has {len(b_decs)} decisions in Stage B. Must be 1-to-1."
            )

        matched_identity = any(d.identifier == a_map.semantic_identity for d in b_decs)
        if not matched_identity:
            actual_idents = [d.identifier for d in b_decs]
            errors.append(
                f"STAGE_B_SILENT_RENAMING: Obligation '{ob_id}' identity was validated as '{a_map.semantic_identity}' in Stage A, "
                f"but Stage B renamed it to {actual_idents}. Silent renaming is forbidden."
            )

        if a_map.semantic_target_artifact:
            matched_artifact = any(
                d.target_file.replace("\\", "/") == a_map.semantic_target_artifact.replace("\\", "/")
                for d in b_decs
            )
            if not matched_artifact:
                actual_files = [d.target_file for d in b_decs]
                errors.append(
                    f"STAGE_B_SILENT_RELOCATION: Obligation '{ob_id}' target artifact was validated as '{a_map.semantic_target_artifact}' in Stage A, "
                    f"but Stage B placed it in {actual_files}."
                )

        expected_struct = "DATA_MODEL" if a_map.element_kind.upper() in ("DATA_MODEL", "MODEL", "SCHEMA", "ENTITY") else "INTERFACE_CONTRACT"
        for d in b_decs:
            if d.target_structure != expected_struct:
                errors.append(
                    f"STAGE_B_SILENT_REINTERPRETATION: Obligation '{ob_id}' structure was validated as '{expected_struct}' ({a_map.element_kind}) in Stage A, "
                    f"but Stage B declared target_structure as '{d.target_structure}'."
                )

    is_valid = len(errors) == 0
    return is_valid, errors, []


# ============================================================================
# 4. Conversion to SemanticArchitecturalPlan for Serializer #1.8.5
# ============================================================================

def convert_stage_b_to_semantic_plan(
    frozen_stage_a: FrozenStageAMappings,
    assembly: StageBAssemblyOutput,
    task_id: str = "default_task",
    target_language: str = "python"
) -> Tuple[Optional[SemanticArchitecturalPlan], List[str]]:
    """
    Transforms validated Stage B assembly output and locked Stage A state
    into canonical SemanticArchitecturalPlan ready for Treatment #1.8.5 serializer.
    """
    if not assembly or not assembly.semantic_decisions:
        return None, ["CONVERT_EMPTY_ASSEMBLY: Stage B has no decisions to serialize."]

    files_map = dict(assembly.files)
    if assembly.target_file and assembly.scaffold_code and assembly.target_file not in files_map:
        files_map[assembly.target_file] = assembly.scaffold_code

    plan = SemanticArchitecturalPlan(
        target_file=assembly.target_file,
        semantic_decisions=list(assembly.semantic_decisions),
        scaffold_code=assembly.scaffold_code,
        files=files_map,
        unresolved_obligations=[],
        task_id=task_id,
        target_language=target_language,
        summary=f"Staged architectural assembly synthesized from Stage A seal {frozen_stage_a.sha256_seal[:12]}."
    )
    return plan, []


def assemble_stage_b_blueprint(
    frozen_stage_a: FrozenStageAMappings,
    assembly: StageBAssemblyOutput,
    task_id: str = "default_task",
    target_language: str = "python"
) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    """
    Treatment #1.8.8: Deterministic Python assembly of Stage B output into canonical Blueprint.
    1. Validates Stage B preservation invariants against sealed Stage A.
    2. Enforces non-empty target_file and scaffold code.
    3. Converts to SemanticArchitecturalPlan.
    4. Serializes to canonical Blueprint via Treatment #1.8.5 serializer.
    """
    if not assembly:
        return None, ["STAGE_B_ASSEMBLY_EMPTY: No Stage B assembly output provided."]

    valid, pres_errs, rev_reqs = validate_stage_b_preservation(frozen_stage_a, assembly)
    if not valid:
        return None, pres_errs

    plan, conv_errs = convert_stage_b_to_semantic_plan(
        frozen_stage_a=frozen_stage_a,
        assembly=assembly,
        task_id=task_id,
        target_language=target_language
    )
    if not plan or conv_errs:
        return None, conv_errs or ["STAGE_B_CONVERSION_ERROR: Failed to convert assembly to semantic plan."]

    if serialize_semantic_decision_to_blueprint is None:
        return None, ["SERIALIZER_NOT_AVAILABLE: serialize_semantic_decision_to_blueprint is not imported."]

    blueprint, ser_errs = serialize_semantic_decision_to_blueprint(plan)
    if not blueprint or ser_errs:
        return None, ser_errs or ["STAGE_B_SERIALIZATION_ERROR: Failed to serialize semantic plan to blueprint."]

    return blueprint, []


# ============================================================================
# 4B. Decomposed Stage B Engine (Treatment #1.8.9)
# ============================================================================

def parse_stage_b1_output(text: str) -> Tuple[Optional[StageB1Output], List[str]]:
    """
    Parses Stage B-1 Element Realization output from LLM response text.
    Extracts text inside === STAGE B-1: ELEMENT REALIZATION === ... === END STAGE B-1 ===
    or fallback === STAGE B1: ELEMENT REALIZATION ===.
    """
    if not text or not str(text).strip():
        return None, ["EMPTY_STAGE_B1_RESPONSE: Architect produced no output for Stage B-1."]

    json_str = None
    marker_match = re.search(
        r"===\s*STAGE B-?1(?::\s*ELEMENT REALIZATION)?\s*===\s*([\s\S]*?)\s*===\s*END STAGE B-?1\s*===",
        text,
        re.IGNORECASE
    )
    if marker_match:
        json_str = marker_match.group(1).strip()
    else:
        code_block = re.search(r"```(?:json)?\s*(\{[\s\S]*?\"(?:elements|element_realizations)\"[\s\S]*?\})\s*```", text, re.IGNORECASE)
        if code_block:
            json_str = code_block.group(1).strip()
        else:
            raw_match = re.search(r"(\{[\s\S]*?\"(?:elements|element_realizations)\"[\s\S]*?\})", text)
            if raw_match:
                json_str = raw_match.group(1).strip()

    if not json_str:
        return None, ["STAGE_B1_MARKER_MISSING: Could not find '=== STAGE B-1: ELEMENT REALIZATION ===' block."]

    data, decode_err, _ = decode_canonical_architectural_json(json_str, stage="STAGE_B1")
    if decode_err or data is None:
        return None, [f"STAGE_B1_JSON_PARSE_ERROR: Invalid JSON in Stage B-1 output: {decode_err}"]

    raw_elements = data.get("element_realizations") or data.get("elements") or []
    if not isinstance(raw_elements, list):
        return None, ["STAGE_B1_SCHEMA_ERROR: 'element_realizations' or 'elements' must be a list."]

    elements = []
    errors = []
    for idx, item in enumerate(raw_elements, 1):
        if not isinstance(item, dict):
            errors.append(f"STAGE_B1_ITEM_ERROR: Item #{idx} in elements is not a dict.")
            continue
        try:
            elem = StageB1ElementRealization.from_dict(item)
            elements.append(elem)
        except Exception as ex:
            errors.append(f"STAGE_B1_DESERIALIZATION_ERROR: Failed to parse item #{idx}: {ex}")

    rev_requests = []
    raw_revs = data.get("stage_a_revision_requests") or []
    if isinstance(raw_revs, list):
        for r in raw_revs:
            if isinstance(r, dict):
                rev_requests.append(StageARevisionRequest.from_dict(r))

    if errors:
        return None, errors

    return StageB1Output(elements=elements, stage_a_revision_requests=rev_requests, raw_text=text), []


def validate_stage_b1_realization(
    frozen_stage_a: FrozenStageAMappings,
    b1_output: StageB1Output
) -> Tuple[bool, List[str]]:
    """
    Pure Python Deterministic Stage B-1 Check (Treatment #1.8.9).
    Verifies:
    1. Every required Stage A obligation is represented in B1 (no silent deletion).
    2. No element is duplicated.
    3. No element is silently renamed (semantic_identity must match Stage A).
    4. No unauthorized element is invented.
    5. Element kind is valid and compatible with Stage A.
    6. Target artifact matches Stage A target artifact (no silent relocation).
    7. Explicit architectural_representation is provided.
    
    PYTHON NEVER FIXES THE REALIZATION. Returns (is_valid, errors).
    """
    errors: List[str] = []
    if not b1_output or not b1_output.elements:
        return False, ["STAGE_B1_EMPTY_ELEMENTS: Stage B-1 produced no element realizations."]

    if not frozen_stage_a or not frozen_stage_a.mappings:
        return False, ["STAGE_B1_MISSING_STAGE_A: No frozen Stage A mappings provided to validate against."]

    stage_a_by_id: Dict[str, StageAObligationMapping] = {m.obligation_id: m for m in frozen_stage_a.mappings}
    stage_a_ids: Set[str] = set(stage_a_by_id.keys())
    
    b1_by_id: Dict[str, List[StageB1ElementRealization]] = {}
    b1_seen_identities: Dict[str, StageB1ElementRealization] = {}

    for idx, elem in enumerate(b1_output.elements, 1):
        if not elem.obligation_id:
            errors.append(f"STAGE_B1_MISSING_FIELD: Element #{idx} is missing required 'obligation_id'.")
            continue

        ob_id = elem.obligation_id
        if ob_id not in stage_a_ids:
            errors.append(
                f"STAGE_B1_INVENTED_ELEMENT: Obligation ID '{ob_id}' does not exist in validated Stage A mappings: {sorted(list(stage_a_ids))}."
            )
            continue

        a_map = stage_a_by_id[ob_id]

        if not elem.semantic_identity:
            errors.append(f"STAGE_B1_UNRESOLVED_IDENTITY: Element for obligation '{ob_id}' has empty 'semantic_identity'.")
        elif elem.semantic_identity != a_map.semantic_identity:
            errors.append(
                f"STAGE_B1_SILENT_RENAMING: Obligation '{ob_id}' identity was validated as '{a_map.semantic_identity}' in Stage A, "
                f"but Stage B-1 renamed it to '{elem.semantic_identity}'. Silent renaming is forbidden."
            )

        if not elem.element_kind:
            errors.append(f"STAGE_B1_MISSING_FIELD: Obligation '{ob_id}' is missing 'element_kind'.")
        elif elem.element_kind.upper() not in VALID_ELEMENT_KINDS:
            errors.append(
                f"STAGE_B1_INVALID_KIND: Obligation '{ob_id}' specifies invalid element_kind '{elem.element_kind}'."
            )
        else:
            expected_struct = "DATA_MODEL" if a_map.element_kind.upper() in ("DATA_MODEL", "MODEL", "SCHEMA", "ENTITY") else "CALLABLE"
            actual_struct = "DATA_MODEL" if elem.element_kind.upper() in ("DATA_MODEL", "MODEL", "SCHEMA", "ENTITY") else "CALLABLE"
            if expected_struct != actual_struct:
                errors.append(
                    f"STAGE_B1_CONTRADICTORY_KIND: Obligation '{ob_id}' was declared as '{a_map.element_kind}' in Stage A, "
                    f"which contradicts B-1 declaration '{elem.element_kind}'."
                )

        if not elem.target_artifact:
            errors.append(f"STAGE_B1_UNRESOLVED_ARTIFACT: Obligation '{ob_id}' has empty 'target_artifact'.")
        elif a_map.semantic_target_artifact:
            norm_b1 = elem.target_artifact.replace("\\", "/")
            norm_a = a_map.semantic_target_artifact.replace("\\", "/")
            if norm_b1 != norm_a:
                errors.append(
                    f"STAGE_B1_SILENT_RELOCATION: Obligation '{ob_id}' target artifact was validated as '{norm_a}' in Stage A, "
                    f"but Stage B-1 relocated it to '{norm_b1}'."
                )

        if not elem.architectural_representation:
            errors.append(
                f"STAGE_B1_MISSING_REPRESENTATION: Obligation '{ob_id}' must specify an explicit 'architectural_representation' "
                f"(e.g., REST_CONTROLLER, CLI_HANDLER, DOMAIN_ENTITY, UI_WIDGET)."
            )

        if ob_id not in b1_by_id:
            b1_by_id[ob_id] = []
        b1_by_id[ob_id].append(elem)

        if elem.semantic_identity:
            if elem.semantic_identity in b1_seen_identities:
                prev = b1_seen_identities[elem.semantic_identity]
                if prev.obligation_id != ob_id:
                    errors.append(
                        f"STAGE_B1_DUPLICATE_IDENTITY: Symbol '{elem.semantic_identity}' is mapped to multiple obligations: "
                        f"'{prev.obligation_id}' and '{ob_id}'."
                    )
            else:
                b1_seen_identities[elem.semantic_identity] = elem

    for ob_id, elems in b1_by_id.items():
        if len(elems) > 1:
            errors.append(
                f"STAGE_B1_DUPLICATE_ELEMENT: Obligation '{ob_id}' has {len(elems)} realizations in Stage B-1. Must be exactly 1-to-1."
            )

    covered_ids = set(b1_by_id.keys())
    missing = stage_a_ids - covered_ids
    if missing:
        for m_id in sorted(list(missing)):
            a_map = stage_a_by_id[m_id]
            errors.append(
                f"STAGE_B1_SILENT_DELETION: Obligation '{m_id}' (identity: '{a_map.semantic_identity}') was validated in Stage A "
                f"but is missing from Stage B-1 realization."
            )

    is_valid = len(errors) == 0
    return is_valid, errors


def parse_stage_b2_output(text: str) -> Tuple[Optional[StageB2Output], List[str]]:
    """
    Parses Stage B-2 Relationship / Binding output from LLM response text.
    Extracts text inside === STAGE B-2: RELATIONSHIP BINDINGS === ... === END STAGE B-2 ===
    and raw decoupled scaffold blocks inside === STAGE B: SCAFFOLD ARTIFACTS ===.
    """
    if not text or not str(text).strip():
        return None, ["EMPTY_STAGE_B2_RESPONSE: Architect produced no output for Stage B-2."]

    json_str = None
    marker_match = re.search(
        r"===\s*STAGE B-?2(?::\s*(?:RELATIONSHIP BINDINGS|BINDINGS))?\s*===\s*([\s\S]*?)\s*===\s*END STAGE B-?2\s*===",
        text,
        re.IGNORECASE
    )
    if marker_match:
        json_str = marker_match.group(1).strip()
    else:
        code_block = re.search(r"```(?:json)?\s*(\{[\s\S]*?\"bindings\"[\s\S]*?\})\s*```", text, re.IGNORECASE)
        if code_block:
            json_str = code_block.group(1).strip()
        else:
            raw_match = re.search(r"(\{[\s\S]*?\"bindings\"[\s\S]*?\})", text)
            if raw_match:
                json_str = raw_match.group(1).strip()

    if not json_str:
        fb_match = re.search(
            r"===\s*STAGE B:\s*ARCHITECTURAL DECISIONS\s*===\s*([\s\S]*?)\s*===\s*END STAGE B DECISIONS\s*===",
            text,
            re.IGNORECASE
        )
        if fb_match:
            json_str = fb_match.group(1).strip()

    if not json_str:
        return None, ["STAGE_B2_MARKER_MISSING: Could not find '=== STAGE B-2: RELATIONSHIP BINDINGS ===' block."]

    scaffold_files = extract_stage_b_scaffold_payload(text)

    data, decode_err, _ = decode_canonical_architectural_json(json_str, stage="STAGE_B2")
    if decode_err or data is None:
        return None, [f"STAGE_B2_JSON_PARSE_ERROR: Invalid JSON in Stage B-2 output: {decode_err}"]

    raw_bindings = data.get("bindings") or data.get("relationship_bindings") or []
    if not raw_bindings and ("semantic_decisions" in data or "decisions" in data):
        raw_decisions = data.get("semantic_decisions") or data.get("decisions") or []
        if isinstance(raw_decisions, list):
            for idx, d in enumerate(raw_decisions, 1):
                if isinstance(d, dict):
                    raw_bindings.append({
                        "binding_id": f"BIND-{idx:02d}",
                        "source_identity": d.get("identifier", ""),
                        "target_identity": d.get("route") or d.get("target_file", ""),
                        "relationship_type": "BINDS_ROUTE" if d.get("route") else "IMPLEMENTS_INTERFACE",
                        "target_artifact": d.get("target_file", ""),
                        "signature_details": {
                            "parameters": d.get("parameters", []),
                            "return_semantics": d.get("return_semantics", {}),
                            "route": d.get("route"),
                            "http_method": d.get("http_method")
                        }
                    })

    if not isinstance(raw_bindings, list):
        return None, ["STAGE_B2_SCHEMA_ERROR: 'bindings' must be a list."]

    bindings = []
    errors = []
    for idx, item in enumerate(raw_bindings, 1):
        if not isinstance(item, dict):
            errors.append(f"STAGE_B2_ITEM_ERROR: Item #{idx} in bindings is not a dict.")
            continue
        try:
            b = StageB2BindingDecision.from_dict(item)
            bindings.append(b)
        except Exception as ex:
            errors.append(f"STAGE_B2_DESERIALIZATION_ERROR: Failed to parse item #{idx}: {ex}")

    json_files = data.get("files") or {}
    if isinstance(json_files, dict):
        for k, v in json_files.items():
            k_norm = str(k).strip().replace("\\", "/")
            if k_norm not in scaffold_files:
                scaffold_files[k_norm] = str(v)

    rev_requests = []
    raw_revs = data.get("stage_a_revision_requests") or []
    if isinstance(raw_revs, list):
        for r in raw_revs:
            if isinstance(r, dict):
                rev_requests.append(StageARevisionRequest.from_dict(r))

    if errors:
        return None, errors

    return StageB2Output(bindings=bindings, scaffold_files=scaffold_files, stage_a_revision_requests=rev_requests, raw_text=text), []


def validate_stage_b2_bindings(
    frozen_stage_a: FrozenStageAMappings,
    b1_state: Union[StageB1Output, FrozenStageB1State],
    b2_output: StageB2Output
) -> Tuple[bool, List[str]]:
    """
    Pure Python Deterministic Stage B-2 Check (Treatment #1.8.9).
    Verifies:
    1. Every binding references an existing validated B-1 element (referential integrity).
    2. Every validated B-1 element has at least one active binding (no disappearing elements).
    3. No Stage A identity changes or unsupported substitutions.
    4. Target artifact matches B-1 validated artifact.
    5. Signature structure is valid.
    
    PYTHON NEVER FIXES THE BINDING. Returns (is_valid, errors).
    """
    errors: List[str] = []
    if not b2_output or not b2_output.bindings:
        return False, ["STAGE_B2_EMPTY_BINDINGS: Stage B-2 produced no relationship bindings."]

    b1_elements = b1_state.elements if hasattr(b1_state, "elements") else []
    b1_by_identity: Dict[str, StageB1ElementRealization] = {e.semantic_identity: e for e in b1_elements}
    b1_identities: Set[str] = set(b1_by_identity.keys())

    bound_identities: Set[str] = set()

    for idx, binding in enumerate(b2_output.bindings, 1):
        if not binding.binding_id:
            errors.append(f"STAGE_B2_MISSING_FIELD: Binding #{idx} is missing 'binding_id'.")

        src = binding.source_identity
        if not src:
            errors.append(f"STAGE_B2_MISSING_FIELD: Binding #{idx} is missing 'source_identity'.")
            continue

        if src not in b1_identities:
            errors.append(
                f"STAGE_B2_UNKNOWN_ELEMENT: Binding '{binding.binding_id or idx}' references unknown source_identity '{src}'. "
                f"Valid B-1 elements are: {sorted(list(b1_identities))}."
            )
            continue

        bound_identities.add(src)
        b1_elem = b1_by_identity[src]

        if not binding.relationship_type:
            errors.append(f"STAGE_B2_MISSING_RELATIONSHIP: Binding for '{src}' is missing 'relationship_type'.")

        if binding.target_artifact:
            norm_b2 = binding.target_artifact.replace("\\", "/")
            norm_b1 = b1_elem.target_artifact.replace("\\", "/")
            if norm_b2 != norm_b1:
                errors.append(
                    f"STAGE_B2_ARTIFACT_MISMATCH: Binding for '{src}' references target_artifact '{norm_b2}', "
                    f"which does not match validated B-1 artifact '{norm_b1}'."
                )

        sig = binding.signature_details
        if sig and isinstance(sig, dict):
            params = sig.get("parameters")
            if params is not None and not isinstance(params, list):
                errors.append(f"STAGE_B2_INVALID_SIGNATURE: 'parameters' for binding '{src}' must be a list.")

    missing_elements = b1_identities - bound_identities
    if missing_elements:
        for m_ident in sorted(list(missing_elements)):
            b1_elem = b1_by_identity[m_ident]
            errors.append(
                f"STAGE_B2_MISSING_BINDING: Validated element '{m_ident}' (obligation '{b1_elem.obligation_id}') "
                f"has no binding or relationship defined in Stage B-2."
            )

    is_valid = len(errors) == 0
    return is_valid, errors


def assemble_decomposed_stage_b_blueprint(
    frozen_stage_a: FrozenStageAMappings,
    b1_state: Union[StageB1Output, FrozenStageB1State],
    b2_state: Union[StageB2Output, FrozenStageB2State],
    task_id: str = "default_task",
    target_language: str = "python"
) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    """
    Treatment #1.8.9: Pure Python deterministic assembly of decomposed Stage B decisions.
    Combines:
    1. Validated Stage B-1 Element Realizations (identities, roles, artifacts, kinds)
    2. Validated Stage B-2 Relationship Bindings (routes, signatures, dependencies)
    3. Raw unescaped scaffold code from Stage B-2/B-3 (#1.8.8 decoupled payload)
    
    Transforms into SemanticArchitecturalPlan and serializes to canonical ArchitecturalBlueprint.
    PYTHON NEVER INFERS MISSING ARCHITECTURE.
    """
    b1_out = b1_state if isinstance(b1_state, StageB1Output) else StageB1Output(elements=list(b1_state.elements))
    b1_valid, b1_errs = validate_stage_b1_realization(frozen_stage_a, b1_out)
    if not b1_valid:
        return None, b1_errs

    b2_out = b2_state if isinstance(b2_state, StageB2Output) else StageB2Output(bindings=list(b2_state.bindings), scaffold_files=dict(b2_state.scaffold_files))
    b2_valid, b2_errs = validate_stage_b2_bindings(frozen_stage_a, b1_state, b2_out)
    if not b2_valid:
        return None, b2_errs

    stage_a_by_id = {m.obligation_id: m for m in frozen_stage_a.mappings}
    b2_by_src: Dict[str, List[StageB2BindingDecision]] = {}
    for b in b2_out.bindings:
        if b.source_identity not in b2_by_src:
            b2_by_src[b.source_identity] = []
        b2_by_src[b.source_identity].append(b)

    decisions: List[SemanticArchitecturalDecision] = []
    primary_target_file = ""

    for b1_elem in b1_out.elements:
        a_map = stage_a_by_id.get(b1_elem.obligation_id)
        bindings = b2_by_src.get(b1_elem.semantic_identity, [])
        primary_binding = bindings[0] if bindings else None

        tgt_file = b1_elem.target_artifact or (a_map.semantic_target_artifact if a_map else "main.py")
        if not primary_target_file:
            primary_target_file = tgt_file

        is_model = b1_elem.element_kind.upper() in ("DATA_MODEL", "MODEL", "SCHEMA", "ENTITY")
        tgt_struct = "DATA_MODEL" if is_model else "INTERFACE_CONTRACT"

        sig = primary_binding.signature_details if primary_binding else {}

        params = sig.get("parameters")
        if params is None and a_map and a_map.semantic_parameters:
            params = list(a_map.semantic_parameters)
        if params is None:
            params = []

        norm_params: List[SemanticParameter] = []
        for p in params:
            if isinstance(p, SemanticParameter):
                norm_params.append(p)
            elif isinstance(p, dict):
                norm_params.append(SemanticParameter.from_dict(p))
            elif isinstance(p, str):
                norm_params.append(SemanticParameter(name=p.strip()))

        ret = sig.get("return_semantics") or sig.get("return")
        if ret is None and a_map and a_map.semantic_return:
            ret = dict(a_map.semantic_return)
        if ret is None:
            ret = {}

        if isinstance(ret, SemanticReturn):
            norm_ret: Optional[SemanticReturn] = ret
        elif isinstance(ret, dict):
            norm_ret = SemanticReturn.from_dict(ret)
        elif isinstance(ret, str) and ret.strip():
            norm_ret = SemanticReturn(type=ret.strip())
        else:
            norm_ret = SemanticReturn()

        route = sig.get("route")
        http_method = sig.get("http_method") or sig.get("method")
        if not route and primary_binding and primary_binding.relationship_type.upper() == "BINDS_ROUTE":
            route = primary_binding.target_identity

        fields_list = sig.get("fields") or []
        if is_model and not fields_list and params:
            fields_list = params

        dec = SemanticArchitecturalDecision(
            obligation_id=b1_elem.obligation_id,
            target_structure=tgt_struct,
            identifier=b1_elem.semantic_identity,
            target_file=tgt_file,
            parameters=norm_params,
            return_semantics=norm_ret,
            fields=fields_list,
            route=route,
            http_method=http_method
        )
        decisions.append(dec)

    scaffold_files = dict(b2_out.scaffold_files)
    if not primary_target_file and b1_out.elements:
        primary_target_file = b1_out.elements[0].target_artifact
    if not primary_target_file:
        primary_target_file = "main.py"

    primary_scaffold = scaffold_files.get(primary_target_file, "")
    if not primary_scaffold and scaffold_files:
        primary_scaffold = next(iter(scaffold_files.values()))

    assembly = StageBAssemblyOutput(
        target_file=primary_target_file,
        files=scaffold_files,
        scaffold_code=primary_scaffold,
        semantic_decisions=decisions,
        stage_a_revision_requests=list(b2_out.stage_a_revision_requests),
        raw_text=b2_out.raw_text,
        is_decoupled=True
    )

    plan, conv_errs = convert_stage_b_to_semantic_plan(
        frozen_stage_a=frozen_stage_a,
        assembly=assembly,
        task_id=task_id,
        target_language=target_language
    )
    if not plan or conv_errs:
        return None, conv_errs or ["STAGE_B_CONVERSION_ERROR: Failed to convert decomposed assembly to semantic plan."]

    if serialize_semantic_decision_to_blueprint is None:
        return None, ["SERIALIZER_NOT_AVAILABLE: serialize_semantic_decision_to_blueprint is not imported."]

    blueprint, ser_errs = serialize_semantic_decision_to_blueprint(plan)
    if not blueprint or ser_errs:
        return None, ser_errs or ["STAGE_B_SERIALIZATION_ERROR: Failed to serialize semantic plan to blueprint."]

    return blueprint, []


# ============================================================================
# 5. Prompt Construction for Stage A & Stage B (Treatment #1.8.7)
# ============================================================================

STAGE_A_SYSTEM_PROMPT = """Anda adalah Senior Software & System Architect dalam tim rekayasa perangkat lunak ReinDev Studio.
Peran Anda pada sesi ini adalah melaksanakan:
STAGE A: ACCEPTANCE OBLIGATION MAPPING.

TUGAS TAHAP A:
Petakan setiap acceptance obligation publik ke elemen arsitektur semantik abstrak.
JANGAN membuat file_tree, JANGAN menulis scaffold code, JANGAN membuat Blueprint JSON, JANGAN menggunakan field Pydantic schema kanonikal.
Fokus murni pada: "Apa elemen arsitektur yang diperlukan untuk memenuhi obligation ini?"

EPISTEMIC EVIDENCE HIERARCHY (HIERARKI BUKTI EPISTEMIK):
Anda WAJIB mengikuti hierarki bukti yang ketat:
  1. ACCEPTANCE AUTHORITY (Otoritas penerimaan mutlak: Frozen Acceptance Oracle)
  2. AUTHORITATIVE OBLIGATIONS (Daftar kewajiban publik yang dapat diobservasi)
  3. AUTHORITATIVE SCENARIOS (Skenario stimulus/respons dan asersi)
  4. V0 REQUIREMENTS (Intensi pengguna & model kebutuhan V0)
  5. PM REQUIREMENTS (Spesifikasi Product Manager — referensi desain saja)
  6. EXISTING VALID ARCHITECTURAL STATE (State terbukti & invarian terkunci)
  7. CURRENT REPAIR EVIDENCE (Bukti kegagalan aktif terisolasi & batas perbaikan)
Bukti pada level yang lebih tinggi TIDAK BOLEH dikesampingkan oleh deskripsi pada level yang lebih rendah!

PROMPT FIDELITY RULES (ATURAN KESETIAAN SEMANTIK):
1. DILARANG mengganti nama (rename), menafsirkan ulang (reinterpret), menggabungkan (merge), memecah (split), atau mengganti (replace) authoritative obligation KECUALI bukti otoritatif secara eksplisit mendukung transformasi tersebut.
2. DILARANG mengganti obligation dengan fitur atau sinonim yang tampak mirip secara semantik (semantic synonym temptation). Gunakan simbol dan identitas eksak yang dituntut otoritas penerimaan.
3. Jika bukti tidak mencukupi atau ambigu: tandai keputusan sebagai UNRESOLVED daripada mengarang/menginventasi kebutuhan.
4. Rantai Perilaku Observable (Observable Behavior Chain):
     acceptance_obligation
         ↓
     required observable behavior
         ↓
     semantic architectural element
         ↓
     interface/component representation
   Identitas semantik yang wajib dipertahankan mencakup: operation identity, callable identity, component identity, interaction identity, dan externally observable behavior.
5. Pemisahan WHAT vs HOW:
   DILARANG memaksakan mekanisme implementasi (framework khusus, class exception internal, pola HTTP internal, alias fungsi, layout berkas, dsb.).
   Architect menentukan CARA (HOW); Acceptance Authority menentukan APA (WHAT).

FORMAT LUARAN WAJIB (STAGE A):
Tuliskan pemetaan semantik Anda di dalam penanda persis:
=== STAGE A: OBLIGATION MAPPING ===
{
  "obligation_mappings": [
    {
      "obligation_id": "OBL-01",
      "source_authority": "ACCEPTANCE_ORACLE",
      "semantic_element": "OperationAlpha",
      "mapped_element": "OperationAlpha",
      "element_kind": "FUNCTION",
      "semantic_identity": "operation_alpha",
      "semantic_target_artifact": "main.py",
      "evidence_basis": "Verified from acceptance oracle test stimulus",
      "semantic_parameters": [
        {
          "name": "param_1",
          "type": "str",
          "location": "ARGUMENT",
          "required": true
        }
      ],
      "semantic_return": {
        "type": "str",
        "status_code": 200
      }
    }
  ]
}
=== END STAGE A ===

ATURAN STAGE A:
1. Seluruh obligation dalam [AUTHORITATIVE ACCEPTANCE OBLIGATIONS] WAJIB dipetakan 100% tanpa ada yang tertinggal.
2. DILARANG mengarang obligation_id yang tidak ada dalam daftar authoritative obligations.
3. `element_kind` WAJIB salah satu dari: FUNCTION, CLASS, ENDPOINT, DATA_MODEL, WIDGET, CALLABLE, COMPONENT.
4. `semantic_identity` WAJIB merupakan simbol eksak yang akan dipanggil/diuji oleh pengujian publik.
5. `semantic_target_artifact` adalah nama berkas implementasi target di mana elemen ini akan diletakkan.
6. Traceability: Setiap pemetaan wajib mempertahankan obligation_id, source_authority, semantic_identity, semantic_element (mapped_element), dan evidence_basis."""


STAGE_B_SYSTEM_PROMPT = """Anda adalah Senior Software & System Architect dalam tim rekayasa perangkat lunak ReinDev Studio.
Peran Anda pada sesi ini adalah melaksanakan:
STAGE B: ARCHITECTURAL ASSEMBLY.

TUGAS TAHAP B:
Rakit hubungan antar-elemen arsitektur, organisasi berkas target, dan scaffold code konkret berdasarkan
PEMETAAN SEMANTIK TAHAP A YANG SUDAH TERVALIDASI DAN TERKUNCI (FROZEN).

STAGE B GROUNDING & PRESERVATION INVARIANTS:
1. Stage B menerima pemetaan semantik Tahap A yang tervalidasi sebagai input IMMUTABLE untuk giliran ini.
2. Stage B berhak menentukan representasi arsitektur (struktur berkas, stubs scaffold, penamaan modul), TETAPI WAJIB mempertahankan:
   - obligation identity (obligation_id)
   - semantic identity (semantic_identity)
   - required observable behavior (perilaku observable yang dituntut)
3. Jika Stage B tidak dapat merepresentasikan suatu obligasi secara setia:
   Laporkan representasi yang tidak terselesaikan (unresolved representation) melalui 'stage_a_revision_requests'.
   DILARANG KERAS menafsirkan ulang, mengganti nama, atau menghapus obligasi secara diam-diam!
4. Setiap elemen semantik dari Tahap A harus hadir secara utuh dalam 'semantic_decisions' dan terefleksi pada artefak scaffold code.
5. Anda TIDAK perlu menghafal skema Pydantic kanonikal; serializer deterministik akan memetakannya secara otomatis.

FORMAT LUARAN WAJIB (STAGE B - DECOUPLED REPRESENTATION):
Gunakan dua blok terpisah agar kode sumber mentah TIDAK perlu di-escape ke dalam JSON:

Blok 1: Keputusan Arsitektural (JSON murni tanpa string kode sumber):
=== STAGE B: ARCHITECTURAL DECISIONS ===
{
  "target_file": "main.py",
  "semantic_decisions": [
    {
      "obligation_id": "OBL-01",
      "target_structure": "INTERFACE_CONTRACT",
      "identifier": "operation_alpha",
      "target_file": "main.py",
      "parameters": [
        {
          "name": "param_1",
          "type": "str",
          "location": "ARGUMENT",
          "required": true
        }
      ],
      "return_semantics": {
        "type": "str",
        "status_code": 200
      }
    }
  ],
  "stage_a_revision_requests": []
}
=== END STAGE B DECISIONS ===

Blok 2: Artefak Scaffold Code (Kode sumber mentah tanpa JSON escaping):
=== STAGE B: SCAFFOLD ARTIFACTS ===
=== FILE: main.py ===
def operation_alpha(param_1: str) -> str:
    pass
=== END FILE ===
=== END STAGE B SCAFFOLDS ===

(Catatan: Parser juga tetap mendukung format legacy terpadu === STAGE B: ARCHITECTURAL ASSEMBLY === untuk kompatibilitas ke belakang)."""


def format_stage_a_repair_evidence(
    authoritative_obligations: List[Any],
    current_mappings: Optional[List[StageAObligationMapping]] = None,
    repair_errors: Optional[List[str]] = None,
    repair_boundary: Optional[Dict[str, List[str]]] = None
) -> str:
    """
    Constructs isolated Stage A repair evidence distinguishing:
    - Authoritative obligation set
    - Current mapping
    - Missing obligations
    - Invalid mappings
    - Preserved valid mappings
    - Evidence causing rejection
    - Repair boundary (ALLOWED vs FORBIDDEN)
    """
    lines = ["[STAGE A REPAIR EVIDENCE & BOUNDARY]"]
    auth_ids = set()
    for item in authoritative_obligations:
        if isinstance(item, str):
            auth_ids.add(item.strip())
        elif isinstance(item, dict):
            oid = item.get("obligation_id") or item.get("id")
            if oid:
                auth_ids.add(str(oid).strip())
        elif hasattr(item, "obligation_id"):
            auth_ids.add(str(getattr(item, "obligation_id")).strip())

    lines.append(f"AUTHORITATIVE OBLIGATIONS: {sorted(list(auth_ids)) if auth_ids else 'None declared'}")

    mapped_ids = set()
    if current_mappings:
        valid_maps = []
        invalid_maps = []
        for m in current_mappings:
            mapped_ids.add(m.obligation_id)
            if not m.obligation_id or not m.semantic_identity or not m.semantic_target_artifact:
                invalid_maps.append(m)
            elif auth_ids and m.obligation_id not in auth_ids:
                invalid_maps.append(m)
            else:
                valid_maps.append(m)

        if valid_maps:
            lines.append("PRESERVED VALID MAPPINGS (DO NOT MUTATE OR DISCARD):")
            for vm in valid_maps:
                lines.append(f"  ✓ [{vm.obligation_id}] {vm.semantic_identity} ({vm.element_kind}) in {vm.semantic_target_artifact}")

        if invalid_maps:
            lines.append("INVALID MAPPINGS REQUIRING CORRECTION:")
            for im in invalid_maps:
                lines.append(f"  ✗ [{im.obligation_id}] {im.semantic_identity} ({im.element_kind}) in {im.semantic_target_artifact}")

    if auth_ids:
        missing = auth_ids - mapped_ids
        if missing:
            lines.append(f"MISSING OBLIGATIONS REQUIRING NEW MAPPING: {sorted(list(missing))}")

    if repair_errors:
        lines.append("EVIDENCE CAUSING REJECTION (ACTIVE FAILURES):")
        for e in repair_errors:
            lines.append(f"  - {e}")

    allowed = ["Repair identified semantic mismatch", "Map missing authoritative obligations", "Preserve all already-valid mappings"]
    forbidden = ["Do NOT mutate, rename, or drop already-valid mappings", "Do NOT invent obligation IDs not in authoritative set", "Do NOT replace authoritative identity with a synonym"]
    if repair_boundary and isinstance(repair_boundary, dict):
        allowed = repair_boundary.get("allowed_changes", allowed)
        forbidden = repair_boundary.get("forbidden_changes", forbidden)

    lines.append("REPAIR BOUNDARY:")
    lines.append("  ALLOWED:")
    for a in allowed:
        lines.append(f"    + {a}")
    lines.append("  FORBIDDEN:")
    for f_ in forbidden:
        lines.append(f"    x {f_}")

    return "\n".join(lines)


def build_stage_a_prompt(
    target_lang: str,
    user_task: str,
    specs: str = "",
    oracle_ledger: str = "",
    oracle_scenarios: str = "",
    v0_model: Optional[Any] = None,
    existing_state: Optional[Any] = None,
    repair_errors: Optional[List[str]] = None,
    repair_packet: Optional[Any] = None,
    authoritative_obligations: Optional[List[Any]] = None,
    current_mappings: Optional[List[StageAObligationMapping]] = None
) -> str:
    """
    Constructs prompt for Stage A (Acceptance Obligation Mapping)
    strictly following the 7-Layer Epistemic Evidence Hierarchy (Treatment #1.8.7).
    """
    # [1] ACCEPTANCE AUTHORITY
    level_1 = (
        "[1] ACCEPTANCE AUTHORITY (GROUND TRUTH — IMMUTABLE)\n"
        "===================================================\n"
        "The Acceptance Authority (Frozen Acceptance Oracle) is the sole authoritative arbiter of WHAT must be built and tested.\n"
        "All public callables, endpoints, data models, and widgets demanded by the Acceptance Authority are mandatory FACTS.\n\n"
        "PROMPT FIDELITY RULES:\n"
        "1. Do NOT rename, reinterpret, merge, split, or replace an authoritative obligation unless authoritative evidence explicitly supports that transformation.\n"
        "2. Do NOT substitute a semantically similar feature or synonym for the authoritative obligation (resist semantic synonym temptation).\n"
        "3. If evidence is insufficient or ambiguous: mark the decision UNRESOLVED rather than inventing a requirement.\n"
        "4. The behavioral relationship MUST be preserved:\n"
        "     acceptance_obligation\n"
        "         ↓\n"
        "     required observable behavior\n"
        "         ↓\n"
        "     semantic architectural element\n"
        "         ↓\n"
        "     interface/component representation\n"
        "   Preserved semantic identity includes: operation identity, callable identity, component identity, interaction identity, and externally observable behavior.\n"
        "5. The Architect decides HOW; the Acceptance Authority defines WHAT. Do NOT prescribe implementation mechanisms (frameworks, internal exception classes, HTTP library specifics, function aliases, file layouts, or coding patterns)."
    )

    # [2] AUTHORITATIVE OBLIGATIONS
    level_2 = (
        "[2] AUTHORITATIVE OBLIGATIONS (MANDATORY ACCEPTANCE LEDGER)\n"
        "===========================================================\n"
        + (oracle_ledger.strip() if oracle_ledger.strip() else "(No explicit obligation ledger declared; infer from Acceptance Authority)")
    )

    # [3] AUTHORITATIVE SCENARIOS
    level_3 = (
        "[3] AUTHORITATIVE SCENARIOS (BEHAVIORAL SPECIFICATION & ASSERTIONS)\n"
        "===================================================================\n"
        + (oracle_scenarios.strip() if oracle_scenarios.strip() else "(No explicit behavioral scenarios declared)")
    )

    # [4] V0 REQUIREMENTS
    v0_text = ""
    if v0_model:
        if isinstance(v0_model, dict):
            reqs = v0_model.get("requirements", [])
            lines = []
            for r in reqs:
                if isinstance(r, dict):
                    lines.append(f"  - [{r.get('category', 'REQ')}] {r.get('description', str(r))}")
                else:
                    lines.append(f"  - {r}")
            v0_text = "\n".join(lines)
        else:
            v0_text = str(v0_model)
    level_4 = (
        "[4] V0 REQUIREMENTS (USER INTENT & INITIAL REQUIREMENT MODEL)\n"
        "=============================================================\n"
        f"User Task Intent:\n{user_task.strip()}\n"
        + (f"\nV0 Requirement Model:\n{v0_text.strip()}\n" if v0_text.strip() else "")
        + "\n(Notice: V0 requirements provide user context but CANNOT override or contradict Authoritative Obligations at Levels 1-3)."
    )

    # [5] PM REQUIREMENTS
    level_5 = (
        "[5] PM REQUIREMENTS (PRODUCT MANAGER PROPOSAL — REFERENCE ONLY)\n"
        "===============================================================\n"
        + (specs.strip() if specs.strip() else "(No PM specifications provided)")
        + "\n\n(Notice: PM specifications are proposals [PM_PROPOSAL] for design guidance. They do NOT possess acceptance authority and CANNOT alter Authoritative Obligations at Levels 1-3)."
    )

    # [6] EXISTING VALID ARCHITECTURAL STATE
    state_lines = []
    if existing_state:
        if isinstance(existing_state, dict):
            for k, v in existing_state.items():
                state_lines.append(f"  {k}: {v}")
        elif isinstance(existing_state, list):
            for item in existing_state:
                state_lines.append(f"  - {item}")
        else:
            state_lines.append(str(existing_state))
    level_6 = (
        "[6] EXISTING VALID ARCHITECTURAL STATE (LOCKED INVARIANTS & PROVEN ELEMENTS)\n"
        "============================================================================\n"
        + ("\n".join(state_lines) if state_lines else "None (Initial synthesis turn).")
    )

    # [7] CURRENT REPAIR EVIDENCE
    if repair_errors or repair_packet or current_mappings:
        repair_text = format_stage_a_repair_evidence(
            authoritative_obligations=authoritative_obligations or [],
            current_mappings=current_mappings,
            repair_errors=repair_errors,
            repair_boundary=getattr(repair_packet, "repair_boundary", None) if repair_packet else None
        )
        repair_header = "[PERBAIKAN STAGE A DIPERLUKAN - HASIL VALIDASI GAGAL]\n" if repair_errors else ""
        level_7 = (
            "[7] CURRENT REPAIR EVIDENCE (ISOLATED ACTIVE FAILURES & REPAIR BOUNDARY)\n"
            "========================================================================\n"
            + repair_header
            + repair_text
        )
    else:
        level_7 = (
            "[7] CURRENT REPAIR EVIDENCE\n"
            "===========================\n"
            "No active failures. Clean initial synthesis."
        )

    sections = [
        f"TARGET BAHASA PEMROGRAMAN: {target_lang.upper()}",
        level_1,
        level_2,
        level_3,
        level_4,
        level_5,
        level_6,
        level_7,
        """PRE-SEAL SELF-REVIEW (Sebelum menyerahkan blueprint):
1. Specification -> Coverage: Apakah seluruh requirement dari spesifikasi sudah terwakili tanpa ada yang terlewat?
2. Blueprint -> Internal Consistency: Apakah setiap simbol yang digunakan memiliki sumber resolusi yang jelas?
3. Blueprint -> Contract Consistency: Apakah antarmuka yang ditentukan spesifikasi dipertahankan secara eksak?
4. Acceptance Obligations Coverage: Apakah SELURUH obligasi publik dalam [AUTHORITATIVE ACCEPTANCE OBLIGATIONS] telah memiliki padanan deklarasi eksplisit?
5. Semantic Identity Fidelity: Apakah semantic_identity mempertahankan nama eksak dari acceptance authority tanpa penamaan ulang atau sinonim?
6. Observable Behavior: Apakah scaffold dan parameter merepresentasikan perilaku yang dituntut secara memadai?

TUGAS ANDA (STAGE A):
Tentukan pemetaan arsitektural semantik untuk setiap acceptance obligation di atas.
Tuliskan luaran Anda di dalam blok === STAGE A: OBLIGATION MAPPING === ... === END STAGE A ===.
JANGAN menulis kode implementasi atau membuat file tree pada tahap ini."""
    ]
    return "\n\n".join(sections)


def build_stage_b_prompt(
    target_lang: str,
    user_task: str,
    specs: str,
    frozen_stage_a: FrozenStageAMappings,
    repair_errors: Optional[List[str]] = None,
    repair_packet: Optional[Any] = None
) -> str:
    """Constructs prompt for Stage B (Architectural Assembly) with Stage B Grounding (Treatment #1.8.7, #1.8.8)."""
    repair_section = ""
    if repair_errors:
        err_bullets = "\n".join(f"- {e}" for e in repair_errors)
        is_rep_err = any("JSON" in e or "MARKER" in e or "PARSE" in e or "SCAFFOLD" in e for e in repair_errors)
        if is_rep_err:
            repair_section = (
                f"\n\n[7] CURRENT REPAIR EVIDENCE (STAGE B FORMAT / REPRESENTATION ERROR)\n"
                f"====================================================================\n"
                f"[PERBAIKAN STAGE B DIPERLUKAN - INVARIANT PRESERVATION VIOLATION]\n"
                f"[KESALAHAN REPRESENTASI ATAU PARSING]\n"
                f"Format perakitan Stage B sebelumnya mengalami kegagalan representasi:\n"
                f"{err_bullets}\n\n"
                f"PETUNJUK PERBAIKAN REPRESENTASI:\n"
                f"Gunakan format terpisah (Decoupled Representation) di bawah.\n"
                f"DILARANG memasukkan kode sumber panjang ke dalam string JSON 'scaffold_code'.\n"
                f"Letakkan JSON keputusan arsitektur di Blok 1, dan seluruh kode scaffold mentah di Blok 2.\n"
            )
        else:
            repair_section = (
                f"\n\n[7] CURRENT REPAIR EVIDENCE (STAGE B PRESERVATION FAILURE)\n"
                f"==========================================================\n"
                f"[PERBAIKAN STAGE B DIPERLUKAN - INVARIANT PRESERVATION VIOLATION]\n"
                f"Perbaiki perakitan arsitektur Stage B berikut:\n"
                f"{err_bullets}\n\n"
                f"PERINGATAN KETAT: Pemetaan Tahap A bersifat TERKUNCI (FROZEN). Anda DILARANG mengganti nama simbol atau menghapus obligasi!\n"
            )
    else:
        repair_section = (
            f"\n\n[7] CURRENT REPAIR EVIDENCE\n"
            f"===========================\n"
            f"No active failures. Clean initial assembly."
        )

    stage_a_table_json = json.dumps(frozen_stage_a.to_dict_list(), indent=2)
    default_target_file = frozen_stage_a.mappings[0].semantic_target_artifact if (frozen_stage_a and frozen_stage_a.mappings) else "main.py"

    prompt = f"""TARGET BAHASA PEMROGRAMAN: {target_lang.upper()}

[1] ACCEPTANCE AUTHORITY (STAGE B GROUNDING INVARIANTS)
=======================================================
1. Stage B menerima pemetaan semantik Tahap A yang tervalidasi sebagai input IMMUTABLE untuk giliran ini.
2. Stage B berhak menentukan representasi arsitektur (struktur berkas, stubs scaffold, organisasi modul), TETAPI WAJIB mempertahankan:
   - obligation identity (obligation_id)
   - semantic identity (semantic_identity)
   - required observable behavior (perilaku observable yang dituntut)
3. Jika Stage B tidak dapat merepresentasikan suatu obligasi secara setia:
   Laporkan representasi yang tidak terselesaikan (unresolved representation) melalui 'stage_a_revision_requests'.
   DILARANG KERAS menafsirkan ulang, mengganti nama, atau menghapus obligasi secara diam-diam!
4. Anda TIDAK perlu menghafal skema Pydantic kanonikal; serializer deterministik akan memetakannya secara otomatis.

[4] V0 REQUIREMENTS (USER INTENT)
=================================
{user_task}

[5] PM REQUIREMENTS (REFERENCE ONLY)
====================================
{specs}

[6] EXISTING VALID ARCHITECTURAL STATE (FROZEN STAGE A SEMANTIC MAPPINGS)
========================================================================
(Seal SHA-256: {frozen_stage_a.sha256_seal})
```json
{stage_a_table_json}
```
{repair_section}

TUGAS ANDA (STAGE B):
Rakit arsitektur konkret, berkas target, dan scaffold code yang mengimplementasikan seluruh elemen semantik Tahap A di atas.
Gunakan format terpisah (decoupled representation) agar kode sumber TIDAK perlu di-escape ke dalam JSON:

Blok 1 (Keputusan Arsitektur - JSON murni tanpa string kode sumber):
=== STAGE B: ARCHITECTURAL DECISIONS ===
{{
  "target_file": "{default_target_file}",
  "semantic_decisions": [
    ...
  ],
  "stage_a_revision_requests": []
}}
=== END STAGE B DECISIONS ===

Blok 2 (Artefak Scaffold - Kode Sumber Mentah Unescaped):
=== STAGE B: SCAFFOLD ARTIFACTS ===
=== FILE: {default_target_file} ===
# Tuliskan kode scaffold mentah di sini dengan indentasi dan tanda kutip normal tanpa JSON escaping
=== END FILE ===
=== END STAGE B SCAFFOLDS ===

INGAT INVARIAN KETAT:
Pertahankan seluruh semantic_identity dan target_artifact dari Tahap A secara eksak!"""
    return prompt


# ============================================================================
# 5B. Stage B-1 & Stage B-2 Prompts & Evidence Formatters (Treatment #1.8.9)
# ============================================================================

STAGE_B1_SYSTEM_PROMPT = """Anda adalah Senior Software & System Architect dalam tim rekayasa perangkat lunak ReinDev Studio.
Peran Anda pada sesi ini adalah melaksanakan:
STAGE B-1: ELEMENT REALIZATION (Treatment #1.8.9).

TUGAS TAHAP B-1:
Nyatakan representasi arsitektur eksplisit untuk SETIAP elemen Tahap A yang sudah divalidasi dan terkunci.
JANGAN menulis kode sumber di sini (Zero source code).
JANGAN membuat keputusan relasi/binding yang merupakan tugas Tahap B-2.

ATURAN KETAT STAGE B-1:
1. Seluruh obligation dalam [VALIDATED TAHAP A SEMANTIC MAPPINGS] WAJIB direalisasikan 1-to-1 tanpa ada yang terlewat.
2. DILARANG mengganti nama (rename), menghapus (delete), atau mengarang (invent) obligation.
3. Pertahankan `semantic_identity` dan `target_artifact` eksak dari Tahap A.
4. Tentukan `architectural_representation` konkret (contoh: REST_ENDPOINT_CONTROLLER, CLI_COMMAND_HANDLER, DOMAIN_ENTITY, UI_METRIC_CARD, UTILITY_MODULE, dsb.).

FORMAT LUARAN WAJIB (STAGE B-1):
=== STAGE B-1: ELEMENT REALIZATION ===
{
  "element_realizations": [
    {
      "obligation_id": "OBL-01",
      "semantic_identity": "exact_symbol_from_stage_a",
      "element_kind": "FUNCTION",
      "target_artifact": "main.py",
      "architectural_representation": "CLI_COMMAND_HANDLER"
    }
  ]
}
=== END STAGE B-1 ==="""


STAGE_B2_SYSTEM_PROMPT = """Anda adalah Senior Software & System Architect dalam tim rekayasa perangkat lunak ReinDev Studio.
Peran Anda pada sesi ini adalah melaksanakan:
STAGE B-2: RELATIONSHIP / BINDING DECISION (Treatment #1.8.9).

TUGAS TAHAP B-2:
Tentukan bagaimana elemen-elemen arsitektur yang sudah divalidasi pada Tahap B-1 saling terhubung (antarmuka, routing, model data, signature panggilan) dan sediakan kode scaffold konkret.

ATURAN KETAT STAGE B-2:
1. Setiap binding WAJIB merujuk pada `source_identity` dari elemen Tahap B-1 yang valid.
2. DILARANG mengubah `semantic_identity` atau menghapus elemen Tahap B-1.
3. Seluruh elemen Tahap B-1 WAJIB memiliki setidaknya satu binding / deklarasi relasi.
4. Tuliskan kode scaffold mentah di Blok 2 tanpa JSON escaping.

FORMAT LUARAN WAJIB (STAGE B-2 - DECOUPLED):
Blok 1 (Keputusan Relasi / Binding - JSON murni):
=== STAGE B-2: RELATIONSHIP BINDINGS ===
{
  "bindings": [
    {
      "binding_id": "BIND-01",
      "source_identity": "exact_symbol_from_b1",
      "target_identity": "/api/resource",
      "relationship_type": "BINDS_ROUTE",
      "target_artifact": "main.py",
      "signature_details": {
        "parameters": [
          {"name": "param_1", "type": "str", "required": true}
        ],
        "return_semantics": {
          "type": "dict",
          "status_code": 200
        },
        "route": "/api/resource",
        "http_method": "POST"
      }
    }
  ]
}
=== END STAGE B-2 ===

Blok 2 (Artefak Scaffold - Kode Sumber Mentah):
=== STAGE B: SCAFFOLD ARTIFACTS ===
=== FILE: main.py ===
# Tuliskan kode scaffold mentah di sini dengan indentasi normal tanpa JSON escaping
=== END FILE ===
=== END STAGE B SCAFFOLDS ==="""


def format_stage_b1_repair_evidence(
    frozen_stage_a: FrozenStageAMappings,
    repair_errors: Optional[List[str]] = None,
    current_b1: Optional[StageB1Output] = None
) -> str:
    """Formats isolated Stage B-1 repair evidence."""
    lines = ["[STAGE B-1 REPAIR EVIDENCE & BOUNDARY]"]
    if repair_errors:
        lines.append("ACTIVE FAILURES IN STAGE B-1:")
        for e in repair_errors:
            lines.append(f"  - {e}")

    lines.append("\nVALIDATED STAGE A ELEMENTS (IMMUTABLE GROUND TRUTH):")
    for m in frozen_stage_a.mappings:
        lines.append(f"  ✓ [{m.obligation_id}] symbol='{m.semantic_identity}' kind='{m.element_kind}' file='{m.semantic_target_artifact}'")

    lines.append("\nREPAIR BOUNDARY:")
    lines.append("  ALLOWED: Assign valid architectural_representation, restore exact Stage A identities, preserve 1-to-1 coverage.")
    lines.append("  FORBIDDEN: Do NOT rename symbols, do NOT omit obligations, do NOT invent obligations, do NOT write source code.")
    return "\n".join(lines)


def format_stage_b2_repair_evidence(
    frozen_stage_a: FrozenStageAMappings,
    frozen_b1: Union[StageB1Output, FrozenStageB1State],
    repair_errors: Optional[List[str]] = None,
    current_b2: Optional[StageB2Output] = None
) -> str:
    """Formats isolated Stage B-2 repair evidence with locked B-1 state."""
    lines = ["[STAGE B-2 REPAIR EVIDENCE & BOUNDARY]"]
    if repair_errors:
        lines.append("ACTIVE FAILURES IN STAGE B-2:")
        for e in repair_errors:
            lines.append(f"  - {e}")

    b1_elems = frozen_b1.elements if hasattr(frozen_b1, "elements") else []
    lines.append("\nLOCKED STAGE B-1 ELEMENTS (DO NOT MUTATE OR DISCARD):")
    for e in b1_elems:
        lines.append(f"  ✓ [{e.obligation_id}] symbol='{e.semantic_identity}' role='{e.architectural_representation}' in {e.target_artifact}")

    lines.append("\nREPAIR BOUNDARY:")
    lines.append("  ALLOWED: Correct route/signature bindings, ensure all B-1 elements are bound, fix scaffold syntax/markers.")
    lines.append("  FORBIDDEN: Do NOT mutate B-1 symbols, do NOT discard B-1 elements, do NOT invent undefined elements.")
    return "\n".join(lines)


def build_stage_b1_prompt(
    target_lang: str,
    user_task: str,
    specs: str,
    frozen_stage_a: FrozenStageAMappings,
    repair_errors: Optional[List[str]] = None,
    current_b1: Optional[StageB1Output] = None
) -> str:
    """Constructs prompt for Stage B-1 (Element Realization)."""
    repair_section = ""
    if repair_errors:
        evidence = format_stage_b1_repair_evidence(frozen_stage_a, repair_errors, current_b1)
        repair_section = f"\n\n[7] CURRENT REPAIR EVIDENCE (STAGE B-1 REALIZATION FAILURE)\n==========================================================\n{evidence}\n"
    else:
        repair_section = "\n\n[7] CURRENT REPAIR EVIDENCE\n===========================\nNo active failures. Clean initial realization.\n"

    stage_a_table_json = json.dumps(frozen_stage_a.to_dict_list(), indent=2)
    default_target_file = frozen_stage_a.mappings[0].semantic_target_artifact if (frozen_stage_a and frozen_stage_a.mappings) else "main.py"

    prompt = f"""TARGET BAHASA PEMROGRAMAN: {target_lang.upper()}

[1] ACCEPTANCE AUTHORITY (STAGE B-1 GROUNDING INVARIANTS)
=========================================================
1. Stage B-1 menerima pemetaan semantik Tahap A yang tervalidasi sebagai input IMMUTABLE.
2. Tugas Anda adalah menyatakan realisasi arsitektur konkret (architectural_representation) untuk SETIAP elemen.
3. JANGAN menulis kode sumber implementasi pada tahap ini.
4. Pertahankan seluruh obligation_id, semantic_identity, element_kind, dan target_artifact secara eksak!

[4] V0 REQUIREMENTS (USER INTENT)
=================================
{user_task}

[5] PM REQUIREMENTS (REFERENCE ONLY)
====================================
{specs}

[6] EXISTING VALID ARCHITECTURAL STATE (FROZEN STAGE A SEMANTIC MAPPINGS)
========================================================================
(Seal SHA-256: {frozen_stage_a.sha256_seal})
```json
{stage_a_table_json}
```
{repair_section}
TUGAS ANDA (STAGE B-1):
Petakan setiap elemen Tahap A di atas ke dalam blok === STAGE B-1: ELEMENT REALIZATION ===.
Contoh:
=== STAGE B-1: ELEMENT REALIZATION ===
{{
  "element_realizations": [
    {{
      "obligation_id": "OBL-01",
      "semantic_identity": "{frozen_stage_a.mappings[0].semantic_identity if frozen_stage_a.mappings else 'example_symbol'}",
      "element_kind": "{frozen_stage_a.mappings[0].element_kind if frozen_stage_a.mappings else 'FUNCTION'}",
      "target_artifact": "{default_target_file}",
      "architectural_representation": "REST_ENDPOINT_CONTROLLER"
    }}
  ]
}}
=== END STAGE B-1 ==="""
    return prompt


def build_stage_b2_prompt(
    target_lang: str,
    user_task: str,
    specs: str,
    frozen_stage_a: FrozenStageAMappings,
    frozen_b1: Union[StageB1Output, FrozenStageB1State],
    scenarios: str = "",
    repair_errors: Optional[List[str]] = None,
    current_b2: Optional[StageB2Output] = None,
    state: Optional[Dict[str, Any]] = None,
    repair_attempt: int = 1,
) -> str:
    """Constructs prompt for Stage B-2 (Relationship / Binding Decisions + Scaffold Code)."""
    repair_section = ""
    if repair_errors:
        try:
            from .b2_repair_delivery import (
                extract_b2_repair_decision_packet,
                _format_p0_components,
            )
        except (ImportError, ValueError):
            try:
                from b2_repair_delivery import (
                    extract_b2_repair_decision_packet,
                    _format_p0_components,
                )
            except ImportError:
                extract_b2_repair_decision_packet = None

        if extract_b2_repair_decision_packet is not None:
            syn_state = dict(state) if state and isinstance(state, dict) else {}
            if "canonical_obligations" not in syn_state and hasattr(frozen_stage_a, "mappings"):
                syn_state["canonical_obligations"] = [m.to_dict() for m in frozen_stage_a.mappings]
            if "contract_validation_errors" not in syn_state:
                syn_state["contract_validation_errors"] = list(repair_errors)
            if "stage_a_output" not in syn_state and hasattr(frozen_stage_a, "to_dict_list"):
                syn_state["stage_a_output"] = frozen_stage_a.to_dict_list()
            if "stage_b1_output" not in syn_state and hasattr(frozen_b1, "elements"):
                syn_state["stage_b1_output"] = [e.to_dict() for e in frozen_b1.elements]
            if "stage_b2_output" not in syn_state and current_b2 and hasattr(current_b2, "to_dict"):
                syn_state["stage_b2_output"] = current_b2.to_dict()

            pkt = extract_b2_repair_decision_packet(syn_state, repair_errors=repair_errors, repair_attempt=repair_attempt)
            evidence = _format_p0_components(pkt)
            repair_section = f"\n\n[7] CURRENT REPAIR EVIDENCE (B2 REPAIR DECISION PACKET v2)\n=========================================================\n{evidence}\n"
        else:
            evidence = format_stage_b2_repair_evidence(frozen_stage_a, frozen_b1, repair_errors, current_b2)
            repair_section = f"\n\n[7] CURRENT REPAIR EVIDENCE (STAGE B-2 BINDING FAILURE)\n======================================================\n{evidence}\n"
    else:
        repair_section = "\n\n[7] CURRENT REPAIR EVIDENCE\n===========================\nNo active failures. Clean initial relationship binding.\n"

    b1_elements = frozen_b1.elements if hasattr(frozen_b1, "elements") else []
    b1_table_json = json.dumps([e.to_dict() for e in b1_elements], indent=2)
    default_target_file = b1_elements[0].target_artifact if b1_elements else "main.py"

    scenario_sec = f"\n\n[3] AUTHORITATIVE SCENARIOS (BEHAVIORAL SPECIFICATION)\n====================================================\n{scenarios.strip()}" if scenarios.strip() else ""

    prompt = f"""TARGET BAHASA PEMROGRAMAN: {target_lang.upper()}

[1] ACCEPTANCE AUTHORITY (STAGE B-2 BINDING INVARIANTS)
=======================================================
1. Stage B-1 elemen arsitektur telah tervalidasi dan TERKUNCI (LOCKED).
2. Tentukan bagaimana setiap elemen B-1 terhubung (antarmuka, signature parameter, routing, return value).
3. Seluruh elemen Tahap B-1 WAJIB memiliki deklarasi binding (source_identity harus ada di daftar B-1).
4. Sediakan artefak kode scaffold mentah di Blok 2 tanpa JSON escaping.
{scenario_sec}

[4] V0 REQUIREMENTS (USER INTENT)
=================================
{user_task}

[5] PM REQUIREMENTS (REFERENCE ONLY)
====================================
{specs}

[6] EXISTING VALID ARCHITECTURAL STATE (LOCKED STAGE B-1 ELEMENT REALIZATIONS)
=============================================================================
```json
{b1_table_json}
```
{repair_section}
TUGAS ANDA (STAGE B-2):
Tentukan hubungan/binding arsitektural dan scaffold code:

Blok 1 (Keputusan Relasi / Binding - JSON murni):
=== STAGE B-2: RELATIONSHIP BINDINGS ===
{{
  "bindings": [
    {{
      "binding_id": "BIND-01",
      "source_identity": "{b1_elements[0].semantic_identity if b1_elements else 'example_symbol'}",
      "target_identity": "{default_target_file}",
      "relationship_type": "IMPLEMENTS_INTERFACE",
      "target_artifact": "{default_target_file}",
      "signature_details": {{
        "parameters": [],
        "return_semantics": {{"type": "None"}}
      }}
    }}
  ]
}}
=== END STAGE B-2 ===

Blok 2 (Artefak Scaffold - Kode Sumber Mentah Unescaped):
=== STAGE B: SCAFFOLD ARTIFACTS ===
=== FILE: {default_target_file} ===
# Tuliskan kode scaffold mentah di sini dengan indentasi normal tanpa JSON escaping
=== END FILE ===
=== END STAGE B SCAFFOLDS ==="""
    return prompt

