# -*- coding: utf-8 -*-
"""
Test Suite: Deterministic Scaffold <-> Acceptance Scenario Compatibility Gate v1
ReinDev Studio — Treatment #1.4

Memverifikasi 24 Gerbang Deterministi:
Gate 01: Positive scenario + matching success path -> COMPATIBLE.
Gate 02: Positive scenario + missing route or parameter mismatch -> INCOMPATIBLE.
Gate 03: Insufficient evidence (stub / opaque) -> UNDETERMINED.
Gate 04: Negative scenario + scaffold with reachable error branch -> COMPATIBLE.
Gate 05: Negative scenario + scaffold with proven absence of error path -> INCOMPATIBLE (and opaque -> UNDETERMINED).
Gate 06: Multiple scenarios evaluated simultaneously.
Gate 07: One scenario repaired without regression.
Gate 08: Regression detection (COMPATIBLE -> INCOMPATIBLE flagged as CRITICAL regression).
Gate 09: Scaffold semantic extraction Python (AST).
Gate 10: Scaffold semantic extraction Dart (token/regex).
Gate 11: Constructor call shape evidence (positional vs named / keyword-only).
Gate 12: Public interface evidence (route and endpoint identity matching).
Gate 13: Control flow observable path evidence (reachable vs unconditional vs opaque).
Gate 14: Current vs historical isolation.
Gate 15: Locked invariant preservation.
Gate 16: Context delivery preserves scenario evidence.
Gate 17: Truncation cannot silently remove evidence.
Gate 18: Oracle immutability (SHA-256 verified).
Gate 19: Sterile executor unchanged (diff clean).
Gate 20: No task-specific solver static audit (AST search).
Gate 21: Cross-language canonical semantic normalization (Python & Dart).
Gate 22: Compatible does not require specific implementation (HOW authority).
Gate 23: Undetermined is never promoted to pass (fail-closed).
Gate 24: Incompatible scaffold cannot freeze contract (status REJECTED).
"""

import ast
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Dict, Any, List

import pytest

from backend.canonical_scenario import (
    CanonicalScenario,
    ScenarioKind,
    CausalStatus,
    ScaffoldCompatibilityStatus,
    ScaffoldCallableFact,
    ScaffoldScenarioCompatibilityItem,
    ScaffoldScenarioMatrix,
    PythonScaffoldExtractor,
    DartScaffoldExtractor,
    _route_matches,
    evaluate_scaffold_scenario_compatibility,
    format_scaffold_compatibility_for_architect,
)
from backend.contract import (
    MachineReadableContract,
    ContractStatus,
    seal_and_freeze_contract,
    check_pre_freeze_authority_compatibility,
    create_draft_contract,
    complete_aligned_contract,
)
from backend.context_hardening import (
    build_architect_decision_context,
)


ORACLE_FASTAPI_DIR = Path("dokumentasi-pengembangan/experiments/frozen_oracle/fastapi_t1")
ORACLE_CLI_DIR = Path("dokumentasi-pengembangan/experiments/frozen_oracle/cli_t1")
ORACLE_FLUTTER_DIR = Path("dokumentasi-pengembangan/experiments/frozen_oracle/flutter_t1")


# ==============================================================================
# Gate 01: Positive scenario + matching success path -> COMPATIBLE
# ==============================================================================
def test_gate_01_positive_scenario_compatible_scaffold():
    sc = CanonicalScenario(
        scenario_id="SCN-POS-01",
        scenario_kind=ScenarioKind.POSITIVE.value,
        stimulus="DELETE /items/1",
        expected_outcome={"http_method": "DELETE", "route": "/items/1", "status_code": 204}
    )
    code = """
from fastapi import FastAPI
app = FastAPI()
items = {1: "existing"}

@app.delete('/items/{item_id}', status_code=204)
def delete_item(item_id: int):
    return None
"""
    matrix = evaluate_scaffold_scenario_compatibility([sc], {"main.py": code})
    assert matrix.is_fully_compatible is True
    assert matrix.compatible_count == 1
    assert matrix.incompatible_count == 0
    assert matrix.undetermined_count == 0
    item = matrix.items[0]
    assert item.compatibility == ScaffoldCompatibilityStatus.COMPATIBLE.value
    assert item.causal_status == CausalStatus.RESOLVED.value


# ==============================================================================
# Gate 02: Positive scenario + missing route -> INCOMPATIBLE
# ==============================================================================
def test_gate_02_positive_scenario_incompatible_scaffold():
    sc = CanonicalScenario(
        scenario_id="SCN-POS-02",
        scenario_kind=ScenarioKind.POSITIVE.value,
        stimulus="GET /users",
        expected_outcome={"http_method": "GET", "route": "/users", "status_code": 200}
    )
    code = """
from fastapi import FastAPI
app = FastAPI()

@app.get('/orders')
def get_orders():
    return []
"""
    matrix = evaluate_scaffold_scenario_compatibility([sc], {"main.py": code})
    assert matrix.is_fully_compatible is False
    assert matrix.incompatible_count == 1
    item = matrix.items[0]
    assert item.compatibility == ScaffoldCompatibilityStatus.INCOMPATIBLE.value
    assert item.causal_status == CausalStatus.VIOLATED.value
    assert "does not define callable" in item.evidence


# ==============================================================================
# Gate 03: Insufficient evidence (stub) -> UNDETERMINED
# ==============================================================================
def test_gate_03_insufficient_evidence_undetermined():
    sc = CanonicalScenario(
        scenario_id="SCN-POS-03",
        scenario_kind=ScenarioKind.POSITIVE.value,
        stimulus="DELETE /items/1",
        expected_outcome={"http_method": "DELETE", "route": "/items/1", "status_code": 204}
    )
    code = """
from fastapi import FastAPI
app = FastAPI()

@app.delete('/items/{item_id}', status_code=204)
def delete_item(item_id: int):
    pass
"""
    matrix = evaluate_scaffold_scenario_compatibility([sc], {"main.py": code})
    assert matrix.is_fully_compatible is False
    assert matrix.undetermined_count == 1
    item = matrix.items[0]
    assert item.compatibility == ScaffoldCompatibilityStatus.UNDETERMINED.value
    assert item.causal_status == CausalStatus.UNRESOLVED.value
    assert "stubbed" in item.evidence.lower()


# ==============================================================================
# Gate 04: Negative scenario + reachable error branch -> COMPATIBLE
# ==============================================================================
def test_gate_04_negative_scenario_compatible_scaffold():
    sc = CanonicalScenario(
        scenario_id="SCN-NEG-04",
        scenario_kind=ScenarioKind.NEGATIVE.value,
        stimulus="DELETE /items/999",
        expected_outcome={"http_method": "DELETE", "route": "/items/999", "status_code": 404}
    )
    code = """
from fastapi import FastAPI, HTTPException
app = FastAPI()
items = {}

@app.delete('/items/{id}', status_code=204)
def delete_item(id: int):
    if id not in items:
        raise HTTPException(status_code=404)
    del items[id]
"""
    matrix = evaluate_scaffold_scenario_compatibility([sc], {"main.py": code})
    assert matrix.is_fully_compatible is True
    assert matrix.compatible_count == 1
    item = matrix.items[0]
    assert item.compatibility == ScaffoldCompatibilityStatus.COMPATIBLE.value
    assert item.causal_status == CausalStatus.RESOLVED.value


# ==============================================================================
# Gate 05: Negative scenario + proven absence -> INCOMPATIBLE (opaque -> UNDETERMINED)
# ==============================================================================
def test_gate_05_negative_scenario_incompatible_scaffold():
    sc = CanonicalScenario(
        scenario_id="SCN-NEG-05",
        scenario_kind=ScenarioKind.NEGATIVE.value,
        stimulus="DELETE /items/999",
        expected_outcome={"http_method": "DELETE", "route": "/items/999", "status_code": 404}
    )

    # Part A: Proven absence (unconditional return, no branch, no error path)
    code_proven_absence = """
from fastapi import FastAPI
app = FastAPI()
items = []

@app.delete('/items/{id}', status_code=204)
def delete_item(id: int):
    global items
    items = [x for x in items if x.id != id]
    return None
"""
    matrix_a = evaluate_scaffold_scenario_compatibility([sc], {"main.py": code_proven_absence})
    assert matrix_a.is_fully_compatible is False
    assert matrix_a.items[0].compatibility == ScaffoldCompatibilityStatus.INCOMPATIBLE.value
    assert matrix_a.items[0].causal_status == CausalStatus.VIOLATED.value
    assert "absence of error path" in matrix_a.items[0].evidence.lower()

    # Part B: Opaque delegation (cannot prove absence statically) -> UNDETERMINED
    code_opaque = """
from fastapi import FastAPI
app = FastAPI()

@app.delete('/items/{id}', status_code=204)
def delete_item(id: int):
    return repo.delete(id)
"""
    matrix_b = evaluate_scaffold_scenario_compatibility([sc], {"main.py": code_opaque})
    assert matrix_b.is_fully_compatible is False
    assert matrix_b.items[0].compatibility == ScaffoldCompatibilityStatus.UNDETERMINED.value
    assert matrix_b.items[0].causal_status == CausalStatus.UNRESOLVED.value
    assert "insufficient static evidence" in matrix_b.items[0].evidence.lower()


# ==============================================================================
# Gate 06: Multiple scenarios evaluated simultaneously
# ==============================================================================
def test_gate_06_multiple_scenarios_evaluation():
    sc_pos = CanonicalScenario(
        scenario_id="SCN-06-POS",
        scenario_kind=ScenarioKind.POSITIVE.value,
        stimulus="DELETE /items/1",
        expected_outcome={"http_method": "DELETE", "route": "/items/1", "status_code": 204}
    )
    sc_neg = CanonicalScenario(
        scenario_id="SCN-06-NEG",
        scenario_kind=ScenarioKind.NEGATIVE.value,
        stimulus="DELETE /items/999",
        expected_outcome={"http_method": "DELETE", "route": "/items/999", "status_code": 404}
    )
    code = """
from fastapi import FastAPI, HTTPException
app = FastAPI()
items = {1: "data"}

@app.delete('/items/{id}', status_code=204)
def delete_item(id: int):
    if id not in items:
        raise HTTPException(status_code=404)
    del items[id]
"""
    matrix = evaluate_scaffold_scenario_compatibility([sc_pos, sc_neg], {"main.py": code})
    assert matrix.is_fully_compatible is True
    assert matrix.compatible_count == 2
    assert matrix.incompatible_count == 0
    assert matrix.undetermined_count == 0


# ==============================================================================
# Gate 07: One scenario repaired without regression
# ==============================================================================
def test_gate_07_one_scenario_repaired_without_regression():
    sc_pos = CanonicalScenario(
        scenario_id="SCN-07-POS",
        scenario_kind=ScenarioKind.POSITIVE.value,
        stimulus="DELETE /items/1",
        expected_outcome={"http_method": "DELETE", "route": "/items/1", "status_code": 204}
    )
    sc_neg = CanonicalScenario(
        scenario_id="SCN-07-NEG",
        scenario_kind=ScenarioKind.NEGATIVE.value,
        stimulus="DELETE /items/999",
        expected_outcome={"http_method": "DELETE", "route": "/items/999", "status_code": 404}
    )

    prev_item_pos = ScaffoldScenarioCompatibilityItem(
        scenario_id="SCN-07-POS",
        compatibility=ScaffoldCompatibilityStatus.COMPATIBLE.value,
        causal_status=CausalStatus.RESOLVED.value
    )
    prev_item_neg = ScaffoldScenarioCompatibilityItem(
        scenario_id="SCN-07-NEG",
        compatibility=ScaffoldCompatibilityStatus.INCOMPATIBLE.value,
        causal_status=CausalStatus.VIOLATED.value
    )
    prev_matrix = ScaffoldScenarioMatrix(
        items=[prev_item_pos, prev_item_neg],
        is_fully_compatible=False,
        compatible_count=1,
        incompatible_count=1
    )

    repaired_code = """
from fastapi import FastAPI, HTTPException
app = FastAPI()
items = {1: "val"}

@app.delete('/items/{id}', status_code=204)
def delete_item(id: int):
    if id not in items:
        raise HTTPException(status_code=404)
    del items[id]
"""
    new_matrix = evaluate_scaffold_scenario_compatibility(
        [sc_pos, sc_neg],
        {"main.py": repaired_code},
        previous_matrix=prev_matrix
    )
    assert new_matrix.is_fully_compatible is True
    assert new_matrix.regression_count == 0
    assert all(not it.is_regression for it in new_matrix.items)


# ==============================================================================
# Gate 08: Regression detection (COMPATIBLE -> INCOMPATIBLE flagged as CRITICAL)
# ==============================================================================
def test_gate_08_regression_detection():
    sc_pos = CanonicalScenario(
        scenario_id="SCN-08-POS",
        scenario_kind=ScenarioKind.POSITIVE.value,
        stimulus="DELETE /items/1",
        expected_outcome={"http_method": "DELETE", "route": "/items/1", "status_code": 204}
    )
    prev_matrix = ScaffoldScenarioMatrix(
        items=[ScaffoldScenarioCompatibilityItem(
            scenario_id="SCN-08-POS",
            compatibility=ScaffoldCompatibilityStatus.COMPATIBLE.value,
            causal_status=CausalStatus.RESOLVED.value
        )],
        is_fully_compatible=True,
        compatible_count=1
    )

    broken_code = """
from fastapi import FastAPI
app = FastAPI()

@app.delete('/different_route')
def delete_different():
    return None
"""
    new_matrix = evaluate_scaffold_scenario_compatibility(
        [sc_pos],
        {"main.py": broken_code},
        previous_matrix=prev_matrix
    )
    assert new_matrix.is_fully_compatible is False
    assert new_matrix.regression_count == 1
    assert new_matrix.items[0].is_regression is True
    assert "[CRITICAL REGRESSION]" in new_matrix.items[0].evidence


# ==============================================================================
# Gate 09: Scaffold semantic extraction Python (AST)
# ==============================================================================
def test_gate_09_scaffold_semantic_extraction_python():
    extractor = PythonScaffoldExtractor()
    code = """
from fastapi import FastAPI, HTTPException
app = FastAPI()
store = {}

@app.delete('/resource/{res_id}', status_code=204)
def remove_resource(res_id: int):
    if res_id not in store:
        raise HTTPException(status_code=404, detail='Not found')
    del store[res_id]
    return None
"""
    facts = extractor.extract_facts("main.py", code)
    assert len(facts) >= 1
    f = [x for x in facts if x.name == "remove_resource"][0]
    assert f.route == "/resource/{res_id}"
    assert f.http_method == "DELETE"
    assert f.positional_params_count == 1
    assert f.param_names == ["res_id"]
    assert len(f.error_paths) == 1
    assert f.error_paths[0]["status_code"] == 404
    assert len(f.conditional_branches) == 1
    assert "res_id not in store" in f.conditional_branches[0]
    assert f.is_stub is False
    assert f.has_unconditional_return is False


# ==============================================================================
# Gate 10: Scaffold semantic extraction Dart (token/regex)
# ==============================================================================
def test_gate_10_scaffold_semantic_extraction_dart():
    extractor = DartScaffoldExtractor()
    code = """
class MetricData {
  final String title;
  final String value;
  final String? unit;

  MetricData({required this.title, required this.value, this.unit});
}

class PlainModel {
  final int id;
  PlainModel(this.id);
}
"""
    facts = extractor.extract_facts("model.dart", code)
    assert len(facts) == 2
    f_named = [x for x in facts if x.name == "MetricData"][0]
    assert f_named.has_named_params is True
    assert "title" in f_named.named_param_names
    assert "value" in f_named.named_param_names

    f_pos = [x for x in facts if x.name == "PlainModel"][0]
    assert f_pos.has_named_params is False
    assert f_pos.positional_params_count == 1


# ==============================================================================
# Gate 11: Constructor call shape evidence (positional vs keyword-only)
# ==============================================================================
def test_gate_11_constructor_call_shape_evidence():
    sc_pos = CanonicalScenario(
        scenario_id="SCN-11-POS-CALL",
        stimulus="Matrix([[1.0, 2.0]])",
        expected_outcome={"callable": "Matrix"}
    )
    pydantic_code = """
from pydantic import BaseModel

class Matrix(BaseModel):
    data: list[list[float]]
"""
    matrix_pydantic = evaluate_scaffold_scenario_compatibility([sc_pos], {"main.py": pydantic_code})
    assert matrix_pydantic.is_fully_compatible is False
    assert matrix_pydantic.items[0].compatibility == ScaffoldCompatibilityStatus.INCOMPATIBLE.value
    assert "positional arguments" in matrix_pydantic.items[0].evidence

    code_with_init = """
from pydantic import BaseModel

class Matrix(BaseModel):
    data: list[list[float]]
    def __init__(self, data: list[list[float]]):
        super().__init__(data=data)
"""
    matrix_init = evaluate_scaffold_scenario_compatibility([sc_pos], {"main.py": code_with_init})
    assert matrix_init.is_fully_compatible is True

    sc_named = CanonicalScenario(
        scenario_id="SCN-11-NAMED-CALL",
        stimulus="MetricData(title: 'A', value: '1')",
        expected_outcome={"widget": "MetricData"}
    )
    dart_pos_ctor = "class MetricData { MetricData(this.title, this.value); final String title; final String value; }"
    matrix_dart_pos = evaluate_scaffold_scenario_compatibility([sc_named], {"card.dart": dart_pos_ctor})
    assert matrix_dart_pos.is_fully_compatible is False
    assert matrix_dart_pos.items[0].compatibility == ScaffoldCompatibilityStatus.INCOMPATIBLE.value
    assert "named arguments" in matrix_dart_pos.items[0].evidence

    dart_named_ctor = "class MetricData { MetricData({required this.title, required this.value}); final String title; final String value; }"
    matrix_dart_named = evaluate_scaffold_scenario_compatibility([sc_named], {"card.dart": dart_named_ctor})
    assert matrix_dart_named.is_fully_compatible is True


# ==============================================================================
# Gate 12: Public interface evidence (route and endpoint identity matching)
# ==============================================================================
def test_gate_12_public_interface_evidence():
    assert _route_matches("/products/1", "/products/{id}") is True
    assert _route_matches("/products/999", "/products/{product_id}") is True
    assert _route_matches("/products", "/products") is True
    assert _route_matches("/products/1/reviews", "/products/{id}") is False
    assert _route_matches("/users", "/orders") is False


# ==============================================================================
# Gate 13: Control flow observable path evidence (reachable vs unconditional vs opaque)
# ==============================================================================
def test_gate_13_control_flow_observable_path_evidence():
    sc_neg = CanonicalScenario(
        scenario_id="SCN-13-NEG",
        scenario_kind=ScenarioKind.NEGATIVE.value,
        stimulus="DELETE /items/1",
        expected_outcome={"status_code": 404}
    )

    scaffold_reachable = {"main.py": "@app.delete('/items/{id}')\ndef del_item(id: int):\n    if id not in store: raise HTTPException(404)"}
    m_reach = evaluate_scaffold_scenario_compatibility([sc_neg], scaffold_reachable)
    assert m_reach.items[0].compatibility == ScaffoldCompatibilityStatus.COMPATIBLE.value

    scaffold_uncond = {"main.py": "@app.delete('/items/{id}')\ndef del_item(id: int):\n    return 204"}
    m_uncond = evaluate_scaffold_scenario_compatibility([sc_neg], scaffold_uncond)
    assert m_uncond.items[0].compatibility == ScaffoldCompatibilityStatus.INCOMPATIBLE.value

    scaffold_opaque = {"main.py": "@app.delete('/items/{id}')\ndef del_item(id: int):\n    return db_helper.delete(id)"}
    m_opaque = evaluate_scaffold_scenario_compatibility([sc_neg], scaffold_opaque)
    assert m_opaque.items[0].compatibility == ScaffoldCompatibilityStatus.UNDETERMINED.value


# ==============================================================================
# Gate 14: Current vs historical isolation
# ==============================================================================
def test_gate_14_current_vs_historical_isolation():
    sc = CanonicalScenario(
        scenario_id="SCN-14",
        scenario_kind=ScenarioKind.POSITIVE.value,
        stimulus="GET /ping",
        expected_outcome={"status_code": 200, "route": "/ping"}
    )
    code = "@app.get('/ping')\ndef ping(): return {'status': 'ok'}"
    m1 = evaluate_scaffold_scenario_compatibility([sc], {"main.py": code})
    m2 = evaluate_scaffold_scenario_compatibility([sc], {"main.py": code})
    assert m1.is_fully_compatible == m2.is_fully_compatible == True
    assert m1.items[0].compatibility == m2.items[0].compatibility == "COMPATIBLE"


# ==============================================================================
# Gate 15: Locked invariant preservation
# ==============================================================================
def test_gate_15_locked_invariant_preservation():
    state = {
        "task": "Test task",
        "locked_invariants": {
            "INV-01": {"status": "PROVEN", "description": "GET /items returns 200"}
        },
        "contract_status": "ALIGNED"
    }
    ctx, telem = build_architect_decision_context(state)
    assert "INV-01" in ctx
    assert "[PROVEN] INV-01: GET /items returns 200 — mutation: FORBIDDEN" in ctx
    assert telem["locked_invariants"] == 1


# ==============================================================================
# Gate 16: Context delivery preserves scenario evidence
# ==============================================================================
def test_gate_16_context_delivery_preserves_scenario_evidence():
    item = ScaffoldScenarioCompatibilityItem(
        scenario_id="SCN-TEST-16",
        compatibility=ScaffoldCompatibilityStatus.INCOMPATIBLE.value,
        source_reference="test_main.py:10",
        observed_scaffold_facts={"route": "/bad"},
        expected_behavior={"status_code": 404},
        evidence="Scaffold does not define 404 error branch"
    )
    matrix = ScaffoldScenarioMatrix(items=[item], incompatible_count=1)
    formatted = format_scaffold_compatibility_for_architect(matrix)
    assert "[BEHAVIORAL COMPATIBILITY EVIDENCE — SCAFFOLD vs ACCEPTANCE SCENARIOS]" in formatted
    assert "SCN-TEST-16" in formatted
    assert "INCOMPATIBLE" in formatted
    assert "Scaffold does not define 404 error branch" in formatted


# ==============================================================================
# Gate 17: Truncation cannot silently remove evidence
# ==============================================================================
def test_gate_17_truncation_cannot_silently_remove_evidence():
    state = {
        "task": "Build inventory",
        "contract_validation_errors": [
            "SCENARIO_SCAFFOLD_INCOMPATIBILITY: Scenario 'SCN-1' is INCOMPATIBLE."
        ]
    }
    ctx, telem = build_architect_decision_context(state, pkg=object(), max_chars=4000)
    assert "[BEHAVIORAL COMPATIBILITY EVIDENCE" in ctx
    assert "SCENARIO_SCAFFOLD_INCOMPATIBILITY" in ctx


# ==============================================================================
# Gate 18: Oracle immutability (SHA-256 verified)
# ==============================================================================
def test_gate_18_oracle_immutability():
    expected_hashes = {
        "dokumentasi-pengembangan/experiments/frozen_oracle/fastapi_t1/test_main.py": "a1db9bb1f6eaf47d5cf56e102c4a0f6e1f49d757e9faa1485b36f2972a152d63",
        "dokumentasi-pengembangan/experiments/frozen_oracle/cli_t1/test_main.py": "0bd5b598afa7ae4c9cdf0e269d13136b51d35a4e0b1ac6548f0a2cf8a8eba124",
        "dokumentasi-pengembangan/experiments/frozen_oracle/flutter_t1/card_metric_test.dart": "4589e15cfb8f37ba70642e70623ca143bceee1a44175aefd072f441d9e8a9528",
    }
    for file_path, expected_sha in expected_hashes.items():
        p = Path(file_path)
        assert p.exists(), f"Oracle file missing: {file_path}"
        actual_sha = hashlib.sha256(p.read_bytes()).hexdigest().lower()
        assert actual_sha == expected_sha.lower(), f"Oracle {file_path} mutated! Expected {expected_sha}, got {actual_sha}"


# ==============================================================================
# Gate 19: Sterile executor unchanged (diff clean)
# ==============================================================================
def test_gate_19_sterile_executor_unchanged():
    res = subprocess.run(
        ["git", "diff", "HEAD", "--", "backend/sterile_executor.py"],
        capture_output=True,
        text=True
    )
    assert res.returncode == 0
    assert res.stdout.strip() == "", f"sterile_executor.py has unexpected modifications: {res.stdout}"


# ==============================================================================
# Gate 20: No task-specific solver static audit (AST search)
# ==============================================================================
def test_gate_20_no_task_specific_solver_static_audit():
    canonical_file = Path("backend/canonical_scenario.py")
    tree = ast.parse(canonical_file.read_text(encoding="utf-8"))

    forbidden_literals = {
        "fastapi_t1", "cli_t1", "flutter_t1", "Matrix", "MetricData", "delete_product"
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            val = node.value.strip()
            for forb in forbidden_literals:
                assert forb != val, f"Forbidden task-specific solver literal found in canonical_scenario.py: '{forb}'"


# ==============================================================================
# Gate 21: Cross-language canonical semantic normalization (Python & Dart)
# ==============================================================================
def test_gate_21_cross_language_semantic_normalization():
    # User Correction 3:
    # Python evidence -> canonical semantics
    # Dart evidence -> canonical semantics
    # Resulting compatibility item must have identical canonical semantic status & schema
    sc_pos = CanonicalScenario(
        scenario_id="SCN-CROSS-POS",
        stimulus="Service(host: 'localhost', port: 8080)",
        expected_outcome={"callable": "Service"}
    )
    sc_neg = CanonicalScenario(
        scenario_id="SCN-CROSS-NEG",
        scenario_kind=ScenarioKind.NEGATIVE.value,
        stimulus="Service(host: 'invalid')",
        expected_outcome={"status_code": 400}
    )

    py_scaffold = """
class Service:
    def __init__(self, host: str = '', port: int = 0):
        self.host = host
        self.port = port
        if host == 'invalid':
            raise ValueError('Invalid host')
"""
    dart_scaffold = """
class Service {
  final String host;
  final int port;
  Service({required this.host, required this.port}) {
    if (host == 'invalid') {
      throw ArgumentError('Invalid host');
    }
  }
}
"""
    m_py = evaluate_scaffold_scenario_compatibility([sc_pos, sc_neg], {"service.py": py_scaffold})
    m_dart = evaluate_scaffold_scenario_compatibility([sc_pos, sc_neg], {"service.dart": dart_scaffold})

    # Canonical semantic result MUST BE IDENTICAL
    assert m_py.is_fully_compatible == m_dart.is_fully_compatible == True
    assert m_py.items[0].compatibility == m_dart.items[0].compatibility == ScaffoldCompatibilityStatus.COMPATIBLE.value
    assert m_py.items[0].authority == m_dart.items[0].authority == "FROZEN_ORACLE"
    assert m_py.items[0].causal_status == m_dart.items[0].causal_status == CausalStatus.RESOLVED.value

    assert m_py.items[1].compatibility == m_dart.items[1].compatibility == ScaffoldCompatibilityStatus.COMPATIBLE.value
    assert m_py.items[1].causal_status == m_dart.items[1].causal_status == CausalStatus.RESOLVED.value


# ==============================================================================
# Gate 22: Compatible does not require specific implementation (HOW authority)
# ==============================================================================
def test_gate_22_compatible_does_not_require_specific_implementation():
    sc_neg = CanonicalScenario(
        scenario_id="SCN-22-NEG",
        scenario_kind=ScenarioKind.NEGATIVE.value,
        stimulus="DELETE /items/999",
        expected_outcome={"http_method": "DELETE", "route": "/items/999", "status_code": 404}
    )

    code_dict = """
@app.delete('/items/{id}', status_code=204)
def delete_item(id: int):
    if id not in items_dict:
        raise HTTPException(404)
    del items_dict[id]
"""
    code_list = """
@app.delete('/items/{id}', status_code=204)
def delete_item(id: int):
    match = [x for x in items_list if x.id == id]
    if not match:
        raise HTTPException(404)
    items_list.remove(match[0])
"""
    code_repo = """
@app.delete('/items/{id}', status_code=204)
def delete_item(id: int):
    if not repo.exists(id):
        raise HTTPException(404)
    repo.remove(id)
"""
    m_dict = evaluate_scaffold_scenario_compatibility([sc_neg], {"main.py": code_dict})
    m_list = evaluate_scaffold_scenario_compatibility([sc_neg], {"main.py": code_list})
    m_repo = evaluate_scaffold_scenario_compatibility([sc_neg], {"main.py": code_repo})

    assert m_dict.is_fully_compatible is True
    assert m_list.is_fully_compatible is True
    assert m_repo.is_fully_compatible is True


# ==============================================================================
# Gate 23: Undetermined is never promoted to pass (fail-closed)
# ==============================================================================
def test_gate_23_undetermined_is_never_promoted_to_pass():
    item_undet = ScaffoldScenarioCompatibilityItem(
        scenario_id="SCN-23",
        compatibility=ScaffoldCompatibilityStatus.UNDETERMINED.value,
        causal_status=CausalStatus.UNRESOLVED.value
    )
    matrix = ScaffoldScenarioMatrix(
        items=[item_undet],
        is_fully_compatible=False,
        undetermined_count=1
    )
    assert matrix.is_fully_compatible is False


# ==============================================================================
# Gate 24: Incompatible scaffold cannot freeze contract (status REJECTED)
# ==============================================================================
def test_gate_24_incompatible_scaffold_cannot_freeze_contract():
    draft = create_draft_contract(raw_intent="Manage Products API", target_language="python", domain="REST_API")
    contract_data = complete_aligned_contract(
        draft_dict=draft,
        data_models=[
            {
                "model_name": "Product",
                "target_file": "main.py",
                "fields": [
                    {"field_name": "id", "field_type": "int", "is_required": True},
                    {"field_name": "name", "field_type": "str", "is_required": True},
                    {"field_name": "price", "field_type": "float", "is_required": True}
                ]
            }
        ],
        interface_contracts=[
            {
                "interface_id": "IFC-01",
                "interface_type": "HTTP_ENDPOINT",
                "identifier": "/products",
                "route": "/products",
                "http_method": "GET",
                "target_file": "main.py"
            },
            {
                "interface_id": "IFC-02",
                "interface_type": "HTTP_ENDPOINT",
                "identifier": "/products",
                "route": "/products",
                "http_method": "POST",
                "target_file": "main.py"
            },
            {
                "interface_id": "IFC-03",
                "interface_type": "HTTP_ENDPOINT",
                "identifier": "/products/{id}",
                "route": "/products/{id}",
                "http_method": "GET",
                "target_file": "main.py"
            },
            {
                "interface_id": "IFC-04",
                "interface_type": "HTTP_ENDPOINT",
                "identifier": "/products/{id}",
                "route": "/products/{id}",
                "http_method": "PUT",
                "target_file": "main.py"
            },
            {
                "interface_id": "IFC-05",
                "interface_type": "HTTP_ENDPOINT",
                "identifier": "/products/{id}",
                "route": "/products/{id}",
                "http_method": "DELETE",
                "target_file": "main.py"
            }
        ],
        testable_assertions=[]
    )

    # Blueprint with bad scaffold (unconditional 204 return on delete_product)
    blueprint_bad = {
        "files": {
            "main.py": """
from fastapi import FastAPI
app = FastAPI()
products = []

@app.get('/products')
def get_products(): return []

@app.post('/products')
def create_product(product: dict): return product

@app.get('/products/{id}')
def get_product(id: int): return None

@app.put('/products/{id}')
def update_product(id: int, product: dict): return product

@app.delete('/products/{id}', status_code=204)
def delete_product(id: int):
    global products
    products = [p for p in products if p.id != id]
    return None
"""
        }
    }

    oracle_path = str(ORACLE_FASTAPI_DIR)
    success, sealed, errors, warnings = seal_and_freeze_contract(
        contract_data,
        frozen_oracle_path=oracle_path,
        blueprint=blueprint_bad
    )

    # Must be REJECTED! Contract cannot freeze!
    assert success is False
    assert sealed["status"] == ContractStatus.REJECTED.value
    assert any("SCENARIO_SCAFFOLD_INCOMPATIBILITY" in e for e in errors)
