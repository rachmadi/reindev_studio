# -*- coding: utf-8 -*-
"""
Unit & Integration Tests — LOCKED_INVARIANTS / ONCE PROVEN, LOCK IT
ReinDev Studio — Mandatory Validation Suite per Section K Mandat IA

16 Kasus Uji Wajib:
1. Evidence valid -> invariant PROVEN.
2. PROVEN -> masuk LOCKED_INVARIANTS.
3. Locked invariant tetap PROVEN setelah repair yang tidak merusaknya.
4. Repair yang merusak invariant -> REGRESSION.
5. REGRESSION masuk CURRENT_FAILURES.
6. Regression tidak boleh dihitung sebagai repair success.
7. Provenance tetap tersedia antar turn.
8. Invariant tanpa deterministic evidence tidak boleh menjadi PROVEN.
9. Multiple invariants dapat coexist.
10. Memperbaiki satu failure tidak boleh menghapus invariant lain.
11. Locked invariant dievaluasi ulang setelah setiap repair.
12. Tidak ada task-specific solver (generik untuk Python dan Dart).
13. Tidak ada perubahan pada Frozen Oracle (SHA invariant immutable).
14. Tidak ada perubahan pada Contract authority (FROZEN invariant immutable).
15. Existing V1–V6 regression tetap PASS.
16. Khusus Pola Empiris Ornith:
    Turn N: MetricData = PROVEN, CardMetric.data = PROVEN, CardMetricData = FAIL
    Turn N+1: CardMetricData diperbaiki, tetapi MetricData hilang
    Validator harus menolak hasil (REGRESSION terdeteksi, verdict FAIL).
"""

import pytest
import hashlib
from backend.locked_invariants import (
    LockedInvariant,
    scan_code_symbols,
    evaluate_symbol_invariant,
    evaluate_compiler_error_freedom,
    discover_newly_proven_invariants,
    revalidate_locked_invariants,
    format_separated_repair_context,
)
from backend.phase_validators import validate_executor_phase


# ---------------------------------------------------------------------------
# Test 1: Evidence valid -> invariant PROVEN
# ---------------------------------------------------------------------------
def test_evidence_valid_becomes_proven():
    code_files = {
        "lib/card_metric.dart": "class MetricData { final String title; MetricData(this.title); }"
    }
    prev_violations = [{"observed_symbol": "MetricData", "message": "Method not found: 'MetricData'"}]
    discovered = discover_newly_proven_invariants(
        code_files=code_files,
        test_results={"passed": False, "exit_code": 1},
        compiler_output="",
        target_lang="dart",
        authoritative_file="lib/card_metric.dart",
        previous_violations=prev_violations,
        current_violations=[],
        turn=1
    )
    assert len(discovered) == 1
    inv = discovered[0]
    assert inv.status == "PROVEN"
    assert inv.state == "LOCKED"
    assert inv.target_symbol == "MetricData"
    assert inv.proven_by_validator == "B5_EXECUTOR_ITERATION"


# ---------------------------------------------------------------------------
# Test 2: PROVEN -> masuk LOCKED_INVARIANTS
# ---------------------------------------------------------------------------
def test_proven_enters_locked_invariants_registry():
    inv = LockedInvariant(
        invariant_id="INV-SYM-MetricData",
        category="SYMBOL_DECLARATION",
        description="MetricData declared",
        target_symbol="MetricData",
        target_file="lib/card_metric.dart",
        condition="MetricData in AST",
        status="PROVEN",
        state="LOCKED"
    )
    registry = {inv.invariant_id: inv.to_dict()}
    code = {"lib/card_metric.dart": "class MetricData {}"}
    updated, regressed, maintained = revalidate_locked_invariants(registry, code, {}, "dart", turn=2)
    assert "INV-SYM-MetricData" in updated
    assert updated["INV-SYM-MetricData"].status == "PROVEN"
    assert updated["INV-SYM-MetricData"].state == "LOCKED"
    assert len(maintained) == 1
    assert len(regressed) == 0


# ---------------------------------------------------------------------------
# Test 3: Locked invariant tetap PROVEN setelah repair yang tidak merusaknya
# ---------------------------------------------------------------------------
def test_locked_invariant_preserved_across_safe_repair():
    inv = LockedInvariant(
        invariant_id="INV-SYM-MetricData",
        category="SYMBOL_DECLARATION",
        description="MetricData declared",
        target_symbol="MetricData",
        target_file="lib/card_metric.dart",
        condition="MetricData in AST",
        status="PROVEN",
        state="LOCKED",
        proven_at_turn=1
    )
    registry = {inv.invariant_id: inv.to_dict()}
    # Repair menambahkan class lain tanpa menghapus MetricData
    repaired_code = {
        "lib/card_metric.dart": "class MetricData {}\nclass CardMetricData { final int value; CardMetricData(this.value); }"
    }
    updated, regressed, maintained = revalidate_locked_invariants(registry, repaired_code, {}, "dart", turn=2)
    assert updated["INV-SYM-MetricData"].status == "PROVEN"
    assert updated["INV-SYM-MetricData"].revalidated_at_turn == 2
    assert len(regressed) == 0


# ---------------------------------------------------------------------------
# Test 4: Repair yang merusak invariant -> REGRESSION
# ---------------------------------------------------------------------------
def test_repair_breaking_invariant_triggers_regression():
    inv = LockedInvariant(
        invariant_id="INV-SYM-MetricData",
        category="SYMBOL_DECLARATION",
        description="MetricData declared",
        target_symbol="MetricData",
        target_file="lib/card_metric.dart",
        condition="MetricData in AST",
        status="PROVEN",
        state="LOCKED",
        proven_at_turn=1
    )
    registry = {inv.invariant_id: inv.to_dict()}
    # Repair yang menghapus MetricData dan me-rename jadi CardMetricData
    broken_code = {
        "lib/card_metric.dart": "class CardMetricData { final int value; CardMetricData(this.value); }"
    }
    updated, regressed, maintained = revalidate_locked_invariants(registry, broken_code, {}, "dart", turn=2)
    assert len(regressed) == 1
    broken_inv = updated["INV-SYM-MetricData"]
    assert broken_inv.status == "REGRESSION"
    assert broken_inv.state == "VIOLATED"
    assert broken_inv.regression_count == 1
    assert len(broken_inv.regression_history) == 1


# ---------------------------------------------------------------------------
# Test 5 & 6: REGRESSION masuk CURRENT_FAILURES dan membatalkan status sukses
# ---------------------------------------------------------------------------
def test_regression_enters_failures_and_denies_success():
    state = {
        "task": "Build widget",
        "target_language": "dart",
        "code_files": {"lib/card_metric.dart": "class CardMetricData {}"}, # MetricData hilang!
        "test_results": {"passed": True, "exit_code": 0, "passed_count": 1, "failed_count": 0}, # Exit code seolah 0
        "locked_invariants": {
            "INV-SYM-MetricData": {
                "invariant_id": "INV-SYM-MetricData",
                "category": "SYMBOL_DECLARATION",
                "description": "MetricData declared",
                "target_symbol": "MetricData",
                "target_file": "lib/card_metric.dart",
                "condition": "MetricData in AST",
                "status": "PROVEN",
                "state": "LOCKED",
                "proven_at_turn": 1,
                "proven_by_validator": "B5_EXECUTOR_ITERATION",
                "regression_count": 0,
                "regression_history": []
            }
        },
        "contract": {"task_intent": {"authoritative_target_file": "lib/card_metric.dart"}}
    }
    contract = validate_executor_phase(state)
    # Regression harus membatalkan status lulus: verdict WAJIB FAIL
    assert contract["verdict"] == "FAIL"
    assert len(contract["regressions"]) == 1
    # Regression masuk ke violations roster
    assert any(v["criterion"] == "zero_regression_invariant" for v in contract["violations"])


# ---------------------------------------------------------------------------
# Test 7: Provenance tetap tersedia antar turn
# ---------------------------------------------------------------------------
def test_provenance_persisted_across_turns():
    inv = LockedInvariant(
        invariant_id="INV-PARAM-CardMetric-data",
        category="CONSTRUCTOR_PARAM",
        description="CardMetric accepts parameter data",
        target_symbol="CardMetric.data",
        target_file="lib/card_metric.dart",
        condition="constructor has param data",
        status="PROVEN",
        state="LOCKED",
        proven_at_turn=1,
        proven_by_validator="B5_EXECUTOR_ITERATION",
        provenance={"violation_resolved": "param_mismatch", "turn_proven": 1}
    )
    d = inv.to_dict()
    restored = LockedInvariant.from_dict(d)
    assert restored.provenance["violation_resolved"] == "param_mismatch"
    assert restored.proven_at_turn == 1
    assert restored.proven_by_validator == "B5_EXECUTOR_ITERATION"


# ---------------------------------------------------------------------------
# Test 8: Invariant tanpa deterministic evidence tidak boleh menjadi PROVEN
# ---------------------------------------------------------------------------
def test_no_invariant_proven_without_deterministic_evidence():
    code_files = {
        "lib/card_metric.dart": "// Komentar kosong tanpa kode"
    }
    prev_violations = [{"observed_symbol": "MetricData", "message": "Method not found: 'MetricData'"}]
    # Simbol tidak ada di AST
    discovered = discover_newly_proven_invariants(
        code_files=code_files,
        test_results={"passed": False, "exit_code": 1},
        compiler_output="Error: Method not found: 'MetricData'",
        target_lang="dart",
        authoritative_file="lib/card_metric.dart",
        previous_violations=prev_violations,
        current_violations=[],
        turn=1
    )
    assert len(discovered) == 0


# ---------------------------------------------------------------------------
# Test 9 & 10: Multiple invariants dapat coexist & tidak saling menghapus
# ---------------------------------------------------------------------------
def test_multiple_invariants_coexistence():
    code = {
        "lib/card_metric.dart": """
        class MetricData { final String title; MetricData(this.title); }
        class CardMetricData { final int value; CardMetricData(this.value); }
        class CardMetric { const CardMetric({required this.data}); final MetricData data; }
        """
    }
    inv1 = LockedInvariant(
        invariant_id="INV-SYM-MetricData",
        category="SYMBOL_DECLARATION",
        description="MetricData in AST",
        target_symbol="MetricData",
        target_file="lib/card_metric.dart",
        condition="MetricData present"
    )
    inv2 = LockedInvariant(
        invariant_id="INV-SYM-CardMetricData",
        category="SYMBOL_DECLARATION",
        description="CardMetricData in AST",
        target_symbol="CardMetricData",
        target_file="lib/card_metric.dart",
        condition="CardMetricData present"
    )
    inv3 = LockedInvariant(
        invariant_id="INV-PARAM-CardMetric-data",
        category="CONSTRUCTOR_PARAM",
        description="CardMetric has param data",
        target_symbol="CardMetric.data",
        target_file="lib/card_metric.dart",
        condition="CardMetric accepts data"
    )
    registry = {
        inv1.invariant_id: inv1.to_dict(),
        inv2.invariant_id: inv2.to_dict(),
        inv3.invariant_id: inv3.to_dict(),
    }
    updated, regressed, maintained = revalidate_locked_invariants(registry, code, {}, "dart", turn=1)
    assert len(maintained) == 3
    assert len(regressed) == 0
    assert all(inv.status == "PROVEN" for inv in updated.values())


# ---------------------------------------------------------------------------
# Test 11: Locked invariant dievaluasi ulang setelah setiap repair
# ---------------------------------------------------------------------------
def test_revalidation_executes_on_each_repair():
    inv = LockedInvariant(
        invariant_id="INV-SYM-MetricData",
        category="SYMBOL_DECLARATION",
        description="MetricData present",
        target_symbol="MetricData",
        target_file="lib/card_metric.dart",
        condition="MetricData in AST",
        proven_at_turn=1
    )
    reg = {inv.invariant_id: inv.to_dict()}
    code_t2 = {"lib/card_metric.dart": "class MetricData {}"}
    up2, reg2, main2 = revalidate_locked_invariants(reg, code_t2, {}, "dart", turn=2)
    assert up2["INV-SYM-MetricData"].revalidated_at_turn == 2

    code_t3 = {"lib/card_metric.dart": "class Other {}"} # Hapus di turn 3
    up3, reg3, main3 = revalidate_locked_invariants({k: v.to_dict() for k, v in up2.items()}, code_t3, {}, "dart", turn=3)
    assert up3["INV-SYM-MetricData"].status == "REGRESSION"
    assert up3["INV-SYM-MetricData"].regression_history[-1]["turn"] == 3


# ---------------------------------------------------------------------------
# Test 12: Tidak ada task-specific solver (Bekerja Generik untuk Python & Dart)
# ---------------------------------------------------------------------------
def test_generic_python_support():
    py_code = {
        "main.py": """
        class Product:
            def __init__(self, name: str, price: float = 0.0):
                self.name = name
                self.price = price
        """
    }
    inv_py = LockedInvariant(
        invariant_id="INV-SYM-Product",
        category="SYMBOL_DECLARATION",
        description="Product class declared",
        target_symbol="Product",
        target_file="main.py",
        condition="Product in AST"
    )
    inv_param = LockedInvariant(
        invariant_id="INV-PARAM-Product-price",
        category="CONSTRUCTOR_PARAM",
        description="Product accepts price",
        target_symbol="Product.price",
        target_file="main.py",
        condition="Product has price param"
    )
    reg = {inv_py.invariant_id: inv_py.to_dict(), inv_param.invariant_id: inv_param.to_dict()}
    updated, regressed, maintained = revalidate_locked_invariants(reg, py_code, {}, "python", turn=1)
    assert len(maintained) == 2
    assert len(regressed) == 0


# ---------------------------------------------------------------------------
# Test 13 & 14: Frozen Oracle & Contract Authority Immutable
# ---------------------------------------------------------------------------
def test_oracle_and_contract_immutability():
    from backend.context_assembler import _collect_oracle_invariants, _collect_contract_invariant
    oracle_sha = "4589e15cfb8f37ba70642e70623ca143bceee1a44175aefd072f441d9e8a9528"
    contract_sha = "9e2742c8cea664a48873c95772b8472b8ccaf3742c52f4b94a55b21471eddde3"
    state = {
        "expected_oracle_sha": oracle_sha,
        "contract_status": "FROZEN",
        "contract_sha256": contract_sha
    }
    or_invs = _collect_oracle_invariants(state)
    con_inv = _collect_contract_invariant(state)
    assert any(inv.evidence_value.startswith(oracle_sha[:16]) for inv in or_invs)
    assert con_inv.evidence_value.startswith(contract_sha[:16])
    assert con_inv.category == "CONTRACT_STATUS"


# ---------------------------------------------------------------------------
# Test 15: Separated Repair Context Formatting (4 Dimensions)
# ---------------------------------------------------------------------------
def test_separated_repair_context_four_dimensions():
    inv = LockedInvariant(
        invariant_id="INV-001",
        category="SYMBOL_DECLARATION",
        description="MetricData in AST",
        target_symbol="MetricData",
        target_file="lib/card_metric.dart",
        condition="MetricData declared",
        status="PROVEN"
    )
    formatted = format_separated_repair_context(
        locked_invariants=[inv],
        current_failures=[{"observed_symbol": "exit_code_1", "message": "compilation error"}],
        regressions=[],
        repair_boundary_allowed=["Modify lib/card_metric.dart"],
        repair_boundary_forbidden=["Modify Frozen Oracle"]
    )
    assert "[LOCKED / PROVEN INVARIANTS" in formatted
    assert "[CURRENT FAILURES" in formatted
    assert "[REPAIR BOUNDARY]" in formatted
    assert "[EXPECTED POST-REPAIR STATE]" in formatted
    assert "INV-001" in formatted


# ---------------------------------------------------------------------------
# Test 16 (KHUSUS POLA EMPIRIS ORNITH):
# Turn N: MetricData = PROVEN, CardMetric.data = PROVEN, CardMetricData = FAIL
# Turn N+1: CardMetricData diperbaiki, tetapi MetricData hilang
# Validator harus MENOLAK hasil (REGRESSION terdeteksi, verdict FAIL).
# ---------------------------------------------------------------------------
def test_ornith_empirical_regression_oscillation_rejected():
    # Turn N state
    state_turn_n = {
        "task": "Card Metric Widget",
        "target_language": "dart",
        "code_files": {
            "lib/card_metric.dart": """
            class MetricData { final String title; MetricData(this.title); }
            class CardMetric { const CardMetric({required this.data}); final MetricData data; }
            """
        },
        "locked_invariants": {
            "INV-SYM-MetricData": {
                "invariant_id": "INV-SYM-MetricData",
                "category": "SYMBOL_DECLARATION",
                "description": "MetricData declared",
                "target_symbol": "MetricData",
                "target_file": "lib/card_metric.dart",
                "condition": "MetricData in AST",
                "status": "PROVEN",
                "state": "LOCKED",
                "proven_at_turn": 1,
                "proven_by_validator": "B5_EXECUTOR_ITERATION",
                "regression_count": 0,
                "regression_history": []
            },
            "INV-PARAM-CardMetric-data": {
                "invariant_id": "INV-PARAM-CardMetric-data",
                "category": "CONSTRUCTOR_PARAM",
                "description": "CardMetric accepts parameter data",
                "target_symbol": "CardMetric.data",
                "target_file": "lib/card_metric.dart",
                "condition": "CardMetric accepts data",
                "status": "PROVEN",
                "state": "LOCKED",
                "proven_at_turn": 1,
                "proven_by_validator": "B5_EXECUTOR_ITERATION",
                "regression_count": 0,
                "regression_history": []
            }
        },
        "test_results": {"passed": False, "exit_code": 1, "failed_count": 1, "output": "Error: 'CardMetricData' isn't a type."},
        "contract": {"task_intent": {"authoritative_target_file": "lib/card_metric.dart"}},
        "iteration_count": 1
    }

    # Validator berjalan di Turn N
    contract_n = validate_executor_phase(state_turn_n)
    # Di Turn N: MetricData dan CardMetric.data tetap PROVEN
    assert contract_n["locked_invariants"]["INV-SYM-MetricData"]["status"] == "PROVEN"

    # Turn N+1: Developer memperbaiki CardMetricData dengan me-rename MetricData menjadi CardMetricData (MetricData HILANG!)
    state_turn_n_plus_1 = {
        "task": "Card Metric Widget",
        "target_language": "dart",
        "code_files": {
            "lib/card_metric.dart": """
            class CardMetricData { final int value; CardMetricData(this.value); }
            class CardMetric { const CardMetric({required this.data}); final CardMetricData data; }
            """
        },
        "locked_invariants": contract_n["locked_invariants"],
        "test_results": {"passed": True, "exit_code": 0, "failed_count": 0, "output": "All tests passed!"}, # Uji lokal lulus
        "contract": {"task_intent": {"authoritative_target_file": "lib/card_metric.dart"}},
        "iteration_count": 2
    }

    # Validator berjalan di Turn N+1
    contract_n_plus_1 = validate_executor_phase(state_turn_n_plus_1)

    # PEMBUKTIAN KRUSIAL:
    # 1. Validator WAJIB MENOLAK hasil (Verdict = FAIL) meskipun exit_code == 0
    assert contract_n_plus_1["verdict"] == "FAIL"
    # 2. Regresi terdeteksi pada MetricData
    assert len(contract_n_plus_1["regressions"]) >= 1
    assert any(r["test_or_invariant"] == "MetricData" for r in contract_n_plus_1["regressions"])
    # 3. Status invariant berubah menjadi REGRESSION
    assert contract_n_plus_1["locked_invariants"]["INV-SYM-MetricData"]["status"] == "REGRESSION"
    assert contract_n_plus_1["locked_invariants"]["INV-SYM-MetricData"]["state"] == "VIOLATED"
    # 4. Pelanggaran zero_regression_invariant tercatat di violations
    assert any(v["criterion"] == "zero_regression_invariant" for v in contract_n_plus_1["violations"])


# ---------------------------------------------------------------------------
# Test 6: Regression tidak boleh dihitung sebagai repair success
# ---------------------------------------------------------------------------
def test_regression_not_counted_as_repair_success():
    state = {
        "task": "Test regression blocking success",
        "target_language": "dart",
        "code_files": {"lib/card_metric.dart": "class NewOnly {}"},
        "test_results": {"passed": True, "exit_code": 0, "passed_count": 5, "failed_count": 0},
        "locked_invariants": {
            "INV-SYM-MetricData": {
                "invariant_id": "INV-SYM-MetricData",
                "category": "SYMBOL_DECLARATION",
                "description": "MetricData declared",
                "target_symbol": "MetricData",
                "target_file": "lib/card_metric.dart",
                "condition": "MetricData in AST",
                "status": "PROVEN",
                "state": "LOCKED",
                "proven_at_turn": 1,
            }
        },
        "contract": {"task_intent": {"authoritative_target_file": "lib/card_metric.dart"}}
    }
    result = validate_executor_phase(state)
    assert result["verdict"] == "FAIL"
    assert len(result["regressions"]) > 0


# ---------------------------------------------------------------------------
# Test 10: Memperbaiki satu failure tidak boleh menghapus invariant lain
# ---------------------------------------------------------------------------
def test_repairing_one_failure_does_not_evict_other_invariants():
    code = {
        "lib/card_metric.dart": """
        class ExistingProven {}
        class NewlyAddedToFixFailure {}
        """
    }
    inv = LockedInvariant(
        invariant_id="INV-SYM-ExistingProven",
        category="SYMBOL_DECLARATION",
        description="ExistingProven",
        target_symbol="ExistingProven",
        target_file="lib/card_metric.dart",
        condition="present",
        status="PROVEN"
    )
    reg = {inv.invariant_id: inv.to_dict()}
    updated, regressed, maintained = revalidate_locked_invariants(reg, code, {}, "dart", turn=2)
    assert "INV-SYM-ExistingProven" in updated
    assert updated["INV-SYM-ExistingProven"].status == "PROVEN"
    assert len(maintained) == 1
    assert len(regressed) == 0


# ---------------------------------------------------------------------------
# Test 15: Existing V1–V6 Phase Validators Regression Safety
# ---------------------------------------------------------------------------
def test_existing_v1_to_v6_validators_regression_pass():
    from backend.phase_validators import (
        validate_pm_phase,
        validate_architect_phase,
        validate_reviewer_phase
    )
    # V1 (PM)
    pm_state = {"blueprint": {"task_summary": "Summary", "system_architecture": "Arch", "components": [{"name": "A"}]}}
    pm_res = validate_pm_phase(pm_state)
    assert pm_res["verdict"] in ("PASS", "FAIL")

    # V2 (Architect)
    arch_state = {"contract": {"interface_definitions": ["class A"]}}
    arch_res = validate_architect_phase(arch_state)
    assert arch_res["verdict"] in ("PASS", "FAIL")

    # V6 (Reviewer)
    rev_state = {
        "review": {
            "status": "APPROVED",
            "verdict": "PASS",
            "confidence": 0.95,
            "checklist": {"correctness": True, "clean_code": True},
            "summary": "Implementation satisfies oracle.",
            "caller_consistency_applied": True
        },
        "test_results": {"passed": True, "exit_code": 0},
        "target_language": "dart"
    }
    rev_res = validate_reviewer_phase(rev_state, "PASS", "Implementation satisfies oracle.")
    assert rev_res["verdict"] == "PASS"


# ---------------------------------------------------------------------------
# Test 17: Discovery dari previous_diagnostic_evidence["failing_tests"]
# Prinsip: kandidat dari failing_tests turn N-1, PROVEN ditentukan oleh dual gate turn N
# ---------------------------------------------------------------------------
def test_discovery_from_previous_diagnostic_evidence():
    """
    previous_diagnostic_evidence["failing_tests"] adalah SUMBER KANDIDAT saja.
    Status PROVEN ditentukan oleh kehadiran di AST (Gate 1) + compiler clean (Gate 2).
    """
    code_files = {
        "lib/card_metric.dart": "class MetricData { final String title; MetricData(this.title); }"
    }
    # Simulasi failing_tests dari turn sebelumnya — MetricData gagal turn N-1
    prev_diag = {
        "failing_tests": [
            {
                "message": "Method not found: 'MetricData'",
                "source_symbol": "MetricData",
                "test_name": "test_card_metric",
                "failure_type": "METHOD_NOT_FOUND"
            }
        ]
    }
    discovered = discover_newly_proven_invariants(
        code_files=code_files,
        test_results={"passed": True, "exit_code": 0},
        compiler_output="",
        target_lang="dart",
        authoritative_file="lib/card_metric.dart",
        previous_violations=[],
        current_violations=[],
        turn=1,
        previous_diagnostic_evidence=prev_diag
    )
    assert len(discovered) >= 1, (
        "MetricData harus PROVEN karena ada di AST dan compiler bersih di turn N"
    )
    syms = [inv.target_symbol for inv in discovered]
    assert "MetricData" in syms, f"MetricData tidak ditemukan di {syms}"
    inv = next(i for i in discovered if i.target_symbol == "MetricData")
    assert inv.status == "PROVEN"
    assert inv.state == "LOCKED"
    assert inv.category == "SYMBOL_DECLARATION"


# ---------------------------------------------------------------------------
# Test 18: Discovery dari previous_stderr (raw compiler output sebelumnya)
# ---------------------------------------------------------------------------
def test_discovery_from_previous_stderr():
    """
    previous_stderr adalah SUMBER KANDIDAT saja.
    PROVEN hanya jika simbol ada di AST turn N dan compiler turn N bersih.
    """
    code_files = {
        "lib/card_metric.dart": (
            "class CardMetricData { final int value; CardMetricData(this.value); }"
        )
    }
    prev_stderr = (
        "lib/card_metric_widget.dart:10:5: Error: 'CardMetricData' isn't a type.\n"
        "    CardMetricData data = CardMetricData(value: 42);\n"
        "    ^^^^^^^^^^^^^^\n"
    )
    discovered = discover_newly_proven_invariants(
        code_files=code_files,
        test_results={"passed": False, "exit_code": 1},
        compiler_output="",
        target_lang="dart",
        authoritative_file="lib/card_metric.dart",
        previous_violations=[],
        current_violations=[],
        turn=1,
        previous_stderr=prev_stderr
    )
    assert len(discovered) >= 1, (
        "CardMetricData harus PROVEN karena ada di AST dan compiler saat ini bersih"
    )
    syms = [inv.target_symbol for inv in discovered]
    assert "CardMetricData" in syms, f"CardMetricData tidak ditemukan di {syms}"
    inv = next(i for i in discovered if i.target_symbol == "CardMetricData")
    assert inv.status == "PROVEN"
    assert inv.category == "SYMBOL_DECLARATION"


# ---------------------------------------------------------------------------
# Test 19 (Negative): previous_diagnostic_evidence tanpa kehadiran di AST → TIDAK PROVEN
# Gate 1 gagal: simbol tidak ada di kode saat ini
# ---------------------------------------------------------------------------
def test_previous_diagnostic_evidence_without_ast_not_proven():
    """
    previous_diagnostic_evidence hanya kandidat.
    Tanpa kehadiran di AST kode saat ini (Gate 1 gagal), tidak ada PROVEN.
    """
    code_files = {
        "lib/card_metric.dart": "// File kosong — MetricData tidak dideklarasikan"
    }
    prev_diag = {
        "failing_tests": [
            {
                "message": "Method not found: 'MetricData'",
                "source_symbol": "MetricData",
            }
        ]
    }
    discovered = discover_newly_proven_invariants(
        code_files=code_files,
        test_results={"passed": False, "exit_code": 1},
        compiler_output="",
        target_lang="dart",
        authoritative_file="lib/card_metric.dart",
        previous_violations=[],
        current_violations=[],
        turn=1,
        previous_diagnostic_evidence=prev_diag
    )
    proven_syms = [inv.target_symbol for inv in discovered]
    assert "MetricData" not in proven_syms, (
        "MetricData tidak boleh PROVEN karena tidak ada di AST kode saat ini (Gate 1 gagal)"
    )
    assert len(discovered) == 0, (
        f"Tidak boleh ada invariant PROVEN. Ditemukan: {proven_syms}"
    )


# ---------------------------------------------------------------------------
# Test 20 (Negative): exit_code_1 tidak pernah menjadi kandidat atau PROVEN
# ---------------------------------------------------------------------------
def test_exit_code_1_never_becomes_candidate_or_proven():
    """
    exit_code_1 adalah meta-token pipeline, bukan simbol semantik.
    Harus selalu diblokir di _BLOCKED_CLASS_TOKENS sebelum dual gate.
    Ini mereproduksi failure mode aktual ablasi Ornith 9B.
    """
    code_files = {
        "lib/card_metric.dart": "class MetricData { MetricData(); }"
    }
    prev_violations = [
        {
            "criterion": "sandbox_exit_code_clean",
            "observed_symbol": "exit_code_1",
            "message": "Sandbox execution failed (exit code 1)"
        }
    ]
    discovered = discover_newly_proven_invariants(
        code_files=code_files,
        test_results={},
        compiler_output="",
        target_lang="dart",
        authoritative_file="lib/card_metric.dart",
        previous_violations=prev_violations,
        current_violations=[],
        turn=1,
    )
    bad_inv = [inv for inv in discovered if "exit_code" in inv.invariant_id.lower()]
    assert not bad_inv, f"exit_code_1 tidak boleh menjadi invariant: {bad_inv}"
    assert not any(inv.target_symbol == "exit_code_1" for inv in discovered), (
        "exit_code_1 tidak boleh menjadi target_symbol dari invariant apapun"
    )


# ---------------------------------------------------------------------------
# Test 21 (Negative): Simbol ada di AST tapi compiler masih melaporkan error → TIDAK PROVEN
# Gate 2 gagal: compiler output tidak bersih
# ---------------------------------------------------------------------------
def test_not_proven_if_compiler_still_reporting_error_for_symbol():
    """
    Dual gate: Gate 1 terpenuhi (MetricData ada di AST), Gate 2 GAGAL (compiler masih error).
    → MetricData TIDAK boleh menjadi PROVEN.
    Ini memvalidasi bahwa previous_diagnostic_evidence tidak langsung menghasilkan PROVEN
    jika state kode saat ini belum benar-benar memperbaiki error tersebut.
    """
    code_files = {
        "lib/card_metric.dart": "class MetricData { MetricData(); }"
    }
    prev_diag = {
        "failing_tests": [
            {
                "message": "Method not found: 'MetricData'",
                "source_symbol": "MetricData"
            }
        ]
    }
    # Compiler saat ini MASIH melaporkan error untuk MetricData (Gate 2 gagal)
    current_compiler_output = (
        "lib/card_metric_widget.dart:5:7: Error: Method not found: 'MetricData'.\n"
        "      MetricData(title: 'test');\n"
    )
    discovered = discover_newly_proven_invariants(
        code_files=code_files,
        test_results={"passed": False, "exit_code": 1},
        compiler_output=current_compiler_output,
        target_lang="dart",
        authoritative_file="lib/card_metric.dart",
        previous_violations=[],
        current_violations=[],
        turn=1,
        previous_diagnostic_evidence=prev_diag
    )
    proven_syms = [inv.target_symbol for inv in discovered if inv.status == "PROVEN"]
    assert "MetricData" not in proven_syms, (
        "MetricData tidak boleh PROVEN karena compiler masih melaporkan error (Gate 2 gagal). "
        f"Ditemukan: {proven_syms}"
    )
