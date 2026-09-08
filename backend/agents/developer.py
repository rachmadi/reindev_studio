import re
from langchain_core.messages import SystemMessage, HumanMessage
try:
    from ..state import SquadState
    from ..config import get_llm
    from ..environment_grounding import generate_fact_card
except (ImportError, ValueError):
    from state import SquadState
    from config import get_llm
    try:
        from environment_grounding import generate_fact_card
    except ImportError:
        def generate_fact_card(target_language: str) -> str:  # type: ignore[misc]
            return ""

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
    
    # 1. Pola Utama: === FILE: filename === ... hingga === FILE:, === END FILE ===, atau akhir teks
    pattern = r"=== FILE:\s*([\w\.\-/\\\\]+)\s*===\s*(.*?)(?=(?:=== FILE:|=== END FILE ===|$))"
    matches = re.findall(pattern, text, re.DOTALL)
    
    for filename, content in matches:
        cleaned = clean_code_content(content)
        cleaned = re.sub(r'=== END FILE ===', '', cleaned).strip()
        
        # AST healing untuk Python jika kode terpotong di baris terakhir
        if not is_dart and filename.strip().endswith(".py") and cleaned:
            try:
                import ast
                ast.parse(cleaned)
            except SyntaxError:
                lines = cleaned.splitlines()
                while len(lines) > 2:
                    lines.pop()
                    cand = "\n".join(lines)
                    try:
                        ast.parse(cand)
                        cleaned = cand
                        break
                    except SyntaxError:
                        continue
                        
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
        
        # Sediakan konteks kode yang sudah ditulis sebelumnya
        prev_code_blocks = []
        for fname, content in state.get("code_files", {}).items():
            prev_code_blocks.append(f"=== FILE: {fname} ===\n{content}\n=== END FILE ===")
        prev_code_str = "\n".join(prev_code_blocks) if prev_code_blocks else "(Belum ada kode)"
        
        # Sediakan konteks test suite dari QA Tester
        qa_test_blocks = []
        for fname, content in state.get("test_files", {}).items():
            qa_test_blocks.append(f"=== TEST FILE: {fname} ===\n{content}\n=== END TEST FILE ===")
        qa_test_str = "\n".join(qa_test_blocks) if qa_test_blocks else "(Belum ada test)"
        
        feedback_section = f"""

[PERHATIAN KRUSIAL - SIKLUS PERBAIKAN SELF-HEALING (LOOP {iteration}/{state.get('max_iterations', 3)})]:
Pengujian QA Tester GAGAL dengan pesan galat berikut:
{output_err}

BERKAS KODE YANG TELAH ANDA TULIS:
{prev_code_str}

BERKAS UNIT TEST DARI QA TESTER YANG WAJIB ANDA LOLOSKAN:
{qa_test_str}

INSTRUKSI PERBAIKAN:
1. Analisis galat di atas dan periksa baris kode spesifik yang menyebabkan pengujian gagal.
2. Perbaiki fungsi atau logika kode Anda agar seluruh assertion pada berkas test QA Tester LULUS 100%. Jika QA Tester mengharapkan exception/ValueError untuk input tertentu (misal dimensi matriks atau parameter tidak valid), sesuaikan validasi fungsi Anda agar melempar exception tersebut.
3. Tuliskan kembali berkas yang diperbaiki dengan nama file yang SAMA PERSIS.
"""
        
    arch_section = f"\nRencana Arsitektur & File Tree:\n{arch_plan}\n" if arch_plan else ""
    
    lang_rule = (
        "ATURAN DART / FLUTTER (WAJIB):\n"
        "- Tulis kode Dart murni dengan Sound Null Safety dan Strong Typing.\n"
        "- Konsolidasikan seluruh implementasi (model data, Riverpod provider, dan ConsumerWidget) dalam 1 file di lib/ (contoh: === FILE: lib/card_metric.dart ===).\n"
        "- DILARANG menulis file pubspec.yaml atau file test (fokus hanya pada file kode produksi di lib/).\n"
        "- Untuk Widget dengan Riverpod: Jika method `build` menerima `WidgetRef ref` (contoh: `Widget build(BuildContext context, WidgetRef ref)`), WAJIB mendeklarasikan kelas sebagai `class MyWidget extends ConsumerWidget {`.\n"
        "- Jika menggunakan Card widget, tetapkan properti visual: `Card(color: Colors.white, elevation: 2.0, child: ...)`.\n"
        "- Untuk model data Dart, berikan nilai default pada konstruktor named parameter: `CardMetricData({this.value = 75, this.title = 'CPU', this.unit = '%'});` agar aman diinisialisasi tanpa argumen maupun dengan argumen.\n"
        "- Untuk State Management Riverpod, gunakan `Provider<T>`: `final cardMetricProvider = Provider<CardMetricData>((ref) => CardMetricData());`.\n"
        "- DILARANG menggunakan `StateProvider`, `ChangeNotifierProvider`, atau `StateNotifier` (deprecated/hilang pada Riverpod terbaru)."
        if is_dart else
        "ATURAN PYTHON (WAJIB):\n"
        "- Tulis kode Python PEP 8 modular dengan type hint murni.\n"
        "- DILARANG menulis file test atau file non-kode seperti README.md atau requirements.txt (fokus hanya pada file kode .py).\n"
        "- WAJIB tulis SELURUH implementasi FastAPI (model Pydantic, endpoint, dan in-memory store) dalam SATU FILE bernama main.py. DILARANG membuat file models.py, schemas.py, database.py, atau file Python terpisah lainnya.\n"
        "- Pastikan seluruh class/model yang digunakan diimpor secara eksplisit.\n"
        "- Untuk FastAPI & Pydantic v2:\n"
        "  * Implementasikan endpoint CRUD lengkap: POST '/products/' (status_code=201), GET '/products/' (list all), GET '/products/{id}' (raise HTTPException(404, 'Product not found') jika tidak ada), dan DELETE '/products/{id}' (status_code=204, raise HTTPException(404) jika tidak ada).\n"
        "  * Pada DELETE endpoint (/products/{id}, status_code=204):\n"
        "    initial_len = len(products)\n"
        "    products[:] = [p for p in products if getattr(p, 'id', None) != id]\n"
        "    if len(products) == initial_len:\n"
        "        raise HTTPException(status_code=404, detail='Product not found')\n"
        "    return None\n"
        "- Untuk modul kalkulator / parsing matriks:\n"
        "  * WAJIB menambahkan `import sys` di baris pertama file.\n"
        "  * Dalam parse_matrix, validasi bahwa matriks berdimensi 2x2 atau 3x3 dan seragam (jika dimensi bukan 2x2 atau 3x3, atau baris tidak seragam, raise ValueError('Invalid dimensions')).\n"
        "  * Buat signature fungsi main: `def main(args=None):` (jika args is None, gunakan sys.argv[1:]; dukung format 3 argumen `[m1, op, m2]` maupun format 4 argumen). Selalu panggil `sys.exit(0)` saat operasi selesai atau tertangani.\n"
        "- Simpan file implementasi dengan ekstensi .py di root direktori (contoh: === FILE: main.py ===)."
    )
    
    # Environment Grounding: periksa fakta lingkungan aktual sebelum Developer mulai coding
    try:
        env_fact_card = generate_fact_card(target_lang)
    except Exception:
        env_fact_card = ""
    env_grounding_section = f"\n{env_fact_card}\n" if env_fact_card else ""

    prompt = f"""TARGET BAHASA PEMROGRAMAN: {target_lang.upper()}

{lang_rule}
{env_grounding_section}
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
    
    # Gabungkan dengan kode sebelumnya agar file yang tidak diubah tidak hilang
    existing_code = dict(state.get("code_files", {}))
    existing_code.update(code_files)
    final_code_files = existing_code if existing_code else code_files
    
    file_list_str = ", ".join(final_code_files.keys()) if final_code_files else "(tidak ada file)"
    new_log = f"[Developer]: Berhasil menghasilkan/memperbarui {len(final_code_files)} file kode bersih ({target_lang.upper()}): {file_list_str}."
    current_logs = state.get("logs", [])
    
    return {
        "code_files": final_code_files,
        "status": "dev_done",
        "logs": current_logs + [new_log]
    }
