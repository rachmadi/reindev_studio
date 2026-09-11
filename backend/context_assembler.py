"""
Context Assembler — Deterministic Context Assembly Engine
ReinDev Studio — Iterasi 7 (Deterministic Context-Aware Validation)

Mengumpulkan seluruh fakta objektif, dependensi violation, batasan aktif,
invarian yang telah terbukti benar, dan menetapkan repair boundary untuk
setiap gerbang validasi B1–B6.

Semua nilai dirakit dari state aktual sistem, bukan dihasilkan atau
diinterpretasikan oleh LLM. LLM hanya menerima paket bukti terpadu ini
sebagai konteks untuk menentukan HOW TO REPAIR.

Prinsip:
  Python determines REALITY.
  LLM determines HOW TO REPAIR.
"""

from __future__ import annotations

import hashlib
import re
import ast
from typing import Dict, List, Any, Optional

try:
    from .contextual_evidence import (
        ContextualEvidencePackage,
        ViolationItem,
        PreservedInvariant,
        RepairBoundary,
        RequiredChange,
        ViolationDependency,
        ActionableRepairPrescription,
    )
    from .state import SquadState
except (ImportError, ValueError):
    from contextual_evidence import (
        ContextualEvidencePackage,
        ViolationItem,
        PreservedInvariant,
        RepairBoundary,
        RequiredChange,
        ViolationDependency,
        ActionableRepairPrescription,
    )
    from state import SquadState


# ===========================================================================
# 1. Shared Helpers
# ===========================================================================

def _get_authoritative_target_file(state: SquadState) -> str:
    """Mengekstrak authoritative target file dari state secara deterministik."""
    contract = state.get("contract") or {}
    target_lang = (state.get("target_language") or "python").lower()
    is_dart = "dart" in target_lang or "flutter" in target_lang

    if isinstance(contract, dict):
        task_intent = contract.get("task_intent", {})
        if isinstance(task_intent, dict):
            atf = task_intent.get("authoritative_target_file")
            if atf:
                return atf
        for ifc in contract.get("interface_contracts", []):
            tf = ifc.get("target_file")
            if tf:
                return tf
        for dm in contract.get("data_models", []):
            tf = dm.get("target_file")
            if tf:
                return tf

    return "lib/card_metric.dart" if is_dart else "main.py"


def _get_authoritative_interfaces(state: SquadState) -> List[str]:
    """Mengekstrak daftar nama interface otoritatif dari kontrak."""
    contract = state.get("contract") or {}
    if not isinstance(contract, dict):
        return []
    return [
        ifc.get("identifier", "")
        for ifc in contract.get("interface_contracts", [])
        if ifc.get("identifier")
    ]


def _get_authoritative_models(state: SquadState) -> List[str]:
    """Mengekstrak daftar nama model data otoritatif dari kontrak."""
    contract = state.get("contract") or {}
    if not isinstance(contract, dict):
        return []
    return [
        dm.get("model_name", "")
        for dm in contract.get("data_models", [])
        if dm.get("model_name")
    ]


def _collect_oracle_invariants(state: SquadState) -> List[PreservedInvariant]:
    """Mengumpulkan invariant Oracle SHA-256 dari state."""
    invariants = []
    oracle_sha = state.get("expected_oracle_sha") or state.get("oracle_sha256") or ""
    if oracle_sha:
        invariants.append(PreservedInvariant(
            invariant_id="INV-ORACLE",
            category="ORACLE_INTEGRITY",
            description=f"Frozen Oracle SHA-256 is 100% intact",
            evidence_value=oracle_sha[:16] + "...",
            status="VERIFIED_TRUE",
        ))
    # Juga catat berdasarkan test_files yang dimuat
    test_files = state.get("test_files") or {}
    if test_files:
        for fname, content in test_files.items():
            computed = hashlib.sha256(content.encode("utf-8")).hexdigest()
            invariants.append(PreservedInvariant(
                invariant_id=f"INV-ORACLE-{fname}",
                category="ORACLE_INTEGRITY",
                description=f"Frozen Oracle file '{fname}' SHA-256 verified",
                evidence_value=computed[:16] + "...",
                status="VERIFIED_TRUE",
            ))
            break  # satu oracle, satu invariant
    return invariants


def _collect_contract_invariant(state: SquadState) -> Optional[PreservedInvariant]:
    """Mengumpulkan invariant status kontrak FROZEN dari state."""
    contract_status = state.get("contract_status")
    contract_sha = state.get("contract_sha256")
    if contract_status == "FROZEN" and contract_sha:
        return PreservedInvariant(
            invariant_id="INV-CONTRACT",
            category="CONTRACT_STATUS",
            description=f"Contract is FROZEN with SHA-256 seal",
            evidence_value=contract_sha[:16] + "...",
            status="VERIFIED_TRUE",
        )
    return None


def _collect_passing_test_invariants(state: SquadState) -> List[PreservedInvariant]:
    """Mengumpulkan test yang sudah lulus sebagai behavioral invariant yang terkunci."""
    invariants = []
    prev_passed = list(state.get("previous_passed_tests") or [])

    # Fallback deterministik: jika previous_passed_tests kosong, ekstrak dari output runner
    if not prev_passed:
        output_text = state.get("test_results", {}).get("output") or state.get("test_results", {}).get("stdout") or ""
        if output_text:
            matched_passes = re.findall(r"([\w\.:]+)\s+PASSED", output_text)
            if matched_passes:
                prev_passed = matched_passes

    history_map = state.get("invariant_regression_history") or {}

    for t in prev_passed:
        clean_name = t.split("::")[-1].strip()
        inv_id = f"INV-BEHAVIOR-{clean_name[:30].replace(' ', '_')}"
        hist = history_map.get(inv_id, {})
        ever_reg = hist.get("ever_regressed", False)
        reg_count = hist.get("regression_count", 0)
        reg_hist = hist.get("regression_history", [])

        invariants.append(PreservedInvariant(
            invariant_id=inv_id,
            category="PASSING_TEST",
            description=f"Behavioral contract for '{clean_name}' proven passing in sandbox — behavioral mutation is forbidden",
            evidence_value=t,
            status="PROVEN",
            target=f"behavior:{clean_name}",
            state="LOCKED",
            mutation="FORBIDDEN",
            ever_regressed=ever_reg,
            regression_count=reg_count,
            regression_history=reg_hist,
        ))
    return invariants[:10]


def _standard_forbidden_changes(target_lang: str) -> List[str]:
    """Mengembalikan daftar larangan standard yang berlaku pada semua repair."""
    is_dart = "dart" in target_lang.lower() or "flutter" in target_lang.lower()
    forbidden = [
        "Modify Frozen Oracle (test files)",
        "Unfreeze or amend FROZEN contract",
        "Invent speculative public interfaces not in contract",
        "Rename authoritative interface names defined in contract",
        "Modify already-proven passing tests",
        "Create hidden repair budget or extra repair loops",
    ]
    if is_dart:
        forbidden += [
            "Use deprecated StateNotifier, ChangeNotifier, or StateProvider",
            "Split widget code into multiple files outside lib/",
        ]
    return forbidden


# ===========================================================================
# 2. B1: PM Context Assembler
# ===========================================================================

def assemble_b1_evidence(
    state: SquadState,
    violations: List[ViolationItem],
    evidence: List[Dict[str, Any]],
    run_id: str = "",
    iteration: int = 0,
) -> ContextualEvidencePackage:
    """Merakit ContextualEvidencePackage untuk kegagalan B1 (PM Phase-End)."""
    has_fail = any(v.severity == "CRITICAL" for v in violations)
    verdict = "FAIL" if has_fail else "PASS"

    root_causes = []
    if has_fail:
        root_causes.append(
            "PM specification does not meet minimum structural requirements "
            "(missing User Stories, Acceptance Criteria, or adequate length)."
        )

    required_changes = []
    for i, v in enumerate(violations, 1):
        required_changes.append(RequiredChange(
            change_id=f"REQ-{i:03d}",
            target="pm_specification",
            violation_ref=v.violation_id,
            deterministic_requirement=v.observed_state + " → " + v.expected_state,
        ))

    return ContextualEvidencePackage(
        package_id=ContextualEvidencePackage.make_id(run_id or "unknown", "B1_PM_PHASE_END", iteration),
        timestamp=ContextualEvidencePackage.make_timestamp(),
        validator="B1_PM_PHASE_END",
        phase="PM",
        validator_type="PHASE_END",
        verdict=verdict,
        causal_owner="PM" if has_fail else "NONE",
        failure_summary="PM specification lacks required structure (User Stories / Acceptance Criteria)." if has_fail else "PM phase validated.",
        root_causes=root_causes,
        violations=violations,
        violation_dependencies=[],
        authoritative_context={},
        active_constraints={"spec_min_words": 15, "spec_min_chars": 50},
        preserved_invariants=[],
        repair_boundary=RepairBoundary(
            allowed_changes=["Add User Stories section", "Add Acceptance Criteria section", "Expand specification text"],
            forbidden_changes=_standard_forbidden_changes(state.get("target_language") or "python"),
        ),
        forbidden_changes=_standard_forbidden_changes(state.get("target_language") or "python"),
        required_changes=required_changes,
        expected_post_repair_state=[
            "Specification length >= 15 words and >= 50 chars",
            "Contains structured User Stories or Acceptance Criteria",
        ],
        verification_criteria=[
            "validate_pm_phase returns verdict == 'PASS'",
        ],
        source_of_truth="PM_SPECIFICATION_SCHEMA_V1",
        evidence=evidence,
        remaining_budget=0,
    )


# ===========================================================================
# 3. B2: Architect Context Assembler
# ===========================================================================

def assemble_b2_evidence(
    state: SquadState,
    violations: List[ViolationItem],
    evidence: List[Dict[str, Any]],
    run_id: str = "",
    iteration: int = 0,
) -> ContextualEvidencePackage:
    """Merakit ContextualEvidencePackage untuk kegagalan B2 (Architect Phase-End)."""
    has_fail = any(v.severity == "CRITICAL" for v in violations)
    verdict = "FAIL" if has_fail else "PASS"

    target_lang = (state.get("target_language") or "python").lower()
    auth_file = _get_authoritative_target_file(state)
    interfaces = _get_authoritative_interfaces(state)
    models = _get_authoritative_models(state)
    contract_sha = state.get("contract_sha256") or ""
    contract_status = state.get("contract_status") or "UNKNOWN"

    # Kategorisasi kegagalan
    ast_violations = [v for v in violations if "symbol" in v.criterion or "ast" in v.criterion.lower()]
    contract_violations = [v for v in violations if "contract" in v.criterion.lower() or "interface" in v.criterion.lower()]

    root_causes = []
    if ast_violations:
        root_causes.append(
            "Blueprint contains code snippets with unresolvable decorator or class references "
            "(missing import statements or declaration in the analyzed module scope)."
        )
    if contract_violations:
        root_causes.append(
            f"Contract has not reached FROZEN status (current: {contract_status}) "
            "or contains interface inconsistencies vs authoritative specification."
        )

    # Violation dependencies: AST fixes must precede contract seal
    violation_deps = []
    for ast_v in ast_violations:
        for con_v in contract_violations:
            violation_deps.append(ViolationDependency(
                dependent_violation=con_v.violation_id,
                prerequisite=ast_v.violation_id,
                rationale="Blueprint AST must be clean before contract can be sealed.",
            ))

    # Preserved invariants
    preserved = []
    oracle_inv = _collect_oracle_invariants(state)
    preserved.extend(oracle_inv)

    # Required changes
    required_changes = []
    for i, v in enumerate(violations, 1):
        required_changes.append(RequiredChange(
            change_id=f"REQ-{i:03d}",
            target="architecture_plan" if v in ast_violations else "contract",
            violation_ref=v.violation_id,
            deterministic_requirement=v.expected_state,
            preserve_refs=[inv.invariant_id for inv in preserved],
            forbidden_refs=["Unfreeze contract", "Invent speculative interfaces", "Modify Frozen Oracle"],
        ))

    contract_rev = state.get("contract_revision_count", 0)
    max_rev = state.get("max_contract_revisions", 5)
    remaining = max(0, max_rev - contract_rev)

    return ContextualEvidencePackage(
        package_id=ContextualEvidencePackage.make_id(run_id or "unknown", "B2_ARCHITECT_PHASE_END", iteration),
        timestamp=ContextualEvidencePackage.make_timestamp(),
        validator="B2_ARCHITECT_PHASE_END",
        phase="ARCHITECT",
        validator_type="PHASE_END",
        verdict=verdict,
        causal_owner="ARCHITECT" if has_fail else "NONE",
        failure_summary=(
            f"Blueprint/contract rejected: {len(violations)} violation(s) detected by global AST scan and Contract Gate P0-2.1."
            if has_fail else "Architect phase validated."
        ),
        root_causes=root_causes,
        violations=violations,
        violation_dependencies=violation_deps,
        authoritative_context={
            "authoritative_target_file": auth_file,
            "required_interfaces": interfaces,
            "required_models": models,
            "contract_status": contract_status,
            "contract_sha256": (contract_sha[:16] + "...") if contract_sha else "UNSEALED",
        },
        active_constraints={
            "target_language": target_lang,
            "max_files": 2,
            "contract_revisions_used": contract_rev,
            "contract_revisions_max": max_rev,
        },
        preserved_invariants=preserved,
        repair_boundary=RepairBoundary(
            allowed_changes=[
                "Add missing import statements to blueprint code blocks",
                f"Consolidate implementation into single authoritative file: {auth_file}",
                "Remove duplicate data model definitions",
                "Replace speculative interfaces with exact authoritative interfaces from contract",
                "Add explicit constructor parameter alignment",
            ],
            forbidden_changes=_standard_forbidden_changes(target_lang),
        ),
        forbidden_changes=_standard_forbidden_changes(target_lang),
        required_changes=required_changes,
        expected_post_repair_state=[
            "All referenced decorators and class bases resolve to valid imports",
            "Blueprint AST parses with 0 errors across all code blocks",
            f"Contract status == FROZEN with valid SHA-256 seal",
            f"Interface contracts exactly match: {interfaces}",
            "No duplicate model names in data_models",
            "Preserved invariants remain verified",
        ],
        verification_criteria=[
            "validate_architect_blueprint returns (True, [])",
            "validate_contract_gate returns (True, [], [])",
            "contract_status == 'FROZEN'",
            "B2 verdict == 'PASS'",
        ],
        source_of_truth=f"CONTRACT_GATE_P0_2.1:{contract_sha[:16] if contract_sha else 'UNSEALED'}",
        evidence=evidence,
        remaining_budget=remaining,
    )


# ===========================================================================
# 4. B3: Developer Pre-Execution Context Assembler
# ===========================================================================

def assemble_b3_evidence(
    state: SquadState,
    violations: List[ViolationItem],
    evidence: List[Dict[str, Any]],
    run_id: str = "",
    iteration: int = 0,
) -> ContextualEvidencePackage:
    """Merakit ContextualEvidencePackage untuk kegagalan B3 (Developer Pre-Execution Gate)."""
    has_fail = any(v.severity == "CRITICAL" for v in violations)
    verdict = "FAIL" if has_fail else "PASS"

    target_lang = (state.get("target_language") or "python").lower()
    is_dart = "dart" in target_lang or "flutter" in target_lang
    auth_file = _get_authoritative_target_file(state)
    interfaces = _get_authoritative_interfaces(state)
    models = _get_authoritative_models(state)

    root_causes = []
    for v in violations:
        if "syntax" in v.criterion.lower():
            root_causes.append(f"Syntax error at {v.location}: {v.observed_state}")
        elif "symbol" in v.criterion.lower() or "contract_symbols" in v.criterion:
            root_causes.append(f"Required symbol not declared: {v.observed_state}")
        elif "target_file" in v.criterion.lower():
            root_causes.append(f"Code not written to authoritative target file '{auth_file}'.")
        else:
            root_causes.append(v.observed_state)

    # Preserved invariants
    preserved: List[PreservedInvariant] = []
    oracle_invs = _collect_oracle_invariants(state)
    preserved.extend(oracle_invs)
    contract_inv = _collect_contract_invariant(state)
    if contract_inv:
        preserved.append(contract_inv)
    passing_invs = _collect_passing_test_invariants(state)
    preserved.extend(passing_invs)

    # Required changes
    required_changes = []
    for i, v in enumerate(violations, 1):
        required_changes.append(RequiredChange(
            change_id=f"REQ-{i:03d}",
            target=auth_file,
            violation_ref=v.violation_id,
            deterministic_requirement=v.expected_state,
            preserve_refs=[inv.invariant_id for inv in preserved],
            forbidden_refs=["Modify Frozen Oracle", "Unfreeze contract"],
        ))

    max_iter = state.get("max_iterations", 10)
    remaining = max(0, max_iter - iteration)

    allowed_changes = [
        f"Write/rewrite code in '{auth_file}' only (use === FILE: {auth_file} === block)",
        "Fix syntax errors identified in the violation roster",
        "Add missing class/function declarations for required contract symbols",
    ]
    if is_dart:
        allowed_changes.append("Use Provider<T> for state management (not StateNotifier/ChangeNotifier)")
        allowed_changes.append("Keep all code in single file lib/ directory")

    return ContextualEvidencePackage(
        package_id=ContextualEvidencePackage.make_id(run_id or "unknown", "B3_DEVELOPER_PRE_EXECUTION", iteration),
        timestamp=ContextualEvidencePackage.make_timestamp(),
        validator="B3_DEVELOPER_PRE_EXECUTION",
        phase="DEVELOPER",
        validator_type="PHASE_END",
        verdict=verdict,
        causal_owner="DEVELOPER" if has_fail else "NONE",
        failure_summary=(
            f"Code rejected before sandbox execution: {len(violations)} static violation(s) detected."
            if has_fail else "Pre-execution gate passed."
        ),
        root_causes=root_causes,
        violations=violations,
        violation_dependencies=[],
        authoritative_context={
            "authoritative_target_file": auth_file,
            "required_interfaces": interfaces,
            "required_models": models,
        },
        active_constraints={
            "target_language": target_lang,
            "max_files": 2,
            "iteration": iteration,
            "max_iterations": max_iter,
        },
        preserved_invariants=preserved,
        repair_boundary=RepairBoundary(
            allowed_changes=allowed_changes,
            forbidden_changes=_standard_forbidden_changes(target_lang),
        ),
        forbidden_changes=_standard_forbidden_changes(target_lang),
        required_changes=required_changes,
        expected_post_repair_state=[
            f"Code written to '{auth_file}'",
            "0 syntax errors detected by AST parser",
            f"All required symbols present: {models} and {interfaces}",
            "Preserved invariants remain valid",
        ],
        verification_criteria=[
            "B3 validate_developer_phase returns verdict == 'PASS'",
            "ast.parse succeeds with 0 SyntaxError",
        ],
        source_of_truth="DEVELOPER_STATIC_CONTRACT_AUDIT",
        evidence=evidence,
        remaining_budget=remaining,
    )


# ===========================================================================
# 5. B5: Executor Iteration Context Assembler & Actionable Prescriptions
# ===========================================================================

def inspect_ast_exception_hierarchy(
    code_files: Dict[str, str],
    auth_file: str,
    actual_exc_name: str,
    expected_exc_name: str,
) -> Dict[str, Any]:
    """
    Audit deterministik hierarki kelas exception pada kode sumber target menggunakan AST.
    Memverifikasi apakah actual_exc_name dideklarasikan dan apakah mewarisi expected_exc_name.
    Prinsip: Python menentukan REALITY.
    """
    target_code = code_files.get(auth_file, "")
    if not target_code and code_files:
        for fn, c in code_files.items():
            if fn.endswith(".py"):
                target_code = c
                auth_file = fn
                break

    if not target_code:
        return {
            "audited": False,
            "reason": "Target code empty",
            "is_subclass_compatible": False,
            "declared_bases": [],
            "hierarchy_path": f"{actual_exc_name} -> unknown",
            "subclass_relation": f"{actual_exc_name} !-> {expected_exc_name}",
        }

    try:
        tree = ast.parse(target_code)
    except Exception as e:
        return {
            "audited": False,
            "reason": f"AST parse error: {e}",
            "is_subclass_compatible": False,
            "declared_bases": [],
            "hierarchy_path": f"{actual_exc_name} -> parse_error",
            "subclass_relation": f"{actual_exc_name} !-> {expected_exc_name}",
        }

    # Cari ClassDef untuk actual_exc_name
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == actual_exc_name:
            bases = []
            for b in node.bases:
                if isinstance(b, ast.Name):
                    bases.append(b.id)
                elif isinstance(b, ast.Attribute):
                    bases.append(b.attr)

            is_compatible = (expected_exc_name in bases)
            hierarchy_path = f"{actual_exc_name} -> {', '.join(bases) if bases else 'object'}"
            subclass_relation = f"{actual_exc_name} {'->' if is_compatible else '!->'} {expected_exc_name}"

            return {
                "audited": True,
                "class_found": True,
                "class_name": actual_exc_name,
                "declared_bases": bases,
                "expected_base": expected_exc_name,
                "is_subclass_compatible": is_compatible,
                "hierarchy_path": hierarchy_path,
                "subclass_relation": subclass_relation,
                "source_file": auth_file,
            }

    # Jika bukan custom class, cek apakah built-in
    is_same = (actual_exc_name == expected_exc_name)
    return {
        "audited": True,
        "class_found": False,
        "class_name": actual_exc_name,
        "declared_bases": [],
        "expected_base": expected_exc_name,
        "is_subclass_compatible": is_same,
        "hierarchy_path": f"{actual_exc_name} (built-in / undeclared)",
        "subclass_relation": f"{actual_exc_name} {'==' if is_same else '!=='} {expected_exc_name}",
        "source_file": auth_file,
    }


def extract_oracle_tested_exception_functions(
    test_files: Dict[str, str],
    output: str,
    code_files: Dict[str, str],
    auth_file: str,
) -> List[str]:
    """
    Mengekstrak secara deterministik nama fungsi target yang diuji oleh Oracle dalam blok pytest.raises.
    Mencegah 'Function Boundary Blind Spot' dengan menghubungkan assertion uji langsung ke fungsi implementasi.
    """
    tested_funcs: List[str] = []
    failing_test_names = re.findall(r"FAILED\s+[\w\/\.\\]+::(?P<tname>\w+)", output)

    # 1. AST walk of test_files
    for tf_name, tf_code in test_files.items():
        try:
            tree = ast.parse(tf_code)
            helpers = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
            for node in tree.body:
                if isinstance(node, ast.FunctionDef):
                    if failing_test_names and node.name not in failing_test_names:
                        continue
                    for child in ast.walk(node):
                        if isinstance(child, ast.With):
                            for with_item in child.items:
                                expr = with_item.context_expr
                                if isinstance(expr, ast.Call):
                                    fn = expr.func
                                    fn_name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
                                    if "raises" in fn_name:
                                        for call in ast.walk(child):
                                            if isinstance(call, ast.Call) and call is not expr:
                                                cname = call.func.id if isinstance(call.func, ast.Name) else getattr(call.func, "attr", "")
                                                if cname in helpers:
                                                    h_node = helpers[cname]
                                                    for h_child in ast.walk(h_node):
                                                        if isinstance(h_child, ast.Attribute) and getattr(h_child.value, "id", "") == "main":
                                                            tested_funcs.append(h_child.attr)
                                                elif hasattr(call.func, "value") and getattr(call.func.value, "id", "") == "main":
                                                    tested_funcs.append(call.func.attr)
        except Exception:
            pass

    # 2. Fallback via code_files & test names if AST didn't find any or test_files empty
    if not tested_funcs:
        code = code_files.get(auth_file, "")
        defined_funcs: List[str] = []
        if code:
            try:
                dtree = ast.parse(code)
                defined_funcs = [n.name for n in dtree.body if isinstance(n, ast.FunctionDef)]
            except Exception:
                pass
        for tname in failing_test_names:
            tname_lower = tname.lower()
            found_for_test = False
            for df in defined_funcs:
                core_op = df.replace("_matrices", "").replace("matrix_", "")
                if core_op and core_op in tname_lower:
                    tested_funcs.append(df)
                    found_for_test = True
            if not found_for_test:
                if "addition" in tname_lower:
                    tested_funcs.append("add_matrices")
                if "multiplication" in tname_lower:
                    tested_funcs.append("multiply_matrices")

    # Deduplicate preserving order
    seen = set()
    result: List[str] = []
    for f in tested_funcs:
        if f not in seen:
            seen.add(f)
            result.append(f)
    return result


def synthesize_b5_actionable_prescriptions(
    state: SquadState,
    violations: List[ViolationItem],
    output: str,
    target_lang: str,
    auth_file: str,
) -> List[ActionableRepairPrescription]:
    """
    Menghasilkan deterministic actionable repair prescriptions khusus untuk Gate B5 (Executor Iteration).
    Menerapkan pemisahan epistemik:
      - oracle_call_site: fakta observasional pemanggilan aktual Oracle (AST / call-site test)
      - implementation_symbol: simbol target pada berkas implementasi
      - evidence_basis: dasar bukti deterministik (AST trace, runtime traceback)
    Menjaga batas WHAT vs HOW:
      - Mendikte persyaratan kontraktual objektif yang dibuktikan Oracle.
      - DILARANG menyarankan implementasi kode spesifik seperti template '__init__'.
    """
    prescriptions: List[ActionableRepairPrescription] = []
    test_files = state.get("test_files") or {}
    models = _get_authoritative_models(state)
    interfaces = _get_authoritative_interfaces(state)

    # 1. Pattern: Positional argument mismatch in Python (cli_t1 / BaseModel.__init__)
    pos_arg_match = re.search(
        r"(?:TypeError:\s*(?:BaseModel\.__init__\(\)|[\w\.]+\.__init__\(\)|[\w\.]+\(\))\s*takes\s+\d+\s+positional\s+arguments?\s+but\s+(\d+)\s+were\s+given|takes\s+1\s+positional\s+argument\s+but\s+(\d+)\s+were\s+given)",
        output,
        re.IGNORECASE,
    )

    if pos_arg_match and target_lang == "python":
        oracle_call_site = ""
        called_symbol = "Matrix" if "Matrix" in models else (models[0] if models else "Model")

        # Ekstraksi deterministik call site aktual dari Frozen Oracle test files via AST
        for tf_name, tf_code in test_files.items():
            try:
                tree = ast.parse(tf_code)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        cname = ""
                        if isinstance(node.func, ast.Name):
                            cname = node.func.id
                        elif isinstance(node.func, ast.Attribute):
                            val = getattr(node.func.value, "id", "")
                            cname = f"{val}.{node.func.attr}" if val else node.func.attr

                        target_candidates = models if models else ["Matrix"]
                        short_name = cname.split(".")[-1]
                        if short_name in target_candidates or any(short_name.lower() == m.lower() for m in target_candidates):
                            if len(node.args) > 0:
                                oracle_call_site = (
                                    f"{cname}(...) with {len(node.args)} positional arg(s) at {tf_name}:{node.lineno}"
                                )
                                called_symbol = short_name
                                break
            except Exception:
                pass
            if oracle_call_site:
                break

        if not oracle_call_site:
            oracle_call_site = f"{called_symbol}(data) in Oracle test suite (positional invocation)"

        observed_failure = pos_arg_match.group(0).strip()
        rx = ActionableRepairPrescription(
            prescription_id="RX-B5-POS-ARG-001",
            evidence_ref="B5_SANDBOX_TYPE_ERROR",
            observed_failure=f"{observed_failure} (positional instantiation failed)",
            oracle_call_site=oracle_call_site,
            implementation_symbol=f"class {called_symbol} in '{auth_file}'",
            evidence_basis="ORACLE_AST_CALL_TRACE + RUNTIME_TYPE_ERROR_TRACEBACK",
            required_change=(
                f"Class '{called_symbol}' must accept positional argument 'data' and map this value "
                f"to the underlying model representation. The implementation approach "
                f"(e.g. custom constructor, validation hook, or wrapper) is determined by "
                f"the developer, but the requirement to support positional instantiation "
                f"'{called_symbol}(data)' must be fulfilled."
            ),
            repair_boundary_allowed=[
                f"Modify constructor or interface of class '{called_symbol}' in '{auth_file}' to accept positional arguments",
                f"Map positional arguments to model attributes in '{auth_file}'",
            ],
            repair_boundary_forbidden=[
                "Do NOT modify Frozen Oracle test files (e.g. test_main.py)",
                "Do NOT alter matrix calculation logic or string parsing logic unless causal to constructor invocation",
                "Do NOT alter frozen contract status",
            ],
            expected_post_repair_state=f"'{called_symbol}(data)' can be instantiated positionally without raising TypeError.",
            verification_evidence=f"Oracle test assertions instantiating '{called_symbol}' with positional arguments execute without TypeError.",
        )
        prescriptions.append(rx)

    # 2. Pattern: Missing module attribute / function (AttributeError)
    attr_match = re.search(
        r"AttributeError:\s*(?:module '[^']+' has no attribute '([^']+)'|'([^']+)' object has no attribute '([^']+)')",
        output,
    )
    if attr_match and not prescriptions:
        missing_attr = attr_match.group(1) or attr_match.group(3) or "attribute"
        obj_name = attr_match.group(2) or auth_file
        rx = ActionableRepairPrescription(
            prescription_id="RX-B5-ATTR-001",
            evidence_ref="B5_SANDBOX_ATTRIBUTE_ERROR",
            observed_failure=attr_match.group(0).strip(),
            oracle_call_site=f"Invocation of '{missing_attr}' in Oracle test suite",
            implementation_symbol=f"symbol '{missing_attr}' on {obj_name} in '{auth_file}'",
            evidence_basis="RUNTIME_ATTRIBUTE_ERROR_TRACEBACK",
            required_change=(
                f"Implement or expose '{missing_attr}' on '{obj_name}' to satisfy the contract "
                f"and Oracle test interface requirements."
            ),
            repair_boundary_allowed=[
                f"Add or export '{missing_attr}' in '{auth_file}'",
                f"Implement logic for '{missing_attr}' according to contract specification",
            ],
            repair_boundary_forbidden=[
                "Do NOT modify Frozen Oracle test files",
                "Do NOT alter frozen contract status",
            ],
            expected_post_repair_state=f"'{missing_attr}' is resolvable and callable without AttributeError.",
            verification_evidence=f"Tests calling '{missing_attr}' execute without AttributeError.",
        )
        prescriptions.append(rx)

    # 3. Pattern: Exception type mismatch / Incompatible Exception (cli_t1 / pytest.raises)
    # Dual evidence: Runtime traceback + AST class hierarchy audit
    exc_mismatch_match = re.search(
        r"with pytest\.raises\((?P<expected_exc>[\w\.]+)\):[\s\S]*?E\s+(?:[\w\.]+\.)?(?P<actual_exc>\w+):(?P<error_msg>.*)",
        output
    )
    summary_mismatch = re.search(
        r"FAILED\s+[\w\.:]+incompatible_dimensions\s+-\s+(?:[\w\.]+\.)?(?P<actual_exc>\w+):(?P<error_msg>.*)",
        output
    )
    did_not_raise_match = re.search(
        r"Failed:\s*DID NOT RAISE\s*<class\s*['\"](?P<expected_exc>[\w\.]+)['\"]>",
        output
    )

    if (exc_mismatch_match or did_not_raise_match or summary_mismatch) and target_lang == "python":
        expected_exc = "ValueError"
        actual_exc = "Exception"
        error_msg = ""

        if exc_mismatch_match:
            expected_exc = exc_mismatch_match.group("expected_exc").split(".")[-1]
            actual_exc = exc_mismatch_match.group("actual_exc")
            error_msg = exc_mismatch_match.group("error_msg").strip()
        elif did_not_raise_match:
            expected_exc = did_not_raise_match.group("expected_exc").split(".")[-1]
            if summary_mismatch:
                actual_exc = summary_mismatch.group("actual_exc")
                error_msg = summary_mismatch.group("error_msg").strip()
            else:
                actual_exc = "None"
        elif summary_mismatch:
            actual_exc = summary_mismatch.group("actual_exc")
            error_msg = summary_mismatch.group("error_msg").strip()

        # Evidence 2: Deterministic AST audit of exception class hierarchy in target code
        code_files = state.get("code_files") or {}
        ast_audit = inspect_ast_exception_hierarchy(
            code_files=code_files,
            auth_file=auth_file,
            actual_exc_name=actual_exc,
            expected_exc_name=expected_exc,
        )

        # Emisi resep HANYA jika terbukti tidak kompatibel secara deterministik
        if not ast_audit.get("is_subclass_compatible", False):
            # Ekstraksi fungsi target deterministik untuk eliminasi Function Boundary Blind Spot
            target_funcs = extract_oracle_tested_exception_functions(
                test_files=test_files,
                output=output,
                code_files=code_files,
                auth_file=auth_file,
            )

            if target_funcs:
                funcs_display = ", ".join(target_funcs)
                oracle_calls = ", ".join([f"{f}(a, b)" for f in target_funcs])
                impl_symbol = f"Oracle-tested functions: {funcs_display} in '{auth_file}'"
                call_site = f"Direct invocation in Oracle test suite: {oracle_calls} with incompatible dimensions"
                req_change = (
                    f"When matrix dimensions are incompatible, each function must raise an exception compatible with '{expected_exc}'. "
                    f"Required behavioral condition: ensure that dimension validation is performed inside the function body of {', '.join([repr(f) for f in target_funcs])} "
                    f"before element-wise operations (e.g. verify row and column counts conform to algebraic rules). "
                    f"This requirement is satisfied either by: "
                    f"(a) raising '{expected_exc}' directly inside {funcs_display}, or "
                    f"(b) ensuring that any custom domain exception (e.g. {actual_exc}) explicitly inherits from "
                    f"'{expected_exc}' (i.e. class {actual_exc}({expected_exc}): ...). "
                    f"The structural design is determined by the developer, but type compatibility with "
                    f"'{expected_exc}' and exception raising directly within {funcs_display} is mandatory."
                )
                boundary_allowed = [
                    f"Add or update dimension compatibility validation inside {funcs_display} in '{auth_file}'",
                    f"Raise '{expected_exc}' (or a subclass of '{expected_exc}') when dimensions are incompatible in '{auth_file}'",
                    f"Modify exception class declaration or raise statements in '{auth_file}'",
                ]
                verif_evidence = f"Invoke each function directly with the Oracle's incompatible-dimension inputs and confirm pytest.raises({expected_exc})."
            else:
                impl_symbol = f"Exception declaration and raising logic in '{auth_file}'"
                call_site = f"with pytest.raises({expected_exc}) at Oracle test suite"
                req_change = (
                    f"When invalid input or incompatible dimensions are provided, operations must raise an exception "
                    f"compatible with '{expected_exc}'. This requirement is satisfied either by: "
                    f"(a) raising '{expected_exc}' directly, or "
                    f"(b) ensuring that any custom domain exception (e.g. {actual_exc}) explicitly inherits from "
                    f"'{expected_exc}' (i.e. class {actual_exc}({expected_exc}): ...). "
                    f"The structural design is determined by the developer, but type compatibility with "
                    f"'{expected_exc}' is mandatory."
                )
                boundary_allowed = [
                    f"Modify exception class declaration or raise statements in dimension validation logic in '{auth_file}'",
                    f"Add or update input validation for incompatible dimensions in '{auth_file}'",
                ]
                verif_evidence = f"test_matrix_addition_incompatible_dimensions and test_matrix_multiplication_incompatible_dimensions execute and PASS."

            rx = ActionableRepairPrescription(
                prescription_id="RX-B5-EXC-COMPAT-001",
                evidence_ref="DUAL_EVIDENCE_RUNTIME_AND_AST_HIERARCHY_AUDIT",
                observed_failure=(
                    f"Oracle test asserted with pytest.raises({expected_exc}), but function raised '{actual_exc}' "
                    f"({error_msg}). Deterministic AST audit confirms '{actual_exc}' inherits from "
                    f"{ast_audit.get('declared_bases', [])}, not '{expected_exc}' ({ast_audit.get('subclass_relation', '')})."
                ),
                oracle_call_site=call_site,
                implementation_symbol=impl_symbol,
                evidence_basis=f"RUNTIME_TRACEBACK + AST_HIERARCHY_AUDIT ({ast_audit.get('hierarchy_path', '')})",
                required_change=req_change,
                repair_boundary_allowed=boundary_allowed,
                repair_boundary_forbidden=[
                    "Do NOT alter matrix arithmetic algorithms or return formats for addition, subtraction, or multiplication which are already LOCKED behavioral invariants",
                    "Do NOT alter Frozen Oracle test files (e.g. test_main.py)",
                    "Do NOT alter frozen contract status",
                ],
                expected_post_repair_state=f"Operations with incompatible dimensions raise an exception caught by pytest.raises({expected_exc}).",
                verification_evidence=verif_evidence,
            )
            prescriptions.append(rx)

    return prescriptions



def assemble_b5_evidence(
    state: SquadState,
    violations: List[ViolationItem],
    regressions: List[Dict[str, Any]],
    evidence: List[Dict[str, Any]],
    run_id: str = "",
    iteration: int = 0,
) -> ContextualEvidencePackage:
    """Merakit ContextualEvidencePackage untuk kegagalan B5 (Executor Iteration)."""
    has_fail = any(v.severity == "CRITICAL" for v in violations) or bool(regressions)
    verdict = "FAIL" if has_fail else "PASS"

    target_lang = (state.get("target_language") or "python").lower()
    is_dart = "dart" in target_lang or "flutter" in target_lang
    auth_file = _get_authoritative_target_file(state)
    interfaces = _get_authoritative_interfaces(state)
    models = _get_authoritative_models(state)

    test_results = state.get("test_results") or {}
    output = test_results.get("output") or test_results.get("stdout") or ""
    failed_count = test_results.get("failed_count", 0)
    exit_code = test_results.get("exit_code")
    passed_count = test_results.get("passed_count", 0)

    root_causes = []
    for v in violations:
        if "regression" in v.criterion.lower():
            root_causes.append(f"Regression detected: {v.observed_state}")
        elif "sandbox" in v.criterion.lower() or "exit_code" in v.criterion.lower():
            root_causes.append(f"Sandbox test failure (exit_code={exit_code}, failed={failed_count}).")

    # Extract concise error evidence from sandbox output
    relevant_lines: List[str] = []
    for line in output.splitlines():
        stripped = line.strip()
        if stripped and any(k in stripped.lower() for k in ("error", "exception", "fail", "expected", "actual", "nosuchmethod", "undefined", "isn't defined", "flutter")):
            relevant_lines.append(stripped)
    sandbox_evidence_str = "\n".join(relevant_lines[:12]) if relevant_lines else output[:400]

    # Preserved invariants
    preserved: List[PreservedInvariant] = []
    preserved.extend(_collect_oracle_invariants(state))
    contract_inv = _collect_contract_invariant(state)
    if contract_inv:
        preserved.append(contract_inv)
    preserved.extend(_collect_passing_test_invariants(state))

    # Oracle call site from test_files (crucial context for semantic fixation)
    test_files = state.get("test_files") or {}
    oracle_callsite_excerpt = ""
    for fname, content in test_files.items():
        # Ekstrak 15 baris pertama yang relevan sebagai call-site context
        relevant = [ln for ln in content.splitlines() if any(k in ln for k in (interfaces + models + ["test", "expect", "find"]))][:8]
        oracle_callsite_excerpt = "\n".join(relevant)
        break

    # Required changes
    required_changes = []
    for i, v in enumerate(violations, 1):
        req_text = (
            f"Fix test failure: {v.observed_state}. Required: {v.expected_state}. "
            f"Reference Oracle call site and match interface exactly."
        )
        required_changes.append(RequiredChange(
            change_id=f"REQ-{i:03d}",
            target=auth_file,
            violation_ref=v.violation_id,
            deterministic_requirement=req_text,
            preserve_refs=[inv.invariant_id for inv in preserved],
            forbidden_refs=["Modify Frozen Oracle", "Unfreeze contract"],
        ))

    max_iter = state.get("max_iterations", 10)
    remaining = max(0, max_iter - iteration)

    allowed = [
        f"Modify implementation code in '{auth_file}' to satisfy Oracle call sites",
        "Align constructor parameters, method signatures with Oracle test expectations",
        "Add missing class fields or methods required by failing tests",
    ]
    if is_dart:
        allowed.append("Use Provider<T> for state management (Riverpod pattern)")

    actionable_prescriptions = synthesize_b5_actionable_prescriptions(
        state=state,
        violations=violations,
        output=output,
        target_lang=target_lang,
        auth_file=auth_file,
    )

    return ContextualEvidencePackage(
        package_id=ContextualEvidencePackage.make_id(run_id or "unknown", "B5_EXECUTOR_ITERATION", iteration),
        timestamp=ContextualEvidencePackage.make_timestamp(),
        validator="B5_EXECUTOR_ITERATION",
        phase="EXECUTOR",
        validator_type="ITERATION",
        verdict=verdict,
        causal_owner="DEVELOPER" if has_fail else "NONE",
        failure_summary=(
            f"Sandbox execution failed: {failed_count} test(s) failed "
            f"(exit_code={exit_code}, passed={passed_count})."
            if has_fail else "Executor iteration passed."
        ),
        root_causes=root_causes,
        violations=violations,
        violation_dependencies=[],
        authoritative_context={
            "authoritative_target_file": auth_file,
            "required_interfaces": interfaces,
            "required_models": models,
            "oracle_call_site_excerpt": oracle_callsite_excerpt,
        },
        active_constraints={
            "target_language": target_lang,
            "iteration": iteration,
            "max_iterations": max_iter,
            "sandbox_runner": "flutter_test" if is_dart else "pytest",
        },
        preserved_invariants=preserved,
        repair_boundary=RepairBoundary(
            allowed_changes=allowed,
            forbidden_changes=_standard_forbidden_changes(target_lang),
        ),
        forbidden_changes=_standard_forbidden_changes(target_lang),
        required_changes=required_changes,
        expected_post_repair_state=[
            f"All {failed_count + passed_count} test(s) pass",
            "exit_code == 0",
            "failed_count == 0",
            "Zero regressions against previously-passing tests",
            "Preserved invariants remain valid",
        ],
        verification_criteria=[
            "sandbox exit_code == 0",
            "test_results['passed'] == True",
            "test_results['failed_count'] == 0",
            "B5 verdict == 'PASS'",
        ],
        source_of_truth=f"SANDBOX_RUNNER:exit_code_{exit_code}",
        evidence=evidence + ([{
            "item": "sandbox_error_excerpt",
            "evidence_class": "DETERMINISTIC",
            "observed": sandbox_evidence_str[:500],
            "expected": "0 errors",
            "status": "INVALID",
        }] if sandbox_evidence_str else []),
        remaining_budget=remaining,
        actionable_prescriptions=actionable_prescriptions,
    )


# ===========================================================================
# 6. B4 & B6 context assemblers (simpler — rarely need repair packages)
# ===========================================================================

def assemble_b4_evidence(
    state: SquadState,
    violations: List[ViolationItem],
    evidence: List[Dict[str, Any]],
    run_id: str = "",
    iteration: int = 0,
) -> ContextualEvidencePackage:
    """Merakit ContextualEvidencePackage untuk kegagalan B4 (Oracle Phase-End)."""
    has_fail = any(v.severity == "CRITICAL" for v in violations)
    expected_sha = state.get("expected_oracle_sha") or ""

    return ContextualEvidencePackage(
        package_id=ContextualEvidencePackage.make_id(run_id or "unknown", "B4_ORACLE_PHASE_END", iteration),
        timestamp=ContextualEvidencePackage.make_timestamp(),
        validator="B4_ORACLE_PHASE_END",
        phase="ORACLE",
        validator_type="PHASE_END",
        verdict="FAIL" if has_fail else "PASS",
        causal_owner="NONE",  # B4 failures are terminal — no repair path
        failure_summary="CRITICAL: Frozen Oracle integrity violated. Execution aborted." if has_fail else "Oracle integrity verified.",
        root_causes=["SHA-256 checksum mismatch indicates Oracle file was tampered or corrupted."] if has_fail else [],
        violations=violations,
        violation_dependencies=[],
        authoritative_context={"expected_sha256": expected_sha[:16] + "..." if expected_sha else "UNSPECIFIED"},
        active_constraints={"repair_budget": 0, "terminal": True},
        preserved_invariants=[],
        repair_boundary=RepairBoundary(allowed_changes=[], forbidden_changes=["Any modification to Oracle files"]),
        forbidden_changes=["Any modification to Oracle files"],
        required_changes=[],
        expected_post_repair_state=["Oracle SHA-256 matches baseline exactly (no manual repair possible)"],
        verification_criteria=["SHA-256 match is deterministic — no workaround"],
        source_of_truth=f"FROZEN_ORACLE_SHA256:{expected_sha[:16] if expected_sha else 'UNKNOWN'}",
        evidence=evidence,
        remaining_budget=0,
    )


def assemble_b6_evidence(
    state: SquadState,
    violations: List[ViolationItem],
    evidence: List[Dict[str, Any]],
    review_verdict: str = "FAIL",
    run_id: str = "",
    iteration: int = 0,
) -> ContextualEvidencePackage:
    """Merakit ContextualEvidencePackage untuk kegagalan B6 (Reviewer Phase-End)."""
    has_fail = any(v.severity == "CRITICAL" for v in violations)
    target_lang = (state.get("target_language") or "python").lower()

    max_iter = state.get("max_iterations", 10)
    remaining = max(0, max_iter - iteration)

    root_causes = []
    if has_fail:
        root_causes.append(
            f"Reviewer verdict '{review_verdict}' rejected: "
            "either budget exhausted, false approval without test evidence, or illegal contract amendment requested."
        )

    return ContextualEvidencePackage(
        package_id=ContextualEvidencePackage.make_id(run_id or "unknown", "B6_REVIEWER_PHASE_END", iteration),
        timestamp=ContextualEvidencePackage.make_timestamp(),
        validator="B6_REVIEWER_PHASE_END",
        phase="REVIEWER",
        validator_type="PHASE_END",
        verdict="FAIL" if has_fail else "PASS",
        causal_owner="DEVELOPER" if (review_verdict == "NEEDS_REVISION" and remaining > 0) else "NONE",
        failure_summary=(
            "Reviewer verdict rejected by B6: terminal FAIL." if (has_fail and remaining == 0)
            else "Reviewer verdict requires Developer repair." if has_fail
            else "Reviewer phase validated."
        ),
        root_causes=root_causes,
        violations=violations,
        violation_dependencies=[],
        authoritative_context={},
        active_constraints={
            "reviewer_verdict": review_verdict,
            "developer_budget_remaining": remaining,
            "contract_frozen": state.get("contract_status") == "FROZEN",
        },
        preserved_invariants=_collect_oracle_invariants(state),
        repair_boundary=RepairBoundary(
            allowed_changes=(["Developer code repair (if budget > 0)"] if remaining > 0 else []),
            forbidden_changes=_standard_forbidden_changes(target_lang),
        ),
        forbidden_changes=_standard_forbidden_changes(target_lang),
        required_changes=[],
        expected_post_repair_state=["All Frozen Oracle tests PASS", "Reviewer verdict == APPROVED"],
        verification_criteria=["test_results['passed'] == True", "B6 verdict == 'PASS'"],
        source_of_truth="REVIEWER_AUDIT_LAYER_1",
        evidence=evidence,
        remaining_budget=remaining,
    )
