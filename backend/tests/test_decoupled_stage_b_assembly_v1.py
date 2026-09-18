"""
Synthetic Unit Test Suite for Treatment #1.8.8: Decoupled Stage B Scaffold Assembly v1
Tests A through R (18 tests)

Domain-Agnostic Validation across Synthetic Domains:
- Avionics Telemetry
- Quantum Register Simulation
- Financial Ledger
"""

import ast
import json
import inspect
from pathlib import Path
from typing import Dict, List, Any

import pytest

from backend.architect_staged import (
    StageAObligationMapping,
    FrozenStageAMappings,
    StageARevisionRequest,
    StageBAssemblyOutput,
    extract_stage_b_scaffold_payload,
    parse_stage_b_assembly,
    validate_stage_b_preservation,
    assemble_stage_b_blueprint,
    build_stage_b_prompt,
    STAGE_B_SYSTEM_PROMPT,
)
from backend.canonical_scenario import (
    CanonicalScenario,
    PythonAstScenarioExtractor,
    evaluate_scaffold_scenario_compatibility,
    ScaffoldCompatibilityStatus,
)


# ============================================================================
# Test A: Raw Scaffold Payload Extractor - Single File Block
# ============================================================================
def test_a_extract_single_file_block():
    """Extract single file block with 100% byte fidelity."""
    text = """
Some explanatory commentary from the model.

=== FILE: telemetry/receiver.py ===
class Receiver:
    def __init__(self, port: int = 8080):
        self.port = port

    def read_packet(self) -> bytes:
        return b"ACK"
=== END FILE ===

Closing remarks.
"""
    files = extract_stage_b_scaffold_payload(text)
    assert "telemetry/receiver.py" in files
    expected = (
        "class Receiver:\n"
        "    def __init__(self, port: int = 8080):\n"
        "        self.port = port\n\n"
        "    def read_packet(self) -> bytes:\n"
        "        return b\"ACK\""
    )
    assert files["telemetry/receiver.py"] == expected


# ============================================================================
# Test B: Raw Scaffold Payload Extractor - Multi-File Blocks
# ============================================================================
def test_b_extract_multi_file_blocks():
    """Extract multiple distinct files with separate paths."""
    text = """
=== FILE: core/types.py ===
from typing import NamedTuple

class Packet(NamedTuple):
    id: int
    payload: str
=== END FILE ===

=== FILE: core/engine.py ===
from .types import Packet

def process(pkt: Packet) -> bool:
    return len(pkt.payload) > 0
=== END FILE ===
"""
    files = extract_stage_b_scaffold_payload(text)
    assert len(files) == 2
    assert "core/types.py" in files
    assert "core/engine.py" in files
    assert "class Packet(NamedTuple):" in files["core/types.py"]
    assert "def process(pkt: Packet) -> bool:" in files["core/engine.py"]


# ============================================================================
# Test C: Container Tag Support
# ============================================================================
def test_c_extract_container_tags():
    """Extract files when wrapped inside === STAGE B: SCAFFOLD ARTIFACTS === container."""
    text = """
=== STAGE B: SCAFFOLD ARTIFACTS ===
=== FILE: quantum/qubit.py ===
class Qubit:
    def __init__(self, state: complex = 1+0j):
        self.state = state
=== END FILE ===
=== END STAGE B SCAFFOLDS ===
"""
    files = extract_stage_b_scaffold_payload(text)
    assert "quantum/qubit.py" in files
    assert "class Qubit:" in files["quantum/qubit.py"]


# ============================================================================
# Test D: Exact Preservation of Special Characters, Indentation, Docstrings
# ============================================================================
def test_d_preserve_raw_code_formatting():
    """Verify that quotes, triple quotes, indentation, braces, and newlines are unmodified."""
    raw_code = '''def complex_func(x: int) -> dict:
    """This docstring has 'single' and "double" quotes and {braces}."""
    raw_json = '{"nested": [1, 2, 3]}'
    return {
        "val": x * 2,
        "escapes": "\\n\\t\\r"
    }'''
    text = f"=== FILE: complex.py ===\n{raw_code}\n=== END FILE ==="
    files = extract_stage_b_scaffold_payload(text)
    assert files["complex.py"] == raw_code


# ============================================================================
# Test E: Graceful Handling of Malformed or Empty Payload
# ============================================================================
def test_e_extract_empty_or_malformed():
    """Empty or unclosed file blocks must be handled gracefully without crashing."""
    assert extract_stage_b_scaffold_payload("") == {}
    assert extract_stage_b_scaffold_payload("No file tags here.") == {}

    # Unclosed file tag should still be captured
    unclosed = "=== FILE: unclosed.py ===\nprint('hello')\n"
    files = extract_stage_b_scaffold_payload(unclosed)
    assert "unclosed.py" in files
    assert "print('hello')" in files["unclosed.py"]


# ============================================================================
# Test F: Parse Decoupled Stage B Output (JSON decisions + raw code block)
# ============================================================================
def test_f_parse_decoupled_stage_b_assembly():
    """parse_stage_b_assembly correctly integrates decoupled decisions and raw code."""
    text = """
=== STAGE B: ARCHITECTURAL DECISIONS ===
{
  "target_file": "telemetry.py",
  "semantic_decisions": [
    {
      "obligation_id": "TEL-01",
      "target_structure": "INTERFACE_CONTRACT",
      "identifier": "transmit",
      "target_file": "telemetry.py",
      "parameters": [{"name": "signal", "type": "str", "location": "ARGUMENT", "required": true}],
      "return_semantics": {"type": "bool", "status_code": 200}
    }
  ],
  "stage_a_revision_requests": []
}
=== END STAGE B DECISIONS ===

=== STAGE B: SCAFFOLD ARTIFACTS ===
=== FILE: telemetry.py ===
def transmit(signal: str) -> bool:
    return True
=== END FILE ===
=== END STAGE B SCAFFOLDS ===
"""
    assembly, errors = parse_stage_b_assembly(text)
    assert not errors
    assert assembly is not None
    assert assembly.is_decoupled is True
    assert assembly.target_file == "telemetry.py"
    assert len(assembly.semantic_decisions) == 1
    assert assembly.semantic_decisions[0].identifier == "transmit"
    assert "telemetry.py" in assembly.files
    assert "def transmit(signal: str) -> bool:" in assembly.files["telemetry.py"]
    assert assembly.scaffold_code == assembly.files["telemetry.py"]


# ============================================================================
# Test G: Backward Compatibility with Legacy Combined Assembly
# ============================================================================
def test_g_parse_legacy_combined_assembly():
    """parse_stage_b_assembly must still parse legacy single JSON format."""
    text = """
=== STAGE B: ARCHITECTURAL ASSEMBLY ===
{
  "target_file": "legacy.py",
  "files": {
    "legacy.py": {
      "scaffold_code": "def old_style():\\n    pass\\n"
    }
  },
  "scaffold_code": "def old_style():\\n    pass\\n",
  "semantic_decisions": [
    {
      "obligation_id": "LEG-01",
      "target_structure": "INTERFACE_CONTRACT",
      "identifier": "old_style",
      "target_file": "legacy.py",
      "parameters": [],
      "return_semantics": {"type": "None", "status_code": 200}
    }
  ],
  "stage_a_revision_requests": []
}
=== END STAGE B ===
"""
    assembly, errors = parse_stage_b_assembly(text)
    assert not errors
    assert assembly is not None
    assert assembly.target_file == "legacy.py"
    assert "def old_style():" in assembly.scaffold_code


# ============================================================================
# Test H: Decoupled Decisions Overlay Priority
# ============================================================================
def test_h_decoupled_overlay_precedence():
    """Raw file block overrides any dummy scaffold_code inside JSON."""
    text = """
=== STAGE B: ARCHITECTURAL DECISIONS ===
{
  "target_file": "app.py",
  "scaffold_code": "# STUB FROM JSON",
  "semantic_decisions": [
    {
      "obligation_id": "APP-01",
      "target_structure": "INTERFACE_CONTRACT",
      "identifier": "run",
      "target_file": "app.py",
      "parameters": [],
      "return_semantics": {"type": "None", "status_code": 200}
    }
  ],
  "stage_a_revision_requests": []
}
=== END STAGE B DECISIONS ===

=== FILE: app.py ===
# REAL RAW SCAFFOLD
def run():
    print("running")
=== END FILE ===
"""
    assembly, errors = parse_stage_b_assembly(text)
    assert not errors
    assert assembly is not None
    assert assembly.is_decoupled is True
    assert "# REAL RAW SCAFFOLD" in assembly.files["app.py"]
    assert "# STUB FROM JSON" not in assembly.files["app.py"]


# ============================================================================
# Test I: assemble_stage_b_blueprint Requires Target File and Concrete Scaffold
# ============================================================================
def test_i_assemble_enforces_target_and_scaffold():
    """assemble_stage_b_blueprint fails if target_file or scaffold code is missing."""
    mapping = StageAObligationMapping(
        obligation_id="OBL-01",
        source_authority="ACCEPTANCE_ORACLE",
        semantic_element="E1",
        element_kind="FUNCTION",
        semantic_identity="ident_1",
        semantic_target_artifact="main.py",
        evidence_basis="test"
    )
    frozen_a = FrozenStageAMappings.freeze([mapping])

    # Missing scaffold
    assembly_empty = StageBAssemblyOutput(
        target_file="main.py",
        files={},
        scaffold_code="",
        semantic_decisions=[]
    )
    bp, errs = assemble_stage_b_blueprint(frozen_a, assembly_empty)
    assert bp is None
    assert any("STAGE_B_MISSING_SCAFFOLD" in e for e in errs)


# ============================================================================
# Test J: assemble_stage_b_blueprint Enforces Stage A Invariants
# ============================================================================
def test_j_assemble_enforces_stage_a_invariants():
    """assemble_stage_b_blueprint rejects silent renaming or deletion of Stage A mappings."""
    mapping = StageAObligationMapping(
        obligation_id="OBL-01",
        source_authority="ACCEPTANCE_ORACLE",
        semantic_element="E1",
        element_kind="FUNCTION",
        semantic_identity="correct_identity",
        semantic_target_artifact="main.py",
        evidence_basis="test"
    )
    frozen_a = FrozenStageAMappings.freeze([mapping])

    # Silent renaming
    assembly_renamed, _ = parse_stage_b_assembly("""
=== STAGE B: ARCHITECTURAL DECISIONS ===
{
  "target_file": "main.py",
  "semantic_decisions": [
    {
      "obligation_id": "OBL-01",
      "target_structure": "INTERFACE_CONTRACT",
      "identifier": "renamed_synonym",
      "target_file": "main.py",
      "parameters": [],
      "return_semantics": {"type": "None", "status_code": 200}
    }
  ],
  "stage_a_revision_requests": []
}
=== END STAGE B DECISIONS ===
=== FILE: main.py ===
def renamed_synonym(): pass
=== END FILE ===
""")
    bp, errs = assemble_stage_b_blueprint(frozen_a, assembly_renamed)
    assert bp is None
    assert any("STAGE_B_SILENT_RENAMING" in e for e in errs)


# ============================================================================
# Test K: assemble_stage_b_blueprint Produces Valid Canonical Blueprint
# ============================================================================
def test_k_assemble_produces_canonical_blueprint():
    """assemble_stage_b_blueprint produces valid blueprint with files, decisions, and schema."""
    mapping = StageAObligationMapping(
        obligation_id="OBL-01",
        source_authority="ACCEPTANCE_ORACLE",
        semantic_element="E1",
        element_kind="FUNCTION",
        semantic_identity="correct_identity",
        semantic_target_artifact="main.py",
        evidence_basis="test"
    )
    frozen_a = FrozenStageAMappings.freeze([mapping])

    assembly, _ = parse_stage_b_assembly("""
=== STAGE B: ARCHITECTURAL DECISIONS ===
{
  "target_file": "main.py",
  "semantic_decisions": [
    {
      "obligation_id": "OBL-01",
      "target_structure": "INTERFACE_CONTRACT",
      "identifier": "correct_identity",
      "target_file": "main.py",
      "parameters": [],
      "return_semantics": {"type": "None", "status_code": 200}
    }
  ],
  "stage_a_revision_requests": []
}
=== END STAGE B DECISIONS ===
=== FILE: main.py ===
def correct_identity():
    pass
=== END FILE ===
""")
    bp, errs = assemble_stage_b_blueprint(frozen_a, assembly)
    assert not errs
    assert bp is not None
    assert bp.authoritative_target_file == "main.py"
    assert "main.py" in bp.files
    assert "correct_identity" in bp.files["main.py"].code_scaffold


# ============================================================================
# Test L: Python AST Scenario Extractor Identifies Harness Helpers
# ============================================================================
def test_l_scenario_extractor_identifies_harness_helpers():
    """Extractor marks tests that invoke module-level non-test helpers as harness adapters."""
    test_code = """
import main

def _helper_add(a, b):
    if hasattr(main, 'Matrix'):
        return main.Matrix(a)
    return main.add_matrices(a, b)

def test_add():
    res = _helper_add([1, 2], [3, 4])
    assert res == [4, 6]
"""
    extractor = PythonAstScenarioExtractor()
    scs = extractor.extract_scenarios("test_pkg.py", test_code)
    assert len(scs) == 1
    sc = scs[0]
    assert sc.is_harness_adapter is True
    assert "Matrix" in sc.adapter_target_symbols
    assert "add_matrices" in sc.adapter_target_symbols


# ============================================================================
# Test M: Target Symbol Propagation Across Helper Chains
# ============================================================================
def test_m_propagate_targets_across_helper_chains():
    """Helper calling another helper inherits the target symbols of the callee."""
    test_code = """
import target_mod

def _wrap_base(x):
    return target_mod.BaseClass(x)

def _wrap_outer(a, b):
    w = _wrap_base(a)
    return target_mod.outer_action(w, b)

def test_feature():
    val = _wrap_outer(10, 20)
    assert val > 0
"""
    extractor = PythonAstScenarioExtractor()
    scs = extractor.extract_scenarios("test_feature.py", test_code)
    assert len(scs) == 1
    sc = scs[0]
    assert sc.is_harness_adapter is True
    # Inherited from _wrap_base
    assert "BaseClass" in sc.adapter_target_symbols
    # Defined in _wrap_outer
    assert "outer_action" in sc.adapter_target_symbols


# ============================================================================
# Test N: Scenario Compatibility Evaluator Matches Adapter Target Symbols
# ============================================================================
def test_n_evaluator_matches_adapter_targets():
    """Scaffold defining the adapter target symbol satisfies scenario compatibility."""
    sc = CanonicalScenario(
        scenario_id="SCN-TEST-01",
        stimulus="_adapter_call(x)",
        is_harness_adapter=True,
        adapter_target_symbols=["Vector", "add_vectors"],
        expected_outcome={"equals": 42}
    )
    # Scaffold provides Vector class
    scaffold = {
        "vector.py": "class Vector:\n    def __init__(self, x):\n        self.x = x\n"
    }
    matrix = evaluate_scaffold_scenario_compatibility([sc], scaffold)
    assert matrix.incompatible_count == 0
    assert len(matrix.items) == 1
    assert matrix.items[0].compatibility == ScaffoldCompatibilityStatus.COMPATIBLE.value


# ============================================================================
# Test O: Direct Non-Adapter Stimuli Retain Strict Matching
# ============================================================================
def test_o_direct_stimuli_strict_matching():
    """Scenarios with direct stimuli without adapter flags are matched strictly by symbol/route."""
    sc = CanonicalScenario(
        scenario_id="SCN-DIRECT-01",
        stimulus="calculate_integral(dx)",
        is_harness_adapter=False,
        adapter_target_symbols=[],
        expected_outcome={"status": 200}
    )
    # Scaffold provides unrelated symbol
    scaffold = {
        "math_ops.py": "def unrelated_fn(): pass\n"
    }
    matrix = evaluate_scaffold_scenario_compatibility([sc], scaffold)
    assert matrix.incompatible_count == 1
    assert matrix.items[0].compatibility == ScaffoldCompatibilityStatus.INCOMPATIBLE.value


# ============================================================================
# Test P: Domain Generality (Quantum Simulation Domain)
# ============================================================================
def test_p_domain_generality_quantum_simulation():
    """Adapter resolution and scaffold evaluation work identically for novel domains."""
    quantum_test_code = """
import simulator

def _simulate_circuit(gates):
    if hasattr(simulator, 'QubitRegister'):
        reg = simulator.QubitRegister(2)
        return reg.apply(gates)
    return simulator.execute_circuit(gates)

def test_bell_state():
    state = _simulate_circuit(['H', 'CNOT'])
    assert state is not None
"""
    extractor = PythonAstScenarioExtractor()
    scs = extractor.extract_scenarios("test_quantum.py", quantum_test_code)
    assert len(scs) == 1
    sc = scs[0]
    assert sc.is_harness_adapter is True
    assert set(sc.adapter_target_symbols) == {"QubitRegister", "execute_circuit"}

    # Evaluate against scaffold implementing QubitRegister
    scaffold = {
        "simulator.py": """class QubitRegister:
    def __init__(self, num_qubits: int):
        self.num_qubits = num_qubits
    def apply(self, gates):
        return [1, 0, 0, 1]
"""
    }
    matrix = evaluate_scaffold_scenario_compatibility(scs, scaffold)
    assert matrix.incompatible_count == 0
    assert matrix.items[0].compatibility == ScaffoldCompatibilityStatus.COMPATIBLE.value


# ============================================================================
# Test Q: Repair Prompt Differentiates Format Errors from Semantic Drift
# ============================================================================
def test_q_repair_prompt_differentiates_errors():
    """build_stage_b_prompt distinguishes representation errors from preservation violations."""
    mapping = StageAObligationMapping(
        obligation_id="OBL-01",
        source_authority="ACCEPTANCE_ORACLE",
        semantic_element="E1",
        element_kind="FUNCTION",
        semantic_identity="ident_1",
        semantic_target_artifact="main.py",
        evidence_basis="test"
    )
    frozen_a = FrozenStageAMappings.freeze([mapping])

    # Format / representation error
    fmt_prompt = build_stage_b_prompt(
        target_lang="python",
        user_task="test task",
        specs="",
        frozen_stage_a=frozen_a,
        repair_errors=["STAGE_B_JSON_PARSE_ERROR: Invalid control character at line 23"]
    )
    assert "FORMAT / REPRESENTATION ERROR" in fmt_prompt
    assert "Decoupled Representation" in fmt_prompt

    # Preservation / semantic drift error
    pres_prompt = build_stage_b_prompt(
        target_lang="python",
        user_task="test task",
        specs="",
        frozen_stage_a=frozen_a,
        repair_errors=["STAGE_B_SILENT_RENAMING: Obligation 'OBL-01' identity renamed"]
    )
    assert "PRESERVATION FAILURE" in pres_prompt
    assert "DILARANG mengganti nama simbol" in pres_prompt


# ============================================================================
# Test R: Anti-Solver Static Audit
# ============================================================================
def test_r_anti_solver_static_audit():
    """Verify zero hardcoded task names or tokens in Stage B assembly or adapter code."""
    import backend.architect_staged as arch_staged
    import backend.canonical_scenario as can_scen

    staged_src = inspect.getsource(arch_staged)
    scen_src = inspect.getsource(can_scen)

    for forbidden in ["fastapi_t1", "cli_t1", "flutter_t1"]:
        assert forbidden not in staged_src, f"Task-specific token '{forbidden}' found in architect_staged.py"

    # Adapter extraction in canonical_scenario must NOT hardcode specific helper names
    extractor_src = inspect.getsource(PythonAstScenarioExtractor)
    for forbidden in ["_add", "_sub", "_mul", "_get_matrix", "cli_t1", "fastapi_t1", "flutter_t1"]:
        assert forbidden not in extractor_src, f"Hardcoded token '{forbidden}' found in PythonAstScenarioExtractor"
