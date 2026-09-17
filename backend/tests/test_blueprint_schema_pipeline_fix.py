# -*- coding: utf-8 -*-
"""
Test Suite: Pipeline Integrity Fix — Remove Language-Biased Schema Default v1
Verifies:
A. No language-specific filename is silently injected.
B. A Blueprint missing authoritative_target_file is rejected.
C. An explicit valid authoritative_target_file is accepted.
D. An explicit target that does not exist in files remains rejected.
E. A non-Python target such as a generic path can be accepted when explicitly represented and structurally consistent.
F. Existing Python behavior remains valid when the target is explicitly supplied.
"""

import pytest
from pydantic_core import PydanticUndefined
from pydantic import ValidationError

from backend.blueprint_schema import (
    ArchitecturalBlueprint,
    BlueprintFileModule,
    BlueprintInterfaceContract,
)


class TestPipelineIntegritySchemaDefaultRemoval:
    """Deterministic tests A-F verifying removal of language-biased schema defaults."""

    def test_a_no_language_specific_filename_silently_injected(self):
        """Test A: No language-specific filename is silently injected via schema default."""
        field = ArchitecturalBlueprint.model_fields["authoritative_target_file"]
        assert field.default is PydanticUndefined or field.default is None, (
            f"Expected no default on authoritative_target_file, found: {field.default}"
        )
        assert field.is_required() is True, "authoritative_target_file must be a required field"

    def test_b_missing_authoritative_target_file_rejected(self):
        """Test B: A Blueprint missing authoritative_target_file is rejected."""
        synthetic_data = {
            "file_tree": ["synthetic/worker.ext"],
            "files": {
                "synthetic/worker.ext": {
                    "file_path": "synthetic/worker.ext",
                    "code_scaffold": "// synthetic code scaffold"
                }
            }
        }
        with pytest.raises(ValidationError) as exc_info:
            ArchitecturalBlueprint.model_validate(synthetic_data)

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("authoritative_target_file",) for e in errors), (
            f"Expected missing authoritative_target_file validation error, got: {errors}"
        )

    def test_c_explicit_valid_authoritative_target_file_accepted(self):
        """Test C: An explicit valid authoritative_target_file is accepted."""
        target_path = "core/engine.xyz"
        synthetic_data = {
            "authoritative_target_file": target_path,
            "file_tree": [target_path],
            "architecture_summary": "Generic synthetic architecture",
            "files": {
                target_path: {
                    "file_path": target_path,
                    "code_scaffold": "export class Engine {}"
                }
            },
            "interface_contracts": [
                {
                    "identifier": "process",
                    "target_file": target_path
                }
            ]
        }
        bp = ArchitecturalBlueprint.model_validate(synthetic_data)
        assert bp.authoritative_target_file == target_path
        assert target_path in bp.files
        assert bp.files[target_path].file_path == target_path

    def test_d_explicit_target_missing_in_files_rejected(self):
        """Test D: An explicit target that does not exist in files remains rejected per canonical rule."""
        synthetic_data = {
            "authoritative_target_file": "declared/entrypoint.xyz",
            "file_tree": ["other/file.xyz"],
            "files": {
                "other/file.xyz": {
                    "file_path": "other/file.xyz",
                    "code_scaffold": "module file;"
                }
            }
        }
        with pytest.raises(ValueError, match="tidak ditemukan dalam kamus 'files'"):
            ArchitecturalBlueprint.model_validate(synthetic_data)

    def test_e_generic_non_python_target_accepted_when_consistent(self):
        """Test E: A non-Python target such as a generic path is accepted when explicitly represented and consistent."""
        generic_path = "lib/domain/widget_component.ext"
        synthetic_data = {
            "target_language": "generic_lang",
            "authoritative_target_file": generic_path,
            "file_tree": [generic_path],
            "architecture_summary": "Generic non-python modular blueprint",
            "files": {
                generic_path: {
                    "file_path": generic_path,
                    "module_role": "Primary Component",
                    "code_scaffold": "component WidgetComponent { state: ready; }"
                }
            },
            "interface_contracts": [
                {
                    "identifier": "WidgetComponent",
                    "target_file": generic_path
                }
            ]
        }
        bp = ArchitecturalBlueprint.model_validate(synthetic_data)
        assert bp.authoritative_target_file == generic_path
        assert bp.target_language == "generic_lang"
        assert generic_path in bp.files
        assert bp.file_tree == [generic_path]

    def test_f_existing_python_behavior_valid_when_explicitly_supplied(self):
        """Test F: Existing Python behavior remains valid when the target is explicitly supplied."""
        synthetic_data = {
            "target_language": "python",
            "authoritative_target_file": "main.py",
            "file_tree": ["main.py"],
            "architecture_summary": "Standard python module",
            "files": {
                "main.py": {
                    "file_path": "main.py",
                    "module_role": "Entrypoint",
                    "code_scaffold": "def entrypoint() -> None:\n    pass\n"
                }
            },
            "interface_contracts": [
                {
                    "identifier": "entrypoint",
                    "target_file": "main.py"
                }
            ]
        }
        bp = ArchitecturalBlueprint.model_validate(synthetic_data)
        assert bp.authoritative_target_file == "main.py"
        assert "main.py" in bp.files
        assert bp.interface_contracts[0].identifier == "entrypoint"
