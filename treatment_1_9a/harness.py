# -*- coding: utf-8 -*-
"""
Treatment #1.9A — Architect Semantic Mapping Micro-Benchmark Harness
ReinDev Studio — Diagnostic Research Harness

Isolates:
- Baseline A: Existing context representation (exact production prompt from pilot)
- Condition B: Explicit generic canonical mapping (Obligation -> Blueprint Element)
- Condition C: Condition B + Generic worked example (WHAT -> HOW transformation)

Strictly non-production. Zero pipeline modifications.
"""

import os
import sys
import json
import time
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple
import requests

PROJECT_ROOT = Path(r"D:\Pekerjaan\Antigravity\reindev_studio")
sys.path.insert(0, str(PROJECT_ROOT))

from backend.agents.architect import (
    ARCHITECT_SYSTEM_PROMPT,
    _normalize_interface_contract_dict,
    _build_default_aligned_contract
)
from backend.blueprint_schema import parse_blueprint_json, normalize_blueprint_data_models
from backend.canonical_obligation import (
    extract_canonical_oracle_obligations,
    format_authoritative_obligation_ledger,
    check_obligation_coverage,
    normalize_route_path,
    find_deterministic_callable_fact
)
from backend.canonical_scenario import (
    extract_canonical_scenarios,
    format_scenarios_for_architect,
    extract_all_scaffold_facts
)
from backend.contract import (
    check_pre_freeze_authority_compatibility,
    seal_and_freeze_contract,
    create_draft_contract,
    complete_aligned_contract,
    ContractStatus
)
from backend.phase_validators import validate_architect_phase
from backend.environment_grounding import generate_fact_card_for_architect

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "qwen2.5-coder:7b"
TEMPERATURE = 0.2
NUM_CTX = 8192
NUM_PREDICT = 2048

ORACLE_DIR = PROJECT_ROOT / "dokumentasi-pengembangan/experiments/frozen_oracle/fastapi_t1"
OUTPUT_DIR = PROJECT_ROOT / "treatment_1_9a/output"
CONDITIONS_DIR = PROJECT_ROOT / "treatment_1_9a/conditions"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Base Prompt Builder
# -----------------------------------------------------------------------------

def load_cached_context() -> Dict[str, Any]:
    cached_path = CONDITIONS_DIR / "cached_pm_context.json"
    if not cached_path.exists():
        raise FileNotFoundError(f"Missing cached context: {cached_path}")
    with open(cached_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def build_base_prompt(context: Dict[str, Any], condition_mode: str) -> str:
    user_task = context["task"]
    target_lang = context["target_language"]
    specs = context["specifications"]
    v0_model = context.get("v0_requirement_model")

    structure_rule = (
        "ATURAN STRUKTUR PROYEK PYTHON (WAJIB):\n"
        "- Gunakan struktur modul Python sederhana dan kohesif: MAKSIMAL 1-2 file kode implementasi untuk Developer (misal: `main.py` atau `models.py` + `main.py`).\n"
        "- Gabungkan data models, in-memory store/state, dan antarmuka utama dalam modul utama (contoh: `main.py` atau `models.py` + `main.py`) untuk menghindari fragmentasi folder dan kesalahan impor silang.\n"
        "- DILARANG merancang hierarki folder yang terlalu dalam (hindari app/api/, app/schemas/, app/models/). Jaga struktur tetap datar di root.\n"
        "- ARTIFACT PURITY (WAJIB): file_tree dan files HANYA untuk modul kode implementasi. DILARANG KERAS memasukkan file pengujian/test ke dalam file_tree atau files!\n"
    )

    try:
        env_card = generate_fact_card_for_architect(target_lang, task=user_task)
    except Exception:
        env_card = ""
    env_section = f"\n{env_card}\n" if env_card else ""

    # V0 Section
    v0_section = ""
    if v0_model and isinstance(v0_model, dict):
        core_reqs = v0_model.get("requirements", [])
        if core_reqs:
            v0_lines = [
                f"- [{r.get('category', 'REQ')}] {r.get('description', str(r))}"
                if isinstance(r, dict) else f"- {r}"
                for r in core_reqs[:8]
            ]
            v0_section = "\nKebutuhan Aplikasi V0 (Epistemic Grounding):\n" + "\n".join(v0_lines) + "\n"

    # Oracle obligations & scenarios
    obs = extract_canonical_oracle_obligations(frozen_oracle_path=str(ORACLE_DIR))
    scs = extract_canonical_scenarios(frozen_oracle_path=str(ORACLE_DIR))

    oracle_ledger_section = format_authoritative_obligation_ledger(obs).strip()
    oracle_scenario_section = f"\n\n{format_scenarios_for_architect(scs).strip()}"

    # Section 2 & 4 modifications based on condition
    extra_condition_section = ""
    if condition_mode in ("B", "C"):
        extra_condition_section += """

[CANONICAL OBLIGATION TO BLUEPRINT BINDING SPECIFICATION]
Prinsip Pemetaan Kanonikal (Generic Binding Rules):
Setiap Acceptance Obligation di bawah ini WAJIB dipetakan secara eksplisit ke elemen ArchitecturalBlueprint yang bersesuaian:

1. Obligation ID: OBL-HTTP-POST-products
   Authority Identity:
     kind: INTERACTION
     value: /products
     method: POST
   Blueprint Binding:
     element_kind: interface_contracts
     required: true

2. Obligation ID: OBL-HTTP-GET-products
   Authority Identity:
     kind: INTERACTION
     value: /products
     method: GET
   Blueprint Binding:
     element_kind: interface_contracts
     required: true

3. Obligation ID: OBL-HTTP-GET-products_id
   Authority Identity:
     kind: INTERACTION
     value: /products/{id}
     method: GET
   Blueprint Binding:
     element_kind: interface_contracts
     required: true

4. Obligation ID: OBL-HTTP-DELETE-products_id
   Authority Identity:
     kind: INTERACTION
     value: /products/{id}
     method: DELETE
   Blueprint Binding:
     element_kind: interface_contracts
     required: true

ATURAN TRANSFORMASI KANONIKAL GENERIK:
- Jika identity.kind == "INTERACTION", elemen pada `interface_contracts` WAJIB menyertakan:
  * `route`: string path persis dari identity.value
  * `method`: string HTTP method persis dari identity.method
  * `identifier`: nama fungsi/handler pengimplementasi route
- Jika identity.kind == "DATA_MODEL", petakan ke `data_models` dengan `model_name` sesuai identity.value.
- Jika identity.kind == "OBSERVABLE_RUNTIME", petakan ke `interface_contracts` dengan `identifier` sesuai identity.value.
"""

    if condition_mode == "C":
        extra_condition_section += """

[GENERIC WORKED EXAMPLE — CANONICAL BINDING TRANSFORMATION]
Berikut adalah satu contoh generik transformasi antarmuka interaksi publik menjadi kontrak blueprint kanonikal (WHAT -> HOW):

Contoh Obligasi:
{
  "obligation_id": "OBL-SVC-01",
  "identity": {
    "kind": "INTERACTION",
    "value": "/api/v1/resource",
    "method": "PATCH"
  },
  "blueprint_binding": {
    "element_kind": "interface_contracts",
    "required": true
  }
}

Transformasi pada Blueprint:
1. Pada "interface_contracts":
{
  "identifier": "update_resource_handler",
  "route": "/api/v1/resource",
  "method": "PATCH",
  "target_file": "service.py",
  "parameters": [
    {
      "param_name": "payload",
      "param_type": "dict",
      "param_location": "BODY",
      "is_required": true
    }
  ],
  "expected_return": {
    "return_type": "dict"
  }
}
2. Pada "files" ("service.py" scaffold):
Deklarasikan fungsi antarmuka publik yang menangani route "/api/v1/resource" dengan method "PATCH".
"""

    if condition_mode == "A":
        # Baseline A: Exact Section [4] from production architect.py line 635
        sec4_interface_desc = '- "interface_contracts": list object interface {"identifier": str, "target_file": str, "parameters": list, "expected_return": dict}'
    else:
        # Condition B & C: Explicit canonical schema definition with route and method
        sec4_interface_desc = '- "interface_contracts": list object interface {"identifier": str, "route": str, "method": str, "target_file": str, "parameters": list, "expected_return": dict}'

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
{oracle_ledger_section}{oracle_scenario_section}{extra_condition_section}

[3] PM SPECIFICATION (PROPOSAL — DESIGN REFERENCE ONLY):
Peran: Product Manager adalah PROPOSAL perancangan fitur, BUKAN Acceptance Authority.
Aturan Otoritas: Jika terdapat perbedaan atau konflik antara PM Proposal dengan [2] ACCEPTANCE OBLIGATION LEDGER, maka [2] ACCEPTANCE OBLIGATION LEDGER MUTLAK MENANG. Architect DILARANG mengubah atau mengarang nama/tipe yang bertentangan dengan Acceptance Authority.
{specs}

[4] BLUEPRINT SCHEMA & CANONICAL OUTPUT SPECIFICATION:
Tugas Anda adalah menghasilkan SATU cetak biru ArchitecturalBlueprint dalam format JSON kanonikal di dalam penanda persis === BLUEPRINT JSON === ... === END BLUEPRINT JSON ===.
Format root harus berupa object JSON ArchitecturalBlueprint dengan fields:
- "authoritative_target_file": nama file kode utama (contoh "main.py" atau "lib/card_metric.dart")
- "file_tree": list path file implementasi (maksimal 1-2 file, DILARANG memasukkan file test)
- "architecture_summary": ringkasan arsitektur
- "files": mapping file path ke object {{"module_role": str, "imports": list, "code_scaffold": str}}
{sec4_interface_desc}
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

    return prompt

# -----------------------------------------------------------------------------
# LLM Invocation Helper
# -----------------------------------------------------------------------------

def invoke_ollama_chat(system_prompt: str, user_prompt: str) -> Tuple[str, float, int, int]:
    t0 = time.time()
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "options": {
            "temperature": TEMPERATURE,
            "num_ctx": NUM_CTX,
            "num_predict": NUM_PREDICT
        },
        "stream": False
    }

    resp = requests.post(OLLAMA_URL, json=payload, timeout=300)
    latency = time.time() - t0
    resp.raise_for_status()
    data = resp.json()

    raw_output = data.get("message", {}).get("content", "")
    prompt_tokens = data.get("prompt_eval_count", 0)
    eval_tokens = data.get("eval_count", 0)

    return raw_output, latency, prompt_tokens, eval_tokens

# -----------------------------------------------------------------------------
# Evaluation Engine
# -----------------------------------------------------------------------------

def evaluate_condition_run(
    condition_name: str,
    raw_output: str,
    latency: float,
    prompt_tokens: int,
    eval_tokens: int
) -> Dict[str, Any]:
    output_chars = len(raw_output)
    user_task = "Bangun modul REST API FastAPI untuk manajemen inventaris produk dengan validasi Pydantic dan automated pytest."

    # 1. Structural Blueprint Validity
    extracted_bp, bp_err = parse_blueprint_json(raw_output)
    is_structurally_valid = (extracted_bp is not None and bp_err is None)
    parse_error_msg = str(bp_err) if bp_err else None

    declared_symbols = []
    declared_routes = []
    scaffold_facts = []
    if extracted_bp:
        primary_file = extracted_bp.authoritative_target_file or "main.py"
        scaffold_files = {}
        if hasattr(extracted_bp, "files") and extracted_bp.files:
            for fp, fmod in extracted_bp.files.items():
                sc_text = getattr(fmod, "code_scaffold", "") if hasattr(fmod, "code_scaffold") else (fmod.get("code_scaffold", "") if isinstance(fmod, dict) else str(fmod))
                if sc_text:
                    scaffold_files[fp] = sc_text
        scaffold_facts = extract_all_scaffold_facts(scaffold_files) if extract_all_scaffold_facts else []

        if hasattr(extracted_bp, "interface_contracts") and extracted_bp.interface_contracts:
            for ifc in extracted_bp.interface_contracts:
                ident = getattr(ifc, "identifier", None) or (ifc.get("identifier") if isinstance(ifc, dict) else None)
                route = getattr(ifc, "route", None) or (ifc.get("route") if isinstance(ifc, dict) else None)
                method = getattr(ifc, "method", None) or (ifc.get("method") if isinstance(ifc, dict) else None)
                if ident:
                    declared_symbols.append(ident)
                if route:
                    declared_routes.append({"identifier": ident, "route": route, "method": method})

        if hasattr(extracted_bp, "data_models") and extracted_bp.data_models:
            for dm in extracted_bp.data_models:
                mname = getattr(dm, "model_name", None) or (dm.get("model_name") if isinstance(dm, dict) else None)
                if mname:
                    declared_symbols.append(mname)

        ifaces = []
        assertions = []
        for idx, ifc in enumerate(extracted_bp.interface_contracts, 1):
            d_raw = ifc.model_dump() if hasattr(ifc, "model_dump") else dict(ifc)
            if not d_raw.get("route") and scaffold_facts:
                fact = find_deterministic_callable_fact(d_raw.get("identifier"), d_raw.get("target_file"), scaffold_facts)
                if fact and fact.route:
                    d_raw["route"] = fact.route
                    if fact.http_method:
                        d_raw["http_method"] = fact.http_method
                    d_raw["interface_type"] = "HTTP_ENDPOINT"

            d = _normalize_interface_contract_dict(d_raw, idx, False, primary_file)
            ifaces.append(d)
            ident = d.get("identifier", "target")
            assertions.append({
                "assertion_id": f"AST-{idx:02d}",
                "linked_req_id": "REQ-01",
                "linked_interface_id": d["interface_id"],
                "test_scenario": f"Execution of {ident} meets functional requirements",
                "target_symbol": ident,
                "input_fixture": f"{ident}()",
                "expected_outcome": {"outcome_type": "VALUE_EQUALS", "value": 0}
            })

        canonical_models, model_errs = normalize_blueprint_data_models(
            extracted_bp.data_models,
            default_target_file=primary_file
        )

        draft = create_draft_contract(
            raw_intent=user_task,
            target_language="python",
            goal_summary="Inventory API"
        )

        aligned_contract = complete_aligned_contract(
            draft_dict=draft,
            data_models=canonical_models,
            interface_contracts=ifaces,
            testable_assertions=assertions
        )

        # 2. Seal & Freeze Contract Evaluation (Authority Binding)
        success, frozen_contract, errors, warnings = seal_and_freeze_contract(
            aligned_contract,
            frozen_oracle_path=str(ORACLE_DIR),
            task_text=user_task,
            blueprint=extracted_bp
        )

        oracle_obs = extract_canonical_oracle_obligations(frozen_oracle_path=str(ORACLE_DIR))
        cov_matrix = check_obligation_coverage(
            obligations=oracle_obs,
            contract=aligned_contract,
            blueprint=extracted_bp
        )
    else:
        success = False
        errors = [parse_error_msg or "Failed to parse blueprint JSON"]
        warnings = []
        oracle_obs = extract_canonical_oracle_obligations(frozen_oracle_path=str(ORACLE_DIR))
        cov_matrix = check_obligation_coverage(
            obligations=oracle_obs,
            contract={},
            blueprint=None
        )

    # 3. Identity Fidelity
    auth_paths = {"/products", "/products/{id}"}
    observed_paths = {r["route"].rstrip("/") for r in declared_routes if r.get("route")}
    for f in scaffold_facts:
        if f.route:
            observed_paths.add(f.route.rstrip("/"))
    identity_fidelity = auth_paths.issubset(observed_paths)

    # 4. Semantic Mapping Fidelity
    has_route_bindings = len(declared_routes) > 0 or any(f.route for f in scaffold_facts)

    # 5. Invented Elements
    oracle_symbols = {"/products", "/products/{id}", "Product"}
    invented_elements = [s for s in declared_symbols if s not in oracle_symbols and not any(s in f.name for f in scaffold_facts if f.route)]

    # 6. Authority Substitution
    authority_substituted = (not has_route_bindings and any("product" in s.lower() for s in declared_symbols))

    verdict = "PASS" if (success and cov_matrix.is_fully_covered and is_structurally_valid) else "FAIL"

    metrics = {
        "condition": condition_name,
        "verdict": verdict,
        "seal_success": success,
        "latency_sec": round(latency, 2),
        "prompt_tokens": prompt_tokens,
        "eval_tokens": eval_tokens,
        "raw_output_chars": output_chars,
        "structural_blueprint_validity": is_structurally_valid,
        "parse_error": parse_error_msg,
        "obligation_coverage": {
            "total_obligations": cov_matrix.obligations_count,
            "covered_count": cov_matrix.covered_count,
            "missing_count": cov_matrix.missing_count,
            "is_fully_covered": cov_matrix.is_fully_covered
        },
        "identity_fidelity": identity_fidelity,
        "observed_paths": list(observed_paths),
        "semantic_mapping_fidelity": {
            "has_route_bindings": has_route_bindings,
            "declared_routes_count": len(declared_routes),
            "declared_routes": declared_routes
        },
        "invented_elements": invented_elements,
        "authority_substitution": authority_substituted,
        "errors": errors[:3],
        "warnings": warnings[:3]
    }

    return metrics

# -----------------------------------------------------------------------------
# Main Runner
# -----------------------------------------------------------------------------

def run_microbenchmark():
    print("=" * 80)
    print("TREATMENT #1.9A: ARCHITECT SEMANTIC MAPPING MICRO-BENCHMARK")
    print(f"Model: {MODEL_NAME} | num_ctx: {NUM_CTX} | num_predict: {NUM_PREDICT}")
    print("=" * 80)

    context = load_cached_context()
    conditions = ["A", "B", "C"]
    results = {}

    for cond in conditions:
        print(f"\n>>> Running Condition {cond}...")
        user_prompt = build_base_prompt(context, condition_mode=cond)

        prompt_file = OUTPUT_DIR / f"prompt_condition_{cond}.txt"
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write(f"=== SYSTEM PROMPT ===\n{ARCHITECT_SYSTEM_PROMPT}\n\n=== USER PROMPT ===\n{user_prompt}")

        raw_out, latency, p_tokens, e_tokens = invoke_ollama_chat(
            system_prompt=ARCHITECT_SYSTEM_PROMPT,
            user_prompt=user_prompt
        )

        raw_out_file = OUTPUT_DIR / f"raw_output_condition_{cond}.txt"
        with open(raw_out_file, 'w', encoding='utf-8') as f:
            f.write(raw_out)

        metrics = evaluate_condition_run(
            condition_name=cond,
            raw_output=raw_out,
            latency=latency,
            prompt_tokens=p_tokens,
            eval_tokens=e_tokens
        )
        results[cond] = metrics

        print(f"  Verdict: {metrics['verdict']} | Seal: {metrics['seal_success']} | Latency: {metrics['latency_sec']}s | Chars: {metrics['raw_output_chars']}")
        print(f"  Structural Validity: {metrics['structural_blueprint_validity']}")
        print(f"  Obligation Coverage: {metrics['obligation_coverage']['covered_count']}/{metrics['obligation_coverage']['total_obligations']} (Fully Covered: {metrics['obligation_coverage']['is_fully_covered']})")
        print(f"  Identity Fidelity: {metrics['identity_fidelity']} (Observed Paths: {metrics['observed_paths']})")
        print(f"  Route Bindings: {metrics['semantic_mapping_fidelity']['has_route_bindings']} ({metrics['semantic_mapping_fidelity']['declared_routes_count']} routes)")
        print(f"  Invented Elements: {metrics['invented_elements']}")
        print(f"  Authority Substitution: {metrics['authority_substitution']}")
        if metrics['errors']:
            print(f"  Errors: {metrics['errors']}")

    summary_file = OUTPUT_DIR / "treatment_1_9a_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 80)
    print("MICRO-BENCHMARK COMPLETE")
    print(f"Results saved to: {summary_file}")
    print("=" * 80)

if __name__ == "__main__":
    run_microbenchmark()
