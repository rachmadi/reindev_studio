# -*- coding: utf-8 -*-
"""
Deterministic Test Matrix for Architect Authority Binding v1
ReinDev Studio — Iterasi 6 (Controlled Architect Treatment)

Tests A through L + Abstract Failure Pattern:
- Test A: Exact identity match -> PASS
- Test B: Identity mismatch -> REJECT (CALLABLE_IDENTITY)
- Test C: Parameter identity mismatch -> REJECT (PARAMETER_IDENTITY)
- Test D: Return mismatch bila authoritative -> REJECT (RETURN_IDENTITY)
- Test E: Target artifact mismatch bila authoritative -> REJECT (TARGET_ARTIFACT)
- Test F: PM proposal conflicts with Oracle -> Oracle remains authority
- Test G: Semantically similar but non-identical names -> Exact Identity Rule rejects
- Test H: Insufficient evidence -> UNDETERMINED / fail-closed
- Test I: Multiple possible blueprint matches -> ambiguity / fail-closed
- Test J: Unrelated implementation detail -> MUST NOT reject
- Test K: Generic cross-task test -> no domain-specific branch
- Test L: Repair preserves unrelated proven invariants
- Abstract Failure Pattern: A != B, PM proposal = B, Architect chooses B -> REJECTED
"""

import pytest
from backend.canonical_obligation import (
    CanonicalObligation,
    ObligationKind,
    ObligationAuthority,
    ObligationProvenance,
    CoverageStatus,
    AuthorityMismatchDimension,
    AuthorityBindingEvidence,
    check_obligation_coverage,
    CoverageMatrix,
)
from backend.contract import (
    MachineReadableContract,
    ContractStatus,
    check_pre_freeze_authority_compatibility,
    seal_and_freeze_contract,
)


def _make_obligation(
    ob_id: str,
    identity: str,
    kind: ObligationKind,
    inputs: dict = None,
    outputs: dict = None,
    pos_args: int = 0,
    kw_args: list = None,
    arg_names: list = None,
    source_ref: str = "tests/test_suite.py:10",
    metadata: dict = None,
) -> CanonicalObligation:
    return CanonicalObligation(
        obligation_id=ob_id,
        authority=ObligationAuthority.FROZEN_ORACLE.value,
        provenance=ObligationProvenance.ORACLE_FACT.value,
        obligation_kind=kind.value,
        public_identity=identity,
        inputs=inputs or {},
        outputs=outputs or {},
        positional_arguments=pos_args,
        keyword_arguments=kw_args or [],
        argument_names=arg_names or (kw_args or []),
        source_reference=source_ref,
        metadata=metadata or {},
        observable_behavior=f"Test observable behavior for {identity}",
        acceptance_evidence=f"test_{identity}()"
    )


def test_a_exact_identity_match_passes():
    """Test A: Exact identity match -> PASS (CoverageStatus.COVERED)."""
    ob = _make_obligation(
        "OBL-01",
        "calculate_hash",
        ObligationKind.CALLABLE_INTERFACE,
        pos_args=2,
        arg_names=["data", "salt"]
    )
    contract = {
        "interface_contracts": [{
            "interface_id": "IFC-01",
            "identifier": "calculate_hash",
            "target_file": "crypto.py",
            "parameters": [
                {"param_name": "data", "is_required": True},
                {"param_name": "salt", "is_required": True}
            ]
        }]
    }
    blueprint = {
        "files": {
            "crypto.py": "def calculate_hash(data, salt):\n    pass\n"
        }
    }
    matrix = check_obligation_coverage([ob], contract, blueprint=blueprint)
    assert matrix.is_fully_covered is True
    assert matrix.covered_count == 1
    assert matrix.incompatible_count == 0
    assert matrix.results[0].status == CoverageStatus.COVERED


def test_b_identity_mismatch_rejects():
    """Test B: Identity mismatch -> REJECT (CALLABLE_IDENTITY)."""
    ob = _make_obligation(
        "OBL-02",
        "execute_transaction",
        ObligationKind.CALLABLE_INTERFACE,
        pos_args=1,
        arg_names=["tx"]
    )
    contract = {
        "interface_contracts": [{
            "interface_id": "IFC-02",
            "identifier": "run_transaction",
            "target_file": "tx_engine.py"
        }]
    }
    blueprint = {
        "files": {
            "tx_engine.py": "def run_transaction(tx):\n    pass\n"
        }
    }
    matrix = check_obligation_coverage([ob], contract, blueprint=blueprint)
    assert matrix.is_fully_covered is False
    assert matrix.missing_count == 1
    r = matrix.results[0]
    assert r.status == CoverageStatus.MISSING
    assert r.binding_evidence is not None
    assert r.binding_evidence.mismatch_dimension == AuthorityMismatchDimension.CALLABLE_IDENTITY


def test_c_parameter_identity_mismatch_rejects():
    """Test C: Parameter identity mismatch -> REJECT (PARAMETER_IDENTITY)."""
    ob = _make_obligation(
        "OBL-03",
        "/items",
        ObligationKind.INTERACTION,
        inputs={"http_method": "POST", "payload_fields": ["title", "priority"]},
        outputs={"expected_status": 201}
    )
    contract = {
        "interface_contracts": [{
            "interface_id": "IFC-03",
            "identifier": "/items",
            "route": "/items",
            "http_method": "POST",
            "target_file": "main.py"
        }],
        "data_models": [{
            "model_name": "Item",
            "fields": [{"name": "title"}, {"name": "importance"}],
            "target_file": "main.py"
        }]
    }
    blueprint = {
        "files": {
            "main.py": (
                "from pydantic import BaseModel\n"
                "class Item(BaseModel):\n"
                "    title: str\n"
                "    importance: int\n\n"
                "@app.post('/items', status_code=201)\n"
                "def create_item(item: Item):\n"
                "    pass\n"
            )
        }
    }
    matrix = check_obligation_coverage([ob], contract, blueprint=blueprint)
    assert matrix.is_fully_covered is False
    assert matrix.incompatible_count == 1
    r = matrix.results[0]
    assert r.status == CoverageStatus.INCOMPATIBLE
    assert r.binding_evidence is not None
    assert r.binding_evidence.mismatch_dimension == AuthorityMismatchDimension.PARAMETER_IDENTITY
    assert "priority" in r.reason


def test_d_return_mismatch_authoritative_rejects():
    """Test D: Return mismatch bila authoritative -> REJECT (RETURN_IDENTITY)."""
    ob = _make_obligation(
        "OBL-04",
        "/orders",
        ObligationKind.INTERACTION,
        inputs={"http_method": "POST"},
        outputs={"expected_status": 201}
    )
    contract = {
        "interface_contracts": [{
            "interface_id": "IFC-04",
            "identifier": "/orders",
            "route": "/orders",
            "http_method": "POST",
            "target_file": "main.py",
            "status_code": 200
        }]
    }
    blueprint = {
        "files": {
            "main.py": (
                "@app.post('/orders', status_code=200)\n"
                "def place_order():\n"
                "    pass\n"
            )
        }
    }
    matrix = check_obligation_coverage([ob], contract, blueprint=blueprint)
    assert matrix.is_fully_covered is False
    assert matrix.incompatible_count == 1
    r = matrix.results[0]
    assert r.status == CoverageStatus.INCOMPATIBLE
    assert r.binding_evidence is not None
    assert r.binding_evidence.mismatch_dimension == AuthorityMismatchDimension.RETURN_IDENTITY


def test_e_target_artifact_mismatch_rejects():
    """Test E: Target artifact mismatch bila authoritative -> REJECT (TARGET_ARTIFACT)."""
    ob = _make_obligation(
        "OBL-05",
        "ConfigParser",
        ObligationKind.DATA_MODEL,
        metadata={"target_artifact": "config/loader.py"}
    )
    contract = {
        "data_models": [{
            "model_name": "ConfigParser",
            "target_file": "utils/parser.py",
            "fields": []
        }]
    }
    blueprint = {
        "files": {
            "utils/parser.py": "class ConfigParser:\n    pass\n"
        }
    }
    matrix = check_obligation_coverage([ob], contract, blueprint=blueprint)
    assert matrix.is_fully_covered is False
    assert matrix.incompatible_count == 1
    r = matrix.results[0]
    assert r.status == CoverageStatus.INCOMPATIBLE
    assert r.binding_evidence is not None
    assert r.binding_evidence.mismatch_dimension == AuthorityMismatchDimension.TARGET_ARTIFACT


def test_f_pm_proposal_conflicts_with_oracle_oracle_remains_authority():
    """Test F: PM proposal conflicts with Oracle -> Oracle remains sole acceptance authority."""
    ob = _make_obligation(
        "OBL-06",
        "compress_stream",
        ObligationKind.CALLABLE_INTERFACE,
        pos_args=1,
        arg_names=["stream"]
    )
    contract = {
        "interface_contracts": [{
            "interface_id": "IFC-06",
            "identifier": "zip_data",
            "target_file": "compression.py"
        }]
    }
    blueprint = {
        "files": {
            "compression.py": "def zip_data(stream):\n    pass\n"
        }
    }
    matrix = check_obligation_coverage([ob], contract, blueprint=blueprint)
    assert matrix.is_fully_covered is False
    assert matrix.missing_count == 1
    r = matrix.results[0]
    assert r.status == CoverageStatus.MISSING
    assert r.binding_evidence is not None
    assert r.binding_evidence.mismatch_dimension == AuthorityMismatchDimension.CALLABLE_IDENTITY


def test_g_semantically_similar_names_exact_identity_rule_rejects():
    """Test G: Semantically similar but non-identical names -> exact identity rule rejects (no fuzzy match)."""
    ob = _make_obligation(
        "OBL-07",
        "find_by_id",
        ObligationKind.CALLABLE_INTERFACE,
        pos_args=1,
        arg_names=["id"]
    )
    contract = {
        "interface_contracts": [{
            "interface_id": "IFC-07",
            "identifier": "get_by_id",
            "target_file": "repo.py"
        }]
    }
    blueprint = {
        "files": {
            "repo.py": "def get_by_id(id):\n    pass\n"
        }
    }
    matrix = check_obligation_coverage([ob], contract, blueprint=blueprint)
    assert matrix.is_fully_covered is False
    assert matrix.missing_count == 1
    r = matrix.results[0]
    assert r.status == CoverageStatus.MISSING
    assert r.binding_evidence.mismatch_dimension == AuthorityMismatchDimension.CALLABLE_IDENTITY


def test_h_insufficient_evidence_undetermined_fail_closed():
    """Test H: Insufficient evidence -> UNDETERMINED / fail-closed."""
    ob = _make_obligation(
        "OBL-08",
        "/metrics",
        ObligationKind.INTERACTION,
        inputs={"http_method": "GET"}
    )
    contract = {
        "interface_contracts": [{
            "interface_id": "IFC-08",
            "identifier": "/metrics",
            "route": "/metrics",
            "http_method": None,
            "target_file": "main.py"
        }]
    }
    matrix = check_obligation_coverage([ob], contract)
    assert matrix.is_fully_covered is False
    assert matrix.undetermined_count == 1
    r = matrix.results[0]
    assert r.status == CoverageStatus.UNDETERMINED
    assert r.binding_evidence is not None
    assert r.binding_evidence.mismatch_dimension == AuthorityMismatchDimension.INSUFFICIENT_EVIDENCE


def test_i_multiple_possible_blueprint_matches_ambiguity_fail_closed():
    """Test I: Multiple possible blueprint matches -> ambiguity / fail-closed."""
    ob = _make_obligation(
        "OBL-09",
        "/sync",
        ObligationKind.INTERACTION,
        inputs={"http_method": "POST"}
    )
    contract = {
        "interface_contracts": [
            {"interface_id": "IFC-09A", "identifier": "/sync", "route": "/sync", "http_method": "GET", "target_file": "main.py"},
            {"interface_id": "IFC-09B", "identifier": "/sync", "route": "/sync", "http_method": "DELETE", "target_file": "main.py"}
        ]
    }
    matrix = check_obligation_coverage([ob], contract)
    assert matrix.is_fully_covered is False
    assert matrix.missing_count == 1


def test_j_unrelated_implementation_detail_must_not_reject():
    """Test J: Unrelated implementation detail -> MUST NOT reject."""
    ob = _make_obligation(
        "OBL-10",
        "parse_tokens",
        ObligationKind.CALLABLE_INTERFACE,
        pos_args=1,
        arg_names=["text"]
    )
    contract = {
        "interface_contracts": [
            {"interface_id": "IFC-10", "identifier": "parse_tokens", "target_file": "parser.py"},
            {"interface_id": "IFC-HELPER", "identifier": "_internal_token_normalizer", "target_file": "parser.py"}
        ],
        "data_models": [
            {"model_name": "TokenCache", "fields": [{"name": "capacity"}], "target_file": "parser.py"}
        ]
    }
    blueprint = {
        "files": {
            "parser.py": (
                "class TokenCache:\n    def __init__(self, capacity):\n        self.capacity = capacity\n\n"
                "def _internal_token_normalizer(t):\n    return t.strip()\n\n"
                "def parse_tokens(text):\n    return _internal_token_normalizer(text).split()\n"
            )
        }
    }
    matrix = check_obligation_coverage([ob], contract, blueprint=blueprint)
    assert matrix.is_fully_covered is True
    assert matrix.covered_count == 1
    assert matrix.incompatible_count == 0


def test_k_generic_cross_task_no_domain_specific_branch():
    """Test K: Generic cross-task test -> no domain-specific branch."""
    ob = _make_obligation(
        "OBL-11",
        "QuantumRegister",
        ObligationKind.DATA_MODEL,
        kw_args=["num_qubits", "entangled"]
    )
    contract = {
        "data_models": [{
            "model_name": "QuantumRegister",
            "fields": [{"name": "num_qubits"}, {"name": "entangled"}],
            "target_file": "quantum.py"
        }]
    }
    blueprint = {
        "files": {
            "quantum.py": (
                "class QuantumRegister:\n"
                "    def __init__(self, num_qubits, entangled=False):\n"
                "        self.num_qubits = num_qubits\n"
                "        self.entangled = entangled\n"
            )
        }
    }
    matrix = check_obligation_coverage([ob], contract, blueprint=blueprint)
    assert matrix.is_fully_covered is True
    assert matrix.covered_count == 1


def test_l_repair_preserves_unrelated_proven_invariants():
    """Test L: Repair preserves unrelated proven invariants."""
    ob_proven = _make_obligation(
        "OBL-12A",
        "validate_input",
        ObligationKind.CALLABLE_INTERFACE,
        pos_args=1,
        arg_names=["inp"]
    )
    ob_fixed = _make_obligation(
        "OBL-12B",
        "format_output",
        ObligationKind.CALLABLE_INTERFACE,
        pos_args=1,
        arg_names=["res"]
    )
    contract = {
        "interface_contracts": [
            {"interface_id": "IFC-12A", "identifier": "validate_input", "target_file": "pipeline.py"},
            {"interface_id": "IFC-12B", "identifier": "format_output", "target_file": "pipeline.py"}
        ]
    }
    blueprint = {
        "files": {
            "pipeline.py": (
                "def validate_input(inp):\n    return True\n\n"
                "def format_output(res):\n    return str(res)\n"
            )
        }
    }
    matrix = check_obligation_coverage([ob_proven, ob_fixed], contract, blueprint=blueprint)
    assert matrix.is_fully_covered is True
    assert matrix.covered_count == 2
    assert matrix.incompatible_count == 0


def test_abstract_failure_pattern_a_ne_b_rejected():
    """
    Abstract Failure Pattern Test:
    Authority demands A.
    PM proposes B.
    Architect chooses B.
    A != B.
    Verdict: REJECTED (Contract Gate MUST NOT freeze).
    """
    ob_a = _make_obligation(
        "OBL-ABS-A",
        "symbol_A",
        ObligationKind.CALLABLE_INTERFACE,
        pos_args=1,
        arg_names=["arg1"]
    )
    contract = {
        "interface_contracts": [{
            "interface_id": "IFC-ABS-B",
            "identifier": "symbol_B",
            "target_file": "module.py"
        }]
    }
    blueprint = {
        "files": {
            "module.py": "def symbol_B(arg1):\n    pass\n"
        }
    }
    matrix = check_obligation_coverage([ob_a], contract, blueprint=blueprint)
    assert matrix.is_fully_covered is False
    assert matrix.missing_count == 1
    r = matrix.results[0]
    assert r.status == CoverageStatus.MISSING
    assert r.binding_evidence is not None
    assert r.binding_evidence.mismatch_dimension == AuthorityMismatchDimension.CALLABLE_IDENTITY
    assert r.binding_evidence.expected_value == "symbol_A"
    assert "symbol_B" in r.binding_evidence.actual_value
