"""
Unit Test Suite: Contract–Oracle Consistency Gate (V2 / B2 Pre-Freeze)
ReinDev Studio — Church of Goat Epistemic Doctrine (D-098, D-099, D-100)

Memverifikasi bahwa tidak ada kontrak yang dapat dibekukan (FROZEN) sebelum
konsistensinya terhadap Acceptance Authority (Frozen Oracle) terbukti secara deterministik,
serta menguji perenderan preskripsi non-solver murni level requirement.
"""

import pytest
from pathlib import Path

from backend.contract import (
    create_draft_contract,
    complete_aligned_contract,
    seal_and_freeze_contract,
    check_oracle_interface_consistency,
    ContractStatus,
    InterfaceContract,
)
from backend.phase_validators import validate_architect_phase
from backend.context_assembler import synthesize_b5_actionable_prescriptions


def test_dart_flutter_inconsistent_contract_rejected_before_freeze(tmp_path):
    """
    1. Kontrak Dart/Flutter dengan nama widget spekulatif (CardMetricWidget)
    WAJIB ditolak (REJECTED) dan TIDAK BOLEH disegel FROZEN jika Oracle menuntut CardMetric.
    """
    oracle_dir = tmp_path / "oracle_flutter"
    oracle_dir.mkdir()
    test_file = oracle_dir / "card_metric_test.dart"
    test_file.write_text(
        "import 'package:flutter_test/flutter_test.dart';\n"
        "void main() {\n"
        "  testWidgets('renders CardMetric', (tester) async {\n"
        "    await tester.pumpWidget(MaterialApp(home: Scaffold(body: CardMetric())));\n"
        "    expect(find.byType(CardMetric), findsOneWidget);\n"
        "  });\n"
        "}\n",
        encoding="utf-8"
    )

    draft = create_draft_contract(raw_intent="Card Metric Widget", target_language="dart", domain="FLUTTER_WIDGET")
    inconsistent_contract = complete_aligned_contract(
        draft_dict=draft,
        data_models=[],
        interface_contracts=[{
            "interface_id": "IFC-01",
            "interface_type": "WIDGET",
            "identifier": "CardMetricWidget",
            "target_file": "lib/card_metric.dart",
            "parameters": [],
            "expected_return": {"return_type": "Widget"}
        }],
        testable_assertions=[{
            "assertion_id": "AST-01",
            "linked_req_id": "REQ-01",
            "linked_interface_id": "IFC-01",
            "test_scenario": "Render CardMetricWidget",
            "target_symbol": "CardMetricWidget",
            "input_fixture": "CardMetricWidget()",
            "expected_outcome": {"outcome_type": "WIDGET_FOUND"}
        }]
    )

    success, result_contract, errors, _ = seal_and_freeze_contract(
        inconsistent_contract,
        frozen_oracle_path=str(oracle_dir),
        task_text="Build card metric widget"
    )

    assert not success
    assert result_contract.get("status") == ContractStatus.REJECTED.value
    assert not result_contract.get("provenance", {}).get("contract_sha256")

    err_text = "\n\n".join(errors)
    assert "CONTRACT_VALIDATION_FAILED" in err_text
    assert "CardMetricWidget" in err_text
    assert "CardMetric" in err_text
    assert "inconsistent with the frozen test interface" in err_text.lower() or "tidak konsisten dengan authoritative acceptance call-site" in err_text


def test_dart_flutter_aligned_contract_sealed_frozen(tmp_path):
    """
    2. Kontrak Dart/Flutter yang selaras dengan Acceptance Oracle (CardMetric)
    berhasil divalidasi dan disegel menjadi FROZEN dengan hash SHA-256 RFC 8785.
    """
    oracle_dir = tmp_path / "oracle_flutter_aligned"
    oracle_dir.mkdir()
    test_file = oracle_dir / "card_metric_test.dart"
    test_file.write_text(
        "import 'package:flutter_test/flutter_test.dart';\n"
        "void main() {\n"
        "  testWidgets('renders CardMetric', (tester) async {\n"
        "    await tester.pumpWidget(MaterialApp(home: Scaffold(body: CardMetric())));\n"
        "    expect(find.byType(CardMetric), findsOneWidget);\n"
        "  });\n"
        "}\n",
        encoding="utf-8"
    )

    draft = create_draft_contract(raw_intent="Card Metric Widget", target_language="dart", domain="FLUTTER_WIDGET")
    aligned_contract = complete_aligned_contract(
        draft_dict=draft,
        data_models=[],
        interface_contracts=[{
            "interface_id": "IFC-01",
            "interface_type": "WIDGET",
            "identifier": "CardMetric",
            "target_file": "lib/card_metric.dart",
            "parameters": [],
            "expected_return": {"return_type": "Widget"}
        }],
        testable_assertions=[{
            "assertion_id": "AST-01",
            "linked_req_id": "REQ-01",
            "linked_interface_id": "IFC-01",
            "test_scenario": "Render CardMetric",
            "target_symbol": "CardMetric",
            "input_fixture": "CardMetric()",
            "expected_outcome": {"outcome_type": "WIDGET_FOUND"}
        }]
    )

    success, result_contract, errors, _ = seal_and_freeze_contract(
        aligned_contract,
        frozen_oracle_path=str(oracle_dir),
        task_text="Build card metric widget"
    )

    assert success
    assert result_contract.get("status") == ContractStatus.FROZEN.value
    sha = result_contract.get("provenance", {}).get("contract_sha256")
    assert sha and len(sha) == 64
    assert len(errors) == 0


def test_python_fastapi_oracle_consistency_preserved(tmp_path):
    """
    3. Konsistensi Oracle untuk Python REST API (FastAPI) tetap berfungsi normal.
    """
    oracle_dir = tmp_path / "oracle_api"
    oracle_dir.mkdir()
    test_file = oracle_dir / "test_main.py"
    test_file.write_text(
        "import pytest\ndef test_products():\n    res = client.get('/products')\n    assert res.status_code == 200\n",
        encoding="utf-8"
    )

    draft = create_draft_contract(raw_intent="API", target_language="python", domain="REST_API")
    bad_contract = complete_aligned_contract(
        draft_dict=draft,
        data_models=[],
        interface_contracts=[{
            "interface_id": "IFC-01",
            "interface_type": "HTTP_ENDPOINT",
            "identifier": "/items",
            "http_method": "GET",
            "target_file": "main.py",
            "parameters": [],
            "expected_return": {"return_type": "list", "status_code_success": 200, "status_code_errors": []}
        }],
        testable_assertions=[{
            "assertion_id": "AST-01",
            "linked_req_id": "REQ-01",
            "linked_interface_id": "IFC-01",
            "test_scenario": "Get items",
            "target_symbol": "/items",
            "input_fixture": "client.get('/items')",
            "expected_outcome": {"outcome_type": "HTTP_STATUS", "expected_status": 200}
        }]
    )

    success, res, errs, _ = seal_and_freeze_contract(bad_contract, frozen_oracle_path=str(oracle_dir))
    assert not success
    assert res.get("status") == ContractStatus.REJECTED.value


def test_python_cli_oracle_consistency_preserved(tmp_path):
    """
    4. Konsistensi Oracle untuk Python CLI / Module tetap berfungsi normal.
    """
    oracle_dir = tmp_path / "oracle_cli"
    oracle_dir.mkdir()
    test_file = oracle_dir / "test_main.py"
    test_file.write_text(
        "import pytest, main\ndef test_matrix():\n    assert hasattr(main, 'Matrix')\n",
        encoding="utf-8"
    )

    draft = create_draft_contract(raw_intent="Matrix", target_language="python", domain="CLI_TOOL")
    bad_contract = complete_aligned_contract(
        draft_dict=draft,
        data_models=[],
        interface_contracts=[{
            "interface_id": "IFC-01",
            "interface_type": "FUNCTION",
            "identifier": "MatrixCalc",
            "target_file": "main.py",
            "parameters": [],
            "expected_return": {"return_type": "None"}
        }],
        testable_assertions=[{
            "assertion_id": "AST-01",
            "linked_req_id": "REQ-01",
            "linked_interface_id": "IFC-01",
            "test_scenario": "Matrix check",
            "target_symbol": "MatrixCalc",
            "input_fixture": "MatrixCalc()",
            "expected_outcome": {"outcome_type": "VALUE_EQUALS", "value": 0}
        }]
    )

    success, res, errs, _ = seal_and_freeze_contract(bad_contract, frozen_oracle_path=str(oracle_dir))
    assert not success
    assert res.get("status") == ContractStatus.REJECTED.value


def test_gate_v2_architect_phase_validator_reports_oracle_inconsistency():
    """
    5. Gate V2 validate_architect_phase melaporkan kriteria 'contract_oracle_consistency'
    dan menetapkan aksi perbaikan ALIGN_CONTRACT_WITH_ORACLE jika terjadi disparitas kontrak vs Oracle.
    """
    state = {
        "architecture_plan": '=== BLUEPRINT JSON ===\n{"authoritative_target_file": "lib/card_metric.dart", "file_tree": ["lib/card_metric.dart"], "architecture_summary": "Card metric widget", "files": {"lib/card_metric.dart": {"module_role": "Widget", "imports": ["package:flutter/material.dart"], "code_scaffold": "class CardMetricWidget {}"}}, "interface_contracts": [{"identifier": "CardMetricWidget", "route": "", "method": "", "interface_type": "WIDGET", "description": "Widget", "parameters": [], "expected_return": "Widget"}], "data_models": []}',
        "target_language": "dart",
        "contract": {"interface_contracts": [{"identifier": "CardMetricWidget"}]},
        "contract_status": ContractStatus.REJECTED.value,
        "contract_sha256": None,
        "contract_validation_errors": [
            "Pilar 4 (Oracle Consistency): CONTRACT_VALIDATION_FAILED\n\nreason:\nArchitect interface contract is inconsistent with the frozen test interface.\n\ndetails:\nContract interface ['CardMetricWidget'] tidak konsisten dengan authoritative acceptance call-site ['CardMetric'] pada berkas pengujian 'card_metric_test.dart'."
        ],
    }

    result = validate_architect_phase(state)

    assert result["verdict"] == "FAIL"
    assert "contract_oracle_consistency" in result["criteria_checked"]

    # Evidence
    ev_items = {e["item"]: e for e in result["evidence"]}
    assert "contract_oracle_interface_consistency" in ev_items
    assert ev_items["contract_oracle_interface_consistency"]["status"] == "INVALID"

    # Violations
    vio_criteria = [v["criterion"] for v in result["violations"]]
    assert "contract_oracle_consistency" in vio_criteria

    # Required Repairs
    repair_actions = [r["action"] for r in result["required_repairs"]]
    assert "ALIGN_CONTRACT_WITH_ORACLE" in repair_actions
    assert result["repair_owner"] == "ARCHITECT"


def test_b5_dart_prescription_pure_non_solver_requirement_level():
    """
    6. Preskripsi B5 Dart Pattern 1 mematuhi prinsip Pure Non-Solver (D-100):
    Menyatakan requirement kontrak murni ('The implementation must satisfy...'),
    bukan instruksi imperatif solusi ('Define or export class/method').
    """
    state = {
        "code_files": {"lib/card_metric.dart": "class CardMetricWidget {}"},
        "test_files": {
            "test/card_metric_test.dart": "void main() { testWidgets('test', (t) async { body: CardMetric(); }); }"
        },
        "target_language": "dart",
    }
    output = "test/card_metric_test.dart:13:19: Error: Method not found: 'CardMetric'."

    prescriptions = synthesize_b5_actionable_prescriptions(
        state=state,
        violations=[],
        output=output,
        target_lang="dart",
        auth_file="lib/card_metric.dart",
    )

    assert len(prescriptions) >= 1
    rx = prescriptions[0]
    assert "CardMetric" in rx.required_change
    assert "The implementation must satisfy" in rx.required_change
    assert "while preserving all valid frozen external requirements" in rx.required_change

    # Pastikan tidak ada instruksi solusi imperatif 'Define or export class/method'
    assert "Define or export class/method" not in rx.required_change
    assert "Define or export class or method" not in rx.repair_boundary_allowed[0]
