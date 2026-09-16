"""
System Architect Agent (v1.1.0)
ReinDev Studio — Iterasi 6

Merancang arsitektur perangkat lunak modular, peta file tree, dan kontrak antarmuka publik.
v1.1.0: Injeksi Architect vNext Invariants (Coverage, Authority, Symbol Resolvability,
Declaration Consistency), Pre-Seal Self-Review, dan Deterministic Blueprint Validator
Self-Healing Revision Loop (max 2 revisions).
"""

import re
import json
from datetime import datetime
from pathlib import Path
from langchain_core.messages import SystemMessage, HumanMessage
try:
    from ..state import SquadState
    from ..config import get_llm
    from ..contract import (
        create_draft_contract,
        complete_aligned_contract,
        extract_contract_json_from_text,
        ContractStatus
    )
    from ..tracer import get_tracer
    from ..environment_grounding import generate_fact_card_for_architect
    from ..architect_validator import validate_architect_blueprint
    from ..canonical_obligation import (
        extract_canonical_oracle_obligations,
        format_authoritative_obligation_ledger,
        format_acceptance_usage_evidence
    )
    from ..canonical_scenario import (
        extract_canonical_scenarios,
        format_scenarios_for_architect
    )
except (ImportError, ValueError):
    from state import SquadState
    from config import get_llm
    try:
        from contract import (
            create_draft_contract,
            complete_aligned_contract,
            extract_contract_json_from_text,
            ContractStatus
        )
    except ImportError:
        def create_draft_contract(*args, **kwargs): return {}
        def complete_aligned_contract(d, *args, **kwargs): return d
        def extract_contract_json_from_text(t): return None
        class ContractStatus: ALIGNED = "ALIGNED"
    try:
        from tracer import get_tracer
    except ImportError:
        def get_tracer(run_id=None): return None
    try:
        from environment_grounding import generate_fact_card_for_architect
    except ImportError:
        def generate_fact_card_for_architect(*args, **kwargs): return ""
    try:
        from architect_validator import validate_architect_blueprint
    except ImportError:
        def validate_architect_blueprint(*args, **kwargs): return True, []
    try:
        from canonical_obligation import (
            extract_canonical_oracle_obligations,
            format_authoritative_obligation_ledger,
            format_acceptance_usage_evidence
        )
    except ImportError:
        def extract_canonical_oracle_obligations(*args, **kwargs): return []
        def format_authoritative_obligation_ledger(*args, **kwargs): return ""
        def format_acceptance_usage_evidence(*args, **kwargs): return ""
    try:
        from canonical_scenario import (
            extract_canonical_scenarios,
            format_scenarios_for_architect
        )
    except ImportError:
        def extract_canonical_scenarios(*args, **kwargs): return []
        def format_scenarios_for_architect(*args, **kwargs): return ""
try:
    from ..blueprint_schema import (
        ArchitecturalBlueprint,
        parse_blueprint_json,
        extract_blueprint_json_text,
        blueprint_to_narrative_markdown,
        normalize_blueprint_data_models
    )
except (ImportError, ValueError):
    try:
        from blueprint_schema import (
            ArchitecturalBlueprint,
            parse_blueprint_json,
            extract_blueprint_json_text,
            blueprint_to_narrative_markdown,
            normalize_blueprint_data_models
        )
    except ImportError:
        ArchitecturalBlueprint = None
        parse_blueprint_json = lambda t: (None, "Schema not available")
        extract_blueprint_json_text = lambda t: None
        blueprint_to_narrative_markdown = lambda b: ""
        normalize_blueprint_data_models = lambda m, **kw: (m, [])

ARCHITECT_SYSTEM_PROMPT = """Anda adalah Senior Software & System Architect dalam tim rekayasa perangkat lunak ReinDev Studio.
Tugas Anda adalah menerima spesifikasi dari Product Manager dan merancang struktur arsitektur perangkat lunak yang modular, terpisah dengan jelas (Separation of Concerns), dan mudah diuji.

FORMAT LUARAN YANG WAJIB ANDA HASILKAN:
Anda WAJIB menghasilkan blok cetak biru arsitektur terstruktur dalam format JSON kanonikal di dalam penanda persis seperti berikut:

=== BLUEPRINT JSON ===
{
  "authoritative_target_file": "main.py",
  "file_tree": ["main.py"],
  "architecture_summary": "Rencana arsitektur modular yang mendefinisikan antarmuka dan model data",
  "files": {
    "main.py": {
      "module_role": "Authoritative Single Module",
      "imports": [],
      "code_scaffold": "class EntityA:\n    def __init__(self, attribute_a: str = ''):\n        self.attribute_a = attribute_a\n\ndef operation_a(entity: EntityA) -> EntityA:\n    pass\n"
    }
  },
  "interface_contracts": [
    {
      "identifier": "operation_a",
      "route": "/operation_a",
      "method": "POST",
      "target_file": "main.py"
    }
  ],
  "data_models": [
    {
      "model_name": "EntityA",
      "target_file": "main.py",
      "fields": [
        {
          "field_name": "attribute_a",
          "field_type": "str",
          "is_required": true,
          "description": "Atribut abstrak entitas"
        }
      ],
      "construction_shape": {}
    }
  ]
}
=== END BLUEPRINT JSON ===

PRINSIP KONSISTENSI & KODIFIKASI ARSITEKTUR (WAJIB):
1. File-Centric Signatures & Scaffolding: Setiap berkas dituliskan sebagai kerangka interface di dalam string `code_scaffold`.
   - BATAS SCAFFOLD WAJIB: `code_scaffold` berupa interface signatures dan stubs minimal.
   - OBSERVABLE BEHAVIOR: Scaffolds must represent sufficient observable behavior for deterministic compatibility analysis. Do not prescribe implementation-specific mechanisms. The Architect may choose the appropriate architectural representation, provided that the required observable behavior is preserved.
   - ARTIFACT PURITY: `file_tree` dan `files` HANYA untuk modul implementasi kode. DILARANG memasukkan file test atau QA test suite (seperti test_*.py atau test/*_test.dart) ke dalam file_tree atau files!
   - TARGET UKURAN: <=1200 karakter per file. DILARANG menuliskan implementasi logika bisnis penuh di dalam scaffold.
2. Symbol Resolvability: Setiap berkas WAJIB menyertakan statement `import` lengkap di awal berkas. Jika menggunakan decorator, instance dan class dekorator WAJIB dideklarasikan atau diimpor secara lokal di berkas yang bersangkutan.
3. Authority Hierarchy: Acceptance Oracle adalah Acceptance Authority (WHAT). Canonical Schema dan Governance menentukan aturan validitas struktur. Architect adalah Design Authority (HOW). Pre-seal checklist dan Invariants A-H adalah panduan penalaran (reasoning guidance) Architect; validator deterministik menentukan REALITY.
4. INTEGRITAS ENVIRONMENT: Patuhi batasan ENVIRONMENT FACT CARD dan dilarang menggunakan API terlarang.
5. Canonical Data Models: Setiap entitas dalam `data_models` WAJIB menggunakan format kanonikal: `field_name` dan `field_type` untuk setiap item dalam `fields`.
6. Two-Stage Architect Synthesis:
   - Stage 1 (Semantic Blueprint Model): Bangun model penalaran semantik terlebih dahulu (acceptance obligations, scenarios, architectural representations, interface identities, target artifacts, dan scaffold observable behaviors).
   - Stage 2 (Canonical Serialization): Lakukan serialisasi model semantik tersebut ke dalam skema ArchitecturalBlueprint kanonikal yang ada tanpa improvisasi format atau distorsi tipe data.
7. Schema Fidelity as Representation Contract:
   - Skema luaran adalah kontrak representasi yang diturunkan langsung dari definisi ArchitecturalBlueprint kanonikal.
   - Koleksi WAJIB mempertahankan semantik koleksi (misalnya `file_tree` sebagai list of strings, `interface_contracts` dan `data_models` sebagai list of objects).
   - Kamus berkas (`files`) WAJIB memiliki kunci yang sama persis dengan jalur di `file_tree`.
   - Seluruh field wajib yang ditentukan oleh skema harus dipertahankan.
8. Blueprint Integrity Invariants (A-H — Architect Reasoning Guidance):
   - INVARIANT-A (Identity Stability): Setiap antarmuka yang dideklarasikan memiliki identitas yang stabil.
   - INVARIANT-B (Consistent Location): Setiap antarmuka memiliki lokasi target artifact yang konsisten.
   - INVARIANT-C (File Structure Consistency): Koleksi berkas memiliki konsistensi 1-ke-1 dengan modul implementasi.
   - INVARIANT-D (Obligation Representation): Setiap obligasi penerimaan memiliki representasi arsitektural.
   - INVARIANT-E (Interface Shape Preservation): Bentuk antarmuka tidak berubah secara semantik tanpa bukti.
   - INVARIANT-F (Non-Destructive Repair): Perbaikan tidak boleh menghapus elemen atau field lain yang valid di bawah skema kanonikal.
   - INVARIANT-G (Relational Consistency): Artefak, antarmuka, dan scaffold membentuk struktur yang konsisten secara relasional.
   - INVARIANT-H (Serialization Equivalence): Serialisasi skema merepresentasikan struktur semantik yang identik.
9. Generic Repair Preservation (Anti-Field-Loss):
   - Prinsip: CURRENT VALID STATE + REPAIRED ELEMENT (perbaikan terlokalisasi).
   - Pada giliran repair, pertahankan seluruh elemen dan field yang masih valid di bawah skema kanonikal.
   - DILARANG meregenerasi subset dari state atau menghilangkan field valid (seperti `identifier`, `target_file`, atau anggota modul).

Tuliskan output JSON yang valid, presisi, dan konsisten tanpa teks pengantar berlebih di luar penanda.
"""

def _build_default_aligned_contract(draft_contract: dict, task: str, target_lang: str, arch_plan: str = "") -> dict:
    """Membangun spesifikasi teknis ALIGNED yang konsisten dengan 4 pilar validasi gate secara generik."""
    is_dart = "dart" in target_lang.lower() or "flutter" in target_lang.lower()
    default_itype = "WIDGET" if is_dart else "FUNCTION"

    # Ekstraksi fungsi atau method yang dirancang oleh Architect di arch_plan
    func_matches = re.findall(
        r"(?:def\s+|-\s*|\*\s*|`)([A-Za-z_][A-Za-z0-9_]*)\s*\((.*?)\)(?:\s*->\s*([A-Za-z0-9_\[\], ]+))?",
        arch_plan
    )
    # Ekstraksi class yang dideklarasikan secara sintaksis formal dalam Python:
    raw_class_matches = re.findall(
        r"(?:^|[;\n`])\s*class\s+([A-Za-z_][A-Za-z0-9_]*)(?:\s*\([^)]*\))?\s*:",
        arch_plan,
        re.MULTILINE
    )
    _CLASS_STOP_WORDS = {
        "dengan", "and", "or", "in", "is", "for", "the", "a", "an", "to", "of",
        "pass", "def", "return", "class", "from", "import", "as", "not"
    }
    seen_classes = set()
    class_matches = []
    for cname in raw_class_matches:
        cname_clean = cname.strip()
        if cname_clean and cname_clean.lower() not in _CLASS_STOP_WORDS and cname_clean not in seen_classes:
            seen_classes.add(cname_clean)
            class_matches.append(cname_clean)

    plan_files = [f for f in re.findall(r"(?:^|[;\n`\-\*])\s*([A-Za-z0-9_./\-]+\.(?:py|dart))\b", arch_plan) if not Path(f).name.startswith("test")]
    primary_target_file = plan_files[0] if plan_files else ("lib/main.dart" if is_dart else "main.py")

    data_models = []
    interface_contracts = []
    testable_assertions = []

    if class_matches:
        for cname in class_matches:
            data_models.append({
                "model_name": cname,
                "target_file": primary_target_file,
                "fields": []
            })

    if func_matches:
        seen_fns = set()
        for idx, (fn_name, params_str, ret_type) in enumerate(func_matches, 1):
            if fn_name in ("if", "for", "while", "with", "print", "assert", "return"):
                continue
            if fn_name in seen_fns:
                continue
            seen_fns.add(fn_name)
            ifid = f"IFC-0{idx}" if idx < 10 else f"IFC-{idx}"
            astid = f"AST-0{idx}" if idx < 10 else f"AST-{idx}"
            ret = ret_type.strip() if ret_type else "float"
            interface_contracts.append({
                "interface_id": ifid,
                "interface_type": default_itype,
                "identifier": fn_name,
                "http_method": None,
                "target_file": primary_target_file,
                "parameters": [],
                "expected_return": {
                    "return_type": ret,
                    "status_code_success": None,
                    "status_code_errors": []
                }
            })
            testable_assertions.append({
                "assertion_id": astid,
                "linked_req_id": "REQ-01",
                "linked_interface_id": ifid,
                "test_scenario": f"Execution of {fn_name} returns expected value",
                "target_symbol": fn_name,
                "input_fixture": f"{fn_name}()",
                "expected_outcome": {
                    "outcome_type": "VALUE_EQUALS",
                    "value": 0
                }
            })
    else:
        fn_name = "execute"
        interface_contracts = [
            {
                "interface_id": "IFC-01",
                "interface_type": default_itype,
                "identifier": fn_name,
                "http_method": None,
                "target_file": primary_target_file,
                "parameters": [
                    {"param_name": "a", "param_type": "float", "param_location": "ARGUMENT", "is_required": True},
                    {"param_name": "b", "param_type": "float", "param_location": "ARGUMENT", "is_required": True}
                ],
                "expected_return": {
                    "return_type": "float",
                    "status_code_success": None,
                    "status_code_errors": []
                }
            }
        ]
        testable_assertions = [
            {
                "assertion_id": "AST-01",
                "linked_req_id": "REQ-01",
                "linked_interface_id": "IFC-01",
                "test_scenario": f"Execution of {fn_name} returns expected value",
                "target_symbol": fn_name,
                "input_fixture": f"{fn_name}(2.0, 3.0)",
                "expected_outcome": {
                    "outcome_type": "VALUE_EQUALS",
                    "value": 5.0
                }
            }
        ]

    return complete_aligned_contract(
        draft_dict=draft_contract,
        data_models=data_models,
        interface_contracts=interface_contracts,
        testable_assertions=testable_assertions
    )


def architect_agent(state: SquadState) -> dict:
    llm = get_llm(role="architect", provider=state.get("provider"))
    
    user_task = state.get("task", "")
    specs = state.get("specifications", "")
    target_lang = state.get("target_language", "python").strip()
    is_dart = "dart" in target_lang.lower() or "flutter" in target_lang.lower()
    
    structure_rule = (
        "ATURAN STRUKTUR PROYEK DART / FLUTTER (WAJIB):\n"
        "- Gunakan struktur modul tunggal kohesif: MAKSIMAL 1 file kode implementasi untuk Developer di lib/ (contoh: `lib/card_metric.dart`).\n"
        "- Gabungkan model data, provider Riverpod, dan Widget UI dalam 1 file `lib/card_metric.dart` untuk mencegah fragmentasi file dan kesalahan impor silang.\n"
        "- DILARANG merancang struktur banyak file yang terpisah-pisah untuk widget sederhana.\n"
        "- ARTIFACT PURITY (WAJIB): file_tree dan files HANYA untuk modul kode implementasi. DILARANG KERAS memasukkan file pengujian/test ke dalam file_tree atau files!\n"
        if is_dart else
        "ATURAN STRUKTUR PROYEK PYTHON (WAJIB):\n"
        "- Gunakan struktur modul Python sederhana dan kohesif: MAKSIMAL 1-2 file kode implementasi untuk Developer (misal: `main.py` atau `models.py` + `main.py`).\n"
        "- Gabungkan data models, in-memory store/state, dan antarmuka utama dalam modul utama (contoh: `main.py` atau `models.py` + `main.py`) untuk menghindari fragmentasi folder dan kesalahan impor silang.\n"
        "- DILARANG merancang hierarki folder yang terlalu dalam (hindari app/api/, app/schemas/, app/models/). Jaga struktur tetap datar di root.\n"
        "- ARTIFACT PURITY (WAJIB): file_tree dan files HANYA untuk modul kode implementasi. DILARANG KERAS memasukkan file pengujian/test ke dalam file_tree atau files!\n"
    )
    
    feedback_section = ""
    latest_cep = state.get("latest_evidence_package")
    tracer = get_tracer(state.get("run_id"))

    pkg = None
    if latest_cep and latest_cep.get("causal_owner") == "ARCHITECT":
        try:
            from ..contextual_evidence import ContextualEvidencePackage
        except (ImportError, ValueError):
            try:
                from contextual_evidence import ContextualEvidencePackage
            except ImportError:
                ContextualEvidencePackage = None
        if ContextualEvidencePackage and latest_cep:
            pkg = ContextualEvidencePackage.from_dict(latest_cep)

    decision_ctx = ""
    telem_data = {}
    try:
        from ..context_hardening import build_architect_decision_context, ContextTelemetry, emit_context_telemetry
    except (ImportError, ValueError):
        try:
            from context_hardening import build_architect_decision_context, ContextTelemetry, emit_context_telemetry
        except ImportError:
            build_architect_decision_context = None
            ContextTelemetry = None
            emit_context_telemetry = None

    if build_architect_decision_context:
        decision_ctx, telem_data = build_architect_decision_context(state, pkg=pkg)
        if tracer and ContextTelemetry and emit_context_telemetry and telem_data:
            import dataclasses
            known_fields = {f.name for f in dataclasses.fields(ContextTelemetry)}
            filtered_telem_data = {k: v for k, v in telem_data.items() if k in known_fields}
            telem = ContextTelemetry(
                agent="architect",
                model=str(state.get("model_name", "")),
                context_version="hardening_v1",
                run_id=str(state.get("run_id", "")),
                iteration=state.get("contract_revision_count", 0),
                **filtered_telem_data
            )
            emit_context_telemetry(tracer, "architect", telem)
            if hasattr(tracer, "log_repair_attempt") and pkg:
                rev_idx = state.get("contract_revision_count", 0)
                tracer.log_repair_attempt(turn=rev_idx, package_id=pkg.package_id, iteration=rev_idx)

    feedback_section = ""
    contract_feedback = state.get("contract_feedback")
    if contract_feedback:
        feedback_section = (
            f"\n\n[PERHATIAN: KONTRAK SEBELUMNYA DITOLAK OLEH GERBANG VALIDASI - REVISI DIPERLUKAN]\n"
            f"{contract_feedback}\n\n"
            "INSTRUKSI REVISI WAJIB (GENERIC REPAIR PRESERVATION):\n"
            "- Lakukan perbaikan terlokalisasi: CURRENT VALID STATE + REPAIRED ELEMENT.\n"
            "- Perbaiki hubungan arsitektural atau elemen skema yang dinyatakan tidak valid sesuai feedback di atas.\n"
            "- Pertahankan seluruh elemen, antarmuka, dan field yang masih valid di bawah skema kanonikal ArchitecturalBlueprint.\n"
            "- DILARANG menghapus atau meregenerasi hanya subset dari state (anti-field-loss).\n"
            "- Pastikan antarmuka publik yang didefinisikan dapat dipanggil oleh pengujian independen (nama fungsi/kelas, callable signature, parameter, return type)."
        )

    # Environment Grounding untuk Architect
    try:
        arch_fact_card = generate_fact_card_for_architect(target_lang, task=user_task)
    except Exception:
        arch_fact_card = ""
    env_section = f"\n{arch_fact_card}\n" if arch_fact_card else ""

    # Acceptance Oracle Obligations Ledger (Read-Only Authoritative WHAT)
    oracle_ledger_section = ""
    try:
        f_oracle_path = state.get("frozen_oracle_path")
        t_files = state.get("test_files")
        oracle_obs = extract_canonical_oracle_obligations(
            frozen_oracle_path=f_oracle_path,
            test_files=t_files
        )
        if oracle_obs:
            ledger_text = format_authoritative_obligation_ledger(oracle_obs)
            usage_evidence_text = format_acceptance_usage_evidence(oracle_obs)
            sec_items = []
            if ledger_text:
                sec_items.append(ledger_text)
            if usage_evidence_text:
                sec_items.append(usage_evidence_text)
            if sec_items:
                oracle_ledger_section = f"\n" + "\n\n".join(sec_items) + "\n"
    except Exception:
        oracle_ledger_section = ""

    # Acceptance Behavior & Scenarios (Read-Only Authoritative Ground Truth)
    oracle_scenario_section = ""
    try:
        f_oracle_path = state.get("frozen_oracle_path")
        t_files = state.get("test_files")
        scenarios = extract_canonical_scenarios(
            frozen_oracle_path=f_oracle_path,
            test_files=t_files
        )
        if scenarios:
            scenario_text = format_scenarios_for_architect(scenarios)
            if scenario_text:
                oracle_scenario_section = f"\n{scenario_text}\n"
    except Exception:
        oracle_scenario_section = ""

    decision_text = f"\n{decision_ctx}\n" if decision_ctx else ""

    prompt = f"""TARGET BAHASA PEMROGRAMAN WAJIB: {target_lang.upper()}

{structure_rule}
{env_section}
Deskripsi Tugas Pengguna:
{user_task}
{oracle_ledger_section}{oracle_scenario_section}
Spesifikasi Product Manager:
{specs}{feedback_section}
{decision_text}
ATURAN KETAT:
Seluruh file tree, hierarki modul, dan ekstensi file WAJIB menggunakan bahasa {target_lang.upper()} murni (Maksimal 2-3 file implementasi total).
DILARANG KERAS merancang file tree atau struktur dalam bahasa selain {target_lang.upper()}!
ARTIFACT PURITY (WAJIB): DILARANG KERAS memasukkan file pengujian/test ke dalam file_tree atau files!
DILARANG KERAS merancang kelas, dependensi, atau pola yang dinyatakan dilarang dalam BATASAN ARSITEKTUR WAJIB di atas!

PRE-SEAL SELF-REVIEW (Sebelum menyerahkan blueprint):
Lakukan audit mandiri singkat terhadap rancangan arsitektur Anda:
1. Specification -> Coverage: Apakah seluruh requirement dari spesifikasi sudah terwakili tanpa ada yang terlewat?
2. Blueprint -> Internal Consistency: Apakah setiap simbol/decorator yang digunakan dalam blueprint/snippet memiliki sumber resolusi/impor yang jelas, dan deklarasi interface/constructor konsisten dengan pemanggilannya?
3. Blueprint -> Contract Consistency: Apakah antarmuka yang telah ditentukan oleh spesifikasi dipertahankan secara eksak tanpa disingkat atau diimprovisasi?
4. Acceptance Obligations Coverage: Apakah SELURUH obligasi publik dalam [AUTHORITATIVE ACCEPTANCE OBLIGATIONS], [ACCEPTANCE USAGE EVIDENCE], dan seluruh alur [ACCEPTANCE BEHAVIOR & SCENARIOS] (jika ada) telah memiliki padanan deklarasi eksplisit di `interface_contracts` atau `data_models` dengan bentuk pemanggilan (call-shape) yang kompatibel?
5. Observable Behavior: Apakah scaffold merepresentasikan perilaku observable yang disyaratkan secara memadai untuk analisis kompatibilitas deterministik?
6. Two-Stage Synthesis & Relational Invariants: Apakah model semantik telah dirancang sebelum serialisasi, dan apakah Invariants A-H terpenuhi?
7. Schema Fidelity as Representation Contract: Apakah format serialisasi mengikuti skema kanonikal ArchitecturalBlueprint secara presisi tanpa distorsi tipe data (koleksi berupa array/list, kunci files sesuai file_tree, seluruh field wajib terisi)?
8. Generic Repair Preservation: Jika dalam giliran repair, apakah seluruh field dan elemen valid sebelumnya dipertahankan tanpa penghapusan atau distorsi (CURRENT VALID STATE + REPAIRED ELEMENT)?
(Catatan: Pre-seal checklist ini adalah panduan penalaran Architect; bukan Acceptance Authority dan tidak menggantikan validator deterministik).
Tuliskan output JSON yang valid, presisi, dan konsisten di dalam penanda === BLUEPRINT JSON === ... === END BLUEPRINT JSON ===."""

    messages = [
        SystemMessage(content=ARCHITECT_SYSTEM_PROMPT),
        HumanMessage(content=prompt)
    ]
    
    response = llm.invoke(messages)
    arch_plan = response.content if hasattr(response, "content") else str(response)

    # P0-2: Lengkapi kontrak menjadi ALIGNED (Prioritas: Blueprint JSON -> Kontrak JSON blok -> Default Fallback)
    draft_contract = state.get("contract")
    if not draft_contract or not isinstance(draft_contract, dict):
        draft_contract = create_draft_contract(
            raw_intent=user_task,
            target_language=target_lang,
            goal_summary=user_task[:120]
        )

    # 1. Coba ekstrak dari skema ArchitecturalBlueprint JSON
    extracted_bp, bp_err = parse_blueprint_json(arch_plan)
    contract_errors = []
    is_dart = "dart" in target_lang.lower() or "flutter" in target_lang.lower()

    if extracted_bp and not bp_err:
        ifaces = []
        assertions = []
        for idx, ifc in enumerate(extracted_bp.interface_contracts, 1):
            d = ifc.model_dump() if hasattr(ifc, "model_dump") else dict(ifc)
            ifid = f"IFC-{idx:02d}"
            if not d.get("interface_id"):
                d["interface_id"] = ifid
            if not d.get("http_method") and d.get("method"):
                d["http_method"] = d.get("method")
            if not d.get("interface_type"):
                if d.get("route") or (d.get("http_method") and str(d.get("http_method")).upper() in ("GET", "POST", "PUT", "DELETE", "PATCH")):
                    d["interface_type"] = "HTTP_ENDPOINT"
                else:
                    d["interface_type"] = "WIDGET" if is_dart else "FUNCTION"
            ifaces.append(d)
            ident = d.get("identifier", "target")
            assertions.append({
                "assertion_id": f"AST-{idx:02d}",
                "linked_req_id": "REQ-01",
                "linked_interface_id": d["interface_id"],
                "test_scenario": f"Execution of {ident} meets functional requirements",
                "target_symbol": ident,
                "input_fixture": f"{ident}()",
                "expected_outcome": {
                    "outcome_type": "VALUE_EQUALS",
                    "value": 0
                }
            })

        # Boundary canonicalization: petakan data_models blueprint ke format kanonikal strict ModelField
        primary_file = extracted_bp.authoritative_target_file or ("lib/main.dart" if is_dart else "main.py")
        canonical_models, model_errs = normalize_blueprint_data_models(
            extracted_bp.data_models,
            default_target_file=primary_file
        )

        if model_errs:
            contract_errors.extend(model_errs)
            aligned_contract = dict(draft_contract)
            aligned_contract["status"] = "REJECTED"
            if "provenance" not in aligned_contract or not isinstance(aligned_contract["provenance"], dict):
                aligned_contract["provenance"] = {}
            aligned_contract["provenance"]["active_validation_errors"] = list(contract_errors)
            aligned_contract["provenance"]["contract_validation_errors"] = list(contract_errors)
            val_hist = list(aligned_contract["provenance"].get("validation_history") or [])
            val_hist.append({
                "timestamp": datetime.now().isoformat(),
                "phase": "ARCHITECT_MODEL_NORMALIZATION",
                "status": "REJECTED",
                "errors": list(contract_errors)
            })
            aligned_contract["provenance"]["validation_history"] = val_hist
        else:
            aligned_contract = complete_aligned_contract(
                draft_dict=draft_contract,
                data_models=canonical_models,
                interface_contracts=ifaces,
                testable_assertions=assertions
            )
            if extracted_bp:
                bp_dict_pre = extracted_bp.model_dump() if hasattr(extracted_bp, "model_dump") else (extracted_bp.to_dict() if hasattr(extracted_bp, "to_dict") else extracted_bp)
                if isinstance(bp_dict_pre, dict) and "files" in bp_dict_pre:
                    aligned_contract["files"] = bp_dict_pre.get("files", {})
    else:
        # Blueprint JSON parsing failed or produced schema errors.
        # Strict Principle: JANGAN gunakan semantic regex fallback (zero fabricated contract).
        # Tolak kontrak secara deterministik dan sampaikan bukti error untuk perbaikan mandiri Architect.
        parse_msg = f"SCHEMA_VIOLATION: Blueprint JSON parse failure: {bp_err or 'Invalid or missing blueprint JSON'}"
        contract_errors.append(parse_msg)
        aligned_contract = dict(draft_contract)
        aligned_contract["status"] = "REJECTED"
        if "provenance" not in aligned_contract or not isinstance(aligned_contract["provenance"], dict):
            aligned_contract["provenance"] = {}
        aligned_contract["provenance"]["active_validation_errors"] = list(contract_errors)
        aligned_contract["provenance"]["contract_validation_errors"] = list(contract_errors)
        val_hist = list(aligned_contract["provenance"].get("validation_history") or [])
        val_hist.append({
            "timestamp": datetime.now().isoformat(),
            "phase": "ARCHITECT_BLUEPRINT_PARSE",
            "status": "REJECTED",
            "errors": list(contract_errors)
        })
        aligned_contract["provenance"]["validation_history"] = val_hist

    # Observability: Catat penyelarasan kontrak ALIGNED / REJECTED
    tracer = get_tracer(state.get("run_id"))
    if tracer:
        prov = aligned_contract.get("provenance", {}) if isinstance(aligned_contract, dict) else {}
        hist_count = len(prov.get("validation_history", [])) if isinstance(prov, dict) else 0
        tracer.log_event(
            stage="contract",
            event_type="contract_aligned",
            iteration=0,
            data={
                "contract_id": aligned_contract.get("contract_id"),
                "status": aligned_contract.get("status", "ALIGNED"),
                "models_count": len(aligned_contract.get("data_models", [])),
                "interfaces_count": len(aligned_contract.get("interface_contracts", [])),
                "assertions_count": len(aligned_contract.get("testable_assertions", [])),
                "active_error_count": len(contract_errors),
                "active_validation_errors": list(contract_errors),
                "historical_error_count": hist_count
            }
        )
    
    status_label = aligned_contract.get("status", "ALIGNED")
    new_log = (
        f"[System Architect]: Rencana arsitektur ({len(arch_plan)} char) dirancang. "
        f"Status kontrak: {status_label} ({len(aligned_contract.get('testable_assertions', []))} assertions)."
    )
    current_logs = state.get("logs", [])
    
    bp_dict = None
    if extracted_bp:
        bp_dict = extracted_bp.model_dump() if hasattr(extracted_bp, "model_dump") else (extracted_bp.to_dict() if hasattr(extracted_bp, "to_dict") else extracted_bp)

    return {
        "architecture_plan": arch_plan,
        "architectural_blueprint": bp_dict,
        "contract": aligned_contract,
        "contract_status": status_label,
        "contract_validation_errors": contract_errors,
        "blueprint_revision_count": state.get("blueprint_revision_count", 0),
        "status": "architect_done",
        "logs": current_logs + [new_log]
    }


