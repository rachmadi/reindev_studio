"""
Unit Tests for Part 2: Pre-Freeze Authority Compatibility Gate
ReinDev Studio — Architectural Hardening v1

Validates:
1. REST API: Detection of missing HTTP methods/endpoints demanded by Oracle
2. Python CLI/Module: Detection of missing callable symbols/classes
3. Dart/Flutter: Detection of missing widgets/data models
4. Full Compatibility: Passing when all obligations are covered
5. Integration with seal_and_freeze_contract: Rejection to status REJECTED on incompatibility
6. Non-Solver Guarantee: Error output specifies requirement/obligation, not solution code
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from backend.contract import (
    MachineReadableContract,
    InterfaceContract,
    DataModel,
    ContractStatus,
    check_pre_freeze_authority_compatibility,
    seal_and_freeze_contract,
    create_draft_contract,
    complete_aligned_contract,
)


@pytest.fixture
def temp_oracle_dir():
    temp_dir = tempfile.mkdtemp(prefix="reindev_oracle_test_")
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_rest_api_missing_http_method(temp_oracle_dir):
    """
    Oracle tests both GET /items and POST /items.
    Contract only specifies POST /items.
    Pre-freeze gate MUST reject with exact obligation report.
    """
    oracle_test_file = temp_oracle_dir / "test_api.py"
    oracle_test_file.write_text(
        "def test_items(client):\n"
        "    res = client.post('/items', json={'name': 'Book'})\n"
        "    assert res.status_code == 201\n"
        "    res2 = client.get('/items')\n"
        "    assert res2.status_code == 200\n",
        encoding="utf-8"
    )

    draft = create_draft_contract(raw_intent="Manage Items API", target_language="python", domain="REST_API")
    aligned = complete_aligned_contract(
        draft_dict=draft,
        data_models=[],
        interface_contracts=[{
            "interface_id": "IFC-01",
            "interface_type": "HTTP_ENDPOINT",
            "identifier": "/items",
            "target_file": "main.py",
            "http_method": "POST"
        }],
        testable_assertions=[{
            "assertion_id": "AST-01",
            "linked_req_id": "REQ-01",
            "test_scenario": "Create item",
            "target_symbol": "/items",
            "expected_outcome": {"outcome_type": "HTTP_STATUS", "expected_status": 201}
        }]
    )

    contract_obj = MachineReadableContract(**aligned)
    is_compat, errors, missing = check_pre_freeze_authority_compatibility(contract_obj, str(temp_oracle_dir))

    assert is_compat is False
    assert len(missing) == 1
    assert missing[0]["obligation"] == "HTTP GET /items"
    assert missing[0]["coverage"] == "MISSING"
    assert "INCOMPATIBLE — CONTRACT MUST NOT FREEZE" in missing[0]["result"]

    combined_err = "\n".join(errors)
    assert "ORACLE_OBLIGATION:" in combined_err
    assert "HTTP GET /items" in combined_err
    assert "CONTRACT_COVERAGE:" in combined_err
    assert "MISSING" in combined_err
    assert "INCOMPATIBLE — CONTRACT MUST NOT FREEZE" in combined_err


def test_rest_api_all_methods_covered(temp_oracle_dir):
    """
    Oracle tests GET /items and POST /items.
    Contract covers both. Gate MUST accept.
    """
    oracle_test_file = temp_oracle_dir / "test_api.py"
    oracle_test_file.write_text(
        "def test_items(client):\n"
        "    res = client.post('/items', json={'name': 'Book'})\n"
        "    res2 = client.get('/items')\n",
        encoding="utf-8"
    )

    draft = create_draft_contract(raw_intent="Manage Items API", target_language="python", domain="REST_API")
    aligned = complete_aligned_contract(
        draft_dict=draft,
        data_models=[],
        interface_contracts=[
            {
                "interface_id": "IFC-01",
                "interface_type": "HTTP_ENDPOINT",
                "identifier": "/items",
                "target_file": "main.py",
                "http_method": "POST"
            },
            {
                "interface_id": "IFC-02",
                "interface_type": "HTTP_ENDPOINT",
                "identifier": "/items",
                "target_file": "main.py",
                "http_method": "GET"
            }
        ],
        testable_assertions=[{
            "assertion_id": "AST-01",
            "linked_req_id": "REQ-01",
            "test_scenario": "Get items",
            "target_symbol": "/items",
            "expected_outcome": {"outcome_type": "HTTP_STATUS", "expected_status": 200}
        }]
    )

    contract_obj = MachineReadableContract(**aligned)
    is_compat, errors, missing = check_pre_freeze_authority_compatibility(contract_obj, str(temp_oracle_dir))
    assert is_compat is True
    assert len(errors) == 0
    assert len(missing) == 0


def test_python_cli_missing_callable_symbol(temp_oracle_dir):
    """
    Oracle imports parse_arguments and execute_command from main.
    Contract only covers parse_arguments.
    Gate MUST reject.
    """
    oracle_test_file = temp_oracle_dir / "test_cli.py"
    oracle_test_file.write_text(
        "from main import parse_arguments, execute_command\n\n"
        "def test_cli():\n"
        "    args = parse_arguments(['--help'])\n"
        "    res = execute_command(args)\n"
        "    assert res == 0\n",
        encoding="utf-8"
    )

    draft = create_draft_contract(raw_intent="CLI tool", target_language="python", domain="CLI_TOOL")
    aligned = complete_aligned_contract(
        draft_dict=draft,
        data_models=[],
        interface_contracts=[{
            "interface_id": "IFC-01",
            "interface_type": "FUNCTION",
            "identifier": "parse_arguments",
            "target_file": "main.py"
        }],
        testable_assertions=[{
            "assertion_id": "AST-01",
            "linked_req_id": "REQ-01",
            "test_scenario": "Test parse arguments",
            "target_symbol": "parse_arguments",
            "expected_outcome": {"outcome_type": "VALUE_EQUALS"}
        }]
    )

    contract_obj = MachineReadableContract(**aligned)
    is_compat, errors, missing = check_pre_freeze_authority_compatibility(contract_obj, str(temp_oracle_dir))
    assert is_compat is False
    assert any("execute_command" in m["obligation"] for m in missing)
    assert any("execute_command" in err for err in errors)


def test_dart_widget_missing_type(temp_oracle_dir):
    """
    Oracle widget test finds MetricCard and StatusBadge.
    Contract only defines MetricCard.
    Gate MUST reject.
    """
    oracle_test_file = temp_oracle_dir / "widget_test.dart"
    oracle_test_file.write_text(
        "import 'package:flutter_test/flutter_test.dart';\n\n"
        "void main() {\n"
        "  testWidgets('Renders dashboard', (tester) async {\n"
        "    expect(find.byType(MetricCard), findsOneWidget);\n"
        "    expect(find.byType(StatusBadge), findsOneWidget);\n"
        "  });\n"
        "}\n",
        encoding="utf-8"
    )

    draft = create_draft_contract(raw_intent="Dashboard Widget", target_language="dart", domain="FLUTTER_WIDGET")
    aligned = complete_aligned_contract(
        draft_dict=draft,
        data_models=[],
        interface_contracts=[{
            "interface_id": "IFC-01",
            "interface_type": "WIDGET",
            "identifier": "MetricCard",
            "target_file": "lib/main.dart"
        }],
        testable_assertions=[{
            "assertion_id": "AST-01",
            "linked_req_id": "REQ-01",
            "test_scenario": "Render MetricCard",
            "target_symbol": "MetricCard",
            "expected_outcome": {"outcome_type": "WIDGET_FOUND"}
        }]
    )

    contract_obj = MachineReadableContract(**aligned)
    is_compat, errors, missing = check_pre_freeze_authority_compatibility(contract_obj, str(temp_oracle_dir))
    assert is_compat is False
    assert any("StatusBadge" in m["obligation"] for m in missing)


def test_seal_and_freeze_fails_on_incompatible_contract(temp_oracle_dir):
    """
    seal_and_freeze_contract MUST transition contract to REJECTED if pre-freeze
    compatibility check detects missing oracle obligations.
    """
    oracle_test_file = temp_oracle_dir / "test_api.py"
    oracle_test_file.write_text(
        "def test_calc(client):\n"
        "    r = client.get('/calculate')\n",
        encoding="utf-8"
    )

    draft = create_draft_contract(raw_intent="Calculator API", target_language="python", domain="REST_API")
    aligned = complete_aligned_contract(
        draft_dict=draft,
        data_models=[],
        interface_contracts=[{
            "interface_id": "IFC-01",
            "interface_type": "HTTP_ENDPOINT",
            "identifier": "/other",
            "target_file": "main.py",
            "http_method": "GET"
        }],
        testable_assertions=[{
            "assertion_id": "AST-01",
            "linked_req_id": "REQ-01",
            "test_scenario": "Test other endpoint",
            "target_symbol": "/other",
            "expected_outcome": {"outcome_type": "HTTP_STATUS", "expected_status": 200}
        }]
    )

    success, sealed, errors, warnings = seal_and_freeze_contract(
        aligned,
        frozen_oracle_path=str(temp_oracle_dir)
    )

    assert success is False
    assert sealed.get("status") == ContractStatus.REJECTED.value
    assert any("PRE_FREEZE_AUTHORITY_INCOMPATIBLE" in e for e in errors)
    assert any("HTTP GET /calculate" in e for e in errors)


def test_non_solver_guarantee(temp_oracle_dir):
    """
    Verify that error messages generated by pre-freeze compatibility gate do NOT
    contain task-specific solver code (e.g. no code snippets implementing the fix).
    """
    oracle_test_file = temp_oracle_dir / "test_api.py"
    oracle_test_file.write_text(
        "def test_data(client):\n"
        "    r = client.get('/users')\n",
        encoding="utf-8"
    )

    draft = create_draft_contract(raw_intent="Users API", target_language="python", domain="REST_API")
    aligned = complete_aligned_contract(
        draft_dict=draft,
        data_models=[],
        interface_contracts=[],
        testable_assertions=[]
    )

    contract_obj = MachineReadableContract(**aligned)
    is_compat, errors, missing = check_pre_freeze_authority_compatibility(contract_obj, str(temp_oracle_dir))
    assert is_compat is False
    for err in errors:
        assert "def " not in err
        assert "return " not in err
        assert "@app." not in err
        assert "class " not in err