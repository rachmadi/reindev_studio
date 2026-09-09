"""
Unit Test Suite for P0-2.1: Mandatory Interface Contract Enforcement
ReinDev Studio — Deterministic Contract Validation Gate & Revision Failsafe

Mencakup seluruh kriteria penerimaan P0-2.1:
1. interface_contracts: [] pada task non-UI tidak dapat mencapai FROZEN (REJECTED).
2. Feedback terstruktur mengandung pesan dan field wajib yang ditentukan.
3. Task UI (Flutter) diakomodasi dengan benar.
4. Task non-UI dengan interface eksplisit mencapai FROZEN.
5. Verifikasi konsistensi interface contract terhadap Frozen Oracle mendeteksi mismatch.
6. Verifikasi konsistensi interface contract terhadap Frozen Oracle lolos saat selaras.
7. Routing: Kontrak REJECTED dengan revision_count < 2 rute kembali ke architect.
8. Routing Failsafe KUNCI: Kontrak REJECTED dengan revision_count >= 2 rute langsung ke END (FAIL/STOP), Developer TIDAK PERNAH DIJALANKAN.
9. Node contract_validation_node mencatat contract_feedback dan menaikkan revision_count.
10. Architect agent mengonsumsi contract_feedback dan menyertakannya dalam prompt revisi.
11. Fallback Architect independen dari Frozen Oracle (tidak membaca oracle / tidak membocorkan solusi).
12. Audit integritas: SHA-256 seluruh Frozen Oracle tetap identik 100%.
"""

import copy
import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from langgraph.graph import END

from backend.contract import (
    create_draft_contract,
    complete_aligned_contract,
    validate_contract_gate,
    seal_and_freeze_contract,
    is_non_ui_computational_task,
    check_oracle_interface_consistency,
    ContractStatus
)
from backend.graph import (
    contract_validation_node,
    route_after_contract_gate
)
from backend.agents.architect import (
    _build_default_aligned_contract,
    architect_agent
)
from backend.state import SquadState


# ===========================================================================
# Fixture Helpers
# ===========================================================================

def build_sample_non_ui_contract(empty_interfaces: bool = False) -> dict:
    """Helper untuk membangun kontrak non-UI (CLI / Algorithm)."""
    draft = create_draft_contract(
        raw_intent="Kalkulator matriks CLI Python",
        target_language="python",
        domain="CLI_TOOL",
        goal_summary="Operasi penjumlahan dan perkalian matriks 2x2",
        contract_id="contract_test_cli_001",
        reqs=[
            {
                "req_id": "REQ-01",
                "description": "Menghitung operasi matriks",
                "acceptance_semantics": ["Menghasilkan hasil matriks yang benar"]
            }
        ]
    )
    if empty_interfaces:
        interfaces = []
        assertions = []
    else:
        interfaces = [
            {
                "interface_id": "IFC-01",
                "interface_type": "FUNCTION",
                "identifier": "add_matrices",
                "http_method": None,
                "target_file": "main.py",
                "parameters": [
                    {"param_name": "a", "param_type": "list", "param_location": "ARGUMENT", "is_required": True},
                    {"param_name": "b", "param_type": "list", "param_location": "ARGUMENT", "is_required": True}
                ],
                "expected_return": {
                    "return_type": "list",
                    "status_code_success": None,
                    "status_code_errors": []
                }
            }
        ]
        assertions = [
            {
                "assertion_id": "AST-01",
                "linked_req_id": "REQ-01",
                "linked_interface_id": "IFC-01",
                "test_scenario": "Addition of matrices returns correct sum",
                "target_symbol": "add_matrices",
                "input_fixture": "add_matrices([[1, 2]], [[3, 4]])",
                "expected_outcome": {
                    "outcome_type": "VALUE_EQUALS",
                    "expected_value": "[[4, 6]]"
                }
            }
        ]

    return complete_aligned_contract(
        draft_dict=draft,
        data_models=[],
        interface_contracts=interfaces,
        testable_assertions=assertions
    )


# ===========================================================================
# Test Cases
# ===========================================================================

def test_p0_2_1_mandatory_interface_non_ui_empty_rejected():
    """1. Task non-UI dengan interface_contracts kosong WAJIB ditolak dan tidak boleh masuk FROZEN."""
    contract = build_sample_non_ui_contract(empty_interfaces=True)
    
    is_valid, errors, _ = validate_contract_gate(contract)
    assert not is_valid
    assert any("CONTRACT_VALIDATION_FAILED" in err for err in errors)
    assert any("interface_contracts is empty for a non-UI computational task" in err for err in errors)

    success, result_contract, errors, _ = seal_and_freeze_contract(contract)
    assert not success
    assert result_contract.get("status") == ContractStatus.REJECTED.value
    assert result_contract.get("provenance", {}).get("contract_sha256") is None


def test_p0_2_1_structured_feedback_format():
    """2. Validasi harus mengembalikan feedback terstruktur dengan pesan dan field wajib."""
    contract = build_sample_non_ui_contract(empty_interfaces=True)
    is_valid, errors, _ = validate_contract_gate(contract)
    assert not is_valid
    
    feedback_text = "\n\n".join(errors)
    assert "CONTRACT_VALIDATION_FAILED" in feedback_text
    assert "reason:" in feedback_text
    assert "required_action:" in feedback_text
    assert "required_fields:" in feedback_text
    assert "- module/function/class name" in feedback_text
    assert "- callable signature" in feedback_text
    assert "- expected input" in feedback_text
    assert "- expected output" in feedback_text
    assert "- public invocation mechanism" in feedback_text


def test_p0_2_1_is_non_ui_computational_task_detection():
    """3. Fungsi deteksi task membedakan non-UI vs UI secara tepat."""
    # REST API -> non-UI
    c_api = {"task_intent": {"domain": "REST_API"}, "target_ecosystem": {"language": "python"}}
    assert is_non_ui_computational_task(c_api) is True

    # CLI Tool -> non-UI
    c_cli = {"task_intent": {"domain": "CLI_TOOL"}, "target_ecosystem": {"language": "python"}}
    assert is_non_ui_computational_task(c_cli) is True

    # Flutter Widget -> UI
    c_flutter = {"task_intent": {"domain": "FLUTTER_WIDGET"}, "target_ecosystem": {"framework": "flutter", "language": "dart"}}
    assert is_non_ui_computational_task(c_flutter) is False


def test_p0_2_1_non_ui_with_explicit_interfaces_reaches_frozen():
    """4. Task non-UI dengan interface yang terdefinisi eksplisit berhasil divalidasi dan mencapai FROZEN."""
    contract = build_sample_non_ui_contract(empty_interfaces=False)
    success, result_contract, errors, _ = seal_and_freeze_contract(contract)
    
    assert success
    assert errors == []
    assert result_contract.get("status") == ContractStatus.FROZEN.value
    assert result_contract.get("provenance", {}).get("contract_sha256") is not None
    assert len(result_contract["provenance"]["contract_sha256"]) == 64


def test_p0_2_1_oracle_consistency_check_detects_mismatch(tmp_path):
    """5. Mismatch antarmuka terhadap Frozen Oracle ditolak dengan CONTRACT_VALIDATION_FAILED."""
    # Buat file oracle tiruan yang menguji endpoint /orders
    oracle_dir = tmp_path / "oracle_test"
    oracle_dir.mkdir()
    test_file = oracle_dir / "test_main.py"
    test_file.write_text(
        "import pytest\ndef test_orders():\n    res = client.get('/orders')\n    assert res.status_code == 200\n",
        encoding="utf-8"
    )

    draft = create_draft_contract(raw_intent="API", target_language="python", domain="REST_API")
    contract = complete_aligned_contract(
        draft_dict=draft,
        data_models=[],
        interface_contracts=[
            {
                "interface_id": "IFC-01",
                "interface_type": "HTTP_ENDPOINT",
                "identifier": "/products",
                "http_method": "GET",
                "target_file": "main.py",
                "parameters": [],
                "expected_return": {"return_type": "list", "status_code_success": 200, "status_code_errors": []}
            }
        ],
        testable_assertions=[
            {
                "assertion_id": "AST-01",
                "linked_req_id": "REQ-01",
                "linked_interface_id": "IFC-01",
                "test_scenario": "Get products",
                "target_symbol": "/products",
                "input_fixture": "client.get('/products')",
                "expected_outcome": {"outcome_type": "HTTP_STATUS", "expected_status": 200}
            }
        ]
    )

    success, result_contract, errors, _ = seal_and_freeze_contract(
        contract,
        frozen_oracle_path=str(oracle_dir)
    )
    assert not success
    assert result_contract.get("status") == ContractStatus.REJECTED.value
    feedback = "\n\n".join(errors)
    assert "CONTRACT_VALIDATION_FAILED" in feedback
    assert "Architect interface contract is inconsistent with the frozen test interface." in feedback


def test_p0_2_1_oracle_consistency_check_passes_when_aligned(tmp_path):
    """6. Antarmuka yang selaras dengan Frozen Oracle lolos validasi konsistensi."""
    oracle_dir = tmp_path / "oracle_test_aligned"
    oracle_dir.mkdir()
    test_file = oracle_dir / "test_main.py"
    test_file.write_text(
        "import pytest\ndef test_products():\n    res = client.get('/products')\n    assert res.status_code == 200\n",
        encoding="utf-8"
    )

    draft = create_draft_contract(raw_intent="API", target_language="python", domain="REST_API")
    contract = complete_aligned_contract(
        draft_dict=draft,
        data_models=[],
        interface_contracts=[
            {
                "interface_id": "IFC-01",
                "interface_type": "HTTP_ENDPOINT",
                "identifier": "/products",
                "http_method": "GET",
                "target_file": "main.py",
                "parameters": [],
                "expected_return": {"return_type": "list", "status_code_success": 200, "status_code_errors": []}
            }
        ],
        testable_assertions=[
            {
                "assertion_id": "AST-01",
                "linked_req_id": "REQ-01",
                "linked_interface_id": "IFC-01",
                "test_scenario": "Get products",
                "target_symbol": "/products",
                "input_fixture": "client.get('/products')",
                "expected_outcome": {"outcome_type": "HTTP_STATUS", "expected_status": 200}
            }
        ]
    )

    success, result_contract, errors, _ = seal_and_freeze_contract(
        contract,
        frozen_oracle_path=str(oracle_dir)
    )
    assert success
    assert result_contract.get("status") == ContractStatus.FROZEN.value


def test_p0_2_1_routing_rejected_under_limit_routes_to_architect():
    """7. Kontrak REJECTED pada revision_count < 2 dirutekan kembali ke architect untuk revisi."""
    state_rev0: SquadState = {
        "contract_status": ContractStatus.REJECTED.value,
        "contract_revision_count": 0
    }  # type: ignore
    assert route_after_contract_gate(state_rev0) == "architect"

    state_rev1: SquadState = {
        "contract_status": ContractStatus.REJECTED.value,
        "contract_revision_count": 1
    }  # type: ignore
    assert route_after_contract_gate(state_rev1) == "architect"


def test_p0_2_1_routing_rejected_limit_reached_stops_at_end_and_never_developer():
    """
    8. KRITERIA PENERIMAAN KUNCI:
    Kontrak REJECTED pada revision_count >= 2 WAJIB STOP di END (FAIL).
    Developer TIDAK PERNAH DIJALANKAN.
    """
    state_rev2: SquadState = {
        "contract_status": ContractStatus.REJECTED.value,
        "contract_revision_count": 2
    }  # type: ignore
    decision = route_after_contract_gate(state_rev2)
    assert decision == END
    assert decision != "developer"

    state_rev3: SquadState = {
        "contract_status": ContractStatus.REJECTED.value,
        "contract_revision_count": 3
    }  # type: ignore
    assert route_after_contract_gate(state_rev3) == END


def test_p0_2_1_routing_frozen_routes_to_developer():
    """9. Kontrak FROZEN dirutekan ke developer."""
    state_frozen: SquadState = {
        "contract_status": ContractStatus.FROZEN.value,
        "contract_revision_count": 0
    }  # type: ignore
    assert route_after_contract_gate(state_frozen) == "developer"


def test_p0_2_1_contract_validation_node_state_update():
    """10. contract_validation_node mencatat feedback terstruktur dan menandai kegagalan saat batas tercapai."""
    invalid_contract = build_sample_non_ui_contract(empty_interfaces=True)

    # Putaran revisi 1
    state_in: SquadState = {
        "contract": invalid_contract,
        "contract_revision_count": 0,
        "logs": []
    }  # type: ignore

    out1 = contract_validation_node(state_in)
    assert out1["contract_status"] == ContractStatus.REJECTED.value
    assert out1["contract_revision_count"] == 1
    assert "CONTRACT_VALIDATION_FAILED" in out1["contract_feedback"]
    assert out1.get("status") is None  # Belum abort

    # Putaran revisi 2 (mencapai batas)
    state_in2: SquadState = {
        "contract": invalid_contract,
        "contract_revision_count": 1,
        "logs": []
    }  # type: ignore

    out2 = contract_validation_node(state_in2)
    assert out2["contract_status"] == ContractStatus.REJECTED.value
    assert out2["contract_revision_count"] == 2
    assert out2.get("status") == "contract_validation_failed"  # Abort flag diset


def test_p0_2_1_architect_prompt_consumes_feedback():
    """11. Architect agent mengonsumsi contract_feedback dan menyertakannya dalam prompt jika kontrak ditolak."""
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content="Mock architecture plan with def calculate(x): pass")

    state_with_feedback: SquadState = {
        "task": "Kalkulator matriks CLI Python",
        "specifications": "Spesifikasi PM",
        "target_language": "python",
        "contract_feedback": "CONTRACT_VALIDATION_FAILED: interface_contracts is empty.",
        "contract_revision_count": 1,
        "provider": "ollama",
        "logs": []
    }  # type: ignore

    with patch("backend.agents.architect.get_llm", return_value=mock_llm):
        res = architect_agent(state_with_feedback)

    call_args = mock_llm.invoke.call_args[0][0]
    human_msg = call_args[1].content
    assert "[PERHATIAN: KONTRAK SEBELUMNYA DITOLAK OLEH GERBANG VALIDASI - REVISI DIPERLUKAN]" in human_msg
    assert "CONTRACT_VALIDATION_FAILED" in human_msg


def test_p0_2_1_fallback_does_not_leak_or_read_frozen_oracle():
    """
    12. KRITERIA PENERIMAAN KUNCI:
    Fallback Architect TIDAK membaca atau meng-hardcode operator matriks khusus Frozen Oracle.
    """
    draft = create_draft_contract(raw_intent="CLI math", target_language="python", domain="CLI_TOOL")
    result = _build_default_aligned_contract(draft, "CLI math tool", "python", arch_plan="")

    identifiers = [iface["identifier"] for iface in result["interface_contracts"]]
    assert "__add__" not in identifiers
    assert "__sub__" not in identifiers
    assert "__mul__" not in identifiers
    assert "add_matrices" not in identifiers


def test_p0_2_1_frozen_oracles_hash_immutability():
    """
    13. KRITERIA PENERIMAAN KUNCI:
    SHA-256 seluruh Frozen Oracle wajib 100% identik dengan baseline.
    """
    expected_hashes = {
        "dokumentasi-pengembangan/experiments/frozen_oracle/fastapi_t1/test_main.py": "a1db9bb1f6eaf47d5cf56e102c4a0f6e1f49d757e9faa1485b36f2972a152d63",
        "dokumentasi-pengembangan/experiments/frozen_oracle/cli_t1/test_main.py": "0bd5b598afa7ae4c9cdf0e269d13136b51d35a4e0b1ac6548f0a2cf8a8eba124",
        "dokumentasi-pengembangan/experiments/frozen_oracle/flutter_t1/card_metric_test.dart": "4589e15cfb8f37ba70642e70623ca143bceee1a44175aefd072f441d9e8a9528",
    }

    for path_str, expected_hash in expected_hashes.items():
        p = Path(path_str)
        assert p.exists(), f"Oracle file missing: {path_str}"
        content = p.read_bytes()
        actual_hash = hashlib.sha256(content).hexdigest().lower()
        assert actual_hash == expected_hash.lower()
