"""
Unit Tests for Generic Dart & Flutter Diagnostic Harvester (Gate B5)
ReinDev Studio — Staged Causal Evidence (IA-Calibrated)

Memverifikasi kemampuan Gate B5 mengekstrak preskripsi diagnostik kausal secara
deterministik dari output kompilator Dart dan test runner Flutter:
1. Pure Non-Solver Principle: preskripsi hanya menyatakan fakta disparitas/inkompatibilitas (WHAT),
   tanpa mendikte alternatif solusi teknis (HOW).
2. Epistemic Attribution: attribution call-site HANYA disertakan jika terbukti secara faktual di test_files.
   Tidak mengarang atau melakukan fallback asumtif jika error terjadi pada implementasi atau sumber eksternal.
"""

import sys
from pathlib import Path

# Ensure backend is importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
try:
    from backend.context_assembler import (
        synthesize_b5_actionable_prescriptions,
        _extract_dart_callsite,
    )
    from backend.contextual_evidence import ViolationItem
except ImportError:
    from context_assembler import (
        synthesize_b5_actionable_prescriptions,
        _extract_dart_callsite,
    )
    from contextual_evidence import ViolationItem



@pytest.fixture
def mock_state():
    oracle_code = """import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../lib/card_metric.dart';

void main() {
  testWidgets('renders CardMetric with Material 3 Card and Riverpod state', (WidgetTester tester) async {
    await tester.pumpWidget(
      ProviderScope(
        child: MaterialApp(
          theme: ThemeData(useMaterial3: true),
          home: Scaffold(
            body: CardMetric(
              data: MetricData(title: 'Revenue', value: '1000', color: Colors.blue),
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
  });
}
"""
    return {
        "test_files": {"test/card_metric_test.dart": oracle_code},
        "code_files": {"lib/card_metric.dart": "// stub"},
        "target_language": "dart",
        "authoritative_target_file": "lib/card_metric.dart",
        "authoritative_models": ["MetricData"],
        "authoritative_interfaces": ["CardMetric"],
    }


def test_extract_dart_callsite_proven_oracle_callsite(mock_state):
    """Epistemic Attribution: Memverifikasi pemetaan call-site jika terbukti ada di test_files."""
    test_files = mock_state["test_files"]
    code_files = mock_state["code_files"]
    res = _extract_dart_callsite(test_files, "test/card_metric_test.dart", 14, code_files=code_files)
    assert "Oracle test call site at test/card_metric_test.dart:14" in res
    assert "data: MetricData(title: 'Revenue', value: '1000', color: Colors.blue)" in res


def test_extract_dart_callsite_implementation_site_no_false_attribution(mock_state):
    """Epistemic Attribution: Error pada implementasi TIDAK boleh mengarang fallback ke test_files."""
    test_files = mock_state["test_files"]
    code_files = mock_state["code_files"]
    res = _extract_dart_callsite(test_files, "lib/card_metric.dart", 8, code_files=code_files)
    assert "Implementation declaration at lib/card_metric.dart:8" in res
    assert "Oracle test call site" not in res


def test_extract_dart_callsite_unknown_location(mock_state):
    """Epistemic Attribution: Lokasi yang tidak terdaftar tidak boleh mengarang call site."""
    test_files = mock_state["test_files"]
    res = _extract_dart_callsite(test_files, "external_pkg/some_file.dart", 99)
    assert "unmapped to Oracle test files" in res
    assert "Oracle test call site" not in res


def test_dart_harvester_method_not_found_symbol(mock_state):
    """Memverifikasi ekstraksi Method not found: 'MetricData' menjadi RX-B5-DART-SYMBOL."""
    output = """
Compilation failed for testPath=D:/test/card_metric_test.dart: test/card_metric_test.dart:14:21: Error: Method not found: 'MetricData'.
              data: MetricData(title: 'Revenue', value: '1000', color: Colors.blue),
                    ^^^^^^^^^^
"""
    prescriptions = synthesize_b5_actionable_prescriptions(
        state=mock_state,
        violations=[],
        output=output,
        target_lang="dart",
        auth_file="lib/card_metric.dart",
    )

    assert len(prescriptions) >= 1
    rx = prescriptions[0]
    assert rx.prescription_id.startswith("RX-B5-DART-SYMBOL")
    assert "symbol 'MetricData' in 'lib/card_metric.dart'" in rx.implementation_symbol
    assert "Oracle test call site at test/card_metric_test.dart:14" in rx.oracle_call_site
    assert "MetricData" in rx.required_change
    assert "Do NOT modify Frozen Oracle test files" in rx.repair_boundary_forbidden


def test_dart_harvester_named_parameter_not_defined(mock_state):
    """Memverifikasi ekstraksi The named parameter 'data' isn't defined menjadi RX-B5-DART-PARAM."""
    output = """
test/card_metric_test.dart:14:15: Error: The named parameter 'data' isn't defined.
              data: MetricData(title: 'Revenue', value: '1000', color: Colors.blue),
              ^^^^
"""
    prescriptions = synthesize_b5_actionable_prescriptions(
        state=mock_state,
        violations=[],
        output=output,
        target_lang="dart",
        auth_file="lib/card_metric.dart",
    )

    assert len(prescriptions) >= 1
    rx = prescriptions[0]
    assert rx.prescription_id.startswith("RX-B5-DART-PARAM")
    assert "parameter 'data'" in rx.implementation_symbol
    assert "named parameter 'data'" in rx.required_change
    assert "Oracle test call site at test/card_metric_test.dart:14" in rx.oracle_call_site


def test_dart_harvester_null_safety_error_non_solver(mock_state):
    """Koreksi Wajib #1 IA: Memverifikasi preskripsi Sound Null Safety murni Non-Solver (tanpa daftar solusi)."""
    output = """
lib/card_metric.dart:8:15: Error: The parameter 'data' can't have a value of 'null' because of its type, but the implicit default value is 'null'.
  final MetricData data;
                   ^^^^
"""
    prescriptions = synthesize_b5_actionable_prescriptions(
        state=mock_state,
        violations=[],
        output=output,
        target_lang="dart",
        auth_file="lib/card_metric.dart",
    )

    assert len(prescriptions) >= 1
    rx = prescriptions[0]
    assert rx.prescription_id.startswith("RX-B5-DART-NULL-SAFETY")
    assert "parameter 'data'" in rx.implementation_symbol
    # Strict Non-Solver phrasing verification
    assert "Observed null-safety incompatibility: parameter 'data'" in rx.observed_failure
    assert "receives or permits a null value incompatible with its declared type" in rx.observed_failure
    assert "Observed null-safety incompatibility: parameter 'data' in 'lib/card_metric.dart' receives or permits a null value incompatible with its declared type" in rx.required_change
    # Verify it does NOT enumerate solver alternatives like 'required, default non-null, or nullable'
    assert "Declare 'data' as 'required'" not in rx.required_change
    assert "provide a non-null default value" not in rx.required_change
    # Epistemic Attribution: source file is in lib/, so not an Oracle test call site
    assert "Implementation declaration at lib/card_metric.dart:8" in rx.oracle_call_site


def test_dart_harvester_flutter_widget_assertion_failure(mock_state):
    """Memverifikasi penangkapan kegagalan assertion widget tester Flutter."""
    output = """
══╡ EXCEPTION CAUGHT BY FLUTTER TEST FRAMEWORK ╞════════════════════════════════════════════════════
The following TestFailure was thrown running a test:
Expected: exactly one matching candidate
  Actual: _TypeWidgetFinder:<zero widgets with type "Card" (ignoring offstage widgets)>
   Which: means none were found but one was expected
════════════════════════════════════════════════════════════════════════════════════════════════════
"""
    prescriptions = synthesize_b5_actionable_prescriptions(
        state=mock_state,
        violations=[],
        output=output,
        target_lang="dart",
        auth_file="lib/card_metric.dart",
    )

    assert len(prescriptions) == 1
    rx = prescriptions[0]
    assert rx.prescription_id == "RX-B5-FLUTTER-WIDGET-ASSERTION"
    assert "exactly one matching candidate" in rx.observed_failure
    assert 'zero widgets with type "Card"' in rx.observed_failure


def test_dart_harvester_pure_non_solver_arbitrary_identifiers():
    """Non-Solver Invariant: Memverifikasi ekstraksi bekerja identik untuk simbol & parameter arbitrer sembarang."""
    arbitrary_state = {
        "test_files": {
            "test/order_widget_test.dart": "  Widget buildOrder() => OrderCard(order: UserOrder(id: 123));\n"
        },
        "code_files": {"lib/order_card.dart": "// code"},
        "target_language": "dart",
    }
    output = """
test/order_widget_test.dart:1:25: Error: Method not found: 'UserOrder'.
  Widget buildOrder() => OrderCard(order: UserOrder(id: 123));
                         ^^^^^^^^^
test/order_widget_test.dart:1:15: Error: The named parameter 'order' isn't defined.
"""
    prescriptions = synthesize_b5_actionable_prescriptions(
        state=arbitrary_state,
        violations=[],
        output=output,
        target_lang="dart",
        auth_file="lib/order_card.dart",
    )

    assert len(prescriptions) == 2
    sym_rx = next(p for p in prescriptions if "SYMBOL" in p.prescription_id)
    assert "symbol 'UserOrder' in 'lib/order_card.dart'" in sym_rx.implementation_symbol
    assert "Oracle test call site at test/order_widget_test.dart:1" in sym_rx.oracle_call_site

    param_rx = next(p for p in prescriptions if "PARAM" in p.prescription_id)
    assert "parameter 'order' on constructor/method" in param_rx.implementation_symbol
    assert "Oracle test call site at test/order_widget_test.dart:1" in param_rx.oracle_call_site


def test_dart_harvester_provenance_preserving_deduplication_internal_first(mock_state):
    """
    Koreksi Wajib IA (D-096): Memverifikasi bahwa ketika kesalahan simbol muncul terlebih dahulu
    pada deklarasi internal (lib/...) dan kemudian pada call-site acceptance test (test/...),
    deduplikasi TIDAK membuang bukti Oracle. Bukti Oracle call-site wajib dipreservasi
    dengan otoritas tertinggi ([AUTHORITATIVE ORACLE CALL-SITE]).
    """
    output = """
lib/card_metric.dart:4:5: Error: Undefined name 'CardMetric'.
final cardMetricProvider = Provider<CardMetric>((ref) => CardMetric());
^^^^^^^^^^
test/card_metric_test.dart:13:17: Error: Method not found: 'CardMetric'.
            body: CardMetric(
                  ^^^^^^^^^^
"""
    prescriptions = synthesize_b5_actionable_prescriptions(
        state=mock_state,
        violations=[],
        output=output,
        target_lang="dart",
        auth_file="lib/card_metric.dart",
    )

    assert len(prescriptions) == 1
    rx = prescriptions[0]
    assert "symbol 'CardMetric' in 'lib/card_metric.dart'" in rx.implementation_symbol

    # Provenance Preserved: Kedua call-site terpreservasi
    assert "[AUTHORITATIVE ORACLE CALL-SITE]" in rx.oracle_call_site
    assert "test/card_metric_test.dart:13" in rx.oracle_call_site
    assert "body: CardMetric(" in rx.oracle_call_site
    assert "[INTERNAL IMPLEMENTATION REFERENCE]" in rx.oracle_call_site
    assert "lib/card_metric.dart:4" in rx.oracle_call_site

    # Otoritas Hierarki: Authoritative Oracle call-site berada di urutan pertama / teratas
    oracle_idx = rx.oracle_call_site.index("[AUTHORITATIVE ORACLE CALL-SITE]")
    internal_idx = rx.oracle_call_site.index("[INTERNAL IMPLEMENTATION REFERENCE]")
    assert oracle_idx < internal_idx

    # Kontrak perbaikan wajib menuntut pemenuhan kebutuhan pemanggil acceptance test
    assert "Oracle test call site at test/card_metric_test.dart:13" in rx.required_change


def test_dart_harvester_provenance_preserving_deduplication_test_first(mock_state):
    """
    Koreksi Wajib IA (D-096): Memverifikasi urutan sebaliknya (test/... mendahului lib/...)
    tetap menghasilkan representasi preskripsi yang identik dengan Oracle call-site sebagai otoritas utama.
    """
    output = """
test/card_metric_test.dart:13:17: Error: Method not found: 'CardMetric'.
            body: CardMetric(
                  ^^^^^^^^^^
lib/card_metric.dart:4:5: Error: Undefined name 'CardMetric'.
final cardMetricProvider = Provider<CardMetric>((ref) => CardMetric());
^^^^^^^^^^
"""
    prescriptions = synthesize_b5_actionable_prescriptions(
        state=mock_state,
        violations=[],
        output=output,
        target_lang="dart",
        auth_file="lib/card_metric.dart",
    )

    assert len(prescriptions) == 1
    rx = prescriptions[0]
    assert "symbol 'CardMetric' in 'lib/card_metric.dart'" in rx.implementation_symbol

    # Provenance Preserved: Kedua call-site terpreservasi
    assert "[AUTHORITATIVE ORACLE CALL-SITE]" in rx.oracle_call_site
    assert "test/card_metric_test.dart:13" in rx.oracle_call_site
    assert "[INTERNAL IMPLEMENTATION REFERENCE]" in rx.oracle_call_site
    assert "lib/card_metric.dart:4" in rx.oracle_call_site

    oracle_idx = rx.oracle_call_site.index("[AUTHORITATIVE ORACLE CALL-SITE]")
    internal_idx = rx.oracle_call_site.index("[INTERNAL IMPLEMENTATION REFERENCE]")
    assert oracle_idx < internal_idx
    assert "Oracle test call site at test/card_metric_test.dart:13" in rx.required_change

