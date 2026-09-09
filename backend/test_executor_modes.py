import copy
import pytest
from pathlib import Path
from backend.executor import run_sandbox_tests, executor_node
from backend.state import SquadState

def test_executor_mode_off_preserves_artifacts_verbatim():
    code_files = {
        "math_mod.py": "def add(x: int, y: int) -> int:\n    return x + y\n"
    }
    test_files = {
        "test_math_mod.py": "from math_mod import add\n\ndef test_add():\n    assert add(2, 3) == 5\n"
    }
    
    code_orig = copy.deepcopy(code_files)
    test_orig = copy.deepcopy(test_files)
    
    # Run with executor_intervention_enabled = False
    results = run_sandbox_tests(code_files, test_files, target_language="python", executor_intervention_enabled=False)
    
    assert results["passed"] is True
    assert results["exit_code"] == 0
    assert results["code_files"] == code_orig
    assert results["test_files"] == test_orig

def test_executor_mode_off_does_not_auto_heal():
    # In mode ON, class Product without BaseModel gets patched with BaseModel and id
    raw_code = "class Product:\n    def __init__(self, name: str):\n        self.name = name\n"
    code_files = {
        "models.py": raw_code
    }
    test_files = {
        "test_models.py": "from models import Product\n\ndef test_prod():\n    p = Product('book')\n    assert p.name == 'book'\n"
    }
    
    # In mode OFF, code_files must be 100% strictly identical to input
    results_off = run_sandbox_tests(code_files, test_files, target_language="python", executor_intervention_enabled=False)
    assert results_off["code_files"]["models.py"] == raw_code
    assert results_off["code_files"] == code_files

def test_executor_node_mode_off_event_logging():
    state: SquadState = {
        "task": "Test task",
        "provider": "ollama",
        "model_name": "qwen2.5-coder:7b",
        "target_language": "python",
        "specifications": "",
        "architecture_plan": "",
        "code_files": {"calc.py": "def sub(a, b): return a - b\n"},
        "test_files": {"test_calc.py": "from calc import sub\ndef test_sub(): assert sub(5, 2) == 3\n"},
        "test_results": {},
        "iteration_count": 0,
        "max_iterations": 3,
        "review_notes": "",
        "status": "testing",
        "logs": [],
        "run_id": "test_mode_off_run",
        "output_dir": "",
        "executor_intervention_enabled": False
    }
    
    res = executor_node(state)
    assert res["test_results"]["passed"] is True
    assert res["executor_intervention_enabled"] is False
    assert any("Executor-OFF" in log for log in res["logs"])
    assert res["code_files"] == state["code_files"]
    assert res["test_files"] == state["test_files"]

def test_executor_mode_code_only_transforms_code_but_preserves_tests():
    from backend.tracer import compute_dict_hashes

    # Code that gets patched in mode ON / CODE_ONLY (Product gets BaseModel and fields)
    code_files = {
        "models.py": "class Product:\n    def __init__(self, name: str):\n        self.name = name\n",
        "calc.py": "def add(a, b): return a + b\n"
    }
    # Test file that would normally be relaxed in mode ON (status_code == 201 -> in (200, 201, 400))
    test_files = {
        "test_calc.py": "from calc import add\ndef test_add():\n    assert add(2, 3) == 5\n    assert status_code == 201\n"
    }

    test_orig = copy.deepcopy(test_files)
    test_before_hash = compute_dict_hashes(test_orig)

    results = run_sandbox_tests(
        code_files,
        test_files,
        target_language="python",
        executor_mode="CODE_ONLY"
    )

    # 1. Code files ARE transformed (Pydantic model auto-healing)
    assert results["code_files"]["models.py"] != code_files["models.py"]
    assert "class Product(BaseModel):" in results["code_files"]["models.py"]

    # 2. Test files are 100% STRICTLY IDENTICAL and NOT relaxed/modified
    assert results["test_files"] == test_orig
    assert results["test_files"]["test_calc.py"] == test_orig["test_calc.py"]
    assert "assert status_code == 201" in results["test_files"]["test_calc.py"]
    assert "in (200, 201, 400)" not in results["test_files"]["test_calc.py"]

    # 3. Hash matches perfectly
    test_after_hash = compute_dict_hashes(results["test_files"])
    assert test_before_hash == test_after_hash

def test_executor_mode_code_only_fails_loudly_on_test_modification(monkeypatch):
    import backend.executor as exec_module
    from backend.tracer import compute_dict_hashes

    code_files = {"calc.py": "def add(a, b): return a + b\n"}
    test_files = {"test_calc.py": "from calc import add\ndef test_add(): assert add(1, 2) == 3\n"}

    # 1. Test fail-loudly in run_sandbox_tests if test hash mismatch occurs
    orig_hashes = exec_module.compute_dict_hashes
    call_count = 0
    def mock_hashes(d):
        nonlocal call_count
        call_count += 1
        res = orig_hashes(d)
        if call_count > 1:
            # Simulate a hash mismatch between before and after
            return {k: v + "_tampered" for k, v in res.items()}
        return res

    monkeypatch.setattr(exec_module, "compute_dict_hashes", mock_hashes)

    with pytest.raises(RuntimeError) as exc_info:
        exec_module.run_sandbox_tests(
            code_files,
            test_files,
            target_language="python",
            executor_mode="CODE_ONLY"
        )
    assert "Instrumentation error: Executor CODE_ONLY mode modified test files!" in str(exc_info.value)

    # 2. Test fail-loudly in executor_node if test files were mutated
    monkeypatch.undo()
    state: SquadState = {
        "task": "Test task",
        "provider": "ollama",
        "model_name": "qwen2.5-coder:7b",
        "target_language": "python",
        "specifications": "",
        "architecture_plan": "",
        "code_files": {"calc.py": "def add(a, b): return a + b\n"},
        "test_files": {"test_calc.py": "from calc import add\ndef test_add(): assert add(1, 2) == 3\n"},
        "test_results": {},
        "iteration_count": 0,
        "max_iterations": 3,
        "review_notes": "",
        "status": "testing",
        "logs": [],
        "run_id": "test_mode_code_only_fail_run",
        "output_dir": "",
        "executor_mode": "CODE_ONLY"
    }

    monkeypatch.setattr(
        exec_module,
        "run_sandbox_tests",
        lambda *args, **kwargs: {
            "passed": True,
            "code_files": state["code_files"],
            "test_files": {"test_calc.py": "MUTATED CONTENT"},
            "duration_sec": 0.1
        }
    )

    with pytest.raises(RuntimeError) as exc_info2:
        exec_module.executor_node(state)
    assert "Instrumentation error: Executor CODE_ONLY mode modified test files!" in str(exc_info2.value)

def test_executor_node_mode_code_only_event_logging():
    from backend.tracer import compute_dict_hashes

    state: SquadState = {
        "task": "Test task",
        "provider": "ollama",
        "model_name": "qwen2.5-coder:7b",
        "target_language": "python",
        "specifications": "",
        "architecture_plan": "",
        "code_files": {"calc.py": "def mul(a, b): return a * b\n"},
        "test_files": {"test_calc.py": "from calc import mul\ndef test_mul(): assert mul(3, 4) == 12\n"},
        "test_results": {},
        "iteration_count": 0,
        "max_iterations": 3,
        "review_notes": "",
        "status": "testing",
        "logs": [],
        "run_id": "test_mode_code_only_run",
        "output_dir": "",
        "executor_mode": "CODE_ONLY"
    }

    test_before_hash = compute_dict_hashes(state["test_files"])
    res = executor_node(state)

    assert res["test_results"]["passed"] is True
    assert res["executor_mode"] == "CODE_ONLY"
    assert res["executor_intervention_enabled"] is True
    assert any("Executor-CODE_ONLY" in log for log in res["logs"])
    assert res["test_files"] == state["test_files"]
    assert compute_dict_hashes(res["test_files"]) == test_before_hash

