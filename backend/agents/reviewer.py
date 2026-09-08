from langchain_core.messages import SystemMessage, HumanMessage
try:
    from ..state import SquadState
    from ..config import get_llm
except (ImportError, ValueError):
    from state import SquadState
    from config import get_llm

REVIEWER_SYSTEM_PROMPT = """Anda adalah Principal Code Reviewer & Tech Lead dalam tim rekayasa perangkat lunak ReinDev Studio.
Tugas Anda adalah melakukan audit menyeluruh terhadap kode program yang telah ditulis oleh Developer dan diuji oleh QA Tester.

Aspek yang WAJIB Anda audit:
1. Status Kelayakan (Keputusan tegas: [APPROVED] atau [NEEDS_REVISION])
2. Kepatuhan terhadap Spesifikasi dan Rencana Arsitektur
3. Kebersihan dan Mutu Kode (Modularitas, Type Annotation, Ketiadaan Obrolan/Komentar Sampah)
4. Keamanan Dasar dan Penanganan Edge Cases
5. Saran Peningkatan & Pemeliharaan Jangka Panjang

Gunakan Bahasa Indonesia yang profesional, analitis, dan objektif.
"""

def reviewer_agent(state: SquadState) -> dict:
    llm = get_llm(role="reviewer", provider=state.get("provider"))
    
    specs = state.get("specifications", "")
    arch_plan = state.get("architecture_plan", "")
    code_files = state.get("code_files", {})
    test_results = state.get("test_results", {})
    
    code_summary = []
    for fname, content in code_files.items():
        code_summary.append(f"--- File: {fname} ---\n{content}\n")
    code_context = "\n".join(code_summary) if code_summary else "(Tidak ada kode)"
    
    test_summary = f"Passed: {test_results.get('passed')}, Total: {test_results.get('total')}, Output:\n{test_results.get('output', '')}"
    target_lang = state.get("target_language", "python").strip()
    is_dart = "dart" in target_lang.lower() or "flutter" in target_lang.lower()
    
    guideline = (
        "STANDAR AUDIT DART:\n"
        "- Periksa kepatuhan Effective Dart, Sound Null Safety, keterpisahan lib/ dan test/.\n"
        "- Pastikan tidak ada anti-pattern atau sisa kode Python."
        if is_dart else
        "STANDAR AUDIT PYTHON:\n"
        "- Periksa kepatuhan PEP 8, modularitas package, dan exception handling."
    )
    
    prompt = f"""Target Bahasa Pemrograman: {target_lang.upper()}
{guideline}

Spesifikasi Produk:
{specs}

Rencana Arsitektur:
{arch_plan}

Kode Program:
{code_context}

Hasil Pengujian Sandbox QA:
{test_summary}

Silakan lakukan audit komprehensif dan berikan laporan review resmi (maksimal 2 paragraf singkat, status [APPROVED])."""

    messages = [
        SystemMessage(content=REVIEWER_SYSTEM_PROMPT),
        HumanMessage(content=prompt)
    ]
    
    response = llm.invoke(messages)
    review_notes = response.content if hasattr(response, "content") else str(response)
    
    new_log = f"[Code Reviewer]: Audit kode selesai dilaksanakan ({len(review_notes)} karakter)."
    current_logs = state.get("logs", [])
    
    return {
        "review_notes": review_notes,
        "status": "completed",
        "logs": current_logs + [new_log]
    }
