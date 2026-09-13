import os
import copy
import json
import re
from langchain_core.messages import SystemMessage, HumanMessage
try:
    from ..state import SquadState
    from ..config import get_llm
    from ..environment_grounding import generate_fact_card
    from ..tracer import get_tracer, compute_sha256, compute_dict_hashes, compute_object_hash
    from ..contract import verify_contract_checkpoint, ContractIntegrityError
except (ImportError, ValueError):
    from state import SquadState
    from config import get_llm
    try:
        from environment_grounding import generate_fact_card
    except ImportError:
        def generate_fact_card(target_language: str, task: str = "") -> str:  # type: ignore[misc]
            return ""
    try:
        from tracer import get_tracer, compute_sha256, compute_dict_hashes, compute_object_hash
    except ImportError:
        def get_tracer(run_id=None): return None
        def compute_sha256(s): return ""
        def compute_dict_hashes(f): return {}
        def compute_object_hash(o): return ""
    try:
        from contract import verify_contract_checkpoint, ContractIntegrityError
    except ImportError:
        def verify_contract_checkpoint(c, name, raise_on_error=False): return True, None
        class ContractIntegrityError(Exception): pass

try:
    from ..developer_gateway import DeveloperGateway, DeveloperTransportError, DeveloperResponse
except (ImportError, ValueError):
    try:
        from developer_gateway import DeveloperGateway, DeveloperTransportError, DeveloperResponse
    except ImportError:
        DeveloperGateway = None
        class DeveloperTransportError(Exception):
            def to_dict(self): return {"error_code": "MODEL_TRANSPORT_ERROR", "message": str(self)}
        DeveloperResponse = None

_orig_get_llm = get_llm


DEV_SYSTEM_PROMPT = """Anda adalah Senior Software Developer dalam tim rekayasa perangkat lunak ReinDev Studio.
Tugas Anda adalah menulis kode program berkualitas produksi berdasarkan spesifikasi dari Product Manager dan rencana arsitektur dari System Architect.

ATURAN REKAYASA & KEBERSIHAN KODE (STRICT):
1. DILARANG KERAS menyertakan teks obrolan, salam, basa-basi, atau penjelasan di luar kode. Output Anda harus 100% berupa definisi file kode murni.
2. Tulis kode yang lengkap, modular, dengan penanganan kesalahan dan type annotation sesuai target bahasa pemrograman.
3. JANGAN PERNAH menyertakan placeholder seperti '# TODO', '# implement later', atau '...'.
4. DOKTRIN REKAYASA (ENGINEERING DOCTRINE):
   - [AUTHORITATIVE CONTRACT]: Signature dan antarmuka Oracle adalah sumber kebenaran mutlak.
   - [EXCEPTION COMPATIBILITY]: Tipe exception harus kompatibel secara hierarkis (issubclass(Actual, Expected)).
   - [BEHAVIORAL INVARIANT PRESERVATION]: Fungsionalitas/pengujian yang sudah berstatus PROVEN dilarang keras dirusak (BEHAVIORAL_MUTATION: FORBIDDEN).
   - [CAUSAL REPAIR SCOPE]: Modifikasi HANYA kode yang terbukti kausal terhadap kegagalan.
5. Format setiap file kode menggunakan blok penanda khusus persis seperti ini:
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
    specs = state.get("specifications", "")
    arch_plan = state.get("architecture_plan", "")
    user_task = state.get("task", "")
    target_lang = state.get("target_language", "python").strip()
    is_dart = "dart" in target_lang.lower() or "flutter" in target_lang.lower()
    iteration = state.get("iteration_count", 0)
    test_results = state.get("test_results", {})
    
    # Observability: Rekam snapshot INPUT AKTUAL yang diterima fungsi secara mendalam (deep copy)
    dev_input_snapshot = {
        "task": user_task,
        "specifications": specs,
        "architecture_plan": arch_plan,
        "iteration_count": iteration,
        "code_files": copy.deepcopy(state.get("code_files", {})),
        "test_files": copy.deepcopy(state.get("test_files", {})),
        "test_results": copy.deepcopy(test_results),
        "logs": copy.deepcopy(state.get("logs", [])),
        "status": state.get("status", "")
    }
    dev_input_hashes = {
        "code_files_hashes": compute_dict_hashes(dev_input_snapshot["code_files"]),
        "test_files_hashes": compute_dict_hashes(dev_input_snapshot["test_files"]),
        "specifications_sha256": compute_sha256(specs),
        "architecture_plan_sha256": compute_sha256(arch_plan),
        "test_results_sha256": compute_object_hash(test_results),
        "input_snapshot_sha256": compute_object_hash(dev_input_snapshot)
    }

    tracer = get_tracer(state.get("run_id"))
    if tracer:
        tracer.log_event(
            stage="developer",
            event_type="input",
            iteration=iteration,
            data={
                "developer_input": dev_input_snapshot,
                "developer_input_hashes": dev_input_hashes,
                "iteration": iteration
            }
        )

    # P0-2: Verifikasi Integritas Kontrak FROZEN sebelum Developer memproses
    contract = state.get("contract")
    if contract and contract.get("status") in ("FROZEN", "EXECUTING"):
        checkpoint_name = f"developer_iteration_{iteration}" if iteration > 0 else "developer_pre_flight"
        verify_contract_checkpoint(contract, checkpoint_name, raise_on_error=True)
        if tracer:
            tracer.log_event(
                stage="developer",
                event_type="contract_integrity_verified",
                iteration=iteration,
                data={
                    "checkpoint": checkpoint_name,
                    "contract_sha256": contract.get("provenance", {}).get("contract_sha256")
                }
            )
    
    # P0-2 & Intervensi 1: Determine Authoritative Target File from Contract
    authoritative_target_file = None
    if contract:
        authoritative_target_file = contract.get("target_file")
        if not authoritative_target_file:
            for iface in contract.get("interface_contracts", []):
                if iface.get("target_file"):
                    authoritative_target_file = iface["target_file"]
                    break
        if not authoritative_target_file:
            for m in contract.get("data_models", []):
                if m.get("target_file"):
                    authoritative_target_file = m["target_file"]
                    break
    if not authoritative_target_file:
        authoritative_target_file = "lib/card_metric.dart" if is_dart else "main.py"

    feedback_section = ""
    latest_cep = state.get("latest_evidence_package")
    dev_max_iter = state.get("max_iterations") if state.get("max_iterations") is not None else 10

    if latest_cep and latest_cep.get("causal_owner") == "DEVELOPER":
        try:
            from ..context_hardening import build_developer_repair_context, ContextTelemetry, emit_context_telemetry
        except (ImportError, ValueError):
            try:
                from context_hardening import build_developer_repair_context, ContextTelemetry, emit_context_telemetry
            except ImportError:
                build_developer_repair_context = None
                ContextTelemetry = None
                emit_context_telemetry = None

        if build_developer_repair_context:
            pkg = None
            try:
                from ..contextual_evidence import ContextualEvidencePackage
            except (ImportError, ValueError):
                try:
                    from contextual_evidence import ContextualEvidencePackage
                except ImportError:
                    ContextualEvidencePackage = None
            if ContextualEvidencePackage:
                pkg = ContextualEvidencePackage.from_dict(latest_cep)

            repair_ctx, telem_data = build_developer_repair_context(state, pkg=pkg)
            feedback_section = f"\n\n[PERHATIAN KRUSIAL - SIKLUS PERBAIKAN DETERMINISTIK (LOOP {iteration}/{dev_max_iter})]:\n{repair_ctx}\n"

            tracer = get_tracer(state.get("run_id"))
            if tracer and ContextTelemetry and emit_context_telemetry:
                telem = ContextTelemetry(
                    agent="developer",
                    model=str(state.get("model_name", "")),
                    context_version="hardening_v1",
                    run_id=str(state.get("run_id", "")),
                    iteration=iteration,
                    **telem_data
                )
                emit_context_telemetry(tracer, "developer", telem)
                if hasattr(tracer, "log_repair_attempt") and pkg:
                    tracer.log_repair_attempt(turn=iteration, package_id=pkg.package_id, iteration=iteration)

    is_repair_mode = (iteration > 0 or state.get("status") == "developer_preflight_rejected" or bool(state.get("developer_feedback")) or bool(latest_cep and latest_cep.get("causal_owner") == "DEVELOPER"))

    if not feedback_section and is_repair_mode and (test_results or state.get("developer_feedback")):
        # P0-1 & Improved Repentance: Compact Repair Context (<= 2.500 karakter untuk num_ctx=8192)
        targeted_feedback = state.get("developer_feedback")

        if not targeted_feedback and isinstance(test_results.get("diagnostic_evidence"), dict):
            try:
                from ..diagnostic_parser import build_targeted_feedback_from_dict
            except (ImportError, ValueError):
                try:
                    from diagnostic_parser import build_targeted_feedback_from_dict
                except ImportError:
                    build_targeted_feedback_from_dict = None
            if build_targeted_feedback_from_dict:
                targeted_feedback = build_targeted_feedback_from_dict(
                    test_results["diagnostic_evidence"],
                    iteration=iteration,
                    max_iterations=dev_max_iter,
                    run_id=state.get("run_id"),
                    contract=contract,
                    repair_history=state.get("repair_history"),
                    known_good_constraints=state.get("known_good_constraints"),
                    failed_strategies=state.get("failed_strategies"),
                    use_repentance=True
                )

        if targeted_feedback:
            compact_err = targeted_feedback.strip()
        else:
            raw_out = test_results.get("output", "") or test_results.get("stdout", "")
            lines = [ln.strip() for ln in raw_out.splitlines() if ln.strip()]
            err_lines = [ln for ln in lines if any(k in ln.lower() for k in ("error", "failed", "exception", "nosuchmethod", "undefined"))]
            if err_lines:
                compact_err = "\n".join(err_lines[:8])
            else:
                compact_err = "\n".join(lines[:6])

        # Pastikan compact feedback <= 2500 chars (Aman untuk num_ctx=8192)
        if len(compact_err) > 2500:
            compact_err = compact_err[:2450] + "\n...(dipotong untuk efisiensi konteks)"

        # Sediakan konteks kode yang sudah ditulis sebelumnya - prioritaskan authoritative target file
        prev_code_blocks = []
        code_files = state.get("code_files", {})
        if authoritative_target_file in code_files:
            prev_code_blocks.append(f"=== FILE: {authoritative_target_file} ===\n{code_files[authoritative_target_file]}\n=== END FILE ===")
        else:
            for fname, content in code_files.items():
                prev_code_blocks.append(f"=== FILE: {fname} ===\n{content}\n=== END FILE ===")
                break
        prev_code_str = "\n".join(prev_code_blocks) if prev_code_blocks else "(Belum ada kode)"

        # Sediakan konteks test suite dari QA Tester secara ringkas (tanpa bocoran)
        qa_test_blocks = []
        for fname, content in state.get("test_files", {}).items():
            if len(content) > 1200:
                test_summary = content[:1200] + "\n// ... (sisa test suite dipotong untuk efisiensi konteks)"
            else:
                test_summary = content
            qa_test_blocks.append(f"=== TEST FILE: {fname} ===\n{test_summary}\n=== END TEST FILE ===")
        qa_test_str = "\n".join(qa_test_blocks) if qa_test_blocks else "(Belum ada test)"

        feedback_section = f"""

[PERHATIAN KRUSIAL - SIKLUS PERBAIKAN SELF-HEALING (LOOP {iteration}/{dev_max_iter})]:
DIAGNOSTIK KEGAGALAN TERARAH & REPENTANCE GUIDANCE:
{compact_err}

BERKAS KODE TERAKHIR ANDA:
{prev_code_str}

BERKAS TEST RUNNER:
{qa_test_str}

INSTRUKSI PERBAIKAN:
1. Analisis diagnostik terarah dan ikuti langkah-langkah [IMPROVED REPENTANCE GUIDANCE] di atas secara disiplin.
2. Periksa [ROOT CAUSE], patuhi [REQUIRED DIRECTION], dan jaga [PRESERVATION RULE] agar tidak terjadi regresi.
3. Pastikan antarmuka kode memenuhi ekspektasi test runner dan kontrak resmi.
4. Tuliskan kembali berkas yang diperbaiki dengan Target File Authoritative: '{authoritative_target_file}'. DILARANG menggunakan nama file lain!
"""

    contract_section = ""
    if contract:
        models = [m.get("model_name") for m in contract.get("data_models", [])]
        interfaces = [f"{i.get('http_method') or ''} {i.get('identifier')}".strip() for i in contract.get("interface_contracts", [])]
        contract_section = f"""
[KONTRAK RESMI PROYEK (STRICTLY FROZEN - WAJIB DIPATUHI 100%)]:
- Target File Authoritative (WAJIB): {authoritative_target_file}
- ATURAN MUTLAK TARGET FILE: Developer WAJIB menghasilkan dan memperbaiki kode HANYA pada file target authoritative '{authoritative_target_file}' (menggunakan blok === FILE: {authoritative_target_file} ===).
- PERINGATAN KERAS: DILARANG menggunakan nama file alternatif/lain (misalnya jika System Architect mengusulkan nama file lain, nama file dari Architect TIDAK BOLEH mengoverride Target File Authoritative ini).
- Domain: {contract.get('task_intent', {}).get('domain', '')}
- Model Data Resmi: {', '.join(models) if models else '(Sesuai interface)'}
- Antarmuka Resmi: {', '.join(interfaces) if interfaces else '(Fungsi utama)'}
- Batasan: DILARANG menambah endpoint, fungsi, atau model di luar kontrak resmi ini!
"""

    if not is_repair_mode:
        if arch_plan:
            try:
                from ..blueprint_schema import parse_blueprint_json, blueprint_to_narrative_markdown
            except (ImportError, ValueError):
                try:
                    from blueprint_schema import parse_blueprint_json, blueprint_to_narrative_markdown
                except ImportError:
                    parse_blueprint_json = lambda t: (None, "")
                    blueprint_to_narrative_markdown = lambda b: ""

            bp_obj, _ = parse_blueprint_json(arch_plan)
            if bp_obj:
                rendered_plan = blueprint_to_narrative_markdown(bp_obj)
            else:
                rendered_plan = arch_plan

            arch_section = (
                f"\nRencana Arsitektur & File Tree (PANDUAN KONSEPTUAL):\n"
                f"[PERINGATAN PRESEDEN: Jika ada kelas/pola di rancangan arsitek yang bertentangan dengan FACT CARD di atas, FACT CARD MUTLAK MENANG]\n"
                f"{rendered_plan}\n"
            )
        else:
            arch_section = ""
    else:
        # Intervensi 2: Compact Repair Context - hilangkan arsitektur usang/bertele-tele di loop perbaikan
        arch_section = f"\n[Rencana Arsitektur]: Gunakan Target File Authoritative '{authoritative_target_file}' dan ikuti Kontrak Resmi di atas.\n"

    
    if is_dart:
        lang_rule = (
            "ATURAN DART / FLUTTER (WAJIB):\n"
            "- Tulis kode Dart murni dengan Sound Null Safety dan Strong Typing.\n"
            f"- Konsolidasikan seluruh implementasi (model data, Riverpod provider, dan ConsumerWidget) dalam 1 file di lib/ (contoh: === FILE: {authoritative_target_file} ===).\n"
            "- DILARANG menulis file pubspec.yaml atau file test (fokus hanya pada file kode produksi di lib/).\n"
            "- Untuk Widget dengan Riverpod: Jika method `build` menerima `WidgetRef ref` (contoh: `Widget build(BuildContext context, WidgetRef ref)`), deklarasikan kelas sebagai `class ... extends ConsumerWidget {`.\n"
            "- Jika menggunakan Card widget, gunakan Material Design 3 Card.\n"
            "- Untuk model data Dart, gunakan konstruktor named parameter dengan Sound Null Safety (gunakan default value atau tipe nullable `?` jika opsional) agar aman diinisialisasi.\n"
            "- Untuk State Management Riverpod, gunakan `Provider<T>` standar (contoh: `final ...Provider = Provider<...>((ref) => ...)`).\n"
            "- DILARANG menggunakan `StateProvider`, `ChangeNotifierProvider`, atau `StateNotifier` (deprecated/hilang pada Riverpod terbaru)."
        )
    else:
        py_rules = [
            "ATURAN PYTHON (WAJIB):",
            "- Tulis kode Python PEP 8 modular dengan type hint murni.",
            "- DILARANG menulis file test atau file non-kode seperti README.md atau requirements.txt (fokus hanya pada file kode .py).",
            "- Pastikan seluruh class/model yang digunakan diimpor secara eksplisit.",
            "- Simpan file implementasi dengan ekstensi .py di root direktori (contoh: === FILE: main.py ===).",
            "- Seluruh antarmuka yang didefinisikan dalam Kontrak Resmi (interface_contracts dan data_models) WAJIB diimplementasikan secara utuh.",
            "- Sesuaikan operasi mutasi internal dengan struktur data yang Anda pilih agar konsisten dengan call-site dan ekspektasi test.",
        ]
        lang_rule = "\n".join(py_rules)
    
    # Environment Grounding: periksa fakta lingkungan aktual sebelum Developer mulai coding
    try:
        env_fact_card = generate_fact_card(target_lang, task=user_task)
    except Exception:
        env_fact_card = ""
    env_grounding_section = f"\n{env_fact_card}\n" if env_fact_card else ""


    repair_closing_directive = (
        "WAJIB selesaikan seluruh perbaikan yang diminta pada instruksi diagnostik di atas secara disiplin!\n"
        if is_repair_mode else ""
    )

    prompt = f"""TARGET BAHASA PEMROGRAMAN: {target_lang.upper()}

{lang_rule}
{env_grounding_section}
Tugas Pengguna:
{user_task}

Spesifikasi Product Manager:
{specs}
{arch_section}{contract_section}{feedback_section}

ATURAN KETAT:
Tulis seluruh implementasi file kode HANYA dalam bahasa {target_lang.upper()}.
Jangan gunakan bahasa pemrograman lain!
{repair_closing_directive}Patuhi ENVIRONMENT FACT CARD dan POLA KANONIKAL di atas sebagai kebenaran mutlak runtime.

Silakan tulis kode program lengkap sesuai format penanda === FILE: ... === tanpa teks obrolan apapun."""
    
    messages = [
        SystemMessage(content=DEV_SYSTEM_PROMPT),
        HumanMessage(content=prompt)
    ]
    
    # Periksa apakah get_llm dimonkeypatch oleh test suite (e.g. test_tracer_e2e atau test_diagnostic_parser)
    is_mocked = (get_llm is not _orig_get_llm) or hasattr(get_llm, "mock_calls") or (
        hasattr(get_llm, "__code__") and hasattr(_orig_get_llm, "__code__") and get_llm.__code__ != _orig_get_llm.__code__
    )

    dev_backend = (
        state.get("developer_backend") or 
        (state.get("provider") if state.get("provider") == "openrouter" else None) or 
        os.getenv("DEVELOPER_BACKEND") or 
        ""
    ).lower()

    use_gateway = (dev_backend == "openrouter") or (not is_mocked and DeveloperGateway is not None)

    metadata = {}
    if use_gateway and DeveloperGateway is not None:
        adapter = DeveloperGateway.from_state(state)
        try:
            response = adapter.invoke(
                messages,
                run_id=state.get("run_id"),
                experiment_id=state.get("experiment_id"),
                iteration=iteration
            )
            raw_output = response.content if hasattr(response, "content") else str(response)
            metadata = getattr(response, "metadata", {})
        except DeveloperTransportError as exc:
            err_dict = exc.to_dict()
            if tracer:
                tracer.log_event(
                    stage="developer",
                    event_type="transport_error",
                    iteration=iteration,
                    data=err_dict
                )
            error_log = f"[Developer Gateway Transport Error] {exc.error_code} ({exc.provider}/{exc.model}): {str(exc)}"
            current_logs = state.get("logs", [])
            return {
                "status": "transport_error",
                "error": err_dict,
                "logs": current_logs + [error_log]
            }
    else:
        llm = get_llm(role="developer", provider=state.get("provider"))
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
    
    # Observability Trace Logging: Rekam OUTPUT AKTUAL Developer
    iteration = state.get("iteration_count", 0)
    tracer = get_tracer(state.get("run_id"))
    if tracer:
        tracer_data = {
            "developer_raw_output": raw_output,
            "developer_parsed_output": final_code_files,
            "code_files_hashes": compute_dict_hashes(final_code_files),
            "newly_parsed_files": list(code_files.keys()),
            "iteration": iteration
        }
        if metadata:
            tracer_data.update({
                "developer_backend": metadata.get("developer_backend"),
                "provider": metadata.get("provider"),
                "model": metadata.get("model"),
                "latency_s": metadata.get("latency_s"),
                "usage": metadata.get("usage", {})
            })
        tracer.log_event(
            stage="developer",
            event_type="output",
            iteration=iteration,
            data=tracer_data
        )

    return {
        "code_files": final_code_files,
        "status": "dev_done",
        "logs": current_logs + [new_log]
    }
