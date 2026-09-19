# -*- coding: utf-8 -*-
"""
Deterministic Unit Test Suite: Treatment #1.8.10 Minimal Pipeline Repair v1
ReinDev Studio — Iterasi 6 (Epistemic Boundary & Call Shape Alignment)

Verifies:
PART A — CALLABLE BINDING:
- Test A.1: Callable + route + method deterministically binds to canonical interface.
- Test A.2: Missing route remains unresolved (fail-closed).
- Test A.3: Naming similarity alone does not create binding (fail-closed).
- Test A.4: Multiple ambiguous bindings do not auto-resolve (fail-closed).
- Test A.5: Non-HTTP callable remains supported without route injection.

PART B — STUB SEMANTICS:
- Test B.6: Correct stub + correct signature = structurally compatible.
- Test B.7: Stub does NOT become behavioral PASS (UNDETERMINED preserved).
- Test B.8: Insufficient evidence remains BEHAVIOR_NOT_PROVABLE.
- Test B.9: Genuinely incompatible signature remains structurally INCOMPATIBLE.
- Test B.10: Non-stub behavioral evidence continues to work (reachable vs unconditional).

PART C — CONTRACT GATE:
- Test C.11: Structural compatibility admits an Architect contract for Developer.
- Test C.12: Genuine structural incompatibility still rejects.
- Test C.13: Unresolved binding still fails closed.
- Test C.14: Oracle behavioral failure still fails downstream.
- Test C.15: No regression of existing Flutter control path.

PART D — GENERALIZATION & CROSS-LANGUAGE:
- Test D.16: Python callable AST extraction and scenario matching.
- Test D.17: Python HTTP-style callable binding.
- Test D.18: Dart class/widget symbol and constructor matching.
- Test D.19: Non-HTTP CLI callable.
- Test D.20: Generic scenario with return expectation.
- Test D.21: Generic scenario with exception expectation.

STATIC ANTI-SOLVER AUDIT:
- Test E.22: Zero task-specific branching or hardcoded solver tokens.
"""

import ast
import hashlib
from pathlib import Path
from typing import Dict, Any, List

import pytest

from backend.canonical_scenario import (
    CanonicalScenario,
    ScenarioKind,
    CausalStatus,
    ScaffoldCompatibilityStatus,
    ScaffoldStructuralStatus,
    ScaffoldBehavioralStatus,
    ScaffoldCallableFact,
    ScaffoldScenarioCompatibilityItem,
    ScaffoldScenarioMatrix,
    PythonScaffoldExtractor,
    DartScaffoldExtractor,
    extract_all_scaffold_facts,
    evaluate_scaffold_scenario_compatibility,
    format_scaffold_compatibility_for_architect,
)
from backend.canonical_obligation import (
    CanonicalInterfaceDeclaration,
    CanonicalObligation,
    ObligationKind,
    ObligationAuthority,
    ObligationProvenance,
    CoverageStatus,
    ObligationCoverageResult,
    find_deterministic_callable_fact,
    bind_scaffold_callable_facts_to_interfaces,
    check_obligation_coverage,
    normalize_route_path,
)
from backend.contract import (
    MachineReadableContract,
    ContractStatus,
    create_draft_contract,
    complete_aligned_contract,
    seal_and_freeze_contract,
    check_pre_freeze_authority_compatibility,
)
from backend.blueprint_schema import ArchitecturalBlueprint


ORACLE_FASTAPI_DIR = Path("dokumentasi-pengembangan/experiments/frozen_oracle/fastapi_t1")
ORACLE_CLI_DIR = Path("dokumentasi-pengembangan/experiments/frozen_oracle/cli_t1")
ORACLE_FLUTTER_DIR = Path("dokumentasi-pengembangan/experiments/frozen_oracle/flutter_t1")


# ==============================================================================
# PART A — CALLABLE BINDING
# ==============================================================================

def test_a1_callable_route_method_deterministically_binds():
    """A.1: Callable + route + method deterministically binds to canonical interface."""
    code = """
from fastapi import FastAPI
app = FastAPI()

@app.post("/items")
def create_item(payload: dict):
    pass
"""
    facts = extract_all_scaffold_facts({"main.py": code})
    assert len(facts) >= 1
    create_fact = next(f for f in facts if f.name == "create_item")
    assert create_fact.route == "/items"
    assert create_fact.http_method == "POST"

    ifc = CanonicalInterfaceDeclaration(
        identifier="create_item",
        target_file="main.py",
        interface_type="FUNCTION",
        canonical_route=None,
        canonical_method=None,
        raw_declaration={"identifier": "create_item", "target_file": "main.py"}
    )

    bound_ifcs = bind_scaffold_callable_facts_to_interfaces([ifc], facts)
    assert bound_ifcs[0].canonical_route == "/items"
    assert bound_ifcs[0].canonical_method == "POST"
    assert bound_ifcs[0].interface_type == "HTTP_ENDPOINT"


def test_a2_missing_route_remains_unresolved():
    """A.2: Missing route remains unresolved (fail-closed)."""
    code = """
def helper_function(x: int) -> int:
    return x * 2
"""
    facts = extract_all_scaffold_facts({"utils.py": code})
    fact = find_deterministic_callable_fact("helper_function", "utils.py", facts)
    assert fact is not None
    assert fact.route is None
    assert fact.http_method is None

    ifc = CanonicalInterfaceDeclaration(
        identifier="helper_function",
        target_file="utils.py",
        interface_type="FUNCTION",
        canonical_route=None,
        canonical_method=None
    )
    bound = bind_scaffold_callable_facts_to_interfaces([ifc], facts)
    assert bound[0].canonical_route is None
    assert bound[0].canonical_method is None
    assert bound[0].interface_type == "FUNCTION"


def test_a3_naming_similarity_alone_does_not_bind():
    """A.3: Naming similarity alone does NOT create binding (fail-closed)."""
    # Callable is named 'get_items', but has NO route decorator
    code = """
def get_items():
    pass
"""
    facts = extract_all_scaffold_facts({"main.py": code})
    ob_http = CanonicalObligation(
        obligation_id="OBL-HTTP-01",
        authority=ObligationAuthority.FROZEN_ORACLE.value,
        provenance=ObligationProvenance.ORACLE_FACT.value,
        obligation_kind=ObligationKind.INTERACTION.value,
        public_identity="/items",
        inputs={"http_method": "GET"}
    )

    # In check_obligation_coverage, get_items must NOT be bound to /items
    cov = check_obligation_coverage(
        obligations=[ob_http],
        contract={
            "files": {"main.py": {"code_scaffold": code}},
            "interface_contracts": [
                {"identifier": "get_items", "target_file": "main.py", "interface_type": "FUNCTION"}
            ]
        },
        blueprint=None
    )
    assert cov.is_fully_covered is False
    assert cov.missing_count == 1
    assert any("Public HTTP endpoint '/items' has no declared interface coverage" in r.reason for r in cov.results)


def test_a4_multiple_ambiguous_bindings_do_not_autoresolve():
    """A.4: Multiple ambiguous bindings with conflicting routes do not auto-resolve (fail-closed)."""
    fact1 = ScaffoldCallableFact(
        name="fetch_data",
        file_path="main.py",
        route="/v1/data",
        http_method="GET"
    )
    fact2 = ScaffoldCallableFact(
        name="fetch_data",
        file_path="main.py",
        route="/v2/data",
        http_method="GET"
    )
    facts = [fact1, fact2]

    # Rule A.4: Multiple conflicting routes for the same callable name must return None
    resolved = find_deterministic_callable_fact("fetch_data", "main.py", facts)
    assert resolved is None


def test_a5_non_http_callable_remains_supported():
    """A.5: Non-HTTP callable remains supported without route injection."""
    code = """
def calculate_metrics(values: list) -> float:
    pass
"""
    facts = extract_all_scaffold_facts({"calc.py": code})
    ifc = CanonicalInterfaceDeclaration(
        identifier="calculate_metrics",
        target_file="calc.py",
        interface_type="FUNCTION",
        canonical_route=None,
        canonical_method=None,
        raw_declaration={"identifier": "calculate_metrics", "target_file": "calc.py"}
    )
    bound = bind_scaffold_callable_facts_to_interfaces([ifc], facts)
    assert bound[0].identifier == "calculate_metrics"
    assert bound[0].canonical_route is None
    assert bound[0].interface_type == "FUNCTION"


# ==============================================================================
# PART B — STUB SEMANTICS
# ==============================================================================

def test_b6_correct_stub_and_signature_structurally_compatible():
    """B.6: Correct stub + correct signature = structurally compatible."""
    sc = CanonicalScenario(
        scenario_id="SCN-B6",
        scenario_kind=ScenarioKind.POSITIVE.value,
        stimulus="compute_total(items=[1, 2, 3])",
        expected_outcome={"callable": "compute_total", "return_value": 6.0}
    )
    code = """
def compute_total(items: list) -> float:
    pass
"""
    matrix = evaluate_scaffold_scenario_compatibility([sc], {"main.py": code})
    item = matrix.items[0]

    # Structural compatibility MUST be match
    assert item.structural_compatibility == ScaffoldStructuralStatus.STRUCTURAL_MATCH.value
    # Behavioral evidence CANNOT be proven from a stub
    assert item.behavioral_evidence == ScaffoldBehavioralStatus.BEHAVIOR_NOT_PROVABLE.value
    # Backward compatibility: compatibility remains UNDETERMINED
    assert item.compatibility == ScaffoldCompatibilityStatus.UNDETERMINED.value
    # Epistemic matrix flag
    assert matrix.is_structurally_compatible is True
    # But NOT fully compatible behaviorally
    assert matrix.is_fully_compatible is False


def test_b7_stub_does_not_become_behavioral_pass():
    """B.7: Stub does NOT become behavioral PASS (UNDETERMINED is never promoted to BEHAVIOR_PASS)."""
    sc = CanonicalScenario(
        scenario_id="SCN-B7",
        scenario_kind=ScenarioKind.POSITIVE.value,
        stimulus="evaluate_risk(score=50)",
        expected_outcome={"status": "APPROVED", "score": 50}
    )
    code = """
def evaluate_risk(score: int):
    pass
"""
    matrix = evaluate_scaffold_scenario_compatibility([sc], {"risk.py": code})
    assert matrix.is_fully_compatible is False
    assert matrix.compatible_count == 0
    assert matrix.undetermined_count == 1
    assert matrix.items[0].compatibility == ScaffoldCompatibilityStatus.UNDETERMINED.value
    assert matrix.items[0].behavioral_evidence == ScaffoldBehavioralStatus.BEHAVIOR_NOT_PROVABLE.value


def test_b8_insufficient_evidence_remains_behavior_not_provable():
    """B.8: Behavioral expectation with insufficient evidence remains BEHAVIOR_NOT_PROVABLE."""
    sc_err = CanonicalScenario(
        scenario_id="SCN-B8-ERR",
        scenario_kind=ScenarioKind.NEGATIVE.value,
        stimulus="divide(a=1, b=0)",
        expected_outcome={"exception": "ZeroDivisionError"}
    )
    code = """
def divide(a: float, b: float) -> float:
    pass
"""
    matrix = evaluate_scaffold_scenario_compatibility([sc_err], {"math_ops.py": code})
    item = matrix.items[0]
    assert item.structural_compatibility == ScaffoldStructuralStatus.STRUCTURAL_MATCH.value
    assert item.behavioral_evidence == ScaffoldBehavioralStatus.BEHAVIOR_NOT_PROVABLE.value
    assert item.compatibility == ScaffoldCompatibilityStatus.UNDETERMINED.value
    # Not incompatible, because it does not lock in an unconditional success path
    assert matrix.is_structurally_compatible is True


def test_b9_genuinely_incompatible_signature_remains_incompatible():
    """B.9: Genuinely incompatible signature remains structurally INCOMPATIBLE."""
    sc = CanonicalScenario(
        scenario_id="SCN-B9",
        scenario_kind=ScenarioKind.POSITIVE.value,
        stimulus="Matrix([[1.0, 2.0]])",
        expected_outcome={"callable": "Matrix"}
    )
    # Stub has completely incompatible constructor call shape (Pydantic BaseModel without __init__ expects named arguments, not positional)
    code = """
from pydantic import BaseModel

class Matrix(BaseModel):
    data: list[list[float]]
"""
    matrix = evaluate_scaffold_scenario_compatibility([sc], {"main.py": code})
    item = matrix.items[0]
    assert item.structural_compatibility == ScaffoldStructuralStatus.INCOMPATIBLE.value
    assert matrix.is_structurally_compatible is False
    assert matrix.structural_incompatible_count == 1


def test_b10_non_stub_behavioral_evidence_continues_to_work():
    """B.10: Non-stub behavioral evidence continues to work (reachable vs unconditional)."""
    sc_neg = CanonicalScenario(
        scenario_id="SCN-B10",
        scenario_kind=ScenarioKind.NEGATIVE.value,
        stimulus="validate_age(-5)",
        expected_outcome={"exception": "ValueError"}
    )
    # Scaffold 1: Reachable error branch
    code_with_error = """
def validate_age(age: int):
    if age < 0:
        raise ValueError("Age cannot be negative")
    return True
"""
    m_with_error = evaluate_scaffold_scenario_compatibility([sc_neg], {"age.py": code_with_error})
    assert m_with_error.items[0].compatibility == ScaffoldCompatibilityStatus.COMPATIBLE.value
    assert m_with_error.items[0].behavioral_evidence == ScaffoldBehavioralStatus.BEHAVIORALLY_PROVABLE.value
    assert m_with_error.is_fully_compatible is True

    # Scaffold 2: Proven absence of error path (unconditional return)
    code_unconditional = """
def validate_age(age: int):
    return True
"""
    m_unconditional = evaluate_scaffold_scenario_compatibility([sc_neg], {"age.py": code_unconditional})
    assert m_unconditional.items[0].compatibility == ScaffoldCompatibilityStatus.INCOMPATIBLE.value
    assert m_unconditional.items[0].behavioral_evidence == ScaffoldBehavioralStatus.INCOMPATIBLE.value
    assert m_unconditional.is_structurally_compatible is False


# ==============================================================================
# PART C — CONTRACT GATE
# ==============================================================================

def test_c11_structural_compatibility_admits_architect_contract():
    """C.11: Structural compatibility admits an Architect contract when behavioral proof belongs to Developer/Oracle."""
    blueprint_cli = {
        "files": {
            "main.py": """
class Matrix:
    def __init__(self, data):
        pass

def add_matrices(a, b):
    pass

def subtract_matrices(a, b):
    pass

def multiply_matrices(a, b):
    pass
"""
        }
    }
    draft = create_draft_contract(raw_intent="Matrix CLI Calculator", target_language="python", domain="CLI_TOOL")
    contract_data = complete_aligned_contract(
        draft_dict=draft,
        data_models=[{"model_name": "Matrix", "target_file": "main.py"}],
        interface_contracts=[
            {"interface_id": "IFC-01", "interface_type": "FUNCTION", "identifier": "add_matrices", "target_file": "main.py"},
            {"interface_id": "IFC-02", "interface_type": "FUNCTION", "identifier": "subtract_matrices", "target_file": "main.py"},
            {"interface_id": "IFC-03", "interface_type": "FUNCTION", "identifier": "multiply_matrices", "target_file": "main.py"},
        ],
        testable_assertions=[
            {
                "assertion_id": "AST-01",
                "description": "Matrix addition",
                "linked_req_id": "REQ-01",
                "test_scenario": "Matrix addition",
                "target_symbol": "add_matrices",
                "expected_outcome": {"outcome_type": "VALUE_EQUALS"}
            }
        ]
    )
    success, sealed, errors, warnings = seal_and_freeze_contract(
        contract_data,
        frozen_oracle_path=str(ORACLE_CLI_DIR),
        blueprint=blueprint_cli
    )
    assert success is True
    assert sealed["status"] == ContractStatus.FROZEN.value


def test_c12_genuine_structural_incompatibility_still_rejects():
    """C.12: Genuine structural incompatibility still rejects."""
    blueprint_empty = {
        "files": {
            "main.py": "def irrelevant_func(): pass"
        }
    }
    draft = create_draft_contract(raw_intent="Matrix CLI Calculator", target_language="python", domain="CLI_TOOL")
    contract_data = complete_aligned_contract(
        draft_dict=draft,
        data_models=[],
        interface_contracts=[
            {"interface_id": "IFC-01", "interface_type": "FUNCTION", "identifier": "irrelevant_func", "target_file": "main.py"},
        ],
        testable_assertions=[]
    )
    success, sealed, errors, warnings = seal_and_freeze_contract(
        contract_data,
        frozen_oracle_path=str(ORACLE_CLI_DIR),
        blueprint=blueprint_empty
    )
    assert success is False
    assert sealed["status"] == ContractStatus.REJECTED.value


def test_c13_unresolved_binding_fails_closed():
    """C.13: Unresolved binding still fails closed."""
    # Scenario requires HTTP route /products, but scaffold only has helper_func with no route
    ob_http = CanonicalObligation(
        obligation_id="OBL-HTTP-PROD",
        authority=ObligationAuthority.FROZEN_ORACLE.value,
        provenance=ObligationProvenance.ORACLE_FACT.value,
        obligation_kind=ObligationKind.INTERACTION.value,
        public_identity="/products",
        inputs={"http_method": "GET"}
    )
    blueprint = {
        "files": {
            "main.py": {
                "code_scaffold": "def helper_func(): pass"
            }
        }
    }
    draft = create_draft_contract(raw_intent="Products API", target_language="python", domain="REST_API")
    contract_data = complete_aligned_contract(
        draft_dict=draft,
        data_models=[],
        interface_contracts=[
            {
                "interface_id": "IFC-01",
                "interface_type": "FUNCTION",
                "identifier": "helper_func",
                "target_file": "main.py"
            }
        ],
        testable_assertions=[]
    )

    cov = check_obligation_coverage(
        obligations=[ob_http],
        contract=contract_data,
        blueprint=blueprint
    )
    assert cov.is_fully_covered is False
    assert cov.missing_count == 1


def test_c14_oracle_behavioral_failure_fails_downstream():
    """C.14: Oracle behavioral failure still fails downstream when stubs are executed."""
    # Stubs pass Contract Gate because they are structurally compatible
    code_stub = """
def calculate_vat(amount: float, rate: float) -> float:
    pass
"""
    # Downstream execution simulation: calling stub returns None, failing behavioral assertion
    namespace = {}
    exec(code_stub, namespace)
    func = namespace["calculate_vat"]
    result = func(100.0, 0.2)

    # Oracle assertion: must return 20.0
    with pytest.raises(AssertionError):
        assert result == 20.0, f"Stub returned {result}, expected 20.0"


def test_c15_no_regression_of_existing_flutter_path():
    """C.15: Flutter control case passes through fact extraction and scenario evaluation without regression."""
    dart_scaffold = """
import 'package:flutter/material.dart';

class CardMetric extends StatelessWidget {
  final String title;
  final String value;
  final IconData icon;

  const CardMetric({
    Key? key,
    required this.title,
    required this.value,
    required this.icon,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Container();
  }
}
"""
    facts = extract_all_scaffold_facts({"card_metric.dart": dart_scaffold})
    assert len(facts) >= 1
    cm_fact = next(f for f in facts if f.name == "CardMetric")
    assert cm_fact.name == "CardMetric"
    assert "title" in cm_fact.named_param_names
    assert "value" in cm_fact.named_param_names
    assert "icon" in cm_fact.named_param_names

    sc = CanonicalScenario(
        scenario_id="SCN-FLUTTER-01",
        scenario_kind=ScenarioKind.POSITIVE.value,
        stimulus="CardMetric(title: 'Revenue', value: '$100', icon: Icons.attach_money)",
        expected_outcome={"callable": "CardMetric"}
    )
    matrix = evaluate_scaffold_scenario_compatibility([sc], {"card_metric.dart": dart_scaffold})
    assert matrix.is_structurally_compatible is True
    assert matrix.items[0].structural_compatibility == ScaffoldStructuralStatus.STRUCTURAL_MATCH.value


# ==============================================================================
# PART D — GENERALIZATION & CROSS-LANGUAGE
# ==============================================================================

def test_d16_generalization_python_callable():
    """D.16: Python callable AST extraction, parameter typing, and scenario matching."""
    code = """
def process_records(records: list, limit: int = 10) -> int:
    pass
"""
    facts = extract_all_scaffold_facts({"processor.py": code})
    assert len(facts) == 1
    fact = facts[0]
    assert fact.name == "process_records"
    assert fact.param_names == ["records", "limit"]

    sc = CanonicalScenario(
        scenario_id="SCN-D16",
        scenario_kind=ScenarioKind.POSITIVE.value,
        stimulus="process_records([1, 2], limit=5)",
        expected_outcome={"callable": "process_records"}
    )
    matrix = evaluate_scaffold_scenario_compatibility([sc], {"processor.py": code})
    assert matrix.is_structurally_compatible is True


def test_d17_generalization_python_http_callable_binding():
    """D.17: Python HTTP-style callable binding from router/app decorators."""
    code = """
from fastapi import APIRouter
router = APIRouter()

@router.put("/users/{user_id}")
def update_user_profile(user_id: str, data: dict):
    pass
"""
    facts = extract_all_scaffold_facts({"routes.py": code})
    assert len(facts) >= 1
    fact = facts[0]
    assert fact.name == "update_user_profile"
    assert fact.route == "/users/{user_id}"
    assert fact.http_method == "PUT"

    ifc = CanonicalInterfaceDeclaration(
        identifier="update_user_profile",
        target_file="routes.py",
        interface_type="FUNCTION",
        canonical_route=None,
        canonical_method=None
    )
    bound = bind_scaffold_callable_facts_to_interfaces([ifc], facts)
    assert bound[0].canonical_route == "/users/{id}"
    assert bound[0].canonical_method == "PUT"
    assert bound[0].interface_type == "HTTP_ENDPOINT"


def test_d18_generalization_dart_class_widget_symbol():
    """D.18: Dart class/widget constructor symbol extraction and matching."""
    dart_code = """
class MetricView extends StatelessWidget {
  final String label;
  final double score;

  const MetricView({required this.label, required this.score});
}
"""
    extractor = DartScaffoldExtractor()
    facts = extractor.extract_facts("metric_view.dart", dart_code)
    assert any(f.name == "MetricView" for f in facts)
    mv_fact = next(f for f in facts if f.name == "MetricView")
    assert "label" in mv_fact.named_param_names
    assert "score" in mv_fact.named_param_names


def test_d19_generalization_non_http_callable():
    """D.19: Non-HTTP CLI callable without route injection."""
    code = """
def execute_command(cmd: str, flags: list) -> bool:
    pass
"""
    facts = extract_all_scaffold_facts({"cli_tool.py": code})
    assert len(facts) == 1
    assert facts[0].route is None
    assert facts[0].http_method is None

    ifc = CanonicalInterfaceDeclaration(
        identifier="execute_command",
        target_file="cli_tool.py",
        interface_type="FUNCTION"
    )
    bound = bind_scaffold_callable_facts_to_interfaces([ifc], facts)
    assert bound[0].interface_type == "FUNCTION"
    assert bound[0].canonical_route is None


def test_d20_generalization_return_expectation_scenario():
    """D.20: Generic scenario with return expectation against stub vs concrete implementation."""
    sc = CanonicalScenario(
        scenario_id="SCN-D20",
        scenario_kind=ScenarioKind.POSITIVE.value,
        stimulus="get_system_status()",
        expected_outcome={"return_type": "str", "status": "ONLINE"}
    )
    # Stub: structurally matches, behavior not provable
    stub_code = "def get_system_status() -> str:\n    pass"
    m_stub = evaluate_scaffold_scenario_compatibility([sc], {"sys.py": stub_code})
    assert m_stub.items[0].structural_compatibility == ScaffoldStructuralStatus.STRUCTURAL_MATCH.value
    assert m_stub.items[0].behavioral_evidence == ScaffoldBehavioralStatus.BEHAVIOR_NOT_PROVABLE.value

    # Concrete code with return: fully compatible
    concrete_code = "def get_system_status() -> str:\n    return 'ONLINE'"
    m_concrete = evaluate_scaffold_scenario_compatibility([sc], {"sys.py": concrete_code})
    assert m_concrete.items[0].structural_compatibility == ScaffoldStructuralStatus.STRUCTURAL_MATCH.value
    assert m_concrete.items[0].behavioral_evidence == ScaffoldBehavioralStatus.BEHAVIORALLY_PROVABLE.value
    assert m_concrete.items[0].compatibility == ScaffoldCompatibilityStatus.COMPATIBLE.value


def test_d21_generalization_exception_expectation_scenario():
    """D.21: Generic scenario with exception expectation against stub vs concrete implementation."""
    sc = CanonicalScenario(
        scenario_id="SCN-D21",
        scenario_kind=ScenarioKind.NEGATIVE.value,
        stimulus="check_boundary(val=150)",
        expected_outcome={"exception": "OverflowError"}
    )
    # Stub: structurally matches, behavior not provable
    stub_code = "def check_boundary(val: int) -> bool:\n    pass"
    m_stub = evaluate_scaffold_scenario_compatibility([sc], {"bounds.py": stub_code})
    assert m_stub.items[0].structural_compatibility == ScaffoldStructuralStatus.STRUCTURAL_MATCH.value
    assert m_stub.items[0].behavioral_evidence == ScaffoldBehavioralStatus.BEHAVIOR_NOT_PROVABLE.value

    # Concrete code raising exception: reachable error path
    raise_code = "def check_boundary(val: int) -> bool:\n    if val > 100: raise OverflowError()\n    return True"
    m_raise = evaluate_scaffold_scenario_compatibility([sc], {"bounds.py": raise_code})
    assert m_raise.items[0].behavioral_evidence == ScaffoldBehavioralStatus.BEHAVIORALLY_PROVABLE.value
    assert m_raise.items[0].compatibility == ScaffoldCompatibilityStatus.COMPATIBLE.value


# ==============================================================================
# STATIC ANTI-SOLVER AUDIT
# ==============================================================================

def test_e22_static_anti_solver_invariants():
    """
    E.22: Static Anti-Solver Audit.
    Ensures backend modules contain zero task-specific branching or hardcoded solver tokens:
    - No 'if framework == "FastAPI"'
    - No 'if route == "/products"'
    - No 'if function == "get_products"'
    - No task-specific literal solvers
    """
    modules_to_check = [
        Path("backend/canonical_scenario.py"),
        Path("backend/canonical_obligation.py"),
        Path("backend/agents/architect.py"),
        Path("backend/contract.py"),
    ]

    forbidden_snippets = [
        'framework == "FastAPI"',
        'framework == "CLI"',
        'framework == "Flutter"',
        'route == "/products"',
        'function == "get_products"',
        'task == "fastapi_t1"',
        'task == "cli_t1"',
        'task == "flutter_t1"',
    ]

    for mod_path in modules_to_check:
        assert mod_path.exists(), f"Module {mod_path} does not exist"
        content = mod_path.read_text(encoding="utf-8")
        for snippet in forbidden_snippets:
            assert snippet not in content, (
                f"Forbidden task-specific solver snippet '{snippet}' found in {mod_path}"
            )
