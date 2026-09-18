"""
Deterministic Test Suite — Staged Architect JSON Decoder Consistency v1
Treatment #1.8.6 Pipeline Repair

Tests A through J verifying:
A. Multiline Python scaffold containing raw newline characters
B. Multiline Dart scaffold containing raw newline characters
C. Quotes inside source strings
D. Tabs inside source strings
E. Ordinary escaped JSON strings
F. Malformed JSON structure remains rejected
G. Missing required fields remains rejected
H. Invalid schema remains rejected
I. Stage-A validated mappings remain unchanged
J. Serializer behavior remains unchanged & decoded scaffold == intended scaffold
"""

import json
import pytest
from backend.blueprint_schema import (
    decode_canonical_architectural_json,
    parse_blueprint_json_classified,
    ArchitecturalBlueprint
)
from backend.architect_staged import (
    StageAObligationMapping,
    FrozenStageAMappings,
    validate_stage_a_mappings,
    parse_stage_b_assembly,
    validate_stage_b_preservation,
    convert_stage_b_to_semantic_plan,
    StageBAssemblyOutput
)
from backend.semantic_serializer import (
    serialize_semantic_decision_to_blueprint
)


# ============================================================================
# Test A: Multiline Python scaffold containing raw newline characters
# ============================================================================
def test_a_multiline_python_scaffold_raw_newlines():
    intended_scaffold = (
        "def add_matrices(a: list, b: list) -> list:\n"
        "    if len(a) != len(b):\n"
        "        raise ValueError('Dimension mismatch')\n"
        "    return [[a[i][j] + b[i][j] for j in range(len(a[0]))] for i in range(len(a))]\n"
    )
    
    # Construct raw JSON containing literal raw unescaped newlines inside the string value
    raw_code_val = json.dumps(intended_scaffold).replace(r"\n", "\n")
    
    raw_stage_b = (
        "=== STAGE B: ARCHITECTURAL ASSEMBLY ===\n"
        "{\n"
        '  "target_file": "main.py",\n'
        '  "scaffold_code": ' + raw_code_val + ',\n'
        '  "files": {\n'
        '    "main.py": ' + raw_code_val + '\n'
        "  },\n"
        '  "semantic_decisions": [\n'
        "    {\n"
        '      "obligation_id": "OBL-01",\n'
        '      "target_structure": "INTERFACE_CONTRACT",\n'
        '      "identifier": "add_matrices",\n'
        '      "target_file": "main.py",\n'
        '      "parameters": [{"name": "a", "type": "list"}, {"name": "b", "type": "list"}],\n'
        '      "return_semantics": {"type": "list"}\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "=== END STAGE B ==="
    )
    
    assembly, errs = parse_stage_b_assembly(raw_stage_b)
    assert errs == []
    assert assembly is not None
    assert assembly.target_file == "main.py"
    assert assembly.scaffold_code == intended_scaffold
    assert assembly.files["main.py"] == intended_scaffold
    assert assembly.decoder_telemetry.get("decoder_mode") == "CANONICAL_STRICT_FALSE"
    assert assembly.decoder_telemetry.get("parse_success") is True


# ============================================================================
# Test B: Multiline Dart scaffold containing raw newline characters
# ============================================================================
def test_b_multiline_dart_scaffold_raw_newlines():
    intended_dart_scaffold = (
        "import 'package:flutter/material.dart';\n"
        "\n"
        "class MetricData {\n"
        "  final String label;\n"
        "  final double value;\n"
        "  const MetricData({required this.label, required this.value});\n"
        "}\n"
        "\n"
        "class CardMetric extends StatelessWidget {\n"
        "  final MetricData data;\n"
        "  const CardMetric({Key? key, required this.data}) : super(key: key);\n"
        "  @override\n"
        "  Widget build(BuildContext context) {\n"
        "    return Text('${data.label}: ${data.value}');\n"
        "  }\n"
        "}\n"
    )
    
    raw_code_val = json.dumps(intended_dart_scaffold).replace(r"\n", "\n")
    
    raw_stage_b = (
        "=== STAGE B: ARCHITECTURAL ASSEMBLY ===\n"
        "{\n"
        '  "target_file": "lib/card_metric.dart",\n'
        '  "files": {\n'
        '    "lib/card_metric.dart": ' + raw_code_val + '\n'
        "  },\n"
        '  "scaffold_code": ' + raw_code_val + ',\n'
        '  "semantic_decisions": [\n'
        "    {\n"
        '      "obligation_id": "OBL-01",\n'
        '      "target_structure": "DATA_MODEL",\n'
        '      "identifier": "MetricData",\n'
        '      "target_file": "lib/card_metric.dart"\n'
        "    },\n"
        "    {\n"
        '      "obligation_id": "OBL-02",\n'
        '      "target_structure": "INTERFACE_CONTRACT",\n'
        '      "identifier": "CardMetric",\n'
        '      "target_file": "lib/card_metric.dart"\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "=== END STAGE B ==="
    )
    
    assembly, errs = parse_stage_b_assembly(raw_stage_b)
    assert errs == []
    assert assembly is not None
    assert assembly.target_file == "lib/card_metric.dart"
    assert assembly.scaffold_code == intended_dart_scaffold
    assert assembly.files["lib/card_metric.dart"] == intended_dart_scaffold
    assert assembly.decoder_telemetry.get("parse_success") is True


# ============================================================================
# Test C: Quotes inside source strings
# ============================================================================
def test_c_quotes_inside_source_strings():
    intended_code = 'msg = "Hello \\"World\\""\nquote = \'single quote\''
    json_literal = json.dumps(intended_code).replace(r"\n", "\n")
    
    raw_stage_b = (
        "=== STAGE B: ARCHITECTURAL ASSEMBLY ===\n"
        "{\n"
        '  "target_file": "quote.py",\n'
        '  "scaffold_code": ' + json_literal + ',\n'
        '  "files": {"quote.py": ' + json_literal + '},\n'
        '  "semantic_decisions": [\n'
        "    {\n"
        '      "obligation_id": "OBL-01",\n'
        '      "target_structure": "INTERFACE_CONTRACT",\n'
        '      "identifier": "quote_fn",\n'
        '      "target_file": "quote.py"\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "=== END STAGE B ==="
    )
    assembly, errs = parse_stage_b_assembly(raw_stage_b)
    assert errs == []
    assert assembly is not None
    assert assembly.scaffold_code == intended_code
    assert 'Hello \\"World\\"' in assembly.scaffold_code
    assert "'single quote'" in assembly.scaffold_code


# ============================================================================
# Test D: Tabs inside source strings
# ============================================================================
def test_d_tabs_inside_source_strings():
    intended_code = "def tabbed():\n\treturn 42\n"
    json_literal = json.dumps(intended_code).replace(r"\t", "\t").replace(r"\n", "\n")
    
    raw_stage_b = (
        "=== STAGE B: ARCHITECTURAL ASSEMBLY ===\n"
        "{\n"
        '  "target_file": "tabs.py",\n'
        '  "scaffold_code": ' + json_literal + ',\n'
        '  "semantic_decisions": [\n'
        "    {\n"
        '      "obligation_id": "OBL-01",\n'
        '      "target_structure": "INTERFACE_CONTRACT",\n'
        '      "identifier": "tabbed",\n'
        '      "target_file": "tabs.py"\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "=== END STAGE B ==="
    )
    assembly, errs = parse_stage_b_assembly(raw_stage_b)
    assert errs == []
    assert assembly is not None
    assert assembly.scaffold_code == intended_code
    assert "\treturn 42" in assembly.scaffold_code


# ============================================================================
# Test E: Ordinary escaped JSON strings
# ============================================================================
def test_e_ordinary_escaped_json_strings():
    intended_code = "def calc():\n    return 100\n"
    raw_stage_b = """
    === STAGE B: ARCHITECTURAL ASSEMBLY ===
    {
      "target_file": "calc.py",
      "scaffold_code": "def calc():\\n    return 100\\n",
      "files": {"calc.py": "def calc():\\n    return 100\\n"},
      "semantic_decisions": [
        {
          "obligation_id": "OBL-01",
          "target_structure": "INTERFACE_CONTRACT",
          "identifier": "calc",
          "target_file": "calc.py"
        }
      ]
    }
    === END STAGE B ===
    """
    assembly, errs = parse_stage_b_assembly(raw_stage_b)
    assert errs == []
    assert assembly is not None
    assert assembly.scaffold_code == intended_code
    assert assembly.decoder_telemetry.get("parse_success") is True


# ============================================================================
# Test F: Malformed JSON structure remains rejected
# ============================================================================
def test_f_malformed_json_structure_remains_rejected():
    raw_bad_json = """
    === STAGE B: ARCHITECTURAL ASSEMBLY ===
    {
      "target_file": "calc.py",
      "scaffold_code": "unclosed json string...
    === END STAGE B ===
    """
    assembly, errs = parse_stage_b_assembly(raw_bad_json)
    assert assembly is None
    assert len(errs) > 0
    assert any("STAGE_B_JSON_PARSE_ERROR" in e for e in errs)


# ============================================================================
# Test G: Missing required fields remains rejected
# ============================================================================
def test_g_missing_required_fields_remains_rejected():
    raw_stage_b = """
    === STAGE B: ARCHITECTURAL ASSEMBLY ===
    {
      "target_file": "calc.py",
      "semantic_decisions": "NOT_A_LIST"
    }
    === END STAGE B ===
    """
    assembly, errs = parse_stage_b_assembly(raw_stage_b)
    assert assembly is None
    assert any("STAGE_B_SCHEMA_ERROR" in e for e in errs)


# ============================================================================
# Test H: Invalid schema remains rejected
# ============================================================================
def test_h_invalid_schema_remains_rejected():
    raw_array_json = """
    === STAGE B: ARCHITECTURAL ASSEMBLY ===
    ["not", "a", "dictionary"]
    === END STAGE B ===
    """
    assembly, errs = parse_stage_b_assembly(raw_array_json)
    assert assembly is None
    assert any("STAGE_B_JSON_PARSE_ERROR" in e or "STAGE_B_STRUCTURE_ERROR" in e for e in errs)


# ============================================================================
# Test I: Stage-A validated mappings remain unchanged
# ============================================================================
def test_i_stage_a_validated_mappings_remain_unchanged():
    auth_obs = ["OBL-01", "OBL-02"]
    mappings = [
        StageAObligationMapping(
            obligation_id="OBL-01",
            semantic_element="add",
            element_kind="FUNCTION",
            semantic_identity="add",
            semantic_target_artifact="math_ops.py",
            semantic_return={"type": "int"}
        ),
        StageAObligationMapping(
            obligation_id="OBL-02",
            semantic_element="sub",
            element_kind="FUNCTION",
            semantic_identity="sub",
            semantic_target_artifact="math_ops.py",
            semantic_return={"type": "int"}
        )
    ]
    is_valid, errs = validate_stage_a_mappings(mappings, auth_obs)
    assert is_valid is True
    assert errs == []
    
    frozen_a = FrozenStageAMappings.freeze(mappings)
    assert len(frozen_a.mappings) == 2
    assert frozen_a.sha256_seal is not None
    
    # Verify Stage B preserves these exact mappings
    multiline_code = (
        "def add(a: int, b: int) -> int:\n"
        "    return a + b\n\n"
        "def sub(a: int, b: int) -> int:\n"
        "    return a - b\n"
    )
    raw_code_val = json.dumps(multiline_code).replace(r"\n", "\n")
    raw_stage_b = (
        "=== STAGE B: ARCHITECTURAL ASSEMBLY ===\n"
        "{\n"
        '  "target_file": "math_ops.py",\n'
        '  "scaffold_code": ' + raw_code_val + ',\n'
        '  "semantic_decisions": [\n'
        "    {\n"
        '      "obligation_id": "OBL-01",\n'
        '      "target_structure": "INTERFACE_CONTRACT",\n'
        '      "identifier": "add",\n'
        '      "target_file": "math_ops.py"\n'
        "    },\n"
        "    {\n"
        '      "obligation_id": "OBL-02",\n'
        '      "target_structure": "INTERFACE_CONTRACT",\n'
        '      "identifier": "sub",\n'
        '      "target_file": "math_ops.py"\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "=== END STAGE B ==="
    )
    assembly, b_errs = parse_stage_b_assembly(raw_stage_b)
    assert b_errs == []
    b_valid, b_pres_errs, revs = validate_stage_b_preservation(frozen_a, assembly)
    assert b_valid is True
    assert b_pres_errs == []


# ============================================================================
# Test J: Serializer behavior remains unchanged & decoded scaffold == intended scaffold
# ============================================================================
def test_j_serializer_behavior_and_scaffold_preservation():
    intended_code = (
        "class Matrix:\n"
        "    def __init__(self, data: list):\n"
        "        self.data = data\n"
        "\n"
        "def add_matrices(a: list, b: list) -> list:\n"
        "    return [[a[i][j] + b[i][j] for j in range(len(a[0]))] for i in range(len(a))]\n"
    )
    
    mapping = StageAObligationMapping(
        obligation_id="OBL-01",
        semantic_element="add_matrices",
        element_kind="FUNCTION",
        semantic_identity="add_matrices",
        semantic_target_artifact="matrix.py",
        semantic_parameters=({"name": "a", "type": "list"}, {"name": "b", "type": "list"}),
        semantic_return={"type": "list"}
    )
    frozen_a = FrozenStageAMappings.freeze([mapping])
    
    raw_code_val = json.dumps(intended_code).replace(r"\n", "\n")
    raw_stage_b = (
        "=== STAGE B: ARCHITECTURAL ASSEMBLY ===\n"
        "{\n"
        '  "target_file": "matrix.py",\n'
        '  "scaffold_code": ' + raw_code_val + ',\n'
        '  "files": {\n'
        '    "matrix.py": ' + raw_code_val + '\n'
        "  },\n"
        '  "semantic_decisions": [\n'
        "    {\n"
        '      "obligation_id": "OBL-01",\n'
        '      "target_structure": "INTERFACE_CONTRACT",\n'
        '      "identifier": "add_matrices",\n'
        '      "target_file": "matrix.py",\n'
        '      "parameters": [{"name": "a", "type": "list"}, {"name": "b", "type": "list"}],\n'
        '      "return_semantics": {"type": "list"}\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "=== END STAGE B ==="
    )
    assembly, parse_errs = parse_stage_b_assembly(raw_stage_b)
    assert parse_errs == []
    assert assembly is not None
    assert assembly.scaffold_code == intended_code
    
    # Test conversion to plan
    plan, conv_errs = convert_stage_b_to_semantic_plan(frozen_a, assembly, task_id="matrix_cli")
    assert conv_errs == []
    assert plan is not None
    assert plan.files["matrix.py"] == intended_code
    
    # Test serialization to blueprint
    bp, ser_errs = serialize_semantic_decision_to_blueprint(plan)
    assert ser_errs == []
    assert bp is not None
    assert bp.authoritative_target_file == "matrix.py"
    assert bp.files["matrix.py"].code_scaffold == intended_code
    assert len(bp.interface_contracts) == 1
    assert bp.interface_contracts[0].identifier == "add_matrices"
