# -*- coding: utf-8 -*-
"""
Unit Test Suite: Architect Contract Binding v2
ReinDev Studio — Generic, Mission-Agnostic, Language-Agnostic Contract Binding

Verifies all 15 core scenarios:
1. Canonical obligation extraction from Python test suite (Interaction + Model + Callable).
2. Canonical obligation extraction from Dart test suite (Widget + Provider + Model).
3. 100% coverage when Architect contract exactly matches Oracle obligations.
4. 100% coverage with semantic equivalence (proven route mapping).
5. Rejection when 1 mandatory obligation is missing (coverage < 100%).
6. Rejection when 1 obligation is incompatible (method mismatch).
7. Rejection when internal functions exist but NO public route binding covers the endpoint.
8. Rejected contract is NOT acceptance authority (provenance check, cannot seed new obligations).
9. Attempt-0 feedback propagation (first attempt receives full Coverage Matrix diagnosis).
10. Repair loop reaches FROZEN when Architect supplies missing obligation on subsequent turn.
11. Repair loop aborts after budget exhaustion if Architect never covers obligations.
12. Canonical Obligation Integrity check (CANONICAL OBLIGATION INTEGRITY invariant).
13. Non-solver guarantee (diagnoses WHAT is missing, zero imperative HOW instructions).
14. Language-agnostic adapter boundary test (pure PARSE -> NORMALIZE -> REPRESENT).
15. Telemetry verification (CoverageMatrix logged to tracer).
"""

import pytest
from pathlib import Path
from typing import Dict, Any, List

from backend.canonical_obligation import (
    CanonicalObligation,
    CanonicalObligationIntegrityError,
    ObligationAuthority,
    ObligationProvenance,
    ObligationKind,
    CoverageStatus,
    ObligationCoverageResult,
    CoverageMatrix,
    PythonAstOracleAdapter,
    DartAstOracleAdapter,
    extract_canonical_oracle_obligations,
    check_obligation_coverage,
    validate_canonical_obligation_integrity,
    assert_canonical_obligation_unmodified,
)
from backend.contract import (
    MachineReadableContract,
    ContractStatus,
    InterfaceContract,
    DataModel,
    create_draft_contract,
    complete_aligned_contract,
    seal_and_freeze_contract,
    check_pre_freeze_authority_compatibility,
)
from backend.phase_validators import validate_architect_phase
from backend.graph import architect_validator_node


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def tmp_oracle_dir(tmp_path):
    """Direktori sementara untuk Frozen Acceptance Oracle."""
    oracle_dir = tmp_path / "frozen_oracle"
    oracle_dir.mkdir(parents=True, exist_ok=True)
    return oracle_dir


# ===========================================================================
# 1. Extraction Scenarios (Python & Dart)
# ===========================================================================

def test_scenario_01_python_canonical_obligation_extraction(tmp_oracle_dir):
    """
    Scenario 1: Canonical obligation extraction from Python test suite.
    Extracts Interaction (HTTP GET/POST), Data Model (Product), and Callable (add_numbers, calculate).
    """
    test_file = tmp_oracle_dir / "test_api_and_module.py"
    test_file.write_text(
        "from main import Product, add_numbers\n"
        "import main\n\n"
        "def test_app(client):\n"
        "    r1 = client.get('/products')\n"
        "    r2 = client.post('/orders', json={'qty': 1})\n"
        "    assert hasattr(main, 'calculate')\n"
        "    assert main.compute_total() == 100\n",
        encoding="utf-8"
    )

    obligations = extract_canonical_oracle_obligations(frozen_oracle_path=str(tmp_oracle_dir))

    assert len(obligations) >= 5
    # Check integrity & provenance
    for ob in obligations:
        assert ob.authority == ObligationAuthority.ORACLE.value
        assert ob.provenance == ObligationProvenance.ORACLE_FACT.value
        assert ob.source_reference.startswith("test_api_and_module.py")

    kinds = {ob.public_identity: ob.obligation_kind for ob in obligations}
    assert kinds.get("/products") == ObligationKind.INTERACTION.value
    assert kinds.get("/orders") == ObligationKind.INTERACTION.value
    assert kinds.get("Product") == ObligationKind.DATA_MODEL.value
    assert kinds.get("add_numbers") == ObligationKind.CALLABLE_INTERFACE.value
    assert kinds.get("calculate") == ObligationKind.CALLABLE_INTERFACE.value


def test_scenario_02_dart_canonical_obligation_extraction(tmp_oracle_dir):
    """
    Scenario 2: Canonical obligation extraction from Dart test suite.
    Extracts Observable Runtime (Widget), State Provider, and Data Model without framework pollution.
    """
    test_file = tmp_oracle_dir / "dashboard_widget_test.dart"
    test_file.write_text(
        "import 'package:flutter_test/flutter_test.dart';\n"
        "void main() {\n"
        "  testWidgets('renders dashboard', (tester) async {\n"
        "    final data = MetricData(title: 'Revenue', amount: 5000);\n"
        "    await tester.pumpWidget(MaterialApp(home: Scaffold(body: CardMetric(data: data))));\n"
        "    expect(find.byType(CardMetric), findsOneWidget);\n"
        "    expect(find.byType(StatusBadge), findsOneWidget);\n"
        "    final val = container.read(metricDataProvider);\n"
        "  });\n"
        "}\n",
        encoding="utf-8"
    )

    obligations = extract_canonical_oracle_obligations(frozen_oracle_path=str(tmp_oracle_dir))

    assert len(obligations) >= 4
    for ob in obligations:
        assert ob.authority == ObligationAuthority.ORACLE.value
        assert ob.provenance == ObligationProvenance.ORACLE_FACT.value
        assert ob.source_reference.startswith("dashboard_widget_test.dart")

    identities = {ob.public_identity for ob in obligations}
    assert "CardMetric" in identities
    assert "StatusBadge" in identities
    assert "metricDataProvider" in identities
    assert "MetricData" in identities

    # Excluded framework types must NOT be present
    for fw in ["MaterialApp", "Scaffold", "WidgetTester", "Key"]:
        assert fw not in identities


# ===========================================================================
# 2. Coverage & Compatibility Scenarios
# ===========================================================================

def test_scenario_03_exact_match_full_coverage_freezes(tmp_oracle_dir):
    """
    Scenario 3: 100% coverage when Architect contract exactly matches Oracle obligations.
    All obligations COVERED -> contract transitions to FROZEN with valid SHA-256 seal.
    """
    test_file = tmp_oracle_dir / "test_products.py"
    test_file.write_text(
        "def test_products(client):\n"
        "    r1 = client.get('/products')\n"
        "    r2 = client.post('/products', json={'name': 'Item'})\n",
        encoding="utf-8"
    )

    draft = create_draft_contract(raw_intent="Products API", target_language="python", domain="REST_API")
    contract_dict = complete_aligned_contract(
        draft_dict=draft,
        data_models=[],
        interface_contracts=[
            {
                "interface_id": "IFC-01",
                "interface_type": "HTTP_ENDPOINT",
                "identifier": "/products",
                "target_file": "main.py",
                "http_method": "GET"
            },
            {
                "interface_id": "IFC-02",
                "interface_type": "HTTP_ENDPOINT",
                "identifier": "/products",
                "target_file": "main.py",
                "http_method": "POST"
            }
        ],
        testable_assertions=[{
            "assertion_id": "AST-01",
            "linked_req_id": "REQ-01",
            "test_scenario": "Test products endpoint",
            "target_symbol": "/products",
            "expected_outcome": {"outcome_type": "HTTP_STATUS", "expected_status": 200}
        }]
    )

    success, frozen, errors, warnings = seal_and_freeze_contract(
        contract_dict,
        frozen_oracle_path=str(tmp_oracle_dir)
    )

    assert success is True
    assert frozen.get("status") == ContractStatus.FROZEN.value
    assert len(frozen.get("provenance", {}).get("contract_sha256", "")) == 64
    assert len(errors) == 0


def test_scenario_04_semantic_route_equivalence_covered(tmp_oracle_dir):
    """
    Scenario 4 (Correction 1): 100% coverage with semantic equivalence.
    Oracle tests client.get('/users/123').
    Architect defines interface route='/users' with method GET.
    Deterministic compatibility proof accepts valid semantic mapping.
    """
    test_file = tmp_oracle_dir / "test_users.py"
    test_file.write_text(
        "def test_get_user(client):\n"
        "    user_id = 123\n"
        "    r = client.get(f'/users/{user_id}')\n"
        "    assert r.status_code == 200\n",
        encoding="utf-8"
    )

    draft = create_draft_contract(raw_intent="Users API", target_language="python", domain="REST_API")
    contract_dict = complete_aligned_contract(
        draft_dict=draft,
        data_models=[],
        interface_contracts=[{
            "interface_id": "IFC-USER-01",
            "interface_type": "HTTP_ENDPOINT",
            "identifier": "get_user_by_id",
            "route": "/users",
            "target_file": "main.py",
            "http_method": "GET",
            "parameters": [{"param_name": "user_id", "param_type": "int", "param_location": "PATH", "is_required": True}]
        }],
        testable_assertions=[{
            "assertion_id": "AST-01",
            "linked_req_id": "REQ-01",
            "test_scenario": "Get user by ID",
            "target_symbol": "get_user_by_id",
            "expected_outcome": {"outcome_type": "HTTP_STATUS", "expected_status": 200}
        }]
    )

    contract_obj = MachineReadableContract(**contract_dict)
    is_compat, errors, missing = check_pre_freeze_authority_compatibility(contract_obj, str(tmp_oracle_dir))

    assert is_compat is True
    assert len(missing) == 0
    assert len(errors) == 0


def test_scenario_05_rejection_missing_mandatory_obligation(tmp_oracle_dir):
    """
    Scenario 5: Rejection when 1 mandatory obligation is missing.
    Oracle demands GET /items and POST /items. Contract only declares POST /items.
    """
    test_file = tmp_oracle_dir / "test_items.py"
    test_file.write_text(
        "def test_items(client):\n"
        "    r1 = client.get('/items')\n"
        "    r2 = client.post('/items', json={'name': 'Item'})\n",
        encoding="utf-8"
    )

    draft = create_draft_contract(raw_intent="Items API", target_language="python", domain="REST_API")
    contract_dict = complete_aligned_contract(
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
            "test_scenario": "Post items",
            "target_symbol": "/items",
            "expected_outcome": {"outcome_type": "HTTP_STATUS", "expected_status": 201}
        }]
    )

    success, res, errors, warnings = seal_and_freeze_contract(
        contract_dict,
        frozen_oracle_path=str(tmp_oracle_dir)
    )

    assert success is False
    assert res.get("status") == ContractStatus.REJECTED.value
    assert any("GET /items" in e for e in errors)


def test_scenario_06_rejection_incompatible_method(tmp_oracle_dir):
    """
    Scenario 6: Rejection when 1 obligation is incompatible (method mismatch).
    Oracle demands DELETE /items. Contract declares /items with PUT.
    """
    test_file = tmp_oracle_dir / "test_delete.py"
    test_file.write_text(
        "def test_delete(client):\n"
        "    r = client.delete('/items')\n",
        encoding="utf-8"
    )

    draft = create_draft_contract(raw_intent="Delete API", target_language="python", domain="REST_API")
    contract_dict = complete_aligned_contract(
        draft_dict=draft,
        data_models=[],
        interface_contracts=[{
            "interface_id": "IFC-01",
            "interface_type": "HTTP_ENDPOINT",
            "identifier": "/items",
            "target_file": "main.py",
            "http_method": "PUT"
        }],
        testable_assertions=[{
            "assertion_id": "AST-01",
            "linked_req_id": "REQ-01",
            "test_scenario": "Put items",
            "target_symbol": "/items",
            "expected_outcome": {"outcome_type": "HTTP_STATUS", "expected_status": 200}
        }]
    )

    success, res, errors, _ = seal_and_freeze_contract(
        contract_dict,
        frozen_oracle_path=str(tmp_oracle_dir)
    )

    assert success is False
    assert res.get("status") == ContractStatus.REJECTED.value


def test_scenario_07_internal_function_without_route_binding_rejected(tmp_oracle_dir):
    """
    Scenario 7: Rejection when internal functions exist but NO public route binding covers the endpoint.
    Oracle demands HTTP GET /products.
    Contract declares internal function 'get_products' without public HTTP route binding.
    """
    test_file = tmp_oracle_dir / "test_products.py"
    test_file.write_text(
        "def test_products(client):\n"
        "    r = client.get('/products')\n",
        encoding="utf-8"
    )

    draft = create_draft_contract(raw_intent="API", target_language="python", domain="REST_API")
    contract_dict = complete_aligned_contract(
        draft_dict=draft,
        data_models=[],
        interface_contracts=[{
            "interface_id": "IFC-FN-01",
            "interface_type": "FUNCTION",
            "identifier": "get_products",
            "target_file": "main.py",
            "parameters": []
        }],
        testable_assertions=[{
            "assertion_id": "AST-01",
            "linked_req_id": "REQ-01",
            "test_scenario": "Get products internal function",
            "target_symbol": "get_products",
            "expected_outcome": {"outcome_type": "VALUE_EQUALS"}
        }]
    )

    contract_obj = MachineReadableContract(**contract_dict)
    is_compat, errors, missing = check_pre_freeze_authority_compatibility(contract_obj, str(tmp_oracle_dir))

    assert is_compat is False
    assert len(missing) == 1
    assert "HTTP GET /products" in missing[0]["obligation"]
    # Notice about internal function is surfaced in diagnosis
    assert any("Notice: Found internal function(s)" in m["reason"] for m in missing)


# ===========================================================================
# 3. Provenance & Invariant Scenarios
# ===========================================================================

def test_scenario_08_rejected_contract_not_acceptance_authority(tmp_oracle_dir):
    """
    Scenario 8: Rejected contract is NOT acceptance authority.
    Obligations cannot be derived from rejected artifacts or PM proposals.
    Attempting to create an obligation with authority ORACLE but non-ORACLE_FACT provenance fails.
    """
    with pytest.raises(CanonicalObligationIntegrityError) as exc_info:
        CanonicalObligation(
            obligation_id="OBL-FAKED",
            authority=ObligationAuthority.ORACLE.value,
            provenance=ObligationProvenance.ARCHITECT_INFERENCE.value,  # Tainted!
            public_identity="faked_func"
        )
    assert "Violation of Canonical Obligation Integrity" in str(exc_info.value)


def test_scenario_12_canonical_obligation_integrity_guard():
    """
    Scenario 12: CANONICAL OBLIGATION INTEGRITY invariant.
    assert_canonical_obligation_unmodified detects any mutation or post-hoc tampering.
    """
    ob1 = CanonicalObligation(
        obligation_id="OBL-1",
        authority=ObligationAuthority.ORACLE.value,
        provenance=ObligationProvenance.ORACLE_FACT.value,
        public_identity="/endpoint",
        inputs={"http_method": "GET"},
        source_reference="test_file.py:10"
    )
    authoritative = [ob1]

    # Modifying inputs in a candidate copy must raise error
    tampered_ob = CanonicalObligation(
        obligation_id="OBL-1",
        authority=ObligationAuthority.ORACLE.value,
        provenance=ObligationProvenance.ORACLE_FACT.value,
        public_identity="/endpoint",
        inputs={"http_method": "POST"},  # Mutated!
        source_reference="test_file.py:10"
    )

    with pytest.raises(CanonicalObligationIntegrityError) as exc:
        assert_canonical_obligation_unmodified(authoritative, [tampered_ob])
    assert "Post-hoc compliance violation" in str(exc.value)

    # Deleting an obligation must raise error
    with pytest.raises(CanonicalObligationIntegrityError) as exc2:
        assert_canonical_obligation_unmodified(authoritative, [])
    assert "Post-hoc compliance violation: Obligations set modified" in str(exc2.value)


# ===========================================================================
# 4. Feedback Propagation & Repair Loop Scenarios
# ===========================================================================

def test_scenario_09_attempt_0_feedback_propagation(tmp_oracle_dir):
    """
    Scenario 9: Attempt-0 feedback propagation.
    On Attempt 0, if contract fails pre-freeze gate, contract_validation_errors
    must be immediately propagated to temp_state, phase validator, and CEP evidence package.
    """
    test_file = tmp_oracle_dir / "test_main.py"
    test_file.write_text(
        "import main\ndef test_feature():\n    assert hasattr(main, 'MandatoryCoreFeature')\n",
        encoding="utf-8"
    )

    draft = create_draft_contract(raw_intent="Feature", target_language="python", domain="CLI_TOOL")
    incomplete_contract = complete_aligned_contract(
        draft_dict=draft,
        data_models=[],
        interface_contracts=[{
            "interface_id": "IFC-01",
            "interface_type": "FUNCTION",
            "identifier": "OtherFeature",
            "target_file": "main.py"
        }],
        testable_assertions=[{
            "assertion_id": "AST-01",
            "linked_req_id": "REQ-01",
            "test_scenario": "Other feature",
            "target_symbol": "OtherFeature",
            "expected_outcome": {"outcome_type": "VALUE_EQUALS"}
        }]
    )

    initial_state = {
        "run_id": "test_run_attempt_0",
        "task": "Implement MandatoryCoreFeature",
        "contract": incomplete_contract,
        "frozen_oracle_path": str(tmp_oracle_dir),
        "target_language": "python",
        "architecture_plan": '=== BLUEPRINT JSON ===\n{"authoritative_target_file": "main.py", "file_tree": ["main.py"], "architecture_summary": "Architecture", "files": {"main.py": {"module_role": "Core", "imports": [], "code_scaffold": "def OtherFeature(): pass"}}, "interface_contracts": [{"identifier": "OtherFeature", "route": "", "method": "", "interface_type": "FUNCTION", "description": "", "parameters": [], "expected_return": "None"}], "data_models": []}',
        "repair_attempt_counts": {"architect": 0},
        "max_repairs": 3,
        "logs": []
    }

    result = architect_validator_node(initial_state)

    # Verifikasi Attempt 0 menerima diagnosis lengkap
    assert result["architect_validator_contract"]["verdict"] == "FAIL"
    gate_errors = result["contract_validation_errors"]
    assert len(gate_errors) > 0
    assert any("MandatoryCoreFeature" in err for err in gate_errors)
    assert result["contract_status"] == ContractStatus.REJECTED.value

    # Verifikasi CEP memuat preskripsi terkait ketiadaan obligasi
    cep = result.get("latest_evidence_package")
    assert cep is not None
    rx_changes = [rx.get("required_change", "") for rx in cep.get("actionable_prescriptions", [])]
    assert any("lacks deterministic coverage for mandatory acceptance obligations" in chg for chg in rx_changes)


def test_scenario_10_repair_loop_reaches_frozen(tmp_oracle_dir):
    """
    Scenario 10: Multi-turn repair loop succeeds.
    Turn 0: Incomplete contract -> REJECTED.
    Turn 1: Repaired contract with missing symbol -> FROZEN.
    """
    test_file = tmp_oracle_dir / "test_main.py"
    test_file.write_text(
        "import main\ndef test_calc():\n    assert hasattr(main, 'calculate')\n",
        encoding="utf-8"
    )

    draft = create_draft_contract(raw_intent="Calculator", target_language="python", domain="CLI_TOOL")

    # Turn 0: Missing calculate
    bad_contract = complete_aligned_contract(
        draft_dict=draft,
        data_models=[],
        interface_contracts=[{"interface_id": "IFC-01", "interface_type": "FUNCTION", "identifier": "wrong_fn", "target_file": "main.py"}],
        testable_assertions=[{"assertion_id": "AST-01", "linked_req_id": "REQ-01", "test_scenario": "Test", "target_symbol": "wrong_fn", "expected_outcome": {"outcome_type": "VALUE_EQUALS"}}]
    )
    ok0, res0, err0, _ = seal_and_freeze_contract(bad_contract, frozen_oracle_path=str(tmp_oracle_dir))
    assert not ok0
    assert res0.get("status") == ContractStatus.REJECTED.value

    # Turn 1: Repaired with calculate
    good_contract = complete_aligned_contract(
        draft_dict=draft,
        data_models=[],
        interface_contracts=[{"interface_id": "IFC-01", "interface_type": "FUNCTION", "identifier": "calculate", "target_file": "main.py"}],
        testable_assertions=[{"assertion_id": "AST-01", "linked_req_id": "REQ-01", "test_scenario": "Test", "target_symbol": "calculate", "expected_outcome": {"outcome_type": "VALUE_EQUALS"}}]
    )
    ok1, res1, err1, _ = seal_and_freeze_contract(good_contract, frozen_oracle_path=str(tmp_oracle_dir))
    assert ok1
    assert res1.get("status") == ContractStatus.FROZEN.value
    assert len(res1.get("provenance", {}).get("contract_sha256", "")) == 64


def test_scenario_11_budget_exhaustion_stops(tmp_oracle_dir):
    """
    Scenario 11: Repair loop aborts after budget exhaustion if Architect never covers obligations.
    """
    test_file = tmp_oracle_dir / "test_main.py"
    test_file.write_text(
        "import main\ndef test_req():\n    assert hasattr(main, 'Mandatory')\n",
        encoding="utf-8"
    )

    draft = create_draft_contract(raw_intent="Tool", target_language="python", domain="CLI_TOOL")
    bad_contract = complete_aligned_contract(
        draft_dict=draft,
        data_models=[],
        interface_contracts=[{"interface_id": "IFC-01", "interface_type": "FUNCTION", "identifier": "Wrong", "target_file": "main.py"}],
        testable_assertions=[{"assertion_id": "AST-01", "linked_req_id": "REQ-01", "test_scenario": "Test", "target_symbol": "Wrong", "expected_outcome": {"outcome_type": "VALUE_EQUALS"}}]
    )

    state = {
        "run_id": "test_budget",
        "task": "Build tool",
        "contract": bad_contract,
        "frozen_oracle_path": str(tmp_oracle_dir),
        "target_language": "python",
        "architecture_plan": "Short",
        "repair_attempt_counts": {"architect": 2},
        "max_repairs": 2,
        "logs": []
    }

    result = architect_validator_node(state)
    assert result["architect_validator_contract"]["verdict"] == "FAIL"
    assert result["status"] == "terminal_failure_architect_boundary"
    assert result["contract_status"] == ContractStatus.REJECTED.value


# ===========================================================================
# 5. Non-Solver & Boundary Scenarios
# ===========================================================================

def test_scenario_13_non_solver_guarantee(tmp_oracle_dir):
    """
    Scenario 13 (Correction 3): Non-solver guarantee.
    Coverage engine and CEP provide DIAGNOSIS (WHAT is missing/incompatible),
    NOT solution design (zero imperative instructions like 'Tambahkan fungsi X').
    """
    test_file = tmp_oracle_dir / "test_api.py"
    test_file.write_text(
        "def test_app(client):\n"
        "    r = client.post('/checkout')\n",
        encoding="utf-8"
    )

    draft = create_draft_contract(raw_intent="API", target_language="python", domain="REST_API")
    contract_dict = complete_aligned_contract(
        draft_dict=draft,
        data_models=[],
        interface_contracts=[],
        testable_assertions=[]
    )

    contract_obj = MachineReadableContract(**contract_dict)
    is_compat, errors, missing = check_pre_freeze_authority_compatibility(contract_obj, str(tmp_oracle_dir))

    combined = "\n".join(errors)
    # Check for presence of diagnosis markers
    assert "ORACLE_OBLIGATION:" in combined
    assert "CONTRACT_COVERAGE:" in combined
    assert "DIAGNOSIS:" in combined
    assert "RESULT:" in combined

    # Check ABSENCE of imperative solver instructions
    imperative_forbidden = [
        "Tambahkan fungsi",
        "Buat file",
        "Tambahkan class",
        "Gunakan decorator",
        "Implementasikan method",
        "Definisikan route",
    ]
    for forbid in imperative_forbidden:
        assert forbid.lower() not in combined.lower()


def test_scenario_14_language_adapter_pure_parse_normalize_represent():
    """
    Scenario 14 (Correction 2): Language adapters are strictly PARSE -> NORMALIZE -> REPRESENT.
    Adapters do not possess task-specific domain heuristics.
    """
    py_adapter = PythonAstOracleAdapter()
    dart_adapter = DartAstOracleAdapter()

    # Python adapter handles only test files
    assert py_adapter.can_handle("test_api.py") is True
    assert py_adapter.can_handle("api_test.py") is True
    assert py_adapter.can_handle("main.py") is False

    # Dart adapter handles only test files
    assert dart_adapter.can_handle("widget_test.dart") is True
    assert dart_adapter.can_handle("main.dart") is False

    # Check that adapters extract obligations from synthetic code without knowing any task
    py_code = "from main import CustomCalculator\ndef test(): assert hasattr(main, 'calc_root')\n"
    py_obs = py_adapter.extract_obligations("test_sample.py", py_code)
    identities_py = {ob.public_identity for ob in py_obs}
    assert "CustomCalculator" in identities_py
    assert "calc_root" in identities_py

    dart_code = "void main() { testWidgets('t', (tester) async { expect(find.byType(CustomGraphWidget), findsOneWidget); }); }"
    dart_obs = dart_adapter.extract_obligations("widget_test.dart", dart_code)
    identities_dart = {ob.public_identity for ob in dart_obs}
    assert "CustomGraphWidget" in identities_dart


def test_scenario_15_telemetry_coverage_matrix_logged(tmp_oracle_dir):
    """
    Scenario 15: Telemetry verification.
    Coverage matrix telemetry (counts, is_fully_covered) is recorded on contract and logged to tracer.
    """
    test_file = tmp_oracle_dir / "test_math.py"
    test_file.write_text(
        "from main import add_vectors, multiply_matrices\n",
        encoding="utf-8"
    )

    draft = create_draft_contract(raw_intent="Math", target_language="python", domain="ALGORITHM")
    aligned = complete_aligned_contract(
        draft_dict=draft,
        data_models=[],
        interface_contracts=[
            {"interface_id": "IFC-01", "interface_type": "FUNCTION", "identifier": "add_vectors", "target_file": "main.py"},
            {"interface_id": "IFC-02", "interface_type": "FUNCTION", "identifier": "multiply_matrices", "target_file": "main.py"}
        ],
        testable_assertions=[
            {"assertion_id": "AST-01", "linked_req_id": "REQ-01", "test_scenario": "Add", "target_symbol": "add_vectors", "expected_outcome": {"outcome_type": "VALUE_EQUALS"}},
            {"assertion_id": "AST-02", "linked_req_id": "REQ-01", "test_scenario": "Mul", "target_symbol": "multiply_matrices", "expected_outcome": {"outcome_type": "VALUE_EQUALS"}}
        ]
    )

    ok, frozen, errors, _ = seal_and_freeze_contract(aligned, frozen_oracle_path=str(tmp_oracle_dir))
    assert ok is True

    # Telemetry attached to contract
    cov_dict = frozen.get("provenance", {}).get("coverage_matrix")
    assert cov_dict is not None
    assert cov_dict["oracle_obligations_count"] == 2
    assert cov_dict["covered_count"] == 2
    assert cov_dict["missing_count"] == 0
    assert cov_dict["is_fully_covered"] is True
