"""
Test Suite: Implementation Grounding & Diagnostic Evidence Hardening v1
ReinDev Studio — 20 Deterministic Verification Tests (Church of Goat Doctrine)

Tests:
1. test_symbol_exists_grounding
2. test_symbol_missing_grounding
3. test_constructor_positional_named_mismatch
4. test_callable_signature_mismatch
5. test_type_incompatibility_grounding
6. test_import_package_resolution_failure
7. test_multiple_compiler_diagnostics_harvested
8. test_multiple_runtime_diagnostics_harvested
9. test_duplicate_diagnostic_preservation
10. test_caller_callee_incompatibility_linkage
11. test_implementation_fact_vs_llm_prior_conflict
12. test_current_error_vs_historical_isolation
13. test_grounding_evidence_survives_context_assembly
14. test_locked_invariant_survives_grounding_repair
15. test_frozen_oracle_remains_byte_identical
16. test_sterile_executor_zero_transformation
17. test_task_domain_model_agnostic_behavior
18. test_generation_truncation_detection
19. test_compact_evidence_does_not_discard_independent_failures
20. test_unknown_causal_attribution_remains_unknown
"""

import ast
import hashlib
import inspect
from pathlib import Path
from typing import Dict, Any, List

import pytest

from backend.canonical_evidence import (
    CanonicalImplementationEvidence,
    ImplementationEvidenceType,
    VALID_EVIDENCE_TYPES,
    deduplicate_evidence,
)
from backend.implementation_grounding import (
    ImplementationGroundingEngine,
    PythonGroundingAdapter,
    DartGroundingAdapter,
    DART_MATERIAL_ICONS,
)
from backend.diagnostic_parser import (
    DiagnosticEvidence,
    FailingTest,
    parse_pytest_output,
    parse_dart_output,
    prioritize_failures,
    build_targeted_feedback,
)
from backend.contextual_evidence import (
    ContextualEvidencePackage,
    PreservedInvariant,
    RepairBoundary,
    ContextualEvidenceRenderer,
)
from backend.context_hardening import (
    build_developer_repair_context,
    ContextTelemetry,
)
from backend.phase_validators import (
    validate_developer_phase,
    detect_generation_truncation,
)


# ==============================================================================
# 1. Symbol Exists Grounding
# ==============================================================================
def test_symbol_exists_grounding():
    """1. Symbol present in installed SDK/package passes grounding with status COMPATIBLE."""
    dart_adapter = DartGroundingAdapter()
    code = "import 'package:flutter/material.dart';\nfinal icon = Icons.home;"
    facts = dart_adapter.harvest_grounding(
        code_files={"lib/main.dart": code},
        test_files={}
    )
    # Icons.home is valid in DART_MATERIAL_ICONS, so NO SYMBOL_NOT_FOUND is emitted
    missing_icon_facts = [f for f in facts if f.evidence_type == ImplementationEvidenceType.SYMBOL_NOT_FOUND.value]
    assert len(missing_icon_facts) == 0

    # Also verify explicitly via DART_MATERIAL_ICONS set
    assert "home" in DART_MATERIAL_ICONS
    assert "settings" in DART_MATERIAL_ICONS


# ==============================================================================
# 2. Symbol Missing Grounding
# ==============================================================================
def test_symbol_missing_grounding():
    """2. Symbol not present in installed SDK/package produces SYMBOL_NOT_FOUND fact with status NOT_FOUND."""
    dart_adapter = DartGroundingAdapter()
    code = "import 'package:flutter/material.dart';\nfinal icon = Icons.cpu;"
    facts = dart_adapter.harvest_grounding(
        code_files={"lib/main.dart": code},
        test_files={}
    )
    missing = [f for f in facts if f.evidence_type == ImplementationEvidenceType.SYMBOL_NOT_FOUND.value]
    assert len(missing) == 1
    assert missing[0].symbol_reference == "Icons.cpu"
    assert missing[0].compatibility_status == "NOT_FOUND"
    assert "cpu" in missing[0].observed
    assert missing[0].provenance == "DETERMINISTIC_TOOLING"


# ==============================================================================
# 3. Constructor Positional vs Named Mismatch
# ==============================================================================
def test_constructor_positional_named_mismatch():
    """3. Calling positional vs named or incompatible parameter produces CONSTRUCTOR_MISMATCH."""
    py_adapter = PythonGroundingAdapter()
    code = (
        "from pydantic import BaseModel\n"
        "class Matrix(BaseModel):\n"
        "    data: list\n"
    )
    test = (
        "from main import Matrix\n"
        "def test_matrix():\n"
        "    m = Matrix([[1, 2], [3, 4]])\n"
    )
    facts = py_adapter.harvest_grounding(
        code_files={"main.py": code},
        test_files={"test_main.py": test}
    )
    mismatches = [f for f in facts if f.evidence_type == ImplementationEvidenceType.CONSTRUCTOR_MISMATCH.value]
    assert len(mismatches) == 1
    assert mismatches[0].symbol_reference == "Matrix"
    assert mismatches[0].compatibility_status == "INCOMPATIBLE"
    assert "positional" in mismatches[0].observed.lower()
    assert mismatches[0].caller_site is not None
    assert mismatches[0].callee_site is not None


# ==============================================================================
# 4. Callable Signature Mismatch
# ==============================================================================
def test_callable_signature_mismatch():
    """4. Arity mismatch produces SIGNATURE_MISMATCH with caller/callee linkage."""
    py_adapter = PythonGroundingAdapter()
    code = (
        "def calculate_total(price: float) -> float:\n"
        "    return price * 1.1\n"
    )
    test = (
        "from main import calculate_total\n"
        "def test_calc():\n"
        "    res = calculate_total(10.0, 0.05, 'USD')\n"
    )
    facts = py_adapter.harvest_grounding(
        code_files={"main.py": code},
        test_files={"test_main.py": test}
    )
    sig_mismatches = [f for f in facts if f.evidence_type == ImplementationEvidenceType.SIGNATURE_MISMATCH.value]
    assert len(sig_mismatches) == 1
    assert sig_mismatches[0].symbol_reference == "calculate_total"
    assert sig_mismatches[0].compatibility_status == "INCOMPATIBLE"
    assert "3" in str(sig_mismatches[0].observed)  # passed 3 args
    assert "1" in str(sig_mismatches[0].expected)  # expected 1 arg
    assert "test_main.py" in sig_mismatches[0].caller_site
    assert "main.py" in sig_mismatches[0].callee_site


# ==============================================================================
# 5. Type Incompatibility Grounding
# ==============================================================================
def test_type_incompatibility_grounding():
    """5. Type incompatibility produces TYPE_INCOMPATIBILITY canonical evidence."""
    ev = CanonicalImplementationEvidence(
        evidence_id=CanonicalImplementationEvidence.make_id("pytest", "TYPE_INCOMPATIBILITY", "main.py", 42, "add"),
        evidence_type=ImplementationEvidenceType.TYPE_INCOMPATIBILITY.value,
        source="pytest_runtime",
        file_reference="main.py",
        line_reference=42,
        symbol_reference="add",
        observed="unsupported operand type(s) for +: 'int' and 'str'",
        expected="int + int",
        compatibility_status="INCOMPATIBLE",
        diagnostic_message="TypeError: unsupported operand type(s) for +: 'int' and 'str'",
        provenance="RUNTIME",
        confidence=1.0,
        causal_status="PROVEN"
    )
    compact = ev.format_compact()
    assert "[TYPE_INCOMPATIBILITY]" in compact
    assert "main.py:42" in compact
    assert "unsupported operand" in compact
    assert ev.evidence_type in VALID_EVIDENCE_TYPES


# ==============================================================================
# 6. Import Package Resolution Failure
# ==============================================================================
def test_import_package_resolution_failure():
    """6. Importing uninstalled package produces IMPORT_RESOLUTION_FAILURE."""
    stdout = "ERROR collecting test_main.py\nModuleNotFoundError: No module named 'nonexistent_package_xyz'"
    ev = parse_pytest_output(stdout=stdout, exit_code=2)
    assert ev.execution_status == "error"
    assert len(ev.canonical_evidence) >= 1
    canon = ev.canonical_evidence[0]
    assert canon.evidence_type in ("IMPORT_RESOLUTION_ERROR", "IMPORT_RESOLUTION_FAILURE")
    assert canon.compatibility_status == "INCOMPATIBLE"
    assert "nonexistent_package_xyz" in canon.diagnostic_message


# ==============================================================================
# 7. Multiple Compiler Diagnostics Harvested
# ==============================================================================
def test_multiple_compiler_diagnostics_harvested():
    """7. Multiple compilation errors in single run are all harvested into individual canonical items."""
    dart_err = (
        "lib/card_metric.dart:15:3: Error: Member not found: 'cpu'.\n"
        "lib/card_metric.dart:28:10: Error: No named parameter with the name 'title'.\n"
        "lib/card_metric.dart:40:1: Error: Can't find ')' to match '('."
    )
    ev = parse_dart_output(stdout=dart_err, exit_code=1)
    assert len(ev.failing_tests) == 3
    assert len(ev.canonical_evidence) == 3

    types = [item.evidence_type for item in ev.canonical_evidence]
    assert "SYMBOL_NOT_FOUND" in types
    assert "CONSTRUCTOR_MISMATCH" in types
    assert "COMPILATION_ERROR" in types


# ==============================================================================
# 8. Multiple Runtime Diagnostics Harvested
# ==============================================================================
def test_multiple_runtime_diagnostics_harvested():
    """8. Multiple runtime test failure assertions are all harvested into canonical items."""
    pytest_out = (
        "FAILED test_main.py::test_add - assert 4 == 5\n"
        "FAILED test_main.py::test_sub - TypeError: unsupported operand type\n"
        "FAILED test_main.py::test_get - 422 Unprocessable Entity\n"
        "========================= 3 failed in 0.15s ========================="
    )
    ev = parse_pytest_output(stdout=pytest_out, exit_code=1)
    assert len(ev.failing_tests) == 3
    assert len(ev.canonical_evidence) == 3

    ev_types = [item.evidence_type for item in ev.canonical_evidence]
    assert "BEHAVIORAL_ASSERTION" in ev_types
    assert "TYPE_INCOMPATIBILITY" in ev_types
    assert "SCHEMA_VALIDATION_ERROR" in ev_types


# ==============================================================================
# 9. Duplicate Diagnostic Preservation / Deduplication
# ==============================================================================
def test_duplicate_diagnostic_preservation():
    """9. Multiple identical compiler diagnostics produce unique IDs or are cleanly deduplicated."""
    ev1 = CanonicalImplementationEvidence(
        evidence_id="EV-1",
        evidence_type="SYMBOL_NOT_FOUND",
        source="compiler",
        file_reference="lib/card.dart",
        line_reference=10,
        symbol_reference="cpu",
        observed="member not found: cpu",
        compatibility_status="NOT_FOUND"
    )
    ev2 = CanonicalImplementationEvidence(
        evidence_id="EV-2",
        evidence_type="SYMBOL_NOT_FOUND",
        source="compiler",
        file_reference="lib/card.dart",
        line_reference=10,
        symbol_reference="cpu",
        observed="member not found: cpu",
        compatibility_status="NOT_FOUND"
    )
    # Different line produces distinct ID
    ev3 = CanonicalImplementationEvidence(
        evidence_id="EV-3",
        evidence_type="SYMBOL_NOT_FOUND",
        source="compiler",
        file_reference="lib/card.dart",
        line_reference=25,
        symbol_reference="cpu",
        observed="member not found: cpu",
        compatibility_status="NOT_FOUND"
    )

    deduped = deduplicate_evidence([ev1, ev2, ev3])
    # ev1 and ev2 share (evidence_type, file, line, symbol) -> collapsed to 1
    # ev3 has line 25 -> kept
    assert len(deduped) == 2
    assert {e.line_reference for e in deduped} == {10, 25}


# ==============================================================================
# 10. Caller-Callee Incompatibility Linkage
# ==============================================================================
def test_caller_callee_incompatibility_linkage():
    """10. Fact connects caller line/token to callee declaration signature."""
    ev = CanonicalImplementationEvidence(
        evidence_id="EV-LINK-1",
        evidence_type="CONSTRUCTOR_MISMATCH",
        source="ast_inspector",
        file_reference="main.py",
        line_reference=5,
        symbol_reference="Matrix",
        observed="Matrix([[1, 2]])",
        expected="Matrix(data=[[1, 2]])",
        compatibility_status="INCOMPATIBLE",
        diagnostic_message="BaseModel subclass requires keyword arguments",
        caller_site="test_main.py:12: Matrix([[1, 2]])",
        callee_site="main.py:5: class Matrix(BaseModel)",
        causal_status="PROVEN"
    )
    compact = ev.format_compact()
    assert "Caller: test_main.py:12: Matrix([[1, 2]])" in compact
    assert "Causal: PROVEN" in compact
    assert ev.callee_site == "main.py:5: class Matrix(BaseModel)"


# ==============================================================================
# 11. Implementation Fact vs LLM Prior Conflict Resolution
# ==============================================================================
def test_implementation_fact_vs_llm_prior_conflict():
    """11. When fact contradicts prior LLM knowledge, context explicitly declares AUTHORITY ASSERTION."""
    state = {
        "target_language": "flutter",
        "code_files": {"lib/main.dart": "final icon = Icons.cpu;"},
        "test_files": {},
        "iteration_count": 1,
        "max_iterations": 10,
        "contract": {
            "task_intent": {"authoritative_target_file": "lib/main.dart"},
            "interface_contracts": [{"identifier": "main"}],
            "data_models": []
        }
    }
    context, telemetry = build_developer_repair_context(state)
    assert "[IMPLEMENTATION GROUNDING — DETERMINISTIC REALITY]" in context
    assert "AUTHORITY ASSERTION" in context
    assert "NOT_FOUND in active environment" in context
    assert "Deterministic tooling overrides LLM parametric knowledge" in context


# ==============================================================================
# 12. Current Error vs Historical Isolation
# ==============================================================================
def test_current_error_vs_historical_isolation():
    """12. Active iteration failure is isolated from prior run historical regressions."""
    state = {
        "target_language": "python",
        "code_files": {"main.py": "def add(a, b): return a + b"},
        "locked_invariants": {
            "INV-001": {
                "description": "Historical feature test_sub passed in Iteration 0",
                "status": "PROVEN",
                "regression_count": 1
            }
        },
        "test_results": {
            "output": "FAILED test_main.py::test_add - assert 2 == 3"
        }
    }
    context, telemetry = build_developer_repair_context(state)
    # Historical invariant is in section 3 (LOCKED INVARIANTS)
    assert "[3] LOCKED INVARIANTS" in context
    assert "INV-001" in context
    assert "pernah regresi 1x" in context
    # Current runtime diagnostics is in section 6
    assert "[6] RUNTIME DIAGNOSTICS" in context
    assert "test_add" in context
    assert telemetry["current_failure_count"] >= 0
    assert telemetry["historical_failure_count"] == 1


# ==============================================================================
# 13. Grounding Evidence Survives Context Assembly
# ==============================================================================
def test_grounding_evidence_survives_context_assembly():
    """13. Grounding evidence package passes through serialization and rendering without data loss."""
    ev = CanonicalImplementationEvidence(
        evidence_id="EV-100",
        evidence_type="SYMBOL_NOT_FOUND",
        source="dart_analyzer",
        file_reference="lib/card.dart",
        line_reference=20,
        symbol_reference="Icons.cpu",
        observed="member not found: 'cpu'",
        compatibility_status="NOT_FOUND",
        diagnostic_message="Icons.cpu does not exist in flutter/material.dart",
        provenance="COMPILER",
        confidence=1.0,
        causal_status="PROVEN"
    )
    pkg = ContextualEvidencePackage(
        package_id="EV-TEST",
        timestamp=ContextualEvidencePackage.make_timestamp(),
        validator="B3_DEVELOPER_PHASE_END",
        phase="DEVELOPER",
        validator_type="PHASE_END",
        verdict="FAIL",
        causal_owner="DEVELOPER",
        failure_summary="Symbol not found in SDK",
        root_causes=["Icons.cpu not in flutter/material.dart"],
        violations=[],
        violation_dependencies=[],
        authoritative_context={},
        active_constraints={},
        preserved_invariants=[],
        repair_boundary=RepairBoundary(),
        forbidden_changes=[],
        required_changes=[],
        expected_post_repair_state=[],
        verification_criteria=[],
        source_of_truth="DART_COMPILER",
        evidence=[],
        implementation_evidence=[ev]
    )

    # Roundtrip serialization
    pkg_dict = pkg.to_dict()
    assert "implementation_evidence" in pkg_dict
    pkg_restored = ContextualEvidencePackage.from_dict(pkg_dict)
    assert len(pkg_restored.implementation_evidence) == 1

    # Render for prompt
    rendered = ContextualEvidenceRenderer.render_for_prompt(pkg_restored)
    assert "[4B. IMPLEMENTATION GROUNDING EVIDENCE — DETERMINISTIC REALITY" in rendered
    assert "[SYMBOL_NOT_FOUND]" in rendered
    assert "Icons.cpu" in rendered


# ==============================================================================
# 14. Locked Invariant Survives Grounding Repair
# ==============================================================================
def test_locked_invariant_survives_grounding_repair():
    """14. Locked invariants remain locked (PROVEN, mutation: FORBIDDEN) across grounding repairs."""
    inv = PreservedInvariant(
        invariant_id="INV-042",
        category="PASSING_TEST",
        description="test_addition_passes",
        evidence_value="exit_code=0",
        status="PROVEN",
        state="LOCKED",
        mutation="FORBIDDEN"
    )
    assert inv.state == "LOCKED"
    assert inv.mutation == "FORBIDDEN"

    state = {
        "target_language": "python",
        "code_files": {"main.py": "x = 1"},
        "locked_invariants": {inv.invariant_id: inv.to_dict()}
    }
    context, telemetry = build_developer_repair_context(state)
    assert "[3] LOCKED INVARIANTS" in context
    assert "INV-042" in context
    assert "mutation: FORBIDDEN" in context
    assert telemetry["locked_invariants"] == 1


# ==============================================================================
# 15. Frozen Oracle Remains Byte-Identical
# ==============================================================================
def test_frozen_oracle_remains_byte_identical():
    """15. Frozen Oracle files and SHA-256 remain byte-identical through all operations."""
    oracle_content = "def test_oracle_contract():\n    assert True\n"
    test_files = {"test/test_oracle.py": oracle_content}
    original_sha = hashlib.sha256(oracle_content.encode("utf-8")).hexdigest()

    state = {
        "target_language": "python",
        "code_files": {"main.py": "def run(): pass"},
        "test_files": test_files,
        "contract": {"task_intent": {"authoritative_target_file": "main.py"}},
        "iteration_count": 0
    }

    # Harvest grounding
    ImplementationGroundingEngine.harvest_implementation_grounding("python", state["code_files"], state["test_files"])

    # Validate developer phase
    validate_developer_phase(state)

    # Build repair context
    build_developer_repair_context(state)

    # Post-check: test_files content and SHA must be 100% identical
    post_sha = hashlib.sha256(state["test_files"]["test/test_oracle.py"].encode("utf-8")).hexdigest()
    assert original_sha == post_sha
    assert state["test_files"]["test/test_oracle.py"] == oracle_content


# ==============================================================================
# 16. Sterile Executor Zero Transformation
# ==============================================================================
def test_sterile_executor_zero_transformation():
    """16. Raw LLM code is executed without regex rewrites or synthetic shims in sterile mode."""
    from backend.executor_v2 import run_sandbox_tests_v2
    raw_code = "def custom_fn():\n    return 'no_shims_here'\n"
    test_code = "from main import custom_fn\ndef test_fn():\n    assert custom_fn() == 'no_shims_here'\n"

    res = run_sandbox_tests_v2(
        {"main.py": raw_code},
        {"test_main.py": test_code},
        executor_mode="OFF"
    )
    assert res is not None
    assert "exit_code" in res
    assert res.get("exit_code") == 0


# ==============================================================================
# 17. Task / Domain / Model Agnostic Behavior
# ==============================================================================
def test_task_domain_model_agnostic_behavior():
    """17. Grounding engine and validators contain NO task-specific branching."""
    files_to_check = [
        Path("backend/canonical_evidence.py"),
        Path("backend/implementation_grounding.py"),
        Path("backend/diagnostic_parser.py"),
        Path("backend/context_hardening.py"),
    ]
    forbidden_task_branches = [
        'task == "fastapi"',
        'task == "flutter"',
        'task == "matrix"',
        'task == "cli"',
        'task_name == "fastapi"',
        'task_name == "flutter"',
        'task_name == "matrix"',
        'task_name == "cli"',
    ]

    for fpath in files_to_check:
        if fpath.exists():
            content = fpath.read_text(encoding="utf-8").lower()
            for branch in forbidden_task_branches:
                assert branch not in content, f"Forbidden task-specific branch '{branch}' found in {fpath}"


# ==============================================================================
# 18. Generation Truncation Detection
# ==============================================================================
def test_generation_truncation_detection():
    """18. Unterminated strings, dangling decorators, or abrupt EOFs are flagged."""
    # Truncated 1: unclosed triple-quotes
    code_unclosed_str = 'def run():\n    """This docstring is not closed'
    is_trunc, msg = detect_generation_truncation(code_unclosed_str, "main.py")
    assert is_trunc is True
    assert "triple-quoted" in msg.lower() or "unterminated" in msg.lower()

    # Truncated 2: dangling decorator at EOF
    code_dangling_dec = 'import fastapi\napp = fastapi.FastAPI()\n@app.get("/items")'
    is_trunc, msg = detect_generation_truncation(code_dangling_dec, "main.py")
    assert is_trunc is True
    assert "dangling decorator" in msg.lower() or "decorator" in msg.lower()

    # Truncated 3: abrupt statement ending with self._
    code_abrupt_token = "class Matrix:\n    def __init__(self):\n        return self._"
    is_trunc, msg = detect_generation_truncation(code_abrupt_token, "main.py")
    assert is_trunc is True
    assert "self._" in msg

    # Complete code: should pass without truncation
    code_complete = "def run():\n    return 42\n"
    is_trunc, msg = detect_generation_truncation(code_complete, "main.py")
    assert is_trunc is False
    assert msg is None

    # Test gate B3 quarantine on truncation
    state = {
        "target_language": "python",
        "code_files": {"main.py": code_unclosed_str},
        "contract": {"task_intent": {"authoritative_target_file": "main.py"}}
    }
    contract = validate_developer_phase(state)
    assert contract["verdict"] == "FAIL"
    trunc_v = [v for v in contract["violations"] if v.get("criterion") == "generation_truncation_safety"]
    assert len(trunc_v) == 1
    assert "GENERATION_TRUNCATION_DETECTED" in trunc_v[0]["message"]


# ==============================================================================
# 19. Compact Evidence Does Not Discard Independent Failures
# ==============================================================================
def test_compact_evidence_does_not_discard_independent_failures():
    """19. High-density compact format preserves distinct independent failure categories without starvation."""
    # 8 identical assertion failures on test_duplicate
    failures = [
        FailingTest(test_name=f"test_dup_{i}", test_file="test_main.py", failure_type="assertion_failure", message="assert 1 == 2")
        for i in range(8)
    ]
    # 1 independent syntax failure
    failures.append(FailingTest(test_name="test_syntax", test_file="test_main.py", failure_type="syntax_parse_error", message="invalid syntax"))
    # 1 independent import failure
    failures.append(FailingTest(test_name="test_import", test_file="test_main.py", failure_type="import_module_error", message="no module named x"))

    selected, omitted = prioritize_failures(failures, max_selected=3)
    assert len(selected) == 3
    selected_types = {t.failure_type for t in selected}

    # All 3 distinct categories are selected; duplicate assertions do not starve syntax and import!
    assert "syntax_parse_error" in selected_types
    assert "import_module_error" in selected_types
    assert "assertion_failure" in selected_types
    assert len(omitted) == 7


# ==============================================================================
# 20. Unknown Causal Attribution Remains Unknown
# ==============================================================================
def test_unknown_causal_attribution_remains_unknown():
    """20. Causal status defaults to UNKNOWN when root cause cannot be deterministically proven."""
    ev = CanonicalImplementationEvidence(
        evidence_id="EV-UNK-1",
        evidence_type="RUNTIME_EXCEPTION",
        source="pytest",
        file_reference="unknown_file",
        observed="Random unhandled exception in background thread",
        compatibility_status="UNKNOWN"
    )
    assert ev.causal_status == "UNKNOWN"
    compact = ev.format_compact()
    # UNKNOWN causal status is omitted from compact string to avoid polluting context
    assert "Causal: UNKNOWN" not in compact

    # If causal status is explicitly set to PROVEN, it is included
    ev.causal_status = "PROVEN"
    assert "Causal: PROVEN" in ev.format_compact()
