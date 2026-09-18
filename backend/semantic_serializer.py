"""
Semantic Architectural Decision -> Deterministic Canonical Serialization Engine (v1.1.0)
Treatment #1.8.5 — Universal Semantic Decision -> Deterministic Canonical Serialization v1

CORE PRINCIPLE:
"The serializer may translate representation; it may never infer architecture."

Decouples Architect semantic architectural reasoning from exact canonical JSON/Pydantic serialization:
- Architect explicitly declares architectural decisions: target_structure ("INTERFACE_CONTRACT" | "DATA_MODEL"),
  identity, target_file, parameters, fields, and returns.
- Serializer deterministically translates these decisions into canonical Pydantic structures.
- Serializer NEVER infers architecture, NEVER invents obligations/parameters, and NEVER supplies default files.
"""

from __future__ import annotations
import json
import re
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple, Set, Union

try:
    from .blueprint_schema import (
        ArchitecturalBlueprint,
        BlueprintInterfaceContract,
        BlueprintDataModel,
        BlueprintFileModule,
        BlueprintModelField
    )
except (ImportError, ValueError):
    try:
        from blueprint_schema import (
            ArchitecturalBlueprint,
            BlueprintInterfaceContract,
            BlueprintDataModel,
            BlueprintFileModule,
            BlueprintModelField
        )
    except ImportError:
        ArchitecturalBlueprint = None
        BlueprintInterfaceContract = None
        BlueprintDataModel = None
        BlueprintFileModule = None
        BlueprintModelField = None


# ============================================================================
# 1. Lean Intermediate Semantic Decision Models
# ============================================================================

VALID_TARGET_STRUCTURES = {"INTERFACE_CONTRACT", "DATA_MODEL"}
VALID_PARAM_LOCATIONS = {"PATH", "QUERY", "BODY", "ARGUMENT", "PROP"}


@dataclass
class SemanticParameter:
    """Generic semantic parameter for an interface contract."""
    name: str
    type: str = "str"
    location: str = "ARGUMENT"  # PATH, QUERY, BODY, ARGUMENT, PROP
    required: bool = True
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SemanticParameter:
        name = data.get("name") or data.get("param_name") or ""
        typ = data.get("type") or data.get("param_type") or "str"
        loc = data.get("location") or data.get("param_location") or "ARGUMENT"
        req = data.get("required") if "required" in data else data.get("is_required", True)
        desc = data.get("description")
        return cls(
            name=str(name).strip(),
            type=str(typ).strip(),
            location=str(loc).strip().upper(),
            required=bool(req),
            description=desc
        )


@dataclass
class SemanticReturn:
    """Generic semantic return definition for an interface contract."""
    type: str = "None"
    status_code: Optional[int] = None
    error_codes: Optional[List[int]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SemanticReturn:
        typ = data.get("type") or data.get("return_type") or "None"
        sc = data.get("status_code") or data.get("status_code_success")
        if sc is not None:
            try:
                sc = int(sc)
            except (ValueError, TypeError):
                sc = None
        errs = data.get("error_codes") or data.get("status_code_errors")
        if errs is not None and isinstance(errs, list):
            try:
                errs = [int(x) for x in errs]
            except (ValueError, TypeError):
                errs = None
        return cls(type=str(typ).strip(), status_code=sc, error_codes=errs)


@dataclass
class SemanticArchitecturalDecision:
    """
    Intermediate Architectural Decision made by the Architect.
    Architect explicitly states:
    - WHAT obligation is addressed (obligation_id)
    - WHAT canonical structure it represents (target_structure: "INTERFACE_CONTRACT" | "DATA_MODEL")
    - WHAT symbol/class it defines (identifier)
    - WHERE it resides (target_file)
    - Parameter/return or field specifications
    """
    obligation_id: str
    target_structure: str  # "INTERFACE_CONTRACT" | "DATA_MODEL"
    identifier: str
    target_file: str = ""
    parameters: List[SemanticParameter] = field(default_factory=list)
    return_semantics: Optional[SemanticReturn] = None
    fields: Optional[List[Dict[str, Any]]] = None
    route: Optional[str] = None
    http_method: Optional[str] = None
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "obligation_id": self.obligation_id,
            "target_structure": self.target_structure,
            "identifier": self.identifier,
            "target_file": self.target_file,
            "parameters": [p.to_dict() for p in self.parameters],
            "return_semantics": self.return_semantics.to_dict() if self.return_semantics else None,
            "fields": self.fields,
            "route": self.route,
            "http_method": self.http_method,
            "description": self.description
        }
        return {k: v for k, v in d.items() if v is not None}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SemanticArchitecturalDecision:
        ob_id = str(data.get("obligation_id") or data.get("obligation") or "").strip()
        
        # Structure decision (Architect's explicit structural choice)
        raw_struct = (
            data.get("target_structure") or
            data.get("structure") or
            data.get("element_kind") or
            data.get("kind") or
            ""
        ).strip().upper()

        if raw_struct in ("DATA_MODEL", "MODEL", "SCHEMA", "ENTITY"):
            target_struct = "DATA_MODEL"
        elif raw_struct in ("INTERFACE_CONTRACT", "INTERFACE", "CONTRACT", "FUNCTION", "ENDPOINT", "METHOD", "CALLABLE", "WIDGET", "CLASS", "COMPONENT", "HTTP_ENDPOINT"):
            target_struct = "INTERFACE_CONTRACT"
        else:
            target_struct = raw_struct  # Will trigger SERIALIZATION_INSUFFICIENT_EVIDENCE if invalid

        ident = str(
            data.get("identifier") or
            data.get("architectural_element") or
            data.get("element") or
            data.get("name") or
            ""
        ).strip()

        target = str(
            data.get("target_file") or
            data.get("target_artifact") or
            ""
        ).strip().replace("\\", "/")
        
        # Parameters
        raw_params = data.get("parameters") or []
        params = []
        if isinstance(raw_params, list):
            for p in raw_params:
                if isinstance(p, dict):
                    params.append(SemanticParameter.from_dict(p))
                elif isinstance(p, str):
                    params.append(SemanticParameter(name=p.strip()))

        # Return semantics
        raw_ret = data.get("return_semantics") or data.get("expected_return") or data.get("return")
        ret_sem = None
        if isinstance(raw_ret, dict):
            ret_sem = SemanticReturn.from_dict(raw_ret)
        elif isinstance(raw_ret, str) and raw_ret.strip():
            ret_sem = SemanticReturn(type=raw_ret.strip())

        flds = data.get("fields") or data.get("attributes") or data.get("properties")
        if flds is not None and not isinstance(flds, list):
            flds = None

        route = data.get("route") or data.get("path") or data.get("endpoint")
        if route is not None:
            route = str(route).strip()

        method = data.get("http_method") or data.get("method")
        if method is not None:
            method = str(method).strip().upper()

        desc = data.get("description") or data.get("desc")

        return cls(
            obligation_id=ob_id,
            target_structure=target_struct,
            identifier=ident,
            target_file=target,
            parameters=params,
            return_semantics=ret_sem,
            fields=flds,
            route=route,
            http_method=method,
            description=desc
        )


@dataclass
class SemanticArchitecturalPlan:
    """
    Lean Intermediate Semantic Plan from Architect.
    Contains ONLY semantic decisions and minimal scaffold info needed for blueprint creation.
    No redundant summary, no redundant file_tree array.
    """
    target_file: str = ""
    semantic_decisions: List[SemanticArchitecturalDecision] = field(default_factory=list)
    scaffold_code: str = ""
    files: Dict[str, str] = field(default_factory=dict)
    unresolved_obligations: List[str] = field(default_factory=list)
    task_id: str = "default_task"
    target_language: str = "python"
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_file": self.target_file,
            "semantic_decisions": [d.to_dict() for d in self.semantic_decisions],
            "scaffold_code": self.scaffold_code,
            "files": self.files,
            "unresolved_obligations": self.unresolved_obligations,
            "task_id": self.task_id,
            "target_language": self.target_language
        }


# ============================================================================
# 2. Extraction & Parsing Machinery
# ============================================================================

SEMANTIC_MARKER_START = "=== SEMANTIC DECISION JSON ==="
SEMANTIC_MARKER_END = "=== END SEMANTIC DECISION JSON ==="

def extract_semantic_decision_json_text(text: str) -> Optional[str]:
    """Extracts raw JSON text bounded by semantic decision markers or markdown code fences."""
    if not text or not isinstance(text, str):
        return None

    # 1. Explicit marker match
    if SEMANTIC_MARKER_START in text:
        parts = text.split(SEMANTIC_MARKER_START, 1)[1]
        if SEMANTIC_MARKER_END in parts:
            cand = parts.split(SEMANTIC_MARKER_END, 1)[0].strip()
            if cand:
                return cand
        else:
            cand = parts.strip()
            if cand:
                return cand

    # 2. Markdown fenced block containing semantic_decisions / decisions
    code_block_pattern = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
    for m in code_block_pattern.finditer(text):
        cand = m.group(1).strip()
        if "semantic_decisions" in cand or "decisions" in cand:
            return cand

    # 3. Raw JSON scan with matching braces containing semantic_decisions / decisions
    for keyword in ("semantic_decisions", "decisions"):
        if keyword in text:
            start_idx = text.find("{")
            if start_idx != -1:
                stack = 0
                for idx in range(start_idx, len(text)):
                    ch = text[idx]
                    if ch == "{":
                        stack += 1
                    elif ch == "}":
                        stack -= 1
                        if stack == 0:
                            cand = text[start_idx : idx + 1].strip()
                            if keyword in cand:
                                return cand
                            break

    return None


def parse_semantic_architectural_plan(raw_text: str) -> Tuple[Optional[SemanticArchitecturalPlan], List[str]]:
    """
    Parses LLM output into a lean SemanticArchitecturalPlan.
    Validates structure deterministically without domain inference.
    """
    errors: List[str] = []
    json_str = extract_semantic_decision_json_text(raw_text)
    if not json_str:
        return None, ["SEMANTIC_PARSE_ERROR: No semantic decision block found in response"]

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as exc:
        return None, [f"SEMANTIC_PARSE_ERROR: Invalid JSON in semantic decision block: {str(exc)}"]

    if not isinstance(data, dict):
        return None, ["SEMANTIC_PARSE_ERROR: Semantic decision root must be a JSON object"]

    target_file = str(
        data.get("target_file") or
        data.get("target_artifact") or
        data.get("authoritative_target_file") or
        ""
    ).strip().replace("\\", "/")

    # Decisions list
    raw_decisions = (
        data.get("semantic_decisions") or
        data.get("decisions") or
        data.get("interface_contracts")
    )

    if raw_decisions is None or not isinstance(raw_decisions, list):
        return None, ["SEMANTIC_SCHEMA_ERROR: 'semantic_decisions' must be a list"]

    parsed_decisions: List[SemanticArchitecturalDecision] = []
    for idx, d in enumerate(raw_decisions, 1):
        if not isinstance(d, dict):
            errors.append(f"SEMANTIC_SCHEMA_ERROR: Decision item #{idx} is not a JSON object")
            continue

        ob_id = d.get("obligation_id") or d.get("obligation")
        ident = d.get("identifier") or d.get("architectural_element") or d.get("element") or d.get("name")
        struct = (
            d.get("target_structure") or
            d.get("structure") or
            d.get("element_kind") or
            d.get("kind")
        )

        if not ob_id:
            errors.append(f"SEMANTIC_SCHEMA_ERROR: Decision #{idx} missing 'obligation_id'")
        if not ident:
            errors.append(f"SEMANTIC_SCHEMA_ERROR: Decision #{idx} missing 'identifier'")
        if not struct:
            errors.append(f"SEMANTIC_SCHEMA_ERROR: Decision #{idx} missing 'target_structure'")

        if ob_id and ident and struct:
            parsed_decisions.append(SemanticArchitecturalDecision.from_dict(d))

    if errors:
        return None, errors

    # Scaffolds handling
    scaffold_code = str(data.get("scaffold_code") or data.get("code_scaffold") or "").strip()
    files_map: Dict[str, str] = {}
    raw_files = data.get("files")
    if isinstance(raw_files, dict):
        for k, v in raw_files.items():
            k_clean = str(k).strip().replace("\\", "/")
            if isinstance(v, str):
                files_map[k_clean] = v
            elif isinstance(v, dict):
                cs = v.get("code_scaffold") or v.get("scaffold") or ""
                files_map[k_clean] = str(cs)
    elif scaffold_code and target_file:
        files_map[target_file] = scaffold_code

    unresolved = data.get("unresolved_obligations") or []
    if isinstance(unresolved, list):
        unresolved = [str(x).strip() for x in unresolved if str(x).strip()]
    else:
        unresolved = []

    task_id = str(data.get("task_id") or "default_task").strip()
    target_lang = str(data.get("target_language") or "python").strip().lower()
    summary = str(data.get("summary") or data.get("architecture_summary") or "").strip()

    plan = SemanticArchitecturalPlan(
        target_file=target_file,
        semantic_decisions=parsed_decisions,
        scaffold_code=scaffold_code,
        files=files_map,
        unresolved_obligations=unresolved,
        task_id=task_id,
        target_language=target_lang,
        summary=summary
    )

    return plan, []


# ============================================================================
# 3. Deterministic Canonical Serializer
# ============================================================================

def serialize_semantic_decision_to_blueprint(
    plan: SemanticArchitecturalPlan
) -> Tuple[Optional[ArchitecturalBlueprint], List[str]]:
    """
    Deterministic Serializer (v1.1.0):
    Translates SemanticArchitecturalPlan into canonical ArchitecturalBlueprint.

    CORE PRINCIPLE:
    "The serializer may translate representation; it may never infer architecture."

    ANTI-SOLVER RULES:
    1. Zero default_target_file: Serializer does NOT supply or assume a target artifact.
       If target_file is missing from both plan and decision -> SERIALIZATION_INSUFFICIENT_EVIDENCE.
    2. Zero architectural inference: Architect must explicitly declare target_structure
       ("INTERFACE_CONTRACT" or "DATA_MODEL"). Serializer does not infer structure from function/widget semantics.
    3. Zero obligation invention: Serializer only serializes what the Architect explicitly declared.
    4. Zero parameter/return invention: Serializer faithfully translates provided parameters/returns.
    """
    errors: List[str] = []

    if ArchitecturalBlueprint is None:
        return None, ["SERIALIZER_ENVIRONMENT_ERROR: ArchitecturalBlueprint schema is not available in environment"]

    if not plan.semantic_decisions:
        return None, ["SERIALIZATION_INSUFFICIENT_EVIDENCE: No semantic architectural decisions provided to serialize"]

    # 1. Authoritative Target File Resolution (Must come from Architect)
    root_target_file = plan.target_file.strip().replace("\\", "/")
    
    # Check that target_file can be resolved without guessing
    # (either from root target_file or uniformly from decisions)
    if not root_target_file:
        decision_files = {d.target_file.strip().replace("\\", "/") for d in plan.semantic_decisions if d.target_file}
        if len(decision_files) == 1:
            root_target_file = next(iter(decision_files))
        elif len(decision_files) > 1:
            # Ambiguous multiple target files with no root authoritative declaration
            return None, [f"SERIALIZATION_INSUFFICIENT_EVIDENCE: Ambiguous target files {sorted(decision_files)} with no authoritative root target_file"]
        else:
            return None, ["SERIALIZATION_INSUFFICIENT_EVIDENCE: Missing authoritative target file in semantic plan and decisions"]

    # 2. Deterministic File Tree & Scaffolds Collection
    all_files: Set[str] = {root_target_file}
    for d in plan.semantic_decisions:
        if d.target_file:
            all_files.add(d.target_file.strip().replace("\\", "/"))
    for f in plan.files.keys():
        all_files.add(f.strip().replace("\\", "/"))

    file_tree = sorted(list(all_files))
    if root_target_file in file_tree:
        file_tree.remove(root_target_file)
        file_tree.insert(0, root_target_file)

    files_dict: Dict[str, Any] = {}
    for fpath in file_tree:
        scaffold = plan.files.get(fpath, "")
        if not scaffold and fpath == root_target_file and plan.scaffold_code:
            scaffold = plan.scaffold_code

        files_dict[fpath] = {
            "file_path": fpath,
            "module_role": "Authoritative Module" if fpath == root_target_file else "Auxiliary Module",
            "imports": [],
            "code_scaffold": scaffold
        }

    # 3. Translate Decisions to Canonical Structures
    interface_contracts: List[Dict[str, Any]] = []
    data_models: List[Dict[str, Any]] = []
    seen_identifiers: Set[str] = set()

    for idx, d in enumerate(plan.semantic_decisions, 1):
        ob_id = d.obligation_id.strip()
        struct = d.target_structure.strip().upper()
        ident = d.identifier.strip()
        elem_target = (d.target_file or root_target_file).strip().replace("\\", "/")

        if not elem_target:
            errors.append(f"SERIALIZATION_INSUFFICIENT_EVIDENCE: Decision #{idx} ('{ident}') has no target_file")
            continue

        if not ident:
            errors.append(f"SERIALIZATION_INSUFFICIENT_EVIDENCE: Missing identifier for obligation '{ob_id}'")
            continue

        if struct not in VALID_TARGET_STRUCTURES:
            errors.append(
                f"SERIALIZATION_INSUFFICIENT_EVIDENCE: Decision #{idx} ('{ident}') declares invalid or ambiguous target_structure '{d.target_structure}'. "
                "Architect must explicitly choose 'INTERFACE_CONTRACT' or 'DATA_MODEL'."
            )
            continue

        if struct == "DATA_MODEL":
            # Translate to BlueprintDataModel
            flds = []
            if d.fields:
                for f in d.fields:
                    if isinstance(f, dict):
                        f_name = f.get("field_name") or f.get("name")
                        f_type = f.get("field_type") or f.get("type") or "str"
                        f_req = f.get("is_required") if "is_required" in f else f.get("required", True)
                        if f_name:
                            flds.append({
                                "field_name": str(f_name).strip(),
                                "field_type": str(f_type).strip(),
                                "is_required": bool(f_req),
                                "description": f.get("description")
                            })
            elif d.parameters:
                # Lossless conversion from parameters to model fields if fields was not provided
                for p in d.parameters:
                    flds.append({
                        "field_name": p.name,
                        "field_type": p.type,
                        "is_required": p.required,
                        "description": p.description
                    })

            data_models.append({
                "model_name": ident,
                "target_file": elem_target,
                "fields": flds
            })
            seen_identifiers.add(ident)

        elif struct == "INTERFACE_CONTRACT":
            # Translate to BlueprintInterfaceContract
            params_list = []
            for p in d.parameters:
                if isinstance(p, dict):
                    p_name = p.get("name") or p.get("param_name") or ""
                    p_type = p.get("type") or p.get("param_type") or "Any"
                    p_loc = (p.get("location") or p.get("param_location") or "ARGUMENT").upper().strip()
                    p_req = p.get("required") if "required" in p else p.get("is_required", True)
                else:
                    p_name = getattr(p, "name", "")
                    p_type = getattr(p, "type", "Any")
                    p_loc = getattr(p, "location", "ARGUMENT").upper().strip()
                    p_req = getattr(p, "required", True)

                if p_loc not in VALID_PARAM_LOCATIONS:
                    p_loc = "ARGUMENT"
                params_list.append({
                    "param_name": p_name,
                    "param_type": p_type,
                    "param_location": p_loc,
                    "is_required": p_req
                })

            ret_dict = None
            if d.return_semantics:
                if isinstance(d.return_semantics, dict):
                    ret_type = d.return_semantics.get("type") or d.return_semantics.get("return_type") or "None"
                    ret_sc = d.return_semantics.get("status_code") or d.return_semantics.get("status_code_success")
                    ret_errs = d.return_semantics.get("error_codes") or d.return_semantics.get("status_code_errors")
                else:
                    ret_type = getattr(d.return_semantics, "type", "None")
                    ret_sc = getattr(d.return_semantics, "status_code", None)
                    ret_errs = getattr(d.return_semantics, "error_codes", None)

                ret_dict = {
                    "return_type": ret_type
                }
                if ret_sc is not None:
                    ret_dict["status_code_success"] = ret_sc
                if ret_errs is not None:
                    ret_dict["status_code_errors"] = list(ret_errs)

            ifc_dict: Dict[str, Any] = {
                "identifier": ident,
                "target_file": elem_target,
                "parameters": params_list,
                "expected_return": ret_dict
            }
            if d.route is not None:
                ifc_dict["route"] = d.route
            if d.http_method is not None:
                ifc_dict["method"] = d.http_method

            interface_contracts.append(ifc_dict)
            seen_identifiers.add(ident)

    if errors:
        return None, errors

    # 4. Construct and Validate Canonical Blueprint
    blueprint_dict = {
        "schema_version": "1.0.0",
        "task_id": plan.task_id or "default_task",
        "target_language": plan.target_language or "python",
        "authoritative_target_file": root_target_file,
        "file_tree": file_tree,
        "architecture_summary": plan.summary or "Deterministic serialization of semantic architectural decisions",
        "files": files_dict,
        "interface_contracts": interface_contracts,
        "data_models": data_models
    }

    try:
        blueprint = ArchitecturalBlueprint.model_validate(blueprint_dict)
        return blueprint, []
    except Exception as exc:
        return None, [f"CANONICAL_SERIALIZATION_VALIDATION_ERROR: {str(exc)}"]


# ============================================================================
# 4. Obligation Coverage & Preservation Functions
# ============================================================================

def check_semantic_obligation_coverage(
    decisions: List[SemanticArchitecturalDecision],
    oracle_obligations: List[Dict[str, Any]],
    unresolved_obligations: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Deterministic obligation coverage evaluator:
    Compares authoritative oracle obligations against semantic decisions.
    """
    unresolved_set = set(unresolved_obligations or [])
    
    oracle_ids: List[str] = []
    for ob in oracle_obligations:
        oid = ob.get("obligation_id") or ob.get("id") or ob.get("identifier")
        if oid:
            oracle_ids.append(str(oid).strip())

    decision_ids: List[str] = [d.obligation_id.strip() for d in decisions if d.obligation_id]

    mapped = [oid for oid in oracle_ids if oid in decision_ids]
    missing = [oid for oid in oracle_ids if oid not in decision_ids and oid not in unresolved_set]
    unresolved = [oid for oid in oracle_ids if oid in unresolved_set]

    counts: Dict[str, int] = {}
    for did in decision_ids:
        counts[did] = counts.get(did, 0) + 1
    duplicated = [did for did, cnt in counts.items() if cnt > 1]

    coverage_ratio = len(mapped) / len(oracle_ids) if oracle_ids else 1.0

    return {
        "total_obligations": len(oracle_ids),
        "mapped": mapped,
        "missing": missing,
        "unresolved": unresolved,
        "duplicated": duplicated,
        "coverage_ratio": coverage_ratio,
        "is_fully_covered": len(missing) == 0 and len(duplicated) == 0
    }


def merge_preservative_semantic_decisions(
    current_decisions: List[SemanticArchitecturalDecision],
    repair_decisions: List[SemanticArchitecturalDecision],
    targeted_obligation_ids: Set[str]
) -> List[SemanticArchitecturalDecision]:
    """
    Preservative Decision Merger:
    Retains all valid semantic decisions not targeted by the repair.
    Replaces or adds decisions targeting the failing/missing obligations.
    (CURRENT VALID STATE + REPAIRED ELEMENT)
    """
    preserved = [d for d in current_decisions if d.obligation_id not in targeted_obligation_ids]
    repaired = [d for d in repair_decisions if d.obligation_id in targeted_obligation_ids or d.obligation_id not in {x.obligation_id for x in current_decisions}]
    return preserved + repaired
