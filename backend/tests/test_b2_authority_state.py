# -*- coding: utf-8 -*-
"""
Test Suite: B2 Authority State, Provenance Preservation, Turn-0 Timing, and Non-Solver Prescriptions
Menguji pemisahan wewenang epistemik (Church of Goat 🐐):
- Test A: Rejected contract has no authority
- Test B: Frozen contract retains authority
- Test C: Oracle authority is preserved
- Test D: Turn-0 timing propagation
- Test E: Non-solver prescription
- Test F: Regression verification
"""

import pytest
from pathlib import Path
from backend.state import SquadState
from backend.contextual_evidence import (
    ContextualEvidencePackage,
    ViolationItem,
    render_repair_directive,
)
from backend.context_assembler import (
    assemble_b2_evidence,
    synthesize_b2_actionable_prescriptions,
    _standard_forbidden_changes,
)
from backend.contract import extract_oracle_tested_symbols
from backend.phase_validators import validate_architect_phase
from backend.graph import architect_validator_node

ORACLE_FLUTTER_PATH = "dokumentasi-pengembangan/experiments/frozen_oracle/flutter_t1"


def test_a_rejected_contract_has_no_authority():
    """
    Test A: Interface dari contract REJECTED/DRAFT tidak boleh memperoleh wewenang.
    - CardMetricWidget tidak muncul sebagai required_interfaces.
    - CardMetricWidget tidak muncul sebagai frozen invariant.
    - CardMetricWidget tidak muncul sebagai expected post-repair interface.
    - CardMetricWidget tidak menghasilkan forbidden rename rule.
    - Rejected interface tetap tersedia sebagai diagnostic evidence dengan provenance.
    """
    state: SquadState = {
        "task": "Bangun komponen widget kartu metrik modern responsif Flutter",
        "target_language": "dart",
        "frozen_oracle_path": ORACLE_FLUTTER_PATH,
        "contract_status": "REJECTED",
        "contract_sha256": "",
        "contract": {
            "task_intent": {"authoritative_target_file": "lib/card_metric.dart"},
            "interface_contracts": [
                {
                    "interface_id": "IFC-01",
                    "interface_type": "WIDGET",
                    "identifier": "CardMetricWidget",
                    "target_file": "lib/card_metric.dart"
                }
            ],
            "data_models": []
        }
    }

    violations = [
        ViolationItem(
            violation_id="VIO-001",
            criterion="contract_oracle_consistency",
            severity="CRITICAL",
            location="contract",
            observed_state="Contract interface ['CardMetricWidget'] tidak konsisten dengan authoritative acceptance call-site ['CardMetric']",
            expected_state="Seluruh interface contract selaras dengan pemanggilan Acceptance Oracle",
            source_detector="PHASE_VALIDATOR_DETERMINISTIC",
            observed_symbol="CardMetricWidget"
        )
    ]

    pkg = assemble_b2_evidence(state, violations, [], run_id="test_run_a", iteration=0)

    # 1. CardMetricWidget TIDAK muncul sebagai required_interfaces
    auth_ctx = pkg.authoritative_context
    assert "CardMetricWidget" not in auth_ctx.get("required_interfaces", [])
    # 2. CardMetricWidget TIDAK muncul sebagai frozen invariant
    for inv in pkg.preserved_invariants:
        assert "CardMetricWidget" not in inv.description
        assert inv.category != "CONTRACT_STATUS"  # No frozen contract invariant
    # 3. CardMetricWidget TIDAK muncul sebagai expected post-repair interface
    for s in pkg.expected_post_repair_state:
        assert "CardMetricWidget" not in s
    # 4. CardMetricWidget TIDAK menghasilkan forbidden rename rule
    assert "Rename authoritative interface names defined in contract" not in pkg.forbidden_changes
    assert "Rename authoritative interface names defined in contract" not in pkg.repair_boundary.forbidden_changes
    # 5. Rejected interface tetap tersedia sebagai diagnostic evidence dengan provenance
    assert "proposed_contract_interfaces" in auth_ctx or any(
        e.get("item") == "proposed_contract_interfaces" for e in pkg.evidence
    )
    diag_ev = next((e for e in pkg.evidence if e.get("item") == "proposed_contract_interfaces"), None)
    assert diag_ev is not None
    assert diag_ev.get("provenance") in ("REJECTED_CONTRACT", "PROPOSED_CONTRACT")
    assert "CardMetricWidget" in diag_ev.get("observed", [])


def test_b_frozen_contract_retains_authority():
    """
    Test B: Interface dari contract FROZEN mempertahankan wewenang formal.
    """
    state: SquadState = {
        "task": "Bangun komponen widget kartu metrik modern responsif Flutter",
        "target_language": "dart",
        "frozen_oracle_path": ORACLE_FLUTTER_PATH,
        "contract_status": "FROZEN",
        "contract_sha256": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        "contract": {
            "task_intent": {"authoritative_target_file": "lib/card_metric.dart"},
            "interface_contracts": [
                {
                    "interface_id": "IFC-01",
                    "interface_type": "WIDGET",
                    "identifier": "CardMetric",
                    "target_file": "lib/card_metric.dart"
                }
            ],
            "data_models": []
        }
    }

    pkg = assemble_b2_evidence(state, [], [], run_id="test_run_b", iteration=0)

    auth_ctx = pkg.authoritative_context
    assert auth_ctx.get("required_interfaces") == ["CardMetric"]
    assert any("Interface contracts exactly match: ['CardMetric']" in s for s in pkg.expected_post_repair_state)
    assert "Rename authoritative interface names defined in contract" in pkg.forbidden_changes


def test_c_oracle_authority_is_preserved():
    """
    Test C: Oracle call-site dikenali sebagai bukti penerimaan otoritatif.
    """
    symbols = extract_oracle_tested_symbols(ORACLE_FLUTTER_PATH, target_lang="dart")
    assert "CardMetric" in symbols

    state: SquadState = {
        "task": "Bangun komponen widget kartu metrik modern responsif Flutter",
        "target_language": "dart",
        "frozen_oracle_path": ORACLE_FLUTTER_PATH,
        "contract_status": "REJECTED",
        "contract": {
            "task_intent": {"authoritative_target_file": "lib/card_metric.dart"},
            "interface_contracts": [{"identifier": "CardMetricWidget"}],
        }
    }

    pkg = assemble_b2_evidence(state, [], [], run_id="test_run_c", iteration=0)
    auth_ctx = pkg.authoritative_context
    assert "CardMetric" in auth_ctx.get("authoritative_oracle_interfaces", [])

    oracle_ev = next((e for e in pkg.evidence if e.get("item") == "authoritative_oracle_interfaces"), None)
    assert oracle_ev is not None
    assert oracle_ev.get("provenance") == "AUTHORITATIVE_ORACLE_INTERFACE"
    assert "CardMetric" in oracle_ev.get("observed", [])


def test_d_turn_0_timing_propagation():
    """
    Test D: Pada Turn 0, contract_validation_errors harus tersedia sebelum
    validate_architect_phase() dan menghasilkan B2 violation pada feedback pertama.
    """
    from backend.contract import create_draft_contract
    from backend.agents.architect import _build_default_aligned_contract

    draft = create_draft_contract(
        raw_intent="Bangun komponen widget kartu metrik modern responsif Flutter",
        target_language="dart",
        domain="FLUTTER_WIDGET"
    )
    aligned = _build_default_aligned_contract(
        draft,
        "Bangun komponen widget kartu metrik modern responsif Flutter",
        "dart",
        arch_plan="Blueprint scaffold plan for card metric widget in Flutter"
    )
    # Ubah identifier agar memicu inkonsistensi terhadap Oracle Acceptance ('CardMetric')
    aligned["interface_contracts"][0]["identifier"] = "CardMetricWidget"
    aligned["testable_assertions"][0]["target_symbol"] = "CardMetricWidget"

    initial_state: SquadState = {
        "task": "Bangun komponen widget kartu metrik modern responsif Flutter dengan Material Design 3 dan Riverpod state.",
        "target_language": "dart",
        "frozen_oracle_path": ORACLE_FLUTTER_PATH,
        "expected_oracle_sha": "4589e15cfb8f37ba70642e70623ca143bceee1a44175aefd072f441d9e8a9528",
        "contract": aligned,
        "architecture_plan": "A valid blueprint scaffold plan exceeding 50 chars for testing purposes.",
        "iteration_count": 0,
        "repair_attempt_counts": {"architect": 0}
    }

    result = architect_validator_node(initial_state)

    # 1. Status kontrak harus REJECTED
    assert result.get("contract_status") == "REJECTED"
    # 2. contract_validation_errors harus terisi pada Turn 0
    gate_errors = result.get("contract_validation_errors", [])
    assert len(gate_errors) > 0
    assert any("Oracle Consistency" in e or "inconsistent with the frozen test" in e for e in gate_errors)
    # 3. Architect Validator Contract (B2) harus FAIL dan memuat violation oracle consistency
    val_c = result.get("architect_validator_contract", {})
    assert val_c.get("verdict") == "FAIL"
    violations = val_c.get("violations", [])
    assert any(v.get("criterion") == "contract_oracle_consistency" for v in violations)
    # 4. Contextual Evidence Package harus diterbitkan ke latest_evidence_package
    cep = result.get("latest_evidence_package")
    assert cep is not None
    assert cep.get("causal_owner") == "ARCHITECT"
    assert any(rx.get("prescription_id", "").startswith("RX-B2-ORACLE-CONSISTENCY") for rx in cep.get("actionable_prescriptions", []))


def test_e_non_solver_prescription():
    """
    Test E: B2 menghasilkan preskripsi requirement-level dan non-solver.
    Dilarang menghasilkan 'Rename X to Y' atau hardcoding identifier kasus.
    """
    violation = ViolationItem(
        violation_id="VIO-002",
        criterion="contract_oracle_consistency",
        severity="CRITICAL",
        location="contract",
        observed_state="Contract interface ['CardMetricWidget'] tidak konsisten dengan authoritative acceptance call-site ['CardMetric']",
        expected_state="Seluruh interface contract selaras dengan pemanggilan Acceptance Oracle pada berkas pengujian independen",
        source_detector="PHASE_VALIDATOR_DETERMINISTIC",
        observed_symbol=None
    )

    prescriptions = synthesize_b2_actionable_prescriptions([violation], "lib/card_metric.dart", "dart")
    assert len(prescriptions) == 1
    rx = prescriptions[0]

    # Requirement-level
    assert "must be consistent with the authoritative acceptance call-sites" in rx.required_change
    # Non-solver check: tidak ada perintah solusi spesifik seperti "Rename"
    assert not rx.required_change.lower().startswith("rename ")
    assert "cardmetric" not in rx.required_change.lower()  # No hardcoding in prescription generator logic


def test_f_no_regression_and_directive_rendering():
    """
    Test F: Verifikasi render_repair_directive, ketahanan regresi epistemik, dan serialisasi.
    - Directive pada REJECTED contract tidak membocorkan larangan rename atau wewenang palsu.
    - Directive pada FROZEN contract mempertahankan boundary dan invariant formal.
    - Serialisasi CEP (to_dict / from_dict) mempertahankan pemisahan wewenang secara idempoten.
    """
    # 1. Kasus REJECTED contract
    state_rejected: SquadState = {
        "task": "Bangun komponen widget kartu metrik modern responsif Flutter",
        "target_language": "dart",
        "frozen_oracle_path": ORACLE_FLUTTER_PATH,
        "contract_status": "REJECTED",
        "contract": {
            "task_intent": {"authoritative_target_file": "lib/card_metric.dart"},
            "interface_contracts": [{"identifier": "CardMetricWidget"}],
        }
    }
    pkg_rejected = assemble_b2_evidence(state_rejected, [], [], run_id="test_run_f_rej", iteration=0)
    directive_rejected = render_repair_directive(pkg_rejected)

    # Memastikan tidak ada larangan rename antarmuka pada artefak rejected
    assert "Rename authoritative interface names defined in contract" not in directive_rejected
    # Memastikan CardMetricWidget tidak diklaim sebagai required_interfaces dalam direktif
    assert "required_interfaces" not in directive_rejected or "CardMetricWidget" not in pkg_rejected.authoritative_context.get("required_interfaces", [])
    # Memastikan konteks otoritatif membedakan proposed vs oracle interfaces
    assert "proposed_contract_interfaces: CardMetricWidget" in directive_rejected
    assert "authoritative_oracle_interfaces: CardMetric" in directive_rejected

    # Memverifikasi provenance eksplisit pada evidence payload
    prop_ev = next((e for e in pkg_rejected.evidence if e.get("item") == "proposed_contract_interfaces"), None)
    assert prop_ev is not None
    assert prop_ev.get("provenance") in ("REJECTED_CONTRACT", "PROPOSED_CONTRACT")
    assert prop_ev.get("evidence_class") == "DIAGNOSTIC"

    oracle_ev = next((e for e in pkg_rejected.evidence if e.get("item") == "authoritative_oracle_interfaces"), None)
    assert oracle_ev is not None
    assert oracle_ev.get("provenance") == "AUTHORITATIVE_ORACLE_INTERFACE"
    assert oracle_ev.get("evidence_class") == "DETERMINISTIC"

    # 2. Kasus FROZEN contract
    state_frozen: SquadState = {
        "task": "Bangun komponen widget kartu metrik modern responsif Flutter",
        "target_language": "dart",
        "frozen_oracle_path": ORACLE_FLUTTER_PATH,
        "contract_status": "FROZEN",
        "contract_sha256": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        "contract": {
            "task_intent": {"authoritative_target_file": "lib/card_metric.dart"},
            "interface_contracts": [{"identifier": "CardMetric"}],
        }
    }
    pkg_frozen = assemble_b2_evidence(state_frozen, [], [], run_id="test_run_f_froz", iteration=0)
    directive_frozen = render_repair_directive(pkg_frozen)

    # Kontrak beku mempertahankan boundary formal
    assert "Rename authoritative interface names defined in contract" in directive_frozen
    assert "CardMetric" in directive_frozen
    assert pkg_frozen.authoritative_context.get("required_interfaces") == ["CardMetric"]

    # 3. Verifikasi serialisasi & rekonstruksi (to_dict / from_dict)
    pkg_dict = pkg_rejected.to_dict()
    pkg_reconstructed = ContextualEvidencePackage.from_dict(pkg_dict)
    assert "required_interfaces" not in pkg_reconstructed.authoritative_context
    assert pkg_reconstructed.authoritative_context.get("proposed_contract_interfaces") == ["CardMetricWidget"]
    assert "CardMetric" in pkg_reconstructed.authoritative_context.get("authoritative_oracle_interfaces", [])


