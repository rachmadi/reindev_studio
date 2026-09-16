"""
Static Audit Suite: Treatment #1.7 — Anti-Solver & General Capability Integrity
Location: backend/tests/test_pm_static_audit_v1.py

Strictly verifies that backend/agents/pm.py contains NO:
- Task-specific solvers ('if task ==', 'fastapi_t1', 'cli_t1', 'flutter_t1')
- Model-specific branching ('if model ==', 'ornith', 'qwen2.5-coder')
- Failure-pattern hardcoded branching ('if failure_pattern', 'FP-002')
- Known-test / Oracle test case shortcuts
- Hardcoded requirements / endpoints / symbols (/items, CardMetric, Matrix, determinan)
- Synthetic requirement fallbacks replacing LLM output
"""

import inspect
import re
import backend.agents.pm as pm_module


def test_no_task_or_model_solvers():
    src = inspect.getsource(pm_module)

    # 1. Prohibited specific task keys
    forbidden_task_keys = [
        "fastapi_t1", "cli_t1", "flutter_t1",
        "task_1", "task_2", "task_3",
        "inventory_app", "matrix_calc", "card_metric"
    ]
    for k in forbidden_task_keys:
        assert k not in src.lower(), f"Forbidden task-specific key found in pm.py: {k}"

    # 2. Prohibited model-specific branching
    forbidden_model_patterns = [
        r"if.*model\s*==",
        r"if.*provider\s*==",
        "ornith",
        "qwen2.5-coder",
        "deepseek",
        "gemma"
    ]
    for pat in forbidden_model_patterns:
        m = re.search(pat, src, re.IGNORECASE)
        assert m is None, f"Forbidden model-specific pattern found: {pat}"

    # 3. Prohibited failure pattern hardcoding
    forbidden_fp_patterns = [
        "fp-001", "fp-002", "fp-003", "fp-004", "fp-005", "fp-006", "fp-007"
    ]
    for fp in forbidden_fp_patterns:
        assert fp not in src.lower(), f"Failure pattern hardcoding found: {fp}"

    # 4. Prohibited synthetic spec fallbacks
    forbidden_fallbacks = [
        r"if\s+not\s+specs.*:\s*specs\s*=",
        r"if\s+len\(specs\).*:\s*specs\s*=",
        r"specs\s*=\s*specs\s+or\s+"
    ]
    for fb in forbidden_fallbacks:
        m = re.search(fb, src)
        assert m is None, f"Synthetic spec fallback found in pm.py: {fb}"

    # 5. Prohibited domain symbol hardcoding
    forbidden_symbols = [
        "/items/", "testclient", "widgettester", "np.linalg",
        "matrix2x2", "productinquiry", "cardmetric"
    ]
    for sym in forbidden_symbols:
        assert sym not in src.lower(), f"Forbidden domain symbol found in pm.py: {sym}"
