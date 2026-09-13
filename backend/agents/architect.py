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
    from ..blueprint_schema import (
        ArchitecturalBlueprint,
        parse_blueprint_json,
        extract_blueprint_json_text,
        blueprint_to_narrative_markdown
    )
except (ImportError, ValueError):
    try:
        from blueprint_schema import (
            ArchitecturalBlueprint,
            parse_blueprint_json,
            extract_blueprint_json_text,
            blueprint_to_narrative_markdown
        )
    except ImportError:
        ArchitecturalBlueprint = None
        parse_blueprint_json = lambda t: (None, "Schema not available")
        extract_blueprint_json_text = lambda t: None
        blueprint_to_narrative_markdown = lambda b: ""

ARCHITECT_SYSTEM_PROMPT = """Anda adalah Senior Software & System Architect dalam tim rekayasa perangkat lunak ReinDev Studio.
Tugas Anda adalah menerima spesifikasi dari Product Manager dan merancang struktur arsitektur perangkat lunak yang modular, terpisah dengan jelas (Separation of Concerns), dan mudah diuji.

FORMAT LUARAN YANG WAJIB ANDA HASILKAN:
Anda WAJIB menghasilkan blok cetak biru arsitektur terstruktur dalam format JSON kanonikal di dalam penanda persis seperti berikut:

=== BLUEPRINT JSON ===
{
  "authoritative_target_file": "main.py",
  "file_tree": ["main.py"],
  "architecture_summary": "Deskripsi ringkas arsitektur modul",
  "files": {
    "main.py": {
      "module_role": "Authoritative Single Module",
      "imports": [
        "from fastapi import FastAPI, HTTPException",
        "from pydantic import BaseModel, field_validator"
      ],
      "code_scaffold": "from fastapi import FastAPI, HTTPException\nfrom pydantic import BaseModel, field_validator\n\napp = FastAPI()\n\nclass Product(BaseModel):\n    id: int\n    name: str\n    price: float\n    stock: int\n\n    @field_validator('price', 'stock')\n    def validate_non_negative(cls, v):\n        if v < 0:\n            raise ValueError('Cannot be negative')\n        return v\n\n@app.post('/products', status_code=201)\ndef create_product(product: Product) -> Product:\n    pass\n\n@app.get('/products')\ndef list_products() -> list[Product]:\n    pass\n"
    }
  },
  "interface_contracts": [
    {
      "identifier": "create_product",
      "route": "/products",
      "method": "POST",
      "target_file": "main.py"
    },
    {
      "identifier": "list_products",
      "route": "/products",
      "method": "GET",
      "target_file": "main.py"
    }
  ]
}
=== END BLUEPRINT JSON ===

PRINSIP KONSISTENSI & KODIFIKASI ARSITEKTUR (WAJIB):
1. File-Centric Signatures & Scaffolding: Setiap berkas dituliskan sebagai kerangka interface di dalam string `code_scaffold`.
   - BATAS SCAFFOLD WAJIB: `code_scaffold` HANYA berupa interface signatures & stubs (misal: deklarasi fungsi/metode dengan `pass`).
   - TARGET UKURAN: <=800 karakter per file. DILARANG menuliskan implementasi logika bisnis penuh di dalam scaffold.
2. Symbol Resolvability: Setiap berkas WAJIB menyertakan statement `import` lengkap di awal berkas. Jika menggunakan decorator, instance dan class dekorator WAJIB dideklarasikan atau diimpor secara lokal di berkas yang bersangkutan.
3. Specification Authority: Pertahankan antarmuka yang telah ditentukan spesifikasi secara eksak.
4. INTEGRITAS ENVIRONMENT: Patuhi batasan ENVIRONMENT FACT CARD dan dilarang menggunakan API terlarang.

Tuliskan output JSON yang valid, presisi, dan konsisten tanpa teks pengantar berlebih di luar penanda.
"""

def _build_default_aligned_contract(draft_contract: dict, task: str, target_lang: str, arch_plan: str = "") -> dict:
    """Membangun spesifikasi teknis ALIGNED yang konsisten dengan 4 pilar validasi gate."""
    is_dart = "dart" in target_lang.lower() or "flutter" in target_lang.lower()
    task_l = task.lower()

    if is_dart:
        data_models = []
        interface_contracts = [
            {
                "interface_id": "IFC-01",
                "interface_type": "WIDGET",
                "identifier": "CardMetric",
                "http_method": None,
                "target_file": "lib/card_metric.dart",
                "parameters": [
                    {"param_name": "data", "param_type": "dynamic", "param_location": "PROP", "is_required": False}
                ],
                "expected_return": {
                    "return_type": "Widget",
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
                "test_scenario": "Widget renders properly inside ProviderScope",
                "target_symbol": "CardMetric",
                "input_fixture": "CardMetric()",
                "expected_outcome": {
                    "outcome_type": "WIDGET_FOUND",
                    "expected_value": "CardMetric"
                }
            }
        ]
    elif any(k in task_l for k in ["fastapi", "rest", "api", "crud", "endpoint", "inventaris"]):
        data_models = [
            {
                "model_name": "Product",
                "target_file": "main.py",
                "fields": [
                    {"field_name": "id", "field_type": "int", "is_required": True, "description": "ID unik produk"},
                    {"field_name": "name", "field_type": "str", "is_required": True, "description": "Nama produk"},
                    {"field_name": "price", "field_type": "float", "is_required": False, "description": "Harga produk"}
                ]
            }
        ]
        interface_contracts = [
            {
                "interface_id": "IFC-01",
                "interface_type": "HTTP_ENDPOINT",
                "identifier": "/products",
                "http_method": "GET",
                "target_file": "main.py",
                "parameters": [],
                "expected_return": {
                    "return_type": "List[Product]",
                    "status_code_success": 200,
                    "status_code_errors": []
                }
            },
            {
                "interface_id": "IFC-02",
                "interface_type": "HTTP_ENDPOINT",
                "identifier": "/products",
                "http_method": "POST",
                "target_file": "main.py",
                "parameters": [
                    {"param_name": "product", "param_type": "Product", "param_location": "BODY", "is_required": True}
                ],
                "expected_return": {
                    "return_type": "Product",
                    "status_code_success": 200,
                    "status_code_errors": [{"code": 422, "condition": "Validation Error"}]
                }
            }
        ]
        testable_assertions = [
            {
                "assertion_id": "AST-01",
                "linked_req_id": "REQ-01",
                "linked_interface_id": "IFC-01",
                "test_scenario": "Read all products returns 200 OK",
                "target_symbol": "/products",
                "input_fixture": "client.get('/products')",
                "expected_outcome": {
                    "outcome_type": "HTTP_STATUS",
                    "expected_status": 200
                }
            },
            {
                "assertion_id": "AST-02",
                "linked_req_id": "REQ-01",
                "linked_interface_id": "IFC-02",
                "test_scenario": "Create product returns 200 OK",
                "target_symbol": "/products",
                "input_fixture": "client.post('/products', json={'name': 'Item', 'price': 100})",
                "expected_outcome": {
                    "outcome_type": "HTTP_STATUS",
                    "expected_status": 200
                }
            }
        ]
    else:
        # Generic CLI / Algorithm / Computational module
        # Ekstraksi fungsi atau method yang dirancang oleh Architect di arch_plan
        func_matches = re.findall(
            r"(?:def\s+|-\s*|\*\s*|`)([A-Za-z_][A-Za-z0-9_]*)\s*\((.*?)\)(?:\s*->\s*([A-Za-z0-9_\[\], ]+))?",
            arch_plan
        )
        # Ekstraksi class yang dideklarasikan secara sintaksis formal dalam Python:
        # Mengharuskan batasan awal baris/delimiter, kata kunci 'class', nama identifier,
        # opsional parameter inheritance/type arguments, dan penutup tanda titik dua ':'
        raw_class_matches = re.findall(
            r"(?:^|[;\n`])\s*class\s+([A-Za-z_][A-Za-z0-9_]*)(?:\s*\([^)]*\))?\s*:",
            arch_plan,
            re.MULTILINE
        )
        # Defense-in-depth: abaikan keyword/stop-words dan deduplikasi berurutan
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
        primary_target_file = plan_files[0] if plan_files else "main.py"

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
                    "interface_type": "FUNCTION",
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
            fn_name = "calculate" if any(k in task_l for k in ["hitung", "kalkulator", "calc", "math"]) else "execute"
            interface_contracts = [
                {
                    "interface_id": "IFC-01",
                    "interface_type": "FUNCTION",
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
                    "test_scenario": "Calculate basic arithmetic calculation returns value",
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
        "- Gunakan struktur modul tunggal kohesif: MAKSIMAL 1 file kode implementasi untuk Developer di lib/ (contoh: `lib/card_metric.dart`) dan 1 file test untuk QA Tester (`test/card_metric_test.dart`).\n"
        "- Gabungkan model data, provider Riverpod, dan Widget UI dalam 1 file `lib/card_metric.dart` untuk mencegah fragmentasi file dan kesalahan impor silang.\n"
        "- DILARANG merancang struktur banyak file yang terpisah-pisah untuk widget sederhana.\n"
        if is_dart else
        "ATURAN STRUKTUR PROYEK PYTHON (WAJIB):\n"
        "- Gunakan struktur modul Python sederhana dan kohesif: MAKSIMAL 1-2 file kode implementasi untuk Developer (misal: `main.py` atau `models.py` + `main.py`) dan 1 file test untuk QA Tester (`test_*.py`).\n"
        "- Gabungkan data models, in-memory store/state, dan antarmuka utama dalam modul utama (contoh: `main.py` atau `models.py` + `main.py`) untuk menghindari fragmentasi folder dan kesalahan impor silang.\n"
        "- DILARANG merancang hierarki folder yang terlalu dalam (hindari app/api/, app/schemas/, app/models/). Jaga struktur tetap datar di root.\n"
    )
    
    feedback_section = ""
    latest_cep = state.get("latest_evidence_package")
    tracer = get_tracer(state.get("run_id"))

    if latest_cep and latest_cep.get("causal_owner") == "ARCHITECT":
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

            decision_ctx, telem_data = build_architect_decision_context(state, pkg=pkg)
            feedback_section = f"\n\n{decision_ctx}\n"

            if tracer and ContextTelemetry and emit_context_telemetry:
                telem = ContextTelemetry(
                    agent="architect",
                    model=str(state.get("model_name", "")),
                    context_version="hardening_v1",
                    run_id=str(state.get("run_id", "")),
                    iteration=state.get("contract_revision_count", 0),
                    **telem_data
                )
                emit_context_telemetry(tracer, "architect", telem)
                if hasattr(tracer, "log_repair_attempt") and pkg:
                    rev_idx = state.get("contract_revision_count", 0)
                    tracer.log_repair_attempt(turn=rev_idx, package_id=pkg.package_id, iteration=rev_idx)

    if not feedback_section:
        contract_feedback = state.get("contract_feedback")
        if contract_feedback:
            feedback_section = (
                f"\n\n[PERHATIAN: KONTRAK SEBELUMNYA DITOLAK OLEH GERBANG VALIDASI - REVISI DIPERLUKAN]\n"
                f"{contract_feedback}\n\n"
                "INSTRUKSI REVISI WAJIB:\n"
                "Perbaiki rancangan arsitektur dan definisikan `interface_contracts` secara eksplisit sesuai feedback di atas.\n"
                "Pastikan antarmuka publik yang didefinisikan dapat dipanggil oleh pengujian independen (nama fungsi/kelas, callable signature, parameter, return type)."
            )

    # V0 App Requirements Grounding (Epistemic Grounding)
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

    # Environment Grounding untuk Architect
    try:
        arch_fact_card = generate_fact_card_for_architect(target_lang, task=user_task)
    except Exception:
        arch_fact_card = ""
    env_section = f"\n{arch_fact_card}\n" if arch_fact_card else ""

    prompt = f"""TARGET BAHASA PEMROGRAMAN WAJIB: {target_lang.upper()}

{structure_rule}
{env_section}
Deskripsi Tugas Pengguna:
{user_task}
{v0_section}
Spesifikasi Product Manager:
{specs}{feedback_section}

ATURAN KETAT:
Seluruh file tree, hierarki modul, dan ekstensi file WAJIB menggunakan bahasa {target_lang.upper()} murni (Maksimal 2-3 file total).
DILARANG KERAS merancang file tree atau struktur dalam bahasa selain {target_lang.upper()}!
DILARANG KERAS merancang kelas, dependensi, atau pola yang dinyatakan dilarang dalam BATASAN ARSITEKTUR WAJIB di atas!

PRE-SEAL SELF-REVIEW (Sebelum menyerahkan blueprint):
Lakukan audit mandiri singkat terhadap rancangan arsitektur Anda:
1. Specification -> Coverage: Apakah seluruh requirement dari spesifikasi sudah terwakili tanpa ada yang terlewat?
2. Blueprint -> Internal Consistency: Apakah setiap simbol/decorator yang digunakan dalam blueprint/snippet memiliki sumber resolusi/impor yang jelas, dan deklarasi interface/constructor konsisten dengan pemanggilannya?
3. Blueprint -> Contract Consistency: Apakah antarmuka yang telah ditentukan oleh spesifikasi dipertahankan secara eksak tanpa disingkat atau diimprovisasi?
Perbaiki inkonsistensi yang ada, lalu tuliskan diagram struktur file tree dan kontrak interface secara SUPER RINGKAS tanpa basa-basi narasi."""

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
    if extracted_bp and extracted_bp.interface_contracts:
        ifaces = []
        assertions = []
        for idx, ifc in enumerate(extracted_bp.interface_contracts, 1):
            d = ifc.model_dump() if hasattr(ifc, "model_dump") else dict(ifc)
            ifid = f"IFC-{idx:02d}"
            if not d.get("interface_id"):
                d["interface_id"] = ifid
            if not d.get("interface_type"):
                d["interface_type"] = "WIDGET" if "dart" in target_lang.lower() else "FUNCTION"
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
        models = [
            m.model_dump() if hasattr(m, "model_dump") else m
            for m in extracted_bp.data_models
        ]
        aligned_contract = complete_aligned_contract(
            draft_dict=draft_contract,
            data_models=models,
            interface_contracts=ifaces,
            testable_assertions=assertions
        )
    else:
        # 2. Fallback cek apakah LLM menghasilkan blok kontrak JSON konvensional
        extracted_json = extract_contract_json_from_text(arch_plan)
        if extracted_json and isinstance(extracted_json, dict) and "interface_contracts" in extracted_json:
            aligned_contract = complete_aligned_contract(
                draft_dict=draft_contract,
                data_models=extracted_json.get("data_models", []),
                interface_contracts=extracted_json.get("interface_contracts", []),
                testable_assertions=extracted_json.get("testable_assertions", []),
                constraints=extracted_json.get("constraints"),
                ambiguities=extracted_json.get("unresolved_ambiguities")
            )
        else:
            aligned_contract = _build_default_aligned_contract(draft_contract, user_task, target_lang, arch_plan)

    # Observability: Catat penyelarasan kontrak ALIGNED
    tracer = get_tracer(state.get("run_id"))
    if tracer:
        tracer.log_event(
            stage="contract",
            event_type="contract_aligned",
            iteration=0,
            data={
                "contract_id": aligned_contract.get("contract_id"),
                "status": "ALIGNED",
                "models_count": len(aligned_contract.get("data_models", [])),
                "interfaces_count": len(aligned_contract.get("interface_contracts", [])),
                "assertions_count": len(aligned_contract.get("testable_assertions", []))
            }
        )
    
    new_log = (
        f"[System Architect]: Rencana arsitektur ({len(arch_plan)} char) dirancang. "
        f"Kontrak dialignasikan ({len(aligned_contract.get('testable_assertions', []))} assertions)."
    )
    current_logs = state.get("logs", [])
    
    return {
        "architecture_plan": arch_plan,
        "contract": aligned_contract,
        "contract_status": "ALIGNED",
        "blueprint_revision_count": state.get("blueprint_revision_count", 0),
        "status": "architect_done",
        "logs": current_logs + [new_log]
    }


