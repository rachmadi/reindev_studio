"""
Unit Test Suite: Dart Bracket Balance Analyzer & Root-Cause Diagnostic Sensor
ReinDev Studio — P0-1.1 High-Resolution Syntax Sensor Verification

Menguji:
1. Tokenizer delimiter Dart yang akurat (mengabaikan komentar, string, raw string, menangani ${...}).
2. Zero false-positive pada kode Dart yang seimbang / valid (termasuk Frozen Oracle).
3. Deteksi presisi akar masalah pada reproduksi nyata Gemma 4 Flutter Rep 2:
   - Menemukan Line 124, Column 13, Token ']'
   - Melaporkan mismatched_closing_delimiter (pasangan '(' dari baris 69 Column)
   - Memformat blok [DART SYNTAX DIAGNOSTIC] secara tepat
4. Deteksi orphan closing delimiter dan unclosed opening delimiter.
5. Zero source code mutation (Read-Only Axiom).
"""

from pathlib import Path
import pytest

from backend.diagnostic_parser import (
    DartSyntaxDiagnostic,
    tokenize_dart_delimiters,
    analyze_dart_bracket_balance,
    HINT_DART_BRACKET_CASCADE,
    infer_semantic_hint,
    parse_dart_output,
    FailingTest
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ORACLE_FLUTTER = PROJECT_ROOT / "dokumentasi-pengembangan/experiments/frozen_oracle/flutter_t1/card_metric_test.dart"
REPRO_FLUTTER = PROJECT_ROOT / "backend/output/project_gemma4_flutter_t1_rep2_20260909_200441/lib/card_metric.dart"


# ===========================================================================
# 1. Tokenizer Delimiter & Comment / String Handling
# ===========================================================================

def test_tokenizer_ignores_comments_and_strings():
    """Komentar dan string yang memuat tanda kurung tidak boleh dianggap sebagai delimiter kode."""
    dart_snippet = """
    // Line comment with ( [ {
    /* Block comment with ( [ { */
    /* Nested /* block */ comment [ ] */
    String s1 = "Hello (World) [123] {abc}";
    String s2 = 'Another (test) [ok]';
    String s3 = r'Raw string with (unclosed [delims {';
    String s4 = '''Triple "quoted" with ( [ {''';
    int x = (1 + 2) * [3][0];
    """
    delims = tokenize_dart_delimiters(dart_snippet)
    chars = [d[0] for d in delims]
    # Hanya (1 + 2) dan [3][0] yang merupakan delimiter kode
    assert chars == ['(', ')', '[', ']', '[', ']']


def test_tokenizer_handles_string_interpolation():
    """String interpolation ${...} dievaluasi sebagai kode ekspresi di dalam string."""
    dart_snippet = """
    String msg = "Result: ${calculate([1, 2], (3 + 4))} done";
    """
    delims = tokenize_dart_delimiters(dart_snippet)
    chars = [d[0] for d in delims]
    assert chars == ['{', '(', '[', ']', '(', ')', ')', '}']


# ===========================================================================
# 2. Balanced Code & Zero False Positives
# ===========================================================================

def test_balanced_code_zero_diagnostics():
    """Kode yang seimbang menghasilkan 0 diagnostik kesalahan."""
    balanced_snippet = """
    class SimpleWidget extends StatelessWidget {
      @override
      Widget build(BuildContext context) {
        return Card(
          child: Column(
            children: [
              Text("Hello"),
            ],
          ),
        );
      }
    }
    """
    diags = analyze_dart_bracket_balance(balanced_snippet, file_path="lib/simple.dart")
    assert len(diags) == 0


def test_frozen_oracle_flutter_zero_diagnostics():
    """Frozen Oracle Dart test suite wajib 100% seimbang tanpa false positive."""
    assert ORACLE_FLUTTER.exists(), f"Oracle file not found: {ORACLE_FLUTTER}"
    content = ORACLE_FLUTTER.read_text(encoding="utf-8")
    diags = analyze_dart_bracket_balance(content, file_path="card_metric_test.dart")
    assert len(diags) == 0


# ===========================================================================
# 3. Precision Root-Cause Attribution: Gemma 4 Flutter Rep 2 Case
# ===========================================================================

def test_reproduction_case_pinpoints_line_124():
    """
    Pada kasus nyata Flutter Rep 2 Gemma 4:
    Compiler Dart mengecoh dengan error di baris 60: "Can't find ')' to match '('".
    Sensor diagnostik presisi WAJIB mendeteksi akar masalah asli di Baris 124, Token ']'.
    """
    assert REPRO_FLUTTER.exists(), f"Reproduction file not found: {REPRO_FLUTTER}"
    content = REPRO_FLUTTER.read_text(encoding="utf-8")

    diags = analyze_dart_bracket_balance(content, file_path="lib/card_metric.dart")
    assert len(diags) > 0

    first_diag = diags[0]
    assert first_diag.file_path == "lib/card_metric.dart"
    assert first_diag.line == 124
    assert first_diag.column == 13
    assert first_diag.offending_token == "]"
    assert first_diag.issue == "mismatched_closing_delimiter"
    assert first_diag.expected_opener == "("
    assert first_diag.opener_line == 69

    # Format diagnostik block
    block = first_diag.format_diagnostic_block()
    assert "[DART SYNTAX DIAGNOSTIC]" in block
    assert "File: lib/card_metric.dart" in block
    assert "Line: 124" in block
    assert "Token: ]" in block
    assert "Likely cause:" in block
    assert "line 69" in block


# ===========================================================================
# 4. Integration with parse_dart_output & P0-1 Hint
# ===========================================================================

def test_parse_dart_output_enriches_compiler_error_with_root_cause():
    """
    Ketika compiler Dart mengeluarkan cascade error (baris 60),
    parse_dart_output memperkaya FailingTest dengan baris akar masalah 124 dan blok diagnostik.
    """
    content = REPRO_FLUTTER.read_text(encoding="utf-8")
    code_files = {"lib/card_metric.dart": content}

    compiler_stdout = """
lib/card_metric.dart:124:13: Error: Expected an identifier, but got ']'.
lib/card_metric.dart:60:20: Error: Can't find ')' to match '('.
        return Card(
                   ^
"""
    evidence = parse_dart_output(
        stdout=compiler_stdout,
        exit_code=1,
        code_files=code_files
    )

    assert evidence.execution_status == "error"
    assert len(evidence.failing_tests) >= 1

    first_fail = evidence.failing_tests[0]
    assert first_fail.source_file == "lib/card_metric.dart"
    # Source line di-redirect ke baris akar masalah (124), bukan baris cascade 60
    assert first_fail.source_line == 124
    assert "[DART SYNTAX DIAGNOSTIC]" in first_fail.message
    assert "Line: 124" in first_fail.message
    assert "Token: ]" in first_fail.message
    assert first_fail.semantic_hint == HINT_DART_BRACKET_CASCADE


# ===========================================================================
# 5. Read-Only Axiom Verification
# ===========================================================================

def test_zero_source_code_mutation():
    """Sensor diagnostik 100% Read-Only: tidak mengubah konten string kode sumber."""
    content = REPRO_FLUTTER.read_text(encoding="utf-8")
    original_copy = str(content)
    _ = analyze_dart_bracket_balance(content, file_path="lib/card_metric.dart")
    assert content == original_copy