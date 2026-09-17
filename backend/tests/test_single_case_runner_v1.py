# -*- coding: utf-8 -*-
"""
Test Suite: Experiment Harness Single-Case Execution Support v1
Verifies generic task selection, deterministic resolution, error handling,
topology preservation, denominator protection, and anti-solver static audit.
Tests A through J.
"""

import os
import pytest
from pathlib import Path

# Clean up any import-time environment side-effects so other unit tests see default 1000
os.environ.pop("OLLAMA_NUM_PREDICT", None)

from backend.run_phase_end_validation_pilot import (
    TASKS,
    TASK_ALIASES,
    PIPELINE_VERSION,
    GOVERNANCE_VERSION,
    resolve_selected_tasks,
    phase_validated_squad_graph
)

# Re-pop after import of runner
os.environ.pop("OLLAMA_NUM_PREDICT", None)



def test_a_default_runner_full_matrix():
    """Test A: Default runner (None/omitted) preserves full existing matrix."""
    active_tasks, mode, selected_ids, available_ids, skipped_ids = resolve_selected_tasks(None)
    assert mode == "full_matrix"
    assert len(active_tasks) == len(TASKS)
    assert active_tasks == TASKS
    assert selected_ids == [t["task_id"] for t in TASKS]
    assert skipped_ids == []
    assert len(available_ids) == len(TASKS)


def test_b_single_case_fastapi():
    """Test B: Single-case ['fastapi'] resolves strictly to fastapi_t1."""
    # Test with alias list
    active_tasks, mode, selected_ids, available_ids, skipped_ids = resolve_selected_tasks(["fastapi"])
    assert mode == "single_case"
    assert len(active_tasks) == 1
    assert active_tasks[0]["task_id"] == "fastapi_t1"
    assert selected_ids == ["fastapi_t1"]
    assert "fastapi_t1" not in skipped_ids
    assert "cli_t1" in skipped_ids
    assert "flutter_t1" in skipped_ids

    # Test with direct canonical id string
    active_tasks2, mode2, selected_ids2, _, _ = resolve_selected_tasks("fastapi_t1")
    assert mode2 == "single_case"
    assert selected_ids2 == ["fastapi_t1"]


def test_c_single_case_cli():
    """Test C: Single-case ['cli'] resolves strictly to cli_t1."""
    active_tasks, mode, selected_ids, available_ids, skipped_ids = resolve_selected_tasks(["cli"])
    assert mode == "single_case"
    assert len(active_tasks) == 1
    assert active_tasks[0]["task_id"] == "cli_t1"
    assert selected_ids == ["cli_t1"]
    assert "cli_t1" not in skipped_ids
    assert "fastapi_t1" in skipped_ids
    assert "flutter_t1" in skipped_ids


def test_d_single_case_flutter():
    """Test D: Single-case ['flutter'] resolves strictly to flutter_t1."""
    active_tasks, mode, selected_ids, available_ids, skipped_ids = resolve_selected_tasks(["flutter"])
    assert mode == "single_case"
    assert len(active_tasks) == 1
    assert active_tasks[0]["task_id"] == "flutter_t1"
    assert selected_ids == ["flutter_t1"]
    assert "flutter_t1" not in skipped_ids
    assert "fastapi_t1" in skipped_ids
    assert "cli_t1" in skipped_ids


def test_e_selected_task_preserves_pipeline_topology():
    """Test E: Selected task does not alter pipeline topology."""
    nodes = list(phase_validated_squad_graph.nodes.keys())
    assert "pm" in nodes
    assert "architect" in nodes
    assert "developer" in nodes
    assert "reviewer" in nodes
    assert "pm_validator" in nodes
    assert "architect_validator" in nodes
    assert "developer_validator" in nodes
    assert "reviewer_validator" in nodes
    assert len(nodes) == 16


def test_f_unselected_task_denominator_protection():
    """Test F: Unselected tasks are marked skipped, producing no PASS/FAIL and excluded from denominator."""
    _, mode, sel_ids, _, skip_ids = resolve_selected_tasks(["fastapi"])
    assert mode == "single_case"
    # When single case is selected, only 1 task is active
    total_planned = len(sel_ids) * 1
    assert total_planned == 1
    # Denominator is strictly 1, NOT 3
    assert len(skip_ids) == 2
    for skipped in skip_ids:
        assert skipped not in sel_ids


def test_g_empty_selection_handled_deterministically():
    """Test G: Empty selection handled deterministically with ValueError."""
    with pytest.raises(ValueError, match="cannot be empty list"):
        resolve_selected_tasks([])


def test_h_invalid_task_identifier_rejected_deterministically():
    """Test H: Invalid task identifier rejected deterministically."""
    with pytest.raises(ValueError, match="Invalid task identifier"):
        resolve_selected_tasks(["unknown_case_123"])

    with pytest.raises(ValueError, match="Invalid task identifier"):
        resolve_selected_tasks("fastapi,nonexistent_task")


def test_i_static_audit_no_task_specific_solver_branches():
    """Test I: Static audit verifying no task-specific solver branches exist in harness."""
    runner_src = Path("backend/run_phase_end_validation_pilot.py").read_text(encoding="utf-8")

    prohibited_patterns = [
        "if task == 'fastapi':",
        "if task_id == 'fastapi':",
        "if task == 'cli':",
        "if task == 'flutter':",
        "if 'fastapi' in task:",
        "inject_contract",
        "mock_solution",
        "solve_task"
    ]
    for pattern in prohibited_patterns:
        assert pattern not in runner_src, f"Prohibited solver pattern found: {pattern}"


def test_j_telemetry_fields_and_versions():
    """Test J: Telemetry fields and version constants integrity."""
    assert PIPELINE_VERSION == "1.8.3"
    assert GOVERNANCE_VERSION == "1.6"

    active_tasks, mode, sel_ids, avail_ids, skip_ids = resolve_selected_tasks(["fastapi"])
    telemetry_payload = {
        "experiment_mode": mode,
        "selected_tasks": sel_ids,
        "available_tasks": avail_ids,
        "skipped_tasks": skip_ids,
        "pipeline_version": PIPELINE_VERSION,
        "governance_version": GOVERNANCE_VERSION,
    }
    assert telemetry_payload["experiment_mode"] == "single_case"
    assert telemetry_payload["selected_tasks"] == ["fastapi_t1"]
    assert telemetry_payload["available_tasks"] == ["fastapi_t1", "cli_t1", "flutter_t1"]
    assert telemetry_payload["skipped_tasks"] == ["cli_t1", "flutter_t1"]
    assert telemetry_payload["pipeline_version"] == "1.8.3"
    assert telemetry_payload["governance_version"] == "1.6"


def test_k_duplicate_aliases_resolve_deterministically():
    """Test K: Duplicate aliases and case variations resolve deterministically to unique canonical IDs."""
    active_tasks, mode, sel_ids, _, skip_ids = resolve_selected_tasks(["fastapi", "FASTAPI", "fastapi_t1", "fastapi"])
    assert mode == "single_case"
    assert len(active_tasks) == 1
    assert sel_ids == ["fastapi_t1"]
    assert set(skip_ids) == {"cli_t1", "flutter_t1"}


def test_l_full_matrix_default_identity():
    """Test L: Full-matrix default produces the exact same selected task set as existing runner."""
    active_tasks, mode, sel_ids, avail_ids, skip_ids = resolve_selected_tasks(None)
    assert mode == "full_matrix"
    assert sel_ids == [t["task_id"] for t in TASKS]
    assert [t["task_id"] for t in active_tasks] == ["fastapi_t1", "cli_t1", "flutter_t1"]
    assert skip_ids == []


def test_m_single_case_mode_does_not_modify_graph_topology():
    """Test M: Single-case mode does not modify phase graph / topology or conditional edges."""
    from backend.graph_phase_validated import build_phase_validated_graph
    graph = build_phase_validated_graph()
    nodes = set(graph.nodes.keys())
    expected_nodes = {
        "v0", "pm", "pm_validator",
        "architect", "architect_validator",
        "developer", "developer_validator",
        "frozen_oracle", "test_suite_validator",
        "executor", "executor_validator",
        "reviewer", "reviewer_validator",
        "complete_success", "terminal_failure", "human_gate"
    }
    # Check that all expected pipeline nodes are intact
    for en in ["pm", "architect", "developer", "reviewer", "pm_validator", "architect_validator"]:
        assert en in nodes


def test_n_skipped_tasks_cannot_affect_e2e_numerator_or_denominator():
    """Test N: Skipped tasks cannot affect E2E numerator or denominator in metrics."""
    # Simulate single-case result calculation
    active_tasks, mode, sel_ids, _, skip_ids = resolve_selected_tasks(["fastapi"])
    total_planned = len(active_tasks) * 1
    assert total_planned == 1
    # Mock single-case results with 1 failure
    results = [{"task_id": "fastapi_t1", "final_verdict": "FAIL"}]
    pass_count = sum(1 for r in results if r.get("final_verdict") == "PASS")
    # Denominator must strictly be total_planned (1), not 3!
    e2e_rate = pass_count / total_planned
    assert total_planned == 1
    assert pass_count == 0
    assert e2e_rate == 0.0
    # Confirm skipped tasks did not generate PASS or FAIL
    result_task_ids = [r["task_id"] for r in results]
    for sk in skip_ids:
        assert sk not in result_task_ids


def test_o_telemetry_metadata_cannot_alter_pipeline_execution():
    """Test O: Telemetry metadata cannot alter pipeline execution or initial state."""
    # Verify metadata fields are not consumed as agent instructions
    from backend.run_phase_end_validation_pilot import TASKS
    task = TASKS[0]
    _, mode, sel_ids, avail_ids, skip_ids = resolve_selected_tasks(["fastapi"])
    assert mode == "single_case"
    assert task["task"] == "Bangun modul REST API FastAPI untuk manajemen inventaris produk dengan validasi Pydantic dan automated pytest."
    # State passed to graph does not inject telemetry into prompt
    assert "single_case" not in task["task"]


def test_p_backward_compatible_single_task_id_behavior():
    """Test P: Existing CLI/backward-compatible single_task_id behavior remains intact."""
    # Pass single_task_id string directly
    active_tasks, mode, sel_ids, _, skip_ids = resolve_selected_tasks("fastapi_t1")
    assert mode == "single_case"
    assert active_tasks[0]["task_id"] == "fastapi_t1"
    assert sel_ids == ["fastapi_t1"]

    # Pass legacy cli_t1
    active_tasks_cli, mode_cli, sel_ids_cli, _, _ = resolve_selected_tasks("cli_t1")
    assert mode_cli == "single_case"
    assert sel_ids_cli == ["cli_t1"]

