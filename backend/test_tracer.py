import json
import shutil
from pathlib import Path
import pytest
from backend.tracer import RunTracer, get_tracer, compute_sha256, compute_dict_hashes, compute_object_hash

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
