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

PM_SYSTEM_PROMPT = """Anda adalah Senior Software Product Manager dalam tim rekayasa perangkat lunak ReinDev Studio.
Tugas Anda adalah merumuskan spesifikasi teknis SUPER RINGKAS (Maksimal 100 kata total).

Format luaran WAJIB:
1. Ringkasan Sistem (1 kalimat)
2. User Stories (Maksimal 2 butir)
3. Acceptance Criteria (Maksimal 2 skenario konkret)

DILARANG KERAS menulis salam, pengantar, atau kesimpulan bertele-tele. Langsung tuliskan poin 1, 2, dan 3.
"""

def pm_agent(state: SquadState) -> dict:
    llm = get_llm(role="pm", provider=state.get("provider"))
    
    user_task = state.get("task", "")
    target_lang = state.get("target_language", "python").strip()
    is_dart = "dart" in target_lang.lower() or "flutter" in target_lang.lower()
    
    ecosystem_guidance = (
        "Target Ekosistem: DART / FLUTTER (Sound Null Safety, Strong Typing, pubspec.yaml, lib/ dan test/)\n"
        if is_dart else
        "Target Ekosistem: PYTHON (PEP 8, Type Hinting, pytest)"
    )

    repair_count = (state.get("repair_attempt_counts") or {}).get("pm", 0)
    pm_feedback = state.get("pm_feedback") or ""
    repair_section = ""
    if repair_count > 0 and pm_feedback:
        repair_section = f"""
PERINGATAN PERBAIKAN (Percobaan Perbaikan #{repair_count}):
Spesifikasi sebelumnya ditolak oleh Phase-End Validator V1 dengan umpan balik:
{pm_feedback}

Instruksi Perbaikan Wajib:
1. Penuhi seluruh komponen yang diminta (khususnya Ringkasan Sistem, User Stories, dan Acceptance Criteria terukur).
2. Pertahankan kebutuhan awal pengguna tanpa membuat asumsi di luar cakupan tugas.
3. Patuhi format luaran 1, 2, 3 secara ketat.
"""
    
    v0_section = ""
    v0_model = state.get("v0_requirement_model")
    if v0_model and isinstance(v0_model, dict):
        facts = [it.get("statement") for it in v0_model.get("epistemic_ledger", []) if it.get("epistemic_status") == "FACT"]
        interpretations = [it.get("statement") for it in v0_model.get("epistemic_ledger", []) if it.get("epistemic_status") == "INTERPRETATION"]
        assumptions = [it.get("statement") for it in v0_model.get("epistemic_ledger", []) if it.get("epistemic_status") == "ASSUMPTION"]
        unresolved = [it.get("statement") for it in v0_model.get("epistemic_ledger", []) if it.get("epistemic_status") in ("UNRESOLVED", "AMBIGUITY")]

        c_status = v0_model.get("constructibility", {}).get("status", "WORKABLE")

        v0_section = f"""
MODEL KEBUTUHAN TERSTRUKTUR (Dari V0 Requirement Interpreter):
- Fakta Terverifikasi (Ground Truth): {'; '.join(facts) if facts else 'Tidak ada fakta tambahan'}
- Interpretasi Logis: {'; '.join(interpretations) if interpretations else 'Tidak ada'}
- Asumsi Rekayasa Standar: {'; '.join(assumptions) if assumptions else 'Tidak ada'}
- Butir Belum Terdefinisi / Terbuka: {'; '.join(unresolved) if unresolved else 'Tidak ada'}
- Status Konstruktibilitas: {c_status}

DOKTRIN PENTING UNTUK PM:
1. Perlakukan Fakta Terverifikasi sebagai batasan mutlak.
2. JANGAN mempromosikan Interpretasi atau Asumsi menjadi Fakta pengguna.
3. JANGAN mengarang atribut entitas atau field data baru yang tidak tercantum dalam model di atas.
4. Pertahankan butir yang belum terdefinisi sebagai batasan terbuka, jangan ditutup dengan spekulasi atribut sepihak.
"""

    prompt = f"""Target Bahasa Pemrograman: {target_lang.upper()}
{ecosystem_guidance}

Deskripsi Tugas Pengguna:
{user_task}
{v0_section}
{repair_section}
Tuliskan spesifikasi SUPER RINGKAS (maksimal 100 kata) sesuai format 1, 2, 3 tanpa basa-basi pembuka atau penutup."""

    messages = [
        SystemMessage(content=PM_SYSTEM_PROMPT),
        HumanMessage(content=prompt)
    ]
    
    response = llm.invoke(messages)
    specs = response.content if hasattr(response, "content") else str(response)

    # Domain detection & DRAFT Contract generation (mission-agnostic categories)
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

    # Ekstrak acceptance semantics dari baris spesifikasi
    acceptance_semantics = []
    for line in specs.splitlines():
        line_s = line.strip()
        if line_s.startswith("-") or line_s.startswith("*") or (len(line_s) > 2 and line_s[:2] in ("1.", "2.", "3.")):
            acceptance_semantics.append(line_s.lstrip("-*0123456789. "))
    if not acceptance_semantics:
        acceptance_semantics = ["Sistem terkompilasi bebas error dan memenuhi fungsi dasar intent."]

    reqs = [
        {
            "req_id": "REQ-01",
            "description": user_task,
            "acceptance_semantics": acceptance_semantics[:3]
        }
    ]

    draft_contract = create_draft_contract(
        raw_intent=user_task,
        target_language=target_lang,
        domain=domain,
        goal_summary=user_task[:120],
        reqs=reqs
    )

    # Observability: Catat pembuatan DRAFT contract
    tracer = get_tracer(state.get("run_id"))
    if tracer:
        tracer.log_event(
            stage="contract",
            event_type="contract_created",
            iteration=0,
            data={
                "contract_id": draft_contract.get("contract_id"),
                "status": "DRAFT",
                "domain": domain,
                "target_language": target_lang,
                "req_count": len(reqs),
                "repair_attempt": repair_count,
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

