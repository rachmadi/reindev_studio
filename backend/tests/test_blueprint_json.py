# -*- coding: utf-8 -*-
"""
Test Suite: Architectural Blueprint JSON Schema & Boundary Rejection
ReinDev Studio — v2.2 (Architectural Modernization)

Memverifikasi:
1. Validasi skema ketat ArchitecturalBlueprint (Pydantic v2).
2. Aturan integritas relasional deterministik (Authoritative file, 1-to-1 files/file_tree, non-empty code_scaffold, interface references).
3. Evaluasi AST per berkas scaffold utuh.
4. Penolakan eksplisit (FAIL V2) terhadap representasi non-JSON / markdown naratif bebas (No silent fallback).
5. Bukti diagnostik CEP B2 agnostik framework (tanpa hardcoding FastAPI/Flutter).
"""

import json
import pytest
from backend.blueprint_schema import (
    ArchitecturalBlueprint,
    BlueprintFileModule,
    BlueprintInterfaceContract,
    parse_blueprint_json,
    extract_blueprint_json_text,
    blueprint_to_narrative_markdown
)
from backend.architect_validator import (
    validate_json_blueprint,
    validate_architect_blueprint
)
from backend.phase_validators import validate_architect_phase
from backend.context_assembler import assemble_b2_evidence, synthesize_b2_actionable_prescriptions
from backend.contextual_evidence import ViolationItem


# ==============================================================================
# 1. Skema Ketat & Relational Invariant Tests
# ==============================================================================

def test_valid_architectural_blueprint():
    valid_data = {
        "schema_version": "1.0.0",
        "task_id": "fastapi_t1",
        "target_language": "python",
        "authoritative_target_file": "main.py",
        "file_tree": ["main.py"],
        "architecture_summary": "REST API FastAPI untuk inventaris produk",
        "files": {
            "main.py": {
                "file_path": "main.py",
                "module_role": "Authoritative Single Module",
                "imports": ["from typing import Optional"],
                "code_scaffold": "def add(a: int, b: int) -> int:\n    return a + b\n"
            }
        },
        "interface_contracts": [
            {
                "identifier": "add",
                "target_file": "main.py"
            }
        ]
    }
    bp = ArchitecturalBlueprint.model_validate(valid_data)
    assert bp.authoritative_target_file == "main.py"
    assert "main.py" in bp.files
    assert len(bp.interface_contracts) == 1


def test_missing_authoritative_target_file_in_files_raises():
    bad_data = {
        "task_id": "t1",
        "authoritative_target_file": "main.py",
        "file_tree": ["other.py"],
        "files": {
            "other.py": {
                "file_path": "other.py",
                "code_scaffold": "x = 1"
            }
        }
    }
    with pytest.raises(ValueError, match="authoritative_target_file 'main.py' tidak ditemukan dalam kamus 'files'"):
        ArchitecturalBlueprint.model_validate(bad_data)


def test_phantom_files_in_file_tree_raises():
    bad_data = {
        "task_id": "t1",
        "authoritative_target_file": "main.py",
        "file_tree": ["main.py", "phantom.py"],
        "files": {
            "main.py": {
                "file_path": "main.py",
                "code_scaffold": "x = 1"
            }
        }
    }
    with pytest.raises(ValueError, match="File dideklarasikan di 'file_tree' tetapi tidak memiliki modul scaffold di 'files'"):
        ArchitecturalBlueprint.model_validate(bad_data)


def test_empty_code_scaffold_raises():
    bad_data = {
        "file_path": "main.py",
        "code_scaffold": "   "
    }
    with pytest.raises(ValueError, match="code_scaffold wajib diisi"):
        BlueprintFileModule.model_validate(bad_data)


def test_orphan_interface_contract_target_raises():
    bad_data = {
        "task_id": "t1",
        "authoritative_target_file": "main.py",
        "file_tree": ["main.py"],
        "files": {
            "main.py": {
                "file_path": "main.py",
                "code_scaffold": "x = 1"
            }
        },
        "interface_contracts": [
            {
                "identifier": "run",
                "target_file": "nonexistent.py"
            }
        ]
    }
    with pytest.raises(ValueError, match="menunjuk target_file 'nonexistent.py' yang tidak eksis"):
        ArchitecturalBlueprint.model_validate(bad_data)


# ==============================================================================
# 2. Rejection of Non-JSON / No-Fallback Tests
# ==============================================================================

def test_validate_architect_blueprint_rejects_plain_markdown():
    plain_markdown = """### Rencana Arsitektur
Berikut adalah struktur file:
```python
def add(a, b):
    return a + b
```
"""
    is_valid, errors = validate_architect_blueprint(plain_markdown, "python")
    assert not is_valid
    assert any("SCHEMA_VIOLATION" in err for err in errors)
    assert any("Cetak biru arsitektur tidak memuat blok JSON kanonikal" in err for err in errors)


def test_validate_architect_blueprint_accepts_valid_json_block():
    raw_bp = """Penjelasan naratif arsitektur arsitek:
=== BLUEPRINT JSON ===
{
  "task_id": "test_bp",
  "target_language": "python",
  "authoritative_target_file": "main.py",
  "file_tree": ["main.py"],
  "architecture_summary": "Modul kalkulator",
  "files": {
    "main.py": {
      "file_path": "main.py",
      "module_role": "Authoritative Single Module",
      "imports": [],
      "code_scaffold": "def kalkulator(a: int, b: int) -> int:\n    return a + b\n"
    }
  },
  "interface_contracts": [
    {
      "identifier": "kalkulator",
      "target_file": "main.py"
    }
  ]
}
=== END BLUEPRINT JSON ===
Teks penutup dari arsitek.
"""
    is_valid, errors = validate_architect_blueprint(raw_bp, "python")
    assert is_valid, f"Expected valid, got errors: {errors}"
    assert len(errors) == 0


# ==============================================================================
# 3. AST Scope & Decorator Resolution Tests
# ==============================================================================

def test_ast_resolves_decorator_when_defined_in_same_file():
    raw_bp = """=== BLUEPRINT JSON ===
{
  "task_id": "fastapi_test",
  "target_language": "python",
  "authoritative_target_file": "main.py",
  "file_tree": ["main.py"],
  "architecture_summary": "FastAPI App",
  "files": {
    "main.py": {
      "file_path": "main.py",
      "module_role": "Authoritative Single Module",
      "imports": ["from fastapi import FastAPI"],
      "code_scaffold": "from fastapi import FastAPI\napp = FastAPI()\n@app.get('/health')\ndef health():\n    return {'status': 'ok'}\n"
    }
  },
  "interface_contracts": []
}
=== END BLUEPRINT JSON ==="""
    is_valid, errors = validate_architect_blueprint(raw_bp, "python")
    assert is_valid, f"Expected decorator @app to resolve, got: {errors}"


def test_ast_fails_when_decorator_unresolved():
    raw_bp = """=== BLUEPRINT JSON ===
{
  "task_id": "fastapi_broken",
  "target_language": "python",
  "authoritative_target_file": "main.py",
  "file_tree": ["main.py"],
  "architecture_summary": "FastAPI App Broken",
  "files": {
    "main.py": {
      "file_path": "main.py",
      "module_role": "Authoritative Single Module",
      "imports": [],
      "code_scaffold": "@app.get('/health')\ndef health():\n    return {'status': 'ok'}\n"
    }
  },
  "interface_contracts": []
}
=== END BLUEPRINT JSON ==="""
    is_valid, errors = validate_architect_blueprint(raw_bp, "python")
    assert not is_valid
    assert any("@app" in err for err in errors)


# ==============================================================================
# 4. Agnostic Actionable CEP B2 Prescription Tests
# ==============================================================================

def test_b2_prescription_is_actionable_and_framework_agnostic():
    violations = [
        ViolationItem(
            violation_id="VIO-001",
            criterion="blueprint_ast_consistency",
            severity="CRITICAL",
            location="architecture_plan",
            observed_state="Berkas 'main.py' (baris 5): Simbol '@app' digunakan sebagai decorator, namun tidak ditemukan dalam statement import maupun deklarasi lokal.",
            expected_state="Simbol '@app' dideklarasikan atau diimpor dalam modul berkas sebelum digunakan",
            source_detector="PHASE_VALIDATOR_DETERMINISTIC",
            observed_symbol="@app"
        )
    ]

    rx_list = synthesize_b2_actionable_prescriptions(violations, auth_file="main.py", target_lang="python")
    assert len(rx_list) == 1
    rx = rx_list[0]

    # Preskripsi memuat simbol dan file target
    assert "@app" in rx.required_change
    assert "main.py" in rx.required_change

    # Preskripsi TIDAK memuat hardcoding spesifik framework
    assert "from fastapi import FastAPI" not in rx.required_change
    assert "app = FastAPI()" not in rx.required_change
    assert "FastAPI" not in rx.required_change

    # Preskripsi memuat boundary dan post repair state yang valid
    assert len(rx.repair_boundary_allowed) > 0
    assert len(rx.repair_boundary_forbidden) > 0
    assert rx.expected_post_repair_state != ""
    assert rx.verification_evidence != ""
