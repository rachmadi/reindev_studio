from langchain_core.messages import SystemMessage, HumanMessage
try:
    from ..state import SquadState
    from ..config import get_llm
except (ImportError, ValueError):
    from state import SquadState
    from config import get_llm

PM_SYSTEM_PROMPT = """Anda adalah Senior Software Product Manager dalam tim rekayasa perangkat lunak ReinDev Studio.
Tugas Anda adalah merumuskan spesifikasi teknis SUPER RINGKAS (Maksimal 100 kata total).

Format luaran WAJIB:
1. Ringkasan Sistem (1 kalimat)
2. User Stories (Maksimal 2 butir)
3. Acceptance Criteria (Maksimal 2 skenario konkret)

DILARANG KERAS menulis salam, pengantar, atau kesimpulan bertele-tele. Langsung tuliskan poin 1, 2, dan 3.
"""

def pm_agent(state: SquadState) -> dict:
    llm = get_llm(role="pm", provider=state.get("provider"))
    
    user_task = state.get("task", "")
    target_lang = state.get("target_language", "python").strip()
    is_dart = "dart" in target_lang.lower() or "flutter" in target_lang.lower()
    
    ecosystem_guidance = (
        "Target Ekosistem: DART / FLUTTER (Sound Null Safety, Strong Typing, pubspec.yaml, lib/ dan test/)\n"
        if is_dart else
        "Target Ekosistem: PYTHON (PEP 8, Type Hinting, pytest)"
    )
    
    prompt = f"""Target Bahasa Pemrograman: {target_lang.upper()}
{ecosystem_guidance}

Deskripsi Tugas Pengguna:
{user_task}

Tuliskan spesifikasi SUPER RINGKAS (maksimal 100 kata) sesuai format 1, 2, 3 tanpa basa-basi pembuka atau penutup."""

    messages = [
        SystemMessage(content=PM_SYSTEM_PROMPT),
        HumanMessage(content=prompt)
    ]
    
    response = llm.invoke(messages)
    specs = response.content if hasattr(response, "content") else str(response)
    
    new_log = f"[Product Manager]: Spesifikasi dan kriteria penerimaan ({target_lang.upper()}) berhasil dirumuskan ({len(specs)} karakter)."
    current_logs = state.get("logs", [])
    
    return {
        "specifications": specs,
        "status": "pm_done",
        "logs": current_logs + [new_log]
    }
