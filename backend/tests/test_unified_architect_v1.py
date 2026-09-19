"""
Deterministic Unit Test Suite: Unified Blueprint Architecture v1
ReinDev Studio — Iterasi 6 (Architect Recovery)

Verifies:
- Test 1: Single LLM Call Invariant (Normal Architect invocation makes strictly 1 LLM call).
- Test 2: Direct Canonical Blueprint JSON Extraction & Validation.
- Test 3: Minimal Scaffold Policy (stubs with pass, signatures, <= 800 chars).
- Test 4: Elimination of Stage Delimiters (no === STAGE A ===, passes document boundary).
- Test 5: Unified Repair Preservation (valid state preserved, error evidence communicated).
- Test 6: Performance Telemetry Completeness (call count, tokens, wall time, status).
- Test 7: Static Anti-Solver & Representation Invariants.
"""

import json
import pytest
from langchain_core.messages import AIMessage

from backend.agents.architect import architect_agent, ARCHITECT_SYSTEM_PROMPT
from backend.blueprint_schema import (
    ArchitecturalBlueprint,
    parse_blueprint_json,
    serialize_blueprint_to_canonical_json,
    validate_canonical_architecture_plan_state
)


class CountingMockLLM:
    """Mock LLM tracking invocation count and returning synthetic canonical blueprint."""
    def __init__(self, response_content: str = None):
        self.call_count = 0
        self.recorded_messages = []
        self.default_content = response_content or (
            "=== BLUEPRINT JSON ===\n"
            "{\n"
            '  "authoritative_target_file": "main.py",\n'
            '  "file_tree": ["main.py"],\n'
            '  "architecture_summary": "Unified modular architecture blueprint",\n'
            '  "files": {\n'
            '    "main.py": {\n'
            '      "module_role": "Authoritative Single Module",\n'
            '      "imports": [],\n'
            '      "code_scaffold": "class Calculator:\\n    def add(self, a: float, b: float) -> float:\\n        pass\\n"\n'
            '    }\n'
            '  },\n'
            '  "interface_contracts": [\n'
            '    {\n'
            '      "identifier": "add",\n'
            '      "target_file": "main.py",\n'
            '      "parameters": [\n'
            '        {"param_name": "a", "param_type": "float", "param_location": "ARGUMENT", "is_required": true},\n'
            '        {"param_name": "b", "param_type": "float", "param_location": "ARGUMENT", "is_required": true}\n'
            '      ],\n'
            '      "expected_return": {"return_type": "float"}\n'
            '    }\n'
            '  ],\n'
            '  "data_models": [\n'
            '    {\n'
            '      "model_name": "Calculator",\n'
            '      "target_file": "main.py",\n'
            '      "fields": []\n'
            '    }\n'
            '  ]\n'
            "}\n"
            "=== END BLUEPRINT JSON ==="
        )

    def invoke(self, messages):
        self.call_count += 1
        self.recorded_messages.append(messages)
        return AIMessage(content=self.default_content)


def test_01_single_llm_call_invariant():
    """Normal Architect attempt #0 must execute strictly 1 LLM call."""
    mock_llm = CountingMockLLM()
    mock_state = {
        "task": "Build a matrix calculator CLI",
        "target_language": "python",
        "specifications": "Provide matrix addition and subtraction",
        "run_id": "test_single_call",
        "contract_revision_count": 0,
        "logs": []
    }

    res = architect_agent(mock_state, llm=mock_llm)

    assert mock_llm.call_count == 1, (
        f"Expected strictly 1 LLM call for normal Architect invocation, observed: {mock_llm.call_count}"
    )
    assert res["architect_telemetry"]["llm_call_count"] == 1


def test_02_canonical_blueprint_generation():
    """Output must parse cleanly into ArchitecturalBlueprint and yield valid canonical JSON."""
    mock_llm = CountingMockLLM()
    mock_state = {
        "task": "Build a matrix calculator CLI",
        "target_language": "python",
        "specifications": "Provide matrix addition and subtraction",
        "run_id": "test_bp_gen",
        "contract_revision_count": 0,
        "logs": []
    }

    res = architect_agent(mock_state, llm=mock_llm)

    # architecture_plan must be valid JSON string
    plan_str = res["architecture_plan"]
    assert isinstance(plan_str, str)
    decoded = json.loads(plan_str)
    assert decoded["authoritative_target_file"] == "main.py"
    assert "main.py" in decoded["file_tree"]
    assert "main.py" in decoded["files"]

    # architectural_blueprint in state must be dictionary conforming to schema
    bp_dict = res["architectural_blueprint"]
    assert bp_dict is not None
    assert isinstance(bp_dict, dict)
    parsed_bp = ArchitecturalBlueprint.model_validate(bp_dict)
    assert parsed_bp.authoritative_target_file == "main.py"


def test_03_minimal_scaffold_policy():
    """Scaffolds must contain signatures and minimal stubs (pass), under 800 chars."""
    mock_llm = CountingMockLLM()
    mock_state = {
        "task": "Build a matrix calculator CLI",
        "target_language": "python",
        "specifications": "Provide matrix addition",
        "run_id": "test_scaff_policy",
        "contract_revision_count": 0,
        "logs": []
    }

    res = architect_agent(mock_state, llm=mock_llm)
    bp_dict = res["architectural_blueprint"]

    for file_path, file_mod in bp_dict["files"].items():
        scaff = file_mod.get("code_scaffold", "")
        assert "pass" in scaff, f"Scaffold for {file_path} should contain minimal stub ('pass')"
        assert len(scaff) <= 800, (
            f"Scaffold for {file_path} exceeded 800 characters: {len(scaff)}"
        )


def test_04_elimination_of_stage_delimiters():
    """Output must contain zero stage delimiters and pass document-boundary validation."""
    mock_llm = CountingMockLLM()
    mock_state = {
        "task": "Build a matrix calculator CLI",
        "target_language": "python",
        "specifications": "Provide matrix addition",
        "run_id": "test_no_delimiters",
        "contract_revision_count": 0,
        "logs": []
    }

    res = architect_agent(mock_state, llm=mock_llm)
    arch_plan = res["architecture_plan"]

    # Must NOT contain stage delimiters
    for forbidden in ["=== STAGE A", "=== STAGE B", "=== STAGE B-1", "=== STAGE B-2"]:
        assert forbidden not in arch_plan

    # Must pass canonical document-boundary validation
    parsed_bp = ArchitecturalBlueprint.model_validate(res["architectural_blueprint"])
    is_valid, errs = validate_canonical_architecture_plan_state(
        architecture_plan=arch_plan,
        canonical_blueprint=parsed_bp,
        contract=res["contract"]
    )
    assert is_valid is True, f"Canonical architecture plan validation failed: {errs}"


def test_05_unified_repair_preservation():
    """Repair turn must preserve valid state and report structured errors if invalid."""
    invalid_content = "Not a valid json response"
    mock_llm = CountingMockLLM(response_content=invalid_content)
    mock_state = {
        "task": "Build a matrix calculator CLI",
        "target_language": "python",
        "specifications": "Provide matrix addition",
        "run_id": "test_repair_pres",
        "contract_revision_count": 1,
        "contract_feedback": "Previous contract had parse error",
        "logs": []
    }

    res = architect_agent(mock_state, llm=mock_llm)

    assert mock_llm.call_count == 1
    assert res["contract_status"] == "REJECTED"
    assert len(res["contract_validation_errors"]) > 0
    assert "SCHEMA_VIOLATION" in res["contract_validation_errors"][0]


def test_06_performance_telemetry_completeness():
    """Telemetry must record all required performance invariants."""
    mock_llm = CountingMockLLM()
    mock_state = {
        "task": "Build a matrix calculator CLI",
        "target_language": "python",
        "specifications": "Provide matrix addition",
        "run_id": "test_telem",
        "contract_revision_count": 0,
        "model_name": "qwen2.5-coder:7b",
        "num_ctx": 8192,
        "logs": []
    }

    res = architect_agent(mock_state, llm=mock_llm)
    telem = res["architect_telemetry"]

    assert "llm_call_count" in telem and telem["llm_call_count"] == 1
    assert "wall_time" in telem and telem["wall_time"] >= 0.0
    assert "input_chars" in telem and telem["input_chars"] > 0
    assert "estimated_input_tokens" in telem and telem["estimated_input_tokens"] > 0
    assert "output_chars" in telem and telem["output_chars"] > 0
    assert "estimated_output_tokens" in telem and telem["estimated_output_tokens"] > 0
    assert "model" in telem and telem["model"] == "qwen2.5-coder:7b"
    assert "num_ctx" in telem and telem["num_ctx"] == 8192
    assert "delivery_valid" in telem and telem["delivery_valid"] is True
    assert "contract_status" in telem


def test_07_static_anti_solver_invariants():
    """System prompt and logic must remain universal, framework-agnostic, and non-prescriptive."""
    assert "OBSERVABLE BEHAVIOR" in ARCHITECT_SYSTEM_PROMPT
    assert "Do not prescribe implementation-specific mechanisms" in ARCHITECT_SYSTEM_PROMPT
    assert "ARTIFACT PURITY" in ARCHITECT_SYSTEM_PROMPT

    # Zero solver contamination tokens in ARCHITECT_SYSTEM_PROMPT
    banned_domain_tokens = ["class Product", "/products", "price", "stock", "Matrix", "MetricData", "CardMetric"]
    for token in banned_domain_tokens:
        assert token not in ARCHITECT_SYSTEM_PROMPT, f"Contamination token '{token}' in ARCHITECT_SYSTEM_PROMPT"


def test_08_parameter_location_and_interface_normalization():
    """Verify that non-canonical parameter locations ('SELF', 'KEYWORD') and raw return types are normalized safely."""
    from backend.agents.architect import _normalize_interface_contract_dict
    from backend.contract import InterfaceContract

    raw_python_ifc = {
        "identifier": "multiply",
        "parameters": [
            {"param_name": "self", "param_type": "Matrix", "param_location": "SELF"},
            {"param_name": "other", "param_type": "Matrix", "param_location": "KEYWORD", "is_required": True}
        ],
        "expected_return": "Matrix"
    }
    norm_py = _normalize_interface_contract_dict(raw_python_ifc, 1, is_dart=False, primary_file="main.py")
    # 'self' must be stripped for Python methods
    assert len(norm_py["parameters"]) == 1
    assert norm_py["parameters"][0]["param_name"] == "other"
    assert norm_py["parameters"][0]["param_location"] == "ARGUMENT"
    # string expected_return normalized to dict
    assert norm_py["expected_return"] == {"return_type": "Matrix"}
    # Pydantic InterfaceContract validation must pass cleanly
    pydantic_ifc = InterfaceContract.model_validate(norm_py)
    assert pydantic_ifc.parameters[0].param_location == "ARGUMENT"

    raw_dart_ifc = {
        "identifier": "CardMetric",
        "interface_type": "WIDGET",
        "parameters": [
            {"param_name": "data", "param_type": "MetricData", "param_location": "KEYWORD"}
        ]
    }
    norm_dart = _normalize_interface_contract_dict(raw_dart_ifc, 2, is_dart=True, primary_file="lib/card_metric.dart")
    assert norm_dart["parameters"][0]["param_location"] == "PROP"
    assert norm_dart["expected_return"] == {"return_type": "Widget"}
    pydantic_dart_ifc = InterfaceContract.model_validate(norm_dart)
    assert pydantic_dart_ifc.parameters[0].param_location == "PROP"


def test_09_multi_candidate_scenario_compatibility():
    """Verify that evaluate_scaffold_scenario_compatibility evaluates all candidate facts for multi-target adapters."""
    from backend.canonical_scenario import CanonicalScenario, ScenarioKind, evaluate_scaffold_scenario_compatibility, ScaffoldCompatibilityStatus

    sc_neg = CanonicalScenario(
        scenario_id="SCN-NEG-TEST",
        scenario_kind=ScenarioKind.NEGATIVE.value,
        stimulus="_add(a, b)",
        caller="test_addition_incompatible",
        expected_outcome={"raises": "ValueError"},
        expected_exception="ValueError",
        is_harness_adapter=True,
        adapter_target_symbols=["add_matrices", "Matrix"]
    )

    # When Matrix is defined before add_matrices in the scaffold, add_matrices must still be evaluated
    code = """
class Matrix:
    def __init__(self, data: list = None):
        self.data = data or []

def add_matrices(a: list, b: list) -> list:
    if len(a) != len(b):
        raise ValueError("Incompatible dimensions")
    return []
"""
    matrix = evaluate_scaffold_scenario_compatibility([sc_neg], {"main.py": code})
    assert matrix.is_fully_compatible is True
    assert matrix.items[0].compatibility == ScaffoldCompatibilityStatus.COMPATIBLE.value
    assert "add_matrices" in matrix.items[0].evidence


def test_10_prompt_context_authority_structure(tmp_path):
    """Verify Turn 0 prompt structure conforms strictly to 5-section authority order and has no redundant blocks."""
    test_file = tmp_path / "test_calc.py"
    test_file.write_text(
        "def test_calc_add():\n"
        "    calc = Calculator()\n"
        "    res = calc.add(2, 3)\n"
        "    assert res == 5\n"
    )

    mock_llm = CountingMockLLM()
    mock_state = {
        "task": "Build a matrix calculator CLI",
        "target_language": "python",
        "specifications": "Provide matrix addition and subtraction",
        "run_id": "test_prompt_auth",
        "contract_revision_count": 0,
        "test_files": [str(test_file)],
        "v0_requirement_model": {
            "requirements": [{"category": "FUNCTIONAL", "description": "Support addition"}]
        },
        "logs": []
    }

    architect_agent(mock_state, llm=mock_llm)

    assert len(mock_llm.recorded_messages) == 1
    human_msg = mock_llm.recorded_messages[0][1].content

    # 1. Sections strictly ordered [1] to [5]
    idx1 = human_msg.find("[1] USER INTENT / V0 REQUIREMENTS")
    idx2 = human_msg.find("[2] ACCEPTANCE OBLIGATION LEDGER")
    idx3 = human_msg.find("[3] PM SPECIFICATION")
    idx4 = human_msg.find("[4] BLUEPRINT SCHEMA & CANONICAL OUTPUT SPECIFICATION")
    idx5 = human_msg.find("[5] ARCHITECT CONSTRUCTION RULES")

    assert idx1 != -1, "Missing section [1]"
    assert idx2 != -1, "Missing section [2]"
    assert idx3 != -1, "Missing section [3]"
    assert idx4 != -1, "Missing section [4]"
    assert idx5 != -1, "Missing section [5]"
    assert idx1 < idx2 < idx3 < idx4 < idx5, f"Sections out of order: {idx1}, {idx2}, {idx3}, {idx4}, {idx5}"

    # 2. Canonical obligation ledger is present and authoritative
    assert "ACCEPTANCE OBLIGATION LEDGER (AUTHORITATIVE ACCEPTANCE OBLIGATIONS)" in human_msg
    assert "Authority: FROZEN_ORACLE (Immutable Acceptance Authority" in human_msg
    assert "add" in human_msg  # Extracted obligation

    # 3. PM is explicitly labeled PROPOSAL
    assert "[3] PM SPECIFICATION (PROPOSAL — DESIGN REFERENCE ONLY)" in human_msg
    assert "Peran: Product Manager adalah PROPOSAL perancangan fitur, BUKAN Acceptance Authority" in human_msg
    assert "[2] ACCEPTANCE OBLIGATION LEDGER MUTLAK MENANG" in human_msg

    # 4. No duplicate usage evidence or scenario blocks on Turn 0
    assert "=== ACCEPTANCE USAGE EVIDENCE" not in human_msg
    assert "=== SCENARIOS FOR ARCHITECT" not in human_msg
    assert "=== ACCEPTANCE SCENARIOS" not in human_msg


