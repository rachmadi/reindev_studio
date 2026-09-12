"""
Unit Tests: Semantic State Preservation Across Serialization Repair (D-104)
Menguji secara deterministik pemisahan status semantik dari representasi artefak:
A. Semantic invariant yang PROVEN tetap tersedia ketika blueprint schema/serialization gagal.
B. Repair context membedakan PROVEN semantic invariant dari FAILED representation property.
C. Repair serialization tidak menghapus atau mengganti proven interface state.
D. Rejected/Draft interface tidak dapat dipromosikan menjadi proven invariant.
E. Jika evidence baru membuktikan semantic invariant salah, invariant dapat dicabut/ditandai REGRESSION secara deterministik.
F. Mekanisme bersifat generic dan tidak mengandung identifier task-specific seperti `CardMetric`.
G. Regression test untuk authority-state fix sebelumnya tetap PASS.
H. Oracle checksum tetap identik.
"""

import os
import re
import hashlib
from pathlib import Path
import pytest

from backend.contract import (
    ContractStatus,
    extract_oracle_tested_symbols,
    extract_proven_semantic_interfaces,
    check_oracle_interface_consistency,
    InterfaceContract,
)
from backend.phase_validators import validate_architect_phase
from backend.context_assembler import assemble_b2_evidence, synthesize_b2_actionable_prescriptions
from backend.contextual_evidence import (
    ContextualEvidencePackage,
    PreservedInvariant,
    ViolationItem,
    render_repair_directive,
)


ORACLE_FLUTTER_DIR = Path("dokumentasi-pengembangan/experiments/frozen_oracle/flutter_t1")
ORACLE_TEST_FILE = ORACLE_FLUTTER_DIR / "card_metric_test.dart"
EXPECTED_ORACLE_SHA = "4589e15cfb8f37ba70642e70623ca143bceee1a44175aefd072f441d9e8a9528"


def test_a_proven_semantic_invariant_available_when_blueprint_fails(tmp_path):
    """
    Test A: Semantic invariant yang PROVEN tetap tersedia ketika blueprint schema/serialization gagal.
    """
    # 1. Antarmuka terbukti konsisten dengan Oracle (CardMetric)
    proven = extract_proven_semantic_interfaces(
        [{"identifier": "CardMetric", "interface_type": "WIDGET"}],
        str(ORACLE_FLUTTER_DIR),
        target_lang="dart"
    )
    assert proven == ["CardMetric"]

    # 2. Blueprint rusak secara sintaksis/skema (JSON invalid)
    broken_arch_plan = "=== BLUEPRINT JSON ===\n{ invalid json schema syntax ...\n=== END BLUEPRINT JSON ==="
    state = {
        "task": "Buat widget kartu metrik",
        "target_language": "dart",
        "frozen_oracle_path": str(ORACLE_FLUTTER_DIR),
        "architecture_plan": broken_arch_plan,
        "contract": {
            "status": "REJECTED",
            "interface_contracts": [{"identifier": "CardMetric", "interface_type": "WIDGET"}],
            "data_models": [],
        },
        "contract_status": "REJECTED",
        "contract_sha256": None,
        "contract_validation_errors": [],  # Tidak ada error konsistensi oracle
        "proven_semantic_interfaces": ["CardMetric"],
    }

    result = validate_architect_phase(state)

    # Verdict fase Architect wajib FAIL karena blueprint cacat
    assert result["verdict"] == "FAIL"

    # Evaluasi deterministik membuktikan konsistensi antarmuka semantik adalah PROVEN
    oracle_ev = next(e for e in result["evidence"] if e["item"] == "contract_oracle_interface_consistency")
    assert oracle_ev["status"] == "VALID"
    assert "PROVEN" in oracle_ev["observed"]

    # Evaluasi deterministik membuktikan blueprint AST adalah INVALID
    bp_ev = next(e for e in result["evidence"] if e["item"] == "blueprint_ast_validity")
    assert bp_ev["status"] == "INVALID"


def test_b_repair_context_distinguishes_proven_invariant_from_failed_representation():
    """
    Test B: Repair context membedakan PROVEN semantic invariant dari FAILED representation property.
    """
    state = {
        "task": "Implementasi widget kartu metrik",
        "target_language": "dart",
        "frozen_oracle_path": str(ORACLE_FLUTTER_DIR),
        "contract_status": "REJECTED",
        "contract_sha256": None,
        "contract": {
            "status": "REJECTED",
            "interface_contracts": [{"identifier": "CardMetric", "interface_type": "WIDGET"}],
            "data_models": [],
        },
        "proven_semantic_interfaces": ["CardMetric"],
    }

    violations = [
        ViolationItem(
            violation_id="VIO-001",
            severity="CRITICAL",
            criterion="blueprint_json_schema",
            location="architecture_plan",
            observed_state="JSON schema decode failure: Invalid escape character",
            expected_state="Valid ArchitecturalBlueprint JSON",
            source_detector="BLUEPRINT_SCHEMA_CHECK",
        )
    ]

    cep = assemble_b2_evidence(state, violations, [], run_id="test_run", iteration=1)

    # 1. Authoritative Context memisahkan status semantik vs representasi
    auth = cep.authoritative_context
    assert auth["oracle_interface_consistency"] == "PROVEN"
    assert auth["blueprint_schema"] == "FAIL"
    assert auth["contract_freeze"] == "NOT_AUTHORIZED"
    assert auth["proven_semantic_invariants"] == ["CardMetric"]
    assert "blueprint_json_schema" in auth["unproven_failed_representation_properties"]

    # 2. Preserved Invariant memuat PROVEN_SEMANTIC_INVARIANT dengan status PROVEN
    sem_inv = next((inv for inv in cep.preserved_invariants if inv.category == "PROVEN_SEMANTIC_INVARIANT"), None)
    assert sem_inv is not None
    assert sem_inv.status == "PROVEN"
    assert sem_inv.state == "LOCKED"
    assert sem_inv.target == "CardMetric"
    assert sem_inv.mutation == "FORBIDDEN"
    assert sem_inv.provenance_evidence["provenance"] == "PROVEN_SEMANTIC_INVARIANT"

    # 3. Actionable Prescription RX-B2-SEMANTIC-PRESERVE-001 diterbitkan secara non-solver
    prescriptions = cep.actionable_prescriptions
    rx_preserve = next((r for r in prescriptions if "SEMANTIC-PRESERVE" in r.prescription_id), None)
    assert rx_preserve is not None
    assert "proven and must be preserved while repairing the current serialization/schema failure" in rx_preserve.required_change

    # 4. Repair boundary melarang modifikasi antarmuka yang terbukti
    assert any("Do NOT alter or re-infer proven semantic interfaces" in fc for fc in cep.repair_boundary.forbidden_changes)

    # 5. Rendering repair directive memuat seksi yang terpisah
    rendered = render_repair_directive(cep)
    assert "[PROVEN_SEMANTIC_INVARIANT]" in rendered
    assert "CardMetric" in rendered


def test_c_repair_serialization_does_not_erase_proven_interface_state():
    """
    Test C: Repair serialization tidak menghapus atau mengganti proven interface state.
    """
    from backend.agents.architect import architect_agent
    from unittest.mock import patch, MagicMock

    state = {
        "task": "Tugas komponen antarmuka",
        "target_language": "dart",
        "frozen_oracle_path": str(ORACLE_FLUTTER_DIR),
        "contract": {
            "status": "REJECTED",
            "provenance": {},
            "interface_contracts": [{"identifier": "CardMetric", "interface_type": "WIDGET"}],
            "data_models": [],
        },
        "proven_semantic_interfaces": ["CardMetric"],
        "logs": [],
    }

    # Simulasi model mengembalikan JSON blueprint yang valid, namun salah menulis nama identifier (bias 7B)
    mock_llm_response = MagicMock()
    mock_llm_response.content = """=== BLUEPRINT JSON ===
{
  "architecture_summary": "Widget komponen",
  "authoritative_target_file": "lib/card_metric.dart",
  "file_tree": ["lib/card_metric.dart"],
  "files": {
    "lib/card_metric.dart": {
      "file_path": "lib/card_metric.dart",
      "purpose": "Widget",
      "imports": ["package:flutter/material.dart"],
      "declarations": ["CardMetricWidget"],
      "code_scaffold": "class CardMetricWidget extends StatelessWidget {}"
    }
  },
  "interface_contracts": [
    {
      "identifier": "CardMetricWidget",
      "interface_type": "WIDGET",
      "target_file": "lib/card_metric.dart"
    }
  ],
  "data_models": []
}
=== END BLUEPRINT JSON ==="""

    with patch("backend.agents.architect.get_llm") as mock_get_llm:
        mock_llm_inst = MagicMock()
        mock_llm_inst.invoke.return_value = mock_llm_response
        mock_get_llm.return_value = mock_llm_inst

        res = architect_agent(state)

    # Invariant preservation memastikan antarmuka yang terbukti (CardMetric) tidak terhapus
    aligned = res["contract"]
    assert len(aligned["interface_contracts"]) >= 1
    assert aligned["interface_contracts"][0]["identifier"] == "CardMetric"
    assert aligned["testable_assertions"][0]["target_symbol"] == "CardMetric"


def test_d_rejected_draft_interface_not_promoted_to_proven_invariant():
    """
    Test D: Rejected/Draft interface tidak dapat dipromosikan menjadi proven invariant.
    """
    # 1. Usulan kontrak yang ditolak (CardMetricWidget) bertentangan dengan Oracle (CardMetric)
    unproven = extract_proven_semantic_interfaces(
        [{"identifier": "CardMetricWidget", "interface_type": "WIDGET"}],
        str(ORACLE_FLUTTER_DIR),
        target_lang="dart"
    )
    # Harus kosong! Tidak boleh dipromosikan jadi proven!
    assert unproven == []

    # 2. Assembling B2 CEP untuk kontrak ditolak
    state = {
        "task": "Buat widget kartu metrik",
        "target_language": "dart",
        "frozen_oracle_path": str(ORACLE_FLUTTER_DIR),
        "contract_status": "REJECTED",
        "contract_sha256": None,
        "contract": {
            "status": "REJECTED",
            "provenance": {},
            "interface_contracts": [{"identifier": "CardMetricWidget", "interface_type": "WIDGET"}],
            "data_models": [],
        },
        "proven_semantic_interfaces": [],  # Belum ada yang proven
    }

    violations = [
        ViolationItem(
            violation_id="VIO-002",
            severity="CRITICAL",
            criterion="contract_oracle_consistency",
            location="contract",
            observed_state="Inconsistent with acceptance call-site",
            expected_state="Consistent with CardMetric",
            source_detector="ORACLE_CONSISTENCY_GATE",
        )
    ]

    cep = assemble_b2_evidence(state, violations, [], run_id="test_run", iteration=0)

    # Tidak ada invarian berkategori PROVEN_SEMANTIC_INVARIANT
    assert not any(inv.category == "PROVEN_SEMANTIC_INVARIANT" for inv in cep.preserved_invariants)

    # CardMetricWidget hanya tercatat sebagai UNPROVEN_DRAFT dengan provenance REJECTED_CONTRACT
    prop_ev = next((e for e in cep.evidence if e.get("item") == "proposed_contract_interfaces"), None)
    assert prop_ev is not None
    assert prop_ev["status"] == "UNPROVEN_DRAFT"
    assert prop_ev["provenance"] == "REJECTED_CONTRACT"


def test_e_semantic_invariant_revoked_on_deterministic_regression():
    """
    Test E: Jika evidence baru membuktikan semantic invariant salah, invariant dapat dicabut/ditandai REGRESSION secara deterministik.
    """
    # Invariant awal yang sempat dianggap proven
    inv = PreservedInvariant(
        invariant_id="INV-SEM-001",
        category="PROVEN_SEMANTIC_INVARIANT",
        description="Interface consistency for 'OldSymbol'",
        evidence_value="ORACLE_CONSISTENCY_CHECK:OldSymbol",
        status="PROVEN",
        target="OldSymbol",
        state="LOCKED",
        mutation="FORBIDDEN",
    )

    # Simulasi regresi saat evidence baru membuktikan antarmuka hilang/salah
    failure_data = {"type": "ORACLE_INCONSISTENCY", "observed": "OldSymbol not found in updated acceptance test"}
    inv.record_regression(failure_data, iteration=2)

    assert inv.status == "REGRESSED"
    assert inv.state == "VIOLATED"
    assert inv.ever_regressed is True
    assert inv.regression_count == 1
    assert inv.regression_evidence["failure_evidence"] == str(failure_data)

    # Gate V2 mendeteksi regresi semantik ini
    state = {
        "task": "Tugas umum",
        "target_language": "dart",
        "frozen_oracle_path": str(ORACLE_FLUTTER_DIR),
        "architecture_plan": "=== BLUEPRINT JSON ===\n{}\n=== END BLUEPRINT JSON ===",
        "contract": {
            "status": "REJECTED",
            "interface_contracts": [{"identifier": "DifferentSymbol", "interface_type": "WIDGET"}],
            "data_models": [],
        },
        "contract_status": "REJECTED",
        "contract_sha256": None,
        "contract_validation_errors": [],
        "proven_semantic_invariants": [inv],
    }

    result = validate_architect_phase(state)
    assert result["verdict"] == "FAIL"
    assert len(result["regressions"]) >= 1
    assert result["regressions"][0]["type"] == "SEMANTIC_REGRESSION"
    assert result["regressions"][0]["target"] == "OldSymbol"
    assert any(v["criterion"] == "semantic_invariant_regression" for v in result["violations"])


def test_f_generic_mechanism_has_no_task_specific_identifiers():
    """
    Test F: Mekanisme bersifat generic dan tidak mengandung identifier task-specific seperti `CardMetric`.
    """
    import inspect
    from backend.contract import extract_proven_semantic_interfaces
    from backend.context_assembler import assemble_b2_evidence

    # 1. Periksa kode sumber fungsi extract_proven_semantic_interfaces
    src_extract = inspect.getsource(extract_proven_semantic_interfaces)
    assert "CardMetric" not in src_extract
    assert "card_metric" not in src_extract

    # 2. Periksa blok preservasi di assemble_b2_evidence
    src_assemble = inspect.getsource(assemble_b2_evidence)
    # Tidak boleh ada hardcoding 'CardMetric' di dalam blok logika assemble_b2_evidence
    assert "CardMetric" not in src_assemble

    # 3. Uji dengan nama simbol sembarang / generik pada ekosistem Python
    from backend.contract import InterfaceContract
    test_ifaces = [
        InterfaceContract(
            interface_id="IFC-01",
            interface_type="FUNCTION",
            identifier="compute_quantum_tensor",
            target_file="main.py"
        )
    ]
    # Tanpa oracle path valid, fungsi harus mengembalikan [] secara aman tanpa crash
    res = extract_proven_semantic_interfaces(test_ifaces, "", target_lang="python")
    assert res == []


def test_g_prior_authority_state_regression_suite():
    """
    Test G: Regression test untuk authority-state fix sebelumnya tetap PASS.
    """
    import subprocess
    import sys

    res = subprocess.run(
        [sys.executable, "-m", "pytest", "backend/tests/test_b2_authority_state.py", "-q"],
        capture_output=True,
        text=True,
        cwd=str(Path.cwd()),
    )
    assert res.returncode == 0, f"test_b2_authority_state.py failed:\n{res.stdout}\n{res.stderr}"
    assert "6 passed" in res.stdout


def test_h_frozen_oracle_checksum_intact():
    """
    Test H: Oracle checksum tetap identik (4589e15cfb8f37ba70642e70623ca143bceee1a44175aefd072f441d9e8a9528).
    """
    assert ORACLE_TEST_FILE.exists(), f"Oracle test file missing: {ORACLE_TEST_FILE}"
    content = ORACLE_TEST_FILE.read_bytes()
    sha256 = hashlib.sha256(content).hexdigest()
    assert sha256 == EXPECTED_ORACLE_SHA, f"Frozen Oracle mutated! Expected {EXPECTED_ORACLE_SHA}, got {sha256}"
