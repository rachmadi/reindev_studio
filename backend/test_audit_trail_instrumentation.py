import json
from pathlib import Path

import pytest

from backend.graph import _traced_node, _traced_route
from backend.tracer import RunTracer


def _events(trace_dir: Path):
    return [
        json.loads(line)
        for line in (trace_dir / "run_trace.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_traced_node_records_actual_input_output_and_duration(tmp_path):
    run_id = "audit-node-success"
    trace_dir = tmp_path / run_id
    RunTracer.register(run_id, trace_dir)
    state = {
        "run_id": run_id,
        "iteration_count": 2,
        "task": "build a calculator",
        "code_files": {"main.py": "print(1)"},
    }
    original_state = json.loads(json.dumps(state))
    calls = []

    def node_fn(actual_state):
        calls.append(actual_state)
        return {"status": "ok", "code_files": {"main.py": "print(2)"}}

    result = _traced_node("sample_node", node_fn)(state)
    events = _events(trace_dir)

    assert len(calls) == 1
    assert state == original_state
    assert result == {"status": "ok", "code_files": {"main.py": "print(2)"}}
    assert [event["event_type"] for event in events] == ["node_start", "node_complete"]
    assert events[0]["data"]["input_state"] == original_state
    assert events[1]["data"]["output"] == result
    assert events[1]["data"]["duration_sec"] >= 0
    assert events[1]["parent_event_id"] == events[0]["event_id"]
    assert events[0]["correlation_id"] == events[1]["correlation_id"]


def test_traced_node_records_exception_and_reraises_same_error(tmp_path):
    run_id = "audit-node-error"
    trace_dir = tmp_path / run_id
    RunTracer.register(run_id, trace_dir)

    def node_fn(_state):
        raise ValueError("node failed")

    with pytest.raises(ValueError, match="node failed"):
        _traced_node("sample_node", node_fn)({"run_id": run_id, "iteration_count": 0})

    events = _events(trace_dir)
    assert [event["event_type"] for event in events] == ["node_start", "node_error"]
    assert events[1]["data"]["exception_type"] == "ValueError"
    assert events[1]["data"]["exception_message"] == "node failed"


def test_traced_route_records_decision_without_changing_it(tmp_path):
    run_id = "audit-route"
    trace_dir = tmp_path / run_id
    RunTracer.register(run_id, trace_dir)
    state = {
        "run_id": run_id,
        "iteration_count": 1,
        "status": "tests_failed",
        "repair_attempt_counts": {"developer": 1},
        "max_phase_repair_attempts": 2,
    }

    decision = _traced_route("route_after_sample", lambda _state: "developer")(state)
    events = _events(trace_dir)

    assert decision == "developer"
    assert len(events) == 1
    assert events[0]["event_type"] == "route_decision"
    assert events[0]["data"]["target_node"] == "developer"
    assert events[0]["data"]["decision_state"] == state
