# -*- coding: utf-8 -*-
"""
ReinDev Studio — Production Server & Execution Gateway
Integrasi penuh 6 End-Phase Quality Boundaries (V1–V6), Universal 2-Repair Budget,
dan Otomasi Preset Frozen Oracle Checksum Verification.
"""

import os
import sys
import time
import json
import asyncio
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Ensure root path is accessible
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from backend.state import SquadState
from backend.graph import squad_graph
from backend.tracer import RunTracer, get_tracer, compute_sha256, compute_dict_hashes
from backend.contract import ContractStatus

app = FastAPI(
    title="ReinDev Studio Backend API",
    description="Autonomous Multi-Agent Software Engineering Studio Engine (FastAPI + LangGraph + 6 End-Phase Quality Boundaries)",
    version="1.0.0"
)

# REQ-011: CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Runtime Configuration State
CONFIG_STATE = {
    "provider": os.getenv("LLM_PROVIDER", "ollama"),
    "ollama_base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    "ollama_model": os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b"),
    "openrouter_model": os.getenv("OPENROUTER_CODER_MODEL", "deepseek/deepseek-chat"),
    "max_iterations": 3,
    "target_language": "python",
    "executor_intervention_enabled": True,
    "executor_mode": "SAFE",
    "frozen_oracle_path": None,
}

OUTPUT_DIR = BACKEND_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Registri Preset Misi Otoritatif
# ---------------------------------------------------------------------------
PRESET_REGISTRY: Dict[str, Dict[str, Any]] = {
    "fastapi_t1": {
        "preset_id": "fastapi_t1",
        "title": "FastAPI CRUD",
        "task": "Bangun modul REST API FastAPI untuk manajemen inventaris produk dengan validasi Pydantic dan automated pytest.",
        "target_language": "python",
        "oracle_path": PROJECT_ROOT / "dokumentasi-pengembangan/experiments/frozen_oracle/fastapi_t1",
        "expected_sha": "a1db9bb1f6eaf47d5cf56e102c4a0f6e1f49d757e9faa1485b36f2972a152d63",
        "oracle_file": "test_main.py",
        "authoritative_file": "main.py",
        "n_tests": 5,
        "keywords": ["fastapi", "inventaris", "pydantic"]
    },
    "cli_t1": {
        "preset_id": "cli_t1",
        "title": "CLI Calculator",
        "task": "Bangun kalkulator CLI Python dengan operasi matematika matriks dan penanganan error komprehensif.",
        "target_language": "python",
        "oracle_path": PROJECT_ROOT / "dokumentasi-pengembangan/experiments/frozen_oracle/cli_t1",
        "expected_sha": "0bd5b598afa7ae4c9cdf0e269d13136b51d35a4e0b1ac6548f0a2cf8a8eba124",
        "oracle_file": "test_main.py",
        "authoritative_file": "main.py",
        "n_tests": 5,
        "keywords": ["kalkulator cli", "matriks", "matrix", "cli calculator"]
    },
    "flutter_t1": {
        "preset_id": "flutter_t1",
        "title": "Flutter Widget",
        "task": "Bangun komponen widget kartu metrik modern responsif Flutter dengan Material Design 3 dan Riverpod state.",
        "target_language": "dart",
        "oracle_path": PROJECT_ROOT / "dokumentasi-pengembangan/experiments/frozen_oracle/flutter_t1",
        "expected_sha": "4589e15cfb8f37ba70642e70623ca143bceee1a44175aefd072f441d9e8a9528",
        "oracle_file": "card_metric_test.dart",
        "authoritative_file": "lib/card_metric.dart",
        "n_tests": 2,
        "keywords": ["kartu metrik", "card_metric", "flutter widget", "riverpod"]
    }
}

def resolve_preset_config(data: Dict[str, Any]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Mengidentifikasi preset misi dari task text, preset_id, atau oracle_path.
    Mengembalikan (preset_id, resolved_oracle_path, resolved_expected_sha).
    """
    preset_id = data.get("preset_id") or data.get("task_id")
    if preset_id and preset_id in PRESET_REGISTRY:
        p = PRESET_REGISTRY[preset_id]
        return preset_id, str(p["oracle_path"].resolve()), p["expected_sha"]

    task_text = (data.get("task") or "").strip().lower()
    raw_oracle = data.get("frozen_oracle_path") or CONFIG_STATE.get("frozen_oracle_path")

    # 1. Pencocokan via path
    if raw_oracle:
        for pid, p in PRESET_REGISTRY.items():
            if pid in str(raw_oracle).lower():
                return pid, str(p["oracle_path"].resolve()), p["expected_sha"]

    # 2. Pencocokan via teks task persis atau kata kunci
    for pid, p in PRESET_REGISTRY.items():
        if p["task"].strip().lower() == task_text:
            return pid, str(p["oracle_path"].resolve()), p["expected_sha"]
        if any(kw in task_text for kw in p["keywords"]):
            return pid, str(p["oracle_path"].resolve()), p["expected_sha"]

    # 3. Kustom path jika ada
    if raw_oracle and str(raw_oracle).strip():
        return None, str(Path(raw_oracle).resolve()), data.get("expected_oracle_sha")

    return None, None, None

def verify_oracle_checksum(oracle_dir_str: str, expected_sha: str, oracle_file: Optional[str] = None) -> Tuple[bool, str]:
    """Verifikasi checksum SHA-256 untuk frozen oracle."""
    oracle_dir = Path(oracle_dir_str)
    if not oracle_dir.exists():
        return False, "ORACLE_DIRECTORY_NOT_FOUND"

    candidates = [oracle_dir / oracle_file] if oracle_file else list(oracle_dir.glob("*.dart")) + list(oracle_dir.glob("*.py"))
    for f in candidates:
        if f.exists() and f.is_file():
            data = f.read_bytes()
            actual_sha = hashlib.sha256(data).hexdigest().lower()
            if actual_sha == expected_sha.lower():
                return True, actual_sha

    for f in oracle_dir.iterdir():
        if f.is_file():
            data = f.read_bytes()
            actual_sha = hashlib.sha256(data).hexdigest().lower()
            if actual_sha == expected_sha.lower():
                return True, actual_sha

    return False, "SHA_MISMATCH"

# ---------------------------------------------------------------------------
# REQ-012: WebSocket Hub & Connection Manager
# ---------------------------------------------------------------------------
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

    async def send_personal(self, websocket: WebSocket, message: Dict[str, Any]):
        try:
            await websocket.send_json(message)
        except Exception:
            self.disconnect(websocket)

manager = ConnectionManager()

# ---------------------------------------------------------------------------
# REQ-013: Event Helper Protocol
# ---------------------------------------------------------------------------
def make_event(event_type: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    event = {
        "event": event_type,
        "timestamp": datetime.now().isoformat(),
    }
    if payload:
        event.update(payload)
    return event

# ---------------------------------------------------------------------------
# Mapping Node StateGraph ke UI Agent Role
# ---------------------------------------------------------------------------
NODE_TO_UI_ROLE = {
    "pm": "pm",
    "pm_validator": "pm",
    "architect": "architect",
    "architect_validator": "architect",
    "developer": "developer",
    "developer_validator": "developer",
    "tester": "tester",
    "frozen_oracle": "tester",
    "test_suite_validator": "tester",
    "executor": "executor",
    "executor_validator": "executor",
    "reviewer": "reviewer",
    "reviewer_validator": "reviewer",
}

# ---------------------------------------------------------------------------
# REST Endpoints
# ---------------------------------------------------------------------------
@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "reindev_studio_backend",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/presets")
async def list_presets():
    """Mengembalikan daftar preset misi dengan metadata dan hash oracle terverifikasi."""
    presets_data = []
    for pid, p in PRESET_REGISTRY.items():
        presets_data.append({
            "preset_id": pid,
            "title": p["title"],
            "task": p["task"],
            "target_language": p["target_language"],
            "expected_sha": p["expected_sha"],
            "n_tests": p["n_tests"],
            "oracle_path": str(p["oracle_path"].resolve())
        })
    return {
        "status": "success",
        "presets": presets_data
    }

class ConfigUpdateRequest(BaseModel):
    provider: Optional[str] = None
    ollama_model: Optional[str] = None
    openrouter_model: Optional[str] = None
    max_iterations: Optional[int] = Field(None, ge=1, le=10)
    target_language: Optional[str] = None
    executor_intervention_enabled: Optional[bool] = None
    executor_mode: Optional[str] = None
    frozen_oracle_path: Optional[str] = None

@app.get("/api/config")
async def get_config():
    return {
        "status": "success",
        "config": CONFIG_STATE
    }

@app.post("/api/config")
async def update_config(req: ConfigUpdateRequest):
    if req.provider:
        CONFIG_STATE["provider"] = req.provider.lower()
    if req.ollama_model:
        CONFIG_STATE["ollama_model"] = req.ollama_model
    if req.openrouter_model:
        CONFIG_STATE["openrouter_model"] = req.openrouter_model
    if req.max_iterations is not None:
        CONFIG_STATE["max_iterations"] = req.max_iterations
    if req.target_language:
        CONFIG_STATE["target_language"] = req.target_language.lower()
    if req.executor_mode:
        m = req.executor_mode.upper()
        if m in ("SAFE", "ON", "OFF", "CODE_ONLY"):
            CONFIG_STATE["executor_mode"] = m
            CONFIG_STATE["executor_intervention_enabled"] = (m != "OFF")
    elif req.executor_intervention_enabled is not None:
        CONFIG_STATE["executor_intervention_enabled"] = req.executor_intervention_enabled
        CONFIG_STATE["executor_mode"] = "SAFE" if req.executor_intervention_enabled else "OFF"
    if req.frozen_oracle_path is not None:
        CONFIG_STATE["frozen_oracle_path"] = req.frozen_oracle_path if req.frozen_oracle_path != "" else None
    return {
        "status": "updated",
        "config": CONFIG_STATE
    }

@app.get("/api/projects")
async def list_projects():
    projects = []
    if OUTPUT_DIR.exists():
        for p in sorted(OUTPUT_DIR.iterdir(), key=lambda x: x.stat().st_mtime if x.exists() else 0, reverse=True):
            if p.is_dir():
                meta_file = p / "project_meta.json"
                meta_data = {}
                if meta_file.exists():
                    try:
                        meta_data = json.loads(meta_file.read_text(encoding="utf-8"))
                    except Exception:
                        pass
                file_count = sum(1 for f in p.rglob("*") if f.is_file() and f.name != "project_meta.json" and f.name != "run_trace.jsonl")
                projects.append({
                    "name": p.name,
                    "path": str(p.resolve()),
                    "file_count": file_count,
                    "status": meta_data.get("status", "unknown"),
                    "task": meta_data.get("task", ""),
                    "modified": datetime.fromtimestamp(p.stat().st_mtime).isoformat()
                })
    return {
        "status": "success",
        "projects": projects
    }

@app.get("/api/projects/{project_name}")
async def get_project_details(project_name: str):
    target = OUTPUT_DIR / project_name
    if not target.exists() or not target.is_dir():
        raise HTTPException(status_code=404, detail="Project not found")
    
    files = {}
    for f in target.rglob("*"):
        if f.is_file():
            rel_path = f.relative_to(target).as_posix()
            try:
                files[rel_path] = f.read_text(encoding="utf-8")
            except Exception:
                files[rel_path] = f"<binary or unreadable content: {f.stat().st_size} bytes>"
                
    return {
        "project": project_name,
        "path": str(target.resolve()),
        "files": files
    }

# ---------------------------------------------------------------------------
# REQ-012 & REQ-013: WebSocket Endpoint `/ws/squad`
# ---------------------------------------------------------------------------
@app.websocket("/ws/squad")
async def squad_websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    await manager.send_personal(websocket, make_event("connected", {
        "message": "Connected to ReinDev Studio Squad Engine WebSocket Hub (V1-V6 Validated)",
        "active_config": CONFIG_STATE,
        "available_presets": list(PRESET_REGISTRY.keys())
    }))
    
    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                data = json.loads(raw_data)
            except json.JSONDecodeError:
                await manager.send_personal(websocket, make_event("error", {"message": "Invalid JSON format"}))
                continue
                
            action = data.get("action")
            
            if action == "ping":
                await manager.send_personal(websocket, make_event("pong"))
                continue
                
            if action == "start_squad":
                task_text = data.get("task", "").strip()
                if not task_text:
                    await manager.send_personal(websocket, make_event("error", {"message": "Tugas (task) tidak boleh kosong."}))
                    continue
                    
                provider = data.get("provider", CONFIG_STATE["provider"])
                raw_model = data.get("model_name", CONFIG_STATE["ollama_model"])
                if "qwen2.5-coder:7b" in raw_model.lower():
                    model_name = "qwen2.5-coder:7b"
                else:
                    model_name = raw_model

                raw_lang = data.get("target_language", CONFIG_STATE["target_language"])
                if "dart" in raw_lang.lower() or "flutter" in raw_lang.lower():
                    target_lang = "dart"
                else:
                    target_lang = "python"

                max_iter = int(data.get("max_iterations", CONFIG_STATE["max_iterations"]))
                raw_mode = data.get("executor_mode")
                if raw_mode and raw_mode.upper() in ("SAFE", "ON", "OFF", "CODE_ONLY"):
                    executor_mode = raw_mode.upper()
                elif "executor_intervention_enabled" in data:
                    executor_mode = "SAFE" if data["executor_intervention_enabled"] else "OFF"
                else:
                    executor_mode = CONFIG_STATE.get("executor_mode", "SAFE").upper()
                executor_intervention_enabled = (executor_mode != "OFF")

                # Resolusi Preset & Frozen Oracle secara deterministik
                preset_id, resolved_oracle_path, resolved_expected_sha = resolve_preset_config(data)

                # Pre-Flight Verifikasi Integritas Frozen Oracle
                if resolved_oracle_path and resolved_expected_sha:
                    oracle_ok, act_sha = verify_oracle_checksum(resolved_oracle_path, resolved_expected_sha)
                    if not oracle_ok:
                        await manager.send_personal(websocket, make_event("error", {
                            "message": f"Pre-Flight Abort: Frozen Oracle SHA mismatch atau file tidak ditemukan! (Expected: {resolved_expected_sha[:16]}..., Result: {act_sha})"
                        }))
                        continue

                # Inisialisasi Sesi & Observability Tracer
                run_id = f"run_{preset_id or 'custom'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                proj_dir = OUTPUT_DIR / run_id
                proj_dir.mkdir(parents=True, exist_ok=True)
                tracer = RunTracer.register(run_id, proj_dir)

                # Inisialisasi State Squad Lengkap Sesuai Schema V1–V6
                initial_state: SquadState = {
                    "task": task_text,
                    "provider": provider,
                    "model_name": model_name,
                    "developer_backend": os.getenv("DEVELOPER_BACKEND", provider),
                    "developer_model": os.getenv("DEVELOPER_MODEL", model_name),
                    "squad_model": os.getenv("SQUAD_MODEL", model_name),
                    "target_language": target_lang,
                    "specifications": "",
                    "architecture_plan": "",
                    "contract": None,
                    "contract_status": None,
                    "contract_revision_count": 0,
                    "blueprint_revision_count": 0,
                    "max_iterations": max_iter,
                    "max_phase_repair_attempts": int(data.get("max_phase_repair_attempts", 2)),
                    "max_contract_revisions": 2,
                    "max_blueprint_revisions": 2,
                    "repair_attempt_counts": {},
                    "locked_invariants": {},
                    "oscillation_history": [],
                    "proven_semantic_interfaces": [],
                    "previous_passed_tests": [],
                    "code_files": {},
                    "test_files": {},
                    "test_results": {},
                    "iteration_count": 0,
                    "review_notes": "",
                    "status": "in_progress",
                    "logs": [],
                    "run_id": run_id,
                    "output_dir": str(proj_dir.resolve()),
                    "executor_intervention_enabled": executor_intervention_enabled,
                    "executor_mode": executor_mode,
                    "frozen_oracle_path": resolved_oracle_path,
                    "expected_oracle_sha": resolved_expected_sha
                }
                
                # Observability Trace: Event 1 (RUN_START)
                tracer.log_event(
                    stage="run_lifecycle",
                    event_type="run_start",
                    iteration=0,
                    data={
                        "run_id": run_id,
                        "task": task_text,
                        "preset_id": preset_id,
                        "target_language": target_lang,
                        "provider": provider,
                        "model": model_name,
                        "max_iterations": max_iter,
                        "executor_intervention_enabled": executor_intervention_enabled,
                        "executor_mode": executor_mode,
                        "frozen_oracle_path": resolved_oracle_path,
                        "expected_oracle_sha": resolved_expected_sha,
                        "output_directory": str(proj_dir.resolve()),
                        "config": {
                            "ollama_host": CONFIG_STATE.get("ollama_host"),
                            "system_platform": sys.platform
                        }
                    }
                )

                start_time = time.time()
                await manager.send_personal(websocket, make_event("session_start", {
                    "run_id": run_id,
                    "task": task_text,
                    "preset_id": preset_id,
                    "provider": provider,
                    "model_name": model_name,
                    "target_language": target_lang,
                    "max_iterations": max_iter,
                    "executor_intervention_enabled": executor_intervention_enabled,
                    "executor_mode": executor_mode,
                    "frozen_oracle_path": resolved_oracle_path
                }))
                
                loop = asyncio.get_event_loop()
                
                role_info = {
                    "pm": ("Product Manager", "thinking", f"Product Manager menganalisis spesifikasi misi ({target_lang.upper()})..."),
                    "pm_validator": ("PM Validator", "testing", "Memvalidasi kelengkapan spesifikasi dan kriteria penerimaan (Boundary V1)..."),
                    "architect": ("System Architect", "thinking", f"System Architect merancang arsitektur modul dan file tree ({target_lang.upper()})..."),
                    "architect_validator": ("Architect Validator", "testing", "Memvalidasi dan membekukan Interface Contract (Boundary V2)..."),
                    "developer": ("Developer", "working", f"Developer menyintesis kode sumber produksi bersih ({target_lang.upper()})..."),
                    "developer_validator": ("Developer Validator", "testing", "Memvalidasi sintaksis AST dan integritas kode sebelum eksekusi (Boundary V3)..."),
                    "tester": ("QA Tester", "testing", f"QA Tester menyusun automated test suite ({target_lang.upper()})..."),
                    "frozen_oracle": ("Frozen Oracle", "testing", "Memuat frozen oracle test suite komprehensif..."),
                    "test_suite_validator": ("Test Suite Validator", "testing", "Memvalidasi integritas test suite (Boundary V4)..."),
                    "executor": ("Sandbox Executor", "testing", "Mengeksekusi test runner dalam sandbox isolasi..."),
                    "executor_validator": ("Behavioral Validator", "testing", "Mengevaluasi hasil eksekusi, regresi invarian, dan kestabilan (Boundary V5)..."),
                    "reviewer": ("Code Reviewer", "reviewing", f"Code Reviewer mengaudit kode dan arsitektur ({target_lang.upper()})..."),
                    "reviewer_validator": ("Reviewer Validator", "reviewing", "Memvalidasi konsistensi keputusan reviewer terhadap bukti Layer 1 (Boundary V6)..."),
                }
                
                try:
                    stream_generator = squad_graph.stream(initial_state)
                    
                    def get_next(gen):
                        try:
                            return next(gen), False
                        except StopIteration:
                            return None, True

                    accumulated_state = initial_state.copy()
                    next_node_to_announce = "pm"
                    
                    while True:
                        # 0. Notifikasi awal sebelum LLM / Validator mulai bekerja
                        if next_node_to_announce and next_node_to_announce in role_info:
                            r_name, r_status, r_desc = role_info[next_node_to_announce]
                            ui_role = NODE_TO_UI_ROLE.get(next_node_to_announce, next_node_to_announce)
                            await manager.send_personal(websocket, make_event("agent_state", {
                                "node": ui_role,
                                "raw_node": next_node_to_announce,
                                "status": r_status,
                                "iteration": accumulated_state.get("iteration_count", 0),
                                "log": f"[{r_name}]: {r_desc}"
                            }))
                            
                        future = loop.run_in_executor(None, get_next, stream_generator)
                        
                        # Heartbeat loop tiap 2.5 detik selama inferensi berlangsung
                        while not future.done():
                            try:
                                await asyncio.wait_for(asyncio.shield(future), timeout=2.5)
                            except asyncio.TimeoutError:
                                elapsed = round(time.time() - start_time, 1)
                                ui_role = NODE_TO_UI_ROLE.get(next_node_to_announce, "pm")
                                cur_role = role_info.get(next_node_to_announce, ("Squad",))[0]
                                await manager.send_personal(websocket, make_event("agent_heartbeat", {
                                    "node": ui_role,
                                    "raw_node": next_node_to_announce,
                                    "elapsed_sec": elapsed,
                                    "message": f"{cur_role} aktif memproses ({elapsed}s)..."
                                }))
                                
                        step_result, is_done = future.result()
                        if is_done or not step_result:
                            break
                            
                        for node_name, node_output in step_result.items():
                            accumulated_state.update(node_output)
                            ui_role = NODE_TO_UI_ROLE.get(node_name, node_name)
                            last_log = node_output.get("logs", [""])[-1] if node_output.get("logs") else ""
                            
                            # 1. Penanganan Spesifik Setiap Node & Boundary
                            if node_name == "pm" and "specifications" in node_output:
                                tracer.log_event(
                                    stage="pm",
                                    event_type="output",
                                    iteration=0,
                                    data={
                                        "input_task": task_text,
                                        "target_language": target_lang,
                                        "specifications": node_output["specifications"],
                                        "specifications_sha256": compute_sha256(node_output["specifications"]),
                                        "iteration": 0
                                    }
                                )
                                await manager.send_personal(websocket, make_event("agent_thought", {
                                    "agent": "pm",
                                    "thought": node_output["specifications"]
                                }))
                                await manager.send_personal(websocket, make_event("agent_state", {
                                    "node": "pm",
                                    "status": "completed",
                                    "iteration": accumulated_state.get("iteration_count", 0),
                                    "log": "[Product Manager]: Spesifikasi misi berhasil disusun."
                                }))
                                next_node_to_announce = "pm_validator"

                            elif node_name == "pm_validator":
                                contract = node_output.get("pm_validator_contract", {})
                                verdict = contract.get("verdict", "FAIL")
                                repair_count = accumulated_state.get("repair_attempt_counts", {}).get("pm", 0)
                                max_repairs = accumulated_state.get("max_phase_repair_attempts", 2)
                                violations = contract.get("violations", [])

                                await manager.send_personal(websocket, make_event("phase_validation", {
                                    "phase": "PM",
                                    "boundary": "V1",
                                    "verdict": verdict,
                                    "repair_count": repair_count,
                                    "max_repairs": max_repairs,
                                    "violations": violations
                                }))

                                if verdict == "PASS":
                                    await manager.send_personal(websocket, make_event("agent_state", {
                                        "node": "pm",
                                        "status": "completed",
                                        "iteration": accumulated_state.get("iteration_count", 0),
                                        "log": "[PM Validator]: Spesifikasi misi lolos validasi Boundary V1."
                                    }))
                                    next_node_to_announce = "architect"
                                else:
                                    st = "retrying" if repair_count <= max_repairs else "error"
                                    await manager.send_personal(websocket, make_event("agent_state", {
                                        "node": "pm",
                                        "status": st,
                                        "iteration": accumulated_state.get("iteration_count", 0),
                                        "log": f"[PM Validator]: Validasi Boundary V1 GAGAL ({len(violations)} pelanggaran). Repair {repair_count}/{max_repairs}."
                                    }))
                                    next_node_to_announce = "pm" if repair_count <= max_repairs else None

                            elif node_name == "architect" and "architecture_plan" in node_output:
                                tracer.log_event(
                                    stage="architect",
                                    event_type="output",
                                    iteration=0,
                                    data={
                                        "input_task": task_text,
                                        "input_specifications": accumulated_state.get("specifications", ""),
                                        "target_language": target_lang,
                                        "architecture_plan": node_output["architecture_plan"],
                                        "architecture_plan_sha256": compute_sha256(node_output["architecture_plan"]),
                                        "iteration": 0
                                    }
                                )
                                await manager.send_personal(websocket, make_event("agent_thought", {
                                    "agent": "architect",
                                    "thought": node_output["architecture_plan"]
                                }))
                                await manager.send_personal(websocket, make_event("agent_state", {
                                    "node": "architect",
                                    "status": "completed",
                                    "iteration": accumulated_state.get("iteration_count", 0),
                                    "log": "[System Architect]: Rencana arsitektur dan blueprint modul berhasil dirancang."
                                }))
                                next_node_to_announce = "architect_validator"

                            elif node_name == "architect_validator":
                                contract = node_output.get("architect_validator_contract", {})
                                verdict = contract.get("verdict", "FAIL")
                                c_status = accumulated_state.get("contract_status", "UNKNOWN")
                                seal = accumulated_state.get("contract_sha256", "")
                                repair_count = accumulated_state.get("repair_attempt_counts", {}).get("architect", 0)
                                max_repairs = accumulated_state.get("max_phase_repair_attempts", 2)
                                violations = contract.get("violations", [])

                                await manager.send_personal(websocket, make_event("phase_validation", {
                                    "phase": "ARCHITECT",
                                    "boundary": "V2",
                                    "verdict": verdict,
                                    "contract_status": c_status,
                                    "contract_sha256": seal,
                                    "repair_count": repair_count,
                                    "max_repairs": max_repairs,
                                    "violations": violations
                                }))

                                if verdict == "PASS":
                                    await manager.send_personal(websocket, make_event("agent_state", {
                                        "node": "architect",
                                        "status": "completed",
                                        "iteration": accumulated_state.get("iteration_count", 0),
                                        "log": f"[Architect Validator]: Interface Contract FROZEN (Boundary V2 PASS, SHA: {seal[:16]}...). Zero leakage dipastikan."
                                    }))
                                    next_node_to_announce = "developer"
                                else:
                                    st = "retrying" if repair_count <= max_repairs else "error"
                                    await manager.send_personal(websocket, make_event("agent_state", {
                                        "node": "architect",
                                        "status": st,
                                        "iteration": accumulated_state.get("iteration_count", 0),
                                        "log": f"[Architect Validator]: Validasi Boundary V2 GAGAL. Repair {repair_count}/{max_repairs}."
                                    }))
                                    next_node_to_announce = "architect" if repair_count <= max_repairs else None

                            elif node_name == "developer" and "code_files" in node_output:
                                cur_iter = accumulated_state.get("iteration_count", 0)
                                code_files = node_output["code_files"]
                                await manager.send_personal(websocket, make_event("code_update", {
                                    "agent": "developer",
                                    "files": code_files,
                                    "iteration": cur_iter
                                }))
                                await manager.send_personal(websocket, make_event("agent_state", {
                                    "node": "developer",
                                    "status": "completed",
                                    "iteration": cur_iter,
                                    "log": f"[Developer]: Sintesis {len(code_files)} berkas kode sumber selesai."
                                }))
                                next_node_to_announce = "developer_validator"

                            elif node_name == "developer_validator":
                                contract = node_output.get("developer_validator_contract", {})
                                verdict = contract.get("verdict", "FAIL")
                                repair_count = accumulated_state.get("repair_attempt_counts", {}).get("developer", 0)
                                max_repairs = accumulated_state.get("max_phase_repair_attempts", 2)
                                violations = contract.get("violations", [])

                                await manager.send_personal(websocket, make_event("phase_validation", {
                                    "phase": "DEVELOPER",
                                    "boundary": "V3",
                                    "verdict": verdict,
                                    "repair_count": repair_count,
                                    "max_repairs": max_repairs,
                                    "violations": violations
                                }))

                                if verdict == "PASS":
                                    await manager.send_personal(websocket, make_event("agent_state", {
                                        "node": "developer",
                                        "status": "completed",
                                        "iteration": accumulated_state.get("iteration_count", 0),
                                        "log": "[Developer Validator]: Pra-eksekusi AST lolos validasi Boundary V3."
                                    }))
                                    next_node_to_announce = "frozen_oracle" if accumulated_state.get("frozen_oracle_path") else "tester"
                                else:
                                    st = "retrying" if repair_count <= max_repairs else "error"
                                    await manager.send_personal(websocket, make_event("agent_state", {
                                        "node": "developer",
                                        "status": st,
                                        "iteration": accumulated_state.get("iteration_count", 0),
                                        "log": f"[Developer Validator]: Pra-eksekusi GAGAL Boundary V3 ({len(violations)} isu). Repair {repair_count}/{max_repairs}."
                                    }))
                                    next_node_to_announce = "developer" if repair_count <= max_repairs else None

                            elif node_name == "frozen_oracle" and "test_files" in node_output:
                                test_files = node_output["test_files"]
                                await manager.send_personal(websocket, make_event("code_update", {
                                    "agent": "frozen_oracle",
                                    "files": test_files
                                }))
                                await manager.send_personal(websocket, make_event("agent_state", {
                                    "node": "tester",
                                    "status": "completed",
                                    "iteration": accumulated_state.get("iteration_count", 0),
                                    "log": f"[Frozen Oracle]: Berhasil memuat {len(test_files)} berkas test suite immutable."
                                }))
                                next_node_to_announce = "test_suite_validator"

                            elif node_name == "tester" and "test_files" in node_output:
                                test_files = node_output["test_files"]
                                await manager.send_personal(websocket, make_event("code_update", {
                                    "agent": "tester",
                                    "files": test_files
                                }))
                                await manager.send_personal(websocket, make_event("agent_state", {
                                    "node": "tester",
                                    "status": "completed",
                                    "iteration": accumulated_state.get("iteration_count", 0),
                                    "log": f"[QA Tester]: Berhasil menyusun {len(test_files)} berkas automated test suite."
                                }))
                                next_node_to_announce = "test_suite_validator"

                            elif node_name == "test_suite_validator":
                                contract = node_output.get("test_suite_validator_contract", {})
                                verdict = contract.get("verdict", "FAIL")
                                violations = contract.get("violations", [])
                                use_frozen = bool(accumulated_state.get("frozen_oracle_path"))

                                await manager.send_personal(websocket, make_event("phase_validation", {
                                    "phase": "TEST_SUITE",
                                    "boundary": "V4",
                                    "verdict": verdict,
                                    "use_frozen": use_frozen,
                                    "violations": violations
                                }))

                                if verdict == "PASS":
                                    await manager.send_personal(websocket, make_event("agent_state", {
                                        "node": "tester",
                                        "status": "completed",
                                        "iteration": accumulated_state.get("iteration_count", 0),
                                        "log": "[Test Suite Validator]: Integritas test suite lolos validasi Boundary V4."
                                    }))
                                    next_node_to_announce = "executor"
                                else:
                                    await manager.send_personal(websocket, make_event("agent_state", {
                                        "node": "tester",
                                        "status": "error",
                                        "iteration": accumulated_state.get("iteration_count", 0),
                                        "log": "[Test Suite Validator]: Integritas test suite GAGAL Boundary V4. Zero downstream leakage dipicu."
                                    }))
                                    next_node_to_announce = None

                            elif node_name == "executor" and "test_results" in node_output:
                                cur_iter = accumulated_state.get("iteration_count", 0)
                                test_res = node_output["test_results"]
                                await manager.send_personal(websocket, make_event("test_log", {
                                    "results": test_res,
                                    "iteration": cur_iter,
                                    "max_iterations": max_iter
                                }))
                                await manager.send_personal(websocket, make_event("agent_state", {
                                    "node": "executor",
                                    "status": "completed",
                                    "iteration": cur_iter,
                                    "log": f"[Sandbox Executor]: Eksekusi isolasi selesai (passed={test_res.get('passed', False)})."
                                }))
                                next_node_to_announce = "executor_validator"

                            elif node_name == "executor_validator":
                                contract = node_output.get("executor_iteration_validator_contract", {})
                                verdict = contract.get("verdict", "FAIL")
                                test_res = accumulated_state.get("test_results", {})
                                is_passed = bool(test_res.get("passed", False))
                                cur_iter = accumulated_state.get("iteration_count", 0)
                                repair_count = accumulated_state.get("repair_attempt_counts", {}).get("executor", 0)
                                max_repairs = accumulated_state.get("max_phase_repair_attempts", 2)
                                locked_invs = accumulated_state.get("locked_invariants", {})
                                regressions = contract.get("regressions", [])

                                await manager.send_personal(websocket, make_event("phase_validation", {
                                    "phase": "EXECUTOR",
                                    "boundary": "V5",
                                    "verdict": verdict,
                                    "repair_count": repair_count,
                                    "max_repairs": max_repairs,
                                    "regressions": regressions,
                                    "locked_invariants_count": len(locked_invs)
                                }))

                                if verdict == "PASS" and is_passed:
                                    loop_status = "passed"
                                    loop_msg = f"Pengujian Sandbox Lolos Bersih (Loop {cur_iter}/{max_iter}). Melanjutkan ke Code Reviewer untuk sertifikasi rilis."
                                    next_node = "reviewer"
                                elif repair_count <= max_repairs:
                                    loop_status = "retrying"
                                    c_owner = (accumulated_state.get("causal_owner_phase") or "developer").lower()
                                    loop_msg = f"Self-Healing Loop {cur_iter}/{max_iter} (Repair {repair_count}/{max_repairs}): Pengujian belum lolos ({len(regressions)} regresi, {len(locked_invs)} invarian terkunci). Mengarahkan perbaikan ke {c_owner.capitalize()}..."
                                    next_node = c_owner
                                else:
                                    loop_status = "max_reached"
                                    loop_msg = f"Batas Maksimum Self-Healing Tercapai (Repair {repair_count}/{max_repairs}). ZERO LEAKAGE: Eksekusi dihentikan aman."
                                    next_node = None

                                await manager.send_personal(websocket, make_event("loop_status", {
                                    "current_loop": cur_iter,
                                    "max_loops": max_iter,
                                    "status": loop_status,
                                    "message": loop_msg
                                }))
                                await manager.send_personal(websocket, make_event("agent_state", {
                                    "node": "executor",
                                    "status": "completed" if loop_status == "passed" else ("retrying" if loop_status == "retrying" else "error"),
                                    "iteration": cur_iter,
                                    "log": loop_msg
                                }))
                                next_node_to_announce = next_node

                            elif node_name == "reviewer" and "review_notes" in node_output:
                                rev_notes = node_output["review_notes"]
                                await manager.send_personal(websocket, make_event("agent_state", {
                                    "node": "reviewer",
                                    "status": "completed",
                                    "iteration": accumulated_state.get("iteration_count", 0),
                                    "log": "[Code Reviewer]: Audit Sound Null Safety dan integritas arsitektur selesai."
                                }))
                                next_node_to_announce = "reviewer_validator"

                            elif node_name == "reviewer_validator":
                                contract = node_output.get("reviewer_validator_contract", {})
                                verdict = contract.get("verdict", "FAIL")
                                rev_verdict = accumulated_state.get("review_verdict", "FAIL")
                                is_approved = (rev_verdict == "APPROVED" and verdict == "PASS")
                                status_str = "approved" if is_approved else "needs_revision"

                                await manager.send_personal(websocket, make_event("review_report", {
                                    "report": accumulated_state.get("review_notes", ""),
                                    "status": status_str,
                                    "is_approved": is_approved,
                                    "iteration": accumulated_state.get("iteration_count", 0),
                                    "max_iterations": max_iter
                                }))
                                await manager.send_personal(websocket, make_event("phase_validation", {
                                    "phase": "REVIEWER",
                                    "boundary": "V6",
                                    "verdict": verdict,
                                    "evaluated_review_verdict": rev_verdict,
                                    "is_approved": is_approved
                                }))
                                await manager.send_personal(websocket, make_event("agent_state", {
                                    "node": "reviewer",
                                    "status": "completed" if is_approved else "retrying",
                                    "iteration": accumulated_state.get("iteration_count", 0),
                                    "log": f"[Reviewer Validator]: Boundary V6 verdict = {verdict}, review decision = {rev_verdict}."
                                }))
                                
                                if not is_approved and contract.get("repair_owner") == "DEVELOPER" and accumulated_state.get("repair_attempt_counts", {}).get("developer", 0) < accumulated_state.get("max_phase_repair_attempts", 2):
                                    next_node_to_announce = "developer"
                                else:
                                    next_node_to_announce = None
                                
                    duration = round(time.time() - start_time, 2)
                    
                    # Simpan hasil output proyek ke direktori backend/output/
                    proj_slug = run_id
                    proj_dir.mkdir(parents=True, exist_ok=True)
                    
                    all_files = {}
                    all_files.update(accumulated_state.get("code_files", {}))
                    all_files.update(accumulated_state.get("test_files", {}))
                    
                    for fname, content in all_files.items():
                        fpath = proj_dir / fname
                        fpath.parent.mkdir(parents=True, exist_ok=True)
                        fpath.write_text(content, encoding="utf-8")
                        
                    # Evaluasi status final misi secara objektif dan non-kontradiktif (Doktrin #6)
                    test_res = accumulated_state.get("test_results", {})
                    is_test_passed = bool(test_res.get("passed", False))
                    final_rev_notes = accumulated_state.get("review_notes", "")
                    contract_status = accumulated_state.get("contract_status")
                    review_verdict = accumulated_state.get("review_verdict", "FAIL")
                    rev_contract = accumulated_state.get("reviewer_validator_contract", {})
                    is_reviewer_validated = (rev_contract.get("verdict") == "PASS")
                    status_field = accumulated_state.get("status", "")

                    is_final_approved = (
                        is_test_passed
                        and contract_status == "FROZEN"
                        and review_verdict == "APPROVED"
                        and is_reviewer_validated
                    )
                    
                    if is_final_approved:
                        final_status = "completed"
                    elif "terminal_failure" in status_field:
                        final_status = status_field
                    elif not is_test_passed:
                        final_status = "tests_failed"
                    elif review_verdict != "APPROVED":
                        final_status = "needs_revision"
                    else:
                        final_status = "failed"
                        
                    # Simpan metadata proyek komprehensif
                    meta = {
                        "run_id": run_id,
                        "task": task_text,
                        "preset_id": preset_id,
                        "target_language": target_lang,
                        "duration_sec": duration,
                        "iterations": accumulated_state.get("iteration_count", 0),
                        "status": final_status,
                        "tests_passed": is_test_passed,
                        "is_approved": is_final_approved,
                        "contract_status": contract_status,
                        "review_verdict": review_verdict,
                        "locked_invariants": accumulated_state.get("locked_invariants", {}),
                        "repair_attempt_counts": accumulated_state.get("repair_attempt_counts", {}),
                        "executor_intervention_enabled": executor_intervention_enabled,
                        "executor_mode": executor_mode,
                        "frozen_oracle_path": resolved_oracle_path,
                        "expected_oracle_sha": resolved_expected_sha,
                        "timestamp": datetime.now().isoformat()
                    }
                    (proj_dir / "project_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

                    # Observability Trace: Event 9 (RUN_END)
                    tracer.log_event(
                        stage="run_lifecycle",
                        event_type="run_end",
                        iteration=accumulated_state.get("iteration_count", 0),
                        data={
                            "run_id": run_id,
                            "final_status": final_status,
                            "final_iteration": accumulated_state.get("iteration_count", 0),
                            "max_iterations": max_iter,
                            "tests_passed": is_test_passed,
                            "is_approved": is_final_approved,
                            "contract_status": contract_status,
                            "review_verdict": review_verdict,
                            "locked_invariants": accumulated_state.get("locked_invariants", {}),
                            "repair_attempt_counts": accumulated_state.get("repair_attempt_counts", {}),
                            "executor_intervention_enabled": executor_intervention_enabled,
                            "executor_mode": executor_mode,
                            "frozen_oracle_path": resolved_oracle_path,
                            "expected_oracle_sha": resolved_expected_sha,
                            "total_duration_sec": duration,
                            "final_files": list(all_files.keys()),
                            "final_files_hashes": compute_dict_hashes(all_files)
                        }
                    )
                    
                    # Kirim event Complete dengan status objektif
                    await manager.send_personal(websocket, make_event("complete", {
                        "status": final_status,
                        "duration_sec": duration,
                        "iterations": accumulated_state.get("iteration_count", 0),
                        "max_iterations": max_iter,
                        "project_name": proj_slug,
                        "project_dir": str(proj_dir.resolve()),
                        "files": all_files,
                        "files_generated": list(all_files.keys()),
                        "test_results": accumulated_state.get("test_results", {}),
                        "review_notes": final_rev_notes,
                        "tests_passed": is_test_passed,
                        "is_approved": is_final_approved,
                        "contract_status": contract_status,
                        "review_verdict": review_verdict,
                        "locked_invariants": accumulated_state.get("locked_invariants", {}),
                        "repair_attempt_counts": accumulated_state.get("repair_attempt_counts", {})
                    }))
                    
                except Exception as e:
                    await manager.send_personal(websocket, make_event("error", {
                        "message": f"Pipeline Execution Error: {str(e)}"
                    }))
            else:
                await manager.send_personal(websocket, make_event("error", {
                    "message": f"Aksi '{action}' tidak dikenali."
                }))
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
    finally:
        manager.disconnect(websocket)

# ---------------------------------------------------------------------------
# Frontend Web Mount: Serve Flutter Web UI at `/`
# ---------------------------------------------------------------------------
from fastapi.staticfiles import StaticFiles

WEB_DIR = PROJECT_ROOT / "frontend" / "build" / "web"
if WEB_DIR.exists() and (WEB_DIR / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web_ui")

