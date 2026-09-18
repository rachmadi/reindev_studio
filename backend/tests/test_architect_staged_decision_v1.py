"""
Synthetic Test Suite for Treatment #1.8.6: Staged Architectural Decision v1
Tests A through T (20 tests)

Tests:
A. one obligation
B. multiple obligations
C. callable
D. class/component
E. endpoint
F. data model
G. mixed obligation types
H. duplicate mapping
I. missing mapping
J. ambiguous mapping
K. Stage-A preservation
L. Stage-B preservation
M. Stage-A repair without Stage-B mutation
N. Stage-B repair without Stage-A mutation
O. deterministic serialization
P. no obligation invention
Q. cross-domain fixture
R. serializer insufficiency
S. semantic state immutability between stages
T. explicit Stage-A revision request
"""

import pytest
import json
import hashlib
from typing import Dict, List, Any

from backend.architect_staged import (
    StageAObligationMapping,
    FrozenStageAMappings,
    StageARevisionRequest,
    StageBAssemblyOutput,
    parse_stage_a_mappings,
    validate_stage_a_mappings,
    parse_stage_b_assembly,
    validate_stage_b_preservation,
    convert_stage_b_to_semantic_plan,
    build_stage_a_prompt,
    build_stage_b_prompt
)
from backend.semantic_serializer import (
    SemanticParameter,
    SemanticReturn,
    SemanticArchitecturalDecision,
    SemanticArchitecturalPlan,
    serialize_semantic_decision_to_blueprint
)
from backend.blueprint_schema import ArchitecturalBlueprint


# ============================================================================
# Test A: One obligation
# ============================================================================
def test_a_one_obligation():
    auth_obs = ["OBL-01"]
    raw_stage_a = """
    === STAGE A: OBLIGATION MAPPING ===
    {
      "obligation_mappings": [
        {
          "obligation_id": "OBL-01",
          "semantic_element": "ComputeTotal",
          "element_kind": "FUNCTION",
          "semantic_identity": "compute_total",
          "semantic_target_artifact": "main.py",
          "semantic_parameters": [
            {"name": "items", "type": "List[float]", "location": "ARGUMENT", "required": true}
          ],
          "semantic_return": {"type": "float", "status_code": 200}
        }
      ]
    }
    === END STAGE A ===
    """
    mappings, parse_errs = parse_stage_a_mappings(raw_stage_a)
    assert parse_errs == []
    assert len(mappings) == 1
    
    is_valid, val_errs = validate_stage_a_mappings(mappings, auth_obs)
    assert is_valid is True
    assert val_errs == []
    
    frozen_a = FrozenStageAMappings.freeze(mappings)
    assert frozen_a.sha256_seal is not None
    
    raw_stage_b = """
    === STAGE B: ARCHITECTURAL ASSEMBLY ===
    {
      "target_file": "main.py",
      "files": {
        "main.py": {
          "scaffold_code": "def compute_total(items: list) -> float:\\n    return sum(items)\\n"
        }
      },
      "scaffold_code": "def compute_total(items: list) -> float:\\n    return sum(items)\\n",
      "semantic_decisions": [
        {
          "obligation_id": "OBL-01",
          "target_structure": "INTERFACE_CONTRACT",
          "identifier": "compute_total",
          "target_file": "main.py",
          "parameters": [
            {"name": "items", "type": "List[float]", "location": "ARGUMENT", "required": true}
          ],
          "return_semantics": {"type": "float", "status_code": 200}
        }
      ]
    }
    === END STAGE B ===
    """
    assembly, b_parse_errs = parse_stage_b_assembly(raw_stage_b)
    assert b_parse_errs == []
    
    b_valid, b_errs, revs = validate_stage_b_preservation(frozen_a, assembly)
    assert b_valid is True
    assert b_errs == []
    assert revs == []
    
    plan, conv_errs = convert_stage_b_to_semantic_plan(frozen_a, assembly)
    assert conv_errs == []
    
    bp, ser_errs = serialize_semantic_decision_to_blueprint(plan)
    assert ser_errs == []
    assert bp is not None
    assert len(bp.interface_contracts) == 1
    assert bp.interface_contracts[0].identifier == "compute_total"


# ============================================================================
# Test B: Multiple obligations
# ============================================================================
def test_b_multiple_obligations():
    auth_obs = ["OBL-01", "OBL-02", "OBL-03"]
    mappings = [
        StageAObligationMapping(
            obligation_id="OBL-01",
            semantic_element="OpOne",
            element_kind="FUNCTION",
            semantic_identity="op_one",
            semantic_target_artifact="ops.py",
            semantic_return={"type": "int"}
        ),
        StageAObligationMapping(
            obligation_id="OBL-02",
            semantic_element="OpTwo",
            element_kind="FUNCTION",
            semantic_identity="op_two",
            semantic_target_artifact="ops.py",
            semantic_return={"type": "str"}
        ),
        StageAObligationMapping(
            obligation_id="OBL-03",
            semantic_element="OpThree",
            element_kind="FUNCTION",
            semantic_identity="op_three",
            semantic_target_artifact="ops.py",
            semantic_return={"type": "bool"}
        )
    ]
    is_valid, val_errs = validate_stage_a_mappings(mappings, auth_obs)
    assert is_valid is True
    assert val_errs == []
    
    frozen_a = FrozenStageAMappings.freeze(mappings)
    assert len(frozen_a.mappings) == 3
    
    assembly = StageBAssemblyOutput(
        target_file="ops.py",
        files={"ops.py": "def op_one(): pass\ndef op_two(): pass\ndef op_three(): pass"},
        scaffold_code="def op_one(): pass\ndef op_two(): pass\ndef op_three(): pass",
        semantic_decisions=[
            SemanticArchitecturalDecision(obligation_id="OBL-01", target_structure="INTERFACE_CONTRACT", identifier="op_one", target_file="ops.py"),
            SemanticArchitecturalDecision(obligation_id="OBL-02", target_structure="INTERFACE_CONTRACT", identifier="op_two", target_file="ops.py"),
            SemanticArchitecturalDecision(obligation_id="OBL-03", target_structure="INTERFACE_CONTRACT", identifier="op_three", target_file="ops.py"),
        ]
    )
    b_valid, b_errs, _ = validate_stage_b_preservation(frozen_a, assembly)
    assert b_valid is True
    
    plan, conv_errs = convert_stage_b_to_semantic_plan(frozen_a, assembly)
    bp, ser_errs = serialize_semantic_decision_to_blueprint(plan)
    assert ser_errs == []
    assert len(bp.interface_contracts) == 3


# ============================================================================
# Test C: Callable
# ============================================================================
def test_c_callable():
    auth_obs = ["OBL-CALLABLE"]
    m = StageAObligationMapping(
        obligation_id="OBL-CALLABLE",
        semantic_element="CalculateInterest",
        element_kind="CALLABLE",
        semantic_identity="calculate_interest",
        semantic_target_artifact="calculator.py",
        semantic_parameters=({"name": "principal", "type": "float", "location": "ARGUMENT", "required": True},
                             {"name": "rate", "type": "float", "location": "ARGUMENT", "required": True}),
        semantic_return={"type": "float"}
    )
    is_valid, errs = validate_stage_a_mappings([m], auth_obs)
    assert is_valid is True
    
    frozen_a = FrozenStageAMappings.freeze([m])
    assembly = StageBAssemblyOutput(
        target_file="calculator.py",
        files={"calculator.py": "def calculate_interest(principal: float, rate: float) -> float:\n    return principal * rate"},
        scaffold_code="def calculate_interest(principal: float, rate: float) -> float:\n    return principal * rate",
        semantic_decisions=[
            SemanticArchitecturalDecision(
                obligation_id="OBL-CALLABLE",
                target_structure="INTERFACE_CONTRACT",
                identifier="calculate_interest",
                target_file="calculator.py",
                parameters=[
                    SemanticParameter(name="principal", type="float"),
                    SemanticParameter(name="rate", type="float")
                ],
                return_semantics=SemanticReturn(type="float")
            )
        ]
    )
    b_valid, b_errs, _ = validate_stage_b_preservation(frozen_a, assembly)
    assert b_valid is True
    
    plan, _ = convert_stage_b_to_semantic_plan(frozen_a, assembly)
    bp, ser_errs = serialize_semantic_decision_to_blueprint(plan)
    assert ser_errs == []
    assert len(bp.interface_contracts) == 1
    assert len(bp.interface_contracts[0].parameters) == 2


# ============================================================================
# Test D: Class / Component
# ============================================================================
def test_d_class_component():
    auth_obs = ["OBL-COMPONENT"]
    m = StageAObligationMapping(
        obligation_id="OBL-COMPONENT",
        semantic_element="VectorEngine",
        element_kind="CLASS",
        semantic_identity="VectorEngine",
        semantic_target_artifact="engine.py",
        semantic_parameters=({"name": "dimensions", "type": "int", "location": "ARGUMENT", "required": True},),
        semantic_return={"type": "VectorEngine"}
    )
    is_valid, errs = validate_stage_a_mappings([m], auth_obs)
    assert is_valid is True
    
    frozen_a = FrozenStageAMappings.freeze([m])
    assembly = StageBAssemblyOutput(
        target_file="engine.py",
        files={"engine.py": "class VectorEngine:\n    def __init__(self, dimensions: int):\n        self.dimensions = dimensions"},
        scaffold_code="class VectorEngine:\n    def __init__(self, dimensions: int):\n        self.dimensions = dimensions",
        semantic_decisions=[
            SemanticArchitecturalDecision(
                obligation_id="OBL-COMPONENT",
                target_structure="INTERFACE_CONTRACT",
                identifier="VectorEngine",
                target_file="engine.py",
                parameters=[SemanticParameter(name="dimensions", type="int")],
                return_semantics=SemanticReturn(type="VectorEngine")
            )
        ]
    )
    b_valid, _, _ = validate_stage_b_preservation(frozen_a, assembly)
    assert b_valid is True
    
    plan, _ = convert_stage_b_to_semantic_plan(frozen_a, assembly)
    bp, _ = serialize_semantic_decision_to_blueprint(plan)
    assert bp.interface_contracts[0].identifier == "VectorEngine"


# ============================================================================
# Test E: Endpoint
# ============================================================================
def test_e_endpoint():
    auth_obs = ["OBL-ENDPOINT"]
    m = StageAObligationMapping(
        obligation_id="OBL-ENDPOINT",
        semantic_element="GetItemEndpoint",
        element_kind="ENDPOINT",
        semantic_identity="get_item_by_id",
        semantic_target_artifact="server.py",
        semantic_parameters=({"name": "item_id", "type": "int", "location": "PATH", "required": True},),
        semantic_return={"type": "dict", "status_code": 200, "error_codes": [404]}
    )
    is_valid, errs = validate_stage_a_mappings([m], auth_obs)
    assert is_valid is True
    
    frozen_a = FrozenStageAMappings.freeze([m])
    assembly = StageBAssemblyOutput(
        target_file="server.py",
        files={"server.py": "@app.get('/items/{item_id}')\ndef get_item_by_id(item_id: int):\n    return {}"},
        scaffold_code="@app.get('/items/{item_id}')\ndef get_item_by_id(item_id: int):\n    return {}",
        semantic_decisions=[
            SemanticArchitecturalDecision(
                obligation_id="OBL-ENDPOINT",
                target_structure="INTERFACE_CONTRACT",
                identifier="get_item_by_id",
                target_file="server.py",
                route="/items/{item_id}",
                http_method="GET",
                parameters=[SemanticParameter(name="item_id", type="int", location="PATH")],
                return_semantics=SemanticReturn(type="dict", status_code=200, error_codes=[404])
            )
        ]
    )
    b_valid, _, _ = validate_stage_b_preservation(frozen_a, assembly)
    assert b_valid is True
    
    plan, _ = convert_stage_b_to_semantic_plan(frozen_a, assembly)
    bp, _ = serialize_semantic_decision_to_blueprint(plan)
    assert bp.interface_contracts[0].route == "/items/{item_id}"
    assert bp.interface_contracts[0].method == "GET"


# ============================================================================
# Test F: Data model
# ============================================================================
def test_f_data_model():
    auth_obs = ["OBL-MODEL"]
    m = StageAObligationMapping(
        obligation_id="OBL-MODEL",
        semantic_element="StudentRecord",
        element_kind="DATA_MODEL",
        semantic_identity="StudentRecord",
        semantic_target_artifact="models.py",
        semantic_parameters=(),
        semantic_return={}
    )
    is_valid, errs = validate_stage_a_mappings([m], auth_obs)
    assert is_valid is True
    
    frozen_a = FrozenStageAMappings.freeze([m])
    assembly = StageBAssemblyOutput(
        target_file="models.py",
        files={"models.py": "class StudentRecord:\n    id: int\n    name: str\n    active: bool"},
        scaffold_code="class StudentRecord:\n    id: int\n    name: str\n    active: bool",
        semantic_decisions=[
            SemanticArchitecturalDecision(
                obligation_id="OBL-MODEL",
                target_structure="DATA_MODEL",
                identifier="StudentRecord",
                target_file="models.py",
                fields=[
                    {"name": "id", "type": "int", "required": True},
                    {"name": "name", "type": "str", "required": True},
                    {"name": "active", "type": "bool", "required": False}
                ]
            )
        ]
    )
    b_valid, _, _ = validate_stage_b_preservation(frozen_a, assembly)
    assert b_valid is True
    
    plan, _ = convert_stage_b_to_semantic_plan(frozen_a, assembly)
    bp, _ = serialize_semantic_decision_to_blueprint(plan)
    assert len(bp.data_models) == 1
    assert bp.data_models[0].model_name == "StudentRecord"
    assert len(bp.data_models[0].fields) == 3


# ============================================================================
# Test G: Mixed obligation types
# ============================================================================
def test_g_mixed_obligation_types():
    auth_obs = ["OBL-FN", "OBL-CLS", "OBL-EP", "OBL-DM"]
    mappings = [
        StageAObligationMapping("OBL-FN", "HelperFunc", "FUNCTION", "helper_func", "app.py"),
        StageAObligationMapping("OBL-CLS", "ServiceClass", "CLASS", "ServiceClass", "app.py"),
        StageAObligationMapping("OBL-EP", "ApiEndpoint", "ENDPOINT", "handle_api", "app.py"),
        StageAObligationMapping("OBL-DM", "AppPayload", "DATA_MODEL", "AppPayload", "app.py")
    ]
    is_valid, errs = validate_stage_a_mappings(mappings, auth_obs)
    assert is_valid is True
    
    frozen_a = FrozenStageAMappings.freeze(mappings)
    assembly = StageBAssemblyOutput(
        target_file="app.py",
        files={"app.py": "# scaffold"},
        scaffold_code="# scaffold",
        semantic_decisions=[
            SemanticArchitecturalDecision(obligation_id="OBL-FN", target_structure="INTERFACE_CONTRACT", identifier="helper_func", target_file="app.py"),
            SemanticArchitecturalDecision(obligation_id="OBL-CLS", target_structure="INTERFACE_CONTRACT", identifier="ServiceClass", target_file="app.py"),
            SemanticArchitecturalDecision(obligation_id="OBL-EP", target_structure="INTERFACE_CONTRACT", identifier="handle_api", target_file="app.py"),
            SemanticArchitecturalDecision(obligation_id="OBL-DM", target_structure="DATA_MODEL", identifier="AppPayload", target_file="app.py", fields=[{"name": "val", "type": "str"}])
        ]
    )
    b_valid, _, _ = validate_stage_b_preservation(frozen_a, assembly)
    assert b_valid is True
    
    plan, _ = convert_stage_b_to_semantic_plan(frozen_a, assembly)
    bp, _ = serialize_semantic_decision_to_blueprint(plan)
    assert len(bp.interface_contracts) == 3
    assert len(bp.data_models) == 1


# ============================================================================
# Test H: Duplicate mapping
# ============================================================================
def test_h_duplicate_mapping():
    auth_obs = ["OBL-01"]
    mappings = [
        StageAObligationMapping("OBL-01", "ElemA", "FUNCTION", "ident_alpha", "main.py"),
        StageAObligationMapping("OBL-01", "ElemB", "DATA_MODEL", "ident_beta", "main.py")
    ]
    is_valid, errs = validate_stage_a_mappings(mappings, auth_obs)
    assert is_valid is False
    assert any("STAGE_A_DUPLICATE_CONFLICT" in e for e in errs)


# ============================================================================
# Test I: Missing mapping
# ============================================================================
def test_i_missing_mapping():
    auth_obs = ["OBL-01", "OBL-02", "OBL-03"]
    mappings = [
        StageAObligationMapping("OBL-01", "ElemA", "FUNCTION", "func_a", "main.py"),
        StageAObligationMapping("OBL-02", "ElemB", "FUNCTION", "func_b", "main.py")
    ]
    is_valid, errs = validate_stage_a_mappings(mappings, auth_obs)
    assert is_valid is False
    assert any("STAGE_A_MISSING_OBLIGATIONS" in e for e in errs)
    assert any("OBL-03" in e for e in errs)


# ============================================================================
# Test J: Ambiguous mapping
# ============================================================================
def test_j_ambiguous_mapping():
    auth_obs = ["OBL-01", "OBL-02"]
    mappings = [
        StageAObligationMapping("OBL-01", "ElemA", "INVALID_KIND_XYZ", "func_a", "main.py"),
        StageAObligationMapping("OBL-02", "ElemB", "FUNCTION", "", "main.py")
    ]
    is_valid, errs = validate_stage_a_mappings(mappings, auth_obs)
    assert is_valid is False
    assert any("STAGE_A_INVALID_KIND" in e for e in errs)
    assert any("STAGE_A_UNRESOLVED_IDENTITY" in e for e in errs)


# ============================================================================
# Test K: Stage-A preservation
# ============================================================================
def test_k_stage_a_preservation():
    mappings = [
        StageAObligationMapping("OBL-01", "ElemA", "FUNCTION", "func_a", "main.py")
    ]
    frozen = FrozenStageAMappings.freeze(mappings)
    
    with pytest.raises(Exception):
        frozen.mappings = ()
    with pytest.raises(Exception):
        frozen.sha256_seal = "corrupted"
    
    raw_data = [m.to_dict() for m in sorted(mappings, key=lambda m: m.obligation_id)]
    expected_seal = hashlib.sha256(json.dumps(raw_data, sort_keys=True).encode("utf-8")).hexdigest()
    assert frozen.sha256_seal == expected_seal


# ============================================================================
# Test L: Stage-B preservation
# ============================================================================
def test_l_stage_b_preservation():
    mappings = [
        StageAObligationMapping("OBL-01", "ElemA", "FUNCTION", "original_func", "main.py")
    ]
    frozen = FrozenStageAMappings.freeze(mappings)
    
    # Scenario 1: Silent renaming
    assembly_rename = StageBAssemblyOutput(
        target_file="main.py",
        scaffold_code="def renamed_func(): pass",
        files={"main.py": "def renamed_func(): pass"},
        semantic_decisions=[
            SemanticArchitecturalDecision("OBL-01", "INTERFACE_CONTRACT", "renamed_func", "main.py")
        ]
    )
    b_valid, errs, _ = validate_stage_b_preservation(frozen, assembly_rename)
    assert b_valid is False
    assert any("STAGE_B_SILENT_RENAMING" in e for e in errs)
    
    # Scenario 2: Silent deletion
    assembly_empty = StageBAssemblyOutput(
        target_file="main.py",
        scaffold_code="pass",
        files={"main.py": "pass"},
        semantic_decisions=[]
    )
    b_valid_del, errs_del, _ = validate_stage_b_preservation(frozen, assembly_empty)
    assert b_valid_del is False
    assert any("STAGE_B_SILENT_DELETION" in e for e in errs_del)


# ============================================================================
# Test M: Stage-A repair without Stage-B mutation
# ============================================================================
def test_m_stage_a_repair_without_stage_b_mutation():
    auth_obs = ["OBL-01", "OBL-02"]
    turn0_mappings = [StageAObligationMapping("OBL-01", "ElemA", "FUNCTION", "func_a", "main.py")]
    is_valid, errs = validate_stage_a_mappings(turn0_mappings, auth_obs)
    assert is_valid is False
    
    repair_prompt = build_stage_a_prompt("python", "Sample task", "PM specs", repair_errors=errs)
    assert "[PERBAIKAN STAGE A DIPERLUKAN - HASIL VALIDASI GAGAL]" in repair_prompt
    assert "OBL-02" in repair_prompt
    
    turn1_mappings = [
        StageAObligationMapping("OBL-01", "ElemA", "FUNCTION", "func_a", "main.py"),
        StageAObligationMapping("OBL-02", "ElemB", "FUNCTION", "func_b", "main.py")
    ]
    is_valid_t1, errs_t1 = validate_stage_a_mappings(turn1_mappings, auth_obs)
    assert is_valid_t1 is True
    assert errs_t1 == []
    
    frozen = FrozenStageAMappings.freeze(turn1_mappings)
    assert len(frozen.mappings) == 2


# ============================================================================
# Test N: Stage-B repair without Stage-A mutation
# ============================================================================
def test_n_stage_b_repair_without_stage_a_mutation():
    mappings = [
        StageAObligationMapping("OBL-01", "ElemA", "FUNCTION", "stable_func", "main.py")
    ]
    frozen_a = FrozenStageAMappings.freeze(mappings)
    initial_seal = frozen_a.sha256_seal
    
    assembly_bad = StageBAssemblyOutput(
        target_file="main.py",
        scaffold_code="",
        files={},
        semantic_decisions=[
            SemanticArchitecturalDecision("OBL-01", "INTERFACE_CONTRACT", "stable_func", "main.py")
        ]
    )
    b_valid, errs, _ = validate_stage_b_preservation(frozen_a, assembly_bad)
    assert b_valid is False
    assert any("STAGE_B_MISSING_SCAFFOLD" in e for e in errs)
    
    repair_prompt = build_stage_b_prompt("python", "Sample task", "PM specs", frozen_a, repair_errors=errs)
    assert "[PERBAIKAN STAGE B DIPERLUKAN - INVARIANT PRESERVATION VIOLATION]" in repair_prompt
    assert initial_seal in repair_prompt
    
    assert frozen_a.sha256_seal == initial_seal
    assert frozen_a.mappings[0].semantic_identity == "stable_func"


# ============================================================================
# Test O: Deterministic serialization
# ============================================================================
def test_o_deterministic_serialization():
    mappings = [
        StageAObligationMapping("OBL-01", "AddFunc", "FUNCTION", "add", "calc.py",
                                semantic_parameters=({"name": "a", "type": "int", "location": "ARGUMENT", "required": True},
                                                     {"name": "b", "type": "int", "location": "ARGUMENT", "required": True}),
                                semantic_return={"type": "int"})
    ]
    frozen_a = FrozenStageAMappings.freeze(mappings)
    assembly = StageBAssemblyOutput(
        target_file="calc.py",
        scaffold_code="def add(a: int, b: int) -> int: return a + b",
        files={"calc.py": "def add(a: int, b: int) -> int: return a + b"},
        semantic_decisions=[
            SemanticArchitecturalDecision(
                "OBL-01", "INTERFACE_CONTRACT", "add", "calc.py",
                parameters=[SemanticParameter(name="a", type="int"), SemanticParameter(name="b", type="int")],
                return_semantics=SemanticReturn(type="int")
            )
        ]
    )
    plan, _ = convert_stage_b_to_semantic_plan(frozen_a, assembly)
    
    bp, ser_errs = serialize_semantic_decision_to_blueprint(plan)
    assert ser_errs == []
    assert isinstance(bp, ArchitecturalBlueprint)
    assert bp.authoritative_target_file == "calc.py"
    assert "calc.py" in bp.files
    assert bp.interface_contracts[0].identifier == "add"


# ============================================================================
# Test P: No obligation invention
# ============================================================================
def test_p_no_obligation_invention():
    auth_obs = ["OBL-REAL-01"]
    mappings = [
        StageAObligationMapping("OBL-REAL-01", "RealElem", "FUNCTION", "real_func", "main.py"),
        StageAObligationMapping("OBL-PHANTOM-99", "PhantomElem", "FUNCTION", "phantom_func", "main.py")
    ]
    is_valid, errs = validate_stage_a_mappings(mappings, auth_obs)
    assert is_valid is False
    assert any("STAGE_A_INVENTED_OBLIGATION" in e for e in errs)
    assert any("OBL-PHANTOM-99" in e for e in errs)


# ============================================================================
# Test Q: Cross-domain fixture (Zero task-specific branching)
# ============================================================================
def test_q_cross_domain_fixture():
    # Domain 1: Python Web Backend
    obs_web = ["OBL-WEB"]
    map_web = [StageAObligationMapping("OBL-WEB", "ApiEndpoint", "ENDPOINT", "get_status", "main.py")]
    ok_web, _ = validate_stage_a_mappings(map_web, obs_web)
    assert ok_web is True
    
    # Domain 2: Python CLI Tool
    obs_cli = ["OBL-CLI"]
    map_cli = [StageAObligationMapping("OBL-CLI", "CliCommand", "FUNCTION", "execute_matrix_op", "main.py")]
    ok_cli, _ = validate_stage_a_mappings(map_cli, obs_cli)
    assert ok_cli is True
    
    # Domain 3: Dart / Flutter Widget
    obs_dart = ["OBL-DART"]
    map_dart = [StageAObligationMapping("OBL-DART", "CardWidget", "WIDGET", "CardMetric", "lib/card_metric.dart")]
    ok_dart, _ = validate_stage_a_mappings(map_dart, obs_dart)
    assert ok_dart is True
    
    for m in [map_web[0], map_cli[0], map_dart[0]]:
        frozen = FrozenStageAMappings.freeze([m])
        struct = "INTERFACE_CONTRACT"
        assembly = StageBAssemblyOutput(
            target_file=m.semantic_target_artifact,
            scaffold_code="// scaffold",
            files={m.semantic_target_artifact: "// scaffold"},
            semantic_decisions=[SemanticArchitecturalDecision(m.obligation_id, struct, m.semantic_identity, m.semantic_target_artifact)]
        )
        b_ok, _, _ = validate_stage_b_preservation(frozen, assembly)
        assert b_ok is True
        plan, _ = convert_stage_b_to_semantic_plan(frozen, assembly)
        bp, ser_errs = serialize_semantic_decision_to_blueprint(plan)
        assert ser_errs == []
        assert bp.authoritative_target_file == m.semantic_target_artifact


# ============================================================================
# Test R: Serializer insufficiency
# ============================================================================
def test_r_serializer_insufficiency():
    mappings = [StageAObligationMapping("OBL-01", "ElemA", "FUNCTION", "func_a", "main.py")]
    frozen = FrozenStageAMappings.freeze(mappings)
    
    assembly_insufficient = StageBAssemblyOutput(
        target_file="main.py",
        scaffold_code="pass",
        files={"main.py": "pass"},
        semantic_decisions=[
            SemanticArchitecturalDecision("OBL-01", target_structure="", identifier="func_a", target_file="main.py")
        ]
    )
    plan, _ = convert_stage_b_to_semantic_plan(frozen, assembly_insufficient)
    bp, ser_errs = serialize_semantic_decision_to_blueprint(plan)
    assert bp is None
    assert any("SERIALIZATION_INSUFFICIENT_EVIDENCE" in e for e in ser_errs)


# ============================================================================
# Test S: Semantic state immutability between stages
# ============================================================================
def test_s_semantic_state_immutability_between_stages():
    mappings = [
        StageAObligationMapping("OBL-01", "ElemOne", "FUNCTION", "one", "a.py"),
        StageAObligationMapping("OBL-02", "ElemTwo", "DATA_MODEL", "TwoModel", "b.py")
    ]
    frozen_a = FrozenStageAMappings.freeze(mappings)
    seal_before = frozen_a.sha256_seal
    
    assembly = StageBAssemblyOutput(
        target_file="a.py",
        files={"a.py": "def one(): pass", "b.py": "class TwoModel: pass"},
        scaffold_code="def one(): pass",
        semantic_decisions=[
            SemanticArchitecturalDecision("OBL-01", "INTERFACE_CONTRACT", "one", "a.py"),
            SemanticArchitecturalDecision("OBL-02", "DATA_MODEL", "TwoModel", "b.py", fields=[{"name": "id", "type": "int"}])
        ]
    )
    b_ok, _, _ = validate_stage_b_preservation(frozen_a, assembly)
    assert b_ok is True
    
    plan, _ = convert_stage_b_to_semantic_plan(frozen_a, assembly)
    bp, _ = serialize_semantic_decision_to_blueprint(plan)
    assert bp is not None
    
    assert frozen_a.sha256_seal == seal_before


# ============================================================================
# Test T: Explicit Stage-A revision request
# ============================================================================
def test_t_explicit_stage_a_revision_request():
    mappings = [
        StageAObligationMapping("OBL-01", "OldFunc", "FUNCTION", "old_func_name", "main.py")
    ]
    frozen_a = FrozenStageAMappings.freeze(mappings)
    
    raw_b_with_revision = """
    === STAGE B: ARCHITECTURAL ASSEMBLY ===
    {
      "target_file": "main.py",
      "files": {"main.py": "pass"},
      "scaffold_code": "pass",
      "semantic_decisions": [],
      "stage_a_revision_requests": [
        {
          "obligation_id": "OBL-01",
          "reason": "Specification requires class-based service rather than top-level function",
          "requested_change": {
            "element_kind": "CLASS",
            "semantic_identity": "NewServiceClass"
          }
        }
      ]
    }
    === END STAGE B ===
    """
    assembly, _ = parse_stage_b_assembly(raw_b_with_revision)
    assert len(assembly.stage_a_revision_requests) == 1
    
    b_valid, reasons, rev_requests = validate_stage_b_preservation(frozen_a, assembly)
    assert b_valid is False
    assert len(rev_requests) == 1
    assert rev_requests[0].obligation_id == "OBL-01"
    assert "class-based service" in rev_requests[0].reason
    assert any("REVISION_REQUEST" in r for r in reasons)
