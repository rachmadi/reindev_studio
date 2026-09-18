"""
Synthetic Unit Test Suite for Treatment #1.8.7: Semantic Grounding & Prompt Fidelity v1
Tests A through O (15 tests)

Domain-Agnostic Validation across Synthetic Domains:
- Aerospace Telemetry / Guidance Avionics
- Bio-Medical Sensor Analysis
- Distributed Ledger Consensus
"""

import pytest
import json
import inspect
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
    build_stage_a_prompt,
    build_stage_b_prompt,
    format_stage_a_repair_evidence,
    STAGE_A_SYSTEM_PROMPT,
    STAGE_B_SYSTEM_PROMPT,
)


# ============================================================================
# Test A: Exact Obligation Preservation
# ============================================================================
def test_a_exact_obligation_preservation():
    """Authoritative obligation identity must be preserved 1:1 without alteration."""
    auth_obs = [
        {"obligation_id": "AVIONICS-OBL-01", "identity": "calculate_trajectory", "target_file": "guidance.py"}
    ]
    raw_stage_a = """
    === STAGE A: OBLIGATION MAPPING ===
    {
      "obligation_mappings": [
        {
          "obligation_id": "AVIONICS-OBL-01",
          "source_authority": "ACCEPTANCE_ORACLE",
          "semantic_element": "CalculateTrajectory",
          "mapped_element": "CalculateTrajectory",
          "element_kind": "FUNCTION",
          "semantic_identity": "calculate_trajectory",
          "semantic_target_artifact": "guidance.py",
          "evidence_basis": "Direct call in test_guidance.py:24",
          "semantic_parameters": [
            {"name": "altitude", "type": "float", "location": "ARGUMENT", "required": true},
            {"name": "velocity", "type": "float", "location": "ARGUMENT", "required": true}
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
    m = mappings[0]
    assert m.obligation_id == "AVIONICS-OBL-01"
    assert m.semantic_identity == "calculate_trajectory"
    assert m.source_authority == "ACCEPTANCE_ORACLE"

    is_valid, val_errs = validate_stage_a_mappings(mappings, auth_obs)
    assert is_valid is True
    assert val_errs == []

    frozen = FrozenStageAMappings.freeze(mappings)
    assert frozen.sha256_seal is not None
    assert frozen.get_mapping("AVIONICS-OBL-01").semantic_identity == "calculate_trajectory"


# ============================================================================
# Test B: Semantic Synonym Temptation
# ============================================================================
def test_b_semantic_synonym_temptation():
    """Prompt must explicitly forbid substituting semantic synonyms."""
    # System prompt must warn against semantic synonym temptation
    assert "semantic synonym temptation" in STAGE_A_SYSTEM_PROMPT.lower() or "sinonim" in STAGE_A_SYSTEM_PROMPT.lower()
    assert "DILARANG mengganti" in STAGE_A_SYSTEM_PROMPT

    prompt = build_stage_a_prompt(
        target_lang="python",
        user_task="Calculate vehicle tax",
        specs="Use compute_tax function to calculate tax",
        oracle_ledger="[AUTHORITATIVE OBLIGATION: calculate_tax]"
    )
    # The prompt hierarchy must state Level 1 Acceptance Authority overrides Level 5 PM proposal
    assert "[1] ACCEPTANCE AUTHORITY" in prompt
    assert "[5] PM REQUIREMENTS" in prompt
    assert "Do NOT substitute a semantically similar feature or synonym" in prompt


# ============================================================================
# Test C: Obligation Rename Rejection
# ============================================================================
def test_c_obligation_rename_rejection():
    """Stage B attempting silent renaming of a validated Stage A identity must be rejected."""
    map_a = StageAObligationMapping(
        obligation_id="OBL-01",
        semantic_element="SensorStream",
        element_kind="CLASS",
        semantic_identity="SensorStream",
        semantic_target_artifact="sensor.py",
        source_authority="ACCEPTANCE_ORACLE"
    )
    frozen_a = FrozenStageAMappings.freeze([map_a])

    # Stage B renames SensorStream to SensorDataStream
    assembly_b = StageBAssemblyOutput(
        target_file="sensor.py",
        files={"sensor.py": "class SensorDataStream: pass"},
        scaffold_code="class SensorDataStream: pass",
        semantic_decisions=[
            type("Decision", (), {
                "obligation_id": "OBL-01",
                "identifier": "SensorDataStream",
                "target_structure": "INTERFACE_CONTRACT",
                "target_file": "sensor.py",
                "to_dict": lambda s: {"obligation_id": "OBL-01", "identifier": "SensorDataStream", "target_structure": "INTERFACE_CONTRACT"}
            })()
        ]
    )

    is_valid, errors, revs = validate_stage_b_preservation(frozen_a, assembly_b)
    assert is_valid is False
    assert any("STAGE_B_SILENT_RENAMING" in e for e in errors)
    assert any("SensorStream" in e and "SensorDataStream" in e for e in errors)


# ============================================================================
# Test D: Obligation Deletion Detection
# ============================================================================
def test_d_obligation_deletion_detection():
    """Omitting any authoritative obligation must be caught by Stage A validation."""
    auth_obs = ["OBL-01", "OBL-02", "OBL-03"]
    # Model only maps OBL-01 and OBL-02
    mappings = [
        StageAObligationMapping(
            obligation_id="OBL-01",
            semantic_element="Elem1",
            element_kind="FUNCTION",
            semantic_identity="func_1",
            semantic_target_artifact="mod.py"
        ),
        StageAObligationMapping(
            obligation_id="OBL-02",
            semantic_element="Elem2",
            element_kind="FUNCTION",
            semantic_identity="func_2",
            semantic_target_artifact="mod.py"
        )
    ]

    is_valid, errors = validate_stage_a_mappings(mappings, auth_obs)
    assert is_valid is False
    assert any("STAGE_A_MISSING_OBLIGATIONS" in e for e in errors)
    assert any("OBL-03" in e for e in errors)


# ============================================================================
# Test E: Obligation Invention Detection
# ============================================================================
def test_e_obligation_invention_detection():
    """Inventing an obligation ID not present in authoritative obligations must be rejected."""
    auth_obs = ["OBL-AUTH-01"]
    mappings = [
        StageAObligationMapping(
            obligation_id="OBL-AUTH-01",
            semantic_element="RealElem",
            element_kind="FUNCTION",
            semantic_identity="real_elem",
            semantic_target_artifact="mod.py"
        ),
        StageAObligationMapping(
            obligation_id="OBL-INVENTED-99",
            semantic_element="PhantomElem",
            element_kind="FUNCTION",
            semantic_identity="phantom_elem",
            semantic_target_artifact="mod.py"
        )
    ]

    is_valid, errors = validate_stage_a_mappings(mappings, auth_obs)
    assert is_valid is False
    assert any("STAGE_A_INVENTED_OBLIGATION" in e for e in errors)
    assert any("OBL-INVENTED-99" in e for e in errors)


# ============================================================================
# Test F: Multiple Obligations
# ============================================================================
def test_f_multiple_obligations():
    """Handles multiple obligations across varied element kinds cleanly."""
    auth_obs = ["OBL-FN-01", "OBL-CLS-02", "OBL-MOD-03"]
    raw_stage_a = """
    === STAGE A: OBLIGATION MAPPING ===
    {
      "obligation_mappings": [
        {
          "obligation_id": "OBL-FN-01",
          "source_authority": "ACCEPTANCE_ORACLE",
          "semantic_element": "ProcessPayload",
          "mapped_element": "ProcessPayload",
          "element_kind": "FUNCTION",
          "semantic_identity": "process_payload",
          "semantic_target_artifact": "engine.py"
        },
        {
          "obligation_id": "OBL-CLS-02",
          "source_authority": "ACCEPTANCE_ORACLE",
          "semantic_element": "EngineController",
          "mapped_element": "EngineController",
          "element_kind": "CLASS",
          "semantic_identity": "EngineController",
          "semantic_target_artifact": "engine.py"
        },
        {
          "obligation_id": "OBL-MOD-03",
          "source_authority": "ACCEPTANCE_ORACLE",
          "semantic_element": "PayloadConfig",
          "mapped_element": "PayloadConfig",
          "element_kind": "DATA_MODEL",
          "semantic_identity": "PayloadConfig",
          "semantic_target_artifact": "models.py"
        }
      ]
    }
    === END STAGE A ===
    """
    mappings, parse_errs = parse_stage_a_mappings(raw_stage_a)
    assert parse_errs == []
    assert len(mappings) == 3

    is_valid, errors = validate_stage_a_mappings(mappings, auth_obs)
    assert is_valid is True
    assert errors == []


# ============================================================================
# Test G: Ambiguous Evidence
# ============================================================================
def test_g_ambiguous_evidence():
    """Prompt fidelity instruction explicitly tells model to mark unresolved if ambiguous."""
    prompt = build_stage_a_prompt(
        target_lang="python",
        user_task="Generic data pipeline",
        specs="Maybe implement caching or maybe direct stream"
    )
    assert "If evidence is insufficient or ambiguous: mark the decision UNRESOLVED rather than inventing a requirement" in prompt


# ============================================================================
# Test H: Unresolved Evidence Handling
# ============================================================================
def test_h_unresolved_evidence():
    """Stage B reporting unresolved representation via revision requests is handled cleanly."""
    map_a = StageAObligationMapping(
        obligation_id="OBL-01",
        semantic_element="ComplexWidget",
        element_kind="WIDGET",
        semantic_identity="ComplexWidget",
        semantic_target_artifact="widget.dart"
    )
    frozen_a = FrozenStageAMappings.freeze([map_a])

    assembly_b = StageBAssemblyOutput(
        target_file="widget.dart",
        files={"widget.dart": "// stub"},
        scaffold_code="// stub",
        semantic_decisions=[],
        stage_a_revision_requests=[
            StageARevisionRequest(
                obligation_id="OBL-01",
                reason="Platform target lacks native widget primitives for requested shape",
                requested_change={"suggested_kind": "CLASS"}
            )
        ]
    )

    is_valid, reasons, revs = validate_stage_b_preservation(frozen_a, assembly_b)
    assert is_valid is False
    assert len(revs) == 1
    assert revs[0].obligation_id == "OBL-01"
    assert "Platform target lacks" in revs[0].reason


# ============================================================================
# Test I: Repair Preserving Valid Mappings
# ============================================================================
def test_i_repair_preserving_valid_mappings():
    """format_stage_a_repair_evidence clearly preserves already-valid mappings and isolates error."""
    valid_map = StageAObligationMapping(
        obligation_id="OBL-01",
        semantic_element="ValidatedFunc",
        element_kind="FUNCTION",
        semantic_identity="validated_func",
        semantic_target_artifact="core.py"
    )
    invalid_map = StageAObligationMapping(
        obligation_id="OBL-02",
        semantic_element="",  # missing semantic element
        element_kind="FUNCTION",
        semantic_identity="",
        semantic_target_artifact="core.py"
    )

    evidence_text = format_stage_a_repair_evidence(
        authoritative_obligations=["OBL-01", "OBL-02", "OBL-03"],
        current_mappings=[valid_map, invalid_map],
        repair_errors=["Obligation 'OBL-02' has empty 'semantic_identity'"]
    )

    assert "PRESERVED VALID MAPPINGS (DO NOT MUTATE OR DISCARD):" in evidence_text
    assert "✓ [OBL-01] validated_func" in evidence_text
    assert "INVALID MAPPINGS REQUIRING CORRECTION:" in evidence_text
    assert "✗ [OBL-02]" in evidence_text
    assert "MISSING OBLIGATIONS REQUIRING NEW MAPPING: ['OBL-03']" in evidence_text
    assert "EVIDENCE CAUSING REJECTION (ACTIVE FAILURES):" in evidence_text
    assert "Obligation 'OBL-02' has empty 'semantic_identity'" in evidence_text


# ============================================================================
# Test J: Authoritative Evidence Overriding Lower-Priority Proposal
# ============================================================================
def test_j_authoritative_overrides_proposal():
    """Acceptance Authority at Level 1-2 strictly overrides Level 5 PM proposal."""
    prompt = build_stage_a_prompt(
        target_lang="python",
        user_task="Sync service",
        specs="PM suggests naming the function sync_all_records()",
        oracle_ledger="[AUTHORITATIVE OBLIGATION: flush_stream]"
    )

    idx_l1 = prompt.find("[1] ACCEPTANCE AUTHORITY")
    idx_l2 = prompt.find("[2] AUTHORITATIVE OBLIGATIONS")
    idx_l5 = prompt.find("[5] PM REQUIREMENTS")

    assert idx_l1 != -1 and idx_l2 != -1 and idx_l5 != -1
    assert idx_l1 < idx_l2 < idx_l5, "Hierarchy order violated: Acceptance Authority must precede PM Requirements"
    assert "They do NOT possess acceptance authority and CANNOT alter Authoritative Obligations at Levels 1-3" in prompt


# ============================================================================
# Test K: Stage-A -> Stage-B Semantic Preservation
# ============================================================================
def test_k_stage_a_to_stage_b_semantic_preservation():
    """Stage B faithfully reflects all validated Stage A mappings."""
    map_a = StageAObligationMapping(
        obligation_id="OBL-01",
        semantic_element="CalculateCRC",
        element_kind="FUNCTION",
        semantic_identity="calculate_crc",
        semantic_target_artifact="checksum.py",
        semantic_parameters=({"name": "data", "type": "bytes", "location": "ARGUMENT", "required": True},),
        semantic_return={"type": "int", "status_code": 200}
    )
    frozen_a = FrozenStageAMappings.freeze([map_a])

    raw_stage_b = """
    === STAGE B: ARCHITECTURAL ASSEMBLY ===
    {
      "target_file": "checksum.py",
      "files": {
        "checksum.py": {
          "scaffold_code": "def calculate_crc(data: bytes) -> int:\\n    return 0\\n"
        }
      },
      "scaffold_code": "def calculate_crc(data: bytes) -> int:\\n    return 0\\n",
      "semantic_decisions": [
        {
          "obligation_id": "OBL-01",
          "target_structure": "INTERFACE_CONTRACT",
          "identifier": "calculate_crc",
          "target_file": "checksum.py",
          "parameters": [
            {"name": "data", "type": "bytes", "location": "ARGUMENT", "required": true}
          ],
          "return_semantics": {"type": "int", "status_code": 200}
        }
      ]
    }
    === END STAGE B ===
    """
    assembly_b, parse_errs = parse_stage_b_assembly(raw_stage_b)
    assert parse_errs == []

    is_valid, errors, revs = validate_stage_b_preservation(frozen_a, assembly_b)
    assert is_valid is True
    assert errors == []
    assert revs == []


# ============================================================================
# Test L: Traceability Preservation
# ============================================================================
def test_l_traceability_preservation():
    """StageAObligationMapping retains obligation_id, source_authority, semantic_identity, mapped_element, evidence_basis."""
    mapping = StageAObligationMapping(
        obligation_id="OBL-TRACE-42",
        semantic_element="TelemetryGateway",
        element_kind="CLASS",
        semantic_identity="TelemetryGateway",
        semantic_target_artifact="gateway.py",
        source_authority="FROZEN_ORACLE",
        evidence_basis="Extracted from test_gateway.py:45 assert isinstance(gw, TelemetryGateway)"
    )

    d = mapping.to_dict()
    assert d["obligation_id"] == "OBL-TRACE-42"
    assert d["source_authority"] == "FROZEN_ORACLE"
    assert d["semantic_identity"] == "TelemetryGateway"
    assert d["semantic_element"] == "TelemetryGateway"
    assert d["mapped_element"] == "TelemetryGateway"
    assert d["evidence_basis"] == "Extracted from test_gateway.py:45 assert isinstance(gw, TelemetryGateway)"

    restored = StageAObligationMapping.from_dict(d)
    assert restored.obligation_id == mapping.obligation_id
    assert restored.source_authority == mapping.source_authority
    assert restored.semantic_identity == mapping.semantic_identity
    assert restored.mapped_element == mapping.mapped_element
    assert restored.evidence_basis == mapping.evidence_basis


# ============================================================================
# Test M: Historical Evidence Not Active Failure
# ============================================================================
def test_m_historical_evidence_not_active_failure():
    """Resolved historical errors are not injected into Level 7 as active failures."""
    prompt = build_stage_a_prompt(
        target_lang="python",
        user_task="Build ledger",
        repair_errors=None
    )
    assert "[7] CURRENT REPAIR EVIDENCE" in prompt
    assert "No active failures. Clean initial synthesis." in prompt


# ============================================================================
# Test N: Cross-Domain Semantic Grounding
# ============================================================================
def test_n_cross_domain_semantic_grounding():
    """Verifies prompt construction on a medical device telemetry domain."""
    oracle_ledger = "[AUTHORITATIVE ACCEPTANCE OBLIGATIONS]\n- OBL-MED-01: HeartRateMonitor.record_pulse(bpm: int) -> bool\n- OBL-MED-02: BloodPressureSensor.read_vitals() -> VitalsData"
    oracle_scenarios = "[BEHAVIORAL SCENARIOS]\n- SCN-PULSE: Stimulus: monitor.record_pulse(72) => True"

    prompt = build_stage_a_prompt(
        target_lang="python",
        user_task="Build vital signs monitoring firmware interface",
        specs="Create an ECG and vital signs monitor",
        oracle_ledger=oracle_ledger,
        oracle_scenarios=oracle_scenarios
    )

    assert "HeartRateMonitor.record_pulse" in prompt
    assert "BloodPressureSensor.read_vitals" in prompt
    assert "[1] ACCEPTANCE AUTHORITY" in prompt
    assert "[2] AUTHORITATIVE OBLIGATIONS" in prompt
    assert "[3] AUTHORITATIVE SCENARIOS" in prompt


# ============================================================================
# Test O: No Task-Specific Branching
# ============================================================================
def test_o_no_task_specific_branching():
    """Verify production code has zero task-specific keywords or hardcoded symbols."""
    import backend.architect_staged as arch_staged

    source_a = inspect.getsource(arch_staged.build_stage_a_prompt)
    source_b = inspect.getsource(arch_staged.build_stage_b_prompt)
    source_sys_a = arch_staged.STAGE_A_SYSTEM_PROMPT
    source_sys_b = arch_staged.STAGE_B_SYSTEM_PROMPT
    combined = source_a + source_b + source_sys_a + source_sys_b

    forbidden_terms = [
        "fastapi_t1",
        "cli_t1",
        "flutter_t1",
        "/products",
        "/inventaris",
        "CardMetric",
        "_add",
        "_sub",
        "_mul"
    ]

    for term in forbidden_terms:
        assert term not in combined, f"Forbidden task-specific term '{term}' found in architect_staged prompt/logic!"
