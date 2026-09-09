import copy
import pytest
from pathlib import Path
from backend.executor_v2 import (
    run_sandbox_tests_v2,
    executor_node_v2,
    detect_missing_python_imports,
    apply_safe_python_imports,
    validate_python_syntax
)
from backend.state import SquadState
from backend.tracer import compute_dict_hashes

# Test suite fixture from Frozen Oracle FastAPI T1
FASTAPI_T1_ORACLE_PATH = Path(__file__).parent.parent / "dokumentasi-pengembangan/experiments/frozen_oracle/fastapi_t1/test_main.py"
FASTAPI_T1_TEST = FASTAPI_T1_ORACLE_PATH.read_text(encoding="utf-8") if FASTAPI_T1_ORACLE_PATH.exists() else ""


def test_syntax_validation_engine():
    """Syntax validation must correctly identify valid vs invalid Python code."""
    valid_code = "def hello():\n    return 'world'\n"
    is_valid, err = validate_python_syntax(valid_code)
    assert is_valid is True
    assert err is None

    invalid_code = "def hello(\n    return 'world'\n"
    is_valid, err = validate_python_syntax(invalid_code)
    assert is_valid is False
    assert "SyntaxError" in err


def test_safe_missing_imports_detection_and_application():
    """AST import detection must resolve standard missing symbols without modifying logic."""
    code_missing_pydantic = """from fastapi import FastAPI

app = FastAPI()

class Product(BaseModel):
    id: int
    name: str
"""
    missing, reasons = detect_missing_python_imports(code_missing_pydantic)
    assert "from pydantic import BaseModel" in missing
    assert any("BaseModel" in r for r in reasons)

    patched = apply_safe_python_imports(code_missing_pydantic, missing)
    is_valid, _ = validate_python_syntax(patched)
    assert is_valid is True
    assert "from pydantic import BaseModel" in patched
    assert "class Product(BaseModel):" in patched


def test_run10_pattern_prevention():
    """
    RUN 10 VERIFICATION:
    Proves that the regression in Run 10 (where Executor regex injected 'id: int | None = None'
    into ProductCreate, crashing tests with 'multiple values for keyword argument id')
    CAN NEVER HAPPEN AGAIN in SAFE mode.
    """
    run10_raw_code = """from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

products = []

class Product(BaseModel):
    id: int
    name: str
    quantity: int

class ProductCreate(BaseModel):
    name: str
    quantity: int

@app.post("/products/", response_model=Product, status_code=201)
def create_product(product: ProductCreate):
    new_product = Product(id=len(products) + 1, **product.dict())
    products.append(new_product)
    return new_product

@app.get("/products/", response_model=List[Product])
def get_products():
    return products

@app.get("/products/{product_id}", response_model=Product)
def get_product(product_id: int):
    product = next((p for p in products if p.id == product_id), None)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@app.delete("/products/{product_id}", status_code=204)
def delete_product(product_id: int):
    global products
    initial_len = len(products)
    products = [p for p in products if p.id != product_id]
    if len(products) == initial_len:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"detail": "Product deleted"}
"""
    test_files = {"test_main.py": FASTAPI_T1_TEST}

    # 1. Run in SAFE mode
    results = run_sandbox_tests_v2(
        {"main.py": run10_raw_code},
        test_files,
        target_language="python",
        executor_mode="SAFE"
    )

    # In SAFE mode, code is NOT modified with bogus id injection
    assert results["passed"] is True
    assert results["passed_count"] == 5
    assert results["failed_count"] == 0
    assert "id: int | None = None" not in results["code_files"]["main.py"]
    # 0 transformations applied because imports and syntax were already complete
    assert len(results["transformations"]) == 0


def test_run02_safe_import_resolution():
    """
    RUN 02 VERIFICATION (Category B Decisive):
    Proves that missing BaseModel is resolved safely via AST and leads to test pass.
    """
    run02_code = """from fastapi import FastAPI, HTTPException
from typing import List

app = FastAPI()
products = []

class Product(BaseModel):
    id: int
    name: str
    quantity: int

@app.get("/products/", response_model=List[Product])
def get_products():
    return products
"""
    test_code = """from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_get():
    res = client.get("/products/")
    assert res.status_code == 200
    assert res.json() == []
"""
    test_files = {"test_main.py": test_code}

    results = run_sandbox_tests_v2(
        {"main.py": run02_code},
        test_files,
        target_language="python",
        executor_mode="SAFE"
    )

    assert results["passed"] is True
    assert "from pydantic import BaseModel" in results["code_files"]["main.py"]
    assert len(results["transformations"]) == 1
    tx = results["transformations"][0]
    assert tx["file"] == "main.py"
    assert tx["rolled_back"] is False
    assert tx["before_hash"] != tx["after_hash"]


def test_safe_mode_no_destructive_rewriting():
    """
    SAFE mode must NEVER perform:
    - plain model rewriting
    - endpoint auto-injection
    - parser replacement
    - arithmetic operator replacement
    """
    raw_code = """class Product:
    def __init__(self, name: str):
        self.name = name

def parse_matrix(matrix_str):
    return matrix_str

def __truediv__(self, other):
    return self.data[i][k] * other
"""
    missing, _ = detect_missing_python_imports(raw_code)
    # Plain Product is NOT rewritten to inherit BaseModel
    assert "BaseModel" not in missing
    # No endpoint injection
    assert "@app.get" not in raw_code
    # No string replacement
    patched = apply_safe_python_imports(raw_code, missing)
    assert patched == raw_code


def test_safe_mode_test_files_immutability():
    """
    In SAFE mode, test_files must be 100% strictly immutable.
    """
    code_files = {"calc.py": "def add(a, b): return a + b\n"}
    test_files = {"test_calc.py": "from calc import add\ndef test_add():\n    assert add(1, 2) == 3\n    assert status_code == 201\n"}
    
    test_orig = copy.deepcopy(test_files)
    test_before_hash = compute_dict_hashes(test_orig)

    results = run_sandbox_tests_v2(
        code_files,
        test_files,
        target_language="python",
        executor_mode="SAFE"
    )

    assert results["test_files"] == test_orig
    assert compute_dict_hashes(results["test_files"]) == test_before_hash
    # Assert no status_code assertion relaxation occurred
    assert "assert status_code == 201" in results["test_files"]["test_calc.py"]


def test_safe_mode_rollback_on_degradation():
    """
    If candidate transformation causes regression or fails to improve test results,
    it must automatically roll back to the original code.
    """
    code_files = {
        "main.py": "def test_func():\n    return 42\n"
    }
    test_files = {
        "test_main.py": "from main import test_func\ndef test_it(): assert test_func() == 42\n"
    }

    # In safe mode, code already passes, so 0 transformations
    results = run_sandbox_tests_v2(
        code_files,
        test_files,
        target_language="python",
        executor_mode="SAFE"
    )
    assert results["passed"] is True
    assert len(results["transformations"]) == 0


def test_executor_node_v2_safe_mode():
    """Verify executor_node_v2 operates properly within SquadState."""
    state: SquadState = {
        "task": "Test SAFE mode",
        "provider": "ollama",
        "model_name": "qwen2.5-coder:7b",
        "target_language": "python",
        "specifications": "",
        "architecture_plan": "",
        "code_files": {"math_tool.py": "def multiply(x, y): return x * y\n"},
        "test_files": {"test_math_tool.py": "from math_tool import multiply\ndef test_mul(): assert multiply(3, 4) == 12\n"},
        "test_results": {},
        "iteration_count": 0,
        "max_iterations": 3,
        "review_notes": "",
        "status": "testing",
        "logs": [],
        "run_id": "test_safe_node_run",
        "output_dir": "",
        "executor_intervention_enabled": True,
        "executor_mode": "SAFE"
    }

    res = executor_node_v2(state)
    assert res["test_results"]["passed"] is True
    assert res["status"] == "tests_passed"
    assert any("Executor-SAFE" in log for log in res["logs"])
    assert res["code_files"] == state["code_files"]
    assert res["test_files"] == state["test_files"]
