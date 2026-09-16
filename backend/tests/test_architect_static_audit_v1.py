"""
Static Anti-Solver Audit for Treatment #1.8.1:
Universal Structural Blueprint Fidelity & Repair Preservation v1
ReinDev Studio — Iterasi 6

Behavioral AST & Code Audit:
1. Zero model-specific branching (e.g. if 'qwen' in model).
2. Zero task-preset branching in decision/context logic (e.g. if task == 'fastapi_t1').
3. Zero hardcoded failure-to-solution mapping tables.
4. Schema constraints dynamically derived from ArchitecturalBlueprint canonical definition.
5. Observable behavior guidance without prescriptive implementation-specific mechanisms (WHAT > HOW).
"""

import ast
import inspect
from pathlib import Path
import pytest

import backend.agents.architect as architect_mod
import backend.context_hardening as context_hardening_mod
from backend.blueprint_schema import ArchitecturalBlueprint


def get_ast_tree(module) -> ast.Module:
    source = inspect.getsource(module)
    return ast.parse(source)


class TestArchitectBehavioralAntiSolverAudit:
    """Audit AST and runtime mechanics to ensure capability improvements are universal and generic."""

    def test_01_zero_model_specific_branching_in_architect(self):
        """Architect decision and prompt logic must not branch based on model name."""
        tree = get_ast_tree(architect_mod)
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                test_dump = ast.dump(node.test).lower()
                for forbidden_model in ("qwen", "claude", "gemini", "gpt", "deepseek", "ollama"):
                    assert forbidden_model not in test_dump, (
                        f"Model-specific branching detected in architect.py: {test_dump}"
                    )

    def test_02_zero_model_specific_branching_in_context_hardening(self):
        """Context hardening logic must not branch based on model name."""
        tree = get_ast_tree(context_hardening_mod)
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                test_dump = ast.dump(node.test).lower()
                for forbidden_model in ("qwen", "claude", "gemini", "gpt", "deepseek", "ollama"):
                    assert forbidden_model not in test_dump, (
                        f"Model-specific branching detected in context_hardening.py: {test_dump}"
                    )

    def test_03_zero_preset_task_branching_in_decision_context(self):
        """Decision and repair context generation must not branch on preset task IDs."""
        tree = get_ast_tree(context_hardening_mod)
        forbidden_presets = ("fastapi_t1", "cli_t1", "flutter_t1")
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                test_dump = ast.dump(node.test)
                for preset in forbidden_presets:
                    assert preset not in test_dump, (
                        f"Preset task branching detected in context_hardening.py: {test_dump}"
                    )

    def test_04_schema_constraints_derived_from_canonical_blueprint(self):
        """Schema constraints must be derived directly from ArchitecturalBlueprint.model_fields."""
        constraints_text = context_hardening_mod.format_canonical_blueprint_schema_constraints()
        assert "CANONICAL BLUEPRINT SCHEMA CONSTRAINTS" in constraints_text
        # Must reflect the actual model fields
        for field_name in ("files", "file_tree", "interface_contracts", "data_models"):
            assert field_name in constraints_text, (
                f"Field '{field_name}' from ArchitecturalBlueprint not found in canonical constraints text."
            )

    def test_05_observable_behavior_guidance_non_prescriptive_how(self):
        """Scaffold guidance must guide WHAT (observable behavior) without prescribing HOW (specific exceptions or status codes)."""
        prompt = architect_mod.ARCHITECT_SYSTEM_PROMPT
        assert "OBSERVABLE BEHAVIOR" in prompt
        assert "Do not prescribe implementation-specific mechanisms" in prompt
        # Must NOT prescribe specific implementation codes in the generic scaffold principles
        principles_section = prompt.split("PRINSIP KONSISTENSI")[1]
        assert "status_code=404" not in principles_section
        assert "raise ValueError" not in principles_section
        assert "raise HTTPException" not in principles_section
