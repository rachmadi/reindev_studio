"""
Synthetic Test Suite for Architect Semantic Serializer v1 (Refined v1.1.0)
Treatment #1.8.5 — Universal Semantic Decision -> Deterministic Canonical Serialization v1

CORE PRINCIPLE:
"The serializer may translate representation; it may never infer architecture."

Tests A through R:
A. Callable obligation
B. Class/component obligation
C. Endpoint obligation
D. Data-model relationship
E. Multiple obligations
F. Parameters
G. Structured return
H. Missing optional information
I. Ambiguous semantic decision (rejection of undeclared or invalid target_structure)
J. Preservation during repair
K. One invalid decision among valid decisions
L. No obligation invention
M. No semantic information loss
N. Deterministic serialization
O. Serialization round-trip
P. Cross-domain fixture
Q. Malformed semantic decision
R. Serializer rejection of insufficient evidence (missing target_file or empty decisions)
"""

import pytest
from backend.semantic_serializer import (
    SemanticParameter,
    SemanticReturn,
    SemanticArchitecturalDecision,
    SemanticArchitecturalPlan,
    parse_semantic_architectural_plan,
    serialize_semantic_decision_to_blueprint,
    check_semantic_obligation_coverage,
    merge_preservative_semantic_decisions,
    extract_semantic_decision_json_text
)


def get_param_attr(param, attr_name):
    if isinstance(param, dict):
        return param.get(attr_name)
    return getattr(param, attr_name)


def get_ret_attr(ret, attr_name):
    if ret is None:
        return None
    if isinstance(ret, dict):
        return ret.get(attr_name)
    return getattr(ret, attr_name)


# ============================================================================
# Test A: Callable obligation
# ============================================================================
def test_a_callable_obligation():
    plan = SemanticArchitecturalPlan(
        target_file="main.py",
        scaffold_code="def calculate_total(amount: float) -> float:\n    return amount\n",
        semantic_decisions=[
            SemanticArchitecturalDecision(
                obligation_id="OBL-01",
                target_structure="INTERFACE_CONTRACT",
                identifier="calculate_total",
                target_file="main.py",
                parameters=[
                    SemanticParameter(name="amount", type="float", location="ARGUMENT", required=True)
                ],
                return_semantics=SemanticReturn(type="float")
            )
        ]
    )

    bp, errs = serialize_semantic_decision_to_blueprint(plan)
    assert errs == []
    assert bp is not None
    assert len(bp.interface_contracts) == 1
    ifc = bp.interface_contracts[0]
    assert ifc.identifier == "calculate_total"
    assert ifc.target_file == "main.py"
    assert len(ifc.parameters) == 1
    assert get_param_attr(ifc.parameters[0], "param_name") == "amount"
    assert get_param_attr(ifc.parameters[0], "param_type") == "float"
    assert get_param_attr(ifc.parameters[0], "param_location") == "ARGUMENT"
    assert get_ret_attr(ifc.expected_return, "return_type") == "float"


# ============================================================================
# Test B: Class/component obligation
# ============================================================================
def test_b_class_component_obligation():
    plan = SemanticArchitecturalPlan(
        target_file="lib/widget.dart",
        scaffold_code="class MetricCard extends StatelessWidget {}",
        semantic_decisions=[
            SemanticArchitecturalDecision(
                obligation_id="OBL-WIDGET-01",
                target_structure="INTERFACE_CONTRACT",
                identifier="MetricCard",
                target_file="lib/widget.dart",
                parameters=[
                    SemanticParameter(name="title", type="String", location="PROP", required=True),
                    SemanticParameter(name="value", type="double", location="PROP", required=False)
                ],
                return_semantics=SemanticReturn(type="Widget")
            )
        ]
    )

    bp, errs = serialize_semantic_decision_to_blueprint(plan)
    assert errs == []
    assert bp is not None
    assert len(bp.interface_contracts) == 1
    ifc = bp.interface_contracts[0]
    assert ifc.identifier == "MetricCard"
    assert ifc.target_file == "lib/widget.dart"
    assert len(ifc.parameters) == 2
    assert get_param_attr(ifc.parameters[0], "param_name") == "title"
    assert get_param_attr(ifc.parameters[0], "param_location") == "PROP"
    assert get_param_attr(ifc.parameters[1], "is_required") is False


# ============================================================================
# Test C: Endpoint obligation
# ============================================================================
def test_c_endpoint_obligation():
    plan = SemanticArchitecturalPlan(
        target_file="main.py",
        scaffold_code="from fastapi import FastAPI\napp = FastAPI()\n",
        semantic_decisions=[
            SemanticArchitecturalDecision(
                obligation_id="OBL-API-01",
                target_structure="INTERFACE_CONTRACT",
                identifier="create_item",
                target_file="main.py",
                route="/items",
                http_method="POST",
                parameters=[
                    SemanticParameter(name="item_payload", type="ItemSchema", location="BODY", required=True)
                ],
                return_semantics=SemanticReturn(type="ItemSchema", status_code=201, error_codes=[400, 422])
            )
        ]
    )

    bp, errs = serialize_semantic_decision_to_blueprint(plan)
    assert errs == []
    assert bp is not None
    assert len(bp.interface_contracts) == 1
    ifc = bp.interface_contracts[0]
    assert ifc.identifier == "create_item"
    assert ifc.route == "/items"
    assert ifc.method == "POST"
    assert len(ifc.parameters) == 1
    assert get_param_attr(ifc.parameters[0], "param_location") == "BODY"
    assert get_ret_attr(ifc.expected_return, "return_type") == "ItemSchema"
    assert get_ret_attr(ifc.expected_return, "status_code_success") == 201
    assert get_ret_attr(ifc.expected_return, "status_code_errors") == [400, 422]


# ============================================================================
# Test D: Data-model relationship
# ============================================================================
def test_d_data_model_relationship():
    plan = SemanticArchitecturalPlan(
        target_file="main.py",
        scaffold_code="class User: pass",
        semantic_decisions=[
            SemanticArchitecturalDecision(
                obligation_id="OBL-MODEL-01",
                target_structure="DATA_MODEL",
                identifier="User",
                target_file="main.py",
                fields=[
                    {"field_name": "id", "field_type": "int", "is_required": True},
                    {"field_name": "username", "field_type": "str", "is_required": True},
                    {"field_name": "email", "field_type": "str", "is_required": False}
                ]
            )
        ]
    )

    bp, errs = serialize_semantic_decision_to_blueprint(plan)
    assert errs == []
    assert bp is not None
    assert len(bp.data_models) == 1
    dm = bp.data_models[0]
    assert dm.model_name == "User"
    assert len(dm.fields) == 3
    assert dm.fields[0].field_name == "id"
    assert dm.fields[0].field_type == "int"
    assert dm.fields[0].is_required is True
    assert dm.fields[2].is_required is False


# ============================================================================
# Test E: Multiple obligations
# ============================================================================
def test_e_multiple_obligations():
    plan = SemanticArchitecturalPlan(
        target_file="main.py",
        scaffold_code="# multi obligations scaffold",
        semantic_decisions=[
            SemanticArchitecturalDecision(
                obligation_id="OBL-01",
                target_structure="DATA_MODEL",
                identifier="Product",
                fields=[{"name": "sku", "type": "str"}]
            ),
            SemanticArchitecturalDecision(
                obligation_id="OBL-02",
                target_structure="INTERFACE_CONTRACT",
                identifier="list_products",
                route="/products",
                http_method="GET"
            ),
            SemanticArchitecturalDecision(
                obligation_id="OBL-03",
                target_structure="INTERFACE_CONTRACT",
                identifier="get_product",
                route="/products/{sku}",
                http_method="GET",
                parameters=[SemanticParameter(name="sku", type="str", location="PATH")]
            )
        ]
    )

    bp, errs = serialize_semantic_decision_to_blueprint(plan)
    assert errs == []
    assert bp is not None
    assert len(bp.data_models) == 1
    assert len(bp.interface_contracts) == 2

    coverage = check_semantic_obligation_coverage(
        plan.semantic_decisions,
        [{"obligation_id": "OBL-01"}, {"obligation_id": "OBL-02"}, {"obligation_id": "OBL-03"}]
    )
    assert coverage["is_fully_covered"] is True
    assert coverage["coverage_ratio"] == 1.0


# ============================================================================
# Test F: Parameters
# ============================================================================
def test_f_parameters_mapping():
    plan = SemanticArchitecturalPlan(
        target_file="main.py",
        scaffold_code="def op(): pass",
        semantic_decisions=[
            SemanticArchitecturalDecision(
                obligation_id="OBL-PARAM",
                target_structure="INTERFACE_CONTRACT",
                identifier="complex_operation",
                parameters=[
                    SemanticParameter(name="arg1", type="int", location="ARGUMENT", required=True),
                    SemanticParameter(name="q", type="str", location="QUERY", required=False),
                    SemanticParameter(name="body_data", type="dict", location="BODY", required=True),
                    SemanticParameter(name="prop_val", type="bool", location="PROP", required=False)
                ]
            )
        ]
    )

    bp, errs = serialize_semantic_decision_to_blueprint(plan)
    assert errs == []
    assert bp is not None
    ifc = bp.interface_contracts[0]
    assert len(ifc.parameters) == 4
    assert [get_param_attr(p, "param_location") for p in ifc.parameters] == ["ARGUMENT", "QUERY", "BODY", "PROP"]
    assert [get_param_attr(p, "is_required") for p in ifc.parameters] == [True, False, True, False]


# ============================================================================
# Test G: Structured return
# ============================================================================
def test_g_structured_return_mapping():
    plan = SemanticArchitecturalPlan(
        target_file="main.py",
        scaffold_code="def endpoint(): pass",
        semantic_decisions=[
            SemanticArchitecturalDecision(
                obligation_id="OBL-RET",
                target_structure="INTERFACE_CONTRACT",
                identifier="endpoint",
                return_semantics=SemanticReturn(
                    type="List[Item]",
                    status_code=200,
                    error_codes=[401, 403, 500]
                )
            )
        ]
    )

    bp, errs = serialize_semantic_decision_to_blueprint(plan)
    assert errs == []
    assert bp is not None
    ret = bp.interface_contracts[0].expected_return
    assert get_ret_attr(ret, "return_type") == "List[Item]"
    assert get_ret_attr(ret, "status_code_success") == 200
    assert get_ret_attr(ret, "status_code_errors") == [401, 403, 500]


# ============================================================================
# Test H: Missing optional information
# ============================================================================
def test_h_missing_optional_info():
    # If route/method/parameters are missing for an interface, serializer must not fabricate them
    plan = SemanticArchitecturalPlan(
        target_file="main.py",
        scaffold_code="def run(): pass",
        semantic_decisions=[
            SemanticArchitecturalDecision(
                obligation_id="OBL-MINIMAL",
                target_structure="INTERFACE_CONTRACT",
                identifier="run"
            )
        ]
    )

    bp, errs = serialize_semantic_decision_to_blueprint(plan)
    assert errs == []
    assert bp is not None
    ifc = bp.interface_contracts[0]
    assert ifc.identifier == "run"
    assert ifc.route is None
    assert ifc.method is None
    assert ifc.parameters == []
    assert ifc.expected_return is None


# ============================================================================
# Test I: Ambiguous semantic decision (rejection of undeclared or invalid target_structure)
# ============================================================================
def test_i_ambiguous_semantic_decision():
    plan = SemanticArchitecturalPlan(
        target_file="main.py",
        scaffold_code="# test",
        semantic_decisions=[
            SemanticArchitecturalDecision(
                obligation_id="OBL-AMB",
                target_structure="TOTALLY_UNKNOWN_STRUCTURE",  # Invalid / Ambiguous
                identifier="something"
            )
        ]
    )

    bp, errs = serialize_semantic_decision_to_blueprint(plan)
    assert bp is None
    assert any("SERIALIZATION_INSUFFICIENT_EVIDENCE" in e and "TOTALLY_UNKNOWN_STRUCTURE" in e for e in errs)


# ============================================================================
# Test J: Preservation during repair
# ============================================================================
def test_j_preservation_during_repair():
    current_decisions = [
        SemanticArchitecturalDecision(
            obligation_id="OBL-01",
            target_structure="INTERFACE_CONTRACT",
            identifier="stable_func"
        ),
        SemanticArchitecturalDecision(
            obligation_id="OBL-02",
            target_structure="INTERFACE_CONTRACT",
            identifier="failing_func_v1"
        )
    ]

    repair_decisions = [
        SemanticArchitecturalDecision(
            obligation_id="OBL-02",
            target_structure="INTERFACE_CONTRACT",
            identifier="repaired_func_v2",
            parameters=[SemanticParameter(name="arg1", type="str")]
        )
    ]

    merged = merge_preservative_semantic_decisions(
        current_decisions=current_decisions,
        repair_decisions=repair_decisions,
        targeted_obligation_ids={"OBL-02"}
    )

    assert len(merged) == 2
    # OBL-01 preserved untouched
    assert merged[0].obligation_id == "OBL-01"
    assert merged[0].identifier == "stable_func"
    # OBL-02 updated to v2
    assert merged[1].obligation_id == "OBL-02"
    assert merged[1].identifier == "repaired_func_v2"
    assert len(merged[1].parameters) == 1


# ============================================================================
# Test K: One invalid decision among valid decisions
# ============================================================================
def test_k_one_invalid_decision_among_valid_decisions():
    plan = SemanticArchitecturalPlan(
        target_file="main.py",
        scaffold_code="# test",
        semantic_decisions=[
            SemanticArchitecturalDecision(
                obligation_id="OBL-VALID",
                target_structure="INTERFACE_CONTRACT",
                identifier="valid_op"
            ),
            SemanticArchitecturalDecision(
                obligation_id="OBL-INVALID",
                target_structure="INTERFACE_CONTRACT",
                identifier=""  # missing identifier
            )
        ]
    )

    bp, errs = serialize_semantic_decision_to_blueprint(plan)
    assert bp is None
    assert any("Missing identifier for obligation 'OBL-INVALID'" in e for e in errs)


# ============================================================================
# Test L: No obligation invention
# ============================================================================
def test_l_no_obligation_invention():
    plan = SemanticArchitecturalPlan(
        target_file="main.py",
        scaffold_code="# test",
        semantic_decisions=[
            SemanticArchitecturalDecision(
                obligation_id="OBL-EXACT",
                target_structure="INTERFACE_CONTRACT",
                identifier="exact_elem"
            )
        ]
    )

    bp, errs = serialize_semantic_decision_to_blueprint(plan)
    assert errs == []
    assert bp is not None
    # Serializer created exactly 1 interface contract for OBL-EXACT
    assert len(bp.interface_contracts) == 1
    assert bp.interface_contracts[0].identifier == "exact_elem"
    assert len(bp.data_models) == 0


# ============================================================================
# Test M: No semantic information loss
# ============================================================================
def test_m_no_semantic_information_loss():
    param = SemanticParameter(name="user_id", type="UUID", location="PATH", required=True, description="The user id")
    ret = SemanticReturn(type="UserResponse", status_code=200, error_codes=[404])
    decision = SemanticArchitecturalDecision(
        obligation_id="OBL-LOSSLESS",
        target_structure="INTERFACE_CONTRACT",
        identifier="fetch_user",
        target_file="app/api.py",
        parameters=[param],
        return_semantics=ret,
        route="/users/{user_id}",
        http_method="GET",
        description="Endpoint fetching user"
    )

    plan = SemanticArchitecturalPlan(
        target_file="app/api.py",
        scaffold_code="# code",
        semantic_decisions=[decision]
    )

    bp, errs = serialize_semantic_decision_to_blueprint(plan)
    assert errs == []
    assert bp is not None
    ifc = bp.interface_contracts[0]
    assert ifc.identifier == "fetch_user"
    assert ifc.target_file == "app/api.py"
    assert ifc.route == "/users/{user_id}"
    assert ifc.method == "GET"
    assert get_param_attr(ifc.parameters[0], "param_name") == "user_id"
    assert get_param_attr(ifc.parameters[0], "param_type") == "UUID"
    assert get_param_attr(ifc.parameters[0], "param_location") == "PATH"
    assert get_param_attr(ifc.parameters[0], "is_required") is True
    assert get_ret_attr(ifc.expected_return, "return_type") == "UserResponse"
    assert get_ret_attr(ifc.expected_return, "status_code_success") == 200
    assert get_ret_attr(ifc.expected_return, "status_code_errors") == [404]


# ============================================================================
# Test N: Deterministic serialization
# ============================================================================
def test_n_deterministic_serialization():
    plan = SemanticArchitecturalPlan(
        target_file="main.py",
        scaffold_code="def op(): pass",
        semantic_decisions=[
            SemanticArchitecturalDecision(
                obligation_id="OBL-1",
                target_structure="INTERFACE_CONTRACT",
                identifier="op_one",
                parameters=[SemanticParameter(name="p1", type="str")]
            ),
            SemanticArchitecturalDecision(
                obligation_id="OBL-2",
                target_structure="INTERFACE_CONTRACT",
                identifier="op_two",
                parameters=[SemanticParameter(name="p2", type="int")]
            )
        ]
    )

    bp1, errs1 = serialize_semantic_decision_to_blueprint(plan)
    bp2, errs2 = serialize_semantic_decision_to_blueprint(plan)

    assert errs1 == []
    assert errs2 == []
    assert bp1.model_dump() == bp2.model_dump()


# ============================================================================
# Test O: Serialization round-trip
# ============================================================================
def test_o_serialization_round_trip():
    raw_json = """=== SEMANTIC DECISION JSON ===
{
  "target_file": "main.py",
  "scaffold_code": "def run(): pass",
  "semantic_decisions": [
    {
      "obligation_id": "OBL-ROUNDTRIP",
      "target_structure": "INTERFACE_CONTRACT",
      "identifier": "run_process",
      "parameters": [
        {"name": "timeout", "type": "int", "location": "ARGUMENT", "required": false}
      ],
      "return_semantics": {
        "type": "bool"
      }
    }
  ]
}
=== END SEMANTIC DECISION JSON ==="""

    plan, parse_errs = parse_semantic_architectural_plan(raw_json)
    assert parse_errs == []
    assert plan is not None

    bp, ser_errs = serialize_semantic_decision_to_blueprint(plan)
    assert ser_errs == []
    assert bp is not None
    assert bp.interface_contracts[0].identifier == "run_process"
    assert get_param_attr(bp.interface_contracts[0].parameters[0], "param_name") == "timeout"
    assert get_param_attr(bp.interface_contracts[0].parameters[0], "is_required") is False


# ============================================================================
# Test P: Cross-domain fixture
# ============================================================================
def test_p_cross_domain_fixture():
    # Synthetic domain: Embedded Sensor Stream Driver (independent of web/cli/flutter)
    raw_json = """=== SEMANTIC DECISION JSON ===
{
  "target_file": "sensor_driver.py",
  "scaffold_code": "class SensorPacket: pass\\nclass StreamDriver: pass",
  "semantic_decisions": [
    {
      "obligation_id": "OBL-SENSOR-01",
      "target_structure": "DATA_MODEL",
      "identifier": "SensorPacket",
      "fields": [
        {"field_name": "timestamp_ns", "field_type": "int", "is_required": true},
        {"field_name": "voltage_mv", "field_type": "float", "is_required": true}
      ]
    },
    {
      "obligation_id": "OBL-SENSOR-02",
      "target_structure": "INTERFACE_CONTRACT",
      "identifier": "read_telemetry_frame",
      "parameters": [
        {"name": "bus_channel", "type": "int", "location": "ARGUMENT", "required": true}
      ],
      "return_semantics": {
        "type": "SensorPacket"
      }
    }
  ]
}
=== END SEMANTIC DECISION JSON ==="""

    plan, errs = parse_semantic_architectural_plan(raw_json)
    assert errs == []
    assert plan is not None

    bp, ser_errs = serialize_semantic_decision_to_blueprint(plan)
    assert ser_errs == []
    assert bp is not None
    assert len(bp.data_models) == 1
    assert bp.data_models[0].model_name == "SensorPacket"
    assert len(bp.interface_contracts) == 1
    assert bp.interface_contracts[0].identifier == "read_telemetry_frame"


# ============================================================================
# Test Q: Malformed semantic decision
# ============================================================================
def test_q_malformed_semantic_decision():
    malformed_json = """=== SEMANTIC DECISION JSON ===
{
  "semantic_decisions": [
    {"broken_json": "missing closing brace"
=== END SEMANTIC DECISION JSON ==="""

    plan, errs = parse_semantic_architectural_plan(malformed_json)
    assert plan is None
    assert any("SEMANTIC_PARSE_ERROR" in e for e in errs)


# ============================================================================
# Test R: Serializer rejection of insufficient evidence (Anti-Solver)
# ============================================================================
def test_r_rejection_of_insufficient_evidence():
    # 1. Missing target artifact completely (no default_target_file allowed)
    plan_no_target = SemanticArchitecturalPlan(
        target_file="",
        semantic_decisions=[
            SemanticArchitecturalDecision(
                obligation_id="OBL-01",
                target_structure="INTERFACE_CONTRACT",
                identifier="func",
                target_file=""
            )
        ]
    )
    bp1, errs1 = serialize_semantic_decision_to_blueprint(plan_no_target)
    assert bp1 is None
    assert any("Missing authoritative target file" in e for e in errs1)

    # 2. Empty decisions provided
    plan_empty = SemanticArchitecturalPlan(
        target_file="main.py",
        semantic_decisions=[]
    )
    bp2, errs2 = serialize_semantic_decision_to_blueprint(plan_empty)
    assert bp2 is None
    assert any("No semantic architectural decisions provided" in e for e in errs2)
