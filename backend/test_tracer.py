import json
import shutil
from pathlib import Path
import pytest
from backend.tracer import RunTracer, get_tracer, compute_sha256, compute_dict_hashes, compute_object_hash, log_model_interaction

TEST_TRACE_DIR = Path(__file__).parent / "test_traces_temp"

@pytest.fixture(autouse=True)
def cleanup():
    if TEST_TRACE_DIR.exists():
        shutil.rmtree(TEST_TRACE_DIR, ignore_errors=True)
    TEST_TRACE_DIR.mkdir(parents=True, exist_ok=True)
    yield
    if TEST_TRACE_DIR.exists():
        shutil.rmtree(TEST_TRACE_DIR, ignore_errors=True)

def test_compute_sha256():
    h1 = compute_sha256("def hello(): pass")
    h2 = compute_sha256("def hello(): pass")
    h3 = compute_sha256("def hello(): return 1")
    assert h1 == h2
    assert h1 != h3
    assert len(h1) == 64

def test_compute_dict_hashes():
    files = {
        "main.py": "print('hello')",
        "test.py": "assert True"
    }
    hashes = compute_dict_hashes(files)
    assert "main.py" in hashes
    assert "test.py" in hashes
    assert hashes["main.py"] == compute_sha256("print('hello')")

def test_compute_object_hash():
    obj1 = {"a": 1, "b": [1, 2, 3]}
    obj2 = {"b": [1, 2, 3], "a": 1}
    obj3 = {"a": 1, "b": [1, 2, 4]}
    h1 = compute_object_hash(obj1)
    h2 = compute_object_hash(obj2)
    h3 = compute_object_hash(obj3)
    assert h1 == h2
    assert h1 != h3
    assert len(h1) == 64

def test_run_tracer_lifecycle():
    run_id = "test_run_001"
    run_dir = TEST_TRACE_DIR / run_id
    tracer = RunTracer.register(run_id, run_dir)
    assert tracer is not None
    assert get_tracer(run_id) is tracer

    # Log several events
    tracer.log_event("run_lifecycle", "run_start", 0, {"task": "test task"})
    tracer.log_event("pm", "output", 0, {"specifications": "spec 1"})
    tracer.log_event("developer", "output", 0, {"code_files": {"main.py": "code"}})
    tracer.log_event("executor", "execution", 0, {"passed": True, "exit_code": 0})
    tracer.log_event("run_lifecycle", "run_end", 0, {"final_status": "completed"})

    trace_file = run_dir / "run_trace.jsonl"
    assert trace_file.exists()

    lines = trace_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 5

    events = [json.loads(line) for line in lines]
    assert events[0]["stage"] == "run_lifecycle"
    assert events[0]["event_type"] == "run_start"
    assert events[0]["data"]["task"] == "test task"

    assert events[1]["stage"] == "pm"
    assert events[2]["stage"] == "developer"
    assert events[3]["stage"] == "executor"
    assert events[4]["stage"] == "run_lifecycle"
    assert events[4]["event_type"] == "run_end"

def test_tracer_safe_serialization_fallback():
    run_id = "test_run_fallback"
    run_dir = TEST_TRACE_DIR / run_id
    tracer = RunTracer.register(run_id, run_dir)

    # Object that can fail serialization or have weird behavior
    class UnserializableObj:
        def __repr__(self):
            raise ValueError("Cannot repr")

    # tracer.log_event should not raise exception
    tracer.log_event("tester", "output", 0, {"bad_data": UnserializableObj()})

    trace_file = run_dir / "run_trace.jsonl"
    assert trace_file.exists()
    lines = trace_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    event = json.loads(lines[0])
    assert event["stage"] == "tester"



def test_trace_events_have_unique_ids_sequence_and_parent_links():
    run_id = "test_trace_identity"
    tracer = RunTracer.register(run_id, TEST_TRACE_DIR / run_id)
    parent_id = tracer.log_event("graph_node", "node_start", 0, {"node": "pm"})
    child_id = tracer.log_event(
        "graph_node", "node_complete", 0, {"node": "pm"},
        correlation_id="execution-1", parent_event_id=parent_id
    )

    lines = (TEST_TRACE_DIR / run_id / "run_trace.jsonl").read_text(encoding="utf-8").splitlines()
    events = [json.loads(line) for line in lines]
    assert parent_id and child_id and parent_id != child_id
    assert [event["sequence"] for event in events] == [1, 2]
    assert events[0]["event_id"] == parent_id
    assert events[1]["parent_event_id"] == parent_id
    assert events[1]["correlation_id"] == "execution-1"
    assert all(event["run_id"] == run_id for event in events)


def test_explicit_unknown_run_id_never_falls_back_to_active_tracer():
    run_id = "test_trace_isolation"
    tracer = RunTracer.register(run_id, TEST_TRACE_DIR / run_id)
    assert get_tracer(run_id) is tracer
    assert get_tracer("unknown-run-id") is None
    assert get_tracer(None) is None


def test_trace_write_failure_is_reported_without_raising(monkeypatch, caplog):
    import builtins

    run_id = "test_trace_write_failure"
    tracer = RunTracer.register(run_id, TEST_TRACE_DIR / run_id)

    def fail_open(*args, **kwargs):
        raise OSError("simulated disk write failure")

    monkeypatch.setattr(builtins, "open", fail_open)
    with caplog.at_level("ERROR"):
        result = tracer.log_event("tester", "output", 0, {"ok": True})

    assert result is None
    assert tracer.write_failures == 1
    assert "AUDIT_TRACE_WRITE_FAILURE" in caplog.text



def test_model_interaction_trace_contains_prompt_output_timing_and_metadata(tmp_path):
    run_id = "test_model_interaction"
    tracer = RunTracer.register(run_id, tmp_path / run_id)

    class Message:
        type = "human"
        content = "Build a calculator"

    class Client:
        model = "test-model"

    class Response:
        content = "def add(a, b): return a + b"
        response_metadata = {"finish_reason": "stop"}
        usage_metadata = {"input_tokens": 12, "output_tokens": 8}

    response = Response()
    log_model_interaction(
        tracer, role="developer", messages=[Message()], response=response,
        raw_output=response.content, duration_sec=0.125, iteration=1,
        provider="test-provider", requested_model="test-model", model_client=Client(),
        backend_metadata={"latency_s": 0.12},
    )

    event = json.loads((tmp_path / run_id / "run_trace.jsonl").read_text(encoding="utf-8"))
    assert event["event_type"] == "model_call"
    assert event["data"]["prompt_messages"][0]["content"] == "Build a calculator"
    assert event["data"]["raw_output"] == response.content
    assert event["data"]["duration_sec"] == 0.125
    assert event["data"]["resolved_model"] == "test-model"
    assert event["data"]["usage_metadata"]["input_tokens"] == 12
    assert len(event["data"]["prompt_sha256"]) == 64
