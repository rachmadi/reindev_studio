# -*- coding: utf-8 -*-
"""
Unit Test Suite: Active Validation State Lifecycle v1
ReinDev Studio — Generic, Mission-Agnostic, Language-Agnostic Validation Lifecycle

Verifies Scenarios A-H, negative tests, telemetry, and cross-phase isolation:
- Principle: PERSIST HISTORY, RECOMPUTE ACTIVE VALIDITY
- Historical failures are preserved in provenance.validation_history for forensic audit.
- Active validation errors reflect ONLY current candidate validity.
- Resolved failures do not poison future turns.
- Real current failures cannot be hidden.
- Frozen Acceptance Oracle remains 100% immutable.
"""

import os
import json
import pytest
from unittest.mock import MagicMock
from pathlib import Path
from typing import Dict, Any, List

from backend.canonical_obligation import (
    extract_canonical_oracle_obligations,
    check_obligation_coverage,
)
from backend.contract import (
    MachineReadableContract,
    ContractStatus,
    create_draft_contract,
    complete_aligned_contract,
    seal_and_freeze_contract,
    validate_contract_gate,
)
from backend.blueprint_schema import (
    ArchitecturalBlueprint,
    parse_blueprint_json,
    normalize_blueprint_data_models,
)
from backend.agents.architect import architect_agent
from backend.phase_validators import validate_architect_phase, validate_pm_phase, validate_v0_phase
from backend.graph import architect_validator_node


@pytest.fixture
def tmp_oracle_dir(tmp_path):
    """Direktori sementara untuk Frozen Acceptance Oracle."""
    oracle_dir = tmp_path / "frozen_oracle"
    oracle_dir.mkdir(parents=True, exist_ok=True)
    return oracle_dir


# ==============================================================================
# 1. Scenarios A-D: Turn 0 JSON Parse Error -> Turn 1 Clean Resolution -> FROZEN
# ==============================================================================

def test_scenario_a_turn_0_invalid_json_produces_active_error(tmp_oracle_dir, monkeypatch):
    """
    Scenario A:
    Turn 0 produces invalid JSON -> active error is JSON_PARSE_ERROR -> contract REJECTED.
    """
    oracle_file = tmp_oracle_dir / "test_main.py"
    oracle_file.write_text(
        "import main\ndef test_feature():\n    assert hasattr(main, 'calculate')\n",
        encoding="utf-8"
    )

    invalid_plan = "=== BLUEPRINT JSON ===\n{ invalid_json: missing quotes \n=== END BLUEPRINT JSON ==="
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content=invalid_plan)
    monkeypatch.setattr("backend.agents.architect.get_llm", lambda **kwargs: mock_llm)

    draft = create_draft_contract(raw_intent="Calculator CLI", target_language="python", domain="CLI_TOOL")
    state = {
        "run_id": "test_lifecycle_a",
        "task": "Build calculator CLI",
        "target_language": "python",
        "contract": draft,
        "specifications": "CLI calculator with calculate method.",
        "architecture_plan": "",
        "frozen_oracle_path": str(tmp_oracle_dir),
        "blueprint_revision_count": 0,
        "contract_revision_count": 0,
        "logs": []
    }

    # Architect runs on invalid JSON
    res = architect_agent(state)
    assert res["contract_status"] == "REJECTED"
    assert len(res["contract_validation_errors"]) >= 1
    assert any("SCHEMA_VIOLATION: Blueprint JSON parse failure" in e for e in res["contract_validation_errors"])

    # Contract provenance has active_validation_errors set
    contract = res["contract"]
    prov = contract.get("provenance", {})
    assert len(prov.get("active_validation_errors", [])) >= 1
    assert any("SCHEMA_VIOLATION" in e for e in prov.get("active_validation_errors", []))
    assert len(prov.get("validation_history", [])) >= 1


def test_scenario_b_turn_1_valid_json_achieves_frozen(tmp_oracle_dir, monkeypatch):
    """
    Scenario B & D:
    Turn 0 was rejected due to JSON syntax.
    Turn 1 produces valid JSON + full Oracle coverage.
    Contract must transition to FROZEN (historical error does NOT poison Turn 1).
    """
    oracle_file = tmp_oracle_dir / "test_main.py"
    oracle_file.write_text(
        "import main\ndef test_feature():\n    assert hasattr(main, 'calculate')\n",
        encoding="utf-8"
    )

    invalid_plan = "=== BLUEPRINT JSON ===\n{ broken json \n=== END BLUEPRINT JSON ==="
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content=invalid_plan)
    monkeypatch.setattr("backend.agents.architect.get_llm", lambda **kwargs: mock_llm)

    draft = create_draft_contract(raw_intent="Calculator CLI", target_language="python", domain="CLI_TOOL")
    # Simulate Turn 0 failure
    state_turn0 = {
        "run_id": "test_lifecycle_b",
        "task": "Build calculator CLI",
        "target_language": "python",
        "contract": draft,
        "specifications": "CLI calculator with calculate method.",
        "architecture_plan": "",
        "frozen_oracle_path": str(tmp_oracle_dir),
        "blueprint_revision_count": 0,
        "contract_revision_count": 0,
        "logs": []
    }
    res0 = architect_agent(state_turn0)
    contract_after_turn0 = res0["contract"]
    assert contract_after_turn0["status"] == "REJECTED"

    # Turn 1: Valid blueprint covering calculate
    valid_blueprint_text = """=== BLUEPRINT JSON ===
```json
{
  "authoritative_target_file": "main.py",
  "file_tree": ["main.py"],
  "architecture_summary": "CLI Calculator",
  "files": {
    "main.py": {
      "module_role": "Core",
      "imports": [],
      "code_scaffold": "def calculate(): pass"
    }
  },
  "interface_contracts": [
    {
      "identifier": "calculate",
      "route": "CLI: calculate",
      "method": "POST",
      "target_file": "main.py"
    }
  ],
  "data_models": []
}
```
=== END BLUEPRINT JSON ==="""

    mock_llm2 = MagicMock()
    mock_llm2.invoke.return_value = MagicMock(content=valid_blueprint_text)
    monkeypatch.setattr("backend.agents.architect.get_llm", lambda **kwargs: mock_llm2)

    state_turn1 = {
        "run_id": "test_lifecycle_b",
        "task": "Build calculator CLI",
        "target_language": "python",
        "contract": contract_after_turn0,  # Carries rejected contract from Turn 0
        "specifications": "CLI calculator with calculate method.",
        "architecture_plan": "",
        "frozen_oracle_path": str(tmp_oracle_dir),
        "blueprint_revision_count": 1,
        "contract_revision_count": 1,
        "logs": []
    }

    # Architect runs on Turn 1
    res1 = architect_agent(state_turn1)
    assert res1["contract_status"] == "ALIGNED"
    assert res1["contract_validation_errors"] == []

    contract1 = res1["contract"]
    prov1 = contract1.get("provenance", {})
    # Active errors are empty
    assert prov1.get("active_validation_errors") == []
    assert prov1.get("contract_validation_errors") == []

    # Sealing the contract must succeed and freeze
    ok, frozen_c, errors, warnings = seal_and_freeze_contract(contract1, frozen_oracle_path=str(tmp_oracle_dir))
    assert ok is True
    assert frozen_c["status"] == ContractStatus.FROZEN.value
    assert len(frozen_c.get("provenance", {}).get("contract_sha256", "")) == 64
    assert errors == []


def test_scenario_c_historical_record_retains_turn_0_failure(tmp_oracle_dir, monkeypatch):
    """
    Scenario C:
    Verify that provenance.validation_history retains the Turn 0 failure even after Turn 1 freezes.
    """
    oracle_file = tmp_oracle_dir / "test_main.py"
    oracle_file.write_text(
        "import main\ndef test_feature():\n    assert hasattr(main, 'calculate')\n",
        encoding="utf-8"
    )

    invalid_plan = "=== BLUEPRINT JSON ===\n{ broken json \n=== END BLUEPRINT JSON ==="
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content=invalid_plan)
    monkeypatch.setattr("backend.agents.architect.get_llm", lambda **kwargs: mock_llm)

    draft = create_draft_contract(raw_intent="Calculator CLI", target_language="python", domain="CLI_TOOL")
    state_turn0 = {
        "run_id": "test_lifecycle_c",
        "task": "Build calculator CLI",
        "target_language": "python",
        "contract": draft,
        "specifications": "CLI calculator with calculate method.",
        "architecture_plan": "",
        "frozen_oracle_path": str(tmp_oracle_dir),
        "blueprint_revision_count": 0,
        "contract_revision_count": 0,
        "logs": []
    }
    res0 = architect_agent(state_turn0)
    contract0 = res0["contract"]

    valid_blueprint_text = """=== BLUEPRINT JSON ===
```json
{
  "authoritative_target_file": "main.py",
  "file_tree": ["main.py"],
  "architecture_summary": "CLI Calculator",
  "files": {
    "main.py": {
      "module_role": "Core",
      "imports": [],
      "code_scaffold": "def calculate(): pass"
    }
  },
  "interface_contracts": [
    {
      "identifier": "calculate",
      "route": "CLI: calculate",
      "method": "POST",
      "target_file": "main.py"
    }
  ],
  "data_models": []
}
```
=== END BLUEPRINT JSON ==="""

    mock_llm2 = MagicMock()
    mock_llm2.invoke.return_value = MagicMock(content=valid_blueprint_text)
    monkeypatch.setattr("backend.agents.architect.get_llm", lambda **kwargs: mock_llm2)

    state_turn1 = {
        "run_id": "test_lifecycle_c",
        "task": "Build calculator CLI",
        "target_language": "python",
        "contract": contract0,
        "specifications": "CLI calculator with calculate method.",
        "architecture_plan": "",
        "frozen_oracle_path": str(tmp_oracle_dir),
        "blueprint_revision_count": 1,
        "contract_revision_count": 1,
        "logs": []
    }
    res1 = architect_agent(state_turn1)
    ok, frozen_c, errors, warnings = seal_and_freeze_contract(res1["contract"], frozen_oracle_path=str(tmp_oracle_dir))
    assert ok is True

    # Audit history check
    history = frozen_c.get("provenance", {}).get("validation_history", [])
    assert len(history) >= 2  # Turn 0 failure + Turn 1 seal
    # Check that Turn 0 error message is in history
    assert any("SCHEMA_VIOLATION" in str(h) for h in history)


# ==============================================================================
# 2. Scenarios E-F: Multi-Turn Repair with Different Errors
# ==============================================================================

def test_scenario_e_and_f_turn_1_new_error_and_turn_2_recovery(tmp_oracle_dir, monkeypatch):
    """
    Scenario E & F:
    Turn 0: JSON error -> REJECTED.
    Turn 1: JSON valid, but missing 'calculate' -> REJECTED with obligation error (NOT JSON error).
    Turn 2: Adds 'calculate' -> FROZEN.
    """
    oracle_file = tmp_oracle_dir / "test_main.py"
    oracle_file.write_text(
        "import main\ndef test_feature():\n    assert hasattr(main, 'calculate')\n",
        encoding="utf-8"
    )

    draft = create_draft_contract(raw_intent="Calculator CLI", target_language="python", domain="CLI_TOOL")

    # Turn 0: JSON broken
    mock_llm0 = MagicMock()
    mock_llm0.invoke.return_value = MagicMock(content="=== BLUEPRINT JSON ===\n{ broken json \n=== END BLUEPRINT JSON ===")
    monkeypatch.setattr("backend.agents.architect.get_llm", lambda **kwargs: mock_llm0)

    state_t0 = {
        "run_id": "test_multi_turn",
        "task": "Build calculator CLI",
        "target_language": "python",
        "contract": draft,
        "specifications": "CLI calculator with calculate method.",
        "architecture_plan": "",
        "frozen_oracle_path": str(tmp_oracle_dir),
        "blueprint_revision_count": 0,
        "contract_revision_count": 0,
        "logs": []
    }
    res0 = architect_agent(state_t0)
    c0 = res0["contract"]
    assert c0["status"] == "REJECTED"

    # Turn 1: JSON valid, but declared interface is 'wrong_fn', missing 'calculate'
    bp_t1 = """=== BLUEPRINT JSON ===
```json
{
  "authoritative_target_file": "main.py",
  "file_tree": ["main.py"],
  "architecture_summary": "CLI Calculator",
  "files": {
    "main.py": {
      "module_role": "Core",
      "imports": [],
      "code_scaffold": "def wrong_fn(): pass"
    }
  },
  "interface_contracts": [
    {
      "identifier": "wrong_fn",
      "route": "CLI: wrong",
      "method": "POST",
      "target_file": "main.py"
    }
  ],
  "data_models": []
}
```
=== END BLUEPRINT JSON ==="""

    mock_llm1 = MagicMock()
    mock_llm1.invoke.return_value = MagicMock(content=bp_t1)
    monkeypatch.setattr("backend.agents.architect.get_llm", lambda **kwargs: mock_llm1)

    state_t1 = {
        "run_id": "test_multi_turn",
        "task": "Build calculator CLI",
        "target_language": "python",
        "contract": c0,
        "specifications": "CLI calculator with calculate method.",
        "architecture_plan": "",
        "frozen_oracle_path": str(tmp_oracle_dir),
        "blueprint_revision_count": 1,
        "contract_revision_count": 1,
        "logs": []
    }
    res1 = architect_agent(state_t1)
    c1 = res1["contract"]
    # Sealing must fail because 'calculate' is missing, NOT because of JSON error
    ok1, res_c1, err1, _ = seal_and_freeze_contract(c1, frozen_oracle_path=str(tmp_oracle_dir))
    assert ok1 is False
    assert res_c1["status"] == ContractStatus.REJECTED.value
    # Crucial: Error must be about missing calculate / oracle obligation, NOT JSON parse error
    assert not any("Blueprint JSON parse failure" in e for e in err1)
    assert any("calculate" in e.lower() or "missing" in e.lower() or "authority_incompatible" in e.lower() for e in err1)

    # Turn 2: Adds 'calculate'
    bp_t2 = """=== BLUEPRINT JSON ===
```json
{
  "authoritative_target_file": "main.py",
  "file_tree": ["main.py"],
  "architecture_summary": "CLI Calculator",
  "files": {
    "main.py": {
      "module_role": "Core",
      "imports": [],
      "code_scaffold": "def calculate(): pass"
    }
  },
  "interface_contracts": [
    {
      "identifier": "calculate",
      "route": "CLI: calculate",
      "method": "POST",
      "target_file": "main.py"
    }
  ],
  "data_models": []
}
```
=== END BLUEPRINT JSON ==="""

    mock_llm2 = MagicMock()
    mock_llm2.invoke.return_value = MagicMock(content=bp_t2)
    monkeypatch.setattr("backend.agents.architect.get_llm", lambda **kwargs: mock_llm2)

    state_t2 = {
        "run_id": "test_multi_turn",
        "task": "Build calculator CLI",
        "target_language": "python",
        "contract": res_c1,
        "specifications": "CLI calculator with calculate method.",
        "architecture_plan": "",
        "frozen_oracle_path": str(tmp_oracle_dir),
        "blueprint_revision_count": 2,
        "contract_revision_count": 2,
        "logs": []
    }
    res2 = architect_agent(state_t2)
    c2 = res2["contract"]
    ok2, res_c2, err2, _ = seal_and_freeze_contract(c2, frozen_oracle_path=str(tmp_oracle_dir))
    assert ok2 is True
    assert res_c2["status"] == ContractStatus.FROZEN.value
    assert len(res_c2.get("provenance", {}).get("contract_sha256", "")) == 64


# ==============================================================================
# 3. Negative Tests: Prevent False Pass & Error Isolation
# ==============================================================================

def test_negative_scenario_persistent_failure_remains_rejected(tmp_oracle_dir):
    """
    Scenario G:
    Turn 0: Error A (Missing interface).
    Turn 1: Error A is NOT fixed (still missing interface).
    Must remain REJECTED.
    """
    oracle_file = tmp_oracle_dir / "test_main.py"
    oracle_file.write_text(
        "import main\ndef test_feature():\n    assert hasattr(main, 'mandatory_symbol')\n",
        encoding="utf-8"
    )

    draft = create_draft_contract(raw_intent="Test", target_language="python", domain="CLI_TOOL")
    # Candidate missing mandatory_symbol
    c = complete_aligned_contract(
        draft_dict=draft,
        data_models=[],
        interface_contracts=[{"interface_id": "IFC-01", "interface_type": "FUNCTION", "identifier": "other", "target_file": "main.py"}],
        testable_assertions=[]
    )
    ok, res_c, errors, _ = seal_and_freeze_contract(c, frozen_oracle_path=str(tmp_oracle_dir))
    assert ok is False
    assert res_c["status"] == ContractStatus.REJECTED.value

    # Turn 1 candidate STILL missing mandatory_symbol
    c_turn1 = complete_aligned_contract(
        draft_dict=res_c,
        data_models=[],
        interface_contracts=[{"interface_id": "IFC-01", "interface_type": "FUNCTION", "identifier": "still_other", "target_file": "main.py"}],
        testable_assertions=[]
    )
    ok1, res_c1, errors1, _ = seal_and_freeze_contract(c_turn1, frozen_oracle_path=str(tmp_oracle_dir))
    assert ok1 is False
    assert res_c1["status"] == ContractStatus.REJECTED.value
    assert any("mandatory_symbol" in str(errors1) or "incompatible" in str(errors1).lower() for e in errors1)


def test_negative_scenario_different_error_isolation(tmp_oracle_dir, monkeypatch):
    """
    Scenario H:
    Turn 0: Error A (JSON parse error).
    Turn 1: Error B (Missing interface).
    active_validation_errors on Turn 1 must contain ONLY [B].
    validation_history on Turn 1 must contain both [A] and [B].
    """
    oracle_file = tmp_oracle_dir / "test_main.py"
    oracle_file.write_text(
        "import main\ndef test_feature():\n    assert hasattr(main, 'mandatory_fn')\n",
        encoding="utf-8"
    )

    draft = create_draft_contract(raw_intent="Test", target_language="python", domain="CLI_TOOL")
    # Turn 0: JSON error
    mock_llm0 = MagicMock()
    mock_llm0.invoke.return_value = MagicMock(content="=== BLUEPRINT JSON ===\n{ broken \n=== END BLUEPRINT JSON ===")
    monkeypatch.setattr("backend.agents.architect.get_llm", lambda **kwargs: mock_llm0)

    state_t0 = {
        "run_id": "test_isolation",
        "task": "Test",
        "target_language": "python",
        "contract": draft,
        "specifications": "Specs",
        "architecture_plan": "",
        "frozen_oracle_path": str(tmp_oracle_dir),
        "blueprint_revision_count": 0,
        "contract_revision_count": 0,
        "logs": []
    }
    res0 = architect_agent(state_t0)
    c0 = res0["contract"]

    # Turn 1: Valid JSON, but missing mandatory_fn
    bp_t1 = """=== BLUEPRINT JSON ===
```json
{
  "authoritative_target_file": "main.py",
  "file_tree": ["main.py"],
  "architecture_summary": "Test",
  "files": {
    "main.py": {
      "module_role": "Core",
      "imports": [],
      "code_scaffold": "def other(): pass"
    }
  },
  "interface_contracts": [
    {
      "identifier": "other",
      "route": "CLI: other",
      "method": "POST",
      "target_file": "main.py"
    }
  ],
  "data_models": []
}
```
=== END BLUEPRINT JSON ==="""

    mock_llm1 = MagicMock()
    mock_llm1.invoke.return_value = MagicMock(content=bp_t1)
    monkeypatch.setattr("backend.agents.architect.get_llm", lambda **kwargs: mock_llm1)

    state_t1 = {
        "run_id": "test_isolation",
        "task": "Test",
        "target_language": "python",
        "contract": c0,
        "specifications": "Specs",
        "architecture_plan": "",
        "frozen_oracle_path": str(tmp_oracle_dir),
        "blueprint_revision_count": 1,
        "contract_revision_count": 1,
        "logs": []
    }
    res1 = architect_agent(state_t1)
    c1 = res1["contract"]
    ok1, res_c1, errors1, _ = seal_and_freeze_contract(c1, frozen_oracle_path=str(tmp_oracle_dir))
    assert ok1 is False

    active_errs = res_c1.get("provenance", {}).get("active_validation_errors", [])
    val_history = res_c1.get("provenance", {}).get("validation_history", [])

    # Active errors on Turn 1 must NOT contain JSON parse error
    assert not any("Blueprint JSON parse failure" in e for e in active_errs)
    # Validation history must retain the Turn 0 JSON error
    assert any("Blueprint JSON parse failure" in str(h) for h in val_history)
    # And validation history must also contain Turn 1 failure
    assert any("CONTRACT_SEAL" in str(h) for h in val_history)


# ==============================================================================
# 4. Telemetry Verification
# ==============================================================================

def test_telemetry_forensic_fields_in_graph_node(tmp_oracle_dir):
    """
    Verifies that architect_validator_node properly structures active, historical,
    and resolved error counts for telemetry logging.
    """
    oracle_file = tmp_oracle_dir / "test_main.py"
    oracle_file.write_text(
        "import main\ndef test_feature():\n    assert hasattr(main, 'calculate')\n",
        encoding="utf-8"
    )

    draft = create_draft_contract(raw_intent="Test", target_language="python", domain="CLI_TOOL")
    # Simulate contract with historical failure and now clean candidate
    c = complete_aligned_contract(
        draft_dict=draft,
        data_models=[],
        interface_contracts=[{"interface_id": "IFC-01", "interface_type": "FUNCTION", "identifier": "calculate", "target_file": "main.py"}],
        testable_assertions=[{
            "assertion_id": "AST-01",
            "linked_req_id": "REQ-01",
            "linked_interface_id": "IFC-01",
            "test_scenario": "Calculate",
            "target_symbol": "calculate",
            "input_fixture": "calculate()",
            "expected_outcome": {"outcome_type": "VALUE_EQUALS", "value": 0}
        }]
    )
    # Inject fake previous history
    c["provenance"]["validation_history"] = [
        {"timestamp": "2026-09-14T00:00:00", "phase": "ARCHITECT", "status": "REJECTED", "errors": ["OLD_RESOLVED_SYNTAX_ERROR"]}
    ]

    valid_blueprint_text = """=== BLUEPRINT JSON ===
```json
{
  "authoritative_target_file": "main.py",
  "file_tree": ["main.py"],
  "architecture_summary": "Test",
  "files": {
    "main.py": {
      "module_role": "Core",
      "imports": [],
      "code_scaffold": "def calculate(): pass"
    }
  },
  "interface_contracts": [
    {
      "identifier": "calculate",
      "route": "CLI: calculate",
      "method": "POST",
      "target_file": "main.py"
    }
  ],
  "data_models": []
}
```
=== END BLUEPRINT JSON ==="""

    state = {
        "run_id": "test_telemetry",
        "task": "Test",
        "target_language": "python",
        "contract": c,
        "specifications": "Specs",
        "architecture_plan": valid_blueprint_text,
        "frozen_oracle_path": str(tmp_oracle_dir),
        "contract_revision_count": 1,
        "repair_attempt_counts": {"architect": 1},
        "logs": []
    }

    res = architect_validator_node(state)
    assert res.get("contract_status") == ContractStatus.FROZEN.value
    assert res.get("contract_validation_errors") == []
    frozen_c = res["contract"]
    prov = frozen_c.get("provenance", {})
    # Historical record is preserved
    assert any("OLD_RESOLVED_SYNTAX_ERROR" in str(h) for h in prov.get("validation_history", []))
    # Active errors are clean
    assert prov.get("active_validation_errors") == []
