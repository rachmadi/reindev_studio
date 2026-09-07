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
Tugas Anda adalah merancang dan menulis automated test suite (menggunakan pytest untuk Python atau unit test untuk Dart) berdasarkan spesifikasi dari Product Manager dan kode yang telah ditulis oleh Developer.

ATURAN REKAYASA & KEBERSIHAN KODE (STRICT):
1. DILARANG KERAS menyertakan teks obrolan, salam, basa-basi, atau penjelasan di luar kode test.
2. Tulis test cases yang menguji kasus normal (happy path), kasus batas (boundary/edge cases), dan penanganan galat (error handling/exception).
3. Test suite HARUS dapat dieksekusi langsung oleh pytest tanpa syntax error atau missing imports.
4. Format setiap file test menggunakan blok penanda khusus persis seperti ini:
=== FILE: test_[nama_modul].py ===
[isi kode test murni tanpa backtick markdown]
=== END FILE ===

Contoh:
=== FILE: test_calculator.py ===
import pytest
from calculator import add

def test_add_positive():
    assert add(2, 3) == 5

def test_add_negative():
    assert add(-1, -1) == -2
=== END FILE ===
"""

def tester_agent(state: SquadState) -> dict:
    llm = get_llm(role="tester", provider=state.get("provider"))
    
    specs = state.get("specifications", "")
    code_files = state.get("code_files", {})
    target_lang = state.get("target_language", "python")
    
    # Format isi code_files agar QA dapat melihat implementasi yang akan diuji
    code_summary = []
    for fname, content in code_files.items():
        code_summary.append(f"--- File: {fname} ---\n{content}\n")
    code_context = "\n".join(code_summary) if code_summary else "(Belum ada file kode)"
    
    prompt = f"""Target Bahasa: {target_lang}

Spesifikasi & Kriteria Penerimaan:
{specs}

Kode Implementasi Developer:
{code_context}

Silakan tulis automated unit test suite lengkap menggunakan pytest dalam format penanda === FILE: test_... === tanpa teks obrolan apapun."""

    messages = [
        SystemMessage(content=TESTER_SYSTEM_PROMPT),
        HumanMessage(content=prompt)
    ]
    
    response = llm.invoke(messages)
    raw_output = response.content if hasattr(response, "content") else str(response)
    test_files = parse_code_blocks(raw_output)
    
    # Jika model tidak memberi awalan test_, pastikan nama file test diawali test_
    formatted_test_files = {}
    for fname, content in test_files.items():
        clean_name = fname
        if not clean_name.startswith("test_") and not clean_name.endswith("_test.dart"):
            clean_name = f"test_{clean_name}"
        formatted_test_files[clean_name] = content
        
    file_list_str = ", ".join(formatted_test_files.keys()) if formatted_test_files else "(tidak ada test file)"
    new_log = f"[QA Tester]: Berhasil menyusun {len(formatted_test_files)} file unit test: {file_list_str}."
    current_logs = state.get("logs", [])
    
    return {
        "test_files": formatted_test_files,
        "status": "tester_done",
        "logs": current_logs + [new_log]
    }
