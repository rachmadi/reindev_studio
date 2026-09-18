# -*- coding: utf-8 -*-
"""
Test Suite: Canonical Architecture Plan Wrapper Validation v1
Tests A through L covering outer document wrapper detection vs internal markdown fences/backticks.
Generic synthetic tests with zero task-specific tokens.
"""

import json
import pytest
from typing import Dict, Any

from backend.blueprint_schema import (
    ArchitecturalBlueprint,
    BlueprintFileModule,
    BlueprintInterfaceContract,
    BlueprintDataModel,
    serialize_blueprint_to_canonical_json,
    validate_canonical_architecture_plan_state,
)


def _build_generic_blueprint(scaffold_content: str = "def execute_task() -> bool:\n    return True\n") -> ArchitecturalBlueprint:
    return ArchitecturalBlueprint(
        schema_version="1.0.0",
        task_id="synth_task_01",
        target_language="generic_lang",
        authoritative_target_file="module.ext",
        file_tree=["module.ext"],
        architecture_summary="Generic architecture plan for wrapper validation",
        files={
            "module.ext": BlueprintFileModule(
                file_path="module.ext",
                module_role="Main Entrypoint",
                imports=["import core"],
                code_scaffold=scaffold_content
            )
        },
        interface_contracts=[
            BlueprintInterfaceContract(
                identifier="execute_task",
                target_file="module.ext",
                interface_type="FUNCTION"
            )
        ],
        data_models=[]
    )


# ============================================================================
# Test A: Canonical JSON without fences -> PASS
# ============================================================================
def test_a_canonical_json_without_fences_passes():
    bp = _build_generic_blueprint("def compute_value(x: int) -> int:\n    return x + 10\n")
    serialized = serialize_blueprint_to_canonical_json(bp)
    
    ok, errors = validate_canonical_architecture_plan_state(serialized, canonical_blueprint=bp)
    assert ok is True, f"Expected PASS for canonical JSON without fences, got: {errors}"
    assert len(errors) == 0


# ============================================================================
# Test B: Outer ```json wrapper -> FAIL
# ============================================================================
def test_b_outer_triple_backtick_json_wrapper_fails():
    bp = _build_generic_blueprint()
    serialized = serialize_blueprint_to_canonical_json(bp)
    wrapped = f"```json\n{serialized}\n```"
    
    ok, errors = validate_canonical_architecture_plan_state(wrapped)
    assert ok is False
    assert any("STATE_REPRESENTATION_FAILURE" in e for e in errors)
    assert any("```" in e for e in errors)


# ============================================================================
# Test C: Outer ``` wrapper without json -> FAIL
# ============================================================================
def test_c_outer_triple_backtick_wrapper_fails():
    bp = _build_generic_blueprint()
    serialized = serialize_blueprint_to_canonical_json(bp)
    wrapped = f"```\n{serialized}\n```"
    
    ok, errors = validate_canonical_architecture_plan_state(wrapped)
    assert ok is False
    assert any("STATE_REPRESENTATION_FAILURE" in e for e in errors)
    assert any("```" in e for e in errors)


# ============================================================================
# Test D: code_scaffold containing ``` -> PASS
# ============================================================================
def test_d_code_scaffold_containing_triple_backticks_passes():
    scaffold_with_fences = (
        "// Module documentation\n"
        "/* Example usage:\n"
        "```\n"
        "execute_task()\n"
        "```\n"
        "*/\n"
        "def execute_task() -> bool:\n"
        "    return True\n"
    )
    bp = _build_generic_blueprint(scaffold_with_fences)
    serialized = serialize_blueprint_to_canonical_json(bp)
    
    ok, errors = validate_canonical_architecture_plan_state(serialized, canonical_blueprint=bp)
    assert ok is True, f"Expected PASS when backticks are inside code_scaffold, got: {errors}"
    assert len(errors) == 0


# ============================================================================
# Test E: code_scaffold containing ```dart -> PASS
# ============================================================================
def test_e_code_scaffold_containing_dart_code_fence_passes():
    scaffold_with_dart_fence = (
        "```dart\n"
        "class GenericWidget extends StatelessWidget {\n"
        "  const GenericWidget({Key? key}) : super(key: key);\n"
        "}\n"
        "```"
    )
    bp = _build_generic_blueprint(scaffold_with_dart_fence)
    serialized = serialize_blueprint_to_canonical_json(bp)
    
    ok, errors = validate_canonical_architecture_plan_state(serialized, canonical_blueprint=bp)
    assert ok is True, f"Expected PASS when ```dart is inside code_scaffold, got: {errors}"
    assert len(errors) == 0


# ============================================================================
# Test F: code_scaffold containing ```python -> PASS
# ============================================================================
def test_f_code_scaffold_containing_python_code_fence_passes():
    scaffold_with_py_fence = (
        "```python\n"
        "def process_stream(stream_id: str) -> None:\n"
        "    pass\n"
        "```"
    )
    bp = _build_generic_blueprint(scaffold_with_py_fence)
    serialized = serialize_blueprint_to_canonical_json(bp)
    
    ok, errors = validate_canonical_architecture_plan_state(serialized, canonical_blueprint=bp)
    assert ok is True, f"Expected PASS when ```python is inside code_scaffold, got: {errors}"
    assert len(errors) == 0


# ============================================================================
# Test G: Nested JSON string containing backticks -> PASS
# ============================================================================
def test_g_nested_json_string_containing_backticks_passes():
    scaffold_with_markdown = "def render_doc():\n    return 'Use `param_a` and `param_b` strictly.'\n"
    bp = _build_generic_blueprint(scaffold_with_markdown)
    serialized = serialize_blueprint_to_canonical_json(bp)
    
    ok, errors = validate_canonical_architecture_plan_state(serialized, canonical_blueprint=bp)
    assert ok is True, f"Expected PASS when backticks are in strings, got: {errors}"
    assert len(errors) == 0


# ============================================================================
# Test H: Ordinary source code containing backticks -> PASS
# ============================================================================
def test_h_ordinary_source_code_containing_backticks_passes():
    scaffold_with_ticks = "const template = `Value is: ${item_id}`;\n"
    bp = _build_generic_blueprint(scaffold_with_ticks)
    serialized = serialize_blueprint_to_canonical_json(bp)
    
    ok, errors = validate_canonical_architecture_plan_state(serialized, canonical_blueprint=bp)
    assert ok is True, f"Expected PASS when template literal backticks are used, got: {errors}"
    assert len(errors) == 0


# ============================================================================
# Test I: Malformed JSON -> FAIL
# ============================================================================
def test_i_malformed_json_fails():
    malformed = '{"schema_version": "1.0.0", "task_id": "bad_json", '
    ok, errors = validate_canonical_architecture_plan_state(malformed)
    assert ok is False
    assert any("STATE_REPRESENTATION_FAILURE" in e for e in errors)
    assert any("not valid JSON" in e for e in errors)


# ============================================================================
# Test J: Non-object root -> FAIL (existing canonical schema behavior)
# ============================================================================
def test_j_non_object_root_fails():
    list_root = json.dumps(["item1", "item2"])
    ok, errors = validate_canonical_architecture_plan_state(list_root)
    assert ok is False
    assert any("STATE_REPRESENTATION_FAILURE" in e for e in errors)
    assert any("not a JSON object" in e for e in errors)


# ============================================================================
# Test K: Valid blueprint with backtick-bearing source -> semantic equivalence
# ============================================================================
def test_k_valid_blueprint_with_backtick_bearing_source_semantic_equivalence():
    rich_scaffold = (
        "/**\n"
        " * ```generic\n"
        " * let config = `mode: active`;\n"
        " * ```\n"
        " */\n"
        "def execute_task() -> bool:\n"
        "    return True\n"
    )
    bp = _build_generic_blueprint(rich_scaffold)
    serialized = serialize_blueprint_to_canonical_json(bp)
    
    ok, errors = validate_canonical_architecture_plan_state(serialized, canonical_blueprint=bp)
    assert ok is True, f"Expected semantic equivalence, got: {errors}"
    assert len(errors) == 0
    
    # Verify exact decoded content
    decoded = json.loads(serialized)
    assert decoded["files"]["module.ext"]["code_scaffold"] == rich_scaffold


# ============================================================================
# Test L: No source mutation during validation (observational integrity)
# ============================================================================
def test_l_no_source_mutation_during_validation():
    rich_scaffold = "```lang\nconst x = `template`;\n```"
    bp = _build_generic_blueprint(rich_scaffold)
    serialized = serialize_blueprint_to_canonical_json(bp)
    
    original_serialized = str(serialized)
    ok, errors = validate_canonical_architecture_plan_state(serialized, canonical_blueprint=bp)
    
    assert ok is True
    # Verify string was not mutated or sanitized in place
    assert serialized == original_serialized
    # Verify backticks remain inside the serialized text
    assert "```lang" in serialized
    assert "`template`" in serialized
