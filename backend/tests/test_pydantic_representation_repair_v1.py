# -*- coding: utf-8 -*-
"""
Test Suite: Treatment #1.8.3 — Deterministic Pydantic Representation Repair v1
Tests A through M as specified in the Treatment #1.8.3 directive:
- Test A: Canonical string -> unchanged.
- Test B: Supported representation (single wrapper) -> deterministic normalization.
- Test C: Unsupported arbitrary dict in code_scaffold -> rejected.
- Test D: list[str] in code_scaffold -> deterministic normalization.
- Test E: Explicit aliases mapping across all blueprint entities.
- Test F: Ambiguous alias collision -> rejected.
- Test G: Zero field loss.
- Test H: Zero semantic invention.
- Test I: Semantic equivalence guard pass.
- Test J: Malformed representation -> rejected cleanly.
- Test K: Generic Python micro-service fixture.
- Test L: Generic Dart component fixture.
- Test M: Unrelated generic domain fixture (Rust / Go / Kotlin AST).
"""

import pytest
import json
from backend.blueprint_schema import (
    ArchitecturalBlueprint,
    BlueprintFileModule,
    BlueprintInterfaceContract,
    BlueprintDataModel,
    BlueprintModelField,
    BlueprintErrorClass,
    classify_blueprint_error,
    parse_blueprint_json,
    parse_blueprint_json_classified,
    verify_blueprint_semantic_equivalence,
    extract_blueprint_json_text,
)


class TestDeterministicPydanticRepresentationRepairV1:
    """Comprehensive test suite for deterministic representation normalization."""

    # -------------------------------------------------------------------------
    # Test A: Canonical string -> unchanged
    # -------------------------------------------------------------------------
    def test_a_canonical_string_unchanged(self):
        """Test A: Canonical string code_scaffold and canonical fields are preserved unchanged."""
        scaffold_code = "def calculate_total(items: list) -> float:\n    return sum(items)\n"
        bp_dict = {
            "schema_version": "1.0.0",
            "task_id": "task_calc",
            "target_language": "python",
            "authoritative_target_file": "calculator.py",
            "file_tree": ["calculator.py"],
            "architecture_summary": "Modular calculator service",
            "files": {
                "calculator.py": {
                    "file_path": "calculator.py",
                    "module_role": "Authoritative Single Module",
                    "imports": ["from typing import List"],
                    "code_scaffold": scaffold_code,
                    "description": "Core calculation module"
                }
            },
            "interface_contracts": [
                {
                    "identifier": "calculate_total",
                    "route": "/total",
                    "method": "POST",
                    "target_file": "calculator.py"
                }
            ],
            "data_models": []
        }
        raw_json = f"=== BLUEPRINT JSON ===\n{json.dumps(bp_dict)}\n=== END BLUEPRINT JSON ==="
        bp, err, err_cls = parse_blueprint_json_classified(raw_json)

        assert err is None
        assert err_cls is None
        assert bp is not None
        assert bp.authoritative_target_file == "calculator.py"
        assert bp.files["calculator.py"].code_scaffold == scaffold_code
        assert bp.files["calculator.py"].module_role == "Authoritative Single Module"

        is_equiv, diffs = verify_blueprint_semantic_equivalence(bp_dict, bp)
        assert is_equiv is True
        assert len(diffs) == 0

    # -------------------------------------------------------------------------
    # Test B: Supported representation (single wrapper unwrapping)
    # -------------------------------------------------------------------------
    def test_b_supported_single_wrapper_unwrapped(self):
        """Test B: Single-key explicit code wrapper is unwrapped deterministically."""
        inner_code = "def greet(name: str) -> str:\n    return f'Hello {name}'\n"
        bp_dict = {
            "authoritative_target_file": "greeter.py",
            "file_tree": ["greeter.py"],
            "architecture_summary": "Greeting service",
            "files": {
                "greeter.py": {
                    "file_path": "greeter.py",
                    "code_scaffold": {
                        "code": inner_code
                    }
                }
            }
        }
        raw_json = f"```json\n{json.dumps(bp_dict)}\n```"
        bp, err, err_cls = parse_blueprint_json_classified(raw_json)

        assert err is None
        assert err_cls is None
        assert bp is not None
        assert bp.files["greeter.py"].code_scaffold == inner_code

        is_equiv, diffs = verify_blueprint_semantic_equivalence(bp_dict, bp)
        assert is_equiv is True
        assert len(diffs) == 0

    # -------------------------------------------------------------------------
    # Test C: Unsupported arbitrary dict in code_scaffold -> rejected
    # -------------------------------------------------------------------------
    def test_c_arbitrary_dict_in_code_scaffold_rejected(self):
        """Test C: Multi-key arbitrary dict in code_scaffold is strictly rejected without semantic guessing."""
        bp_dict = {
            "authoritative_target_file": "main.py",
            "file_tree": ["main.py"],
            "architecture_summary": "Fragmented app",
            "files": {
                "main.py": {
                    "file_path": "main.py",
                    "code_scaffold": {
                        "imports": ["import os", "import sys"],
                        "models": ["class Item: pass"],
                        "endpoints": ["def route(): pass"]
                    }
                }
            }
        }
        raw_json = f"=== BLUEPRINT JSON ===\n{json.dumps(bp_dict)}\n=== END BLUEPRINT JSON ==="
        bp, err, err_cls = parse_blueprint_json_classified(raw_json)

        assert bp is None
        assert err is not None
        assert err_cls == BlueprintErrorClass.UNRECOVERABLE_REPRESENTATION_ERROR
        assert "UNRECOVERABLE_REPRESENTATION_ERROR" in err
        assert "Arbitrary dict in code_scaffold" in err

    # -------------------------------------------------------------------------
    # Test D: list[str] in code_scaffold -> deterministic normalization
    # -------------------------------------------------------------------------
    def test_d_list_of_strings_in_code_scaffold_joined(self):
        """Test D: list[str] in code_scaffold is deterministically joined with newlines."""
        lines = [
            "import os",
            "import sys",
            "",
            "def run_cli():",
            "    print('CLI running')"
        ]
        bp_dict = {
            "authoritative_target_file": "cli_app.py",
            "file_tree": ["cli_app.py"],
            "architecture_summary": "CLI tool",
            "files": {
                "cli_app.py": {
                    "file_path": "cli_app.py",
                    "code_scaffold": lines
                }
            }
        }
        raw_json = f"=== BLUEPRINT JSON ===\n{json.dumps(bp_dict)}\n=== END BLUEPRINT JSON ==="
        bp, err, err_cls = parse_blueprint_json_classified(raw_json)

        assert err is None
        assert err_cls is None
        assert bp is not None
        expected_joined = "\n".join(lines)
        assert bp.files["cli_app.py"].code_scaffold == expected_joined

        is_equiv, diffs = verify_blueprint_semantic_equivalence(bp_dict, bp)
        assert is_equiv is True
        assert len(diffs) == 0

    # -------------------------------------------------------------------------
    # Test E: Explicit aliases mapping across all blueprint entities
    # -------------------------------------------------------------------------
    def test_e_explicit_aliases_mapping(self):
        """Test E: Canonical schema accepts standard structural aliases across all entities."""
        bp_dict = {
            "target_file": "service.py",  # alias for authoritative_target_file
            "tree": ["service.py"],        # alias for file_tree
            "summary": "Service summary",  # alias for architecture_summary
            "file_modules": [              # alias for files (and as list of dicts)
                {
                    "path": "service.py",      # alias for file_path
                    "role": "Core Service",    # alias for module_role
                    "scaffold": "def serve(): pass\n",  # alias for code_scaffold
                    "desc": "Primary service entry"     # alias for description
                }
            ],
            "interfaces": [                # alias for interface_contracts
                {
                    "name": "serve_request",   # alias for identifier
                    "path": "/serve",          # alias for route
                    "http_method": "GET",      # alias for method
                    "file": "service.py"       # alias for target_file
                }
            ],
            "models": [                    # alias for data_models
                {
                    "name": "RequestPayload",  # alias for model_name
                    "target": "service.py",    # alias for target_file
                    "attributes": [            # alias for fields
                        {
                            "name": "client_id",   # alias for field_name
                            "type": "str",         # alias for field_type
                            "required": True       # alias for is_required
                        }
                    ]
                }
            ]
        }
        raw_json = f"=== BLUEPRINT JSON ===\n{json.dumps(bp_dict)}\n=== END BLUEPRINT JSON ==="
        bp, err, err_cls = parse_blueprint_json_classified(raw_json)

        assert err is None
        assert err_cls is None
        assert bp is not None
        assert bp.authoritative_target_file == "service.py"
        assert bp.file_tree == ["service.py"]
        assert bp.architecture_summary == "Service summary"
        assert "service.py" in bp.files
        mod = bp.files["service.py"]
        assert mod.file_path == "service.py"
        assert mod.module_role == "Core Service"
        assert mod.code_scaffold == "def serve(): pass\n"
        assert mod.description == "Primary service entry"

        assert len(bp.interface_contracts) == 1
        ifc = bp.interface_contracts[0]
        assert ifc.identifier == "serve_request"
        assert ifc.route == "/serve"
        assert ifc.method == "GET"
        assert ifc.target_file == "service.py"

        assert len(bp.data_models) == 1
        dm = bp.data_models[0]
        assert dm.model_name == "RequestPayload"
        assert dm.target_file == "service.py"
        assert len(dm.fields) == 1
        fld = dm.fields[0]
        assert fld.field_name == "client_id"
        assert fld.field_type == "str"
        assert fld.is_required is True

    # -------------------------------------------------------------------------
    # Test F: Ambiguous alias collision -> rejected
    # -------------------------------------------------------------------------
    def test_f_ambiguous_alias_collision_rejected(self):
        """Test F: When canonical and alias are both present with conflicting values, strictly reject as SEMANTIC_ERROR."""
        # 1. Collision in root authoritative_target_file
        bp_dict_root = {
            "authoritative_target_file": "main.py",
            "target_file": "other.py",
            "file_tree": ["main.py"],
            "files": {"main.py": {"file_path": "main.py", "code_scaffold": "pass"}}
        }
        bp, err, err_cls = parse_blueprint_json_classified(json.dumps(bp_dict_root))
        assert bp is None
        assert err_cls == BlueprintErrorClass.SEMANTIC_ERROR
        assert "REPRESENTATION CONFLICT" in err

        # 2. Collision in field_name vs name
        bp_dict_field = {
            "authoritative_target_file": "main.py",
            "file_tree": ["main.py"],
            "files": {"main.py": {"file_path": "main.py", "code_scaffold": "pass"}},
            "data_models": [
                {
                    "model_name": "User",
                    "target_file": "main.py",
                    "fields": [
                        {
                            "field_name": "canonical_id",
                            "name": "aliased_id",
                            "field_type": "str"
                        }
                    ]
                }
            ]
        }
        bp, err, err_cls = parse_blueprint_json_classified(json.dumps(bp_dict_field))
        assert bp is None
        assert err_cls == BlueprintErrorClass.SEMANTIC_ERROR
        assert "REPRESENTATION CONFLICT" in err

        # 3. Collision in interface identifier vs name
        bp_dict_ifc = {
            "authoritative_target_file": "main.py",
            "file_tree": ["main.py"],
            "files": {"main.py": {"file_path": "main.py", "code_scaffold": "pass"}},
            "interface_contracts": [
                {
                    "identifier": "get_user",
                    "name": "fetch_user",
                    "target_file": "main.py"
                }
            ]
        }
        bp, err, err_cls = parse_blueprint_json_classified(json.dumps(bp_dict_ifc))
        assert bp is None
        assert err_cls == BlueprintErrorClass.SEMANTIC_ERROR
        assert "REPRESENTATION CONFLICT" in err

    # -------------------------------------------------------------------------
    # Test G: Zero field loss
    # -------------------------------------------------------------------------
    def test_g_zero_field_loss(self):
        """Test G: Normalization does not discard secondary metadata, constraints, or description."""
        bp_dict = {
            "authoritative_target_file": "app.py",
            "file_tree": ["app.py"],
            "architecture_summary": "Test app",
            "files": {
                "app.py": {
                    "file_path": "app.py",
                    "module_role": "Core",
                    "imports": ["from pydantic import BaseModel, Field"],
                    "code_scaffold": "class Model: pass",
                    "description": "Essential core app file"
                }
            },
            "data_models": [
                {
                    "model_name": "Config",
                    "target_file": "app.py",
                    "fields": [
                        {
                            "field_name": "port",
                            "field_type": "int",
                            "is_required": True,
                            "constraints": {"ge": 1024, "le": 65535},
                            "description": "Listening port"
                        }
                    ],
                    "construction_shape": {"default": 8080}
                }
            ]
        }
        bp, err, err_cls = parse_blueprint_json_classified(json.dumps(bp_dict))
        assert err is None
        assert bp is not None

        mod = bp.files["app.py"]
        assert mod.imports == ["from pydantic import BaseModel, Field"]
        assert mod.description == "Essential core app file"

        dm = bp.data_models[0]
        assert dm.construction_shape == {"default": 8080}
        fld = dm.fields[0]
        assert fld.constraints == {"ge": 1024, "le": 65535}
        assert fld.description == "Listening port"

    # -------------------------------------------------------------------------
    # Test H: Zero semantic invention
    # -------------------------------------------------------------------------
    def test_h_zero_semantic_invention(self):
        """Test H: Normalization never invents files, contracts, or models not provided in raw input."""
        bp_dict = {
            "authoritative_target_file": "solo.py",
            "file_tree": ["solo.py"],
            "architecture_summary": "Minimal solo blueprint",
            "files": {
                "solo.py": {
                    "file_path": "solo.py",
                    "code_scaffold": "def solo(): return 1\n"
                }
            }
        }
        bp, err, err_cls = parse_blueprint_json_classified(json.dumps(bp_dict))
        assert err is None
        assert bp is not None

        assert len(bp.files) == 1
        assert list(bp.files.keys()) == ["solo.py"]
        assert len(bp.interface_contracts) == 0
        assert len(bp.data_models) == 0

        is_equiv, diffs = verify_blueprint_semantic_equivalence(bp_dict, bp)
        assert is_equiv is True
        assert len(diffs) == 0

    # -------------------------------------------------------------------------
    # Test I: Semantic equivalence guard pass & fail cases
    # -------------------------------------------------------------------------
    def test_i_semantic_equivalence_guard(self):
        """Test I: verify_blueprint_semantic_equivalence catches alterations and validates equivalents."""
        raw_dict = {
            "target_file": "worker.py",
            "tree": ["worker.py"],
            "files": {
                "worker.py": "def work(): pass\n"  # Direct string mapping
            },
            "contracts": [
                {"name": "do_work", "file": "worker.py"}
            ]
        }
        bp, err, _ = parse_blueprint_json_classified(json.dumps(raw_dict))
        assert bp is not None
        assert err is None

        # Clean equivalence
        is_equiv, diffs = verify_blueprint_semantic_equivalence(raw_dict, bp)
        assert is_equiv is True
        assert diffs == []

        # Tampered scaffold -> equivalence fails
        bp.files["worker.py"].code_scaffold = "def altered(): pass\n"
        is_equiv2, diffs2 = verify_blueprint_semantic_equivalence(raw_dict, bp)
        assert is_equiv2 is False
        assert any("mismatch" in d for d in diffs2)

    # -------------------------------------------------------------------------
    # Test J: Malformed representation -> rejected cleanly
    # -------------------------------------------------------------------------
    def test_j_malformed_representation_rejected_cleanly(self):
        """Test J: Malformed, non-JSON, and structural invariant violations fail cleanly with appropriate classes."""
        # 1. Plain text with no JSON
        bp1, err1, cls1 = parse_blueprint_json_classified("Here is the architecture: we will use main.py")
        assert bp1 is None
        assert cls1 == BlueprintErrorClass.UNRECOVERABLE_REPRESENTATION_ERROR

        # 2. JSON Array at root
        bp2, err2, cls2 = parse_blueprint_json_classified("[{'file': 'main.py'}]")
        assert bp2 is None
        assert cls2 == BlueprintErrorClass.UNRECOVERABLE_REPRESENTATION_ERROR

        # 3. Missing authoritative_target_file from files (Structural error)
        missing_target_dict = {
            "authoritative_target_file": "missing.py",
            "file_tree": ["missing.py", "existing.py"],
            "files": {
                "existing.py": {"file_path": "existing.py", "code_scaffold": "pass"}
            }
        }
        bp3, err3, cls3 = parse_blueprint_json_classified(json.dumps(missing_target_dict))
        assert bp3 is None
        assert cls3 == BlueprintErrorClass.STRUCTURAL_ERROR

        # 4. Phantom file in file_tree not in files
        phantom_dict = {
            "authoritative_target_file": "main.py",
            "file_tree": ["main.py", "phantom.py"],
            "files": {
                "main.py": {"file_path": "main.py", "code_scaffold": "pass"}
            }
        }
        bp4, err4, cls4 = parse_blueprint_json_classified(json.dumps(phantom_dict))
        assert bp4 is None
        assert cls4 == BlueprintErrorClass.STRUCTURAL_ERROR

    # -------------------------------------------------------------------------
    # Test K: Generic Python micro-service fixture
    # -------------------------------------------------------------------------
    def test_k_generic_python_microservice_fixture(self):
        """Test K: Real-world complex Python web service blueprint normalizes deterministically."""
        raw_plan = """
=== BLUEPRINT JSON ===
{
  "target_file": "api/server.py",
  "file_tree": ["api/server.py", "api/models.py"],
  "architecture_summary": "RESTful API Microservice",
  "files": {
    "api/server.py": {
      "file_path": "api/server.py",
      "module_role": "Application Gateway",
      "imports": ["from fastapi import FastAPI", "from .models import ItemDTO"],
      "code_scaffold": [
        "app = FastAPI()",
        "",
        "@app.get('/items/{item_id}')",
        "def get_item(item_id: int) -> ItemDTO:",
        "    return ItemDTO(item_id=item_id, name='Test')"
      ]
    },
    "api/models.py": {
      "file_path": "api/models.py",
      "module_role": "Domain Entities",
      "imports": ["from pydantic import BaseModel"],
      "code_scaffold": [
        "class ItemDTO(BaseModel):",
        "    item_id: int",
        "    name: str"
      ]
    }
  },
  "interface_contracts": [
    {
      "identifier": "get_item",
      "route": "/items/{item_id}",
      "method": "GET",
      "target_file": "api/server.py"
    }
  ],
  "data_models": [
    {
      "model_name": "ItemDTO",
      "target_file": "api/models.py",
      "fields": [
        {"name": "item_id", "type": "int", "required": true},
        {"name": "name", "type": "str", "required": true}
      ]
    }
  ]
}
=== END BLUEPRINT JSON ===
"""
        bp, err, err_cls = parse_blueprint_json_classified(raw_plan)
        assert err is None
        assert bp is not None
        assert bp.authoritative_target_file == "api/server.py"
        assert len(bp.files) == 2
        assert "api/server.py" in bp.files
        assert "api/models.py" in bp.files
        assert "app = FastAPI()" in bp.files["api/server.py"].code_scaffold
        assert bp.interface_contracts[0].identifier == "get_item"
        assert bp.data_models[0].model_name == "ItemDTO"
        assert bp.data_models[0].fields[0].field_name == "item_id"

    # -------------------------------------------------------------------------
    # Test L: Generic Dart component fixture
    # -------------------------------------------------------------------------
    def test_l_generic_dart_component_fixture(self):
        """Test L: Real-world Flutter/Dart widget architecture blueprint normalizes deterministically."""
        raw_plan = """
=== BLUEPRINT JSON ===
{
  "authoritative_target_file": "lib/metric_card.dart",
  "file_tree": ["lib/metric_card.dart"],
  "architecture_summary": "Flutter Presentation Widget",
  "files": {
    "lib/metric_card.dart": {
      "file_path": "lib/metric_card.dart",
      "module_role": "UI Component",
      "imports": ["package:flutter/material.dart"],
      "code_scaffold": [
        "class MetricCard extends StatelessWidget {",
        "  final String title;",
        "  final double value;",
        "  const MetricCard({Key? key, required this.title, required this.value}) : super(key: key);",
        "  @override",
        "  Widget build(BuildContext context) {",
        "    return Text('$title: $value');",
        "  }",
        "}"
      ]
    }
  },
  "interface_contracts": [
    {
      "identifier": "MetricCard",
      "target_file": "lib/metric_card.dart"
    }
  ]
}
=== END BLUEPRINT JSON ===
"""
        bp, err, err_cls = parse_blueprint_json_classified(raw_plan)
        assert err is None
        assert bp is not None
        assert bp.authoritative_target_file == "lib/metric_card.dart"
        assert "class MetricCard extends StatelessWidget" in bp.files["lib/metric_card.dart"].code_scaffold
        assert bp.interface_contracts[0].identifier == "MetricCard"

    # -------------------------------------------------------------------------
    # Test M: Unrelated generic domain fixture (Rust / Go / Kotlin AST)
    # -------------------------------------------------------------------------
    def test_m_unrelated_generic_domain_fixture(self):
        """Test M: Schema works identically for non-Python/non-Dart languages (Rust / Go / Kotlin)."""
        # Rust CLI
        rust_plan = """
=== BLUEPRINT JSON ===
{
  "authoritative_target_file": "src/main.rs",
  "file_tree": ["src/main.rs", "src/lib.rs"],
  "architecture_summary": "Rust Systems CLI",
  "target_language": "rust",
  "files": {
    "src/main.rs": {
      "file_path": "src/main.rs",
      "module_role": "Entrypoint",
      "code_scaffold": "fn main() { println!(\\"Hello Rust\\"); }"
    },
    "src/lib.rs": {
      "file_path": "src/lib.rs",
      "module_role": "Core Engine",
      "code_scaffold": "pub fn process_data(val: i64) -> i64 { val * 2 }"
    }
  },
  "interface_contracts": [
    {
      "identifier": "process_data",
      "target_file": "src/lib.rs"
    }
  ]
}
=== END BLUEPRINT JSON ===
"""
        bp_rust, err_rust, _ = parse_blueprint_json_classified(rust_plan)
        assert err_rust is None
        assert bp_rust is not None
        assert bp_rust.authoritative_target_file == "src/main.rs"
        assert bp_rust.target_language == "rust"
        assert "process_data" in bp_rust.interface_contracts[0].identifier

        # Go Microservice
        go_plan = """
=== BLUEPRINT JSON ===
{
  "authoritative_target_file": "cmd/server/main.go",
  "file_tree": ["cmd/server/main.go"],
  "architecture_summary": "Go HTTP Microservice",
  "target_language": "go",
  "files": {
    "cmd/server/main.go": {
      "path": "cmd/server/main.go",
      "code": "package main\\n\\nfunc main() { }"
    }
  },
  "interfaces": [
    {
      "name": "Handler",
      "path": "/healthz",
      "http_method": "GET",
      "target": "cmd/server/main.go"
    }
  ]
}
=== END BLUEPRINT JSON ===
"""
        bp_go, err_go, _ = parse_blueprint_json_classified(go_plan)
        assert err_go is None
        assert bp_go is not None
        assert bp_go.authoritative_target_file == "cmd/server/main.go"
        assert bp_go.target_language == "go"
        assert bp_go.interface_contracts[0].identifier == "Handler"
        assert bp_go.interface_contracts[0].route == "/healthz"
