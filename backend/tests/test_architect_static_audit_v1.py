"""
Static Anti-Solver Audit for Treatment #1.8: Universal Acceptance-Grounded Architectural Synthesis v1
ReinDev Studio — Iterasi 6

Audit verifies that Architect implementation is strictly DOMAIN-AGNOSTIC, TASK-AGNOSTIC,
and MODEL-AGNOSTIC. It detects substantive solver behavior:
1. Conditional task/domain solver logic (e.g. if task == 'fastapi', if 'matrix' in task).
2. Hardcoded failure -> solution mappings.
3. Hardcoded symbol injection into outputs.
4. Hardcoded architecture selection based on task names.
5. Model-specific solver logic.
"""

import ast
import inspect
import re
from pathlib import Path
import pytest

from backend.agents import architect
from backend import context_hardening


def _get_ast_tree(module_or_path):
    if isinstance(module_or_path, (str, Path)):
        src = Path(module_or_path).read_text(encoding="utf-8")
    else:
        src = inspect.getsource(module_or_path)
    return ast.parse(src), src


class TestArchitectStaticAntiSolverAudit:
    """Static AST and code audit for substantive solver behavior."""

    def test_no_task_domain_conditional_solvers_in_architect(self):
        """
        Verify no 'if task == ...', 'if matrix in task', 'if product in user_task'
        or hardcoded branch logic exists in architect.py.
        """
        tree, src = _get_ast_tree(architect)

        # Disallowed solver branch patterns
        solver_regexes = [
            r"if\s+.*(?:task|domain|user_task)\s*==\s*['\"]",
            r"if\s+['\"](?:fastapi|cli|flutter|matrix|product)['\"]\s+in\s+(?:task|user_task|domain)",
            r"if\s+.*(?:fastapi_t1|cli_t1|flutter_t1)",
            r"if\s+.*(?:qwen|claude|gpt|llama)\b",
        ]
        for pattern in solver_regexes:
            matches = re.findall(pattern, src, re.IGNORECASE)
            assert not matches, f"Found solver conditional pattern '{pattern}': {matches}"

    def test_no_hardcoded_failure_solution_mappings_in_architect(self):
        """Verify no lookup table mapping specific failure codes or oracle names to architectural blueprints."""
        tree, src = _get_ast_tree(architect)

        mapping_patterns = [
            r"\{\s*['\"](?:FP00|FP-00|OBL-HTTP-DELETE|test_add_matrices)['\"]\s*:",
            r"if\s+.*(?:OBL-HTTP-DELETE|OBL-CLI|FP003|FP004|FP005)\b",
        ]
        for pattern in mapping_patterns:
            matches = re.findall(pattern, src, re.IGNORECASE)
            assert not matches, f"Found hardcoded failure mapping '{pattern}': {matches}"

    def test_no_hardcoded_symbol_injection_in_context_hardening(self):
        """Verify context_hardening does not inject task-specific symbols into context packages."""
        tree, src = _get_ast_tree(context_hardening)

        # Check for hardcoded task-specific symbols injected as solutions
        solver_symbols = [
            r"['\"](?:add_matrices|subtract_matrices|multiply_matrices)['\"]",
            r"['\"]/products/\{id\}['\"]",
            r"['\"]CardMetric['\"]",
        ]
        # In context_hardening, these should NOT appear as hardcoded injected strings in context builder
        for pat in solver_symbols:
            matches = re.findall(pat, src)
            assert not matches, f"Found hardcoded symbol injection in context_hardening '{pat}': {matches}"

    def test_generic_ast_visitor_no_framework_solver(self):
        """Verify architect_agent function uses LLM synthesis, not deterministic dictionary overrides."""
        src = inspect.getsource(architect.architect_agent)
        # Ensure architect_agent invokes the LLM
        assert "llm.invoke" in src
        assert "parse_blueprint_json" in src

    def test_pure_artifact_guidance_present(self):
        """Verify artifact purity instruction is embedded in architect prompt."""
        src = inspect.getsource(architect.architect_agent)
        assert "ARTIFACT PURITY" in src
