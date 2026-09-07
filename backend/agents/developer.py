import re
from langchain_core.messages import SystemMessage, HumanMessage
try:
    from ..state import SquadState
    from ..config import get_llm
except (ImportError, ValueError):
    from state import SquadState
    from config import get_llm

DEV_SYSTEM_PROMPT = """Anda adalah Senior Software Developer dalam tim rekayasa perangkat lunak ReinDev Studio.
Tugas Anda adalah menulis kode program berkualitas produksi berdasarkan spesifikasi dari Product Manager.

ATURAN REKAYASA & KEBERSIHAN KODE (STRICT):
1. DILARANG KERAS menyertakan teks obrolan, salam, basa-basi, atau penjelasan di luar kode. Output Anda harus 100% berupa definisi file kode murni.
2. Tulis kode yang lengkap, modular, dengan penanganan kesalahan dan type annotation.
3. JANGAN PERNAH menyertakan placeholder seperti '# TODO', '# implement later', atau '...'.
4. Format setiap file kode menggunakan blok penanda khusus persis seperti ini:
=== FILE: [nama_file] ===
[isi kode murni tanpa backtick markdown]
=== END FILE ===

Contoh:
=== FILE: calculator.py ===
def add(a: int, b: int) -> int:
    return a + b
=== END FILE ===
"""

def clean_code_content(code: str) -> str:
    """Membersihkan kode dari sisa-sisa markdown backticks atau teks pengantar yang bocor."""
    cleaned = code.strip()
    
    # Bersihkan pembungkus markdown ```python ... ``` jika model menyertakannya
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

def parse_code_blocks(text: str) -> dict:
    """Mengekstrak blok file kode dan membuang segala teks obrolan atau artefak percakapan."""
    files = {}
    
    # 1. Pola Utama: === FILE: filename === ... === END FILE ===
    pattern = r"=== FILE:\s*([\w\.\-/\\\\]+)\s*===\s*(.*?)\s*=== END FILE ==="
    matches = re.findall(pattern, text, re.DOTALL)
    
    for filename, content in matches:
        cleaned = clean_code_content(content)
        if cleaned:
            files[filename.strip()] = cleaned
            
    # 2. Fallback: jika model menggunakan format markdown ```python filename ...
    if not files:
        md_pattern = r"```(?:python|dart)?\s*(?:#|//)?\s*([\w\.\-/\\\\]+)?\n(.*?)\n```"
        md_matches = re.findall(md_pattern, text, re.DOTALL)
        for idx, (filename, content) in enumerate(md_matches):
            fname = filename.strip() if filename else f"module_{idx+1}.py"
            cleaned = clean_code_content(content)
            if cleaned:
                files[fname] = cleaned
                
    # 3. Ultimate fallback: jika output polos tanpa penanda, pastikan bukan teks obrolan
    if not files and text.strip():
        raw = clean_code_content(text)
        # Deteksi apakah teks ini kode program (memiliki import, def, class, return, dll.)
        code_indicators = ["def ", "class ", "import ", "from ", "void ", "int ", "return "]
        if any(ind in raw for ind in code_indicators):
            files["main.py"] = raw
            
    return files

def developer_agent(state: SquadState) -> dict:
    llm = get_llm(role="developer", provider=state.get("provider"))
    
    specs = state.get("specifications", "")
    user_task = state.get("task", "")
    iteration = state.get("iteration_count", 0)
    test_results = state.get("test_results", {})
    
    feedback_section = ""
    if iteration > 0 and test_results:
        output_err = test_results.get("output", "")
        feedback_section = f"\n\n[PERHATIAN - REVISI BUG DARI QA TESTER]:\nPengujian sebelumnya GAGAL dengan pesan error berikut:\n{output_err}\n\nPerbaiki kode Anda agar lolos dari error tersebut!"
        
    prompt = f"Tugas Pengguna:\n{user_task}\n\nSpesifikasi Product Manager:\n{specs}{feedback_section}\n\nSilakan tulis kode program lengkap sesuai format penanda === FILE: ... === tanpa teks obrolan apapun."
    
    messages = [
        SystemMessage(content=DEV_SYSTEM_PROMPT),
        HumanMessage(content=prompt)
    ]
    
    response = llm.invoke(messages)
    raw_output = response.content if hasattr(response, "content") else str(response)
    code_files = parse_code_blocks(raw_output)
    
    file_list_str = ", ".join(code_files.keys()) if code_files else "(tidak ada file)"
    new_log = f"[Developer]: Berhasil menghasilkan {len(code_files)} file kode bersih: {file_list_str}."
    current_logs = state.get("logs", [])
    
    return {
        "code_files": code_files,
        "status": "dev_done",
        "logs": current_logs + [new_log]
    }
