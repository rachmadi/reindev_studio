import re
from langchain_core.messages import SystemMessage, HumanMessage
try:
    from ..state import SquadState
    from ..config import get_llm
    from .developer import clean_code_content, parse_code_blocks
except (ImportError, ValueError):
    from state import SquadState
    from config import get_llm
    from agents.developer import clean_code_content, parse_code_blocks

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
"""

def tester_agent(state: SquadState) -> dict:
    llm = get_llm(role="tester", provider=state.get("provider"))
    
    specs = state.get("specifications", "")
    code_files = state.get("code_files", {})
    target_lang = state.get("target_language", "python").strip()
    is_dart = "dart" in target_lang.lower() or "flutter" in target_lang.lower()
    
    # Format isi code_files agar QA dapat melihat implementasi yang akan diuji
    code_summary = []
    for fname, content in code_files.items():
        code_summary.append(f"--- File: {fname} ---\n{content}\n")
    code_context = "\n".join(code_summary) if code_summary else "(Belum ada file kode)"
    
    test_instruction = (
        "ATURAN DART UNIT TEST (WAJIB):\n"
        "- Gunakan framework package:test: `import 'package:test/test.dart';`\n"
        "- Import file implementasi menggunakan relative import, contoh: `import '../lib/calculator.dart';`\n"
        "- Fungsi pengujian dalam `void main() { group('...', () { test('...', () { expect(actual, equals(expected)); }); }); }`\n"
        "- Simpan di folder test/ dengan akhiran _test.dart (contoh: === FILE: test/calculator_test.dart ===).\n"
        "- DILARANG KERAS menggunakan sintaks Python (pytest, def, assert, test_*.py)!"
        if is_dart else
        "ATURAN PYTHON TEST (WAJIB):\n"
        "- Gunakan framework pytest: `import pytest`\n"
        "- Simpan dengan nama file test_*.py."
    )
    
    prompt = f"""Target Bahasa Pemrograman: {target_lang.upper()}

{test_instruction}

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
    
    return {
        "test_files": formatted_test_files,
        "status": "tester_done",
        "logs": current_logs + [new_log]
    }
