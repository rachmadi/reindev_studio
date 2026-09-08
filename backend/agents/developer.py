import re
from langchain_core.messages import SystemMessage, HumanMessage
try:
    from ..state import SquadState
    from ..config import get_llm
except (ImportError, ValueError):
    from state import SquadState
    from config import get_llm

DEV_SYSTEM_PROMPT = """Anda adalah Senior Software Developer dalam tim rekayasa perangkat lunak ReinDev Studio.
Tugas Anda adalah menulis kode program berkualitas produksi berdasarkan spesifikasi dari Product Manager dan rencana arsitektur dari System Architect.

ATURAN REKAYASA & KEBERSIHAN KODE (STRICT):
1. DILARANG KERAS menyertakan teks obrolan, salam, basa-basi, atau penjelasan di luar kode. Output Anda harus 100% berupa definisi file kode murni.
2. Tulis kode yang lengkap, modular, dengan penanganan kesalahan dan type annotation sesuai target bahasa pemrograman.
3. JANGAN PERNAH menyertakan placeholder seperti '# TODO', '# implement later', atau '...'.
4. Format setiap file kode menggunakan blok penanda khusus persis seperti ini:
=== FILE: [nama_file] ===
[isi kode murni tanpa backtick markdown]
=== END FILE ===

Contoh Python:
=== FILE: calculator.py ===
def add(a: int, b: int) -> int:
    return a + b
=== END FILE ===

Contoh Dart:
=== FILE: lib/calculator.dart ===
class Calculator {
  double add(double a, double b) => a + b;
  double multiply(double a, double b) => a * b;
}
=== END FILE ===
"""

def clean_code_content(code: str) -> str:
    """Membersihkan kode dari sisa-sisa markdown backticks atau teks pengantar yang bocor."""
    cleaned = code.strip()
    
    # Bersihkan pembungkus markdown ```python ... ``` atau ```dart ... ```
    if cleaned.startswith("```"):
        first_newline = cleaned.find("\n")
        if first_newline != -1:
            cleaned = cleaned[first_newline + 1:]
        else:
            cleaned = cleaned.lstrip("`")
            
    if cleaned.endswith("```"):
        last_fence = cleaned.rfind("```")
        cleaned = cleaned[:last_fence].rstrip()
        
    return cleaned.strip()

def parse_code_blocks(text: str, target_lang: str = "python") -> dict:
    """Mengekstrak blok file kode dan membuang segala teks obrolan atau artefak percakapan."""
    files = {}
    is_dart = "dart" in target_lang.lower() or "flutter" in target_lang.lower()
    
    # 1. Pola Utama: === FILE: filename === ... === END FILE ===
    pattern = r"=== FILE:\s*([\w\.\-/\\\\]+)\s*===\s*(.*?)\s*=== END FILE ==="
    matches = re.findall(pattern, text, re.DOTALL)
    
    for filename, content in matches:
        cleaned = clean_code_content(content)
        if cleaned:
            fname = filename.strip()
            # Standarisasi folder lib/ untuk file dart selain pubspec
            if is_dart and not fname.startswith("lib/") and not fname.startswith("test/") and fname.endswith(".dart"):
                fname = f"lib/{fname}"
            files[fname] = cleaned
            
    # 2. Fallback: jika model menggunakan format markdown ```python/dart filename ...
    if not files:
        md_pattern = r"```(?:python|dart)?\s*(?:#|//)?\s*([\w\.\-/\\\\]+)?\n(.*?)\n```"
        md_matches = re.findall(md_pattern, text, re.DOTALL)
        for idx, (filename, content) in enumerate(md_matches):
            ext = ".dart" if is_dart else ".py"
            prefix = "lib/" if is_dart else ""
            fname = filename.strip() if filename else f"{prefix}module_{idx+1}{ext}"
            if is_dart and not fname.startswith("lib/") and not fname.startswith("test/") and fname.endswith(".dart"):
                fname = f"lib/{fname}"
            cleaned = clean_code_content(content)
            if cleaned:
                files[fname] = cleaned
                
    # 3. Ultimate fallback: jika output polos tanpa penanda
    if not files and text.strip():
        raw = clean_code_content(text)
        code_indicators = ["def ", "class ", "import ", "from ", "void ", "int ", "double ", "return "]
        if any(ind in raw for ind in code_indicators):
            default_name = "lib/main.dart" if is_dart else "main.py"
            files[default_name] = raw
            
    return files

def developer_agent(state: SquadState) -> dict:
    llm = get_llm(role="developer", provider=state.get("provider"))
    
    specs = state.get("specifications", "")
    arch_plan = state.get("architecture_plan", "")
    user_task = state.get("task", "")
    target_lang = state.get("target_language", "python").strip()
    is_dart = "dart" in target_lang.lower() or "flutter" in target_lang.lower()
    iteration = state.get("iteration_count", 0)
    test_results = state.get("test_results", {})
    
    feedback_section = ""
    if iteration > 0 and test_results:
        output_err = test_results.get("output", "")
        feedback_section = f"\n\n[PERHATIAN - REVISI BUG DARI QA TESTER]:\nPengujian sebelumnya GAGAL dengan pesan error berikut:\n{output_err}\n\nPerbaiki kode Anda agar lolos dari error tersebut!"
        
    arch_section = f"\nRencana Arsitektur & File Tree:\n{arch_plan}\n" if arch_plan else ""
    
    lang_rule = (
        "ATURAN DART (WAJIB):\n"
        "- Tulis kode Dart murni dengan Sound Null Safety dan Strong Typing.\n"
        "- Simpan file implementasi dalam folder lib/ (contoh: === FILE: lib/calculator.dart ===).\n"
        "- DILARANG menggunakan sintaks Python (def, import pytest, snake_case function tanpa tipe data)."
        if is_dart else
        "ATURAN PYTHON (WAJIB):\n"
        "- Tulis kode Python PEP 8 modular dengan type hint.\n"
        "- Simpan file implementasi dengan ekstensi .py."
    )
    
    prompt = f"""TARGET BAHASA PEMROGRAMAN: {target_lang.upper()}

{lang_rule}

Tugas Pengguna:
{user_task}

Spesifikasi Product Manager:
{specs}
{arch_section}{feedback_section}

ATURAN KETAT:
Tulis seluruh implementasi file kode HANYA dalam bahasa {target_lang.upper()}.
Jangan gunakan bahasa pemrograman lain!

Silakan tulis kode program lengkap sesuai format penanda === FILE: ... === tanpa teks obrolan apapun."""
    
    messages = [
        SystemMessage(content=DEV_SYSTEM_PROMPT),
        HumanMessage(content=prompt)
    ]
    
    response = llm.invoke(messages)
    raw_output = response.content if hasattr(response, "content") else str(response)
    code_files = parse_code_blocks(raw_output, target_lang=target_lang)
    
    file_list_str = ", ".join(code_files.keys()) if code_files else "(tidak ada file)"
    new_log = f"[Developer]: Berhasil menghasilkan {len(code_files)} file kode bersih ({target_lang.upper()}): {file_list_str}."
    current_logs = state.get("logs", [])
    
    return {
        "code_files": code_files,
        "status": "dev_done",
        "logs": current_logs + [new_log]
    }
