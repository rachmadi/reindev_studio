from executor_v2 import run_safe_preflight


def test_missing_basemodel_import_is_safe():
    code = {"main.py": "class Product(BaseModel):\n    id: int\n"}
    result = run_safe_preflight(code, {"test_main.py": ""})
    assert "from pydantic import BaseModel" in result["code_files"]["main.py"]
    assert len(result["transformations"]) == 1


def test_no_schema_or_business_logic_rewrite():
    code = {"main.py": "from pydantic import BaseModel\nclass ProductCreate(BaseModel):\n    name: str\n    quantity: int\n\nproducts=[]\n"}
    result = run_safe_preflight(code, {"test_main.py": ""})
    assert result["code_files"] == code
    assert result["transformations"] == []


def test_run10_regression_pattern_is_untouched():
    code = {"main.py": "from pydantic import BaseModel\nclass Product(BaseModel):\n    id: int\n    name: str\n    quantity: int\nclass ProductCreate(BaseModel):\n    name: str\n    quantity: int\n"}
    result = run_safe_preflight(code, {"test_main.py": ""})
    assert "id: int | None = None" not in result["code_files"]["main.py"]
    assert result["code_files"] == code


def test_tests_are_immutable():
    tests = {"test_main.py": "assert 1 == 1\n"}
    result = run_safe_preflight({"main.py": "x = 1\n"}, tests)
    assert result["test_files"] == tests
    assert result["test_files_unchanged"] is True
