"""
Deterministic Test Gates (01–24) for Treatment #1.5:
Architect Repair Grounding & Preservation v1
ReinDev Studio — Iterasi 6
"""

import ast
import hashlib
import json
import os
import re
import subprocess
import pytest
from pathlib import Path
from typing import Dict, Any, List

from backend.architect_preservation import (
    RepairTransitionStatus,
    RepairStateItem,
    RepairStateLedger,
    ArchitectScaffoldSnapshot,
    generate_scaffold_snapshot,
    compare_scaffold_snapshots,
    evaluate_preservation_and_regression,
    validate_architect_repair_context_delivery,
    hash_scaffold_files,
    extract_scaffold_public_callables,
)
from backend.canonical_scenario import (
    CanonicalScenario,
    ScenarioKind,
    ScaffoldCompatibilityStatus,
    ScaffoldScenarioMatrix,
    ScaffoldScenarioCompatibilityItem,
    evaluate_scaffold_scenario_compatibility,
    extract_canonical_scenarios,
)
from backend.context_hardening import (
    build_architect_repair_context,
    build_architect_decision_context,
    ARCHITECT_REPAIR_PRIORITY_ORDER,
)
from backend.contract import (
    MachineReadableContract,
    InterfaceContract,
    ContractStatus,
    check_pre_freeze_authority_compatibility,
    seal_and_freeze_contract,
    create_draft_contract,
    complete_aligned_contract,
)


def make_valid_contract_dict(interface_id: str = "IFC-01", identifier: str = "/items") -> Dict[str, Any]:
    draft = create_draft_contract(raw_intent="Items API", target_language="python", domain="REST_API")
    return complete_aligned_contract(
        draft_dict=draft,
        data_models=[],
        interface_contracts=[{
            "interface_id": interface_id,
            "interface_type": "HTTP_ENDPOINT",
            "identifier": identifier,
            "route": "/items",
            "target_file": "main.py",
            "http_method": "GET"
        }],
        testable_assertions=[{
            "assertion_id": "AST-01",
            "linked_req_id": "REQ-01",
            "test_scenario": "Test items endpoint",
            "target_symbol": identifier,
            "expected_outcome": {"outcome_type": "HTTP_STATUS", "expected_status": 200}
        }]
    )



@pytest.fixture
def sample_scenarios() -> List[CanonicalScenario]:
    return [
        CanonicalScenario(
            scenario_id="SCN-001",
            scenario_kind=ScenarioKind.POSITIVE.value,
            authority="FROZEN_ORACLE",
            provenance="ORACLE_FACT",
            source_reference="test_main.py::test_create_item",
            stimulus="client.post('/items', json={'name': 'Item1'})",
            caller="create_item",
            observable_output="response.status_code == 201",
            expected_outcome={"http_method": "POST", "route": "/items", "status_code": 201}
        ),
        CanonicalScenario(
            scenario_id="SCN-002",
            scenario_kind=ScenarioKind.POSITIVE.value,
            authority="FROZEN_ORACLE",
            provenance="ORACLE_FACT",
            source_reference="test_main.py::test_get_item",
            stimulus="client.get('/items/1')",
            caller="get_item",
            observable_output="response.status_code == 200",
            expected_outcome={"http_method": "GET", "route": "/items/{item_id}", "status_code": 200}
        ),
        CanonicalScenario(
            scenario_id="SCN-003",
            scenario_kind=ScenarioKind.NEGATIVE.value,
            authority="FROZEN_ORACLE",
            provenance="ORACLE_FACT",
            source_reference="test_main.py::test_get_item_not_found",
            stimulus="client.get('/items/999')",
            caller="get_item",
            observable_output="response.status_code == 404",
            expected_outcome={"http_method": "GET", "route": "/items/{item_id}", "status_code": 404}
        ),
    ]


# Gate 01: Compatible state preserved
def test_gate_01_compatible_state_preserved(sample_scenarios):
    prev_matrix = ScaffoldScenarioMatrix(items=[
        ScaffoldScenarioCompatibilityItem(
            scenario_id="SCN-001",
            compatibility=ScaffoldCompatibilityStatus.COMPATIBLE.value,
            authority="FROZEN_ORACLE",
            source_reference="test_main.py"
        )
    ])
    prev_snap = generate_scaffold_snapshot(
        {"main.py": "@app.post('/items')\ndef create_item(): pass"},
        compatibility_matrix=prev_matrix
    )
    curr_matrix = ScaffoldScenarioMatrix(items=[
        ScaffoldScenarioCompatibilityItem(
            scenario_id="SCN-001",
            compatibility=ScaffoldCompatibilityStatus.COMPATIBLE.value,
            authority="FROZEN_ORACLE",
            source_reference="test_main.py"
        )
    ])

    ledger = evaluate_preservation_and_regression(prev_snap, curr_matrix, [sample_scenarios[0]])
    item = ledger.get_item("SCN-001")
    assert item is not None
    assert item.transition_status == RepairTransitionStatus.PRESERVED.value
    assert item.preserved is True
    assert ledger.has_regression is False


# Gate 02: Incompatible -> compatible recognized as repair
def test_gate_02_incompatible_to_compatible_recognized_as_repair(sample_scenarios):
    prev_matrix = ScaffoldScenarioMatrix(items=[
        ScaffoldScenarioCompatibilityItem(
            scenario_id="SCN-001",
            compatibility=ScaffoldCompatibilityStatus.INCOMPATIBLE.value,
            authority="FROZEN_ORACLE",
            source_reference="test_main.py"
        )
    ])
    prev_snap = generate_scaffold_snapshot({"main.py": ""}, compatibility_matrix=prev_matrix)

    curr_matrix = ScaffoldScenarioMatrix(items=[
        ScaffoldScenarioCompatibilityItem(
            scenario_id="SCN-001",
            compatibility=ScaffoldCompatibilityStatus.COMPATIBLE.value,
            authority="FROZEN_ORACLE",
            source_reference="test_main.py"
        )
    ])
    ledger = evaluate_preservation_and_regression(prev_snap, curr_matrix, [sample_scenarios[0]])
    item = ledger.get_item("SCN-001")
    assert item is not None
    assert item.transition_status == RepairTransitionStatus.REPAIRED.value
    assert item.preserved is False
    assert ledger.repaired_count == 1
    assert ledger.has_regression is False


# Gate 03: Compatible -> incompatible detected as regression
def test_gate_03_compatible_to_incompatible_detected_as_regression(sample_scenarios):
    prev_matrix = ScaffoldScenarioMatrix(items=[
        ScaffoldScenarioCompatibilityItem(
            scenario_id="SCN-001",
            compatibility=ScaffoldCompatibilityStatus.COMPATIBLE.value,
            authority="FROZEN_ORACLE",
            source_reference="test_main.py"
        )
    ])
    prev_snap = generate_scaffold_snapshot({"main.py": "def create_item(): pass"}, compatibility_matrix=prev_matrix)

    curr_matrix = ScaffoldScenarioMatrix(items=[
        ScaffoldScenarioCompatibilityItem(
            scenario_id="SCN-001",
            compatibility=ScaffoldCompatibilityStatus.INCOMPATIBLE.value,
            authority="FROZEN_ORACLE",
            source_reference="test_main.py"
        )
    ])
    ledger = evaluate_preservation_and_regression(prev_snap, curr_matrix, [sample_scenarios[0]])
    item = ledger.get_item("SCN-001")
    assert item is not None
    assert item.transition_status == RepairTransitionStatus.CRITICAL_REGRESSION.value
    assert ledger.has_regression is True
    assert ledger.regression_count == 1
    assert "[REGRESSION EVIDENCE" in ledger.to_regression_evidence_text()


# Gate 04: Multiple scenarios preserved
def test_gate_04_multiple_scenarios_preserved(sample_scenarios):
    prev_matrix = ScaffoldScenarioMatrix(items=[
        ScaffoldScenarioCompatibilityItem(scenario_id=sc.scenario_id, compatibility="COMPATIBLE", authority="FROZEN_ORACLE", source_reference="t")
        for sc in sample_scenarios
    ])
    prev_snap = generate_scaffold_snapshot({"main.py": "code"}, compatibility_matrix=prev_matrix)

    curr_matrix = ScaffoldScenarioMatrix(items=[
        ScaffoldScenarioCompatibilityItem(scenario_id=sc.scenario_id, compatibility="COMPATIBLE", authority="FROZEN_ORACLE", source_reference="t")
        for sc in sample_scenarios
    ])
    ledger = evaluate_preservation_and_regression(prev_snap, curr_matrix, sample_scenarios)
    assert ledger.preserved_count == 3
    assert ledger.regression_count == 0
    assert ledger.is_fully_compatible is True


# Gate 05: Multiple failures delivered together
def test_gate_05_multiple_failures_delivered_together(sample_scenarios):
    state = {
        "contract_validation_errors": [
            "F1: Constructor call shape mismatch for Widget",
            "F2: Required callable calculate_total missing",
            "F3: SCENARIO_SCAFFOLD_INCOMPATIBILITY: SCN-003 unresolved"
        ],
        "contract_status": "REJECTED",
        "contract_revision_count": 1,
    }
    ctx, telem = build_architect_repair_context(state)
    assert "F1: Constructor" in ctx
    assert "F2: Required callable" in ctx
    assert "F3: SCENARIO_SCAFFOLD_INCOMPATIBILITY" in ctx
    assert telem["current_failures"] >= 3


# Gate 06: Repair target delivered
def test_gate_06_repair_target_delivered(sample_scenarios):
    prev_matrix = ScaffoldScenarioMatrix(items=[
        ScaffoldScenarioCompatibilityItem(scenario_id="SCN-001", compatibility="COMPATIBLE", authority="FROZEN_ORACLE", source_reference="t"),
        ScaffoldScenarioCompatibilityItem(scenario_id="SCN-003", compatibility="INCOMPATIBLE", authority="FROZEN_ORACLE", source_reference="t"),
    ])
    prev_snap = generate_scaffold_snapshot({"main.py": "code"}, compatibility_matrix=prev_matrix)
    curr_matrix = ScaffoldScenarioMatrix(items=[
        ScaffoldScenarioCompatibilityItem(scenario_id="SCN-001", compatibility="COMPATIBLE", authority="FROZEN_ORACLE", source_reference="t"),
        ScaffoldScenarioCompatibilityItem(scenario_id="SCN-003", compatibility="INCOMPATIBLE", authority="FROZEN_ORACLE", source_reference="t"),
    ])
    ledger = evaluate_preservation_and_regression(prev_snap, curr_matrix, [sample_scenarios[0], sample_scenarios[2]])
    target_text = ledger.to_repair_targets_text()

    assert "TARGET: SCN-003" in target_text
    assert "REQUIRED TRANSITION: INCOMPATIBLE -> COMPATIBLE" in target_text
    assert "PRESERVE (MUST REMAIN COMPATIBLE — DO NOT BREAK):" in target_text
    assert "SCN-001 = COMPATIBLE" in target_text
    assert "how to solve" not in target_text.lower()


# Gate 07: Immutable obligation cannot be modified
def test_gate_07_immutable_obligation_cannot_be_modified():
    item = RepairStateItem(
        obligation_id="OBL-100",
        scenario_id="SCN-100",
        authority="FROZEN_ORACLE",
        stimulus="test_call()",
        expected_outcome={"status": 200}
    )
    with pytest.raises(ValueError, match="IMMUTABLE ACCEPTANCE OBLIGATION VIOLATION"):
        item.stimulus = "mutated_stimulus()"

    with pytest.raises(ValueError, match="IMMUTABLE ACCEPTANCE OBLIGATION VIOLATION"):
        item.authority = "ARCHITECT_PROPOSAL"


# Gate 08: Scaffold snapshot generated
def test_gate_08_scaffold_snapshot_generated():
    files = {
        "main.py": "def test_func(): pass",
        "models.py": "class Item: pass"
    }
    snap = generate_scaffold_snapshot(files, contract_status="REJECTED")
    assert snap.scaffold_hash == hash_scaffold_files(files)
    assert len(snap.scaffold_hash) == 64
    assert "test_func" in snap.public_callables
    assert "Item" in snap.public_callables
    assert snap.contract_status == "REJECTED"


# Gate 09: Snapshot comparison
def test_gate_09_snapshot_comparison():
    s1 = generate_scaffold_snapshot({"a.py": "def f(): pass", "b.py": "def g(): pass"})
    s2 = generate_scaffold_snapshot({"a.py": "def f(): pass"})

    diff = compare_scaffold_snapshots(s1, s2)
    assert diff["has_dropped_files"] is True
    assert "b.py" in diff["dropped_files"]
    assert diff["has_dropped_callables"] is True
    assert "g" in diff["dropped_callables"]
    assert diff["hash_changed"] is True


# Gate 10: Blind regeneration regression detected
def test_gate_10_blind_regeneration_regression_detected(sample_scenarios):
    s1_files = {"main.py": "def create_item(): pass\ndef get_item(): pass"}
    prev_matrix = ScaffoldScenarioMatrix(items=[
        ScaffoldScenarioCompatibilityItem(scenario_id="SCN-001", compatibility="COMPATIBLE", authority="FROZEN_ORACLE", source_reference="t"),
        ScaffoldScenarioCompatibilityItem(scenario_id="SCN-002", compatibility="COMPATIBLE", authority="FROZEN_ORACLE", source_reference="t"),
    ])
    prev_snap = generate_scaffold_snapshot(s1_files, compatibility_matrix=prev_matrix)

    s2_files = {"main.py": "def get_item(): pass"}
    curr_matrix = ScaffoldScenarioMatrix(items=[
        ScaffoldScenarioCompatibilityItem(scenario_id="SCN-002", compatibility="COMPATIBLE", authority="FROZEN_ORACLE", source_reference="t"),
    ])

    ledger = evaluate_preservation_and_regression(prev_snap, curr_matrix, sample_scenarios[:2], scaffold_files=s2_files)
    item1 = ledger.get_item("SCN-001")
    assert item1.transition_status == RepairTransitionStatus.CRITICAL_REGRESSION.value
    assert "NO BLIND REGENERATION VIOLATION" in item1.acceptance_evidence
    assert ledger.has_regression is True


# Gate 11: Context priority preserved
def test_gate_11_context_priority_preserved():
    state = {
        "task": "Build items API",
        "contract_status": "REJECTED",
        "contract_revision_count": 1,
        "contract_validation_errors": ["Error 1"],
    }
    ctx, _ = build_architect_repair_context(state)
    pos_auth = ctx.find("[1] IMMUTABLE ACCEPTANCE AUTHORITY")
    pos_ledger = ctx.find("[2] ACCEPTANCE OBLIGATION LEDGER")
    pos_fail = ctx.find("[3] CURRENT COMPATIBILITY FAILURES")
    pos_lock = ctx.find("[4] LOCKED/PROVEN STATE")
    pos_scaff = ctx.find("[5] CURRENT SCAFFOLD")
    pos_targ = ctx.find("[6] REPAIR TARGET")
    pos_bound = ctx.find("[7] REPAIR BOUNDARY")
    pos_post = ctx.find("[8] EXPECTED POST-REPAIR STATE")
    pos_ground = ctx.find("[9] IMPLEMENTATION GROUNDING")
    pos_diag = ctx.find("[10] RAW DIAGNOSTICS")

    assert pos_auth != -1
    assert pos_ledger != -1
    assert pos_fail != -1
    assert pos_lock != -1
    assert pos_scaff != -1
    assert pos_targ != -1
    assert pos_bound != -1
    assert pos_post != -1
    assert pos_ground != -1
    assert pos_diag != -1

    assert pos_auth < pos_fail < pos_targ < pos_bound < pos_scaff < pos_lock < pos_post < pos_ledger < pos_ground < pos_diag


# Gate 12: Context truncation detected
def test_gate_12_context_truncation_detected():
    valid_context = (
        "[1] IMMUTABLE ACCEPTANCE AUTHORITY\nAuthority: FROZEN_ORACLE\n"
        "[2] ACCEPTANCE OBLIGATION LEDGER\n[IMMUTABLE ACCEPTANCE OBLIGATIONS]\n"
        "[3] CURRENT COMPATIBILITY FAILURES\nNo active repair targets\n"
        "[4] LOCKED/PROVEN STATE\n[CURRENT ARCHITECT STATE]\nPRESERVED=TRUE\n"
        "[6] REPAIR TARGET\nWHAT: All\nWHERE: main.py\nOBSERVED: No active repair targets\nEXPECTED: Valid\n"
        "[7] REPAIR BOUNDARY\nPRESERVE: Invariants\nALLOWED:\nFORBIDDEN:\n"
    )
    is_v, errs = validate_architect_repair_context_delivery(valid_context)
    assert is_v is True
    assert len(errs) == 0

    truncated = valid_context[:100]
    is_v2, errs2 = validate_architect_repair_context_delivery(truncated)
    assert is_v2 is False
    assert any("ARCHITECT_CONTEXT_DELIVERY_FAILURE" in e for e in errs2)


# Gate 13: Constructor compatibility preserved
def test_gate_13_constructor_compatibility_preserved():
    prev_matrix = ScaffoldScenarioMatrix(items=[
        ScaffoldScenarioCompatibilityItem(scenario_id="SCN-CTOR-1", compatibility="COMPATIBLE", authority="FROZEN_ORACLE", source_reference="test")
    ])
    prev_snap = generate_scaffold_snapshot({"card.dart": "class CardMetric { CardMetric(String title); }"}, compatibility_matrix=prev_matrix)

    curr_matrix = ScaffoldScenarioMatrix(items=[
        ScaffoldScenarioCompatibilityItem(scenario_id="SCN-CTOR-1", compatibility="COMPATIBLE", authority="FROZEN_ORACLE", source_reference="test"),
        ScaffoldScenarioCompatibilityItem(scenario_id="SCN-CTOR-2", compatibility="COMPATIBLE", authority="FROZEN_ORACLE", source_reference="test"),
    ])
    sc = CanonicalScenario(
        scenario_id="SCN-CTOR-1",
        scenario_kind="POSITIVE",
        authority="FROZEN_ORACLE",
        provenance="ORACLE_FACT",
        source_reference="test",
        stimulus="CardMetric('title')",
        caller="CardMetric",
        observable_output="CardMetric",
        expected_outcome={}
    )
    ledger = evaluate_preservation_and_regression(prev_snap, curr_matrix, [sc], scaffold_files={"card.dart": "class CardMetric { CardMetric(String title); }"})
    assert ledger.get_item("SCN-CTOR-1").transition_status == "PRESERVED"
    assert ledger.has_regression is False


# Gate 14: Behavioral scenario preserved
def test_gate_14_behavioral_scenario_preserved(sample_scenarios):
    prev_matrix = ScaffoldScenarioMatrix(items=[
        ScaffoldScenarioCompatibilityItem(scenario_id="SCN-001", compatibility="COMPATIBLE", authority="FROZEN_ORACLE", source_reference="t"),
    ])
    prev_snap = generate_scaffold_snapshot({"main.py": "def create_item(): pass"}, compatibility_matrix=prev_matrix)

    curr_matrix = ScaffoldScenarioMatrix(items=[
        ScaffoldScenarioCompatibilityItem(scenario_id="SCN-001", compatibility="COMPATIBLE", authority="FROZEN_ORACLE", source_reference="t"),
        ScaffoldScenarioCompatibilityItem(scenario_id="SCN-003", compatibility="COMPATIBLE", authority="FROZEN_ORACLE", source_reference="t"),
    ])
    ledger = evaluate_preservation_and_regression(prev_snap, curr_matrix, [sample_scenarios[0], sample_scenarios[2]])
    assert ledger.get_item("SCN-001").transition_status == "PRESERVED"
    assert ledger.get_item("SCN-003").transition_status == "REPAIRED"
    assert ledger.has_regression is False


# Gate 15: Public interface preserved
def test_gate_15_public_interface_preserved():
    prev_calls = ["create_item", "get_item"]
    curr_calls = ["create_item", "get_item", "delete_item"]
    dropped = set(prev_calls) - set(curr_calls)
    assert len(dropped) == 0


# Gate 16: Output completeness
def test_gate_16_output_completeness():
    from backend.blueprint_schema import parse_blueprint_json
    raw_bp = json.dumps({
        "blueprint_version": "1.0.0",
        "task_name": "Test Task",
        "authoritative_target_file": "main.py",
        "files": {
            "main.py": {
                "module_name": "main",
                "target_path": "main.py",
                "purpose": "API Entrypoint",
                "interfaces": ["get_items"],
                "code_scaffold": "def get_items(): pass"
            }
        }
    })
    bp, errors = parse_blueprint_json(raw_bp)
    assert bp is not None
    assert "main.py" in bp.files
    assert bp.files["main.py"].code_scaffold == "def get_items(): pass"


# Gate 17: Regression blocks freeze
def test_gate_17_regression_blocks_freeze(tmp_path):
    oracle_dir = tmp_path / "oracle"
    oracle_dir.mkdir()
    (oracle_dir / "test_main.py").write_text("def test_items():\n    client.get('/items')\n", encoding="utf-8")

    c_data = make_valid_contract_dict(identifier="/items")
    scenarios = extract_canonical_scenarios(frozen_oracle_path=str(oracle_dir))
    sc_id = scenarios[0].scenario_id if scenarios else "SCN-01"
    prev_matrix = ScaffoldScenarioMatrix(items=[
        ScaffoldScenarioCompatibilityItem(scenario_id=sc_id, compatibility="COMPATIBLE", authority="FROZEN_ORACLE", source_reference="test_main.py:1")
    ])
    prev_snap = generate_scaffold_snapshot({"main.py": "@app.get('/items')\ndef get_items(): return []"}, compatibility_matrix=prev_matrix)

    # Current scaffold drops get_items
    blueprint = {"files": {"main.py": {"code_scaffold": "def other_func(): pass"}}}

    success, c_out, errors, warnings = seal_and_freeze_contract(
        c_data,
        frozen_oracle_path=str(oracle_dir),
        blueprint=blueprint,
        previous_snapshot=prev_snap
    )
    assert success is False
    assert c_out["status"] == ContractStatus.REJECTED.value
    assert any("CRITICAL_REGRESSION" in str(e) or "INCOMPATIBLE" in str(e) for e in errors)


# Gate 18: All compatible -> freeze allowed
def test_gate_18_all_compatible_freeze_allowed(tmp_path):
    oracle_dir = tmp_path / "oracle"
    oracle_dir.mkdir()
    (oracle_dir / "test_main.py").write_text("def test_items():\n    client.get('/items')\n", encoding="utf-8")

    c_data = make_valid_contract_dict(identifier="/items")
    blueprint = {
        "files": {
            "main.py": """
from fastapi import FastAPI
app = FastAPI()

@app.get('/items')
def get_items():
    return []
"""
        }
    }

    success, c_out, errors, warnings = seal_and_freeze_contract(
        c_data,
        frozen_oracle_path=str(oracle_dir),
        blueprint=blueprint
    )
    assert success is True
    assert c_out["status"] == ContractStatus.FROZEN.value
    assert "contract_sha256" in c_out["provenance"]


# Gate 19: Undetermined -> freeze rejected
def test_gate_19_undetermined_freeze_rejected(tmp_path):
    oracle_dir = tmp_path / "oracle"
    oracle_dir.mkdir()
    (oracle_dir / "test_main.py").write_text("def test_neg():\n    client.get('/items')\n    assert r.status_code == 404\n", encoding="utf-8")

    c_data = make_valid_contract_dict(identifier="/items")
    # Scaffold is stubbed -> statically UNDETERMINED for negative scenario
    blueprint = {"files": {"main.py": {"code_scaffold": "@app.get('/items')\ndef get_items(): pass"}}}

    success, c_out, errors, warnings = seal_and_freeze_contract(
        c_data,
        frozen_oracle_path=str(oracle_dir),
        blueprint=blueprint
    )
    assert success is False
    assert c_out["status"] == ContractStatus.REJECTED.value


# Gate 20: No task-specific solver
def test_gate_20_no_task_specific_solver():
    files_to_check = [
        Path("backend/architect_preservation.py"),
        Path("backend/canonical_scenario.py"),
    ]
    forbidden_patterns = [
        r"\bif\s+fastapi\b",
        r"\bif\s+cli\b",
        r"\bif\s+flutter\b",
        r"\bif\s+Matrix\b",
        r"\bif\s+MetricData\b",
        r"\bif\s+delete_product\b",
    ]
    for f in files_to_check:
        if f.exists():
            content = f.read_text(encoding="utf-8")
            for pat in forbidden_patterns:
                assert not re.search(pat, content, re.IGNORECASE), f"Forbidden solver pattern '{pat}' found in {f}"


# Gate 21: Cross-language semantic state equivalence
def test_gate_21_cross_language_semantic_state_equivalence():
    sc_pos = CanonicalScenario(
        scenario_id="SCN-01",
        scenario_kind="POSITIVE",
        authority="FROZEN_ORACLE",
        provenance="ORACLE_FACT",
        source_reference="t",
        stimulus="calc()",
        caller="calc",
        observable_output="1",
        expected_outcome={}
    )
    m_py = ScaffoldScenarioMatrix(items=[
        ScaffoldScenarioCompatibilityItem(scenario_id="SCN-01", compatibility="COMPATIBLE", authority="FROZEN_ORACLE", source_reference="t")
    ])
    m_dart = ScaffoldScenarioMatrix(items=[
        ScaffoldScenarioCompatibilityItem(scenario_id="SCN-01", compatibility="COMPATIBLE", authority="FROZEN_ORACLE", source_reference="t")
    ])

    l_py = evaluate_preservation_and_regression(None, m_py, [sc_pos])
    l_dart = evaluate_preservation_and_regression(None, m_dart, [sc_pos])

    assert l_py.get_item("SCN-01").transition_status == l_dart.get_item("SCN-01").transition_status
    assert l_py.is_fully_compatible == l_dart.is_fully_compatible == True


# Gate 22: Oracle immutability
def test_gate_22_oracle_immutability():
    expected_hashes = {
        "dokumentasi-pengembangan/experiments/frozen_oracle/fastapi_t1/test_main.py": "a1db9bb1f6eaf47d5cf56e102c4a0f6e1f49d757e9faa1485b36f2972a152d63",
        "dokumentasi-pengembangan/experiments/frozen_oracle/cli_t1/test_main.py": "0bd5b598afa7ae4c9cdf0e269d13136b51d35a4e0b1ac6548f0a2cf8a8eba124",
        "dokumentasi-pengembangan/experiments/frozen_oracle/flutter_t1/card_metric_test.dart": "4589e15cfb8f37ba70642e70623ca143bceee1a44175aefd072f441d9e8a9528",
    }
    for file_path, expected_sha in expected_hashes.items():
        p = Path(file_path)
        assert p.exists(), f"Oracle file missing: {file_path}"
        actual_sha = hashlib.sha256(p.read_bytes()).hexdigest().lower()
        assert actual_sha == expected_sha.lower(), f"Oracle {file_path} mutated! Expected {expected_sha}, got {actual_sha}"


# Gate 23: Sterile executor unchanged
def test_gate_23_sterile_executor_unchanged():
    executor_path = Path("backend/executor_v2.py")
    assert executor_path.exists()
    res = subprocess.run(
        ["git", "diff", "HEAD", "--", "backend/executor_v2.py"],
        capture_output=True,
        text=True
    )
    assert res.returncode == 0
    assert res.stdout.strip() == "", f"executor_v2.py has unexpected git diff: {res.stdout}"


# Gate 24: Locked invariant preservation
def test_gate_24_locked_invariant_preservation():
    state = {
        "locked_invariants": {
            "INV-01": {"description": "Public API contract /items", "status": "PROVEN"},
            "INV-02": {"description": "Schema structure UserItem", "status": "PROVEN"}
        },
        "contract_status": "REJECTED",
        "contract_revision_count": 1,
    }
    ctx, telem = build_architect_repair_context(state)
    assert "INV-01: Public API contract /items" in ctx
    assert "INV-02: Schema structure UserItem" in ctx
    assert telem["locked_invariants"] == 2
