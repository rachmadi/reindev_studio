import re
from langchain_core.messages import SystemMessage, HumanMessage
try:
    from ..state import SquadState
    from ..config import get_llm
    from .developer import clean_code_content, parse_code_blocks
    from ..tracer import get_tracer, compute_dict_hashes
    from ..contract import verify_contract_checkpoint
except (ImportError, ValueError):
    from state import SquadState
    from config import get_llm
    from agents.developer import clean_code_content, parse_code_blocks
    try:
        from tracer import get_tracer, compute_dict_hashes
    except ImportError:
        def get_tracer(run_id=None): return None
        def compute_dict_hashes(f): return {}
    from contract import verify_contract_checkpoint

TESTER_SYSTEM_PROMPT = """Anda adalah Senior QA & Test Engineer dalam tim rekayasa perangkat lunak ReinDev Studio.
Tugas Anda adalah merancang dan menulis automated test suite berdasarkan spesifikasi dari Product Manager dan kode yang telah ditulis oleh Developer.

ATURAN REKAYASA & KEBERSIHAN KODE (STRICT):
1. DILARANG KERAS menyertakan teks obrolan, salam, basa-basi, atau penjelasan di luar kode test.
2. Tulis test cases yang menguji kasus normal (happy path), kasus batas (boundary/edge cases), dan penanganan galat (error handling/exception).
3. Test suite HARUS dapat dieksekusi langsung oleh test runner target bahasa (dart test untuk Dart, pytest untuk Python).
4. Format setiap file test menggunakan blok penanda khusus persis seperti ini:
=== FILE: [nama_file_test] ===
[isi kode test murni tanpa backtick markdown]
=== END FILE ===

Contoh Python (pytest):
=== FILE: test_calculator.py ===
import pytest
from calculator import add

def test_add_positive():
    assert add(2, 3) == 5
=== END FILE ===

Contoh Dart (dart test):
=== FILE: test/calculator_test.dart ===
import 'package:test/test.dart';
import '../lib/calculator.dart';

void main() {
  group('Calculator Tests', () {
    test('addition returns correct sum', () {
      final calc = Calculator();
      expect(calc.add(2.0, 3.0), equals(5.0));
    });
  });
}
=== END FILE ===

Contoh Flutter Widget Test (flutter_test):
=== FILE: test/widget_test.dart ===
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../lib/metrics_card.dart';

void main() {
  testWidgets('renders widget properly', (WidgetTester tester) async {
    await tester.pumpWidget(
      ProviderScope(
        child: MaterialApp(
          home: Scaffold(
            body: MetricsCard(),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.byType(MetricsCard), findsOneWidget);
  });
}
=== END FILE ===
"""

def tester_agent(state: SquadState) -> dict:
    llm = get_llm(role="tester", provider=state.get("provider"))
    
    specs = state.get("specifications", "")
    code_files = state.get("code_files", {})
    target_lang = state.get("target_language", "python").strip()
    is_dart = "dart" in target_lang.lower() or "flutter" in target_lang.lower()
    
    # Contract Checkpoint & Grounding
    contract = state.get("contract")
    if contract:
        is_valid, err_msg = verify_contract_checkpoint(contract, "tester_pre_flight")
        if not is_valid:
            raise ValueError(f"Contract integrity violation at tester pre-flight: {err_msg}")

    # Format isi code_files agar QA dapat melihat implementasi yang akan diuji
    code_summary = []
    for fname, content in code_files.items():
        code_summary.append(f"--- File: {fname} ---\n{content}\n")
    code_context = "\n".join(code_summary) if code_summary else "(Belum ada file kode)"

    contract_section = ""
    if contract:
        assertions = contract.get("testable_assertions", [])
        contract_section = (
            "\n[KONTRAK RESMI & TESTABLE ASSERTIONS (SINGLE SOURCE OF TRUTH)]:\n"
            f"Contract ID: {contract.get('contract_id', 'UNKNOWN')} (v{contract.get('contract_version', '1.0.0')})\n"
            "DAFTAR TESTABLE ASSERTIONS YANG WAJIB DIUJI:\n"
        )
        for ast in assertions:
            outcome = ast.get("expected_outcome", {})
            contract_section += (
                f"- Assertion ID: {ast.get('assertion_id')}\n"
                f"  Linked Req: {ast.get('linked_req_id')} | Linked Interface: {ast.get('linked_interface_id')}\n"
                f"  Target Symbol: {ast.get('target_symbol')} | Test Type: {ast.get('test_type')}\n"
                f"  Inputs: {ast.get('inputs')}\n"
                f"  Expected Outcome ({outcome.get('outcome_type')}): {outcome.get('value')}\n"
                f"  Expected Status: {outcome.get('status_code')} | Exception: {outcome.get('exception_class')}\n"
                f"  Semantic Assertion: {ast.get('assertion')}\n"
            )
        contract_section += (
            "\nATURAN TRACEABILITY ASSERTION (WAJIB & STRICT):\n"
            "1. Untuk SETIAP test function / test case yang Anda buat, WAJIB sertakan komentar traceability persis:\n"
            "   # Test for: [ASSERTION_ID] (linked to [LINKED_REQ_ID])\n"
            "   Contoh: # Test for: AST-01 (linked to REQ-01)\n"
            "2. Anda HANYA boleh menguji assertion yang tercantum di atas. DILARANG mengarang kriteria di luar kontrak.\n"
        )
    
    test_instruction = (
        "ATURAN DART / FLUTTER TEST (WAJIB):\n"
        "- Buat HANYA 1 unit test case widget komprehensif yang menguji bahwa widget dirender dengan benar dalam ProviderScope (maksimal 30-40 baris)!\n"
        "- DILARANG membuat lebih dari 1 test case!\n"
        "- DILARANG melakukan mutasi state seperti 'provider.state = ...' di dalam test! Fokus murni pada verifikasi rendering widget dan keberadaan teks/komponen UI.\n"
        "- Gunakan format:\n"
        "  testWidgets('renders widget properly', (WidgetTester tester) async {\n"
        "    await tester.pumpWidget(ProviderScope(child: MaterialApp(home: Scaffold(body: MyWidget()))));\n"
        "    await tester.pumpAndSettle();\n"
        "    expect(find.byType(MyWidget), findsOneWidget);\n"
        "  });\n"
        "- Gunakan import relatif ke file implementasi di lib/, contoh: `import '../lib/card_metric.dart';`.\n"
        "- DILARANG menggunakan mockito, DILARANG membuat class Mock, DILARANG menggunakan when()!\n"
        "- Verifikasi menggunakan matcher Flutter standar (contoh: find.byType(...), findsOneWidget, find.text(...)).\n"
        "- Hindari mengakses properti internal style spesifik (seperti card.color atau card.elevation) secara rapuh.\n"
        "- Simpan di folder test/ dengan akhiran _test.dart (contoh: === FILE: test/card_metric_test.dart ===)."
        if is_dart else
        "ATURAN PYTHON TEST (WAJIB):\n"
        "- Gunakan framework pytest: `import pytest`\n"
        "- Uji fungsi-fungsi yang telah diimplementasikan oleh Developer di atas sesuai signature dan tipe datanya.\n"
        "- Untuk FastAPI: gunakan TestClient dari fastapi.testclient (`from fastapi.testclient import TestClient`, `client = TestClient(app)`). DILARANG menggunakan `app.test_client()` (itu sintaks Flask)!\n"
        "- Gunakan import absolut dari root modul (contoh: `from main import app`, `from services.product_service import ProductService`).\n"
        "- DILARANG KERAS menggunakan relative import bertitik ganda (`from ..main`) karena memicu ImportError pada pytest!\n"
        "- DILARANG mengimpor built-in exception (seperti ValueError, TypeError) dari modul Developer; built-in exception sudah otomatis tersedia secara global di Python.\n"
        "- DILARANG menguji string pesan error exception secara kaku dengan `assert str(exc_info.value) == '...'`; cukup pastikan exception terlempar (`pytest.raises(...)`). Untuk SystemExit, periksa `exc_info.value.code == 1`.\n"
        "- Validasi logika input test: Jika menguji exception galat dimensi matriks tidak kompatibel (misal perkalian matriks), pastikan dimensi benar-benar tidak kompatibel (misal cols(A) != rows(B)).\n"
        "- Untuk modul CLI/Matrix: uji fungsi dan method kalkulasi secara langsung (misal: matrix.add(), matrix.multiply(), parse_matrix()); hindari memanggil fungsi main() dengan argv langsung.\n"
        "- Simpan dengan nama file test_*.py di root direktori."
    )
    
    prompt = f"""Target Bahasa Pemrograman: {target_lang.upper()}

{test_instruction}
{contract_section}
Spesifikasi & Kriteria Penerimaan:
{specs}

Kode Implementasi Developer:
{code_context}

Silakan tulis automated unit test suite lengkap sesuai aturan di atas dalam format penanda === FILE: ... === tanpa teks obrolan apapun."""

    messages = [
        SystemMessage(content=TESTER_SYSTEM_PROMPT),
        HumanMessage(content=prompt)
    ]
    
    response = llm.invoke(messages)
    raw_output = response.content if hasattr(response, "content") else str(response)
    test_files = parse_code_blocks(raw_output, target_lang=target_lang)
    
    # Format nama file test
    formatted_test_files = {}
    for fname, content in test_files.items():
        clean_name = fname.strip()
        if is_dart:
            if not clean_name.startswith("test/"):
                clean_name = f"test/{clean_name}"
            if not clean_name.endswith("_test.dart"):
                if clean_name.endswith(".dart"):
                    clean_name = clean_name[:-5] + "_test.dart"
                else:
                    clean_name = f"{clean_name}_test.dart"
        else:
            if not clean_name.startswith("test_") and not clean_name.endswith("_test.py"):
                clean_name = f"test_{clean_name}"
        formatted_test_files[clean_name] = content
        
    file_list_str = ", ".join(formatted_test_files.keys()) if formatted_test_files else "(tidak ada test file)"
    new_log = f"[QA Tester]: Berhasil menyusun {len(formatted_test_files)} file unit test ({target_lang.upper()}): {file_list_str}."
    current_logs = state.get("logs", [])
    
    # Observability Trace Logging
    iteration = state.get("iteration_count", 0)
    tracer = get_tracer(state.get("run_id"))
    if tracer:
        tracer.log_event(
            stage="tester",
            event_type="output",
            iteration=iteration,
            data={
                "input_state": {
                    "target_language": target_lang,
                    "iteration": iteration,
                    "has_specifications": bool(specs),
                    "code_files_keys": list(code_files.keys()),
                    "contract_id": contract.get("contract_id") if contract else None,
                    "contract_sha256": contract.get("provenance", {}).get("contract_sha256") if contract else None
                },
                "raw_output": raw_output,
                "test_files": formatted_test_files,
                "test_files_hashes": compute_dict_hashes(formatted_test_files),
                "iteration": iteration
            }
        )

    return {
        "test_files": formatted_test_files,
        "status": "tester_done",
        "logs": current_logs + [new_log]
    }
