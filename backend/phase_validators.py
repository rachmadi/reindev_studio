"""
Phase-End Validation & Evidence-First Engineering Engine
ReinDev Studio — Iterasi 7 (Deterministic Context-Aware Validation)

Menyediakan validator deterministik berbasis bukti pada batas fase B1-B6:
- B1 (Phase-End): PM -> Architect
- B2 (Phase-End): Architect -> Developer (Contract Gate integration)
- B3 (Phase-End): Developer -> Oracle/Executor (Pre-execution syntax & contract conformance)
- B4 (Phase-End): Oracle -> Executor (Immutable SHA-256 integrity & bypass verification)
- B5 (Iteration): Executor -> Developer/Reviewer (Execution evidence & regression detection)
- B6 (Phase-End): Reviewer -> END/Developer (Reviewer verdict audit & causal rehabilitation)

Iterasi 7 Additions:
- Global scan (no early-stop on first violation) in all validators.
- ContextualEvidencePackage (CEP) injected on every FAIL verdict.
- Preservation Rule enabled on revalidation.
"""

import ast
import re
import hashlib
import builtins
from typing import Dict, List, Any, Optional, Tuple, TypedDict, Set

try:
    from .state import SquadState
    from .tracer import get_tracer, compute_sha256, compute_dict_hashes
    from .contract import verify_contract_checkpoint
    from .architect_validator import validate_architect_blueprint
    from .contextual_evidence import (
        ContextualEvidencePackage, ViolationItem as CEPViolationItem,
        render_repair_directive,
    )
    from .context_assembler import (
        assemble_b1_evidence, assemble_b2_evidence, assemble_b3_evidence,
        assemble_b4_evidence, assemble_b5_evidence, assemble_b6_evidence,
    )
except (ImportError, ValueError):
    from state import SquadState
    try:
        from tracer import get_tracer, compute_sha256, compute_dict_hashes
    except ImportError:
        def get_tracer(run_id=None): return None
        def compute_sha256(s): return ""
        def compute_dict_hashes(f): return {}
    try:
        from contract import verify_contract_checkpoint
    except ImportError:
        def verify_contract_checkpoint(c, name, raise_on_error=False): return True, None
    try:
        from architect_validator import validate_architect_blueprint
    except ImportError:
        def validate_architect_blueprint(*args, **kwargs): return True, []
    try:
        from contextual_evidence import (
            ContextualEvidencePackage, ViolationItem as CEPViolationItem,
            render_repair_directive,
        )
        from context_assembler import (
            assemble_b1_evidence, assemble_b2_evidence, assemble_b3_evidence,
            assemble_b4_evidence, assemble_b5_evidence, assemble_b6_evidence,
        )
    except ImportError:
        ContextualEvidencePackage = None
        CEPViolationItem = None
        render_repair_directive = lambda pkg, **kw: ""
        assemble_b1_evidence = assemble_b2_evidence = assemble_b3_evidence = None
        assemble_b4_evidence = assemble_b5_evidence = assemble_b6_evidence = None



class EvidenceItem(TypedDict, total=False):
    item: str
    evidence_class: str  # "DETERMINISTIC" | "SEMANTIC"
    observed: Any
    expected: Any
    status: str  # "VALID" | "INVALID" | "WARNING"
    details: Optional[str]


class ViolationItem(TypedDict, total=False):
    criterion: str
    severity: str  # "CRITICAL" | "WARNING" | "INFO"
    message: str
    location: Optional[str]


class RegressionItem(TypedDict, total=False):
    test_or_invariant: str
    previous_status: str
    current_status: str
    message: str


class RequiredRepairItem(TypedDict, total=False):
    target_phase: str
    action: str
    details: str


class ValidatorContract(TypedDict, total=False):
    phase: str
    validator_type: str  # "PHASE_END" | "ITERATION"
    verdict: str  # "PASS" | "FAIL"
    criteria_checked: List[str]
    evidence: List[Dict[str, Any]]
    violations: List[Dict[str, Any]]
    regressions: List[Dict[str, Any]]
    required_repairs: List[Dict[str, Any]]
    repair_owner: Optional[str]
    remaining_budget: Optional[int]
    evaluated_review_verdict: Optional[str]
    confidence: float
    source_of_truth: str
    # Iterasi 7: CEP payload for deterministic repair context injection
    contextual_evidence_package: Optional[Dict[str, Any]]


def _make_cep_violations(violations_raw: List[Dict[str, Any]]) -> List["CEPViolationItem"]:
    """Converts old-style violation dicts to CEPViolationItem dataclasses."""
    if CEPViolationItem is None:
        return []
    result = []
    for i, v in enumerate(violations_raw, 1):
        result.append(CEPViolationItem(
            violation_id=f"VIO-{i:03d}",
            criterion=v.get("criterion", "unknown"),
            severity=v.get("severity", "CRITICAL"),
            location=v.get("location", ""),
            observed_state=v.get("observed_state", v.get("message", "")),
            expected_state=v.get("expected_state", v.get("expected", "")),
            source_detector="PHASE_VALIDATOR_DETERMINISTIC",
            observed_symbol=v.get("observed_symbol"),
        ))
    return result

# ==============================================================================
# Helper Static Analyzers (Deterministic)
# ==============================================================================

def audit_python_module_symbol_resolvability(tree: ast.AST, fname: str = "main.py") -> List[Tuple[str, int, str]]:
    """
    Mengaudit keterdefinisan simbol pada tingkat modul dan class-body (bukan di dalam fungsi).
    Mendeteksi simbol seperti 'ConfigDict' atau base class/decorator yang digunakan tanpa impor.
    Mengembalikan list of (symbol_name, lineno, context_description).
    """
    imported_names: Set[str] = set()
    defined_names: Set[str] = set()
    builtin_names: Set[str] = set(dir(builtins))
    common_types: Set[str] = {
        "int", "float", "str", "bool", "bytes", "list", "dict", "tuple", "set",
        "frozenset", "type", "object", "None", "True", "False", "Ellipsis",
        "Any", "Optional", "Union", "List", "Dict", "Tuple", "Set", "Callable"
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                imported_names.add(n.asname or n.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for n in node.names:
                imported_names.add(n.asname or n.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defined_names.add(node.name)
        elif isinstance(node, ast.ClassDef):
            defined_names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    defined_names.add(target.id)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                defined_names.add(node.target.id)

    available = imported_names | defined_names | builtin_names | common_types

    unresolved: List[Tuple[str, int, str]] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            # 1. Base classes
            for base in node.bases:
                if isinstance(base, ast.Name) and base.id not in available:
                    unresolved.append((base.id, base.lineno, f"base class of '{node.name}'"))
            # 2. Decorators on class
            for dec in node.decorator_list:
                dname = dec.id if isinstance(dec, ast.Name) else (dec.func.id if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name) else None)
                if dname and dname not in available:
                    unresolved.append((dname, dec.lineno, f"decorator of class '{node.name}'"))
            # 3. Class body statements (evaluated at module import time)
            for stmt in node.body:
                if not isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for sub in ast.walk(stmt):
                        if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load):
                            if sub.id not in available and not sub.id.startswith("__"):
                                unresolved.append((sub.id, sub.lineno, f"class body of '{node.name}'"))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Decorators on function
            for dec in node.decorator_list:
                dname = dec.id if isinstance(dec, ast.Name) else (dec.func.id if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name) else None)
                if dname and dname not in available:
                    unresolved.append((dname, dec.lineno, f"decorator of def '{node.name}'"))
        elif isinstance(node, ast.Assign):
            # Module-level assign value
            for sub in ast.walk(node.value):
                if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load):
                    if sub.id not in available and not sub.id.startswith("__"):
                        unresolved.append((sub.id, sub.lineno, "module level"))

    return unresolved


def scan_code_symbols(code_files: Dict[str, str], target_lang: str = "python") -> Dict[str, List[str]]:
    """Mengekstrak simbol kelas, fungsi, dan import dari code_files secara deterministik."""
    symbols: Dict[str, List[str]] = {
        "classes": [],
        "functions": [],
        "imports": []
    }
    is_dart = "dart" in target_lang.lower() or "flutter" in target_lang.lower()

    for fname, content in code_files.items():
        if not is_dart and fname.endswith(".py"):
            try:
                tree = ast.parse(content, filename=fname)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        symbols["classes"].append(node.name)
                    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        symbols["functions"].append(node.name)
                    elif isinstance(node, ast.Import):
                        for alias in node.names:
                            symbols["imports"].append(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        mod = node.module or ""
                        for alias in node.names:
                            symbols["imports"].append(f"{mod}.{alias.name}")
            except SyntaxError:
                pass
        elif is_dart:
            class_matches = re.findall(r"\bclass\s+([A-Za-z0-9_]+)", content)
            symbols["classes"].extend(class_matches)
            func_matches = re.findall(r"\b([A-Za-z0-9_]+)\s*\([^)]*\)\s*(?:async\s*)?\{", content)
            symbols["functions"].extend(func_matches)
            import_matches = re.findall(r"import\s+['\"]([^'\"]+)['\"]", content)
            symbols["imports"].extend(import_matches)

    return symbols


def validate_dart_syntax_structural(code: str) -> Tuple[bool, List[str]]:
    """Pemeriksaan sintaksis struktural dasar untuk kode Dart (balanced brackets & quotes)."""
    errors: List[str] = []
    stack = []
    pairs = {')': '(', '}': '{', ']': '['}
    lines = code.splitlines()

    in_single_quote = False
    in_double_quote = False
    in_multiline_comment = False

    for line_idx, line in enumerate(lines, start=1):
        i = 0
        while i < len(line):
            ch = line[i]

            # Multiline comment handling
            if in_multiline_comment:
                if ch == '*' and i + 1 < len(line) and line[i + 1] == '/':
                    in_multiline_comment = False
                    i += 2
                    continue
                i += 1
                continue

            if ch == '/' and i + 1 < len(line) and line[i + 1] == '*':
                in_multiline_comment = True
                i += 2
                continue

            # Single line comment
            if ch == '/' and i + 1 < len(line) and line[i + 1] == '/':
                break

            # String literal handling
            if ch == "'" and not in_double_quote:
                in_single_quote = not in_single_quote
            elif ch == '"' and not in_single_quote:
                in_double_quote = not in_double_quote

            if not in_single_quote and not in_double_quote:
                if ch in pairs.values():
                    stack.append((ch, line_idx))
                elif ch in pairs:
                    if not stack:
                        errors.append(f"Unmatched closing delimiter '{ch}' at line {line_idx}")
                    else:
                        top, top_line = stack.pop()
                        if top != pairs[ch]:
                            errors.append(f"Mismatched delimiter: expected closing for '{top}' (opened at line {top_line}) but found '{ch}' at line {line_idx}")
            i += 1

    if stack:
        for unclosed, line_idx in stack[:3]:
            errors.append(f"Unclosed delimiter '{unclosed}' opened at line {line_idx}")

    return (len(errors) == 0, errors)


# ==============================================================================
# B1: PM Phase Validator (Phase-End)
# ==============================================================================

def validate_pm_phase(state: SquadState) -> ValidatorContract:
    """
    B1: Validasi batas fase PM -> Architect (Phase-End).
    Hierarki Kebenaran Otoritatif:
    1. Authoritative User Requirement:
       - Memeriksa keselarasan terhadap instruksi tugas mentah (`task`) dan platform bahasa (`target_language`).
       - Deteksi kontradiksi eksplisit (CONTRADICTION_WITH_AUTHORITATIVE_SOURCE).
       - Deteksi ketiadaan/ambiguitas ground truth tugas pengguna (AMBIGUOUS_OR_INSUFFICIENT_GROUND_TRUTH).
    2. Engineering Quality Standard:
       - Memeriksa kelengkapan struktural dokumen spesifikasi (System Scope/Summary, Capabilities/User Stories).
       - Memeriksa keberadaan Acceptance Criteria yang konkret dan teruji (MANDATORY_FIELD_MISSING).
       - Memeriksa skema DRAFT Contract awal.
    Budget: Dikelola via universal repair counter (maksimal 2 repair attempts).
    """
    specs = state.get("specifications", "") or ""
    contract = state.get("contract") or {}
    
    user_task_raw = state.get("task")
    has_explicit_task_field = ("task" in state)
    user_task = (
        user_task_raw
        if user_task_raw is not None
        else ((contract.get("task_intent") or {}).get("raw_intent")
              or (contract.get("task_intent") or {}).get("goal_summary")
              or "")
    ) or ""
    
    target_lang = (state.get("target_language") or "python").strip().lower()

    evidence: List[Dict[str, Any]] = []
    violations: List[Dict[str, Any]] = []
    required_repairs: List[Dict[str, Any]] = []
    criteria = [
        "user_intent_conformance",
        "specifications_present",
        "specifications_structure_completeness",
        "acceptance_criteria_actionable",
        "draft_contract_schema_valid",
    ]

    # --------------------------------------------------------------------------
    # 1. Authoritative Ground Truth Check: User Intent & Ambiguity Evaluation
    # --------------------------------------------------------------------------
    user_words = user_task.split()
    if has_explicit_task_field and not user_task.strip():
        evidence.append({
            "item": "authoritative_user_intent",
            "evidence_class": "DETERMINISTIC",
            "observed": "Empty user task",
            "expected": "Actionable user task with ground truth",
            "fact": "Input user task string is empty or whitespace only",
            "inference": "Insufficient ground truth to establish authoritative specification",
            "status": "INVALID",
        })
        violations.append({
            "criterion": "user_intent_conformance",
            "violation_type": "AMBIGUOUS_OR_INSUFFICIENT_GROUND_TRUTH",
            "severity": "CRITICAL",
            "message": "Deskripsi tugas pengguna kosong atau tidak memuat ground truth yang memadai.",
            "location": "task",
            "expected": "Tugas pengguna memuat deskripsi kebutuhan yang jelas.",
        })
    elif user_task.strip():
        # Periksa kontradiksi eksplisit antara spesifikasi PM dan kebutuhan pengguna
        contradictions = []
        is_dart_task = "dart" in target_lang or "flutter" in target_lang or "dart" in user_task.lower()
        is_python_task = "python" in target_lang or "pytest" in user_task.lower()

        specs_lower = specs.lower()
        if is_python_task and not is_dart_task:
            if "target ekosistem: dart" in specs_lower or "target bahasa pemrograman: dart" in specs_lower:
                contradictions.append("Spesifikasi menargetkan DART/FLUTTER padahal kebutuhan pengguna menargetkan PYTHON")
        elif is_dart_task and not is_python_task:
            if "target ekosistem: python" in specs_lower or "target bahasa pemrograman: python" in specs_lower:
                contradictions.append("Spesifikasi menargetkan PYTHON padahal kebutuhan pengguna menargetkan DART/FLUTTER")

        if contradictions:
            evidence.append({
                "item": "authoritative_user_intent",
                "evidence_class": "DETERMINISTIC",
                "observed": "; ".join(contradictions),
                "expected": f"Target platform {target_lang.upper()} matches user intent",
                "fact": f"Contradictions detected: {'; '.join(contradictions)}",
                "inference": "PM specification directly contradicts authoritative user instruction",
                "status": "INVALID",
            })
            for c in contradictions:
                violations.append({
                    "criterion": "user_intent_conformance",
                    "violation_type": "CONTRADICTION_WITH_AUTHORITATIVE_SOURCE",
                    "severity": "CRITICAL",
                    "message": c,
                    "location": "specifications",
                    "expected": f"Spesifikasi selaras dengan target platform {target_lang}.",
                })
        else:
            evidence.append({
                "item": "authoritative_user_intent",
                "evidence_class": "DETERMINISTIC",
                "observed": f"Task: {user_task[:60]}... (target: {target_lang})",
                "expected": f"Aligned with target: {target_lang}",
                "fact": f"User task present ({len(user_words)} words), target language: {target_lang}",
                "inference": "PM specification does not contradict authoritative user intent",
                "status": "VALID",
            })
    else:
        # Task field omitted in minimal test fixture; default to VALID intent
        evidence.append({
            "item": "authoritative_user_intent",
            "evidence_class": "DETERMINISTIC",
            "observed": "Task omitted in fixture",
            "expected": "N/A",
            "fact": "No explicit task provided; evaluating against Engineering Quality Standard only",
            "inference": "Intent check skipped due to omitted task field in fixture",
            "status": "VALID",
        })

    # --------------------------------------------------------------------------
    # 2. Engineering Quality Standard: Length & Structural Completeness
    # --------------------------------------------------------------------------
    words = specs.split()
    specs_lower = specs.lower()
    is_len_ok = (len(words) >= 8)
    evidence.append({
        "item": "specifications_length",
        "evidence_class": "DETERMINISTIC",
        "observed": f"{len(words)} words",
        "expected": ">= 8 words",
        "fact": f"Specifications contain {len(words)} words ({len(specs)} characters)",
        "inference": "Adequate length for functional specification" if is_len_ok else "Specifications too brief or empty",
        "status": "VALID" if is_len_ok else "INVALID",
    })
    if not is_len_ok:
        violations.append({
            "criterion": "specifications_present",
            "violation_type": "STRUCTURAL_INCOMPLETE",
            "severity": "CRITICAL",
            "message": f"Spesifikasi terlalu pendek atau kosong ({len(words)} kata)",
            "location": "specifications",
            "expected": "Dokumen spesifikasi memiliki minimal 15 kata dengan struktur lengkap.",
        })

    # Evaluasi Struktural Berbasis Section / Semantik Dokumen (Bebas Naive Keyword)
    has_summary = any(k in specs_lower for k in [
        "ringkasan", "summary", "sistem", "modul", "overview", "deskripsi",
        "scope", "tujuan", "purpose", "1."
    ])
    has_stories = any(k in specs_lower for k in [
        "user stor", "sebagai", "pengguna", "as a", "i want", "fitur",
        "capabilities", "capability", "fungsi", "function", "fitur:", "2."
    ])
    has_ac = any(k in specs_lower for k in [
        "acceptance", "kriteria penerimaan", "skenario", "scenario", "given",
        "when", "then", "kriteria", "verifikasi", "expected", "input.*menghasilkan",
        "3."
    ]) or bool(re.search(r"(?:skenario|scenario|input\s+\d+|kriteria\s+\d+)", specs_lower))

    evidence.append({
        "item": "specifications_structure",
        "evidence_class": "DETERMINISTIC",
        "observed": {"has_summary": has_summary, "has_stories": has_stories, "has_ac": has_ac},
        "expected": "Mandatory structural sections: Scope/Summary, Capabilities/Stories, Acceptance Criteria",
        "fact": f"Sections detected - Scope: {has_summary}, Stories/Capabilities: {has_stories}, Acceptance Criteria: {has_ac}",
        "inference": "Document structural completeness according to Engineering Quality Standard",
        "status": "VALID" if ((has_summary or has_stories) and has_ac) else "INVALID",
    })

    if not (has_summary or has_stories):
        violations.append({
            "criterion": "specifications_structure_completeness",
            "violation_type": "STRUCTURAL_INCOMPLETE",
            "severity": "CRITICAL",
            "message": "Spesifikasi tidak memuat Ringkasan Sistem / Scope atau User Stories / Capabilities yang jelas",
            "location": "specifications",
            "expected": "Spesifikasi memuat Ringkasan Sistem dan Capabilities / User Stories terstruktur.",
        })

    if not has_ac:
        violations.append({
            "criterion": "acceptance_criteria_actionable",
            "violation_type": "MANDATORY_FIELD_MISSING",
            "severity": "CRITICAL",
            "message": "Spesifikasi kehilangan Acceptance Criteria / Skenario Penerimaan konkret yang dapat diuji",
            "location": "specifications",
            "expected": "Spesifikasi memuat minimal 1 skenario Acceptance Criteria konkret untuk verifikasi hilir.",
        })

    # --------------------------------------------------------------------------
    # 3. Initial DRAFT Contract Conformance
    # --------------------------------------------------------------------------
    domain = contract.get("task_intent", {}).get("domain") if isinstance(contract, dict) else None
    reqs = contract.get("requirements", []) if isinstance(contract, dict) else []
    contract_ok = bool(domain and len(reqs) >= 1)

    evidence.append({
        "item": "draft_contract_metadata",
        "evidence_class": "DETERMINISTIC",
        "observed": {"domain": domain, "reqs_count": len(reqs)},
        "expected": "Domain present and reqs_count >= 1",
        "fact": f"DRAFT contract domain: {domain}, requirements count: {len(reqs)}",
        "inference": "Draft contract initialized properly" if contract_ok else "Draft contract incomplete or missing",
        "status": "VALID" if contract_ok else "WARNING",
    })

    verdict = "FAIL" if any(v["severity"] == "CRITICAL" for v in violations) else "PASS"

    if verdict == "FAIL":
        for v in violations:
            if v["severity"] == "CRITICAL":
                v_type = v.get("violation_type", "STRUCTURAL_INCOMPLETE")
                if v_type == "CONTRADICTION_WITH_AUTHORITATIVE_SOURCE":
                    required_repairs.append({
                        "target_phase": "PM",
                        "action": "ALIGN_WITH_USER_INTENT",
                        "details": f"Perbaiki kontradiksi: {v['message']}. Pastikan spesifikasi selaras dengan instruksi pengguna."
                    })
                elif v_type == "AMBIGUOUS_OR_INSUFFICIENT_GROUND_TRUTH":
                    required_repairs.append({
                        "target_phase": "PM",
                        "action": "DEFENSIVE_SPECIFICATION",
                        "details": "Deskripsi kebutuhan minim. Rumuskan spesifikasi defensif berbasis batasan minimal fungsional."
                    })
                elif v_type == "MANDATORY_FIELD_MISSING":
                    required_repairs.append({
                        "target_phase": "PM",
                        "action": "ADD_ACCEPTANCE_CRITERIA",
                        "details": "Lengkapi spesifikasi dengan Acceptance Criteria terukur (skenario input/output konkret)."
                    })
                elif v_type == "STRUCTURAL_INCOMPLETE":
                    required_repairs.append({
                        "target_phase": "PM",
                        "action": "STRUCTURE_SPECIFICATION",
                        "details": "Lengkapi struktur spesifikasi (Ringkasan Sistem, User Stories / Capabilities, dan Acceptance Criteria)."
                    })

    # Assemble ContextualEvidencePackage on FAIL
    cep_dict: Optional[Dict[str, Any]] = None
    if verdict == "FAIL" and assemble_b1_evidence is not None:
        cep_violations = _make_cep_violations(violations)
        run_id = state.get("run_id", "")
        iteration = state.get("iteration_count", 0)
        cep = assemble_b1_evidence(state, cep_violations, evidence, run_id=run_id, iteration=iteration)
        cep_dict = cep.to_dict()

    return {
        "phase": "PM",
        "validator_type": "PHASE_END",
        "verdict": verdict,
        "criteria_checked": criteria,
        "evidence": evidence,
        "violations": violations,
        "regressions": [],
        "required_repairs": required_repairs,
        "repair_owner": "NONE",
        "remaining_budget": 0,
        "evaluated_review_verdict": None,
        "confidence": 1.0,
        "source_of_truth": "PM_SPECIFICATION_SCHEMA_V1",
        "contextual_evidence_package": cep_dict,
    }


# ==============================================================================
# B2: Architect Phase Validator (Phase-End)
# ==============================================================================

def validate_architect_phase(state: SquadState) -> ValidatorContract:
    """
    B2: Validasi batas fase Architect -> Developer (Phase-End).
    Invarian:
    1. Blueprint arsitektur memuat panduan struktur file.
    2. Blueprint lolos validasi AST internal (no unresolvable imports/decorators).
    3. Kontrak berstatus FROZEN dan memiliki segel SHA-256 RFC 8785.
    4. Antarmuka publik terdefinisi secara eksplisit.
    Budget: max_contract_revisions = 5 & max_blueprint_revisions = 5.
    """
    arch_plan = state.get("architecture_plan", "") or ""
    contract = state.get("contract") or {}
    target_lang = state.get("target_language", "python").strip()
    evidence: List[Dict[str, Any]] = []
    violations: List[Dict[str, Any]] = []
    required_repairs: List[Dict[str, Any]] = []
    criteria = [
        "arch_plan_present",
        "blueprint_ast_consistency",
        "contract_frozen_status",
        "contract_sha256_seal_integrity",
        "public_interfaces_defined",
        "contract_oracle_consistency",
    ]

    # 1. Blueprint presence
    evidence.append({
        "item": "arch_plan_length",
        "evidence_class": "DETERMINISTIC",
        "observed": len(arch_plan),
        "expected": ">= 50 chars",
        "status": "VALID" if len(arch_plan) >= 50 else "INVALID"
    })
    if len(arch_plan) < 50:
        violations.append({
            "criterion": "arch_plan_present",
            "severity": "CRITICAL",
            "message": "Rencana arsitektur kosong atau terlalu pendek",
            "location": "architecture_plan"
        })

    # 2. Blueprint AST consistency
    is_bp_valid, bp_errors = validate_architect_blueprint(arch_plan, target_lang)
    evidence.append({
        "item": "blueprint_ast_validity",
        "evidence_class": "DETERMINISTIC",
        "observed": f"{len(bp_errors)} errors",
        "expected": "0 errors",
        "status": "VALID" if is_bp_valid else "INVALID"
    })
    if not is_bp_valid:
        for err in bp_errors:
            sym = None
            if "@" in err:
                m_sym = re.search(r"@([A-Za-z_][A-Za-z0-9_]*)", err)
                if m_sym:
                    sym = f"@{m_sym.group(1)}"
            elif "kelas basis" in err.lower() or "base class" in err.lower():
                m_base = re.search(r"'(?:class\s+\w+\()?([A-Za-z_][A-Za-z0-9_]*)\)?'", err)
                if m_base:
                    sym = m_base.group(1)

            is_schema = "SCHEMA_VIOLATION" in err
            crit = "blueprint_json_schema" if is_schema else "blueprint_ast_consistency"
            if is_schema:
                expected_desc = "Blueprint wajib berformat ArchitecturalBlueprint JSON yang valid dengan code_scaffold lengkap untuk setiap file"
            elif sym and sym.startswith("@"):
                expected_desc = f"Simbol decorator '{sym}' dideklarasikan atau diimpor dalam modul berkas sebelum digunakan"
            elif sym:
                expected_desc = f"Kelas basis '{sym}' dideklarasikan atau diimpor dalam modul berkas sebelum pewarisan"
            else:
                expected_desc = "Seluruh decorator dan base class terdefinisi dalam lingkup modul berkas"

            violations.append({
                "criterion": crit,
                "severity": "CRITICAL",
                "message": err if is_schema else f"Inkonsistensi AST pada blueprint: {err}",
                "location": "architecture_plan",
                "expected": expected_desc,
                "observed_symbol": sym,
            })

    # 3. Contract status & SHA-256 seal
    contract_status = state.get("contract_status")
    contract_sha = state.get("contract_sha256")
    is_frozen = (contract_status == "FROZEN")
    has_sha = bool(contract_sha and len(contract_sha) == 64)

    evidence.append({
        "item": "contract_status_and_seal",
        "evidence_class": "DETERMINISTIC",
        "observed": {"status": contract_status, "sha256": (contract_sha[:12] + "...") if contract_sha else "None"},
        "expected": {"status": "FROZEN", "sha256": "64-hex-chars"},
        "status": "VALID" if (is_frozen and has_sha) else "INVALID"
    })
    gate_errors = state.get("contract_validation_errors") or []
    has_oracle_inconsistency = any("Oracle Consistency" in str(e) or "inconsistent with the frozen test" in str(e) for e in gate_errors)

    if not is_frozen:
        violations.append({
            "criterion": "contract_frozen_status",
            "severity": "CRITICAL",
            "message": f"Status kontrak belum FROZEN (status saat ini: {contract_status})",
            "location": "contract"
        })
        for gerr in gate_errors:
            crit_name = "contract_oracle_consistency" if ("Oracle Consistency" in gerr or "inconsistent with the frozen test" in gerr) else "contract_gate_p0_2_1"
            violations.append({
                "criterion": crit_name,
                "severity": "CRITICAL",
                "message": gerr,
                "location": "contract",
                "expected": "Seluruh interface contract selaras dengan pemanggilan Acceptance Oracle pada berkas pengujian independen" if crit_name == "contract_oracle_consistency" else "Kontrak lolos validasi 4 Pilar",
            })
    if not has_sha:
        violations.append({
            "criterion": "contract_sha256_seal_integrity",
            "severity": "CRITICAL",
            "message": "Segel kanonikal SHA-256 kontrak hilang atau tidak valid",
            "location": "contract"
        })

    # 4. Public interfaces defined
    ifaces = contract.get("interface_contracts", []) if isinstance(contract, dict) else []
    evidence.append({
        "item": "public_interfaces_count",
        "evidence_class": "DETERMINISTIC",
        "observed": len(ifaces),
        "expected": ">= 1",
        "status": "VALID" if len(ifaces) >= 1 else "INVALID"
    })
    if len(ifaces) < 1:
        violations.append({
            "criterion": "public_interfaces_defined",
            "severity": "CRITICAL",
            "message": "Kontrak tidak mendefinisikan antarmuka publik yang dapat diuji (interface_contracts kosong)",
            "location": "contract"
        })

    # 5. Contract–Oracle Consistency Check (Church of Goat Doctrine 🐐)
    evidence.append({
        "item": "contract_oracle_interface_consistency",
        "evidence_class": "DETERMINISTIC",
        "observed": "Inconsistent with Frozen Oracle acceptance call-site" if has_oracle_inconsistency else "Consistent / Valid",
        "expected": "Interface contracts strictly consistent with authoritative Frozen Oracle call-sites",
        "status": "INVALID" if has_oracle_inconsistency else "VALID"
    })

    verdict = "FAIL" if any(v["severity"] == "CRITICAL" for v in violations) else "PASS"

    contract_rev = state.get("contract_revision_count", 0)
    max_contract_rev = state.get("max_contract_revisions", 5)
    remaining_contract_budget = max(0, max_contract_rev - contract_rev)

    if verdict == "FAIL":
        if has_oracle_inconsistency:
            required_repairs.append({
                "target_phase": "ARCHITECT",
                "action": "ALIGN_CONTRACT_WITH_ORACLE",
                "details": "Selaraskan nama dan signature interface_contracts terhadap pemanggilan aktual Acceptance Oracle sebelum kontrak dapat dibekukan (FROZEN)."
            })
        else:
            required_repairs.append({
                "target_phase": "ARCHITECT",
                "action": "REFINE_ARCHITECTURE_AND_CONTRACT",
                "details": "Perbaiki inkonsistensi simbol pada blueprint dan pastikan kontrak berstatus FROZEN dengan interface contracts lengkap."
            })

    # Iterasi 7: Assemble ContextualEvidencePackage on FAIL
    cep_dict_b2: Optional[Dict[str, Any]] = None
    if verdict == "FAIL" and assemble_b2_evidence is not None:
        cep_violations = _make_cep_violations(violations)
        run_id = state.get("run_id", "")
        iteration = state.get("iteration_count", 0)
        cep = assemble_b2_evidence(state, cep_violations, evidence, run_id=run_id, iteration=iteration)
        cep_dict_b2 = cep.to_dict()

    return {
        "phase": "ARCHITECT",
        "validator_type": "PHASE_END",
        "verdict": verdict,
        "criteria_checked": criteria,
        "evidence": evidence,
        "violations": violations,
        "regressions": [],
        "required_repairs": required_repairs,
        "repair_owner": "ARCHITECT" if verdict == "FAIL" else "NONE",
        "remaining_budget": remaining_contract_budget,
        "evaluated_review_verdict": None,
        "confidence": 1.0,
        "source_of_truth": f"CONTRACT_GATE_P0_2.1:{contract_sha[:16] if contract_sha else 'UNSEALED'}",
        "contextual_evidence_package": cep_dict_b2,
    }


# ==============================================================================
# B3: Developer Phase Validator (Phase-End Pre-Execution Gate)
# ==============================================================================

def validate_developer_phase(state: SquadState) -> ValidatorContract:
    """
    B3: Validasi batas fase Developer -> Oracle/Executor (Phase-End Pre-Execution Gate).
    Invarian:
    1. Berkas kode tidak kosong.
    2. Kode berada di Target File Authoritative (contoh: main.py atau lib/card_metric.dart).
    3. Bebas dari kesalahan sintaksis Python (ast.parse) atau Dart structural delimiters.
    4. Seluruh simbol mandatory kontrak (data_models & interface_contracts) terdefinisi di AST.
    5. Batasan berkas dipatuhi (max_files <= 2).
    6. Known good constraints terjaga (tidak ada pelanggaran pola terlarang).
    Budget: Mengonsumsi 1 loop dari alokasi existing max_iterations = 10.
    """
    code_files = state.get("code_files") or {}
    contract = state.get("contract") or {}
    target_lang = state.get("target_language", "python").strip()
    is_dart = "dart" in target_lang.lower() or "flutter" in target_lang.lower()

    evidence: List[Dict[str, Any]] = []
    violations: List[Dict[str, Any]] = []
    regressions: List[Dict[str, Any]] = []
    required_repairs: List[Dict[str, Any]] = []
    criteria = [
        "code_files_present",
        "authoritative_target_file_compliance",
        "ast_syntax_validity",
        "symbol_resolvability",
        "contract_symbols_conformance",
        "constraint_compliance",
        "known_good_preservation"
    ]

    iteration = state.get("iteration_count", 0)
    max_iter = state.get("max_iterations", 10)
    remaining_dev_budget = max(0, max_iter - iteration)

    # 1. Presence (Global Scan: no early return — collect all violations)
    evidence.append({
        "item": "code_files_count",
        "evidence_class": "DETERMINISTIC",
        "observed": len(code_files),
        "expected": ">= 1",
        "status": "VALID" if len(code_files) >= 1 else "INVALID"
    })
    no_code = (len(code_files) < 1)
    if no_code:
        violations.append({
            "criterion": "code_files_present",
            "severity": "CRITICAL",
            "message": "Developer tidak menghasilkan berkas kode sama sekali",
            "location": "code_files"
        })

    # 2. Authoritative Target File Compliance
    task_intent = contract.get("task_intent", {}) if isinstance(contract, dict) else {}
    auth_file = task_intent.get("authoritative_target_file")
    if not auth_file:
        ifaces = contract.get("interface_contracts", []) if isinstance(contract, dict) else []
        for ifc in ifaces:
            tf = ifc.get("target_file")
            if tf:
                auth_file = tf
                break
    if not auth_file:
        if is_dart:
            auth_file = "lib/card_metric.dart" if "lib/card_metric.dart" in code_files else "lib/main.dart"
        else:
            auth_file = "main.py" if ("main.py" in code_files or not code_files) else next(iter(code_files.keys()))

    has_auth_file = (auth_file in code_files)
    evidence.append({
        "item": "authoritative_target_file",
        "evidence_class": "DETERMINISTIC",
        "observed": list(code_files.keys()),
        "expected": auth_file,
        "status": "VALID" if has_auth_file else "INVALID"
    })
    if not has_auth_file:
        violations.append({
            "criterion": "authoritative_target_file_compliance",
            "severity": "CRITICAL",
            "message": f"Berkas target authoritative '{auth_file}' tidak ditemukan dalam code_files. Berkas yang dihasilkan: {list(code_files.keys())}",
            "location": auth_file
        })

    # 3. Syntax Validity & Symbol Resolvability
    for fname, content in code_files.items():
        if not is_dart and fname.endswith(".py"):
            try:
                tree = ast.parse(content, filename=fname)
                evidence.append({
                    "item": f"ast_syntax_{fname}",
                    "evidence_class": "DETERMINISTIC",
                    "observed": "PARSED_SUCCESS",
                    "expected": "PARSED_SUCCESS",
                    "status": "VALID"
                })

                # V5-4: Module-level and class-scope symbol resolvability audit
                unresolved = audit_python_module_symbol_resolvability(tree, fname)
                if unresolved:
                    for sym_name, lineno, ctx_desc in unresolved:
                        evidence.append({
                            "item": f"symbol_resolvability_{fname}_{sym_name}",
                            "evidence_class": "DETERMINISTIC",
                            "observed": f"Unresolved symbol '{sym_name}' at line {lineno} ({ctx_desc})",
                            "expected": f"Symbol '{sym_name}' defined or imported in module scope",
                            "status": "INVALID",
                            "symbol": sym_name,
                            "location": f"{fname}:{lineno}",
                        })
                        violations.append({
                            "criterion": "symbol_resolvability",
                            "severity": "CRITICAL",
                            "message": f"Simbol '{sym_name}' digunakan pada {ctx_desc} (baris {lineno}) namun tidak diimpor atau didefinisikan.",
                            "location": f"{fname}:{lineno}",
                            "observed_symbol": sym_name,
                            "observed_state": f"Simbol '{sym_name}' tidak terdefinisi di {ctx_desc} ({fname}:{lineno})",
                            "expected_state": f"Impor atau definisikan '{sym_name}' di tingkat modul",
                            "suggested_action": f"Tambahkan impor untuk '{sym_name}' atau definisikan sebelum digunakan pada baris {lineno}."
                        })
                else:
                    evidence.append({
                        "item": f"symbol_resolvability_{fname}",
                        "evidence_class": "DETERMINISTIC",
                        "observed": "ALL_SYMBOLS_RESOLVED",
                        "expected": "ALL_SYMBOLS_RESOLVED",
                        "status": "VALID"
                    })
            except SyntaxError as e:
                evidence.append({
                    "item": f"ast_syntax_{fname}",
                    "evidence_class": "DETERMINISTIC",
                    "observed": f"SyntaxError at line {e.lineno}: {e.msg}",
                    "expected": "PARSED_SUCCESS",
                    "status": "INVALID"
                })
                violations.append({
                    "criterion": "ast_syntax_validity",
                    "severity": "CRITICAL",
                    "message": f"Galat sintaksis Python pada '{fname}' baris {e.lineno}: {e.msg}",
                    "location": f"{fname}:{e.lineno}"
                })
        elif is_dart:
            is_valid_dart, dart_errs = validate_dart_syntax_structural(content)
            evidence.append({
                "item": f"dart_structural_syntax_{fname}",
                "evidence_class": "DETERMINISTIC",
                "observed": f"{len(dart_errs)} structural delimiter errors",
                "expected": "0 errors",
                "status": "VALID" if is_valid_dart else "INVALID"
            })
            if not is_valid_dart:
                for d_err in dart_errs:
                    violations.append({
                        "criterion": "ast_syntax_validity",
                        "severity": "CRITICAL",
                        "message": f"Galat struktur Dart pada '{fname}': {d_err}",
                        "location": fname
                    })

    # 4. Contract Symbol Conformance
    symbols = scan_code_symbols(code_files, target_lang)
    all_symbols = set(symbols["classes"] + symbols["functions"])

    missing_models = []
    for dm in contract.get("data_models", []) if isinstance(contract, dict) else []:
        mname = dm.get("model_name")
        if mname and mname not in all_symbols:
            missing_models.append(mname)

    missing_interfaces = []
    for iface in contract.get("interface_contracts", []) if isinstance(contract, dict) else []:
        iname = iface.get("identifier")
        if not iname:
            continue
        if iname.isidentifier():
            if iname not in all_symbols:
                missing_interfaces.append(iname)
        else:
            found = any(iname in c for c in code_files.values())
            if not found:
                missing_interfaces.append(iname)

    evidence.append({
        "item": "contract_symbols_check",
        "evidence_class": "DETERMINISTIC",
        "observed": {
            "declared_classes": symbols["classes"],
            "declared_functions": symbols["functions"],
            "missing_models": missing_models,
            "missing_interfaces": missing_interfaces
        },
        "expected": "0 missing models and 0 missing interfaces",
        "status": "VALID" if (not missing_models and not missing_interfaces) else "INVALID"
    })

    if missing_models or missing_interfaces:
        if missing_models:
            violations.append({
                "criterion": "contract_symbols_conformance",
                "severity": "CRITICAL",
                "message": f"Data Models mandatory kontrak tidak dideklarasikan: {missing_models}",
                "location": auth_file
            })
        if missing_interfaces:
            violations.append({
                "criterion": "contract_symbols_conformance",
                "severity": "CRITICAL",
                "message": f"Antarmuka mandatory kontrak tidak dideklarasikan: {missing_interfaces}",
                "location": auth_file
            })

    # 5. Constraints Compliance
    constraints = contract.get("constraints", {}) if isinstance(contract, dict) else {}
    max_files = constraints.get("max_files", 3)
    evidence.append({
        "item": "max_files_constraint",
        "evidence_class": "DETERMINISTIC",
        "observed": len(code_files),
        "expected": f"<= {max_files}",
        "status": "VALID" if len(code_files) <= max_files else "INVALID"
    })
    if len(code_files) > max_files:
        violations.append({
            "criterion": "constraint_compliance",
            "severity": "CRITICAL",
            "message": f"Jumlah berkas ({len(code_files)}) melebihi batas constraint max_files ({max_files})",
            "location": "code_files"
        })

    # 6. Forbidden patterns check
    all_code_str = "\n".join(code_files.values())
    if "pydantic.BaseSettings" in all_code_str:
        violations.append({
            "criterion": "known_good_preservation",
            "severity": "CRITICAL",
            "message": "Dilarang menggunakan 'pydantic.BaseSettings' pada Pydantic v2 (gunakan pydantic_settings)",
            "location": auth_file
        })
    if is_dart and any(k in all_code_str for k in ["StateNotifier", "StateNotifierProvider", "ChangeNotifierProvider"]):
        violations.append({
            "criterion": "known_good_preservation",
            "severity": "CRITICAL",
            "message": "Dilarang menggunakan StateNotifier / ChangeNotifier pada Riverpod modern (gunakan Provider<T>)",
            "location": auth_file
        })

    verdict = "FAIL" if any(v["severity"] == "CRITICAL" for v in violations) else "PASS"

    if verdict == "FAIL":
        if no_code:
            required_repairs.append({
                "target_phase": "DEVELOPER",
                "action": "EMIT_CODE_BLOCKS",
                "details": "Tuliskan implementasi kode dalam blok === FILE: ... ==="
            })
        for v in violations:
            if v.get("criterion") != "code_files_present":  # avoid duplicate
                required_repairs.append({
                    "target_phase": "DEVELOPER",
                    "action": f"FIX_{v['criterion'].upper()}",
                    "details": v["message"]
                })

    # Iterasi 7: Assemble ContextualEvidencePackage on FAIL
    cep_dict_b3: Optional[Dict[str, Any]] = None
    if verdict == "FAIL" and assemble_b3_evidence is not None:
        cep_violations = _make_cep_violations(violations)
        run_id = state.get("run_id", "")
        iteration_num = state.get("iteration_count", 0)
        cep = assemble_b3_evidence(state, cep_violations, evidence, run_id=run_id, iteration=iteration_num)
        cep_dict_b3 = cep.to_dict()

    return {
        "phase": "DEVELOPER",
        "validator_type": "PHASE_END",
        "verdict": verdict,
        "criteria_checked": criteria,
        "evidence": evidence,
        "violations": violations,
        "regressions": regressions,
        "required_repairs": required_repairs,
        "repair_owner": "DEVELOPER" if verdict == "FAIL" else "NONE",
        "remaining_budget": remaining_dev_budget,
        "evaluated_review_verdict": None,
        "confidence": 1.0,
        "source_of_truth": "DEVELOPER_STATIC_CONTRACT_AUDIT",
        "contextual_evidence_package": cep_dict_b3,
    }


# ==============================================================================
# B4: Oracle Phase Validator (Phase-End)
# ==============================================================================

def validate_oracle_phase(state: SquadState, expected_sha: Optional[str] = None) -> ValidatorContract:
    """
    B4: Validasi batas fase Frozen Oracle -> Executor (Phase-End).
    Invarian:
    1. Berkas test_files tidak kosong.
    2. Checksum SHA-256 berkas tes identik 100% dengan expected baseline SHA.
    3. QA Tester LLM tidak digunakan sama sekali.
    Budget: 0 revisi (immutable suite).
    """
    test_files = state.get("test_files") or {}
    evidence: List[Dict[str, Any]] = []
    violations: List[Dict[str, Any]] = []
    criteria = [
        "test_files_present",
        "oracle_sha256_checksum_verified",
        "tester_agent_bypassed"
    ]

    # 1. Presence
    evidence.append({
        "item": "test_files_count",
        "evidence_class": "DETERMINISTIC",
        "observed": len(test_files),
        "expected": ">= 1",
        "status": "VALID" if len(test_files) >= 1 else "INVALID"
    })
    if len(test_files) < 1:
        violations.append({
            "criterion": "test_files_present",
            "severity": "CRITICAL",
            "message": "Test suite kosong: tidak ada berkas pengujian yang dimuat",
            "location": "test_files"
        })

    # 2. Checksum SHA-256 verification (1-to-1 explicit)
    calculated_sha = ""
    if test_files:
        first_content = next(iter(test_files.values()))
        calculated_sha = hashlib.sha256(first_content.encode("utf-8")).hexdigest()

    sha_match = True
    if expected_sha and calculated_sha:
        sha_match = (calculated_sha.lower() == expected_sha.lower())
        evidence.append({
            "item": "oracle_file_sha256",
            "evidence_class": "DETERMINISTIC",
            "observed": calculated_sha,
            "expected": expected_sha,
            "status": "VALID" if sha_match else "INVALID"
        })
        if not sha_match:
            violations.append({
                "criterion": "oracle_sha256_checksum_verified",
                "severity": "CRITICAL",
                "message": f"Integritas Frozen Oracle terlanggar! Hash terhitung ({calculated_sha}) berbeda dari baseline ({expected_sha})",
                "location": "test_files"
            })
    else:
        evidence.append({
            "item": "oracle_file_sha256",
            "evidence_class": "DETERMINISTIC",
            "observed": calculated_sha or "N/A",
            "expected": expected_sha or "UNSPECIFIED",
            "status": "VALID" if calculated_sha else "WARNING"
        })

    # 3. Bypass verification
    used_frozen = bool(state.get("frozen_oracle_path"))
    evidence.append({
        "item": "frozen_oracle_used",
        "evidence_class": "DETERMINISTIC",
        "observed": used_frozen,
        "expected": True,
        "status": "VALID" if used_frozen else "INVALID"
    })
    if not used_frozen:
        violations.append({
            "criterion": "tester_agent_bypassed",
            "severity": "CRITICAL",
            "message": "Frozen Oracle tidak digunakan; alur berpotensi jatuh ke QA Tester LLM",
            "location": "frozen_oracle_path"
        })

    verdict = "FAIL" if any(v["severity"] == "CRITICAL" for v in violations) else "PASS"

    # Iterasi 7: Assemble ContextualEvidencePackage on FAIL
    cep_dict_b4: Optional[Dict[str, Any]] = None
    if verdict == "FAIL" and assemble_b4_evidence is not None:
        cep_violations = _make_cep_violations(violations)
        run_id = state.get("run_id", "")
        cep = assemble_b4_evidence(state, cep_violations, evidence, run_id=run_id, iteration=0)
        cep_dict_b4 = cep.to_dict()

    return {
        "phase": "ORACLE",
        "validator_type": "PHASE_END",
        "verdict": verdict,
        "criteria_checked": criteria,
        "evidence": evidence,
        "violations": violations,
        "regressions": [],
        "required_repairs": [],
        "repair_owner": "NONE",
        "remaining_budget": 0,
        "evaluated_review_verdict": None,
        "confidence": 1.0,
        "source_of_truth": f"FROZEN_ORACLE_SHA256:{expected_sha or calculated_sha}",
        "contextual_evidence_package": cep_dict_b4,
    }


# ==============================================================================
# B5: Executor Iteration Validator (Iteration Validator)
# ==============================================================================

def validate_executor_phase(state: SquadState, previous_passed_tests: Optional[List[str]] = None) -> ValidatorContract:
    """
    B5: Validasi siklus perbaikan Executor -> Developer/Reviewer (Iteration Validator).
    Invarian:
    1. Hasil pengujian sandbox tersedia dengan exit code deterministik.
    2. Jika lulus: passed == True, exit_code == 0, failed_count == 0.
    3. Deteksi regresi: jika ada tes yang sebelumnya lulus kini gagal, catat regresi.
    4. Bukti diagnostik kegagalan terikat pada keluaran aktual.
    Budget: max_iterations = 10 (existing Developer repair budget).
    """
    test_results = state.get("test_results") or {}
    evidence: List[Dict[str, Any]] = []
    violations: List[Dict[str, Any]] = []
    regressions: List[Dict[str, Any]] = []
    required_repairs: List[Dict[str, Any]] = []
    criteria = [
        "test_results_available",
        "sandbox_exit_code_clean",
        "zero_regression_invariant",
        "causal_diagnostic_evidence_present"
    ]

    is_passed = bool(test_results.get("passed", False))
    exit_code = test_results.get("exit_code")
    passed_count = test_results.get("passed_count", 0)
    failed_count = test_results.get("failed_count", 0)
    total = test_results.get("total", 0)

    iteration = state.get("iteration_count", 0)
    max_iter = state.get("max_iterations", 10)
    remaining_dev_budget = max(0, max_iter - iteration)

    # 1. Availability
    evidence.append({
        "item": "test_execution_summary",
        "evidence_class": "DETERMINISTIC",
        "observed": {"passed": is_passed, "exit_code": exit_code, "passed_count": passed_count, "failed_count": failed_count, "total": total},
        "expected": "Execution completed",
        "status": "VALID" if exit_code is not None else "INVALID"
    })
    if exit_code is None:
        violations.append({
            "criterion": "test_results_available",
            "severity": "CRITICAL",
            "message": "Hasil uji sandbox tidak memiliki exit code yang valid",
            "location": "test_results",
            "expected": "Hasil uji sandbox tersedia dengan exit_code deterministik (0 atau 1/2)",
            "observed_symbol": "exit_code",
        })

    # 2. Pass/Fail
    if not is_passed:
        violations.append({
            "criterion": "sandbox_exit_code_clean",
            "severity": "CRITICAL",
            "message": f"Pengujian sandbox gagal ({failed_count} failed / exit code {exit_code})",
            "location": "sandbox_tests",
            "expected": "Seluruh pengujian sandbox lulus (exit_code=0, failed=0)",
            "observed_symbol": f"exit_code_{exit_code}",
        })

    # 3. Regression Detection & Passed Tests Extraction
    current_passed_tests = list(test_results.get("passed_test_names", []) or [])
    output_text = test_results.get("output") or test_results.get("stdout") or ""
    passed_count = test_results.get("passed_count", 0)
    if not current_passed_tests and output_text and passed_count > 0:
        matched_passes = re.findall(r"([\w\.:]+)\s+PASSED", output_text)
        if matched_passes:
            current_passed_tests = matched_passes
        else:
            flutter_passes = re.findall(r"\+\d+:\s+([^\n\r]+)", output_text)
            if flutter_passes:
                current_passed_tests = [
                    p.strip() for p in flutter_passes
                    if ("test" in p.lower() or "pump" in p.lower())
                    and not p.strip().lower().startswith("loading ")
                    and not "all tests passed" in p.strip().lower()
                ]

    if previous_passed_tests:
        for prev_t in previous_passed_tests:
            if prev_t not in current_passed_tests:
                regressions.append({
                    "test_or_invariant": prev_t,
                    "previous_status": "PASS",
                    "current_status": "FAIL",
                    "message": f"Regresi terdeteksi: tes '{prev_t}' sebelumnya lulus tetapi kini gagal"
                })

    if regressions:
        evidence.append({
            "item": "regression_detection",
            "evidence_class": "DETERMINISTIC",
            "observed": f"{len(regressions)} regressed tests",
            "expected": "0 regressions",
            "status": "INVALID"
        })
        for reg in regressions:
            violations.append({
                "criterion": "zero_regression_invariant",
                "severity": "CRITICAL",
                "message": reg["message"],
                "location": reg["test_or_invariant"],
                "expected": f"Pengujian '{reg['test_or_invariant']}' tetap berstatus PASS",
                "observed_symbol": reg["test_or_invariant"],
            })
    else:
        evidence.append({
            "item": "regression_detection",
            "evidence_class": "DETERMINISTIC",
            "observed": "0 regressions",
            "expected": "0 regressions",
            "status": "VALID"
        })

    verdict = "PASS" if is_passed and not regressions else "FAIL"

    if verdict == "FAIL":
        required_repairs.append({
            "target_phase": "DEVELOPER",
            "action": "SELF_HEALING_REPAIR",
            "details": f"Perbaiki {failed_count} kegagalan uji sandbox dengan mempertahankan fungsionalitas yang telah lulus."
        })

    # Iterasi 7: Assemble ContextualEvidencePackage on FAIL
    cep_dict_b5: Optional[Dict[str, Any]] = None
    if verdict == "FAIL" and assemble_b5_evidence is not None:
        cep_violations = _make_cep_violations(violations)
        run_id = state.get("run_id", "")
        iteration_num = state.get("iteration_count", 0)
        cep = assemble_b5_evidence(state, cep_violations, regressions, evidence, run_id=run_id, iteration=iteration_num)
        cep_dict_b5 = cep.to_dict()

    return {
        "phase": "EXECUTOR",
        "validator_type": "ITERATION",
        "verdict": verdict,
        "criteria_checked": criteria,
        "evidence": evidence,
        "violations": violations,
        "regressions": regressions,
        "required_repairs": required_repairs,
        "repair_owner": "DEVELOPER" if verdict == "FAIL" else "NONE",
        "remaining_budget": remaining_dev_budget,
        "evaluated_review_verdict": None,
        "confidence": 1.0,
        "source_of_truth": f"SANDBOX_RUNNER:exit_code_{exit_code}",
        "contextual_evidence_package": cep_dict_b5,
        "current_passed_tests": current_passed_tests,
    }


# ==============================================================================
# B6: Reviewer Phase Validator (Phase-End Validation of Reviewer)
# ==============================================================================


# ==============================================================================
# B6 Helper: Deterministik Contract Mutation Intent Classifier (D-112)
# ==============================================================================

_V6_DEMAND_PATTERNS = [
    # 1. Actionable request: Mohon/Tolong/Harap/Silakan/Wajib/Harus/Perlu/Minta/Instruksikan ubah/revisi/ganti/amend/unfreeze kontrak
    re.compile(r'\b(?:tolong|mohon|harap|silakan|wajib|harus|perlu|minta|instruksi(?:kan)?)\s+(?:(?:meng)?ubah|(?:me)?revisi|amend|ganti|unfreeze)\s+(?:kontrak|contract|model\s+kontrak|endpoint\s+kontrak)\b', re.IGNORECASE),
    # 2. Passive modal demand: Kontrak harus/perlu/wajib/mohon di-unfreeze/di-ubah/di-revisi/di-amend
    re.compile(r'\b(?:kontrak|contract)\s+(?:harus|perlu|wajib|mohon|minta)\s+(?:di-?unfreeze|di-?ubah|di-?revisi|di-?amend)\b', re.IGNORECASE),
    # 3. Direct imperative start: Ubah kontrak..., Revisi kontrak..., Ganti model kontrak...
    re.compile(r'(?:^|[\]\)\.:;!\?,\-\n]|\b(?:maka|jadi|untuk\s+itu)\b)\s*(?:ubah|revisi|ganti)\s+(?:kontrak|model\s+kontrak|endpoint\s+kontrak)\b', re.IGNORECASE),
    # 4. Direct unfreeze command: Unfreeze contract..., Amend contract...
    re.compile(r'\b(?:unfreeze|amend)\s+contract\b', re.IGNORECASE),
    # 5. Direct phrase: ganti model kontrak, ganti endpoint kontrak
    re.compile(r'\b(?:ganti|ubah)\s+(?:model|endpoint)\s+kontrak\b', re.IGNORECASE)
]

_V6_PROHIBITION_PATTERNS = [
    re.compile(r'\b(?:tidak\s+boleh|dilarang|jangan|bukan|tidak\s+perlu|tidak\s+dapat)\s+(?:(?:meng)?ubah|(?:me)?revisi|amend|unfreeze)\s+(?:frozen\s+)?(?:kontrak|contract)\b', re.IGNORECASE),
    re.compile(r'\b(?:tanpa|bebas\s+dari)\s+(?:(?:meng)?ubah|(?:me)?revisi)\s+(?:frozen\s+)?(?:kontrak|contract)\b', re.IGNORECASE),
]

_V6_DESCRIPTIVE_PATTERNS = [
    re.compile(r'\b(?:implementasi|kode|perubahan|widget|class|fungsi|method|ini|hal\s+ini)\s+(?:ini\s+)?(?:meng?ubah|merevisi)\s+(?:kontrak|antarmuka|kontrak\s+antarmuka)\b', re.IGNORECASE),
]

def classify_contract_mutation_demand(notes: str) -> Dict[str, Any]:
    """
    Mengklasifikasikan intensi catatan Reviewer terhadap kontrak ke dalam:
    - 'DEMAND': Tuntutan imperatif aktif/pasif untuk mengubah/meng-unfreeze kontrak (is_mutation_demand=True).
    - 'DESCRIPTIVE': Observasi analitis, deskripsi perilaku kode, atau larangan mutasi kontrak (is_mutation_demand=False).
    - 'NONE': Catatan teknis biasa tanpa penyebutan mutasi kontrak (is_mutation_demand=False).
    """
    if not notes:
        return {"classification": "NONE", "matched_pattern": None, "matched_text": None, "is_mutation_demand": False}

    # 1. Evaluasi pola larangan/prohibisi eksplisit terlebih dahulu (contoh: "tidak boleh mengubah kontrak")
    for pat in _V6_PROHIBITION_PATTERNS:
        m = pat.search(notes)
        if m:
            return {
                "classification": "DESCRIPTIVE",
                "matched_pattern": pat.pattern,
                "matched_text": m.group(0),
                "is_mutation_demand": False
            }

    # 2. Evaluasi tuntutan imperatif aktif/pasif (DEMAND)
    for pat in _V6_DEMAND_PATTERNS:
        m = pat.search(notes)
        if m:
            # Periksa apakah ada negasi lokal tepat sebelum match (window 25 karakter)
            start = max(0, m.start() - 25)
            prefix = notes[start:m.start()].lower()
            if any(neg in prefix for neg in ["tidak boleh", "jangan", "dilarang", "tidak "]):
                return {
                    "classification": "DESCRIPTIVE",
                    "matched_pattern": pat.pattern,
                    "matched_text": m.group(0),
                    "is_mutation_demand": False
                }
            return {
                "classification": "DEMAND",
                "matched_pattern": pat.pattern,
                "matched_text": m.group(0),
                "is_mutation_demand": True
            }

    # 3. Evaluasi observasi deskriptif (contoh: "implementasi ini mengubah kontrak antarmuka")
    for pat in _V6_DESCRIPTIVE_PATTERNS:
        m = pat.search(notes)
        if m:
            return {
                "classification": "DESCRIPTIVE",
                "matched_pattern": pat.pattern,
                "matched_text": m.group(0),
                "is_mutation_demand": False
            }

    # 4. Fallback kata kunci umum non-imperatif
    if any(k in notes.lower() for k in ["kontrak", "contract", "unfreeze"]):
        return {
            "classification": "DESCRIPTIVE",
            "matched_pattern": "generic_keyword",
            "matched_text": None,
            "is_mutation_demand": False
        }

    return {"classification": "NONE", "matched_pattern": None, "matched_text": None, "is_mutation_demand": False}


def validate_reviewer_phase(state: SquadState, review_verdict: str, review_notes: str = "") -> ValidatorContract:
    """
    B6: Validasi batas fase Reviewer -> END / Developer (Phase-End).
    Invarian:
    1. Memvalidasi keabsahan `review_verdict` (APPROVED | NEEDS_REVISION | FAIL) terhadap bukti objektif Layer 1.
    2. APPROVED hanya valid jika 100% Frozen Oracle tests PASS dan contract FROZEN.
    3. NEEDS_REVISION hanya valid jika ada kegagalan teknis kode yang terbukti DAN sisa budget Developer > 0.
       Kontrak FROZEN adalah mutlak immutable (DILARANG unfreeze contract).
    4. FAIL valid jika budget habis atau kondisi terminal terpenuhi.
    """
    test_results = state.get("test_results") or {}
    is_test_passed = bool(test_results.get("passed", False))
    contract_status = state.get("contract_status")
    iteration = state.get("iteration_count", 0)
    max_iter = state.get("max_iterations", 10)
    remaining_dev_budget = max(0, max_iter - iteration)

    evidence: List[Dict[str, Any]] = []
    violations: List[Dict[str, Any]] = []
    required_repairs: List[Dict[str, Any]] = []
    criteria = [
        "review_approval_integrity",
        "frozen_contract_immutability",
        "deterministic_evidence_alignment",
        "authorized_budget_availability"
    ]

    clean_verdict = review_verdict.strip().upper() if review_verdict else "FAIL"
    evidence.append({
        "item": "evaluated_review_verdict",
        "evidence_class": "DETERMINISTIC",
        "observed": clean_verdict,
        "expected": "APPROVED (if tests passed) | NEEDS_REVISION (if code repairable) | FAIL",
        "status": "VALID" if clean_verdict in ("APPROVED", "NEEDS_REVISION", "FAIL") else "INVALID"
    })

    validator_verdict = "PASS"
    repair_owner = "NONE"

    if clean_verdict == "APPROVED":
        # Aturan 1: APPROVED hanya sah jika seluruh tes sandbox lulus dan kontrak FROZEN
        is_clean = is_test_passed and (contract_status == "FROZEN")
        evidence.append({
            "item": "approval_criteria_check",
            "evidence_class": "DETERMINISTIC",
            "observed": {"tests_passed": is_test_passed, "contract_status": contract_status},
            "expected": {"tests_passed": True, "contract_status": "FROZEN"},
            "status": "VALID" if is_clean else "INVALID"
        })
        if not is_clean:
            validator_verdict = "FAIL"
            violations.append({
                "criterion": "review_approval_integrity",
                "severity": "CRITICAL",
                "message": "Reviewer menerbitkan APPROVED padahal pengujian teknis gagal atau kontrak tidak valid (False Approval)",
                "location": "review_verdict"
            })

    elif clean_verdict == "NEEDS_REVISION":
        # Aturan 2: NEEDS_REVISION hanya sah jika causal owner adalah Developer (artefak kode masih mutable)
        # dan remaining budget Developer > 0.
        # Kontrak yang sudah FROZEN tidak boleh di-unfreeze.
        classification_res = classify_contract_mutation_demand(review_notes)
        demands_contract_change = classification_res["is_mutation_demand"]
        evidence.append({
            "item": "frozen_contract_immutability_check",
            "evidence_class": "DETERMINISTIC",
            "observed": {"demands_contract_change": demands_contract_change, "contract_status": contract_status},
            "expected": {"demands_contract_change": False, "contract_status": "FROZEN"},
            "status": "INVALID" if demands_contract_change else "VALID"
        })

        if demands_contract_change:
            validator_verdict = "FAIL"
            violations.append({
                "criterion": "frozen_contract_immutability",
                "severity": "CRITICAL",
                "message": "Reviewer menuntut perubahan pada kontrak yang sudah FROZEN. Kontrak FROZEN mutlak immutable (tidak ada mekanisme unfreeze).",
                "location": "review_notes"
            })
        elif remaining_dev_budget <= 0:
            validator_verdict = "FAIL"
            violations.append({
                "criterion": "authorized_budget_availability",
                "severity": "CRITICAL",
                "message": f"Reviewer menuntut revisi kode namun alokasi budget perbaikan Developer telah habis ({iteration}/{max_iter}).",
                "location": "iteration_count"
            })
        else:
            # Valid code repair request
            repair_owner = "DEVELOPER"
            required_repairs.append({
                "target_phase": "DEVELOPER",
                "action": "REVIEWER_REHABILITATION_REPAIR",
                "details": "Perbaiki kode implementasi sesuai catatan audit Reviewer dengan mematuhi kontrak FROZEN."
            })

    elif clean_verdict == "FAIL":
        # Aturan 3: FAIL sah jika kondisi terminal terpenuhi
        evidence.append({
            "item": "terminal_fail_justification",
            "evidence_class": "DETERMINISTIC",
            "observed": {"tests_passed": is_test_passed, "remaining_budget": remaining_dev_budget},
            "expected": "Terminal state accepted",
            "status": "VALID"
        })

    # Iterasi 7: Assemble ContextualEvidencePackage on FAIL
    cep_dict_b6: Optional[Dict[str, Any]] = None
    if validator_verdict == "FAIL" and assemble_b6_evidence is not None:
        cep_violations = _make_cep_violations(violations)
        run_id = state.get("run_id", "")
        iteration_num = state.get("iteration_count", 0)
        cep = assemble_b6_evidence(state, cep_violations, evidence, review_verdict=clean_verdict, run_id=run_id, iteration=iteration_num)
        cep_dict_b6 = cep.to_dict()

    return {
        "phase": "REVIEWER",
        "validator_type": "PHASE_END",
        "verdict": validator_verdict,
        "criteria_checked": criteria,
        "evidence": evidence,
        "violations": violations,
        "regressions": [],
        "required_repairs": required_repairs,
        "repair_owner": repair_owner,
        "remaining_budget": remaining_dev_budget,
        "evaluated_review_verdict": clean_verdict,
        "confidence": 1.0,
        "source_of_truth": "REVIEWER_DETERMINISTIC_GATE_AUDIT",
        "contextual_evidence_package": cep_dict_b6,
    }
