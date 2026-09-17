"""
Test Suite for Treatment #1.8.4: Universal Canonical Contract Grounding v1.
Validates Properties A through O using pure synthetic cross-domain fixtures:

- Test A: Callable obligation grounding (pure callable -> canonical InterfaceContract representation)
- Test B: Class/component obligation grounding (constructible component -> canonical DataModel/Interface)
- Test C: Endpoint obligation grounding (route, method, target_file -> canonical InterfaceContract)
- Test D: Data-model obligation grounding (entity fields, types -> canonical BlueprintDataModel)
- Test E: Multiple obligations simultaneous representation (multi-obligation ledger coverage)
- Test F: Nested parameters representation (param_name, param_type, param_location, is_required)
- Test G: Structured return representation (return_type, status_code_success)
- Test H: Missing optional information handling without hallucination
- Test I: Ambiguous obligation handling (preservation of unresolved boundaries)
- Test J: Preservation during repair (CURRENT VALID STATE retained)
- Test K: Isolated invalid contract repair (single invalid contract fixed without mutating valid contracts)
- Test L: Strict evidence boundary (zero phantom / invented obligations)
- Test M: Lossless serialization round-trip (Pydantic parsing fidelity)
- Test N: Canonical schema equivalence between ArchitecturalBlueprint and MachineReadableContract
- Test O: Cross-domain synthetic independence (Compiler IR pass vs Audio DSP node)
"""

import json
import pytest
from typing import Dict, Any, List

from backend.blueprint_schema import (
    ArchitecturalBlueprint,
    BlueprintInterfaceContract,
    BlueprintFileModule,
    BlueprintDataModel,
    BlueprintModelField,
    parse_blueprint_json,
)
from backend.contract import (
    MachineReadableContract,
    InterfaceContract,
    InterfaceParameter,
    ExpectedReturn,
    DataModel,
    ModelField,
    complete_aligned_contract,
    create_draft_contract,
)
from backend.context_hardening import (
    format_canonical_blueprint_schema_constraints,
    distill_canonical_schema_semantic,
    build_architect_repair_context,
    build_architect_decision_context,
)
from backend.canonical_obligation import (
    CanonicalObligation,
    ObligationKind,
    check_obligation_coverage,
    CoverageStatus,
)


# ---------------------------------------------------------------------------
# Test A: Callable Obligation Grounding
# ---------------------------------------------------------------------------
def test_test_a_callable_obligation_grounding():
    """Test A: Callable obligation is accurately grounded into a canonical InterfaceContract."""
    ob = CanonicalObligation(
        obligation_id="OBL-CALL-01",
        obligation_kind=ObligationKind.CALLABLE_INTERFACE.value,
        public_identity="compute_hash",
        source_reference="test_crypto.py",
        positional_arguments=1,
        keyword_arguments=["algorithm"],
    )
    ifc_dict = {
        "interface_id": "IFC-01",
        "interface_type": "FUNCTION",
        "identifier": "compute_hash",
        "target_file": "crypto_module.py",
        "parameters": [
            {"param_name": "payload", "param_type": "bytes", "param_location": "ARGUMENT", "is_required": True},
            {"param_name": "algorithm", "param_type": "str", "param_location": "ARGUMENT", "is_required": False},
        ],
        "expected_return": {"return_type": "str"}
    }
    ifc = InterfaceContract.model_validate(ifc_dict)
    assert ifc.identifier == "compute_hash"
    assert len(ifc.parameters) == 2
    assert ifc.parameters[0].param_name == "payload"
    assert ifc.expected_return.return_type == "str"

    contract_obj = MachineReadableContract(
        contract_id="test_contract_a",
        interface_contracts=[ifc],
    )
    cov = check_obligation_coverage([ob], contract_obj)
    assert cov.covered_count == 1
    assert cov.missing_count == 0


# ---------------------------------------------------------------------------
# Test B: Class / Component Obligation Grounding
# ---------------------------------------------------------------------------
def test_test_b_class_component_obligation_grounding():
    """Test B: Class/constructible component obligation is grounded into DataModel or Interface."""
    ob = CanonicalObligation(
        obligation_id="OBL-CLS-01",
        obligation_kind=ObligationKind.DATA_MODEL.value,
        public_identity="AudioBuffer",
        source_reference="test_dsp.py",
    )
    dm = DataModel(
        model_name="AudioBuffer",
        target_file="dsp_engine.py",
        fields=[
            ModelField(field_name="sample_rate", field_type="int", is_required=True),
            ModelField(field_name="channels", field_type="int", is_required=True),
        ]
    )
    contract_obj = MachineReadableContract(
        contract_id="test_contract_b",
        data_models=[dm],
    )
    cov = check_obligation_coverage([ob], contract_obj)
    assert cov.covered_count == 1
    assert cov.missing_count == 0


# ---------------------------------------------------------------------------
# Test C: Endpoint Obligation Grounding
# ---------------------------------------------------------------------------
def test_test_c_endpoint_obligation_grounding():
    """Test C: Endpoint obligation maps route, method, parameters, and expected_return."""
    ob = CanonicalObligation(
        obligation_id="OBL-EP-01",
        obligation_kind=ObligationKind.INTERACTION.value,
        public_identity="/api/v1/sensors",
        source_reference="test_telemetry.py",
        inputs={"http_method": "POST", "route": "/api/v1/sensors"}
    )
    ifc = InterfaceContract(
        interface_id="IFC-01",
        interface_type="HTTP_ENDPOINT",
        identifier="register_sensor",
        route="/api/v1/sensors",
        http_method="POST",
        target_file="sensor_service.py",
        parameters=[
            InterfaceParameter(param_name="sensor_data", param_type="dict", param_location="BODY", is_required=True)
        ],
        expected_return=ExpectedReturn(return_type="dict", status_code_success=201)
    )
    contract_obj = MachineReadableContract(
        contract_id="test_contract_c",
        interface_contracts=[ifc]
    )
    cov = check_obligation_coverage([ob], contract_obj)
    assert cov.covered_count == 1
    assert cov.missing_count == 0


# ---------------------------------------------------------------------------
# Test D: Data-Model Obligation Grounding
# ---------------------------------------------------------------------------
def test_test_d_data_model_obligation_grounding():
    """Test D: Data-model entity with fields and types conforms to BlueprintDataModel."""
    bpm = BlueprintDataModel(
        model_name="MetricRecord",
        target_file="metrics.py",
        fields=[
            BlueprintModelField(field_name="timestamp", field_type="int", is_required=True),
            BlueprintModelField(field_name="value", field_type="float", is_required=True),
        ]
    )
    dumped = bpm.model_dump()
    assert dumped["model_name"] == "MetricRecord"
    assert len(dumped["fields"]) == 2
    assert dumped["fields"][0]["field_name"] == "timestamp"


# ---------------------------------------------------------------------------
# Test E: Multiple Obligations Simultaneous Representation
# ---------------------------------------------------------------------------
def test_test_e_multiple_obligations_simultaneous_representation():
    """Test E: Multiple distinct obligations (endpoints, models, callables) covered simultaneously."""
    obs = [
        CanonicalObligation(
            obligation_id="OBL-01",
            obligation_kind=ObligationKind.INTERACTION.value,
            public_identity="/telemetry",
            source_reference="test_suite.py",
            inputs={"http_method": "GET", "route": "/telemetry"}
        ),
        CanonicalObligation(
            obligation_id="OBL-02",
            obligation_kind=ObligationKind.DATA_MODEL.value,
            public_identity="TelemetryPacket",
            source_reference="test_suite.py",
        ),
        CanonicalObligation(
            obligation_id="OBL-03",
            obligation_kind=ObligationKind.CALLABLE_INTERFACE.value,
            public_identity="parse_telemetry",
            source_reference="test_suite.py",
        ),
    ]

    contract_obj = MachineReadableContract(
        contract_id="test_contract_e",
        interface_contracts=[
            InterfaceContract(
                interface_id="IFC-01",
                interface_type="HTTP_ENDPOINT",
                identifier="get_telemetry",
                route="/telemetry",
                http_method="GET",
                target_file="telemetry_api.py",
            ),
            InterfaceContract(
                interface_id="IFC-02",
                interface_type="FUNCTION",
                identifier="parse_telemetry",
                target_file="telemetry_api.py",
            ),
        ],
        data_models=[
            DataModel(
                model_name="TelemetryPacket",
                target_file="telemetry_api.py",
                fields=[ModelField(field_name="raw_bytes", field_type="bytes", is_required=True)]
            )
        ]
    )

    cov = check_obligation_coverage(obs, contract_obj)
    assert cov.is_fully_covered is True
    assert cov.covered_count == 3
    assert cov.missing_count == 0


# ---------------------------------------------------------------------------
# Test F: Nested Parameters Representation (Canonical Fields)
# ---------------------------------------------------------------------------
def test_test_f_nested_parameters_canonical_fields():
    """Test F: Parameters strictly validate canonical field names (param_name, param_type, param_location)."""
    valid_param = {
        "param_name": "config_payload",
        "param_type": "str",
        "param_location": "BODY",
        "is_required": True,
    }
    p = InterfaceParameter.model_validate(valid_param)
    assert p.param_name == "config_payload"
    assert p.param_location == "BODY"

    # Non-canonical field names ('name', 'type') must be rejected by Pydantic validation
    invalid_param = {"name": "config_payload", "type": "str"}
    with pytest.raises(Exception):
        InterfaceParameter.model_validate(invalid_param)

    # Invalid location must be rejected
    with pytest.raises(Exception):
        InterfaceParameter.model_validate({
            "param_name": "x",
            "param_type": "int",
            "param_location": "INVALID_LOCATION",
        })


# ---------------------------------------------------------------------------
# Test G: Structured Return Representation
# ---------------------------------------------------------------------------
def test_test_g_structured_return_representation():
    """Test G: expected_return strictly validates structured object with return_type."""
    valid_ret = {"return_type": "ProcessedStream", "status_code_success": 200}
    ret = ExpectedReturn.model_validate(valid_ret)
    assert ret.return_type == "ProcessedStream"
    assert ret.status_code_success == 200

    # Bare string must be rejected by ExpectedReturn validation
    with pytest.raises(Exception):
        ExpectedReturn.model_validate("ProcessedStream")


# ---------------------------------------------------------------------------
# Test H: Missing Optional Information Handled Without Hallucination
# ---------------------------------------------------------------------------
def test_test_h_missing_optional_information_without_hallucination():
    """Test H: Missing optional fields (status_code, parameters) default cleanly without guessing."""
    ifc = InterfaceContract(
        interface_id="IFC-MIN",
        interface_type="FUNCTION",
        identifier="simple_filter",
        target_file="filter.py",
    )
    assert ifc.parameters == []
    assert ifc.expected_return is None
    assert ifc.route is None
    assert ifc.http_method is None


# ---------------------------------------------------------------------------
# Test I: Ambiguous Obligation Handling
# ---------------------------------------------------------------------------
def test_test_i_ambiguous_obligation_handling():
    """Test I: Ambiguities preserved in unresolved_ambiguities without false certainty."""
    draft = create_draft_contract(
        raw_intent="Process sensor data with optional compression.",
        target_language="python",
    )
    ambiguity = {
        "ambiguity_id": "AMB-01",
        "description": "Compression codec not specified",
        "resolution_strategy": "DEFER_TO_DEVELOPER",
        "assumptions": ["Default to gzip if unspecified"]
    }
    aligned = complete_aligned_contract(
        draft_dict=draft,
        data_models=[],
        interface_contracts=[{
            "interface_id": "IFC-01",
            "interface_type": "FUNCTION",
            "identifier": "process_sensor_data",
            "target_file": "main.py",
        }],
        testable_assertions=[],
        ambiguities=[ambiguity]
    )
    assert len(aligned["unresolved_ambiguities"]) == 1
    assert aligned["unresolved_ambiguities"][0]["ambiguity_id"] == "AMB-01"


# ---------------------------------------------------------------------------
# Test J: Preservation During Repair (CURRENT VALID STATE Retained)
# ---------------------------------------------------------------------------
def test_test_j_preservation_during_repair():
    """Test J: Valid existing contracts are preserved across repair turns."""
    existing_ifcs = [
        {"identifier": "existing_op_1", "target_file": "main.py"},
        {"identifier": "existing_op_2", "target_file": "main.py"},
    ]
    repair_state = {
        "task": "Synthetic task",
        "contract_revision_count": 1,
        "contract": {
            "task_intent": {"authoritative_target_file": "main.py"},
            "file_tree": ["main.py"],
            "interface_contracts": existing_ifcs,
            "data_models": [{"model_name": "StateModel"}]
        },
        "architectural_blueprint": {
            "authoritative_target_file": "main.py",
            "file_tree": ["main.py"],
            "files": {"main.py": {"code_scaffold": "def existing_op_1(): pass\ndef existing_op_2(): pass\n"}},
            "interface_contracts": existing_ifcs,
            "data_models": [{"model_name": "StateModel"}]
        },
        "contract_validation_errors": ["MISSING: OBL-03 (new_operation)"]
    }
    ctx, telem = build_architect_repair_context(repair_state)
    assert "existing_op_1" in ctx
    assert "existing_op_2" in ctx
    assert "StateModel" in ctx
    assert "CURRENT VALID STATE + REPAIRED ELEMENT" in ctx


# ---------------------------------------------------------------------------
# Test K: Isolated Invalid Contract Repair
# ---------------------------------------------------------------------------
def test_test_k_isolated_invalid_contract_repair():
    """Test K: Correcting one invalid contract preserves other valid contracts."""
    valid_c1 = BlueprintInterfaceContract(identifier="valid_one", target_file="module.py")
    valid_c2 = BlueprintInterfaceContract(identifier="valid_two", target_file="module.py")
    repaired_c3 = BlueprintInterfaceContract(identifier="repaired_three", target_file="module.py")

    bp = ArchitecturalBlueprint(
        authoritative_target_file="module.py",
        file_tree=["module.py"],
        architecture_summary="Isolated repair summary",
        files={"module.py": BlueprintFileModule(file_path="module.py", code_scaffold="class Module: pass")},
        interface_contracts=[valid_c1, valid_c2, repaired_c3]
    )
    assert len(bp.interface_contracts) == 3
    assert bp.interface_contracts[0].identifier == "valid_one"
    assert bp.interface_contracts[1].identifier == "valid_two"
    assert bp.interface_contracts[2].identifier == "repaired_three"


# ---------------------------------------------------------------------------
# Test L: Strict Evidence Boundary (No Obligation Invention)
# ---------------------------------------------------------------------------
def test_test_l_strict_evidence_boundary():
    """Test L: Context constraints forbid semantic invention of ungrounded obligations."""
    constraints = format_canonical_blueprint_schema_constraints()
    assert "Stage A (Semantic Mapping)" in constraints
    assert "Stage B (Canonical Serialization)" in constraints
    assert "Obligation Coverage Rule:" in constraints

    distilled = distill_canonical_schema_semantic()
    assert "Obligation Coverage:" in distilled
    assert "Two-Stage Synthesis:" in distilled


# ---------------------------------------------------------------------------
# Test M: Lossless Serialization Round-Trip
# ---------------------------------------------------------------------------
def test_test_m_lossless_serialization_round_trip():
    """Test M: ArchitecturalBlueprint serialized to JSON string parses back losslessly."""
    bp_dict = {
        "authoritative_target_file": "core_engine.py",
        "file_tree": ["core_engine.py"],
        "architecture_summary": "Modular core engine",
        "files": {
            "core_engine.py": {
                "module_role": "Core",
                "imports": ["import sys"],
                "code_scaffold": "def execute_pipeline(): pass\n"
            }
        },
        "interface_contracts": [
            {
                "identifier": "execute_pipeline",
                "target_file": "core_engine.py",
                "parameters": [
                    {"param_name": "config", "param_type": "dict", "param_location": "ARGUMENT", "is_required": True}
                ],
                "expected_return": {"return_type": "int"}
            }
        ],
        "data_models": []
    }
    json_str = json.dumps(bp_dict)
    bp, err = parse_blueprint_json(json_str)
    assert err is None
    assert bp is not None
    assert bp.authoritative_target_file == "core_engine.py"
    assert len(bp.interface_contracts) == 1
    assert bp.interface_contracts[0].identifier == "execute_pipeline"


# ---------------------------------------------------------------------------
# Test N: Canonical Schema Equivalence
# ---------------------------------------------------------------------------
def test_test_n_canonical_schema_equivalence():
    """Test N: Schema constraints introspect InterfaceParameter & ExpectedReturn correctly."""
    constraints = format_canonical_blueprint_schema_constraints()
    assert "Parameter Schema for elements in 'parameters'" in constraints
    assert "ExpectedReturn Schema for 'expected_return'" in constraints
    assert "param_name" in constraints
    assert "param_type" in constraints
    assert "param_location" in constraints
    assert "return_type" in constraints
    assert "VALID:" in constraints
    assert "INVALID:" in constraints


# ---------------------------------------------------------------------------
# Test O: Cross-Domain Synthetic Independence
# ---------------------------------------------------------------------------
def test_test_o_cross_domain_synthetic_independence():
    """Test O: Verifies canonical contract grounding on Compiler IR & Audio DSP domains."""
    # Domain 1: Compiler IR Optimization Pass
    ir_ob = CanonicalObligation(
        obligation_id="OBL-IR-01",
        obligation_kind=ObligationKind.CALLABLE_INTERFACE.value,
        public_identity="optimize_ir_graph",
        source_reference="test_compiler.py",
    )
    ir_ifc = InterfaceContract(
        interface_id="IFC-IR-01",
        interface_type="FUNCTION",
        identifier="optimize_ir_graph",
        target_file="ir_pass.py",
        parameters=[
            InterfaceParameter(param_name="graph", param_type="IRGraph", param_location="ARGUMENT", is_required=True),
        ],
        expected_return=ExpectedReturn(return_type="IRGraph")
    )
    contract_ir = MachineReadableContract(
        contract_id="contract_compiler_ir",
        interface_contracts=[ir_ifc]
    )
    cov_ir = check_obligation_coverage([ir_ob], contract_ir)
    assert cov_ir.is_fully_covered is True

    # Domain 2: Audio DSP Node
    dsp_ob = CanonicalObligation(
        obligation_id="OBL-DSP-01",
        obligation_kind=ObligationKind.DATA_MODEL.value,
        public_identity="BiquadFilterNode",
        source_reference="test_audio.py",
    )
    dsp_model = DataModel(
        model_name="BiquadFilterNode",
        target_file="audio_graph.py",
        fields=[
            ModelField(field_name="cutoff_hz", field_type="float", is_required=True),
            ModelField(field_name="q_factor", field_type="float", is_required=True),
        ]
    )
    contract_dsp = MachineReadableContract(
        contract_id="contract_audio_dsp",
        data_models=[dsp_model]
    )
    cov_dsp = check_obligation_coverage([dsp_ob], contract_dsp)
    assert cov_dsp.is_fully_covered is True
