from langchain_core.messages import SystemMessage, HumanMessage
try:
    from ..state import SquadState
    from ..config import get_llm
    from ..tracer import get_tracer, compute_dict_hashes
except (ImportError, ValueError):
    from state import SquadState
    from config import get_llm
    try:
        from tracer import get_tracer, compute_dict_hashes
    except ImportError:
        def get_tracer(run_id=None): return None
        def compute_dict_hashes(f): return {}

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
        "STANDAR AUDIT DART / FLUTTER:\n"
        "- Periksa kepatuhan Effective Dart, Sound Null Safety, kelengkapan provider, dan keterpisahan lib/ dan test/.\n"
        "- Lakukan audit hanya terhadap kode aktual yang ada tanpa menyebut bahasa pemrograman lain."
        if is_dart else
        "STANDAR AUDIT PYTHON:\n"
        "- Periksa kepatuhan PEP 8, modularitas package, dan exception handling."
    )
    
    iteration = state.get("iteration_count", 0)
    max_iter = state.get("max_iterations", 3)
    is_test_passed = bool(test_results.get("passed", False))

    if not is_test_passed:
        audit_directive = f"""
[KONDISI PENGUJIAN: GAGAL PADA LOOP {iteration}/{max_iter} (BATAS MAKSIMUM SELF-HEALING TERCAPAI)]
Siklus perbaikan otomatis telah mencapai batas maksimum ({iteration}/{max_iter} loop), namun pengujian sandbox masih melaporkan kegagalan assertion / kompilasi.

INSTRUKSI WAJIB REVIEWER (STRICT):
1. Tetapkan STATUS KELAYAKAN TEGAS: [NEEDS_REVISION] (DILARANG memberi status [APPROVED]).
2. Berikan KESIMPULAN AUDIT & BUKTI KEGAGALAN (EVIDENCE):
   - Wajib kutip secara langsung potongan pesan galat / assertion failure / compilation error dari 'Hasil Pengujian Sandbox QA' di atas sebagai BUKTI OTENTIK.
   - Tunjukkan berkas spesifik dan baris kode yang menyebabkan kegagalan tersebut.
3. Berikan REKOMENDASI PERBAIKAN KONKRET:
   - Tunjukkan langkah teknis yang harus dilakukan untuk menyelesaikan masalah tersebut.
4. Tulis laporan Anda secara tuntas, padat, dan lengkap hingga kalimat penutup tanpa terpotong!"""
    else:
        audit_directive = f"""
[KONDISI PENGUJIAN: SUKSES PADA LOOP {iteration}/{max_iter}]
Seluruh automated unit tests telah lulus 100%.

INSTRUKSI WAJIB REVIEWER:
1. Periksa kepatuhan terhadap spesifikasi dan kualitas arsitektur kode.
2. Jika kode memenuhi standar kualitas, tetapkan STATUS KELAYAKAN: [APPROVED].
3. Tulis laporan audit secara tuntas, padat, dan lengkap hingga kalimat penutup tanpa terpotong!"""

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

{audit_directive}"""

    messages = [
        SystemMessage(content=REVIEWER_SYSTEM_PROMPT),
        HumanMessage(content=prompt)
    ]
    
    response = llm.invoke(messages)
    review_notes = response.content if hasattr(response, "content") else str(response)
    
    new_log = f"[Code Reviewer]: Audit kode selesai dilaksanakan ({len(review_notes)} karakter)."
    current_logs = state.get("logs", [])
    
    is_approved = ("[APPROVED]" in review_notes or "APPROVED" in review_notes) and "[NEEDS_REVISION]" not in review_notes
    review_status = "completed" if is_approved else "needs_revision"
    
    # Observability Trace Logging
    iteration = state.get("iteration_count", 0)
    tracer = get_tracer(state.get("run_id"))
    if tracer:
        tracer.log_event(
            stage="reviewer",
            event_type="output",
            iteration=iteration,
            data={
                "input_code_files": code_files,
                "input_code_hashes": compute_dict_hashes(code_files),
                "input_test_files": state.get("test_files", {}),
                "input_test_results": test_results,
                "raw_review_notes": review_notes,
                "is_approved": is_approved,
                "review_status": review_status,
                "iteration": iteration
            }
        )

    return {
        "review_notes": review_notes,
        "status": review_status,
        "logs": current_logs + [new_log]
    }
