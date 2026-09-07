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
    target_lang = state.get("target_language", "python").lower()
    
    prompt = f"""TARGET BAHASA PEMROGRAMAN WAJIB: {target_lang.upper()}

Deskripsi Tugas Pengguna:
{user_task}

Spesifikasi Product Manager:
{specs}

ATURAN KETAT:
Seluruh file tree, hierarki modul, dan ekstensi file WAJIB menggunakan bahasa {target_lang.upper()} (contoh: ekstensi file .py untuk Python, .dart untuk Dart).
DILARANG KERAS merancang file tree atau struktur dalam bahasa selain {target_lang.upper()}!

Silakan rancang rencana arsitektur perangkat lunak, struktur file tree, dan kontrak interface modular."""

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
