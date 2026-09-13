"""
Tests for Sterile Execution Engine (executor.py).
Verifies that run_sandbox_tests and executor_node write code_files and test_files 100% unchanged byte-for-byte,
with ZERO regex auto-patching, test-tampering, or source code mutations.
"""

import hashlib
from pathlib import Path
import pytest

from backend.executor import run_sandbox_tests, executor_node, SANDBOX_DIR


class TestSterileSandboxMaterialization:
    """Test byte-for-byte fidelity and zero mutations during sandbox execution."""

    def test_python_code_and_tests_materialized_unchanged(self):
        code_input = {
            "main.py": (
                "from fastapi import FastAPI\n\n"
                "app = FastAPI()\n\n"
                "@app.get('/items')\n"
                "def list_items():\n"
                "    return [{'id': 1, 'name': 'test'}]\n"
            ),
            "models.py": (
                "from pydantic import BaseModel\n\n"
                "class Item(BaseModel):\n"
                "    id: int\n"
                "    name: str\n"
            ),
        }
        test_input = {
            "test_main.py": (
                "from fastapi.testclient import TestClient\n"
                "from main import app\n\n"
                "client = TestClient(app)\n\n"
                "def test_items():\n"
                "    res = client.get('/items')\n"
                "    assert res.status_code == 200\n"
            )
        }

        # Run in ON mode (which previously would have auto-patched with regexes)
        results = run_sandbox_tests(
            code_files=code_input,
            test_files=test_input,
            target_language="python",
            executor_mode="ON",
        )

        # 1. Verify files in SANDBOX_DIR match byte-for-byte
        for fname, expected_content in code_input.items():
            disk_file = SANDBOX_DIR / fname
            assert disk_file.exists(), f"File {fname} not found in sandbox"
            disk_content = disk_file.read_text(encoding="utf-8")
            assert disk_content == expected_content, f"Code mismatch in {fname}"
            assert hashlib.sha256(disk_content.encode("utf-8")).hexdigest() == (
                hashlib.sha256(expected_content.encode("utf-8")).hexdigest()
            )

        for fname, expected_content in test_input.items():
            disk_file = SANDBOX_DIR / fname
            assert disk_file.exists(), f"File {fname} not found in sandbox"
            disk_content = disk_file.read_text(encoding="utf-8")
            assert disk_content == expected_content, f"Test mismatch in {fname}"
            assert hashlib.sha256(disk_content.encode("utf-8")).hexdigest() == (
                hashlib.sha256(expected_content.encode("utf-8")).hexdigest()
            )

        # 2. Results code_files / test_files must also be identical
        res_code = results.get("code_files", {})
        res_tests = results.get("test_files", {})
        assert res_code == code_input
        assert res_tests == test_input

    def test_no_legacy_regex_solvers_or_stubs_injected(self):
        """
        Verify that legacy auto-patches (such as injecting calculate functions,
        mutating route decorators, or altering test assertions) do NOT occur.
        """
        code_input = {
            "main.py": (
                "def custom_function(x: int) -> int:\n"
                "    return x * 2\n"
            )
        }
        test_input = {
            "test_main.py": (
                "from main import custom_function\n\n"
                "def test_custom():\n"
                "    assert custom_function(3) == 6\n"
            )
        }

        results = run_sandbox_tests(
            code_files=code_input,
            test_files=test_input,
            target_language="python",
            executor_mode="ON",
        )

        disk_main = (SANDBOX_DIR / "main.py").read_text(encoding="utf-8")
        assert disk_main == code_input["main.py"]
        assert "calculate" not in disk_main
        assert results["passed"] is True

    def test_executor_node_leaves_state_sterile(self):
        state = {
            "code_files": {
                "main.py": "def add(a, b): return a + b\n"
            },
            "test_files": {
                "test_main.py": "from main import add\ndef test_add(): assert add(1, 2) == 3\n"
            },
            "target_language": "python",
            "iteration_count": 0,
            "logs": [],
            "executor_mode": "CODE_ONLY",
        }

        res = executor_node(state)
        assert res["status"] == "tests_passed"
        assert res["code_files"] == state["code_files"]
        assert res["test_files"] == state["test_files"]
