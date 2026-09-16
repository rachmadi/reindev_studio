import re
from typing import Dict, Any, List, Optional
from langchain_core.messages import SystemMessage, HumanMessage
try:
    from ..state import SquadState
    from ..config import get_llm
    from ..contract import create_draft_contract, ContractStatus
    from ..tracer import get_tracer
except (ImportError, ValueError):
    from state import SquadState
    from config import get_llm
    try:
        from contract import create_draft_contract, ContractStatus
    except ImportError:
        def create_draft_contract(*args, **kwargs): return {}
        class ContractStatus: DRAFT = "DRAFT"
    try:
        from tracer import get_tracer
    except ImportError:
        def get_tracer(run_id=None): return None

PM_SYSTEM_PROMPT = """Anda adalah Senior Technical Product Manager dalam tim rekayasa perangkat lunak ReinDev Studio.
Tugas Anda adalah merumuskan dokumen spesifikasi teknis (Application Requirement Model) yang substantif, constructible, dan setia (faithful) terhadap kebutuhan pengguna dan model epistemik V0.

DOKTRIN UTAMA: INTERPRETATION ≠ INVENTION
- Turunkan kebutuhan teknis secara logis agar constructible bagi Architect dan Developer downstream.
- JANGAN mengarang atribut data, entitas, atau logika bisnis yang tidak didukung fakta atau kebutuhan pengguna.
- Pertahankan ketidakpastian atau hal yang belum terdefinisi sebagai batasan epistemik defensif (open requirements/gaps).

PEDOMAN KELENGKAPAN SPESIFIKASI:
Dokumen spesifikasi Anda harus mencakup komponen inti rekayasa:
1. Ringkasan Sistem: Ruang lingkup, sasaran utama modul, dan platform target secara konkret dan lugas.
2. Kebutuhan Fungsional / Kemampuan Utama: Rincian fungsi utama sistem yang diturunkan dari fakta pengguna dan interpretasi logis yang valid.
3. Kriteria Penerimaan Terukur: Skenario pengujian konkret dengan kondisi input dan ekspektasi luaran yang dapat diverifikasi.
4. Batasan Epistemik & Kebutuhan Terbuka: Dokumentasi batas rekayasa minimal, asumsi standar, dan butir terbuka/gap yang sengaja dipertahankan tanpa spekulasi atribut liar.

Petunjuk Teknis:
- Tuliskan spesifikasi secara substantif, langsung pada pokok bahasan, tanpa basa-basi pembuka atau penutup.
- Pastikan kriteria penerimaan terukur dan konkret untuk memandu verifikasi hilir.
"""


def pm_agent(state: SquadState) -> dict:
    llm = get_llm(role="pm", provider=state.get("provider"))
    
    user_task = state.get("task", "")
    target_lang = (state.get("target_language") or "python").strip().lower()
    is_dart = "dart" in target_lang or "flutter" in target_lang
    
    ecosystem_guidance = (
        "Target Ekosistem: DART / FLUTTER (Sound Null Safety, Strong Typing, pubspec.yaml, lib/ dan test/)\n"
        if is_dart else
        "Target Ekosistem: PYTHON (PEP 8, Type Hinting, pytest)"
    )

    repair_count = (state.get("repair_attempt_counts") or {}).get("pm", 0)
    pm_feedback = state.get("pm_feedback") or ""
    
    # 1. Ingest Structured V0 Requirement Model with Strict Epistemic Stratification
    v0_section = ""
    v0_model = state.get("v0_requirement_model")
    v0_unresolved: List[str] = []

    if v0_model and isinstance(v0_model, dict):
        ledger = v0_model.get("epistemic_ledger", [])
        facts = [it.get("statement") for it in ledger if it.get("epistemic_status") == "FACT"]
        interpretations = [it.get("statement") for it in ledger if it.get("epistemic_status") == "INTERPRETATION"]
        assumptions = [it.get("statement") for it in ledger if it.get("epistemic_status") == "ASSUMPTION"]
        v0_unresolved = [it.get("statement") for it in ledger if it.get("epistemic_status") in ("UNRESOLVED", "AMBIGUITY")]

        app_model = v0_model.get("application_requirement_model") or {}
        v0_reqs = app_model.get("functional_requirements") or []
        v0_data_reqs = app_model.get("data_requirements") or []
        v0_constraints = app_model.get("constraints") or []

        constructibility = v0_model.get("constructibility") or {}
        c_status = constructibility.get("status", "WORKABLE")
        c_rationale = constructibility.get("rationale", "")
        v0_minimal_interp = constructibility.get("minimal_viable_interpretation", "")

        entity_lines = []
        for dr in v0_data_reqs:
            e_name = dr.get("entity_name", "Entity")
            kf = ", ".join(dr.get("known_fields") or []) or "tidak ada field eksplisit"
            uf = ", ".join(dr.get("unknown_fields") or []) or "none"
            entity_lines.append(f"  * Entitas `{e_name}`: field diketahui [{kf}], field terbuka [{uf}]")
        entity_summary_str = "\n".join(entity_lines) if entity_lines else "  * Tidak ada entitas data khusus"

        v0_section = f"""
EVIDENCE TERSTRUKTUR DARI V0 REQUIREMENT INTERPRETER:
- Status Konstruktibilitas: {c_status} ({c_rationale})
- Interpretasi Minimal Layak: {v0_minimal_interp or 'Gunakan interpretasi langsung dari fakta'}

STRATIFIKASI STATUS EPISTEMIK:
1. Fakta Terverifikasi (Ground Truth - Batasan Mutlak):
{chr(10).join(f'   * {f}' for f in facts) if facts else '   * Tidak ada fakta tambahan'}
2. Kebutuhan Fungsional V0:
{chr(10).join(f'   * {r}' for r in v0_reqs) if v0_reqs else '   * Diturunkan dari task'}
3. Model Entitas Data V0:
{entity_summary_str}
4. Interpretasi Logis (Boleh digunakan sebagai derived requirements):
{chr(10).join(f'   * {i}' for i in interpretations) if interpretations else '   * Tidak ada interpretasi khusus'}
5. Asumsi Rekayasa Standar (JANGAN promosikan menjadi Fakta pengguna):
{chr(10).join(f'   * {a}' for a in assumptions + v0_constraints) if (assumptions or v0_constraints) else '   * Asumsi standar'}
6. Kebutuhan Terbuka / Epistemik Gap (Pertahankan sebagai batasan terbuka, JANGAN diisi tebakan):
{chr(10).join(f'   * {u}' for u in v0_unresolved) if v0_unresolved else '   * Tidak ada ambiguitas terbuka'}

DOKTRIN EPISTEMIK UNTUK PM:
- Fakta Terverifikasi menjadi batasan mutlak ruang lingkup sistem.
- Interpretasi logis diperbolehkan untuk memastikan keterbangunan (constructibility), tetapi jangan menambah atribut atau domain field baru yang tidak disebutkan pengguna.
- Hormati `field terbuka` pada model entitas di atas; biarkan terbuka sebagai batasan defensif.
- Butir terbuka / gap wajib diakui secara eksplisit, bukan ditutupi dengan spekulasi atribut sepihak.
"""

    # 2. Preservative Repair Section (Turn 1+)
    repair_section = ""
    if repair_count > 0:
        prev_specs = state.get("specifications", "") or ""
        prev_snippet = f"\nKANDIDAT SPESIFIKASI SEBELUMNYA:\n```\n{prev_specs}\n```\n" if prev_specs.strip() else "\nKANDIDAT SPESIFIKASI SEBELUMNYA: [KOSONG / GENERATION COLLAPSE]\n"
        
        repair_section = f"""
PERINGATAN PERBAIKAN REINDEVSQUAD (Percobaan #{repair_count}):
Spesifikasi sebelumnya ditolak oleh Phase-End Validator V1 dengan evaluasi deterministik:
{pm_feedback if pm_feedback else 'Format spesifikasi belum memenuhi kelengkapan struktural atau kriteria penerimaan terukur.'}
{prev_snippet}
PANDUAN PERBAIKAN PRESERVATIF:
1. PRESERVE: Pertahankan bagian spesifikasi sebelumnya yang sudah valid dan selaras dengan intent pengguna.
2. REPAIR: Perbaiki secara spesifik pelanggaran yang dilaporkan validator di atas (misalnya lengkapi kriteria penerimaan atau perjelas ruang lingkup sistem).
3. ANTI-COLLAPSE & V0 GROUNDING: Jika percobaan sebelumnya kosong atau terlalu pendek, JANGAN menekan luaran! Manfaatkan Fakta V0, Kebutuhan Fungsional V0, dan Interpretasi Minimal Layak di atas untuk menyusun spesifikasi yang lengkap, substantif, dan mandiri.
"""

    prompt = f"""Target Bahasa Pemrograman: {target_lang.upper()}
{ecosystem_guidance}

Deskripsi Tugas Pengguna:
{user_task}
{v0_section}
{repair_section}
Tuliskan dokumen spesifikasi teknis yang substantif, mencakup ringkasan sistem, kebutuhan fungsional, kriteria penerimaan terukur, dan batasan terbuka/epistemik sesuai pedoman di atas."""

    messages = [
        SystemMessage(content=PM_SYSTEM_PROMPT),
        HumanMessage(content=prompt)
    ]
    
    response = llm.invoke(messages)
    specs = response.content if hasattr(response, "content") else str(response)

    # Domain classification (mission-agnostic categories matching DomainType enum)
    task_lower = user_task.lower()
    if is_dart or "widget" in task_lower:
        domain = "FLUTTER_WIDGET"
    elif any(k in task_lower for k in ["fastapi", "rest", "api", "crud", "endpoint", "inventaris"]):
        domain = "REST_API"
    elif any(k in task_lower for k in ["kalkulator", "calculator", "matriks", "matrix", "cli"]):
        domain = "CLI_TOOL"
    elif any(k in task_lower for k in ["pipeline", "etl", "dataform", "dbt", "stream"]):
        domain = "DATA_PIPELINE"
    else:
        domain = "ALGORITHM"

    # Robust acceptance semantics extraction from specification text (bullet/numbered lines)
    acceptance_semantics = []
    for line in specs.splitlines():
        line_s = line.strip()
        if line_s.startswith("-") or line_s.startswith("*") or (len(line_s) > 2 and line_s[0].isdigit() and line_s[1] in (".", ")")):
            cleaned = line_s.lstrip("-*0123456789. )").strip()
            if cleaned and len(cleaned) > 5:
                acceptance_semantics.append(cleaned)
    if not acceptance_semantics:
        acceptance_semantics = ["Sistem terkompilasi bebas error dan memenuhi fungsi dasar intent."]

    # Standard requirement representation (strictly reusing existing schema)
    reqs = [
        {
            "req_id": "REQ-01",
            "description": user_task,
            "acceptance_semantics": acceptance_semantics[:3]
        }
    ]

    goal_summary = user_task[:120] if user_task else "Spesifikasi sistem teknis"

    # Reuse existing draft_contract factory and synthesis path strictly
    draft_contract = create_draft_contract(
        raw_intent=user_task,
        target_language=target_lang,
        domain=domain,
        goal_summary=goal_summary,
        reqs=reqs
    )

    # Standard dual compatibility for validator inspection
    draft_contract["requirements"] = reqs

    # Standard provenance metadata
    if isinstance(draft_contract.get("provenance"), dict):
        draft_contract["provenance"]["v0_grounded"] = bool(v0_model)
        draft_contract["provenance"]["pm_capability_version"] = "treatment_1_7_v1"

    # Observability: Log draft contract creation
    tracer = get_tracer(state.get("run_id"))
    if tracer:
        tracer.log_event(
            stage="contract",
            event_type="contract_created",
            iteration=repair_count,
            data={
                "contract_id": draft_contract.get("contract_id"),
                "status": "DRAFT",
                "domain": domain,
                "target_language": target_lang,
                "req_count": len(reqs),
                "repair_attempt": repair_count,
                "v0_grounded": bool(v0_model),
                "pm_capability_version": "treatment_1_7_v1"
            }
        )

    repair_str = f" [Repair #{repair_count}]" if repair_count > 0 else ""
    new_log = f"[Product Manager]{repair_str}: Spesifikasi ({len(specs)} char) & DRAFT Contract ({domain}) berhasil dirumuskan."
    current_logs = state.get("logs", [])
    
    return {
        "specifications": specs,
        "contract": draft_contract,
        "contract_version": draft_contract.get("contract_version", "1.0.1"),
        "contract_status": "DRAFT",
        "status": "pm_done",
        "logs": current_logs + [new_log]
    }
