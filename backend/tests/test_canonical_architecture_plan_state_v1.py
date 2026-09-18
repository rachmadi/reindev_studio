# -*- coding: utf-8 -*-
"""
Test Suite: Canonical Architecture Plan State v1
Pipeline Repair: Canonical Architecture Plan State v1
Tests A through O verifying state-contract repair and single source of truth for architecture_plan.
"""

import json
import inspect
import pytest
from typing import Dict, Any, List

from backend.blueprint_schema import (
    ArchitecturalBlueprint,
    BlueprintFileModule,
    BlueprintInterfaceContract,
    BlueprintDataModel,
    serialize_blueprint_to_canonical_json,
    validate_canonical_architecture_plan_state,
    parse_blueprint_json
)
from backend.architect_validator import validate_architect_blueprint
from backend.architect_staged import (
    StageAObligationMapping,
    FrozenStageAMappings,
    StageBAssemblyOutput,
    convert_stage_b_to_semantic_plan
)
from backend.semantic_serializer import (
    SemanticArchitecturalDecision,
    serialize_semantic_decision_to_blueprint
)
from backend.canonical_obligation import CanonicalObligation, CoverageMatrix, check_obligation_coverage


def _build_generic_synthetic_blueprint() -> ArchitecturalBlueprint:
    return ArchitecturalBlueprint(
        schema_version="1.0.0",
        task_id="synthetic_task",
        target_language="python",
        authoritative_target_file="main.py",
        file_tree=["main.py"],
        architecture_summary="Generic synthetic architecture summary",
        files={
            "main.py": BlueprintFileModule(
                file_path="main.py",
                module_role="Authoritative Module",
                imports=["import sys"],
                code_scaffold="def execute_operation(x: int) -> int:\n    return x * 2\n"
            )
        },
        interface_contracts=[
            BlueprintInterfaceContract(
                identifier="execute_operation",
                target_file="main.py",
                interface_type="FUNCTION"
            )
        ],
        data_models=[]
    )


# ============================================================================
# Test A: Stage A + Stage B -> one canonical Blueprint
# ============================================================================
def test_a_stage_a_plus_stage_b_to_one_canonical_blueprint():
    # Stage A
    mapping = StageAObligationMapping(
        obligation_id="OBL-01",
        semantic_element="calculate_metric",
        element_kind="FUNCTION",
        semantic_identity="calculate_metric",
        semantic_target_artifact="main.py",
        description="Generic obligation rationale"
    )
    frozen_a = FrozenStageAMappings.freeze([mapping])

    # Stage B
    decision = SemanticArchitecturalDecision(
        obligation_id="OBL-01",
        target_structure="INTERFACE_CONTRACT",
        identifier="calculate_metric",
        target_file="main.py"
    )
    assembly_b = StageBAssemblyOutput(
        target_file="main.py",
        files={"main.py": "def calculate_metric(a: int) -> int:\n    return a + 1\n"},
        scaffold_code="def calculate_metric(a: int) -> int:\n    return a + 1\n",
        semantic_decisions=[decision]
    )

    plan, conv_errs = convert_stage_b_to_semantic_plan(
        frozen_stage_a=frozen_a,
        assembly=assembly_b,
        task_id="generic_synth",
        target_language="python"
    )
    assert not conv_errs, f"Conversion errors: {conv_errs}"
    assert plan is not None

    bp, ser_errs = serialize_semantic_decision_to_blueprint(plan)
    assert not ser_errs, f"Serialization errors: {ser_errs}"
    assert isinstance(bp, ArchitecturalBlueprint)

    json_str = serialize_blueprint_to_canonical_json(bp)
    assert isinstance(json_str, str)
    assert json_str.startswith("{") and json_str.strip().endswith("}")


# ============================================================================
# Test B: architecture_plan contains exactly one JSON object
# ============================================================================
def test_b_architecture_plan_contains_exactly_one_json_object():
    bp = _build_generic_synthetic_blueprint()
    arch_plan = serialize_blueprint_to_canonical_json(bp)

    decoder = json.JSONDecoder()
    obj, end_idx = decoder.raw_decode(arch_plan.strip())
    assert isinstance(obj, dict)
    assert arch_plan.strip()[end_idx:].strip() == "", "Extra trailing content found"


# ============================================================================
# Test C: multiline Python scaffold survives unchanged
# ============================================================================
def test_c_multiline_python_scaffold_survives_unchanged():
    py_scaffold = (
        "import os\n"
        "import sys\n\n"
        "def run_service(name: str, count: int = 0) -> str:\n"
        "    \"\"\"Multiline docstring\n"
        "    Line 2 of docstring.\n"
        "    \"\"\"\n"
        "    if count <= 0:\n"
        "        raise ValueError('Negative count')\n"
        "    return f'Service {name}: {count}'\n"
    )
    bp = ArchitecturalBlueprint(
        schema_version="1.0.0",
        task_id="py_test",
        target_language="python",
        authoritative_target_file="service.py",
        file_tree=["service.py"],
        architecture_summary="Python test summary",
        files={
            "service.py": BlueprintFileModule(
                file_path="service.py",
                code_scaffold=py_scaffold
            )
        },
        interface_contracts=[
            BlueprintInterfaceContract(
                identifier="run_service",
                target_file="service.py"
            )
        ],
        data_models=[]
    )
    serialized = serialize_blueprint_to_canonical_json(bp)
    decoded = json.loads(serialized)
    assert decoded["files"]["service.py"]["code_scaffold"] == py_scaffold


# ============================================================================
# Test D: multiline Dart scaffold survives unchanged
# ============================================================================
def test_d_multiline_dart_scaffold_survives_unchanged():
    dart_scaffold = (
        "import 'package:flutter/material.dart';\n\n"
        "class WidgetComponent extends StatelessWidget {\n"
        "  final String label;\n"
        "  const WidgetComponent({Key? key, required this.label}) : super(key: key);\n\n"
        "  @override\n"
        "  Widget build(BuildContext context) {\n"
        "    return Container(\n"
        "      child: Text(label),\n"
        "    );\n"
        "  }\n"
        "}\n"
    )
    bp = ArchitecturalBlueprint(
        schema_version="1.0.0",
        task_id="dart_test",
        target_language="dart",
        authoritative_target_file="lib/widget.dart",
        file_tree=["lib/widget.dart"],
        architecture_summary="Dart test summary",
        files={
            "lib/widget.dart": BlueprintFileModule(
                file_path="lib/widget.dart",
                code_scaffold=dart_scaffold
            )
        },
        interface_contracts=[
            BlueprintInterfaceContract(
                identifier="WidgetComponent",
                target_file="lib/widget.dart",
                interface_type="WIDGET"
            )
        ],
        data_models=[]
    )
    serialized = serialize_blueprint_to_canonical_json(bp)
    decoded = json.loads(serialized)
    assert decoded["files"]["lib/widget.dart"]["code_scaffold"] == dart_scaffold


# ============================================================================
# Test E: Stage A raw output is not embedded in architecture_plan
# ============================================================================
def test_e_stage_a_raw_output_is_not_embedded_in_architecture_plan():
    bp = _build_generic_synthetic_blueprint()
    arch_plan = serialize_blueprint_to_canonical_json(bp)

    assert "=== STAGE A OUTPUT ===" not in arch_plan
    assert "=== STAGE A: OBLIGATION MAPPING ===" not in arch_plan
    assert "=== STAGE A REPAIR OUTPUT ===" not in arch_plan
    assert "=== STAGE A" not in arch_plan


# ============================================================================
# Test F: Stage B raw output is not embedded in architecture_plan
# ============================================================================
def test_f_stage_b_raw_output_is_not_embedded_in_architecture_plan():
    bp = _build_generic_synthetic_blueprint()
    arch_plan = serialize_blueprint_to_canonical_json(bp)

    assert "=== STAGE B OUTPUT ===" not in arch_plan
    assert "=== STAGE B: ARCHITECTURAL ASSEMBLY ===" not in arch_plan
    assert "=== STAGE B REPAIR OUTPUT ===" not in arch_plan
    assert "=== STAGE B" not in arch_plan


# ============================================================================
# Test G: existing canonical validator accepts architecture_plan
# ============================================================================
def test_g_existing_canonical_validator_accepts_architecture_plan():
    bp = _build_generic_synthetic_blueprint()
    arch_plan = serialize_blueprint_to_canonical_json(bp)

    ok, errors = validate_architect_blueprint(arch_plan, target_language="python")
    assert ok is True, f"Expected validator to accept canonical plan, got errors: {errors}"
    assert len(errors) == 0


# ============================================================================
# Test H: semantic equivalence between structured Blueprint and architecture_plan
# ============================================================================
def test_h_semantic_equivalence_between_structured_blueprint_and_architecture_plan():
    bp = _build_generic_synthetic_blueprint()
    arch_plan = serialize_blueprint_to_canonical_json(bp)

    ok, errors = validate_canonical_architecture_plan_state(
        architecture_plan=arch_plan,
        canonical_blueprint=bp
    )
    assert ok is True, f"Expected semantic equivalence, got: {errors}"
    assert len(errors) == 0


# ============================================================================
# Test I: malformed Blueprint is rejected
# ============================================================================
def test_i_malformed_blueprint_is_rejected():
    malformed_plan = '{"schema_version": "1.0.0", "missing_files": true}'
    ok, errors = validate_canonical_architecture_plan_state(malformed_plan)
    assert ok is False
    assert any("STATE_REPRESENTATION_FAILURE" in err for err in errors)


# ============================================================================
# Test J: concatenated JSON is rejected
# ============================================================================
def test_j_concatenated_json_is_rejected():
    bp = _build_generic_synthetic_blueprint()
    single_json = serialize_blueprint_to_canonical_json(bp)
    concatenated_json = single_json + "\n" + single_json

    ok, errors = validate_canonical_architecture_plan_state(concatenated_json)
    assert ok is False
    assert any("STATE_REPRESENTATION_FAILURE" in err for err in errors)
    assert any("concatenated" in err.lower() or "extra trailing" in err.lower() for err in errors)


# ============================================================================
# Test K: obligation coverage is preserved
# ============================================================================
def test_k_obligation_coverage_is_preserved():
    bp = _build_generic_synthetic_blueprint()
    arch_plan = serialize_blueprint_to_canonical_json(bp)

    decoded_dict = json.loads(arch_plan)
    contract_ifaces = [
        {"identifier": ifc["identifier"]}
        for ifc in decoded_dict.get("interface_contracts", [])
    ]

    obligations = [
        CanonicalObligation(
            obligation_id="OBL-01",
            public_identity="execute_operation",
            source_reference="test.py:5"
        )
    ]

    cov = check_obligation_coverage(
        obligations=obligations,
        contract={"interface_contracts": contract_ifaces, "data_models": []},
        blueprint=bp
    )
    assert cov.is_fully_covered is True
    assert cov.covered_count == 1
    assert cov.missing_count == 0


# ============================================================================
# Test L: frozen contract semantics are preserved
# ============================================================================
def test_l_frozen_contract_semantics_are_preserved():
    bp = _build_generic_synthetic_blueprint()
    arch_plan = serialize_blueprint_to_canonical_json(bp)

    frozen_contract = {
        "status": "FROZEN",
        "interface_contracts": [
            {"identifier": "execute_operation"}
        ]
    }

    # Should PASS when interfaces match
    ok, errors = validate_canonical_architecture_plan_state(
        architecture_plan=arch_plan,
        canonical_blueprint=bp,
        contract=frozen_contract
    )
    assert ok is True

    # Should FAIL with STATE_REPRESENTATION_FAILURE when frozen contract interface is missing
    frozen_contract_mismatch = {
        "status": "FROZEN",
        "interface_contracts": [
            {"identifier": "execute_operation"},
            {"identifier": "missing_interface"}
        ]
    }
    ok_bad, errors_bad = validate_canonical_architecture_plan_state(
        architecture_plan=arch_plan,
        canonical_blueprint=bp,
        contract=frozen_contract_mismatch
    )
    assert ok_bad is False
    assert any("STATE_REPRESENTATION_FAILURE" in e for e in errors_bad)
    assert any("missing_interface" in e for e in errors_bad)


# ============================================================================
# Test M: raw diagnostic history remains separate
# ============================================================================
def test_m_raw_diagnostic_history_remains_separate():
    from backend.agents.architect import architect_agent
    from langchain_core.messages import AIMessage

    class MockLLM:
        def invoke(self, messages):
            text = str(messages[0].content) if hasattr(messages[0], 'content') else ''
            # If Stage A prompt
            if 'STAGE A' in text or 'Obligation Mapping' in text:
                return AIMessage(content='=== STAGE A: OBLIGATION MAPPING ===\n{\n  "obligation_mappings": [\n    {\n      "obligation_id": "REQ-01",\n      "semantic_element": "calculate",\n      "element_kind": "FUNCTION",\n      "semantic_identity": "calculate",\n      "semantic_target_artifact": "main.py",\n      "semantic_parameters": [],\n      "semantic_return": {"type": "int"}\n    }\n  ]\n}\n=== END STAGE A ===')
            # If Stage B prompt
            return AIMessage(content='=== STAGE B: ARCHITECTURAL ASSEMBLY ===\n{\n  "target_file": "main.py",\n  "files": {\n    "main.py": {\n      "scaffold_code": "def calculate():\\n    return 42\\n"\n    }\n  },\n  "scaffold_code": "def calculate():\\n    return 42\\n",\n  "semantic_decisions": [\n    {\n      "obligation_id": "REQ-01",\n      "target_structure": "INTERFACE_CONTRACT",\n      "identifier": "calculate",\n      "target_file": "main.py",\n      "parameters": [],\n      "return_semantics": {"type": "int"}\n    }\n  ]\n}\n=== END STAGE B ===')

    mock_state = {
        "task": "Build a calculator",
        "target_language": "python",
        "specifications": "calculate function",
        "run_id": "test_diag",
        "logs": []
    }

    res = architect_agent(mock_state, llm=MockLLM())
    # architecture_plan must NOT contain raw delimiters
    assert "=== STAGE A" not in res["architecture_plan"]
    assert "=== STAGE B" not in res["architecture_plan"]

    # Provenance must contain the raw outputs separately
    prov = res["contract"].get("provenance", {})
    assert "raw_stage_a_output" in prov
    assert "raw_stage_b_output" in prov
    assert "=== STAGE A: OBLIGATION MAPPING ===" in prov["raw_stage_a_output"]
    assert "=== STAGE B: ARCHITECTURAL ASSEMBLY ===" in prov["raw_stage_b_output"]


# ============================================================================
# Test N: repair history remains separate
# ============================================================================
def test_n_repair_history_remains_separate():
    bp = _build_generic_synthetic_blueprint()
    arch_plan = serialize_blueprint_to_canonical_json(bp)

    # architecture_plan must be pure JSON
    parsed = json.loads(arch_plan)
    assert "repair_history" not in parsed
    assert "validation_history" not in parsed


# ============================================================================
# Test O: no task-specific branching in implementation
# ============================================================================
def test_o_no_task_specific_branching():
    from backend import blueprint_schema

    source = inspect.getsource(blueprint_schema.serialize_blueprint_to_canonical_json)
    source += inspect.getsource(blueprint_schema.validate_canonical_architecture_plan_state)

    for task_name in ["fastapi_t1", "cli_t1", "flutter_t1"]:
        assert task_name not in source, f"Found task name '{task_name}' in blueprint_schema functions"
