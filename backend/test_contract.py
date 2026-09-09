"""
Comprehensive Test Suite for P0-2: Machine-Readable Contract
ReinDev Studio — Cross-Agent Semantic Contract & Deterministic Validation Gate

Mencakup 24 skenario pengujian komprehensif:
1. Schema & Pydantic validation (Pilar 1)
2. RFC 8785 Canonical JSON determinism
3. Anti-circular canonical hashing (exclusion of provenance.contract_sha256)
4. Validation gate: Pilar 1 (Schema validity)
5. Validation gate: Pilar 2 (Duplicate req_id)
6. Validation gate: Pilar 2 (Duplicate assertion_id)
7. Validation gate: Pilar 2 (Dangling linked_req_id)
8. Validation gate: Pilar 2 (Dangling linked_interface_id)
9. Validation gate: Pilar 2 (Unregistered target_symbol)
10. Validation gate: Pilar 3 (Untested functional requirement / 100% coverage)
11. Validation gate: Pilar 3 (Untestable assertion outcome_type)
12. Validation gate: Pilar 4 (Internal consistency: return_type)
13. Validation gate: Pilar 4 (Internal consistency: status_code mismatch)
14. Validation gate: Pilar 4 (REST convention advisory warning non-blocking)
15. Lifecycle: seal_and_freeze_contract success (ALIGNED -> FROZEN)
16. Lifecycle: seal_and_freeze_contract rejection (invalid -> REJECTED)
17. Checkpoint verification: valid FROZEN contract
18. Checkpoint verification: tamper detection & instant abort
19. Immutability enforcement: modify FROZEN contract without version bump
20. Diagnostic parser integration: deterministic contract mapping
21. Diagnostic parser integration: ambiguous fallback (zero hallucination)
22. Reviewer Dual-Layer: Layer 1 deterministic blocking on test failure or missing AST
23. Reviewer Dual-Layer: Layer 2 bounded review on 100% Layer 1 pass
24. Frozen Oracle bypass preservation
"""

import copy
import pytest
from unittest.mock import MagicMock, patch
from typing import Dict, Any

from backend.contract import (
    MachineReadableContract,
    TaskIntent,
    TargetEcosystem,
    DataModel,
    InterfaceContract,
    FunctionalRequirement,
    TestableAssertion,
    ExpectedOutcome,
    ContractConstraints,
    UnresolvedAmbiguity,
    ContractStatus,
    DomainType,
    TargetLanguage,
    TestFramework,
    canonicalize_json,
    compute_contract_canonical_hash,
    verify_contract_integrity,
    validate_contract_gate,
    seal_and_freeze_contract,
    verify_contract_checkpoint,
    enforce_contract_immutability,
    create_draft_contract,
    complete_aligned_contract,
    extract_contract_json_from_text,
    ContractIntegrityError,
    ContractImmutabilityError
)
from backend.diagnostic_parser import (
    map_evidence_to_contract,
    build_targeted_feedback,
    FailingTest
)
from backend.agents.reviewer import (
    evaluate_deterministic_evidence_gate,
    reviewer_agent
)
from backend.graph import contract_validation_node, frozen_oracle_node
from backend.state import SquadState


# ===========================================================================
# Fixture Helpers
# ===========================================================================

def get_valid_contract_dict() -> Dict[str, Any]:
    """Helper untuk menghasilkan dictionary kontrak valid 100%."""
    draft = create_draft_contract(
        raw_intent="Bangun REST API inventaris produk",
        target_language="python",
        domain="REST_API",
        goal_summary="REST API produk dengan FastAPI",
        contract_id="contract_test_001",
        reqs=[
            {
                "req_id": "REQ-01",
                "description": "Membaca daftar produk inventaris",
                "acceptance_semantics": ["GET /products mengembalikan status 200 dan list produk"]
            },
            {
                "req_id": "REQ-02",
                "description": "Menambahkan produk baru ke inventaris",
                "acceptance_semantics": ["POST /products mengembalikan status 201"]
            }
        ]
    )
    models = [
        {
            "model_name": "Product",
            "target_file": "main.py",
            "fields": [
                {"field_name": "id", "field_type": "int", "is_required": True, "description": "ID unik"},
                {"field_name": "name", "field_type": "str", "is_required": True, "description": "Nama"}
            ]
        }
    ]
    interfaces = [
        {
            "interface_id": "IFC-01",
            "interface_type": "HTTP_ENDPOINT",
            "identifier": "/products",
            "http_method": "GET",
            "target_file": "main.py",
            "parameters": [],
            "expected_return": {
                "return_type": "List[Product]",
                "status_code_success": 200,
                "status_code_errors": []
            }
        },
        {
            "interface_id": "IFC-02",
            "interface_type": "HTTP_ENDPOINT",
            "identifier": "/products",
            "http_method": "POST",
            "target_file": "main.py",
            "parameters": [
                {"param_name": "item", "param_type": "Product", "param_location": "BODY", "is_required": True}
            ],
            "expected_return": {
                "return_type": "Product",
                "status_code_success": 201,
                "status_code_errors": [{"code": 422, "condition": "Validation Error"}]
            }
        }
    ]
    assertions = [
        {
            "assertion_id": "AST-01",
            "linked_req_id": "REQ-01",
            "linked_interface_id": "IFC-01",
            "test_scenario": "Get all products returns 200 OK",
            "target_symbol": "/products",
            "input_fixture": "client.get('/products')",
            "expected_outcome": {
                "outcome_type": "HTTP_STATUS",
                "expected_status": 200,
                "value": None
            },
            "assertion": "response.status_code == 200"
        },
        {
            "assertion_id": "AST-02",
            "linked_req_id": "REQ-02",
            "linked_interface_id": "IFC-02",
            "test_scenario": "Create product returns 201 Created",
            "target_symbol": "/products",
            "input_fixture": "client.post('/products', json={'id': 1, 'name': 'Item'})",
            "expected_outcome": {
                "outcome_type": "HTTP_STATUS",
                "expected_status": 201,
                "value": None
            },
            "assertion": "response.status_code == 201"
        }
    ]
    return complete_aligned_contract(
        draft_dict=draft,
        data_models=models,
        interface_contracts=interfaces,
        testable_assertions=assertions
    )


# ===========================================================================
# 1. Schema & Canonical JCS Tests
# ===========================================================================

def test_contract_schema_pydantic_validation():
    """Test 1: Memvalidasi bahwa skema Pydantic v2 memvalidasi kontrak dengan benar."""
    c_dict = get_valid_contract_dict()
    model = MachineReadableContract.from_dict(c_dict)
    assert model.contract_id == "contract_test_001"
    assert model.contract_version == "1.0.1"
    assert len(model.functional_requirements) == 2
    assert len(model.interface_contracts) == 2
    assert len(model.testable_assertions) == 2


def test_canonicalize_json_rfc8785_determinism():
    """Test 2: Memverifikasi determinisme RFC 8785 JCS (sorting keys, no whitespace)."""
    dict_a = {"z": 1, "a": {"d": 4, "c": 3}, "m": "test"}
    dict_b = {"a": {"c": 3, "d": 4}, "m": "test", "z": 1}
    
    canon_a = canonicalize_json(dict_a)
    canon_b = canonicalize_json(dict_b)
    
    assert canon_a == canon_b
    assert canon_a == '{"a":{"c":3,"d":4},"m":"test","z":1}'


def test_canonical_sha256_anti_circular_exclusion():
    """Test 3: Memverifikasi anti-circular hashing dengan mengecualikan provenance.contract_sha256."""
    c_dict = get_valid_contract_dict()
    
    # Hitung hash sebelum provenance.contract_sha256 disuntikkan
    hash_before = compute_contract_canonical_hash(c_dict)
    
    # Suntikkan hash ke provenance
    c_dict["provenance"]["contract_sha256"] = hash_before
    
    # Hitung kembali hash setelah provenance.contract_sha256 disuntikkan
    hash_after = compute_contract_canonical_hash(c_dict)
    
    # Hash sebelum dan sesudah eksklusi harus 100% IDENTIK (Anti-Circular)
    assert hash_before == hash_after
    assert len(hash_before) == 64


# ===========================================================================
# 2. Validation Gate (4 Pilar) Tests
# ===========================================================================

def test_validation_gate_pilar1_schema_validity():
    """Test 4: Pilar 1 menolak kontrak jika field wajib tidak lengkap atau tipe data salah."""
    c_dict = get_valid_contract_dict()
    del c_dict["interface_contracts"]
    
    is_valid, errors, _ = validate_contract_gate(c_dict)
    assert not is_valid
    assert any("interface_contracts" in e for e in errors)


def test_validation_gate_pilar2_duplicate_req_id():
    """Test 5: Pilar 2 menolak kontrak jika terdapat duplikasi req_id."""
    c_dict = get_valid_contract_dict()
    c_dict["functional_requirements"].append({
        "req_id": "REQ-01",
        "description": "Duplikat REQ-01",
        "acceptance_semantics": []
    })
    
    is_valid, errors, _ = validate_contract_gate(c_dict)
    assert not is_valid
    assert any("Duplikasi req_id" in e for e in errors)


def test_validation_gate_pilar2_duplicate_assertion_id():
    """Test 6: Pilar 2 menolak kontrak jika terdapat duplikasi assertion_id."""
    c_dict = get_valid_contract_dict()
    dup_ast = copy.deepcopy(c_dict["testable_assertions"][0])
    c_dict["testable_assertions"].append(dup_ast)
    
    is_valid, errors, _ = validate_contract_gate(c_dict)
    assert not is_valid
    assert any("Duplikasi assertion_id" in e for e in errors)


def test_validation_gate_pilar2_dangling_linked_req_id():
    """Test 7: Pilar 2 menolak kontrak jika assertion merujuk ke linked_req_id fiktif."""
    c_dict = get_valid_contract_dict()
    c_dict["testable_assertions"][0]["linked_req_id"] = "REQ-99_FIKTIF"
    
    is_valid, errors, _ = validate_contract_gate(c_dict)
    assert not is_valid
    assert any("merujuk ke linked_req_id fiktif" in e for e in errors)


def test_validation_gate_pilar2_dangling_linked_interface_id():
    """Test 8: Pilar 2 menolak kontrak jika assertion merujuk ke linked_interface_id fiktif."""
    c_dict = get_valid_contract_dict()
    c_dict["testable_assertions"][0]["linked_interface_id"] = "IFC-99_FIKTIF"
    
    is_valid, errors, _ = validate_contract_gate(c_dict)
    assert not is_valid
    assert any("merujuk ke linked_interface_id fiktif" in e for e in errors)


def test_validation_gate_pilar2_unregistered_target_symbol():
    """Test 9: Pilar 2 menolak kontrak jika target_symbol tidak terdaftar pada antarmuka atau model."""
    c_dict = get_valid_contract_dict()
    c_dict["testable_assertions"][0]["target_symbol"] = "unknown_symbol_xyz"
    
    is_valid, errors, _ = validate_contract_gate(c_dict)
    assert not is_valid
    assert any("target_symbol 'unknown_symbol_xyz'" in e for e in errors)


def test_validation_gate_pilar3_untested_functional_requirement():
    """Test 10: Pilar 3 menolak kontrak jika ada functional requirement tanpa assertion (100% coverage)."""
    c_dict = get_valid_contract_dict()
    c_dict["functional_requirements"].append({
        "req_id": "REQ-03",
        "description": "Requirement baru tanpa assertion pengujian",
        "acceptance_semantics": ["Harus ada"]
    })
    
    is_valid, errors, _ = validate_contract_gate(c_dict)
    assert not is_valid
    assert any("Pilar 3 (Cakupan): Persyaratan fungsional tanpa assertion" in e for e in errors)


def test_validation_gate_pilar3_untestable_assertion_outcome_type():
    """Test 11: Pilar 3 menolak assertion yang tidak memiliki outcome_type terukur."""
    c_dict = get_valid_contract_dict()
    c_dict["testable_assertions"][0]["expected_outcome"]["outcome_type"] = None
    
    # Model Pydantic akan menolak None pada outcome_type
    is_valid, errors, _ = validate_contract_gate(c_dict)
    assert not is_valid


def test_validation_gate_pilar4_internal_consistency_return_type():
    """Test 12: Pilar 4 memberikan advisory warning jika return_type tidak terdaftar di data_models."""
    c_dict = get_valid_contract_dict()
    c_dict["interface_contracts"][0]["expected_return"]["return_type"] = "UnknownCustomType"
    
    is_valid, errors, warnings = validate_contract_gate(c_dict)
    assert is_valid  # Non-prescriptive, hanya advisory warning
    assert any("UnknownCustomType" in w for w in warnings)


def test_validation_gate_pilar4_internal_consistency_status_code():
    """Test 13: Pilar 4 menolak jika assertion HTTP_STATUS menuntut status code yang tidak dideklarasikan pada interface."""
    c_dict = get_valid_contract_dict()
    # Interface IFC-01 hanya mendeklarasikan 200, tapi assertion menuntut 204
    c_dict["testable_assertions"][0]["expected_outcome"]["expected_status"] = 204
    
    is_valid, errors, _ = validate_contract_gate(c_dict)
    assert not is_valid
    assert any("Assertion 'AST-01' mengharapkan HTTP status 204" in e for e in errors)


def test_validation_gate_pilar4_rest_conventions_advisory_warning():
    """Test 14: Pilar 4 memberikan advisory warning untuk konvensi REST tanpa memblokir validitas."""
    c_dict = get_valid_contract_dict()
    # Ubah POST IFC-02 status sukses menjadi 200 (REST convention menyarankan 201)
    c_dict["interface_contracts"][1]["expected_return"]["status_code_success"] = 200
    c_dict["testable_assertions"][1]["expected_outcome"]["expected_status"] = 200
    
    is_valid, errors, warnings = validate_contract_gate(c_dict)
    assert is_valid
    assert len(errors) == 0
    assert any("mengembalikan status 200 (Konvensi REST" in w for w in warnings)


# ===========================================================================
# 3. Lifecycle Transitions & Checkpoint Tests
# ===========================================================================

def test_lifecycle_seal_and_freeze_success():
    """Test 15: Transisi ALIGNED -> FROZEN menyegel kontrak dengan SHA-256 canonical hash."""
    c_dict = get_valid_contract_dict()
    assert c_dict["status"] == "ALIGNED"
    
    success, frozen, errors, warnings = seal_and_freeze_contract(c_dict)
    assert success is True
    assert frozen["status"] == "FROZEN"
    assert "contract_sha256" in frozen["provenance"]
    assert len(frozen["provenance"]["contract_sha256"]) == 64
    assert len(errors) == 0


def test_lifecycle_seal_and_freeze_rejection():
    """Test 16: Transisi gagal pada kontrak tidak valid mengubah status menjadi REJECTED."""
    c_dict = get_valid_contract_dict()
    c_dict["testable_assertions"][0]["linked_req_id"] = "INVALID"
    
    success, rejected, errors, _ = seal_and_freeze_contract(c_dict)
    assert success is False
    assert rejected["status"] == "REJECTED"
    assert len(errors) > 0


def test_checkpoint_verification_success():
    """Test 17: Verifikasi integritas berhasil pada kontrak FROZEN yang belum diubah."""
    c_dict = get_valid_contract_dict()
    _, frozen, _, _ = seal_and_freeze_contract(c_dict)
    
    is_valid, err = verify_contract_checkpoint(frozen, "developer_pre_flight")
    assert is_valid is True
    assert err is None


def test_checkpoint_verification_tamper_abort():
    """Test 18: Verifikasi integritas mendeteksi modifikasi diam-diam dan memicu abort."""
    c_dict = get_valid_contract_dict()
    _, frozen, _, _ = seal_and_freeze_contract(c_dict)
    
    # Tampering: ubah deskripsi requirement secara diam-diam tanpa memperbarui segel
    frozen_tampered = copy.deepcopy(frozen)
    frozen_tampered["functional_requirements"][0]["description"] = "TAMPERED REQUIREMENT"
    
    is_valid, err = verify_contract_checkpoint(frozen_tampered, "developer_pre_flight")
    assert is_valid is False
    assert "Contract integrity violation" in err
    
    # Melempar ContractIntegrityError saat raise_on_error=True
    with pytest.raises(ContractIntegrityError):
        verify_contract_checkpoint(frozen_tampered, "developer_pre_flight", raise_on_error=True)


def test_contract_immutability_enforcement():
    """Test 19: Penegakan immutabilitas menolak mutasi kontrak FROZEN tanpa bump versi."""
    c_dict = get_valid_contract_dict()
    _, frozen, _, _ = seal_and_freeze_contract(c_dict)
    
    mutated = copy.deepcopy(frozen)
    mutated["constraints"]["max_files"] = 99
    
    with pytest.raises(ContractImmutabilityError):
        enforce_contract_immutability(frozen, mutated)


# ===========================================================================
# 4. Diagnostic Parser Integration Tests
# ===========================================================================

def test_diagnostic_parser_deterministic_contract_mapping():
    """Test 20: Diagnostic parser memetakan kegagalan pengujian ke klausul kontrak secara deterministik."""
    c_dict = get_valid_contract_dict()
    
    failing = FailingTest(
        test_file="test_main.py",
        test_name="test_get_products_ast01",
        failure_type="ASSERTION_FAILURE",
        message="assert 404 == 200"
    )
    
    aid, rid, ifid = map_evidence_to_contract(failing, c_dict)
    assert aid == "AST-01"
    assert rid == "REQ-01"
    assert ifid == "IFC-01"


def test_diagnostic_parser_contract_unambiguous_fallback():
    """Test 21: Diagnostic parser mengembalikan None jika tidak ada tautan pasti (zero hallucination)."""
    c_dict = get_valid_contract_dict()
    
    failing_ambiguous = FailingTest(
        test_file="test_unknown.py",
        test_name="test_random_unrelated_function",
        failure_type="RUNTIME_EXCEPTION",
        message="KeyError: 'foo'"
    )
    
    aid, rid, ifid = map_evidence_to_contract(failing_ambiguous, c_dict)
    assert aid is None
    assert rid is None
    assert ifid is None


# ===========================================================================
# 5. Reviewer Dual-Layer & Frozen Oracle Tests
# ===========================================================================

def test_reviewer_dual_layer_layer1_deterministic_blocking():
    """Test 22: Gerbang Lapis 1 Reviewer menolak jika sandbox pengujian gagal atau simbol AST hilang."""
    c_dict = get_valid_contract_dict()
    _, frozen, _, _ = seal_and_freeze_contract(c_dict)
    
    # Skenario 1: Test runner gagal
    state_failed_test: SquadState = {
        "contract": frozen,
        "code_files": {"main.py": "class Product:\n    pass\n"},
        "test_files": {"test_main.py": "# Test for: AST-01\n"},
        "test_results": {"passed": False, "exit_code": 1, "output": "AssertionError"},
        "target_language": "python",
        "logs": []
    }
    is_passed, gate_data = evaluate_deterministic_evidence_gate(state_failed_test)
    assert is_passed is False
    assert gate_data["checks"]["sandbox_execution"] == "FAILED"
    
    # Skenario 2: Tests pass, tetapi model Product hilang dari AST
    state_missing_symbol: SquadState = {
        "contract": frozen,
        "code_files": {"main.py": "def foo(): pass\n"},
        "test_files": {"test_main.py": "# Test for: AST-01\n# Test for: AST-02\n"},
        "test_results": {"passed": True, "exit_code": 0, "output": "2 passed"},
        "target_language": "python",
        "logs": []
    }
    is_passed, gate_data = evaluate_deterministic_evidence_gate(state_missing_symbol)
    assert is_passed is False
    assert gate_data["checks"]["ast_structural"] == "FAILED"
    assert any("Product" in e for e in gate_data["errors"])


def test_reviewer_dual_layer_layer2_bounded_review_pass():
    """Test 23: Lapis 1 lolos 100% dan Lapis 2 LLM Reviewer memberikan putusan APPROVED."""
    c_dict = get_valid_contract_dict()
    _, frozen, _, _ = seal_and_freeze_contract(c_dict)
    
    valid_code = (
        "class Product:\n"
        "    id: int\n"
        "    name: str\n\n"
        "# Route: /products\n"
        "def get_products():\n"
        "    return []\n"
    )
    
    state_success: SquadState = {
        "contract": frozen,
        "code_files": {"main.py": valid_code},
        "test_files": {"test_main.py": "# Test for: AST-01\n# Test for: AST-02\n"},
        "test_results": {"passed": True, "exit_code": 0, "output": "2 passed"},
        "target_language": "python",
        "specifications": "Spesifikasi produk",
        "architecture_plan": "Rencana arsitektur",
        "logs": [],
        "iteration_count": 0,
        "max_iterations": 3
    }
    
    # Layer 1 Gate Check
    is_passed, gate_data = evaluate_deterministic_evidence_gate(state_success)
    assert is_passed is True
    assert gate_data["checks"]["contract_integrity"] == "PASSED"
    assert gate_data["checks"]["sandbox_execution"] == "PASSED"
    assert gate_data["checks"]["ast_structural"] == "PASSED"
    
    # Mock Reviewer LLM
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content="[APPROVED] Seluruh kode modular dan mematuhi kontrak.")
    
    with patch("backend.agents.reviewer.get_llm", return_value=mock_llm):
        result = reviewer_agent(state_success)
        assert result["status"] == "completed"
        assert "[APPROVED]" in result["review_notes"]
        assert "=== DETERMINISTIC EVIDENCE GATE (LAYER 1) ===" in result["review_notes"]
        assert "=== BOUNDED LLM REVIEW (LAYER 2) ===" in result["review_notes"]


def test_frozen_oracle_bypass_preservation(tmp_path):
    """Test 24: Memastikan bypass Frozen Oracle tetap utuh dan membaca suite pengujian statis."""
    # Buat file oracle dummy
    oracle_dir = tmp_path / "oracle_suite"
    oracle_dir.mkdir()
    (oracle_dir / "test_oracle.py").write_text("def test_ground_truth(): assert True", encoding="utf-8")
    
    state: SquadState = {
        "frozen_oracle_path": str(oracle_dir),
        "target_language": "python",
        "iteration_count": 0,
        "logs": []
    }
    
    result = frozen_oracle_node(state)
    assert "test_files" in result
    assert "test_oracle.py" in result["test_files"]
    assert result["test_files"]["test_oracle.py"] == "def test_ground_truth(): assert True"