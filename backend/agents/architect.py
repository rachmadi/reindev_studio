import re
import json
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

ARCHITECT_SYSTEM_PROMPT = """Anda adalah Senior Software & System Architect dalam tim rekayasa perangkat lunak ReinDev Studio.
Tugas Anda adalah menerima spesifikasi dari Product Manager dan merancang struktur arsitektur perangkat lunak yang modular, terpisah dengan jelas (Separation of Concerns), dan mudah diuji.

Format luaran yang WAJIB Anda hasilkan:
1. Peta Struktur File Proyek (File Tree Structure) sesuai target bahasa pemrograman yang diminta
2. Tanggung Jawab Komponen / Modul
3. Kontrak Interface & Type Annotation (Nama fungsi, parameter, return type)
4. Panduan Implementasi untuk Developer Agent

Gunakan Bahasa Indonesia yang profesional, presisi, dan terstruktur tanpa kata-kata pengantar berlebih.
"""

def _build_default_aligned_contract(draft_contract: dict, task: str, target_lang: str, arch_plan: str = "") -> dict:
    """Membangun spesifikasi teknis ALIGNED yang konsisten dengan 4 pilar validasi gate."""
    is_dart = "dart" in target_lang.lower() or "flutter" in target_lang.lower()
    task_l = task.lower()

    if is_dart:
        data_models = [
            {
                "model_name": "CardMetricData",
                "target_file": "lib/card_metric.dart",
                "fields": [
                    {"field_name": "title", "field_type": "String", "is_required": False, "description": "Judul metrik"},
                    {"field_name": "value", "field_type": "double", "is_required": False, "description": "Nilai numerik metrik"},
                    {"field_name": "unit", "field_type": "String", "is_required": False, "description": "Satuan metrik"}
                ]
            }
        ]
        interface_contracts = [
            {
                "interface_id": "IFC-01",
                "interface_type": "WIDGET",
                "identifier": "CardMetric",
                "http_method": None,
                "target_file": "lib/card_metric.dart",
                "parameters": [
                    {"param_name": "data", "param_type": "CardMetricData", "param_location": "PROP", "is_required": False}
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
        # Generic CLI / Algorithm module
        # Periksa apakah arch_plan mendefinisikan kontrak fungsi eksplisit (misal: - dot_product(...) -> float)
        func_matches = re.findall(r"-\s*([A-Za-z_][A-Za-z0-9_]*)\s*\((.*?)\)(?:\s*->\s*([A-Za-z0-9_\[\], ]+))?", arch_plan)
        if func_matches:
            data_models = []
            interface_contracts = []
            testable_assertions = []
            for idx, (fn_name, params_str, ret_type) in enumerate(func_matches, 1):
                ifid = f"IFC-0{idx}" if idx < 10 else f"IFC-{idx}"
                astid = f"AST-0{idx}" if idx < 10 else f"AST-{idx}"
                ret = ret_type.strip() if ret_type else "float"
                interface_contracts.append({
                    "interface_id": ifid,
                    "interface_type": "FUNCTION",
                    "identifier": fn_name,
                    "http_method": None,
                    "target_file": "vector_math.py" if "vector" in arch_plan.lower() else "main.py",
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
            data_models = []
            interface_contracts = [
                {
                    "interface_id": "IFC-01",
                    "interface_type": "FUNCTION",
                    "identifier": "calculate",
                    "http_method": None,
                    "target_file": "main.py",
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
                    "target_symbol": "calculate",
                    "input_fixture": "calculate(2.0, 3.0)",
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
        "- Untuk REST API FastAPI: gabungkan model Pydantic, in-memory store, dan routes dalam `main.py` (atau `models.py` dan `main.py`) untuk menghindari fragmentasi folder dan kesalahan impor silang.\n"
        "- DILARANG merancang hierarki folder yang terlalu dalam (hindari app/api/, app/schemas/, app/models/). Jaga struktur tetap datar di root.\n"
    )
    
    prompt = f"""TARGET BAHASA PEMROGRAMAN WAJIB: {target_lang.upper()}

{structure_rule}

Deskripsi Tugas Pengguna:
{user_task}

Spesifikasi Product Manager:
{specs}

ATURAN KETAT:
Seluruh file tree, hierarki modul, dan ekstensi file WAJIB menggunakan bahasa {target_lang.upper()} murni (Maksimal 2-3 file total).
DILARANG KERAS merancang file tree atau struktur dalam bahasa selain {target_lang.upper()}!

Tuliskan diagram struktur file tree dan kontrak interface secara SUPER RINGKAS tanpa basa-basi narasi."""

    messages = [
        SystemMessage(content=ARCHITECT_SYSTEM_PROMPT),
        HumanMessage(content=prompt)
    ]
    
    response = llm.invoke(messages)
    arch_plan = response.content if hasattr(response, "content") else str(response)

    # P0-2: Lengkapi kontrak menjadi ALIGNED
    draft_contract = state.get("contract")
    if not draft_contract or not isinstance(draft_contract, dict):
        draft_contract = create_draft_contract(
            raw_intent=user_task,
            target_language=target_lang,
            goal_summary=user_task[:120]
        )

    # Cek apakah LLM menghasilkan blok kontrak JSON
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
        "status": "architect_done",
        "logs": current_logs + [new_log]
    }

