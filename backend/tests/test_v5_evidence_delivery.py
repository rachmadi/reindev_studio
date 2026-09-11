"""
Test Suite: V5 Evidence Delivery & V3 Static Symbol Resolvability
Verifies V5-1 (Preservation), V5-2 (Rendering), V5-3 (Generic Prescriptions), and V5-4 (V3 Resolvability).
"""

import ast
import pytest
from typing import Dict, Any

from backend.contextual_evidence import (
    ContextualEvidencePackage,
    ViolationItem,
    render_repair_directive,
)
from backend.context_assembler import (
    assemble_b5_evidence,
    assemble_b3_evidence,
    synthesize_b5_actionable_prescriptions,
)
from backend.phase_validators import (
    audit_python_module_symbol_resolvability,
    validate_developer_phase,
)


# ==============================================================================
# V5-1: Evidence Preservation Tests
# ==============================================================================

def test_v5_1_evidence_preservation_retains_failing_tests_and_excerpt():
    """V5-1: assemble_b5_evidence retains structured failing tests and error excerpt."""
    output = (
        "FAILED tests/test_products.py::test_create_product - assert 422 == 201\n"
        "+  where 422 = <Response [422 Unprocessable Content]>.status_code\n"
        "E   assert 422 == 201\n"
        "tests/test_products.py:35: AssertionError\n"
    )
    test_results = {
        "passed": False,
        "failed_count": 1,
        "passed_count": 0,
        "exit_code": 1,
        "output": output,
    }
    state = {
        "run_id": "test_v5_1",
        "iteration_count": 1,
        "max_iterations": 10,
        "target_language": "python",
        "code_files": {"main.py": "from fastapi import FastAPI\napp = FastAPI()"},
        "test_files": {"test_main.py": "def test_create_product(): assert 422 == 201"},
        "contract": {"task_intent": {"authoritative_target_file": "main.py"}},
        "test_results": test_results,
    }
    violations = [
        ViolationItem(
            violation_id="VIO-B5-001",
            criterion="sandbox_tests_passed",
            severity="CRITICAL",
            location="sandbox_runner",
            observed_state="1 test(s) failed with exit code 1",
            expected_state="All sandbox tests pass with exit code 0",
            source_detector="B5_EXECUTOR_ITERATION",
        )
    ]

    pkg = assemble_b5_evidence(
        state=state,
        violations=violations,
        regressions=[],
        evidence=[],
        run_id="test_v5_1",
        iteration=1,
    )

    ev_items = {ev["item"]: ev for ev in pkg.evidence}
    assert "sandbox_failing_tests" in ev_items, "Must retain sandbox_failing_tests evidence"
    failing_list = ev_items["sandbox_failing_tests"]["observed"]
    assert len(failing_list) >= 1
    assert any("test_create_product" in ft["test_name"] for ft in failing_list)

    assert "sandbox_error_excerpt" in ev_items, "Must retain sandbox_error_excerpt evidence"
    excerpt = ev_items["sandbox_error_excerpt"]["observed"]
    assert "422" in excerpt or "AssertionError" in excerpt

    for req in pkg.required_changes:
        assert req.deterministic_requirement, "RequiredChange must not have empty requirement"
        assert "Required:" in req.deterministic_requirement


# ==============================================================================
# V5-2: Evidence Rendering Tests
# ==============================================================================

def test_v5_2_evidence_rendering_includes_deterministic_section():
    """V5-2: render_repair_directive renders [DETERMINISTIC SANDBOX FAILURE EVIDENCE]."""
    failing_tests = [
        {
            "test_name": "test_create_product",
            "failure_type": "assertion_error",
            "message": "assert 422 == 201",
            "expected": "201",
            "actual": "422",
            "source_file": "tests/test_products.py",
            "source_line": 35,
            "traceback_excerpt": "assert response.status_code == 201\nE   assert 422 == 201",
        }
    ]
    evidence = [
        {
            "item": "sandbox_failing_tests",
            "evidence_class": "DETERMINISTIC",
            "observed": failing_tests,
            "expected": "0 failing tests",
            "status": "INVALID",
        },
        {
            "item": "sandbox_error_excerpt",
            "evidence_class": "DETERMINISTIC",
            "observed": "E   assert 422 == 201\n+ where 422 = response.status_code",
            "expected": "0 errors",
            "status": "INVALID",
        },
    ]
    pkg = ContextualEvidencePackage.from_dict({
        "package_id": "test_pkg",
        "timestamp": "2026-09-11T00:00:00Z",
        "validator": "B5_EXECUTOR_ITERATION",
        "phase": "EXECUTOR",
        "validator_type": "ITERATION",
        "verdict": "FAIL",
        "causal_owner": "DEVELOPER",
        "failure_summary": "Sandbox execution failed: 1 test(s) failed (exit_code=1, passed=0).",
        "root_causes": ["Test failed: test_create_product"],
        "violations": [],
        "evidence": evidence,
    })

    rendered = render_repair_directive(pkg)
    assert "[DETERMINISTIC SANDBOX FAILURE EVIDENCE]" in rendered
    assert "test_create_product" in rendered
    assert "Expected: 201 | Actual: 422" in rendered
    assert "tests/test_products.py:35" in rendered
    assert "assert 422 == 201" in rendered


# ==============================================================================
# V5-3: Generic Actionable Prescriptions Tests
# ==============================================================================

def test_v5_3_prescription_http_422_status_mismatch():
    """V5-3: Detects HTTP 422 vs 201/200 and prescribes payload schema validation repair."""
    output = (
        "FAILED tests/test_products.py::test_create_product - assert 422 == 201\n"
        "+  where 422 = <Response [422 Unprocessable Content]>.status_code\n"
        "E   assert 422 == 201\n"
    )
    state = {
        "test_files": {},
        "contract": {"task_intent": {"authoritative_target_file": "main.py"}},
    }
    prescriptions = synthesize_b5_actionable_prescriptions(
        state=state,
        violations=[],
        output=output,
        target_lang="python",
        auth_file="main.py",
    )
    assert len(prescriptions) >= 1
    rx = prescriptions[0]
    assert rx.prescription_id == "RX-B5-HTTP-422-SCHEMA"
    assert "422" in rx.observed_failure
    assert "201" in rx.observed_failure
    assert "Unprocessable Content" in rx.required_change
    assert "request payload" in rx.required_change.lower() or "request model" in rx.required_change.lower()


def test_v5_3_prescription_http_status_general_mismatch():
    """V5-3: Detects general HTTP status mismatch (e.g. 404 vs 200)."""
    output = (
        "FAILED tests/test_items.py::test_get_item - assert 404 == 200\n"
        "E   assert 404 == 200\n"
    )
    state = {
        "test_files": {},
        "contract": {"task_intent": {"authoritative_target_file": "main.py"}},
    }
    prescriptions = synthesize_b5_actionable_prescriptions(
        state=state,
        violations=[],
        output=output,
        target_lang="python",
        auth_file="main.py",
    )
    assert len(prescriptions) >= 1
    rx = prescriptions[0]
    assert rx.prescription_id == "RX-B5-HTTP-STATUS-MISMATCH"
    assert "404" in rx.observed_failure
    assert "200" in rx.observed_failure


def test_v5_3_prescription_name_error():
    """V5-3: Detects NameError and prescribes import or definition for the symbol."""
    output = (
        "ERROR collecting tests/test_products.py\n"
        "main.py:15: in <module>\n"
        "    class Product(BaseModel):\n"
        "main.py:18: in Product\n"
        "    model_config = ConfigDict(extra=\'forbid\')\n"
        "E   NameError: name 'ConfigDict' is not defined\n"
    )
    state = {
        "test_files": {},
        "contract": {"task_intent": {"authoritative_target_file": "main.py"}},
    }
    prescriptions = synthesize_b5_actionable_prescriptions(
        state=state,
        violations=[],
        output=output,
        target_lang="python",
        auth_file="main.py",
    )
    assert len(prescriptions) >= 1
    rx = prescriptions[0]
    assert rx.prescription_id == "RX-B5-NAME-ERROR"
    assert "ConfigDict" in rx.observed_failure
    assert "ConfigDict" in rx.implementation_symbol
    assert "import" in rx.required_change.lower()


def test_v5_3_prescription_collection_failure():
    """V5-3: Detects pytest collection failure and prescribes resolving import/syntax errors."""
    output = (
        "ERROR collecting tests/test_main.py\n"
        "ImportError: cannot import name 'UnusedSymbol' from 'main'\n"
    )
    state = {
        "test_files": {},
        "contract": {"task_intent": {"authoritative_target_file": "main.py"}},
    }
    prescriptions = synthesize_b5_actionable_prescriptions(
        state=state,
        violations=[],
        output=output,
        target_lang="python",
        auth_file="main.py",
    )
    assert len(prescriptions) >= 1
    rx = prescriptions[0]
    assert rx.prescription_id == "RX-B5-COLLECTION-ERROR"
    assert "collection" in rx.observed_failure.lower() or "import" in rx.observed_failure.lower()


def test_v5_3_prescription_value_assertion():
    """V5-3: Detects value assertion mismatch (e.g. assert total == 100)."""
    output = (
        "FAILED tests/test_math.py::test_sum - assert 80 == 100\n"
        "E   assert 80 == 100\n"
    )
    state = {
        "test_files": {},
        "contract": {"task_intent": {"authoritative_target_file": "main.py"}},
    }
    prescriptions = synthesize_b5_actionable_prescriptions(
        state=state,
        violations=[],
        output=output,
        target_lang="python",
        auth_file="main.py",
    )
    assert len(prescriptions) >= 1
    rx = prescriptions[0]
    assert rx.prescription_id == "RX-B5-VALUE-ASSERTION-MISMATCH"
    assert "80" in rx.observed_failure
    assert "100" in rx.observed_failure


# ==============================================================================
# V5-4: V3 Static Symbol Resolvability Tests
# ==============================================================================

def test_v5_4_audit_detects_unimported_configdict():
    """V5-4: audit_python_module_symbol_resolvability detects ConfigDict without import."""
    code = (
        "from pydantic import BaseModel\n\n"
        "class Product(BaseModel):\n"
        "    id: int\n"
        "    name: str\n"
        "    model_config = ConfigDict(extra=\'forbid\')\n"
    )
    tree = ast.parse(code)
    unresolved = audit_python_module_symbol_resolvability(tree, "main.py")
    assert len(unresolved) >= 1
    syms = [u[0] for u in unresolved]
    assert "ConfigDict" in syms


def test_v5_4_audit_passes_when_configdict_is_imported():
    """V5-4: audit_python_module_symbol_resolvability passes when ConfigDict is imported."""
    code = (
        "from pydantic import BaseModel, ConfigDict\n\n"
        "class Product(BaseModel):\n"
        "    id: int\n"
        "    name: str\n"
        "    model_config = ConfigDict(extra=\'forbid\')\n"
    )
    tree = ast.parse(code)
    unresolved = audit_python_module_symbol_resolvability(tree, "main.py")
    assert len(unresolved) == 0


def test_v5_4_audit_does_not_flag_function_local_variables():
    """V5-4: audit does not flag local variables inside function definitions."""
    code = (
        "def compute(val: int) -> int:\n"
        "    local_var = val * 2\n"
        "    return local_var + 1\n"
    )
    tree = ast.parse(code)
    unresolved = audit_python_module_symbol_resolvability(tree, "main.py")
    assert len(unresolved) == 0


def test_v5_4_validate_developer_phase_rejects_unresolved_symbol():
    """V5-4: validate_developer_phase returns FAIL when unresolved symbol is in class body."""
    bad_code = (
        "from pydantic import BaseModel\n\n"
        "class Product(BaseModel):\n"
        "    id: int\n"
        "    name: str\n"
        "    model_config = ConfigDict(extra=\'forbid\')\n"
    )
    state = {
        "run_id": "test_v5_4",
        "iteration_count": 0,
        "max_iterations": 10,
        "target_language": "python",
        "code_files": {"main.py": bad_code},
        "contract": {
            "task_intent": {"authoritative_target_file": "main.py"},
            "data_models": [{"model_name": "Product"}],
            "interface_contracts": [],
        },
    }
    result = validate_developer_phase(state)
    assert result["verdict"] == "FAIL"
    criteria_violations = [v["criterion"] for v in result["violations"]]
    assert "symbol_resolvability" in criteria_violations
    assert any("ConfigDict" in v["message"] for v in result["violations"])


def test_v5_4_validate_developer_phase_passes_when_all_symbols_resolved():
    """V5-4: validate_developer_phase returns PASS when all class/module symbols are resolved."""
    good_code = (
        "from pydantic import BaseModel, ConfigDict\n\n"
        "class Product(BaseModel):\n"
        "    id: int\n"
        "    name: str\n"
        "    model_config = ConfigDict(extra=\'forbid\')\n"
    )
    state = {
        "run_id": "test_v5_4_pass",
        "iteration_count": 0,
        "max_iterations": 10,
        "target_language": "python",
        "code_files": {"main.py": good_code},
        "contract": {
            "task_intent": {"authoritative_target_file": "main.py"},
            "data_models": [{"model_name": "Product"}],
            "interface_contracts": [],
        },
    }
    result = validate_developer_phase(state)
    assert result["verdict"] == "PASS"
    assert not any(v["criterion"] == "symbol_resolvability" for v in result["violations"])


def test_v5_2_developer_agent_prompt_with_cep(monkeypatch):
    """V5-2: developer_agent builds prompt with CEP without UnboundLocalError."""
    from backend.agents import developer as dev_module
    from langchain_core.language_models.fake import FakeListLLM

    fake_llm = FakeListLLM(responses=["=== FILE: main.py ===\n# code\n=== END FILE ==="])
    monkeypatch.setattr(dev_module, "get_llm", lambda *a, **kw: fake_llm)

    cep_dict = {
        "package_id": "PKG-001",
        "timestamp": "2026-09-11T00:00:00Z",
        "validator": "B5_EXECUTOR_ITERATION",
        "phase": "EXECUTOR",
        "validator_type": "ITERATION",
        "verdict": "FAIL",
        "causal_owner": "DEVELOPER",
        "failure_summary": "1 test failed",
        "root_causes": ["Test failure"],
        "violations": [],
    }

    state = {
        "run_id": "test_prompt",
        "task": "Test Task",
        "architecture_plan": "JSON plan",
        "target_language": "python",
        "iteration_count": 1,
        "max_iterations": 10,
        "code_files": {"main.py": "def foo(): pass"},
        "test_files": {"test_main.py": "def test_foo(): assert True"},
        "contract": {"task_intent": {"authoritative_target_file": "main.py"}},
        "latest_cep": cep_dict,
    }

    result = dev_module.developer_agent(state)
    assert "code_files" in result
    assert "main.py" in result["code_files"]


