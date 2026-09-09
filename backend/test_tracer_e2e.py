import json
import shutil
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch

from backend.state import SquadState
from backend.tracer import RunTracer
from backend.graph import squad_graph

TEST_E2E_DIR = Path(__file__).parent / "test_e2e_traces"

@pytest.fixture(autouse=True)
def cleanup():
    if TEST_E2E_DIR.exists():
        shutil.rmtree(TEST_E2E_DIR, ignore_errors=True)
    TEST_E2E_DIR.mkdir(parents=True, exist_ok=True)
    yield
    if TEST_E2E_DIR.exists():
        shutil.rmtree(TEST_E2E_DIR, ignore_errors=True)

def test_tracer_e2e_sequence():
    run_id = "project_test_e2e_001"
    run_dir = TEST_E2E_DIR / run_id
    tracer = RunTracer.register(run_id, run_dir)

    initial_state: SquadState = {
        "task": "Buat fungsi kalkulator penambahan",
        "provider": "ollama",
        "model_name": "qwen2.5-coder:7b",
        "target_language": "python",
        "specifications": "",
        "architecture_plan": "",
        "code_files": {},
        "test_files": {},
        "test_results": {},
        "iteration_count": 0,
        "max_iterations": 1,
        "review_notes": "",
        "status": "in_progress",
        "logs": [],
        "run_id": run_id,
        "output_dir": str(run_dir)
    }

    # Log RUN_START
    tracer.log_event("run_lifecycle", "run_start", 0, {
        "run_id": run_id,
        "task": initial_state["task"],
        "target_language": "python",
        "provider": "ollama",
        "model": "qwen2.5-coder:7b",
        "max_iterations": 1
    })

    # Mock the LLM to avoid needing a live Ollama connection during test
    mock_response = MagicMock()
    mock_response.content = "=== FILE: calc.py ===\ndef add(a: int, b: int) -> int:\n    return a + b\n=== END FILE ==="

    mock_test_response = MagicMock()
    mock_test_response.content = "=== FILE: test_calc.py ===\nfrom calc import add\ndef test_add():\n    assert add(1, 2) == 3\n=== END FILE ==="

    mock_rev_response = MagicMock()
    mock_rev_response.content = "[APPROVED]\nKode memenuhi standar kualitas."

    mock_llm = MagicMock()
    def llm_side_effect(messages):
        prompt_str = str(messages)
        if "Product Manager" in prompt_str or "spesifikasi" in prompt_str.lower():
            return MagicMock(content="1. Ringkasan: Kalkulator penambahan\n2. Stories: Tambah angka\n3. Kriteria: 1+2=3")
        elif "System Architect" in prompt_str or "arsitektur" in prompt_str.lower():
            return MagicMock(content="=== File Tree ===\ncalc.py\ntest_calc.py")
        elif "Developer" in prompt_str or "=== FILE:" in prompt_str:
            return mock_response
        elif "QA" in prompt_str or "test" in prompt_str.lower():
            return mock_test_response
        else:
            return mock_rev_response

    mock_llm.invoke.side_effect = llm_side_effect

    with patch("backend.agents.pm.get_llm", return_value=mock_llm), \
         patch("backend.agents.architect.get_llm", return_value=mock_llm), \
         patch("backend.agents.developer.get_llm", return_value=mock_llm), \
         patch("backend.agents.tester.get_llm", return_value=mock_llm), \
         patch("backend.agents.reviewer.get_llm", return_value=mock_llm):

        # Run StateGraph stream
        accumulated_state = initial_state.copy()
        for step in squad_graph.stream(initial_state):
            for node_name, node_output in step.items():
                accumulated_state.update(node_output)
                if node_name == "pm" and "specifications" in node_output:
                    tracer.log_event("pm", "output", 0, {
                        "specifications": node_output["specifications"]
                    })
                elif node_name == "architect" and "architecture_plan" in node_output:
                    tracer.log_event("architect", "output", 0, {
                        "architecture_plan": node_output["architecture_plan"]
                    })

    # Log RUN_END
    tracer.log_event("run_lifecycle", "run_end", accumulated_state.get("iteration_count", 0), {
        "run_id": run_id,
        "final_status": "completed",
        "tests_passed": accumulated_state.get("test_results", {}).get("passed", False)
    })

    trace_file = run_dir / "run_trace.jsonl"
    assert trace_file.exists()
    lines = trace_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 8

    events = [json.loads(line) for line in lines]
    stages = [e["stage"] for e in events]
    print("STAGES RECORDED:", stages)

    # Verify all expected stages are in sequence
    assert "run_lifecycle" in stages  # RUN_START and RUN_END
    assert "pm" in stages
    assert "architect" in stages
    assert "developer" in stages
    assert "routing" in stages
    assert "tester" in stages
    assert "executor" in stages
    assert "reviewer" in stages

    # Check developer event details (input & output)
    dev_input_event = next(e for e in events if e["stage"] == "developer" and e["event_type"] == "input")
    assert "developer_input" in dev_input_event["data"]
    dev_in = dev_input_event["data"]["developer_input"]
    assert "task" in dev_in
    assert "specifications" in dev_in
    assert "architecture_plan" in dev_in
    assert "iteration_count" in dev_in
    assert "code_files" in dev_in
    assert "test_files" in dev_in
    assert "test_results" in dev_in
    assert "logs" in dev_in
    assert "status" in dev_in

    dev_output_event = next(e for e in events if e["stage"] == "developer" and e["event_type"] == "output")
    assert "developer_raw_output" in dev_output_event["data"]
    assert "developer_parsed_output" in dev_output_event["data"]

    # Check executor event details (input & execution)
    exec_input_event = next(e for e in events if e["stage"] == "executor" and e["event_type"] == "input")
    assert "executor_input" in exec_input_event["data"]

    executor_event = next(e for e in events if e["stage"] == "executor" and e["event_type"] == "execution")
    assert "code_files_before" in executor_event["data"]
    assert "code_files_after" in executor_event["data"]
    assert "transformations" in executor_event["data"]
    assert "command" in executor_event["data"]
    assert "working_directory" in executor_event["data"]
    assert "stdout" in executor_event["data"]
    assert "parsed_results" in executor_event["data"]
