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
        "ATURAN STRUKTUR PROYEK DART (WAJIB):\n"
        "Gunakan tata letak standar paket Dart:\n"
        "project/\n"
        "├── pubspec.yaml (konfigurasi nama proyek, sdk: '>=3.0.0 <4.0.0', dev_dependencies: test: ^1.24.0)\n"
        "├── lib/\n"
        "│   └── [nama_modul].dart (implementasi kode sumber Dart murni)\n"
        "└── test/\n"
        "    └── [nama_modul]_test.dart (test suite menggunakan package:test/test.dart)\n"
        "BATASAN JUMLAH BERKAS (WAJIB):\n"
        "Rancang MAKSIMAL 2 file kode produksi (lib/) dan 1 file tes (test/). DILARANG membuat lebih dari 3 file.\n"
        if is_dart else
        "ATURAN STRUKTUR PROYEK PYTHON (WAJIB):\n"
        "Gunakan tata letak modul Python modular (core/, services/, tests/test_*.py). Maksimal 2-3 file total.\n"
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
