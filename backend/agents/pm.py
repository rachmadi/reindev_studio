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
    
    prompt = f"""Target Bahasa Pemrograman: {target_lang.upper()}
{ecosystem_guidance}

Deskripsi Tugas Pengguna:
{user_task}

Tuliskan spesifikasi SUPER RINGKAS (maksimal 100 kata) sesuai format 1, 2, 3 tanpa basa-basi pembuka atau penutup."""

    messages = [
        SystemMessage(content=PM_SYSTEM_PROMPT),
        HumanMessage(content=prompt)
    ]
    
    response = llm.invoke(messages)
    specs = response.content if hasattr(response, "content") else str(response)

    # P0-2: Domain detection & DRAFT Contract generation
    task_lower = user_task.lower()
    if is_dart or "widget" in task_lower:
        domain = "FLUTTER_WIDGET"
    elif any(k in task_lower for k in ["fastapi", "rest", "api", "crud", "endpoint", "inventaris"]):
        domain = "REST_API"
    elif any(k in task_lower for k in ["kalkulator", "calculator", "matriks", "matrix", "cli"]):
        domain = "CLI_TOOL"
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
                "req_count": len(reqs)
            }
        )

    new_log = f"[Product Manager]: Spesifikasi ({len(specs)} char) & DRAFT Contract ({domain}) berhasil dirumuskan."
    current_logs = state.get("logs", [])
    
    return {
        "specifications": specs,
        "contract": draft_contract,
        "contract_version": draft_contract.get("contract_version", "1.0.1"),
        "contract_status": "DRAFT",
        "status": "pm_done",
        "logs": current_logs + [new_log]
    }

