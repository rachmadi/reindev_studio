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
from dataclasses import asdict
from typing import Any, Optional, Dict, List, Tuple
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
        normalize_blueprint_data_models,
        serialize_blueprint_to_canonical_json,
        validate_canonical_architecture_plan_state
    )
except (ImportError, ValueError):
    try:
        from blueprint_schema import (
            ArchitecturalBlueprint,
            parse_blueprint_json,
            extract_blueprint_json_text,
            blueprint_to_narrative_markdown,
            normalize_blueprint_data_models,
            serialize_blueprint_to_canonical_json,
            validate_canonical_architecture_plan_state
        )
    except ImportError:
        ArchitecturalBlueprint = None
        parse_blueprint_json = lambda t: (None, "Schema not available")
        extract_blueprint_json_text = lambda t: None
        blueprint_to_narrative_markdown = lambda b: ""
        normalize_blueprint_data_models = lambda m, **kw: (m, [])
        serialize_blueprint_to_canonical_json = lambda b: "{}"
        validate_canonical_architecture_plan_state = lambda p, *args, **kw: (True, [])
try:
    from ..semantic_serializer import (
        parse_semantic_architectural_plan,
        serialize_semantic_decision_to_blueprint,
        check_semantic_obligation_coverage,
        merge_preservative_semantic_decisions
    )
except (ImportError, ValueError):
    try:
        from semantic_serializer import (
            parse_semantic_architectural_plan,
            serialize_semantic_decision_to_blueprint,
            check_semantic_obligation_coverage,
            merge_preservative_semantic_decisions
        )
    except ImportError:
        parse_semantic_architectural_plan = None
        serialize_semantic_decision_to_blueprint = None
        check_semantic_obligation_coverage = None
        merge_preservative_semantic_decisions = None
try:
    from ..architect_staged import (
        StageAObligationMapping,
        FrozenStageAMappings,
        StageARevisionRequest,
        StageBAssemblyOutput,
        StageB1ElementRealization,
        StageB1Output,
        FrozenStageB1State,
        StageB2BindingDecision,
        StageB2Output,
        FrozenStageB2State,
        parse_stage_a_mappings,
        validate_stage_a_mappings,
        parse_stage_b_assembly,
        validate_stage_b_preservation,
        convert_stage_b_to_semantic_plan,
        assemble_stage_b_blueprint,
        parse_stage_b1_output,
        validate_stage_b1_realization,
        parse_stage_b2_output,
        validate_stage_b2_bindings,
        assemble_decomposed_stage_b_blueprint,
        build_stage_a_prompt,
        build_stage_b_prompt,
        build_stage_b1_prompt,
        build_stage_b2_prompt,
        STAGE_A_SYSTEM_PROMPT,
        STAGE_B_SYSTEM_PROMPT,
        STAGE_B1_SYSTEM_PROMPT,
        STAGE_B2_SYSTEM_PROMPT
    )
except (ImportError, ValueError):
    try:
        from architect_staged import (
            StageAObligationMapping,
            FrozenStageAMappings,
            StageARevisionRequest,
            StageBAssemblyOutput,
            StageB1ElementRealization,
            StageB1Output,
            FrozenStageB1State,
            StageB2BindingDecision,
            StageB2Output,
            FrozenStageB2State,
            parse_stage_a_mappings,
            validate_stage_a_mappings,
            parse_stage_b_assembly,
            validate_stage_b_preservation,
            convert_stage_b_to_semantic_plan,
            assemble_stage_b_blueprint,
            parse_stage_b1_output,
            validate_stage_b1_realization,
            parse_stage_b2_output,
            validate_stage_b2_bindings,
            assemble_decomposed_stage_b_blueprint,
            build_stage_a_prompt,
            build_stage_b_prompt,
            build_stage_b1_prompt,
            build_stage_b2_prompt,
            STAGE_A_SYSTEM_PROMPT,
            STAGE_B_SYSTEM_PROMPT,
            STAGE_B1_SYSTEM_PROMPT,
            STAGE_B2_SYSTEM_PROMPT
        )
    except ImportError:
        StageAObligationMapping = None
        FrozenStageAMappings = None
        StageARevisionRequest = None
        StageBAssemblyOutput = None
        StageB1ElementRealization = None
        StageB1Output = None
        FrozenStageB1State = None
        StageB2BindingDecision = None
        StageB2Output = None
        FrozenStageB2State = None
        parse_stage_a_mappings = None
        validate_stage_a_mappings = None
        parse_stage_b_assembly = None
        validate_stage_b_preservation = None
        convert_stage_b_to_semantic_plan = None
        assemble_stage_b_blueprint = None
        parse_stage_b1_output = None
        validate_stage_b1_realization = None
        parse_stage_b2_output = None
        validate_stage_b2_bindings = None
        assemble_decomposed_stage_b_blueprint = None
        build_stage_a_prompt = None
        build_stage_b_prompt = None
        build_stage_b1_prompt = None
        build_stage_b2_prompt = None
        STAGE_A_SYSTEM_PROMPT = ""
        STAGE_B_SYSTEM_PROMPT = ""
        STAGE_B1_SYSTEM_PROMPT = ""
        STAGE_B2_SYSTEM_PROMPT = ""

try:
    from ..staged_repair import (
        classify_contract_failure_owner,
        compute_stage_lifecycle,
        apply_lifecycle_to_frozen_states,
        verify_stage_preservation,
        build_repair_telemetry,
    )
except (ImportError, ValueError):
    try:
        from staged_repair import (
            classify_contract_failure_owner,
            compute_stage_lifecycle,
            apply_lifecycle_to_frozen_states,
            verify_stage_preservation,
            build_repair_telemetry,
        )
    except ImportError:
        classify_contract_failure_owner = None
        compute_stage_lifecycle = None
        apply_lifecycle_to_frozen_states = None
        verify_stage_preservation = None
        build_repair_telemetry = None

try:
    from ..b2_repair_delivery import (
        assemble_and_distill_b2_repair_prompt,
        validate_b2_repair_context_delivery,
        snapshot_b2_repair_pre_state,
        verify_stage_preservation as verify_b2_stage_preservation,
        resolve_context_budget as resolve_b2_context_budget,
    )
except (ImportError, ValueError):
    try:
        from b2_repair_delivery import (
            assemble_and_distill_b2_repair_prompt,
            validate_b2_repair_context_delivery,
            snapshot_b2_repair_pre_state,
            verify_stage_preservation as verify_b2_stage_preservation,
            resolve_context_budget as resolve_b2_context_budget,
        )
    except ImportError:
        assemble_and_distill_b2_repair_prompt = None
        validate_b2_repair_context_delivery = None
        snapshot_b2_repair_pre_state = None
        verify_b2_stage_preservation = None
        resolve_b2_context_budget = None



ARCHITECT_SYSTEM_PROMPT = """Anda adalah Senior Software & System Architect dalam tim rekayasa perangkat lunak ReinDev Studio.
Tugas Anda adalah menerima spesifikasi dari Product Manager dan merancang struktur arsitektur perangkat lunak yang modular, terpisah dengan jelas (Separation of Concerns), dan mudah diuji.

FORMAT LUARAN YANG WAJIB ANDA HASILKAN:
Anda dapat menghasilkan blok keputusan arsitektur semantik terstruktur di dalam penanda === SEMANTIC DECISION JSON === (format penalaran semantik utama):

=== SEMANTIC DECISION JSON ===
{
  "target_file": "main.py",
  "scaffold_code": "class EntityA:\n    def __init__(self, attribute_a: str = ''):\n        self.attribute_a = attribute_a\n\ndef operation_a(param_1: str) -> EntityA:\n    pass\n",
  "semantic_decisions": [
    {
      "obligation_id": "OBL-01",
      "target_structure": "INTERFACE_CONTRACT",
      "identifier": "operation_a",
      "target_file": "main.py",
      "parameters": [
        {
          "name": "param_1",
          "type": "TypeA",
          "location": "ARGUMENT",
          "required": true
        }
      ],
      "return_semantics": {
        "type": "TypeA"
      }
    },
    {
      "obligation_id": "OBL-02",
      "target_structure": "DATA_MODEL",
      "identifier": "EntityA",
      "target_file": "main.py",
      "fields": [
        {
          "name": "attribute_a",
          "type": "str",
          "required": true
        }
      ]
    }
  ]
}
=== END SEMANTIC DECISION JSON ===

Atau sebagai representasi kanonikal langsung di dalam penanda:

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
      "target_file": "main.py",
      "parameters": [
        {
          "param_name": "param_1",
          "param_type": "TypeA",
          "param_location": "ARGUMENT",
          "is_required": true
        }
      ],
      "expected_return": {
        "return_type": "TypeA"
      }
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
   - STRING FORMAT: `code_scaffold` WAJIB berupa single string (teks kode langsung dengan baris baru) atau list of strings (tiap baris). DILARANG KERAS menggunakan nested dictionary atau objek JSON terpecah untuk kode (seperti {'imports': ..., 'models': ..., 'endpoints': ...}).
   - OBSERVABLE BEHAVIOR: Scaffolds must represent sufficient observable behavior for deterministic compatibility analysis. Do not prescribe implementation-specific mechanisms. The Architect may choose the appropriate architectural representation, provided that the required observable behavior is preserved.
   - ARTIFACT PURITY: `file_tree` dan `files` HANYA untuk modul implementasi kode. DILARANG memasukkan file test atau QA test suite (seperti test_*.py atau test/*_test.dart) ke dalam file_tree atau files!
   - TARGET UKURAN: <=1200 karakter per file. DILARANG menuliskan implementasi logika bisnis penuh di dalam scaffold.
2. Symbol Resolvability: Setiap berkas WAJIB menyertakan statement `import` lengkap di awal berkas. Jika menggunakan decorator, instance dan class dekorator WAJIB dideklarasikan atau diimpor secara lokal di berkas yang bersangkutan.
3. Authority Hierarchy: Acceptance Oracle adalah Acceptance Authority (WHAT). Canonical Schema dan Governance menentukan aturan validitas struktur. Architect adalah Design Authority (HOW). Pre-seal checklist dan Invariants A-H adalah panduan penalaran (reasoning guidance) Architect; validator deterministik menentukan REALITY.
4. INTEGRITAS ENVIRONMENT: Patuhi batasan ENVIRONMENT FACT CARD dan dilarang menggunakan API terlarang.
5. Canonical Data Models: Setiap entitas dalam `data_models` WAJIB menggunakan format kanonikal: `field_name` dan `field_type` untuk setiap item dalam `fields`.
6. Two-Stage Architect Synthesis & Obligation Grounding:
   - Stage 1 (Semantic Blueprint Model): Bangun model penalaran semantik terlebih dahulu (acceptance obligations, scenarios, architectural representations, interface identities, target artifacts, parameter shapes, return structures, dan scaffold observable behaviors).
   - Stage 2 (Canonical Serialization): Lakukan serialisasi model semantik tersebut ke dalam skema ArchitecturalBlueprint kanonikal tanpa improvisasi format atau distorsi tipe data.
   - Obligation Coverage Rule: Setiap mandatory acceptance obligation harus mempunyai canonical architectural representation yang dapat ditelusuri secara deterministik (baik melalui interface_contracts maupun data_models).
   - Parameter & Return Canonical Fidelity:
     * Elemen 'parameters' pada interface_contracts WAJIB menggunakan field kanonikal: `param_name`, `param_type`, `param_location` ('PATH', 'QUERY', 'BODY', 'ARGUMENT', atau 'PROP'), dan `is_required`. DILARANG menggunakan 'name' atau 'type'.
     * Elemen 'expected_return' pada interface_contracts WAJIB berupa objek dictionary dengan kunci `return_type` (contoh: {"return_type": "TypeA", "status_code_success": 200} atau {"return_type": "TypeA"}). DILARANG berupa string telanjang.
     * Untuk antarmuka berbasis HTTP endpoint, sertakan 'route' dan 'method' jika relevan (misal: "route": "/operation_a", "method": "POST").
7. Schema Fidelity as Representation Contract:
   - Skema luaran adalah kontrak representasi yang diturunkan langsung dari definisi ArchitecturalBlueprint kanonikal.
   - Koleksi WAJIB mempertahankan semantik koleksi:
     * `file_tree`: WAJIB List[str] berisi string path berkas (contoh: ["main.py"]).
     * `files`: WAJIB Dict level teratas yang memetakan setiap path dari `file_tree` ke modul scaffold-nya.
     * `interface_contracts` dan `data_models` adalah list of objects.
   - Kamus berkas (`files`) WAJIB memiliki kunci yang sama persis dengan jalur di `file_tree`.
   - DILARANG menggabungkan, mengorbankan, atau menghilangkan salah satu dari `file_tree` atau `files`. Keduanya adalah field terpisah di root JSON.
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


def architect_agent(state: SquadState, llm: Any = None, tracer: Any = None) -> dict:
    if llm is None:
        llm = get_llm(role="architect", provider=state.get("provider"))
    if tracer is None:
        tracer = get_tracer(state.get("run_id"))
    
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
        from ..context_hardening import (
            build_architect_decision_context,
            ContextTelemetry,
            emit_context_telemetry,
            resolve_context_budget,
        )
    except (ImportError, ValueError):
        try:
            from context_hardening import (
                build_architect_decision_context,
                ContextTelemetry,
                emit_context_telemetry,
                resolve_context_budget,
            )
        except ImportError:
            build_architect_decision_context = None
            ContextTelemetry = None
            emit_context_telemetry = None
            resolve_context_budget = lambda s, default=12000: int(s.get("context_budget") or s.get("max_context_chars") or default) if s else default

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

    is_repair_turn = (state.get("contract_revision_count", 0) > 0) or bool(pkg) or bool(state.get("contract_feedback"))

    # Acceptance Oracle Obligations Ledger (Read-Only Authoritative WHAT)
    oracle_ledger_section = ""
    oracle_scenario_section = ""
    # On repair turns with decision_ctx, the Repair Decision Packet in decision_ctx already contains
    # distilled authoritative obligations & scenarios. Omitting duplicate raw ledgers saves ~15,000 chars.
    if not (is_repair_turn and decision_ctx):
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
4. Acceptance Obligations Coverage: Apakah SELURUH obligasi publik dalam [AUTHORITATIVE ACCEPTANCE OBLIGATIONS], [ACCEPTANCE USAGE EVIDENCE], dan seluruh alur [ACCEPTANCE BEHAVIOR & SCENARIOS] (jika ada) telah memiliki padanan deklarasi eksplisit di `interface_contracts` atau `data_models`? Setiap mandatory acceptance obligation harus mempunyai canonical architectural representation yang dapat ditelusuri secara deterministik.
5. Observable Behavior: Apakah scaffold merepresentasikan perilaku observable yang disyaratkan secara memadai untuk analisis kompatibilitas deterministik?
6. Two-Stage Synthesis & Relational Invariants: Apakah model semantik telah dirancang sebelum serialisasi, dan apakah Invariants A-H terpenuhi?
7. Schema Fidelity as Representation Contract: Apakah format serialisasi mengikuti skema kanonikal ArchitecturalBlueprint secara presisi tanpa distorsi tipe data:
   - `authoritative_target_file`: WAJIB str nama file target implementasi utama (harus ada di file_tree dan files).
   - `file_tree`: WAJIB List[str] berisi daftar path berkas (contoh: ["path/ke/file.ext"]). Dilarang menaruh objek/scaffold di dalam file_tree.
   - `files`: WAJIB Dict[str, dict] level teratas yang memetakan setiap berkas di file_tree ke objek scaffold-nya.
   - `code_scaffold`: WAJIB berupa single string atau list of strings (lines). DILARANG menggunakan nested dict/object untuk memecah kode.
   - `interface_contracts`: WAJIB List[dict] yang memuat field wajib identifier dan target_file. Jika mendeklarasikan `parameters`, WAJIB gunakan `param_name`, `param_type`, `param_location` (PATH, QUERY, BODY, ARGUMENT, PROP). Jika mendeklarasikan `expected_return`, WAJIB gunakan objek dictionary dengan `return_type` (bukan string telanjang).
8. Generic Repair Preservation (Anti-Field-Loss): Jika dalam giliran repair, apakah seluruh field level teratas (termasuk `files`) dan elemen valid sebelumnya dipertahankan tanpa penghapusan atau distorsi (CURRENT VALID STATE + REPAIRED ELEMENT)?
(Catatan: Pre-seal checklist ini adalah panduan penalaran Architect; bukan Acceptance Authority dan tidak menggantikan validator deterministik).
Tuliskan output JSON keputusan semantik arsitektur Anda di dalam penanda === SEMANTIC DECISION JSON === ... === END SEMANTIC DECISION JSON === (atau penanda === BLUEPRINT JSON === ... === END BLUEPRINT JSON ===)."""

    messages = [
        SystemMessage(content=ARCHITECT_SYSTEM_PROMPT),
        HumanMessage(content=prompt)
    ]

    # Pre-invocation Delivery Gate (Section 8: Context Delivery Integrity)
    if is_repair_turn:
        try:
            from ..architect_preservation import validate_architect_repair_context_delivery
        except (ImportError, ValueError):
            try:
                from architect_preservation import validate_architect_repair_context_delivery
            except ImportError:
                validate_architect_repair_context_delivery = None

        if validate_architect_repair_context_delivery:
            final_delivered_str = messages[1].content if len(messages) > 1 else prompt
            deliv_ok, deliv_errs = validate_architect_repair_context_delivery(final_delivered_str)
            rec_budget = resolve_b2_context_budget(state) if resolve_b2_context_budget else 12000
            if not deliv_ok:
                # Attempt deterministic recovery pass on prompt
                if assemble_and_distill_b2_repair_prompt:
                    b2_deliv = assemble_and_distill_b2_repair_prompt(state, budget_override=rec_budget)
                    if b2_deliv.delivery_valid and len(b2_deliv.prompt) <= rec_budget:
                        recovered_prompt = prompt.replace(decision_text, f"\n{b2_deliv.prompt}\n") if decision_text else f"{prompt}\n\n{b2_deliv.prompt}"
                        rec_ok, rec_errs = validate_architect_repair_context_delivery(recovered_prompt)
                        if rec_ok:
                            prompt = recovered_prompt
                            messages = [
                                SystemMessage(content=ARCHITECT_SYSTEM_PROMPT),
                                HumanMessage(content=prompt)
                            ]
                            deliv_ok = True
                        else:
                            deliv_errs = rec_errs
                elif build_architect_decision_context and decision_ctx:
                    recovered_ctx, rec_telem = build_architect_decision_context(state, pkg=pkg, max_chars=rec_budget)
                    if recovered_ctx:
                        recovered_prompt = prompt.replace(decision_text, f"\n{recovered_ctx}\n")
                        rec_ok, rec_errs = validate_architect_repair_context_delivery(recovered_prompt)
                        if rec_ok:
                            prompt = recovered_prompt
                            messages = [
                                SystemMessage(content=ARCHITECT_SYSTEM_PROMPT),
                                HumanMessage(content=prompt)
                            ]
                            deliv_ok = True
                        else:
                            deliv_errs = rec_errs

            if not deliv_ok:
                # Structured DELIVERY_FAILURE (Correction 1):
                # No LLM invocation occurs and no Architect repair turn is consumed.
                new_log = f"[System Architect]: DELIVERY_FAILURE — Pre-invocation context delivery check failed: {deliv_errs}"
                current_logs = state.get("logs", [])
                if tracer and ContextTelemetry and emit_context_telemetry:
                    import dataclasses
                    known_fields = {f.name for f in dataclasses.fields(ContextTelemetry)}
                    filtered_telem_data = {k: v for k, v in telem_data.items() if k in known_fields}
                    fail_telem = ContextTelemetry(
                        agent="architect",
                        model=str(state.get("model_name", "")),
                        context_version="hardening_v1",
                        context_sections=list(telem_data.get("context_sections", [])),
                        context_size=len(prompt),
                        authoritative_sources=["FROZEN_ORACLE"],
                        evidence_items=telem_data.get("evidence_items", 0),
                        locked_invariants=telem_data.get("locked_invariants", 0),
                        current_failures=telem_data.get("current_failures", 0),
                        repair_boundary_items=telem_data.get("repair_boundary_items", 0),
                        delivery_valid=False,
                        delivery_errors=deliv_errs,
                        delivery_failure_reason="; ".join(deliv_errs),
                        run_id=str(state.get("run_id", "")),
                        iteration=state.get("contract_revision_count", 0),
                        **{k: v for k, v in filtered_telem_data.items() if k not in (
                            "agent", "model", "context_version", "context_sections", "context_size",
                            "authoritative_sources", "evidence_items", "locked_invariants",
                            "current_failures", "repair_boundary_items", "delivery_valid",
                            "delivery_errors", "delivery_failure_reason", "run_id", "iteration"
                        )}
                    )
                    emit_context_telemetry(tracer, "architect", fail_telem)

                return {
                    "architecture_plan": "",
                    "architectural_blueprint": None,
                    "contract": state.get("contract"),
                    "contract_status": "DELIVERY_FAILURE",
                    "contract_validation_errors": deliv_errs,
                    "blueprint_revision_count": state.get("blueprint_revision_count", 0),
                    "status": "DELIVERY_FAILURE",
                    "delivery_valid": False,
                    "delivery_errors": deliv_errs,
                    "delivery_failure_reason": "; ".join(deliv_errs),
                    "logs": current_logs + [new_log]
                }
    
    # Initialize draft contract and language parameters
    draft_contract = state.get("contract")
    if not draft_contract or not isinstance(draft_contract, dict):
        draft_contract = create_draft_contract(
            raw_intent=user_task,
            target_language=target_lang,
            goal_summary=user_task[:120]
        )

    is_dart = "dart" in target_lang.lower() or "flutter" in target_lang.lower()
    default_auth_file = "lib/card_metric.dart" if is_dart else "main.py"

    # Treatment #1.8.6: Two-Stage Execution Engine
    # STAGE A: Acceptance Obligation Mapping (LLM) -> Deterministic Stage-A Check (Pure Python)
    # STAGE B: Architectural Assembly (LLM) -> Stage-B Preservation Check -> Deterministic Serialization
    use_staged = (parse_stage_a_mappings is not None and validate_stage_a_mappings is not None)
    
    stage_a_coverage = 0.0
    stage_a_valid = False
    stage_a_repairs = 0
    stage_b_completeness = 0.0
    stage_b_repairs = 0
    stage_b1_valid = False
    stage_b1_repairs = 0
    stage_b2_valid = False
    stage_b2_repairs = 0
    serialization_success = False
    b_decoder_telem = {}
    b2_delivery_telemetry = None
    b2_pre_snapshot = None

    mappings_a = None
    assembly_b = None
    b1_output = None
    b2_output = None
    raw_stage_a_output = ""
    raw_stage_b_output = ""
    raw_stage_b1_output = ""
    raw_stage_b2_output = ""

    extracted_bp = None
    bp_err = None
    first_divergence = None
    arch_plan = ""

    # Check if Stage A is already frozen from earlier turn
    prev_contract = state.get("contract") or {}
    prev_prov = prev_contract.get("provenance", {}) if isinstance(prev_contract, dict) else {}
    prev_frozen_a_dict = prev_prov.get("frozen_stage_a")
    frozen_stage_a = None
    if prev_frozen_a_dict and isinstance(prev_frozen_a_dict, dict) and "mappings" in prev_frozen_a_dict:
        try:
            m_list = [StageAObligationMapping.from_dict(d) for d in prev_frozen_a_dict["mappings"]]
            frozen_stage_a = FrozenStageAMappings.freeze(m_list, timestamp=prev_frozen_a_dict.get("validated_at"))
            stage_a_valid = True
            stage_a_coverage = 1.0
        except Exception:
            frozen_stage_a = None

    # Check if Stage B-1 is already frozen from earlier turn
    prev_frozen_b1_dict = prev_prov.get("frozen_stage_b1")
    frozen_stage_b1 = None
    if prev_frozen_b1_dict and isinstance(prev_frozen_b1_dict, dict) and "elements" in prev_frozen_b1_dict:
        try:
            e_list = [StageB1ElementRealization.from_dict(d) for d in prev_frozen_b1_dict["elements"]]
            frozen_stage_b1 = FrozenStageB1State.freeze(e_list, timestamp=prev_frozen_b1_dict.get("validated_at"))
            stage_b1_valid = True
        except Exception:
            frozen_stage_b1 = None

    # Check if Stage B-2 is already frozen from earlier turn
    prev_frozen_b2_dict = prev_prov.get("frozen_stage_b2")
    frozen_stage_b2 = None
    if prev_frozen_b2_dict and isinstance(prev_frozen_b2_dict, dict) and "bindings" in prev_frozen_b2_dict:
        try:
            b_list = [StageB2BindingDecision.from_dict(d) for d in prev_frozen_b2_dict["bindings"]]
            s_files = dict(prev_frozen_b2_dict.get("files", {}))
            frozen_stage_b2 = FrozenStageB2State.freeze(b_list, s_files, timestamp=prev_frozen_b2_dict.get("validated_at"))
            stage_b2_valid = True
        except Exception:
            frozen_stage_b2 = None

    # ========================================================================
    # SELECTIVE STAGE-B UNFREEZE (Treatment #1.8.9 Repair Routing v2)
    # On a repair turn, classify which stage owns the Contract Gate failure and
    # invalidate its lifecycle entry (plus dependents). The existing
    # "if frozen_stage_X is None: invoke LLM" guards then fire naturally.
    # Cache Safety Rule: a FROZEN state that is contradicted by downstream
    # evidence must become INVALIDATED and must NOT be restored.
    # ========================================================================
    new_lifecycle: dict = {}
    _repair_failure_owner: str = ""
    _repair_invalidate_stages: list = []
    _repair_evidence_summary: str = ""
    _repair_causal_category: str = "NONE"
    _repair_outer_category: str = "NONE"
    _repair_target_owner: str = "NONE"
    _invoked_stage: str = "NONE"

    # Snapshot frozen states BEFORE lifecycle is applied (for telemetry hashes)
    _pre_lifecycle_frozen_a = frozen_stage_a
    _pre_lifecycle_frozen_b1 = frozen_stage_b1
    _pre_lifecycle_frozen_b2 = frozen_stage_b2

    _gate_errors_this_turn = list(state.get("contract_validation_errors") or [])

    if (
        is_repair_turn
        and _gate_errors_this_turn
        and classify_contract_failure_owner is not None
        and compute_stage_lifecycle is not None
        and apply_lifecycle_to_frozen_states is not None
    ):
        _clf_res = classify_contract_failure_owner(
            gate_errors=_gate_errors_this_turn,
            violations=[],
            coverage_matrix={},
        )
        _repair_failure_owner = _clf_res.owner
        _repair_invalidate_stages = _clf_res.invalidate_stages
        _repair_evidence_summary = _clf_res.evidence_summary
        _repair_causal_category = getattr(_clf_res, "causal_category", _clf_res.owner)
        _repair_outer_category = getattr(_clf_res, "outer_category", "NONE")
        _repair_target_owner = getattr(_clf_res, "repair_owner", "NONE")

        new_lifecycle = compute_stage_lifecycle(
            prev_lifecycle=prev_prov.get("stage_lifecycle", {}),
            failure_owner=_repair_failure_owner,
            invalidate_stages=_repair_invalidate_stages,
            gate_errors=_gate_errors_this_turn,
        )
        frozen_stage_a, frozen_stage_b1, frozen_stage_b2 = apply_lifecycle_to_frozen_states(
            frozen_stage_a, frozen_stage_b1, frozen_stage_b2, new_lifecycle
        )
        # Sync validity flags: if a state was nulled, mark its validity flag False
        if frozen_stage_a is None:
            stage_a_valid = False
            stage_a_coverage = 0.0
        if frozen_stage_b1 is None:
            stage_b1_valid = False
        if frozen_stage_b2 is None:
            stage_b2_valid = False
    else:
        # Not a repair turn (or classifier unavailable): preserve previous lifecycle as-is
        new_lifecycle = dict(prev_prov.get("stage_lifecycle", {}))

    # Retrieve authoritative obligations
    auth_obs_list = []
    try:
        f_oracle_path = state.get("frozen_oracle_path")
        t_files = state.get("test_files")
        auth_obs_list = extract_canonical_oracle_obligations(
            frozen_oracle_path=f_oracle_path,
            test_files=t_files
        ) or []
    except Exception:
        auth_obs_list = []
    if not auth_obs_list:
        auth_obs_list = [{"obligation_id": "REQ-01", "description": user_task}]

    if use_staged and (frozen_stage_a is None):
        # ====================================================================
        # STAGE A: ACCEPTANCE OBLIGATION MAPPING
        # ====================================================================
        prompt_a = build_stage_a_prompt(
            target_lang=target_lang,
            user_task=user_task,
            specs=specs,
            oracle_ledger=oracle_ledger_section,
            oracle_scenarios=oracle_scenario_section,
            v0_model=state.get("v0_requirement_model"),
            existing_state=state.get("contract"),
            repair_errors=state.get("contract_validation_errors") if (is_repair_turn and new_lifecycle.get("stage_a", {}).get("status") == "INVALIDATED") else None,
            repair_packet=pkg,
            authoritative_obligations=auth_obs_list,
            current_mappings=mappings_a
        )
        messages_a = [
            SystemMessage(content=STAGE_A_SYSTEM_PROMPT),
            HumanMessage(content=prompt_a)
        ]
        resp_a = llm.invoke(messages_a)
        _invoked_stage = "STAGE_A"
        raw_a = resp_a.content if hasattr(resp_a, "content") else str(resp_a)
        raw_stage_a_output = raw_a

        # Check if model returned direct blueprint or raw mock (fallback compatibility for mock tests)
        if ("=== STAGE A: OBLIGATION MAPPING ===" not in raw_a) and ("obligation_mappings" not in raw_a):
            is_semantic = ("=== SEMANTIC DECISION JSON ===" in raw_a) or ("semantic_decisions" in raw_a)
            if is_semantic and parse_semantic_architectural_plan and serialize_semantic_decision_to_blueprint:
                sem_plan, sem_errs = parse_semantic_architectural_plan(raw_a)
                if sem_plan and not sem_errs:
                    extracted_bp, ser_errs = serialize_semantic_decision_to_blueprint(sem_plan)
                    if ser_errs:
                        bp_err = "; ".join(ser_errs)
                        first_divergence = "SERIALIZATION_FAILURE"
                        arch_plan = raw_a
                    elif extracted_bp:
                        serialization_success = True
                        arch_plan = serialize_blueprint_to_canonical_json(extracted_bp)
                else:
                    bp_err = "; ".join(sem_errs)
                    first_divergence = "SEMANTIC_MAPPING_FAILURE"
                    arch_plan = raw_a
            if extracted_bp is None and not is_semantic:
                extracted_bp, bp_err = parse_blueprint_json(raw_a)
                if bp_err:
                    first_divergence = "CONTRACT_VALIDATION_FAILURE"
                    arch_plan = raw_a
                elif extracted_bp:
                    arch_plan = serialize_blueprint_to_canonical_json(extracted_bp)
            use_staged = False
        else:
            mappings_a, parse_errs_a = parse_stage_a_mappings(raw_a)
            val_errs_a = []
            if mappings_a:
                is_valid_a, val_errs_a = validate_stage_a_mappings(mappings_a, auth_obs_list)
            else:
                is_valid_a = False
                val_errs_a = parse_errs_a or ["Failed to parse Stage A mappings"]

            # Isolated Stage A Repair Loop (Max 1 retry within turn if invalid)
            if not is_valid_a:
                stage_a_repairs += 1
                repair_prompt_a = build_stage_a_prompt(
                    target_lang=target_lang,
                    user_task=user_task,
                    specs=specs,
                    oracle_ledger=oracle_ledger_section,
                    oracle_scenarios=oracle_scenario_section,
                    v0_model=state.get("v0_requirement_model"),
                    existing_state=state.get("contract"),
                    repair_errors=val_errs_a,
                    repair_packet=pkg,
                    authoritative_obligations=auth_obs_list,
                    current_mappings=mappings_a
                )
                resp_a_rep = llm.invoke([
                    SystemMessage(content=STAGE_A_SYSTEM_PROMPT),
                    HumanMessage(content=repair_prompt_a)
                ])
                raw_a_rep = resp_a_rep.content if hasattr(resp_a_rep, "content") else str(resp_a_rep)
                raw_stage_a_output += f"\n=== STAGE A REPAIR OUTPUT ===\n{raw_a_rep}\n"
                m_rep, p_rep_errs = parse_stage_a_mappings(raw_a_rep)
                if m_rep:
                    is_valid_a, val_errs_a = validate_stage_a_mappings(m_rep, auth_obs_list)
                    if is_valid_a:
                        mappings_a = m_rep

            if is_valid_a and mappings_a:
                stage_a_valid = True
                stage_a_coverage = 1.0
                frozen_stage_a = FrozenStageAMappings.freeze(mappings_a)
            else:
                first_divergence = "STAGE_A_MAPPING_FAILURE"
                bp_err = "; ".join(val_errs_a)

    # ====================================================================
    # STAGE B: DECOMPOSED ARCHITECTURAL DECISIONS (Treatment #1.8.9)
    # Stage B-1: Element Realization -> Deterministic B1 Gate
    # Stage B-2: Relationship / Binding Decisions -> Deterministic B2 Gate
    # Stage B-3: Deterministic Artifact Assembly
    # ====================================================================
    if use_staged and frozen_stage_a is not None:
        # ----------------------------------------------------------------
        # 1. STAGE B-1: ELEMENT REALIZATION (Zero source code)
        # ----------------------------------------------------------------
        if frozen_stage_b1 is None:
            prompt_b1 = build_stage_b1_prompt(
                target_lang=target_lang,
                user_task=user_task,
                specs=specs,
                frozen_stage_a=frozen_stage_a,
                repair_errors=state.get("contract_validation_errors") if (is_repair_turn and new_lifecycle.get("stage_b1", {}).get("status") == "INVALIDATED") else None,
                current_b1=b1_output
            )
            messages_b1 = [
                SystemMessage(content=STAGE_B1_SYSTEM_PROMPT),
                HumanMessage(content=prompt_b1)
            ]
            resp_b1 = llm.invoke(messages_b1)
            _invoked_stage = "STAGE_B1"
            raw_b1 = resp_b1.content if hasattr(resp_b1, "content") else str(resp_b1)
            raw_stage_b1_output = raw_b1

            # Fallback backward compatibility: if model emitted unified stage B directly
            if ("=== STAGE B-1" not in raw_b1) and ("element_realizations" not in raw_b1) and (
                ("=== STAGE B:" in raw_b1) or ("semantic_decisions" in raw_b1)
            ):
                raw_stage_b_output = raw_b1
                assembly_b, parse_errs_b = parse_stage_b_assembly(raw_b1)
                if assembly_b:
                    b_valid, b_pres_errs, rev_requests = validate_stage_b_preservation(frozen_stage_a, assembly_b)
                    if b_valid:
                        stage_b_completeness = 1.0
                        stage_b1_valid = True
                        stage_b2_valid = True
                        extracted_bp, asm_errs = assemble_stage_b_blueprint(
                            frozen_stage_a=frozen_stage_a,
                            assembly=assembly_b,
                            task_id=user_task[:30],
                            target_language=target_lang
                        )
                        if extracted_bp and not asm_errs:
                            serialization_success = True
                            arch_plan = serialize_blueprint_to_canonical_json(extracted_bp)

            if extracted_bp is None:
                b1_output, parse_errs_b1 = parse_stage_b1_output(raw_b1)
                is_valid_b1 = False
                val_errs_b1 = []
                if b1_output:
                    is_valid_b1, val_errs_b1 = validate_stage_b1_realization(frozen_stage_a, b1_output)
                else:
                    val_errs_b1 = parse_errs_b1 or ["Failed to parse Stage B-1 element realization output."]

                # Isolated Stage B-1 Repair Loop (Max 1 retry within turn)
                if not is_valid_b1:
                    stage_b1_repairs += 1
                    repair_prompt_b1 = build_stage_b1_prompt(
                        target_lang=target_lang,
                        user_task=user_task,
                        specs=specs,
                        frozen_stage_a=frozen_stage_a,
                        repair_errors=val_errs_b1,
                        current_b1=b1_output
                    )
                    resp_b1_rep = llm.invoke([
                        SystemMessage(content=STAGE_B1_SYSTEM_PROMPT),
                        HumanMessage(content=repair_prompt_b1)
                    ])
                    raw_b1_rep = resp_b1_rep.content if hasattr(resp_b1_rep, "content") else str(resp_b1_rep)
                    raw_stage_b1_output += f"\n=== STAGE B-1 REPAIR OUTPUT ===\n{raw_b1_rep}\n"
                    b1_rep, p_errs_rep = parse_stage_b1_output(raw_b1_rep)
                    if b1_rep:
                        is_valid_b1, val_errs_b1 = validate_stage_b1_realization(frozen_stage_a, b1_rep)
                        if is_valid_b1:
                            b1_output = b1_rep

                if is_valid_b1 and b1_output:
                    stage_b1_valid = True
                    frozen_stage_b1 = FrozenStageB1State.freeze(b1_output.elements)
                else:
                    first_divergence = "STAGE_B1_REALIZATION_FAILURE"
                    bp_err = "; ".join(val_errs_b1)

        # ----------------------------------------------------------------
        # 2. STAGE B-2: RELATIONSHIP / BINDING DECISIONS (Only if B-1 is valid)
        # ----------------------------------------------------------------
        if extracted_bp is None and frozen_stage_b1 is not None and frozen_stage_b2 is None:
            is_b2_turn_repair = bool(is_repair_turn and new_lifecycle.get("stage_b2", {}).get("status") == "INVALIDATED")
            b2_repair_errs = state.get("contract_validation_errors") if is_b2_turn_repair else None

            # B2 Repair Delivery v2: Snapshot pre-repair state and enforce delivery validation
            if is_b2_turn_repair and snapshot_b2_repair_pre_state is not None:
                b2_pre_snapshot = snapshot_b2_repair_pre_state(state)

            if is_b2_turn_repair and assemble_and_distill_b2_repair_prompt is not None:
                b2_deliv_res = assemble_and_distill_b2_repair_prompt(
                    state=state,
                    repair_errors=b2_repair_errs,
                    repair_attempt=stage_b2_repairs + 1
                )
                b2_delivery_telemetry = b2_deliv_res.telemetry
                # Section 10: Invocation Invariants
                # repair_owner == B2, invoked_stage == B2, delivery_valid == True, repair_attempt == N
                if not b2_deliv_res.delivery_valid:
                    # Structured DELIVERY_FAILURE:
                    # No LLM invocation occurs and no Architect repair turn is consumed.
                    # Do NOT fall back to Stage A or B-1.
                    new_log = f"[System Architect]: DELIVERY_FAILURE — Stage B-2 repair context delivery check failed: {b2_deliv_res.validation_errors}"
                    current_logs = state.get("logs", [])
                    return {
                        "architecture_plan": "",
                        "architectural_blueprint": None,
                        "contract": state.get("contract"),
                        "contract_status": "DELIVERY_FAILURE",
                        "contract_validation_errors": b2_deliv_res.validation_errors,
                        "blueprint_revision_count": state.get("blueprint_revision_count", 0),
                        "status": "DELIVERY_FAILURE",
                        "delivery_valid": False,
                        "delivery_errors": b2_deliv_res.validation_errors,
                        "delivery_failure_reason": "; ".join(b2_deliv_res.validation_errors),
                        "b2_delivery_telemetry": b2_delivery_telemetry,
                        "logs": current_logs + [new_log]
                    }
                prompt_b2 = b2_deliv_res.prompt
            else:
                prompt_b2 = build_stage_b2_prompt(
                    target_lang=target_lang,
                    user_task=user_task,
                    specs=specs,
                    frozen_stage_a=frozen_stage_a,
                    frozen_b1=frozen_stage_b1,
                    scenarios=oracle_scenario_section,
                    repair_errors=b2_repair_errs,
                    current_b2=b2_output,
                    state=state,
                    repair_attempt=stage_b2_repairs + 1
                )

            messages_b2 = [
                SystemMessage(content=STAGE_B2_SYSTEM_PROMPT),
                HumanMessage(content=prompt_b2)
            ]
            resp_b2 = llm.invoke(messages_b2)
            _invoked_stage = "STAGE_B2"
            raw_b2 = resp_b2.content if hasattr(resp_b2, "content") else str(resp_b2)
            raw_stage_b2_output = raw_b2

            b2_output, parse_errs_b2 = parse_stage_b2_output(raw_b2)
            is_valid_b2 = False
            val_errs_b2 = []
            if b2_output:
                is_valid_b2, val_errs_b2 = validate_stage_b2_bindings(frozen_stage_a, frozen_stage_b1, b2_output)
            else:
                val_errs_b2 = parse_errs_b2 or ["Failed to parse Stage B-2 relationship binding output."]

            # Isolated Stage B-2 Repair Loop (Max 1 retry within turn, keeping B-1 locked)
            if not is_valid_b2:
                stage_b2_repairs += 1
                if assemble_and_distill_b2_repair_prompt is not None:
                    retry_deliv = assemble_and_distill_b2_repair_prompt(
                        state=state,
                        repair_errors=val_errs_b2,
                        repair_attempt=stage_b2_repairs
                    )
                    b2_delivery_telemetry = retry_deliv.telemetry
                    repair_prompt_b2 = retry_deliv.prompt if retry_deliv.delivery_valid else None
                else:
                    repair_prompt_b2 = build_stage_b2_prompt(
                        target_lang=target_lang,
                        user_task=user_task,
                        specs=specs,
                        frozen_stage_a=frozen_stage_a,
                        frozen_b1=frozen_stage_b1,
                        scenarios=oracle_scenario_section,
                        repair_errors=val_errs_b2,
                        current_b2=b2_output,
                        state=state,
                        repair_attempt=stage_b2_repairs
                    )

                if repair_prompt_b2:
                    resp_b2_rep = llm.invoke([
                        SystemMessage(content=STAGE_B2_SYSTEM_PROMPT),
                        HumanMessage(content=repair_prompt_b2)
                    ])
                    raw_b2_rep = resp_b2_rep.content if hasattr(resp_b2_rep, "content") else str(resp_b2_rep)
                    raw_stage_b2_output += f"\n=== STAGE B-2 REPAIR OUTPUT ===\n{raw_b2_rep}\n"
                    b2_rep, p_errs_b2_rep = parse_stage_b2_output(raw_b2_rep)
                    if b2_rep:
                        is_valid_b2, val_errs_b2 = validate_stage_b2_bindings(frozen_stage_a, frozen_stage_b1, b2_rep)
                        if is_valid_b2:
                            b2_output = b2_rep

            if is_valid_b2 and b2_output:
                stage_b2_valid = True
                frozen_stage_b2 = FrozenStageB2State.freeze(b2_output.bindings, b2_output.scaffold_files)
            else:
                first_divergence = "STAGE_B2_BINDING_FAILURE"
                bp_err = "; ".join(val_errs_b2)

            # Section 11 State Preservation Invariant Verification
            if is_b2_turn_repair and b2_pre_snapshot is not None and verify_b2_stage_preservation is not None:
                _b2_pres_ok, _b2_pres_errs = verify_b2_stage_preservation(b2_pre_snapshot, state)
                if not _b2_pres_ok:
                    contract_errors.extend(_b2_pres_errs)
                    first_divergence = "STATE_PRESERVATION_REGRESSION"
                    bp_err = "; ".join(_b2_pres_errs)
                    extracted_bp = None
                    is_valid_b2 = False

            # Section 7 State Preservation Invariant
            if is_repair_turn and verify_stage_preservation is not None:
                _pres_ok, _pres_errs = verify_stage_preservation(
                    pre_lifecycle_frozen_a=_pre_lifecycle_frozen_a,
                    pre_lifecycle_frozen_b1=_pre_lifecycle_frozen_b1,
                    post_repair_frozen_a=frozen_stage_a,
                    post_repair_frozen_b1=frozen_stage_b1,
                    failure_owner=_repair_failure_owner,
                )
                if not _pres_ok:
                    contract_errors.extend(_pres_errs)
                    first_divergence = "STATE_PRESERVATION_REGRESSION"
                    bp_err = "; ".join(_pres_errs)
                    extracted_bp = None

        # ----------------------------------------------------------------
        # 3. STAGE B-3: DETERMINISTIC ARTIFACT ASSEMBLY
        # ----------------------------------------------------------------
        if extracted_bp is None and frozen_stage_b1 is not None and frozen_stage_b2 is not None:
            b2_effective = b2_output or StageB2Output(
                bindings=list(frozen_stage_b2.bindings),
                scaffold_files=dict(frozen_stage_b2.scaffold_files)
            )
            extracted_bp, asm_errs = assemble_decomposed_stage_b_blueprint(
                frozen_stage_a=frozen_stage_a,
                b1_state=frozen_stage_b1,
                b2_state=b2_effective,
                task_id=user_task[:30],
                target_language=target_lang
            )
            if extracted_bp and not asm_errs:
                stage_b_completeness = 1.0
                serialization_success = True
                arch_plan = serialize_blueprint_to_canonical_json(extracted_bp)
            else:
                bp_err = "; ".join(asm_errs)
                first_divergence = "STAGE_B3_ASSEMBLY_FAILURE"

        if not raw_stage_b_output:
            raw_stage_b_output = f"{raw_stage_b1_output}\n{raw_stage_b2_output}".strip()

        b_decoder_telem = {
            "decoder_mode": "DECOMPOSED_B1_B2_B3",
            "b1_valid": stage_b1_valid,
            "b1_repair_count": stage_b1_repairs,
            "b2_valid": stage_b2_valid,
            "b2_repair_count": stage_b2_repairs,
            "stage": "STAGE_B"
        }

    # Legacy/Fallback direct invocation if not staged or if staged was bypassed
    if extracted_bp is None and not use_staged:
        response = llm.invoke(messages)
        raw_direct = response.content if hasattr(response, "content") else str(response)

        is_semantic_output = ("=== SEMANTIC DECISION JSON ===" in raw_direct) or ("semantic_decisions" in raw_direct)
        if is_semantic_output and parse_semantic_architectural_plan and serialize_semantic_decision_to_blueprint:
            sem_plan, sem_errs = parse_semantic_architectural_plan(raw_direct)
            if sem_plan and not sem_errs:
                extracted_bp, ser_errs = serialize_semantic_decision_to_blueprint(sem_plan)
                if ser_errs:
                    bp_err = "; ".join(ser_errs)
                    first_divergence = "SERIALIZATION_FAILURE"
                    arch_plan = raw_direct
                elif extracted_bp:
                    serialization_success = True
                    arch_plan = serialize_blueprint_to_canonical_json(extracted_bp)
            else:
                bp_err = "; ".join(sem_errs)
                first_divergence = "SEMANTIC_MAPPING_FAILURE"
                arch_plan = raw_direct

        if extracted_bp is None and not is_semantic_output:
            extracted_bp, bp_err = parse_blueprint_json(raw_direct)
            if bp_err:
                first_divergence = "CONTRACT_VALIDATION_FAILURE"
                arch_plan = raw_direct
            elif extracted_bp:
                arch_plan = serialize_blueprint_to_canonical_json(extracted_bp)

    contract_errors = []

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

                # Deterministic State Invariant: architecture_plan must be valid canonical ArchitecturalBlueprint JSON
                if serialization_success or arch_plan:
                    is_rep_valid, rep_errs = validate_canonical_architecture_plan_state(
                        architecture_plan=arch_plan,
                        canonical_blueprint=extracted_bp,
                        contract=aligned_contract
                    )
                    if not is_rep_valid:
                        status_label = "STATE_REPRESENTATION_FAILURE"
                        contract_errors.extend(rep_errs)
                        aligned_contract["status"] = "STATE_REPRESENTATION_FAILURE"
                        if "provenance" not in aligned_contract or not isinstance(aligned_contract["provenance"], dict):
                            aligned_contract["provenance"] = {}
                        aligned_contract["provenance"]["active_validation_errors"] = list(contract_errors)
                        aligned_contract["provenance"]["contract_validation_errors"] = list(contract_errors)
                        first_divergence = "STATE_REPRESENTATION_FAILURE"

            if use_staged:
                if "provenance" not in aligned_contract or not isinstance(aligned_contract["provenance"], dict):
                    aligned_contract["provenance"] = {}
                aligned_contract["provenance"]["raw_stage_a_output"] = raw_stage_a_output
                aligned_contract["provenance"]["raw_stage_b_output"] = raw_stage_b_output
                aligned_contract["provenance"]["raw_stage_b1_output"] = raw_stage_b1_output
                aligned_contract["provenance"]["raw_stage_b2_output"] = raw_stage_b2_output
                aligned_contract["provenance"]["staged_metrics"] = {
                    "stage_a_coverage": stage_a_coverage,
                    "stage_a_valid": stage_a_valid,
                    "stage_a_repair_count": stage_a_repairs,
                    "stage_b_completeness": stage_b_completeness,
                    "stage_b_repair_count": stage_b_repairs,
                    "stage_b1_valid": stage_b1_valid,
                    "stage_b1_repair_count": stage_b1_repairs,
                    "stage_b2_valid": stage_b2_valid,
                    "stage_b2_repair_count": stage_b2_repairs,
                    "serialization_success": serialization_success,
                    "first_divergence": first_divergence,
                    "decoder_mode": b_decoder_telem.get("decoder_mode", "DECOMPOSED_B1_B2_B3"),
                    "parse_success": b_decoder_telem.get("parse_success", True),
                    "parse_failure_type": b_decoder_telem.get("parse_failure_type"),
                    "stage": "STAGE_B"
                }
                if b2_delivery_telemetry:
                    aligned_contract["provenance"]["b2_delivery_telemetry"] = b2_delivery_telemetry
                    aligned_contract["provenance"]["staged_metrics"]["b2_delivery_telemetry"] = b2_delivery_telemetry
                if frozen_stage_a:
                    aligned_contract["provenance"]["frozen_stage_a"] = {
                        "mappings": [m.to_dict() for m in frozen_stage_a.mappings],
                        "sha256_seal": frozen_stage_a.sha256_seal,
                        "validated_at": frozen_stage_a.validated_at
                    }
                if frozen_stage_b1:
                    aligned_contract["provenance"]["frozen_stage_b1"] = {
                        "elements": [e.to_dict() for e in frozen_stage_b1.elements],
                        "sha256_seal": frozen_stage_b1.sha256_seal,
                        "validated_at": frozen_stage_b1.validated_at
                    }
                if frozen_stage_b2:
                    aligned_contract["provenance"]["frozen_stage_b2"] = {
                        "bindings": [b.to_dict() for b in frozen_stage_b2.bindings],
                        "files": dict(frozen_stage_b2.scaffold_files),
                        "sha256_seal": frozen_stage_b2.sha256_seal,
                        "validated_at": frozen_stage_b2.validated_at
                    }
                # Lifecycle and repair telemetry
                aligned_contract["provenance"]["stage_lifecycle"] = new_lifecycle
                if build_repair_telemetry is not None:
                    aligned_contract["provenance"]["repair_telemetry"] = build_repair_telemetry(
                        is_repair_turn=is_repair_turn,
                        stage_lifecycle=new_lifecycle,
                        pre_lifecycle_frozen_a=_pre_lifecycle_frozen_a,
                        pre_lifecycle_frozen_b1=_pre_lifecycle_frozen_b1,
                        pre_lifecycle_frozen_b2=_pre_lifecycle_frozen_b2,
                        post_lifecycle_frozen_a=frozen_stage_a,
                        post_lifecycle_frozen_b1=frozen_stage_b1,
                        post_lifecycle_frozen_b2=frozen_stage_b2,
                        new_frozen_b1=frozen_stage_b1 if new_lifecycle.get("stage_b1", {}).get("status") == "INVALIDATED" else None,
                        new_frozen_b2=frozen_stage_b2 if new_lifecycle.get("stage_b2", {}).get("status") == "INVALIDATED" else None,
                        causal_failure_category=_repair_causal_category,
                        outer_error_category=_repair_outer_category,
                        repair_owner=_repair_target_owner,
                        invoked_stage=_invoked_stage,
                        repair_attempt=state.get("contract_revision_count", 0),
                    )
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
        if first_divergence:
            aligned_contract["provenance"]["first_divergence"] = first_divergence
        if use_staged:
            aligned_contract["provenance"]["raw_stage_a_output"] = raw_stage_a_output
            aligned_contract["provenance"]["raw_stage_b_output"] = raw_stage_b_output
            aligned_contract["provenance"]["raw_stage_b1_output"] = raw_stage_b1_output
            aligned_contract["provenance"]["raw_stage_b2_output"] = raw_stage_b2_output
            aligned_contract["provenance"]["staged_metrics"] = {
                "stage_a_coverage": stage_a_coverage,
                "stage_a_valid": stage_a_valid,
                "stage_a_repair_count": stage_a_repairs,
                "stage_b_completeness": stage_b_completeness,
                "stage_b_repair_count": stage_b_repairs,
                "stage_b1_valid": stage_b1_valid,
                "stage_b1_repair_count": stage_b1_repairs,
                "stage_b2_valid": stage_b2_valid,
                "stage_b2_repair_count": stage_b2_repairs,
                "serialization_success": serialization_success,
                "first_divergence": first_divergence,
                "decoder_mode": b_decoder_telem.get("decoder_mode", "DECOMPOSED_B1_B2_B3"),
                "parse_success": b_decoder_telem.get("parse_success", False),
                "parse_failure_type": b_decoder_telem.get("parse_failure_type"),
                "stage": "STAGE_B"
            }
            if b2_delivery_telemetry:
                aligned_contract["provenance"]["b2_delivery_telemetry"] = b2_delivery_telemetry
                aligned_contract["provenance"]["staged_metrics"]["b2_delivery_telemetry"] = b2_delivery_telemetry
            if frozen_stage_a:
                aligned_contract["provenance"]["frozen_stage_a"] = {
                    "mappings": [m.to_dict() for m in frozen_stage_a.mappings],
                    "sha256_seal": frozen_stage_a.sha256_seal,
                    "validated_at": frozen_stage_a.validated_at
                }
            if frozen_stage_b1:
                aligned_contract["provenance"]["frozen_stage_b1"] = {
                    "elements": [e.to_dict() for e in frozen_stage_b1.elements],
                    "sha256_seal": frozen_stage_b1.sha256_seal,
                    "validated_at": frozen_stage_b1.validated_at
                }
            if frozen_stage_b2:
                aligned_contract["provenance"]["frozen_stage_b2"] = {
                    "bindings": [b.to_dict() for b in frozen_stage_b2.bindings],
                    "files": dict(frozen_stage_b2.scaffold_files),
                    "sha256_seal": frozen_stage_b2.sha256_seal,
                    "validated_at": frozen_stage_b2.validated_at
                }
            # Lifecycle and repair telemetry (failure path)
            aligned_contract["provenance"]["stage_lifecycle"] = new_lifecycle
            if build_repair_telemetry is not None:
                aligned_contract["provenance"]["repair_telemetry"] = build_repair_telemetry(
                    is_repair_turn=is_repair_turn,
                    stage_lifecycle=new_lifecycle,
                    pre_lifecycle_frozen_a=_pre_lifecycle_frozen_a,
                    pre_lifecycle_frozen_b1=_pre_lifecycle_frozen_b1,
                    pre_lifecycle_frozen_b2=_pre_lifecycle_frozen_b2,
                    post_lifecycle_frozen_a=frozen_stage_a,
                    post_lifecycle_frozen_b1=frozen_stage_b1,
                    post_lifecycle_frozen_b2=frozen_stage_b2,
                    new_frozen_b1=frozen_stage_b1 if new_lifecycle.get("stage_b1", {}).get("status") == "INVALIDATED" else None,
                    new_frozen_b2=frozen_stage_b2 if new_lifecycle.get("stage_b2", {}).get("status") == "INVALIDATED" else None,
                    causal_failure_category=_repair_causal_category,
                    outer_error_category=_repair_outer_category,
                    repair_owner=_repair_target_owner,
                    invoked_stage=_invoked_stage,
                    repair_attempt=state.get("contract_revision_count", 0),
                )
        val_hist = list(aligned_contract["provenance"].get("validation_history") or [])

        val_hist.append({
            "timestamp": datetime.now().isoformat(),
            "phase": "ARCHITECT_BLUEPRINT_PARSE",
            "status": "REJECTED",
            "errors": list(contract_errors)
        })
        aligned_contract["provenance"]["validation_history"] = val_hist

    # Observability: Catat penyelarasan kontrak ALIGNED / REJECTED / STATE_REPRESENTATION_FAILURE
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

    stage_a_semantic_dict = None
    if frozen_stage_a:
        stage_a_semantic_dict = {
            "mappings": [m.to_dict() for m in frozen_stage_a.mappings],
            "sha256_seal": frozen_stage_a.sha256_seal,
            "validated_at": frozen_stage_a.validated_at
        }
    elif mappings_a:
        stage_a_semantic_dict = {
            "mappings": [m.to_dict() for m in mappings_a]
        }

    stage_b_semantic_dict = None
    if assembly_b:
        stage_b_semantic_dict = assembly_b.to_dict() if hasattr(assembly_b, "to_dict") else asdict(assembly_b)

    ret_status = "STATE_REPRESENTATION_FAILURE" if status_label == "STATE_REPRESENTATION_FAILURE" else "architect_done"

    return {
        "architecture_plan": arch_plan,
        "architectural_blueprint": bp_dict,
        "canonical_blueprint": bp_dict,
        "stage_a_semantic": stage_a_semantic_dict,
        "stage_b_semantic": stage_b_semantic_dict,
        "contract": aligned_contract,
        "contract_status": status_label,
        "contract_validation_errors": contract_errors,
        "blueprint_revision_count": state.get("blueprint_revision_count", 0),
        "status": ret_status,
        "logs": current_logs + [new_log]
    }


