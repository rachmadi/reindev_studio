from langchain_core.messages import SystemMessage, HumanMessage
try:
    from ..state import SquadState
    from ..config import get_llm
except (ImportError, ValueError):
    from state import SquadState
    from config import get_llm

PM_SYSTEM_PROMPT = """Anda adalah Senior Software Product Manager dalam tim rekayasa perangkat lunak ReinDev Studio.
Tugas Anda adalah menerima deskripsi intensi/tugas pengguna dan menguraikannya menjadi spesifikasi teknis yang jelas, ringkas, dan dapat diuji.

Format luaran yang WAJIB Anda hasilkan:
1. Ringkasan Tujuan Sistem (System Overview)
2. User Stories (Format: Sebagai [aktor], saya ingin [aksi], sehingga [manfaat])
3. Batasan Teknis dan Kebutuhan Fungsional
4. Kriteria Penerimaan (Acceptance Criteria dengan skenario pengujian konkret)

Gunakan Bahasa Indonesia yang profesional, lugas, dan terstruktur tanpa kata-kata pengantar berlebih.
"""

def pm_agent(state: SquadState) -> dict:
    llm = get_llm(role="pm", provider=state.get("provider"))
    
    user_task = state.get("task", "")
    messages = [
        SystemMessage(content=PM_SYSTEM_PROMPT),
        HumanMessage(content=f"Deskripsi Tugas dari Pengguna:\n{user_task}\n\nSilakan buat spesifikasi teknis dan kriteria penerimaan lengkap.")
    ]
    
    response = llm.invoke(messages)
    specs = response.content if hasattr(response, "content") else str(response)
    
    new_log = f"[Product Manager]: Spesifikasi dan kriteria penerimaan berhasil dirumuskan ({len(specs)} karakter)."
    current_logs = state.get("logs", [])
    
    return {
        "specifications": specs,
        "status": "pm_done",
        "logs": current_logs + [new_log]
    }
