import os
import pytest

# Pastikan mode mock aktif untuk test suite internal instan
os.environ["MOCK_LLM"] = "true"

from backend.state import SquadState
from backend.agents.architect import architect_agent
from backend.agents.tester import tester_agent as run_tester_node
from backend.agents.reviewer import reviewer_agent
from backend.executor import run_sandbox_tests, executor_node
from backend.graph import route_after_executor, build_squad_graph

# Beritahu pytest agar tidak menganggap node tester sebagai test case
run_tester_node.__test__ = False

def test_architect_agent():
    state: SquadState = {
        "task": "Buat fungsi kalkulator matriks",
        "provider": "ollama",
        "model_name": "qwen2.5-coder:7b",
        "target_language": "python",
        "specifications": "Spesifikasi perkalian matriks 2x2",
        "architecture_plan": "",
        "code_files": {},
        "test_files": {},
        "test_results": {},
        "iteration_count": 0,
        "max_iterations": 3,
        "review_notes": "",
        "status": "init",
        "logs": []
    }
    result = architect_agent(state)
    assert "architecture_plan" in result
    assert len(result["architecture_plan"]) > 10
    assert result["status"] == "architect_done"
    assert len(result["logs"]) == 1

def test_tester_agent():
    state: SquadState = {
        "task": "Kalkulator vektor",
        "provider": "ollama",
        "model_name": "qwen2.5-coder:7b",
        "target_language": "python",
        "specifications": "Acceptance criteria dot product",
        "architecture_plan": "vector_math.py",
        "code_files": {"vector_math.py": "def dot_product(a, b): return sum(x*y for x, y in zip(a, b))"},
        "test_files": {},
        "test_results": {},
        "iteration_count": 0,
        "max_iterations": 3,
        "review_notes": "",
        "status": "dev_done",
        "logs": []
    }
    result = run_tester_node(state)
    assert "test_files" in result
    assert len(result["test_files"]) > 0
    # Pastikan nama file test diawali 'test_'
    for fname in result["test_files"].keys():
        assert fname.startswith("test_")
    assert result["status"] == "tester_done"

def test_sandbox_executor_success():
    code_files = {
        "simple_math.py": "def multiply(x: int, y: int) -> int:\n    return x * y\n"
    }
    test_files = {
        "test_simple_math.py": "from simple_math import multiply\n\ndef test_multiply():\n    assert multiply(3, 4) == 12\n"
    }
    results = run_sandbox_tests(code_files, test_files)
    assert results["passed"] is True
    assert results["exit_code"] == 0
    assert results["passed_count"] == 1
    assert results["failed_count"] == 0

def test_sandbox_executor_failure():
    code_files = {
        "broken_math.py": "def multiply(x: int, y: int) -> int:\n    return x + y  # Bug sengaja!\n"
    }
    test_files = {
        "test_broken_math.py": "from broken_math import multiply\n\ndef test_multiply():\n    assert multiply(3, 4) == 12\n"
    }
    results = run_sandbox_tests(code_files, test_files)
    assert results["passed"] is False
    assert results["exit_code"] != 0
    assert results["failed_count"] >= 1
    assert "assert 7 == 12" in results["output"]

def test_cyclic_routing_logic():
    # Skenario 1: Test LULUS -> Menuju ke Reviewer
    passed_state: SquadState = {
        "test_results": {"passed": True},
        "iteration_count": 0,
        "max_iterations": 3
    }
    assert route_after_executor(passed_state) == "reviewer"

    # Skenario 2: Test GAGAL dan iterasi < max -> Putar balik ke Developer (Self-Healing)
    failed_state_retry: SquadState = {
        "test_results": {"passed": False},
        "iteration_count": 1,
        "max_iterations": 3
    }
    assert route_after_executor(failed_state_retry) == "developer"

    # Skenario 3: Test GAGAL tapi batas iterasi telah tercapai -> Lanjut ke Reviewer dengan catatan kegagalan
    failed_state_maxed: SquadState = {
        "test_results": {"passed": False},
        "iteration_count": 3,
        "max_iterations": 3
    }
    assert route_after_executor(failed_state_maxed) == "reviewer"

def test_reviewer_agent():
    state: SquadState = {
        "task": "Modul matematika",
        "provider": "ollama",
        "model_name": "qwen2.5-coder:7b",
        "target_language": "python",
        "specifications": "Spesifikasi vektor",
        "architecture_plan": "Rencana arsitektur",
        "code_files": {"vector_math.py": "def dot_product(v1, v2): return 0"},
        "test_files": {"test_vector_math.py": "def test_dot(): pass"},
        "test_results": {"passed": True, "total": 1, "output": "1 passed"},
        "iteration_count": 0,
        "max_iterations": 3,
        "review_notes": "",
        "status": "tests_passed",
        "logs": []
    }
    result = reviewer_agent(state)
    assert "review_notes" in result
    assert "APPROVED" in result["review_notes"]
    assert result["status"] == "completed"

def test_full_squad_pipeline_mock():
    graph = build_squad_graph()
    initial_state: SquadState = {
        "task": "Bangun fungsi perkalian vektor matematika",
        "provider": "ollama",
        "model_name": "qwen2.5-coder:7b",
        "target_language": "python",
        "specifications": "",
        "architecture_plan": "",
        "code_files": {},
        "test_files": {},
        "test_results": {},
        "iteration_count": 0,
        "max_iterations": 3,
        "review_notes": "",
        "status": "init",
        "logs": []
    }
    
    final_state = graph.invoke(initial_state)
    
    assert final_state["specifications"] != ""
    assert final_state["architecture_plan"] != ""
    assert len(final_state["code_files"]) > 0
    assert len(final_state["test_files"]) > 0
    assert final_state["test_results"]["passed"] is True
    assert final_state["review_notes"] != ""
    assert final_state["status"] == "completed"
    assert len(final_state["logs"]) >= 6
