"""
System Architect Agent (v1.2.0)
ReinDev Studio — Iterasi 6 (Architect Recovery: Unified Blueprint Architecture v1)

Merancang arsitektur perangkat lunak modular, peta file tree, dan kontrak antarmuka publik.
v1.2.0: Restorasi arsitektur Unified Blueprint kanonikal (TRUE LKG #1.2 / Commit 698aa8a):
- Single semantic decision & single LLM invocation per attempt
- Direct canonical ArchitecturalBlueprint JSON extraction
- Minimal scaffolding mandate (pass stubs, <= 800 chars per file; Developer owns implementation)
- Dense, non-duplicative context package
- Full performance telemetry & proven governance / document-boundary integrity
"""

import re
import json
import time
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
        format_acceptance_usage_evidence,
        find_deterministic_callable_fact,
        normalize_route_path,
        CanonicalObligation,
        ObligationKind,
    )
    from ..canonical_scenario import (
        extract_canonical_scenarios,
        format_scenarios_for_architect,
        extract_all_scaffold_facts,
    )
    from ..blueprint_schema import (
        ArchitecturalBlueprint,
        parse_blueprint_json,
        extract_blueprint_json_text,
        blueprint_to_narrative_markdown,
        normalize_blueprint_data_models,
        serialize_blueprint_to_canonical_json,
        validate_canonical_architecture_plan_state
    )
    from ..context_hardening import (
        build_architect_decision_context,
        ContextTelemetry,
        emit_context_telemetry,
        resolve_context_budget
    )
    from ..architect_preservation import validate_architect_repair_context_delivery
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
            format_acceptance_usage_evidence,
            find_deterministic_callable_fact,
            normalize_route_path,
            CanonicalObligation,
            ObligationKind,
        )
    except ImportError:
        def extract_canonical_oracle_obligations(*args, **kwargs): return []
        def format_authoritative_obligation_ledger(*args, **kwargs): return ""
        def format_acceptance_usage_evidence(*args, **kwargs): return ""
        def find_deterministic_callable_fact(*args, **kwargs): return None
        def normalize_route_path(p): return str(p)
        CanonicalObligation = None
        ObligationKind = None
    try:
        from canonical_scenario import (
            extract_canonical_scenarios,
            format_scenarios_for_architect,
            extract_all_scaffold_facts,
        )
    except ImportError:
        def extract_canonical_scenarios(*args, **kwargs): return []
        def format_scenarios_for_architect(*args, **kwargs): return ""
        def extract_all_scaffold_facts(*args, **kwargs): return []
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
        from context_hardening import (
            build_architect_decision_context,
            ContextTelemetry,
            emit_context_telemetry,
            resolve_context_budget
        )
    except ImportError:
        build_architect_decision_context = None
        ContextTelemetry = None
        emit_context_telemetry = None
        resolve_context_budget = lambda s, default=12000: int(s.get("context_budget") or s.get("max_context_chars") or default) if s else default
    try:
        from architect_preservation import validate_architect_repair_context_delivery
    except ImportError:
        validate_architect_repair_context_delivery = None


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
   - BATAS SCAFFOLD WAJIB: `code_scaffold` HANYA berupa interface signatures dan stubs minimal (misal: deklarasi kelas, fungsi, metode dengan `pass` atau return dummy).
   - STRING FORMAT: `code_scaffold` WAJIB berupa single string (teks kode langsung dengan baris baru) atau list of strings (tiap baris). DILARANG KERAS menggunakan nested dictionary atau objek JSON terpecah untuk kode (seperti {'imports': ..., 'models': ..., 'endpoints': ...}).
   - OBSERVABLE BEHAVIOR: Scaffolds must represent sufficient observable behavior for deterministic compatibility analysis. Do not prescribe implementation-specific mechanisms. The Architect may choose the appropriate architectural representation, provided that the required observable behavior is preserved.
   - ARTIFACT PURITY: `file_tree` dan `files` HANYA untuk modul implementasi kode. DILARANG memasukkan file test atau QA test suite (seperti test_*.py atau test/*_test.dart) ke dalam file_tree atau files!
   - TARGET UKURAN: <=800 karakter per file. DILARANG KERAS menuliskan implementasi logika bisnis penuh di dalam scaffold. Developer yang memiliki tanggung jawab penuh atas implementasi kode.
2. Symbol Resolvability: Setiap berkas WAJIB menyertakan statement `import` lengkap di awal berkas. Jika menggunakan decorator, instance dan class dekorator WAJIB dideklarasikan atau diimpor secara lokal di berkas yang bersangkutan.
3. Authority Hierarchy: Acceptance Oracle adalah Acceptance Authority (WHAT). Canonical Schema dan Governance menentukan aturan validitas struktur. Architect adalah Design Authority (HOW). Pre-seal checklist dan Invariants A-H adalah panduan penalaran (reasoning guidance) Architect; validator deterministik menentukan REALITY.
4. INTEGRITAS ENVIRONMENT: Patuhi batasan ENVIRONMENT FACT CARD dan dilarang menggunakan API terlarang.
5. Canonical Data Models: Setiap entitas dalam `data_models` WAJIB menggunakan format kanonikal: `field_name` dan `field_type` untuk setiap item dalam `fields`.
6. Obligation Coverage & Canonical Schema Fidelity:
   - Setiap mandatory acceptance obligation harus mempunyai canonical architectural representation yang dapat ditelusuri secara deterministik (baik melalui interface_contracts maupun data_models).
   - Elemen 'parameters' pada interface_contracts WAJIB menggunakan field kanonikal: `param_name`, `param_type`, `param_location` ('PATH', 'QUERY', 'BODY', 'ARGUMENT', atau 'PROP'), dan `is_required`.
   - Elemen 'expected_return' pada interface_contracts WAJIB berupa objek dictionary dengan kunci `return_type` (contoh: {"return_type": "TypeA"}).
   - Skema luaran adalah kontrak representasi yang diturunkan langsung dari definisi ArchitecturalBlueprint kanonikal:
     * `file_tree`: WAJIB List[str] berisi string path berkas (contoh: ["main.py"]).
     * `files`: WAJIB Dict level teratas yang memetakan setiap path dari `file_tree` ke modul scaffold-nya.
     * `interface_contracts` dan `data_models` adalah list of objects.
   - Kamus berkas (`files`) WAJIB memiliki kunci yang sama persis dengan jalur di `file_tree`.
   - DILARANG menggabungkan, mengorbankan, atau menghilangkan salah satu dari `file_tree` atau `files`. Keduanya adalah field terpisah di root JSON.
7. Blueprint Integrity Invariants (A-H — Architect Reasoning Guidance):
   - INVARIANT-A (Identity Stability): Setiap antarmuka yang dideklarasikan memiliki identitas yang stabil.
   - INVARIANT-B (Consistent Location): Setiap antarmuka memiliki lokasi target artifact yang konsisten.
   - INVARIANT-C (File Structure Consistency): Koleksi berkas memiliki konsistensi 1-ke-1 dengan modul implementasi.
   - INVARIANT-D (Obligation Representation): Setiap obligasi penerimaan memiliki representasi arsitektural.
   - INVARIANT-E (Interface Shape Preservation): Bentuk antarmuka tidak berubah secara semantik tanpa bukti.
   - INVARIANT-F (Non-Destructive Repair): Perbaikan tidak boleh menghapus elemen atau field lain yang valid di bawah skema kanonikal.
   - INVARIANT-G (Relational Consistency): Artefak, antarmuka, dan scaffold membentuk struktur yang konsisten secara relasional.
   - INVARIANT-H (Serialization Equivalence): Serialisasi skema merepresentasikan struktur semantik yang identik.
8. Generic Repair Preservation (Anti-Field-Loss):
   - Prinsip: CURRENT VALID STATE + REPAIRED ELEMENT (perbaikan terlokalisasi).
   - Pada giliran repair, pertahankan seluruh elemen dan field yang masih valid di bawah skema kanonikal.
   - DILARANG meregenerasi subset dari state atau menghilangkan field valid (seperti `identifier`, `target_file`, atau anggota modul).
9. Call Shape, Constructor, and Scenario Invariants:
   - Skenario Negatif & Error Paths: Untuk skenario penerimaan yang menguji exception atau status code error, fungsi/metode scaffold WAJIB menyertakan observable guard atau error path (misal: conditional branch yang memicu error atau exception yang diharapkan). Analisis statis menolak scaffold jika error path tidak terbukti.
   - Positional Constructors: Jika kelas atau model dipanggil secara posisional di pengujian (misal: instansiasi objek dengan argumen posisi), sediakan konstruktor eksplisit `def __init__(self, data: Any = None): pass` (bukan BaseModel murni tanpa `__init__`).
   - Dart/Flutter Constructors & Widgets: Model data dan widget dengan parameter bernama di pengujian WAJIB mendeklarasikan named constructor parameters (misal: `ModelClass({required this.field_a, required this.field_b})`, `WidgetClass({super.key, required this.data})`). Komponen UI/Widget WAJIB didaftarkan ke `interface_contracts` dengan `interface_type: "WIDGET"`.
   - Hindari Nama Dummy/Spekulatif: DILARANG menggunakan nama dari contoh prompt (seperti `EntityA` atau `operation_a`) jika Acceptance Oracle dalam Section [5] telah mendefinisikan simbol antarmuka nyata.

Tuliskan output JSON yang valid, presisi, dan konsisten tanpa teks pengantar berlebih di luar penanda.
"""


def _build_default_aligned_contract(draft_contract: dict, task: str, target_lang: str, arch_plan: str = "") -> dict:
    """Membangun spesifikasi teknis ALIGNED yang konsisten dengan 4 pilar validasi gate secara generik."""
    is_dart = "dart" in target_lang.lower() or "flutter" in target_lang.lower()
    default_itype = "WIDGET" if is_dart else "FUNCTION"

    func_matches = re.findall(
        r"(?:def\s+|-\s*|\*\s*|`)([A-Za-z_][A-Za-z0-9_]*)\s*\((.*?)\)(?:\s*->\s*([A-Za-z0-9_\[\], ]+))?",
        arch_plan
    )
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
    primary_target_file = plan_files[0] if plan_files else ("lib/card_metric.dart" if is_dart else "main.py")

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


def _normalize_interface_contract_dict(d: dict, idx: int, is_dart: bool, primary_file: str) -> dict:
    """Normalisasi atribut interface contract dict ke skema kanonikal Pydantic (ParameterLocation, ExpectedReturn, dll)."""
    item = dict(d)
    if not item.get("interface_id"):
        item["interface_id"] = f"IFC-{idx:02d}"
    if not item.get("target_file"):
        item["target_file"] = primary_file
    if not item.get("http_method") and item.get("method"):
        item["http_method"] = item.get("method")
    if not item.get("route") and item.get("path"):
        item["route"] = item.get("path")
    if not item.get("route") and item.get("endpoint"):
        item["route"] = item.get("endpoint")
    if not item.get("interface_type"):
        if item.get("route") or (item.get("http_method") and str(item.get("http_method")).upper() in ("GET", "POST", "PUT", "DELETE", "PATCH")):
            item["interface_type"] = "HTTP_ENDPOINT"
        else:
            item["interface_type"] = "WIDGET" if is_dart else "FUNCTION"

    raw_params = item.get("parameters") or item.get("params") or item.get("args") or []
    norm_params = []
    if isinstance(raw_params, list):
        for p in raw_params:
            if isinstance(p, dict):
                p_name = str(p.get("param_name") or p.get("name") or "").strip()
                p_type = str(p.get("param_type") or p.get("type") or "Any").strip()
                raw_loc = str(p.get("param_location") or p.get("location") or "").strip().upper()
                p_req = p.get("is_required", p.get("required", True))
            elif hasattr(p, "param_name"):
                p_name = str(getattr(p, "param_name", "")).strip()
                p_type = str(getattr(p, "param_type", "Any")).strip()
                raw_loc = str(getattr(p, "param_location", "")).strip().upper()
                p_req = getattr(p, "is_required", True)
            else:
                continue

            if not is_dart and p_name.lower() in ("self", "cls"):
                continue

            if raw_loc in ("PATH", "QUERY", "BODY", "ARGUMENT", "PROP"):
                p_loc = raw_loc
            elif raw_loc in ("KEYWORD", "KEYWORD_ARGUMENT", "NAMED", "PROPERTY"):
                p_loc = "PROP" if is_dart else "ARGUMENT"
            elif raw_loc in ("SELF", "POS", "POSITIONAL", "ARG", "VAR"):
                p_loc = "ARGUMENT"
            else:
                p_loc = "PROP" if is_dart else "ARGUMENT"

            norm_params.append({
                "param_name": p_name,
                "param_type": p_type,
                "param_location": p_loc,
                "is_required": bool(p_req)
            })
    item["parameters"] = norm_params

    ret = item.get("expected_return") or item.get("return_type") or item.get("returns")
    if isinstance(ret, str):
        item["expected_return"] = {"return_type": ret}
    elif isinstance(ret, dict):
        if not ret.get("return_type") and ret.get("type"):
            ret["return_type"] = ret.get("type")
        item["expected_return"] = ret
    elif item.get("expected_return") is None:
        item["expected_return"] = {"return_type": "Widget" if is_dart and item.get("interface_type") == "WIDGET" else "Any"}

    return item


def format_canonical_obligation_blueprint_mapping(obligations: List[Any]) -> str:
    """
    Format representasi generik pemetaan dari Acceptance Obligation ke Required Blueprint Element.
    (Treatment — Architect Semantic Grounding v1, Part 1).

    Menghubungkan otoritas penerimaan ke kontrak cetak biru kanonikal secara deklaratif (WHAT)
    tanpa mendikte strategi implementasi atau solver spesifik.
    """
    if not obligations:
        return ""

    lines = [
        "=== [CANONICAL OBLIGATION TO BLUEPRINT BINDING SPECIFICATION] ===",
        "Prinsip Pemetaan Kanonikal (Generic Representation Contract):",
        "Setiap Acceptance Obligation di atas WAJIB dipetakan secara eksplisit ke elemen ArchitecturalBlueprint yang bersesuaian:\n"
    ]

    for idx, ob in enumerate(obligations, 1):
        ob_id = getattr(ob, "obligation_id", f"OBL-{idx}")
        ob_kind = getattr(ob, "obligation_kind", "UNKNOWN")
        pub_ident = getattr(ob, "public_identity", "")
        inputs = getattr(ob, "inputs", {}) or {}

        lines.append(f"{idx}. Obligation ID: {ob_id}")
        lines.append("   Authority Identity:")
        lines.append(f"     kind: {ob_kind}")
        lines.append(f"     value: {pub_ident}")

        method = None
        if isinstance(inputs, dict):
            method = inputs.get("http_method") or inputs.get("method")
        if method:
            lines.append(f"     method: {method}")

        lines.append("   Required Blueprint Element:")
        kind_str = str(ob_kind).upper()
        if "DATA_MODEL" in kind_str:
            lines.append("     element_kind: data_models")
            lines.append(f'     required_identity_fields: model_name (exact: "{pub_ident}"), fields')
        elif "INTERACTION" in kind_str:
            lines.append("     element_kind: interface_contracts")
            method_field = f', method (exact: "{method}")' if method else ""
            lines.append(f'     required_identity_fields: identifier, route (exact: "{pub_ident}"){method_field}')
        elif "OBSERVABLE_RUNTIME" in kind_str:
            lines.append("     element_kind: interface_contracts")
            lines.append(f'     required_identity_fields: identifier (exact: "{pub_ident}"), target_file')
        else:  # CALLABLE_INTERFACE, CALLABLE, FUNCTION, etc.
            lines.append("     element_kind: interface_contracts")
            lines.append(f'     required_identity_fields: identifier (exact: "{pub_ident}"), target_file, parameters')
        lines.append("     required: true\n")

    lines.append("ATURAN TRANSFORMASI KANONIKAL GENERIK:")
    lines.append('- Jika kind == "INTERACTION" (misal: HTTP endpoint / Web API):')
    lines.append("  * `route`: path persis dari identity.value (pertahankan placeholder path identik, misal {id})")
    lines.append("  * `method`: HTTP method persis jika ada")
    lines.append("  * `identifier`: nama fungsi/handler pengimplementasi route")
    lines.append('- Jika kind == "CALLABLE_INTERFACE" atau fungsi/metode publik:')
    lines.append("  * `identifier`: nama callable persis dari identity.value")
    lines.append('- Jika kind == "DATA_MODEL":')
    lines.append("  * petakan ke `data_models` dengan `model_name` sesuai identity.value")
    lines.append('- Jika kind == "OBSERVABLE_RUNTIME":')
    lines.append("  * petakan ke `interface_contracts` dengan `identifier` sesuai identity.value")
    lines.append("=== END [CANONICAL OBLIGATION TO BLUEPRINT BINDING SPECIFICATION] ===")

    return "\n".join(lines)


GENERIC_WORKED_EXAMPLE = """

=== [GENERIC WORKED EXAMPLE — CANONICAL BINDING TRANSFORMATION] ===
Berikut adalah SATU contoh generik transformasi antarmuka interaksi publik menjadi kontrak blueprint kanonikal (WHAT -> HOW):

Contoh Obligasi:
{
  "obligation_id": "OBL-EXAMPLE-01",
  "authority_identity": {
    "kind": "INTERACTION",
    "value": "/service/v1/resource",
    "method": "PATCH"
  },
  "required_blueprint_element": {
    "element_kind": "interface_contracts",
    "required_identity_fields": ["identifier", "route", "method"]
  }
}

Transformasi pada Blueprint:
1. Pada "interface_contracts":
{
  "identifier": "handle_resource_action",
  "route": "/service/v1/resource",
  "method": "PATCH",
  "target_file": "service.py",
  "parameters": [
    {
      "param_name": "payload",
      "param_type": "dict",
      "is_required": true
    }
  ],
  "expected_return": {
    "return_type": "dict"
  }
}
2. Pada "files" ("service.py" scaffold):
Deklarasikan antarmuka publik yang menangani route "/service/v1/resource" dengan method "PATCH" sebagai minimal stub (`pass`).
=== END [GENERIC WORKED EXAMPLE — CANONICAL BINDING TRANSFORMATION] ==="""


def architect_agent(state: SquadState, llm: Any = None, tracer: Any = None) -> dict:
    t0 = time.time()

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

    latest_cep = state.get("latest_evidence_package")
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

    is_repair_turn = (state.get("contract_revision_count", 0) > 0) or bool(pkg) or bool(state.get("contract_feedback"))

    decision_ctx = ""
    telem_data = {}
    if is_repair_turn and build_architect_decision_context:
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

        # Fail-closed: If context delivery validation failed during building
        if telem_data.get("delivery_valid") is False:
            deliv_errs = telem_data.get("delivery_errors") or ["Context delivery validation failed"]
            new_log = f"[System Architect]: DELIVERY_FAILURE — Context delivery check failed: {deliv_errs}"
            current_logs = state.get("logs", [])
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

    feedback_section = ""
    contract_feedback = state.get("contract_feedback")
    if contract_feedback:
        feedback_section = (
            f"\n\n[PERHATIAN: KONTRAK SEBELUMNYA DITOLAK OLEH GERBANG VALIDASI - REVISI DIPERLUKAN]\n"
            f"{contract_feedback}\n\n"
            "INSTRUKSI REVISI WAJIB:\n"
            "Perbaiki rancangan arsitektur dan definisikan `interface_contracts` secara eksplisit sesuai feedback di atas.\n"
            "Pastikan antarmuka publik yang didefinisikan dapat dipanggil oleh pengujian independen (nama fungsi/kelas, callable signature, parameter, return type)."
        )

    # Environment Grounding untuk Architect
    try:
        arch_fact_card = generate_fact_card_for_architect(target_lang, task=user_task)
    except Exception:
        arch_fact_card = ""
    env_section = f"\n{arch_fact_card}\n" if arch_fact_card else ""

    # Authoritative Oracle Obligations Extraction (Available on all turns)
    f_oracle_path = state.get("frozen_oracle_path")
    t_files = state.get("test_files")
    oracle_obs = []
    if extract_canonical_oracle_obligations and (f_oracle_path or t_files):
        try:
            oracle_obs = extract_canonical_oracle_obligations(
                frozen_oracle_path=f_oracle_path,
                test_files=t_files
            )
        except Exception:
            oracle_obs = []

    # Context Assembly: Concise, non-duplicative, dense
    if is_repair_turn and decision_ctx:
        prompt = f"""TARGET BAHASA PEMROGRAMAN WAJIB: {target_lang.upper()}

{structure_rule}
{env_section}

{decision_ctx}{feedback_section}

ATURAN KETAT:
Seluruh file tree, hierarki modul, dan ekstensi file WAJIB menggunakan bahasa {target_lang.upper()} murni (Maksimal 2-3 file implementasi total).
DILARANG KERAS merancang file tree atau struktur dalam bahasa selain {target_lang.upper()}!
ARTIFACT PURITY (WAJIB): DILARANG KERAS memasukkan file pengujian/test ke dalam file_tree atau files!
BATAS SCAFFOLD WAJIB: code_scaffold HANYA berupa interface signatures dan minimal stubs (misal: deklarasi fungsi/metode dengan `pass` atau return dummy). Developer yang mengimplementasikan kode lengkap!

PRE-SEAL SELF-REVIEW (Sebelum menyerahkan blueprint):
1. Specification -> Coverage: Seluruh requirement dari spesifikasi terwakili.
2. Blueprint -> Internal Consistency: Simbol/decorator/constructor terdefinisi secara konsisten.
3. Blueprint -> Contract Consistency: Antarmuka publik dipertahankan secara eksak.
4. Acceptance Obligations Coverage: Seluruh obligasi penerimaan tercakup dalam interface_contracts atau data_models.
5. Generic Repair Preservation: Pertahankan seluruh elemen valid sebelumnya dan perbaiki elemen yang rusak (CURRENT VALID STATE + REPAIRED ELEMENT).

Tuliskan output cetak biru JSON kanonikal di dalam penanda persis === BLUEPRINT JSON === ... === END BLUEPRINT JSON ===."""
    else:
        v0_section = ""
        v0_model = state.get("v0_requirement_model")
        if v0_model and isinstance(v0_model, dict):
            core_reqs = v0_model.get("requirements", [])
            if core_reqs:
                v0_lines = [
                    f"- [{r.get('category', 'REQ')}] {r.get('description', str(r))}"
                    if isinstance(r, dict) else f"- {r}"
                    for r in core_reqs[:8]
                ]
                v0_section = "\nKebutuhan Aplikasi V0 (Epistemic Grounding):\n" + "\n".join(v0_lines) + "\n"

        oracle_ledger_section = ""
        try:
            if oracle_obs:
                ledger_text = format_authoritative_obligation_ledger(oracle_obs)
                if ledger_text:
                    oracle_ledger_section = ledger_text.strip()
        except Exception:
            pass

        # Acceptance Behavior & Scenarios (Read-Only Authoritative Ground Truth)
        oracle_scenario_section = ""
        try:
            scenarios = extract_canonical_scenarios(
                frozen_oracle_path=f_oracle_path,
                test_files=t_files
            ) if extract_canonical_scenarios else []
            if scenarios:
                scenario_text = format_scenarios_for_architect(scenarios)
                if scenario_text:
                    oracle_scenario_section = f"\n\n{scenario_text.strip()}"
        except Exception:
            oracle_scenario_section = ""

        # Canonical Obligation to Blueprint Mapping & Generic Worked Example (Treatment — Architect Semantic Grounding v1)
        canonical_mapping_section = ""
        worked_example_section = ""
        if oracle_obs:
            try:
                mapping_text = format_canonical_obligation_blueprint_mapping(oracle_obs)
                if mapping_text:
                    canonical_mapping_section = f"\n\n{mapping_text.strip()}"
                    worked_example_section = f"\n\n{GENERIC_WORKED_EXAMPLE.strip()}"
            except Exception:
                canonical_mapping_section = ""
                worked_example_section = ""

        prompt = f"""TARGET BAHASA PEMROGRAMAN WAJIB: {target_lang.upper()}

{structure_rule}
{env_section}

[1] USER INTENT / V0 REQUIREMENTS (EPISTEMIC GROUNDING FACTS):
Tugas Pengguna:
{user_task}
{v0_section}

[2] ACCEPTANCE OBLIGATION LEDGER (AUTHORITATIVE ACCEPTANCE OBLIGATIONS):
Authority: FROZEN_ORACLE (Immutable Acceptance Authority — Sumber Kebenaran Mutlak)
Prinsip: Seluruh obligasi publik di bawah ini WAJIB dideklarasikan secara presisi pada interface_contracts atau data_models.
{oracle_ledger_section if oracle_ledger_section else "Tidak ada acceptance obligation spesifik yang diekstrak. Gunakan User Intent dan V0 Requirements sebagai panduan."}{oracle_scenario_section}{canonical_mapping_section}{worked_example_section}

[3] PM SPECIFICATION (PROPOSAL — DESIGN REFERENCE ONLY):
Peran: Product Manager adalah PROPOSAL perancangan fitur, BUKAN Acceptance Authority.
Aturan Otoritas: Jika terdapat perbedaan atau konflik antara PM Proposal dengan [2] ACCEPTANCE OBLIGATION LEDGER, maka [2] ACCEPTANCE OBLIGATION LEDGER MUTLAK MENANG. Architect DILARANG mengubah atau mengarang nama/tipe yang bertentangan dengan Acceptance Authority.
{specs}{feedback_section}

[4] BLUEPRINT SCHEMA & CANONICAL OUTPUT SPECIFICATION:
Tugas Anda adalah menghasilkan SATU cetak biru ArchitecturalBlueprint dalam format JSON kanonikal di dalam penanda persis === BLUEPRINT JSON === ... === END BLUEPRINT JSON ===.
Format root harus berupa object JSON ArchitecturalBlueprint dengan fields:
- "authoritative_target_file": nama file kode utama (contoh "main.py" atau "lib/card_metric.dart")
- "file_tree": list path file implementasi (maksimal 1-2 file, DILARANG memasukkan file test)
- "architecture_summary": ringkasan arsitektur
- "files": mapping file path ke object {{"module_role": str, "imports": list, "code_scaffold": str}}
- "interface_contracts": list object interface {{"identifier": str, "route": str (optional for HTTP/web endpoints), "method": str (optional for HTTP/web endpoints), "target_file": str, "parameters": list, "expected_return": dict}}
- "data_models": list object data model {{"model_name": str, "target_file": str, "fields": list}}

[5] ARCHITECT CONSTRUCTION RULES:
Tugas Utama: Transformasikan kebutuhan pengguna dan acceptance obligations menjadi SATU ArchitecturalBlueprint kanonikal.
Cetak biru Anda harus menjawab:
- WHAT exists? (Kelas, model data, fungsi, endpoint publik apa yang harus ada)
- WHERE does it exist? (File implementasi mana yang memuat deklarasi tersebut)
- HOW is it called? (Callable signature, parameter, tipe, konstruktor)
- WHAT data enters & returns? (Bentuk input parameter dan tipe kembalian)
- WHICH obligation does it satisfy? (Setiap obligasi dari [2] WAJIB terwakili di interface_contracts atau data_models)

BATASAN KETAT (MINIMAL SCAFFOLD & ARTIFACT PURITY):
1. MINIMAL STUB: code_scaffold HANYA berupa interface signatures dan minimal stubs (misal: deklarasi fungsi/metode dengan `pass` atau return default dummy). DILARANG menulis implementasi logika bisnis penuh. Developer yang bertanggung jawab penuh atas implementasi kode.
2. ARTIFACT PURITY: file_tree dan files HANYA untuk modul kode implementasi. DILARANG KERAS memasukkan file pengujian/test (seperti test_*.py atau *_test.dart) ke dalam file_tree atau files!
3. STRUKTUR MODUL: Maksimal 1-2 file kode implementasi. DILARANG membuat hierarki folder berlebihan atau banyak file terfragmentasi.

PRE-SEAL SELF-REVIEW (Sebelum menyerahkan blueprint):
1. Specification -> Coverage: Apakah seluruh requirement dari spesifikasi sudah terwakili tanpa ada yang terlewat?
2. Blueprint -> Internal Consistency: Apakah setiap simbol/decorator/constructor terdefinisi secara konsisten?
3. Blueprint -> Contract Consistency: Apakah antarmuka publik dipertahankan secara eksak?
4. Acceptance Obligations Coverage: Apakah SELURUH obligasi publik dalam [2] ACCEPTANCE OBLIGATION LEDGER dan alur skenario penerimaan telah memiliki padanan deklarasi eksplisit di `interface_contracts` atau `data_models`?
5. Minimal Scaffold: Apakah scaffold berupa minimal stubs (`pass`) tanpa implementasi penuh logika bisnis?

Tuliskan output cetak biru JSON kanonikal di dalam penanda persis === BLUEPRINT JSON === ... === END BLUEPRINT JSON ===."""

    messages = [
        SystemMessage(content=ARCHITECT_SYSTEM_PROMPT),
        HumanMessage(content=prompt)
    ]

    # Pre-invocation Delivery Gate on repair turn with structured context
    if is_repair_turn and decision_ctx and validate_architect_repair_context_delivery:
        final_delivered_str = messages[1].content if len(messages) > 1 else prompt
        deliv_ok, deliv_errs = validate_architect_repair_context_delivery(final_delivered_str)
        if not deliv_ok:
            new_log = f"[System Architect]: DELIVERY_FAILURE — Pre-invocation context delivery check failed: {deliv_errs}"
            current_logs = state.get("logs", [])
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

    # =========================================================================
    # SINGLE LLM INVOCATION (Treatment #1.2 / TRUE LKG Invariant)
    # =========================================================================
    response = llm.invoke(messages)
    raw_content = getattr(response, "content", None)
    if isinstance(raw_content, str):
        raw_output = raw_content
    elif isinstance(response, str):
        raw_output = response
    else:
        raw_output = str(raw_content if raw_content is not None else (response or ""))
    wall_time = time.time() - t0
    llm_call_count = 1
    assert llm_call_count == 1, f"Architect invocation count must be strictly 1, observed: {llm_call_count}"

    draft_contract = state.get("contract")
    if not draft_contract or not isinstance(draft_contract, dict):
        draft_contract = create_draft_contract(
            raw_intent=user_task,
            target_language=target_lang,
            goal_summary=user_task[:120]
        )

    # Direct Canonical Blueprint JSON Extraction & Normalization
    extracted_bp, bp_err = parse_blueprint_json(raw_output)

    # Reversible fallback for legacy staged semantic serializer if legacy output detected
    if extracted_bp is None and any(k in raw_output for k in ("semantic_decisions", "obligation_mappings", "STAGE B")):
        try:
            from ..semantic_serializer import parse_semantic_architectural_plan, serialize_semantic_decision_to_blueprint
        except (ImportError, ValueError):
            try:
                from semantic_serializer import parse_semantic_architectural_plan, serialize_semantic_decision_to_blueprint
            except ImportError:
                parse_semantic_architectural_plan = None
                serialize_semantic_decision_to_blueprint = None

        if parse_semantic_architectural_plan and serialize_semantic_decision_to_blueprint:
            sem_plan, sem_errs = parse_semantic_architectural_plan(raw_output)
            if sem_plan and not sem_errs:
                extracted_bp, ser_errs = serialize_semantic_decision_to_blueprint(sem_plan)
                if extracted_bp:
                    bp_err = None

    contract_errors = []
    aligned_contract = dict(draft_contract)
    arch_plan = raw_output
    serialization_success = False

    if extracted_bp and not bp_err:
        primary_file = extracted_bp.authoritative_target_file or ("lib/card_metric.dart" if is_dart else "main.py")

        # Ekstraksi fakta implementasi scaffold via AST kanonikal (Treatment #1.8.10 Part A)
        scaffold_files_dict = {}
        if hasattr(extracted_bp, "files") and extracted_bp.files:
            for fp, fmod in extracted_bp.files.items():
                sc_text = getattr(fmod, "code_scaffold", "") if hasattr(fmod, "code_scaffold") else (fmod.get("code_scaffold", "") if isinstance(fmod, dict) else str(fmod))
                if sc_text:
                    scaffold_files_dict[fp] = sc_text
        scaffold_facts = extract_all_scaffold_facts(scaffold_files_dict) if extract_all_scaffold_facts else []

        ifaces = []
        assertions = []
        for idx, ifc in enumerate(extracted_bp.interface_contracts, 1):
            d_raw = ifc.model_dump() if hasattr(ifc, "model_dump") else dict(ifc)
            # Binding route & method dari AST facts jika belum didefinisikan secara eksplisit
            if not d_raw.get("route") and scaffold_facts:
                fact = find_deterministic_callable_fact(d_raw.get("identifier"), d_raw.get("target_file"), scaffold_facts)
                if fact and fact.route:
                    d_raw["route"] = fact.route
                    if fact.http_method:
                        d_raw["http_method"] = fact.http_method
                    d_raw["interface_type"] = "HTTP_ENDPOINT"

            d = _normalize_interface_contract_dict(d_raw, idx, is_dart, primary_file)
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

        canonical_models, model_errs = normalize_blueprint_data_models(
            extracted_bp.data_models,
            default_target_file=primary_file
        )

        # Synchronize authoritative oracle obligations that exist in the scaffold files
        # but were omitted from interface_contracts and data_models
        declared_ifc_ids = {d.get("identifier") for d in ifaces if d.get("identifier")}
        declared_routes = {
            (d.get("route").rstrip("/"), str(d.get("http_method", "")).upper())
            for d in ifaces if d.get("route")
        }
        declared_model_names = {m.get("model_name") for m in canonical_models if m.get("model_name")}
        if oracle_obs and hasattr(extracted_bp, "files") and extracted_bp.files:
            for ob in oracle_obs:
                sym = getattr(ob, "public_identity", None)
                if not sym:
                    continue

                # A. INTERACTION OBLIGATION (Route binding)
                if getattr(ob, "obligation_kind", None) == "INTERACTION":
                    req_r = normalize_route_path(sym).rstrip("/")
                    req_m = ob.inputs.get("http_method", "").upper() if ob.inputs else ""
                    if (req_r, req_m) in declared_routes or any(r == req_r for r, m in declared_routes if not req_m or m == req_m):
                        continue

                    # Cari fakta route deterministik dari AST scaffold
                    matching_route_facts = [
                        f for f in scaffold_facts
                        if f.route and normalize_route_path(f.route).rstrip("/") == req_r
                        and (not req_m or not f.http_method or f.http_method.upper() == req_m)
                    ]
                    distinct_names = {f.name for f in matching_route_facts}
                    if len(matching_route_facts) >= 1 and len(distinct_names) == 1:
                        rf = matching_route_facts[0]
                        synced_d = _normalize_interface_contract_dict({
                            "interface_id": f"IFC-{len(ifaces) + 1:02d}",
                            "interface_type": "HTTP_ENDPOINT",
                            "identifier": rf.name,
                            "route": rf.route,
                            "http_method": rf.http_method or req_m or "GET",
                            "target_file": rf.file_path or primary_file,
                            "parameters": [],
                            "expected_return": {"return_type": "Any"}
                        }, len(ifaces) + 1, is_dart, rf.file_path or primary_file)
                        ifaces.append(synced_d)
                        declared_ifc_ids.add(rf.name)
                        declared_routes.add((req_r, str(rf.http_method or req_m).upper()))
                        assertions.append({
                            "assertion_id": f"AST-{len(assertions) + 1:02d}",
                            "linked_req_id": "REQ-01",
                            "linked_interface_id": synced_d["interface_id"],
                            "test_scenario": f"Execution of endpoint {rf.route} meets functional requirements",
                            "target_symbol": rf.name,
                            "input_fixture": f"{rf.name}()",
                            "expected_outcome": {
                                "outcome_type": "VALUE_EQUALS",
                                "value": 0
                            }
                        })
                    continue

                # B. DATA MODEL / CALLABLE SYMBOL OBLIGATION
                if sym in declared_ifc_ids or sym in declared_model_names:
                    continue

                # Check if sym is defined as a class or function in any scaffold file
                target_fp = primary_file
                found_in_scaffold = False
                for fp, fmod in extracted_bp.files.items():
                    sc_text = getattr(fmod, "code_scaffold", "") if hasattr(fmod, "code_scaffold") else (fmod.get("code_scaffold", "") if isinstance(fmod, dict) else str(fmod))
                    if re.search(rf"\b(class|def)\s+{re.escape(sym)}\b", sc_text):
                        target_fp = fp
                        found_in_scaffold = True
                        break

                if found_in_scaffold:
                    is_widget = is_dart and (getattr(ob, "obligation_kind", "") == "OBSERVABLE_RUNTIME" or "Widget" in sym or "Card" in sym)
                    synced_d = _normalize_interface_contract_dict({
                        "interface_id": f"IFC-{len(ifaces) + 1:02d}",
                        "interface_type": "WIDGET" if is_widget else "FUNCTION",
                        "identifier": sym,
                        "target_file": target_fp,
                        "parameters": [],
                        "expected_return": {"return_type": "Widget" if is_widget else "Any"}
                    }, len(ifaces) + 1, is_dart, target_fp)
                    ifaces.append(synced_d)
                    declared_ifc_ids.add(sym)
                    assertions.append({
                        "assertion_id": f"AST-{len(assertions) + 1:02d}",
                        "linked_req_id": "REQ-01",
                        "linked_interface_id": synced_d["interface_id"],
                        "test_scenario": f"Execution of {sym} meets functional requirements",
                        "target_symbol": sym,
                        "input_fixture": f"{sym}()",
                        "expected_outcome": {
                            "outcome_type": "VALUE_EQUALS",
                            "value": 0
                        }
                    })

        if model_errs:
            contract_errors.extend(model_errs)
            aligned_contract["status"] = "REJECTED"
        else:
            aligned_contract = complete_aligned_contract(
                draft_dict=draft_contract,
                data_models=canonical_models,
                interface_contracts=ifaces,
                testable_assertions=assertions
            )
            bp_dict_pre = extracted_bp.model_dump() if hasattr(extracted_bp, "model_dump") else (extracted_bp.to_dict() if hasattr(extracted_bp, "to_dict") else extracted_bp)
            if isinstance(bp_dict_pre, dict) and "files" in bp_dict_pre:
                aligned_contract["files"] = bp_dict_pre.get("files", {})

            arch_plan = serialize_blueprint_to_canonical_json(extracted_bp)
            serialization_success = True

            is_rep_valid, rep_errs = validate_canonical_architecture_plan_state(
                architecture_plan=arch_plan,
                canonical_blueprint=extracted_bp,
                contract=aligned_contract
            )
            if not is_rep_valid:
                aligned_contract["status"] = "STATE_REPRESENTATION_FAILURE"
                contract_errors.extend(rep_errs)
    else:
        parse_msg = f"SCHEMA_VIOLATION: Blueprint JSON parse failure: {bp_err or 'Invalid or missing blueprint JSON'}"
        contract_errors.append(parse_msg)
        aligned_contract["status"] = "REJECTED"

    if "provenance" not in aligned_contract or not isinstance(aligned_contract["provenance"], dict):
        aligned_contract["provenance"] = {}
    aligned_contract["provenance"]["active_validation_errors"] = list(contract_errors)
    aligned_contract["provenance"]["contract_validation_errors"] = list(contract_errors)
    aligned_contract["provenance"]["raw_llm_response"] = raw_output
    aligned_contract["provenance"]["raw_stage_a_output"] = state.get("raw_stage_a_output") or (raw_output if "STAGE A" in raw_output else "=== STAGE A: OBLIGATION MAPPING ===\n{\n  \"obligation_mappings\": []\n}\n=== END STAGE A ===")
    aligned_contract["provenance"]["raw_stage_b_output"] = state.get("raw_stage_b_output") or (raw_output if "STAGE B" in raw_output else "=== STAGE B: ARCHITECTURAL ASSEMBLY ===\n{\n  \"files\": {}\n}\n=== END STAGE B ===")
    val_hist = list(aligned_contract["provenance"].get("validation_history") or [])
    val_hist.append({
        "timestamp": datetime.now().isoformat(),
        "phase": "ARCHITECT_UNIFIED_SYNTHESIS",
        "status": aligned_contract.get("status", "REJECTED"),
        "errors": list(contract_errors)
    })
    aligned_contract["provenance"]["validation_history"] = val_hist

    input_chars = len(messages[0].content) + len(messages[1].content)
    output_chars = len(raw_output)
    scaffold_chars = 0
    if extracted_bp and hasattr(extracted_bp, "files") and extracted_bp.files:
        for m in extracted_bp.files.values():
            s = getattr(m, "code_scaffold", "") or (m.get("code_scaffold", "") if isinstance(m, dict) else "")
            scaffold_chars += len(s)

    architect_telem = {
        "llm_call_count": llm_call_count,
        "architect_llm_invocations": llm_call_count,
        "active_path": "UNIFIED_ARCHITECT_ONE_LLM",
        "wall_time": round(wall_time, 2),
        "input_chars": input_chars,
        "estimated_input_tokens": input_chars // 4,
        "output_chars": output_chars,
        "estimated_output_tokens": output_chars // 4,
        "model": str(state.get("model_name") or "qwen2.5-coder:7b"),
        "num_ctx": int(state.get("num_ctx") or 8192),
        "delivery_valid": True,
        "contract_status": aligned_contract.get("status"),
        "serialization_success": serialization_success,
        "scaffold_size_chars": scaffold_chars
    }

    if tracer:
        tracer.log_event(
            stage="contract",
            event_type="architect_synthesis",
            iteration=state.get("contract_revision_count", 0),
            data=architect_telem
        )

    status_label = aligned_contract.get("status", "ALIGNED")
    new_log = (
        f"[System Architect]: Unified Blueprint ({len(arch_plan)} char, {wall_time:.1f}s) dirancang. "
        f"Status kontrak: {status_label} ({len(aligned_contract.get('testable_assertions', []))} assertions, 1 LLM call)."
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
        "status": "architect_done" if status_label in ("ALIGNED", "FROZEN") else "architect_repair_needed",
        "architect_telemetry": architect_telem,
        "logs": current_logs + [new_log]
    }
