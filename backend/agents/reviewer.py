import ast
import re
from typing import Tuple, Dict, Any, List
from langchain_core.messages import SystemMessage, HumanMessage

try:
    from ..state import SquadState
    from ..config import get_llm
    from ..tracer import get_tracer, compute_dict_hashes
    from ..contract import verify_contract_checkpoint
except (ImportError, ValueError):
    from state import SquadState
    from config import get_llm
    try:
        from tracer import get_tracer, compute_dict_hashes
    except ImportError:
        def get_tracer(run_id=None): return None
        def compute_dict_hashes(f): return {}
    from contract import verify_contract_checkpoint

REVIEWER_SYSTEM_PROMPT = """Anda adalah Principal Code Reviewer & Tech Lead dalam tim rekayasa perangkat lunak ReinDev Studio.
Tugas Anda adalah melakukan audit menyeluruh terhadap kode program yang telah ditulis oleh Developer dan diuji oleh QA Tester.

PRINSIP HIERARKI BUKTI REKAYASA & CALLER CONSISTENCY DOCTRINE (DOKTRIN #6):
1. TIER 1 (SUPREME GROUND TRUTH): FROZEN Acceptance Oracle (Unit Test / Test Suite) adalah otoritas penerimaan eksekutabel tertinggi. Jika seluruh tes Acceptance Oracle lulus 100%, fungsionalitas dan kontrak pemanggil telah terbukti valid secara deterministik.
2. TIER 2 (IMMUTABLE CONTRACT INVARIANTS): Invarian kontrak resmi berstatus FROZEN mutlak immutable (tidak boleh di-unfreeze atau dituntut diubah).
3. TIER 3 (DESIGN CONTEXT): Blueprint arsitektur adalah panduan perancangan awal (design context), BUKAN otoritas eksekutabel untuk menganulir bukti kelulusan Acceptance Oracle.
Reviewer DILARANG menolak implementasi yang telah lulus 100% Acceptance Oracle hanya karena berbeda dari detail blueprint awal yang tidak frozen.
Adaptasi simbol, konstruktor, atau parameter yang secara deterministik dituntut oleh pemanggil/Acceptance Oracle (misalnya parameter judul, metrik, warna, label) adalah kebutuhan teknis yang sah (Caller Consistency) dan WAJIB diterima selama tidak melanggar kontrak frozen.

Aspek yang WAJIB Anda audit:
1. Status Kelayakan (Keputusan tegas: [APPROVED] atau [NEEDS_REVISION])
2. Kepatuhan terhadap Spesifikasi dan Kontrak Resmi
3. Kebersihan dan Mutu Kode (Modularitas, Type Annotation, Ketiadaan Obrolan/Komentar Sampah)
4. Keamanan Dasar dan Penanganan Edge Cases
5. Saran Peningkatan & Pemeliharaan Jangka Panjang

Gunakan Bahasa Indonesia yang profesional, analitis, dan objektif.
"""

def scan_ast_symbols(code_files: dict, target_lang: str) -> Dict[str, List[str]]:
    """Memindai simbol kelas dan fungsi dari code_files."""
    symbols: Dict[str, List[str]] = {"classes": [], "functions": []}
    is_dart = "dart" in target_lang.lower() or "flutter" in target_lang.lower()
    
    for fname, content in code_files.items():
        if not is_dart and fname.endswith(".py"):
            try:
                tree = ast.parse(content, filename=fname)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        symbols["classes"].append(node.name)
                    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        symbols["functions"].append(node.name)
            except SyntaxError:
                pass
        elif is_dart:
            class_matches = re.findall(r"\bclass\s+([A-Za-z0-9_]+)", content)
            symbols["classes"].extend(class_matches)
            func_matches = re.findall(r"\b([A-Za-z0-9_]+)\s*\([^)]*\)\s*(?:async\s*)?\{", content)
            symbols["functions"].extend(func_matches)
            
    return symbols

def evaluate_deterministic_evidence_gate(state: SquadState) -> Tuple[bool, Dict[str, Any]]:
    """
    Mengevaluasi Gerbang Bukti Deterministik (Lapis 1).
    Mengembalikan (is_passed, gate_data).
    
    Pemeriksaan Deterministik:
    1. Integritas SHA-256 kontrak (jika ada).
    2. Hasil pengujian sandbox unit test (exit code == 0 / passed == True).
    3. Pemindaian struktural AST untuk simbol kontrak (data_models & interface_contracts).
    4. Kepatuhan constraints (max_files, forbidden patterns).
    5. Perhitungan Contract Compliance Rate (CCR).
    """
    errors: List[str] = []
    warnings: List[str] = []
    checks: Dict[str, Any] = {
        "contract_integrity": "N/A",
        "sandbox_execution": "N/A",
        "ast_structural": "N/A",
        "constraints": "N/A",
        "ccr": 0.0
    }
    
    contract = state.get("contract")
    code_files = state.get("code_files", {})
    test_results = state.get("test_results", {})
    target_lang = state.get("target_language", "python").strip()
    test_files = state.get("test_files", {})
    
    # 1. Contract Checkpoint Verification
    if contract:
        is_valid, err_msg = verify_contract_checkpoint(contract, "reviewer_pre_flight")
        if not is_valid:
            errors.append(f"Integritas SHA-256 kontrak gagal: {err_msg}")
            checks["contract_integrity"] = "FAILED"
        else:
            checks["contract_integrity"] = "PASSED"
    else:
        checks["contract_integrity"] = "SKIPPED (No Contract)"
        
    # 2. Sandbox Execution Check
    is_test_passed = bool(test_results.get("passed", False))
    if not is_test_passed:
        errors.append("Pengujian sandbox unit test gagal / exit code != 0.")
        checks["sandbox_execution"] = "FAILED"
    else:
        checks["sandbox_execution"] = "PASSED"
        
    # 3. AST Structural Check
    if contract:
        symbols = scan_ast_symbols(code_files, target_lang)
        all_symbols = set(symbols["classes"] + symbols["functions"])
        
        missing_models = []
        for dm in contract.get("data_models", []):
            mname = dm.get("model_name")
            if mname and mname not in all_symbols:
                missing_models.append(mname)
                
        missing_interfaces = []
        for iface in contract.get("interface_contracts", []):
            iname = iface.get("identifier")
            if not iname:
                continue
            if iname.isidentifier():
                if iname not in all_symbols:
                    missing_interfaces.append(iname)
            else:
                found = any(iname in c for c in code_files.values())
                if not found:
                    missing_interfaces.append(iname)
                
        if missing_models or missing_interfaces:
            missing_desc = []
            if missing_models:
                missing_desc.append(f"Data Models: {missing_models}")
            if missing_interfaces:
                missing_desc.append(f"Interfaces: {missing_interfaces}")
            errors.append(f"Simbol wajib kontrak tidak ditemukan di AST kode: {'; '.join(missing_desc)}")
            checks["ast_structural"] = "FAILED"
        else:
            checks["ast_structural"] = "PASSED"
    else:
        checks["ast_structural"] = "SKIPPED (No Contract)"
        
    # 4. Constraints Verification
    if contract and "constraints" in contract:
        constraints = contract.get("constraints", {})
        max_files = constraints.get("max_files")
        if max_files and len(code_files) > max_files:
            errors.append(f"Jumlah berkas ({len(code_files)}) melebihi batas constraint max_files ({max_files}).")
            checks["constraints"] = "FAILED"
        else:
            checks["constraints"] = "PASSED"
    else:
        checks["constraints"] = "SKIPPED (No Constraints)"
        
    # 5. Contract Assertion Coverage (CCR)
    if contract:
        assertions = contract.get("testable_assertions", [])
        total_ast = len(assertions)
        if total_ast > 0:
            if is_test_passed:
                traced_count = 0
                all_test_content = "\n".join(test_files.values())
                for ast_item in assertions:
                    aid = ast_item.get("assertion_id", "")
                    if aid and (f"# Test for: {aid}" in all_test_content or aid in all_test_content):
                        traced_count += 1
                if state.get("frozen_oracle_path"):
                    checks["ccr"] = 1.0
                elif traced_count > 0:
                    checks["ccr"] = round(traced_count / total_ast, 2)
                else:
                    checks["ccr"] = 1.0
            else:
                diag = state.get("diagnostic_evidence")
                failed_ast_ids = set()
                if diag and isinstance(diag, dict):
                    for ft in diag.get("failing_tests", []):
                        if ft.get("linked_assertion_id"):
                            failed_ast_ids.add(ft.get("linked_assertion_id"))
                passed_count = max(0, total_ast - len(failed_ast_ids))
                checks["ccr"] = round(passed_count / total_ast, 2)
        else:
            checks["ccr"] = 1.0 if is_test_passed else 0.0
    else:
        checks["ccr"] = 1.0 if is_test_passed else 0.0
        
    is_passed = (len(errors) == 0)
    gate_data = {
        "is_passed": is_passed,
        "errors": errors,
        "warnings": warnings,
        "checks": checks
    }
    return is_passed, gate_data

def reviewer_agent(state: SquadState) -> dict:
    llm = get_llm(role="reviewer", provider=state.get("provider"))
    
    specs = state.get("specifications", "")
    arch_plan = state.get("architecture_plan", "")
    code_files = state.get("code_files", {})
    test_results = state.get("test_results", {})
    contract = state.get("contract")
    
    # --- LAPIS 1: GERBANG BUKTI DETERMINISTIK ---
    is_gate_passed, gate_data = evaluate_deterministic_evidence_gate(state)
    
    l1_report = (
        "=== DETERMINISTIC EVIDENCE GATE (LAYER 1) ===\n"
        f"STATUS: {'[PASSED]' if is_gate_passed else '[FAILED]'}\n"
        f"- Contract Integrity: {gate_data['checks']['contract_integrity']}\n"
        f"- Sandbox Test Runner: {gate_data['checks']['sandbox_execution']}\n"
        f"- AST Structural Scan: {gate_data['checks']['ast_structural']}\n"
        f"- Constraint Verification: {gate_data['checks']['constraints']}\n"
        f"- Contract Compliance Rate (CCR): {int(gate_data['checks']['ccr'] * 100)}%\n"
        "AKSIOMA BATAS BUKTI (AXIOMS OF EVIDENCE LIMITS):\n"
        "1. AST presence != semantic compliance (Keberadaan simbol dalam AST tidak membuktikan kebenaran semantik logika).\n"
        "2. Test PASS != complete contract compliance (Kelulusan unit test tidak membuktikan kepatuhan 100% jika ada klausul tanpa uji).\n"
    )
    if not is_gate_passed:
        l1_report += "\nDetail Pelanggaran Gerbang Deterministik:\n"
        for err in gate_data["errors"]:
            l1_report += f"- {err}\n"
    
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

    if not is_gate_passed:
        audit_directive = f"""
[KONDISI PENGUJIAN: GERBANG BUKTI DETERMINISTIK (LAPIS 1) GAGAL PADA LOOP {iteration}/{max_iter}]
Gerbang bukti deterministik mesin mendeteksi kegagalan sandbox atau ketidakpatuhan struktural terhadap kontrak.

{l1_report}

INSTRUKSI WAJIB REVIEWER (STRICT):
1. Tetapkan STATUS KELAYAKAN TEGAS: [NEEDS_REVISION] (DILARANG memberi status [APPROVED]).
2. Berikan KESIMPULAN AUDIT & BUKTI KEGAGALAN (EVIDENCE):
   - Wajib kutip secara langsung potongan pesan galat / assertion failure / missing symbol di atas sebagai BUKTI OTENTIK.
   - Tunjukkan berkas spesifik dan baris kode yang menyebabkan kegagalan tersebut.
3. Berikan REKOMENDASI PERBAIKAN KONKRET:
   - Tunjukkan langkah teknis yang harus dilakukan untuk menyelesaikan masalah tersebut.
4. Tulis laporan Anda secara tuntas, padat, dan lengkap hingga kalimat penutup tanpa terpotong!"""
    else:
        audit_directive = f"""
[KONDISI PENGUJIAN: GERBANG BUKTI DETERMINISTIK (LAPIS 1) LULUS 100% PADA LOOP {iteration}/{max_iter}]
Seluruh automated unit tests telah lulus 100% dan seluruh simbol kontrak terverifikasi dalam AST.

{l1_report}

PEDOMAN EVALUASI & DOKTRIN KONSISTENSI PEMANGGIL (DOKTRIN #6):
- Acceptance Oracle yang telah lulus 100% membuktikan secara empiris bahwa pemanggil (caller) dan antarmuka kode selaras.
- DILARANG menolak kode atau menganggapnya sebagai pelanggaran kontrak jika adaptasi parameter/tipe diperlukan oleh Acceptance Oracle dan seluruh tes lulus. Blueprint adalah konteks desain awal, bukan dasar untuk menolak bukti eksekutabel.
- Jika kode bersih, modular, dan seluruh tes lulus, kode memenuhi syarat kelulusan.

LAKUKAN AUDIT LAPIS 2 (BOUNDED LLM REVIEW):
1. Evaluasi kepatuhan semantik terhadap spesifikasi produk dan kontrak resmi.
2. Periksa kebersihan kode, modularitas, penanganan edge cases, dan exception handling.
3. Jika kode memenuhi seluruh standar mutu dan lulus tes, tetapkan STATUS KELAYAKAN: [APPROVED].
4. Hanya jika ditemukan cacat kualitas struktural nyata, bug fatal, atau celah keamanan kritis, tetapkan STATUS KELAYAKAN: [NEEDS_REVISION].
5. Tulis laporan audit secara tuntas, padat, dan lengkap hingga kalimat penutup tanpa terpotong!"""

    contract_context = ""
    if contract:
        contract_context = f"\nKontrak Resmi (SHA-256: {contract.get('provenance', {}).get('contract_sha256', 'N/A')}):\nID: {contract.get('contract_id')}, Versi: {contract.get('contract_version')}\n"

    prompt = f"""Target Bahasa Pemrograman: {target_lang.upper()}
{guideline}
{contract_context}
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
    raw_review_notes = response.content if hasattr(response, "content") else str(response)
    
    # Enforce Deterministic Verdict Override
    if not is_gate_passed:
        is_approved = False
        review_status = "needs_revision"
        if "[APPROVED]" in raw_review_notes:
            raw_review_notes = raw_review_notes.replace("[APPROVED]", "[NEEDS_REVISION]")
    else:
        is_approved = ("[APPROVED]" in raw_review_notes or "APPROVED" in raw_review_notes) and "[NEEDS_REVISION]" not in raw_review_notes
        review_status = "completed" if is_approved else "needs_revision"
        
    final_review_notes = f"{l1_report}\n=== BOUNDED LLM REVIEW (LAYER 2) ===\n{raw_review_notes}"
    
    new_log = f"[Code Reviewer]: Audit kode selesai dilaksanakan ({len(final_review_notes)} karakter, status: {review_status.upper()})."
    current_logs = state.get("logs", [])
    
    # Observability Trace Logging
    tracer = get_tracer(state.get("run_id"))
    if tracer:
        tracer.log_event(
            stage="reviewer",
            event_type="output",
            iteration=iteration,
            data={
                "deterministic_gate": gate_data,
                "is_gate_passed": is_gate_passed,
                "input_code_files": code_files,
                "input_code_hashes": compute_dict_hashes(code_files),
                "input_test_files": state.get("test_files", {}),
                "input_test_results": test_results,
                "raw_review_notes": raw_review_notes,
                "final_review_notes": final_review_notes,
                "is_approved": is_approved,
                "review_status": review_status,
                "iteration": iteration
            }
        )

    return {
        "review_notes": final_review_notes,
        "status": review_status,
        "logs": current_logs + [new_log]
    }
