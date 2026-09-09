from langchain_core.messages import SystemMessage, HumanMessage
try:
    from ..state import SquadState
    from ..config import get_llm
except (ImportError, ValueError):
    from state import SquadState
    from config import get_llm

ARCHITECT_SYSTEM_PROMPT = """Anda adalah Senior Software & System Architect dalam tim rekayasa perangkat lunak ReinDev Studio.
Tugas Anda adalah menerima spesifikasi dari Product Manager dan merancang struktur arsitektur perangkat lunak yang modular, terpisah dengan jelas (Separation of Concerns), dan mudah diuji.

Format luaran yang WAJIB Anda hasilkan:
1. Peta Struktur File Proyek (File Tree Structure) sesuai target bahasa pemrograman yang diminta
2. Tanggung Jawab Komponen / Modul
3. Kontrak Interface & Type Annotation (Nama fungsi, parameter, return type)
4. Panduan Implementasi untuk Developer Agent

Gunakan Bahasa Indonesia yang profesional, presisi, dan terstruktur tanpa kata-kata pengantar berlebih.
"""

def architect_agent(state: SquadState) -> dict:
    llm = get_llm(role="architect", provider=state.get("provider"))
    
    user_task = state.get("task", "")
    specs = state.get("specifications", "")
    target_lang = state.get("target_language", "python").strip()
    is_dart = "dart" in target_lang.lower() or "flutter" in target_lang.lower()
    
    structure_rule = (
        "ATURAN STRUKTUR PROYEK DART / FLUTTER (WAJIB):\n"
        "- Gunakan struktur modul tunggal kohesif: MAKSIMAL 1 file kode implementasi untuk Developer di lib/ (contoh: `lib/card_metric.dart`) dan 1 file test untuk QA Tester (`test/card_metric_test.dart`).\n"
        "- Gabungkan model data, provider Riverpod, dan Widget UI dalam 1 file `lib/card_metric.dart` untuk mencegah fragmentasi file dan kesalahan impor silang.\n"
        "- DILARANG merancang struktur banyak file yang terpisah-pisah untuk widget sederhana.\n"
        if is_dart else
        "ATURAN STRUKTUR PROYEK PYTHON (WAJIB):\n"
        "- Gunakan struktur modul Python sederhana dan kohesif: MAKSIMAL 1-2 file kode implementasi untuk Developer (misal: `main.py` atau `models.py` + `main.py`) dan 1 file test untuk QA Tester (`test_*.py`).\n"
        "- Untuk REST API FastAPI: gabungkan model Pydantic, in-memory store, dan routes dalam `main.py` (atau `models.py` dan `main.py`) untuk menghindari fragmentasi folder dan kesalahan impor silang.\n"
        "- DILARANG merancang hierarki folder yang terlalu dalam (hindari app/api/, app/schemas/, app/models/). Jaga struktur tetap datar di root.\n"
    )
    
    prompt = f"""TARGET BAHASA PEMROGRAMAN WAJIB: {target_lang.upper()}

{structure_rule}

Deskripsi Tugas Pengguna:
{user_task}

Spesifikasi Product Manager:
{specs}

ATURAN KETAT:
Seluruh file tree, hierarki modul, dan ekstensi file WAJIB menggunakan bahasa {target_lang.upper()} murni (Maksimal 2-3 file total).
DILARANG KERAS merancang file tree atau struktur dalam bahasa selain {target_lang.upper()}!

Tuliskan diagram struktur file tree dan kontrak interface secara SUPER RINGKAS tanpa basa-basi narasi."""

    messages = [
        SystemMessage(content=ARCHITECT_SYSTEM_PROMPT),
        HumanMessage(content=prompt)
    ]
    
    response = llm.invoke(messages)
    arch_plan = response.content if hasattr(response, "content") else str(response)
    
    new_log = f"[System Architect]: Rencana arsitektur dan struktur file tree ({target_lang.upper()}) selesai dirancang ({len(arch_plan)} karakter)."
    current_logs = state.get("logs", [])
    
    return {
        "architecture_plan": arch_plan,
        "status": "architect_done",
        "logs": current_logs + [new_log]
    }
