import pytest
import os
from pathlib import Path

# Ensure backend directory is in sys.path
import sys
backend_path = str(Path(__file__).parent.resolve())
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from state import SquadState
from config import get_llm
from agents.pm import pm_agent
from agents.developer import developer_agent, parse_code_blocks

def test_state_schema():
    """Menguji bahwa SquadState TypedDict memiliki semua field wajib."""
    state: SquadState = {
        "task": "Buat fungsi kalkulator matriks 2x2",
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
        "status": "idle",
        "logs": []
    }
    assert state["task"] == "Buat fungsi kalkulator matriks 2x2"
    assert state["provider"] == "ollama"
    assert state["iteration_count"] == 0

def test_config_llm_factory():
    """Menguji bahwa LLM Factory dapat menginisialisasi ChatOllama atau mock model."""
    os.environ["MOCK_LLM"] = "true"
    llm = get_llm(role="pm")
    assert llm is not None
    response = llm.invoke("Halo")
    assert hasattr(response, "content")

def test_parse_code_blocks():
    """Menguji kemampuan parser dalam mengekstrak blok file kode."""
    raw_sample = """Berikut kodenya:
=== FILE: matrix.py ===
class Matrix:
    def __init__(self, data):
        self.data = data
=== END FILE ===

=== FILE: utils.py ===
def identity():
    return [[1, 0], [0, 1]]
=== END FILE ===
"""
    files = parse_code_blocks(raw_sample)
    assert "matrix.py" in files
    assert "utils.py" in files
    assert "class Matrix:" in files["matrix.py"]
    assert "def identity():" in files["utils.py"]

def test_pm_and_developer_pipeline():
    """Menguji aliran data dari PM Agent ke Developer Agent secara sekuensial."""
    os.environ["MOCK_LLM"] = "true"
    
    initial_state: SquadState = {
        "task": "Buat modul vektor 2D dengan fungsi dot product dan magnitude",
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
        "status": "idle",
        "logs": []
    }
    
    # 1. Jalankan PM Node
    pm_output = pm_agent(initial_state)
    assert "specifications" in pm_output
    assert pm_output["status"] == "pm_done"
    assert len(pm_output["logs"]) == 1
    
    # Update state
    state_after_pm = {**initial_state, **pm_output}
    
    # 2. Jalankan Developer Node
    dev_output = developer_agent(state_after_pm)
    assert "code_files" in dev_output
    assert dev_output["status"] == "dev_done"
    assert len(dev_output["logs"]) == 2
    assert len(dev_output["code_files"]) > 0
    assert "vector_math.py" in dev_output["code_files"]
    assert "def dot_product" in dev_output["code_files"]["vector_math.py"]
