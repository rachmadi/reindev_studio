import os
import sys
import time
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Ensure root path is accessible
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.state import SquadState
from backend.graph import squad_graph
from backend.tracer import RunTracer, get_tracer, compute_sha256, compute_dict_hashes

app = FastAPI(
    title="ReinDev Studio Backend API",
    description="Autonomous Multi-Agent Software Engineering Studio Engine (FastAPI + LangGraph)",
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
    "executor_mode": "ON",
    "frozen_oracle_path": None,
}

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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
def make_event(event_type: str, payload: Dict[str, Any] = None) -> Dict[str, Any]:
    event = {
        "event": event_type,
        "timestamp": datetime.now().isoformat(),
    }
    if payload:
        event.update(payload)
    return event

# ---------------------------------------------------------------------------
# REQ-011: REST Endpoint Health Check
# ---------------------------------------------------------------------------
@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "reindev_studio_backend",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

# ---------------------------------------------------------------------------
# REQ-014: REST Endpoints Configuration & Projects
# ---------------------------------------------------------------------------
class ConfigUpdateRequest(BaseModel):
    provider: Optional[str] = None
    ollama_model: Optional[str] = None
    openrouter_model: Optional[str] = None
    max_iterations: Optional[int] = Field(None, ge=1, le=5)
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
        if m in ("ON", "OFF", "CODE_ONLY"):
            CONFIG_STATE["executor_mode"] = m
            CONFIG_STATE["executor_intervention_enabled"] = (m != "OFF")
    elif req.executor_intervention_enabled is not None:
        CONFIG_STATE["executor_intervention_enabled"] = req.executor_intervention_enabled
        CONFIG_STATE["executor_mode"] = "ON" if req.executor_intervention_enabled else "OFF"
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
        for p in OUTPUT_DIR.iterdir():
            if p.is_dir():
                file_count = sum(1 for f in p.rglob("*") if f.is_file())
                projects.append({
                    "name": p.name,
                    "path": str(p.resolve()),
                    "file_count": file_count,
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
        "message": "Connected to ReinDev Studio Squad Engine WebSocket Hub",
        "active_config": CONFIG_STATE
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
                target_lang = data.get("target_language", CONFIG_STATE["target_language"])
                max_iter = data.get("max_iterations", CONFIG_STATE["max_iterations"])
                raw_mode = data.get("executor_mode")
                if raw_mode and raw_mode.upper() in ("ON", "OFF", "CODE_ONLY"):
                    executor_mode = raw_mode.upper()
                elif "executor_intervention_enabled" in data:
                    executor_mode = "ON" if data["executor_intervention_enabled"] else "OFF"
                else:
                    executor_mode = CONFIG_STATE.get("executor_mode", "ON").upper()
                executor_intervention_enabled = (executor_mode != "OFF")
                frozen_oracle_path = data.get("frozen_oracle_path", CONFIG_STATE.get("frozen_oracle_path", None))
                if frozen_oracle_path == "":
                    frozen_oracle_path = None
                
                # Inisialisasi Sesi & Observability Tracer
                run_id = "project_" + datetime.now().strftime("%Y%m%d_%H%M%S")
                proj_dir = OUTPUT_DIR / run_id
                proj_dir.mkdir(parents=True, exist_ok=True)
                tracer = RunTracer.register(run_id, proj_dir)

                # Inisialisasi State Squad
                initial_state: SquadState = {
                    "task": task_text,
                    "provider": provider,
                    "model_name": model_name,
                    "target_language": target_lang,
                    "specifications": "",
                    "architecture_plan": "",
                    "code_files": {},
                    "test_files": {},
                    "test_results": {},
                    "iteration_count": 0,
                    "max_iterations": max_iter,
                    "review_notes": "",
                    "status": "in_progress",
                    "logs": [],
                    "run_id": run_id,
                    "output_dir": str(proj_dir.resolve()),
                    "executor_intervention_enabled": executor_intervention_enabled,
                    "executor_mode": executor_mode,
                    "frozen_oracle_path": frozen_oracle_path
                }
                
                # Observability Trace: Event 1 (RUN_START)
                tracer.log_event(
                    stage="run_lifecycle",
                    event_type="run_start",
                    iteration=0,
                    data={
                        "run_id": run_id,
                        "task": task_text,
                        "target_language": target_lang,
                        "provider": provider,
                        "model": model_name,
                        "max_iterations": max_iter,
                        "executor_intervention_enabled": executor_intervention_enabled,
                        "executor_mode": executor_mode,
                        "frozen_oracle_path": frozen_oracle_path,
                        "output_directory": str(proj_dir.resolve()),
                        "config": {
                            "ollama_host": CONFIG_STATE.get("ollama_host"),
                            "system_platform": sys.platform
                        }
                    }
                )

                start_time = time.time()
                await manager.send_personal(websocket, make_event("session_start", {
                    "task": task_text,
                    "provider": provider,
                    "model_name": model_name,
                    "target_language": target_lang,
                    "max_iterations": max_iter,
                    "executor_intervention_enabled": executor_intervention_enabled,
                    "executor_mode": executor_mode,
                    "frozen_oracle_path": frozen_oracle_path
                }))
                
                # Eksekusi StateGraph secara asynchronous dan broadcast tiap transisi node
                loop = asyncio.get_event_loop()
                
                role_info = {
                    "pm": ("Product Manager", "thinking", f"Product Manager menganalisis spesifikasi misi ({target_lang.upper()})..."),
                    "architect": ("System Architect", "thinking", f"System Architect merancang arsitektur modul dan file tree ({target_lang.upper()})..."),
                    "developer": ("Developer", "working", f"Developer menyintesis kode sumber produksi bersih ({target_lang.upper()})..."),
                    "tester": ("QA Tester", "testing", f"QA Tester menyusun automated test suite komprehensif ({target_lang.upper()})..."),
                    "frozen_oracle": ("Frozen Oracle", "testing", "Memuat frozen oracle test suite komprehensif..."),
                    "executor": ("QA Tester", "testing", "Mengeksekusi test runner dalam sandbox isolasi..."),
                    "reviewer": ("Code Reviewer", "reviewing", f"Code Reviewer mengaudit Sound Null Safety & arsitektur ({target_lang.upper()})..."),
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
                        # 0. Notifikasi awal sebelum LLM mulai berpikir agar UI langsung aktif berdenyut
                        if next_node_to_announce and next_node_to_announce in role_info:
                            r_name, r_status, r_desc = role_info[next_node_to_announce]
                            await manager.send_personal(websocket, make_event("agent_state", {
                                "node": next_node_to_announce,
                                "status": r_status,
                                "iteration": accumulated_state.get("iteration_count", 0),
                                "log": f"[{r_name}]: {r_desc}"
                            }))
                            
                        future = loop.run_in_executor(None, get_next, stream_generator)
                        
                        # Heartbeat loop tiap 2.5 detik selama LLM menghasilkan respon
                        while not future.done():
                            try:
                                await asyncio.wait_for(asyncio.shield(future), timeout=2.5)
                            except asyncio.TimeoutError:
                                elapsed = round(time.time() - start_time, 1)
                                cur_role = role_info.get(next_node_to_announce, ("Squad",))[0]
                                await manager.send_personal(websocket, make_event("agent_heartbeat", {
                                    "node": next_node_to_announce,
                                    "elapsed_sec": elapsed,
                                    "message": f"{cur_role} aktif memproses respon inferensi ({elapsed}s)..."
                                }))
                                
                        step_result, is_done = future.result()
                        if is_done or not step_result:
                            break
                            
                        for node_name, node_output in step_result.items():
                            accumulated_state.update(node_output)
                            last_log = node_output.get("logs", [""])[-1] if node_output.get("logs") else ""
                            
                            # 1. Notifikasi Agent Selesai / Completed
                            await manager.send_personal(websocket, make_event("agent_state", {
                                "node": node_name,
                                "status": "completed",
                                "iteration": accumulated_state.get("iteration_count", 0),
                                "log": last_log
                            }))
                            
                            # 2. Spesifik Event berdasarkan Node
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
                                next_node_to_announce = "architect"
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
                                next_node_to_announce = "developer"
                            elif node_name == "developer" and "code_files" in node_output:
                                cur_iter = accumulated_state.get("iteration_count", 0)
                                has_tests = bool(accumulated_state.get("test_files"))
                                await manager.send_personal(websocket, make_event("code_update", {
                                    "agent": "developer",
                                    "files": node_output["code_files"],
                                    "iteration": cur_iter
                                }))
                                if cur_iter > 0 and has_tests and not accumulated_state.get("tests_need_update", False):
                                    next_node_to_announce = "executor"
                                elif accumulated_state.get("frozen_oracle_path"):
                                    next_node_to_announce = "frozen_oracle"
                                else:
                                    next_node_to_announce = "tester"
                            elif node_name == "frozen_oracle" and "test_files" in node_output:
                                await manager.send_personal(websocket, make_event("code_update", {
                                    "agent": "frozen_oracle",
                                    "files": node_output["test_files"]
                                }))
                                next_node_to_announce = "executor"
                            elif node_name == "tester" and "test_files" in node_output:
                                await manager.send_personal(websocket, make_event("code_update", {
                                    "agent": "tester",
                                    "files": node_output["test_files"]
                                }))
                                next_node_to_announce = "executor"
                            elif node_name == "executor" and "test_results" in node_output:
                                cur_iter = node_output.get("iteration_count", 0)
                                test_res = node_output["test_results"]
                                is_passed = test_res.get("passed", False)
                                
                                await manager.send_personal(websocket, make_event("test_log", {
                                    "results": test_res,
                                    "iteration": cur_iter,
                                    "max_iterations": max_iter
                                }))
                                
                                if not is_passed and cur_iter < max_iter:
                                    next_node_to_announce = "developer"
                                    loop_status = "retrying"
                                    loop_msg = f"Self-Healing Loop {cur_iter}/{max_iter}: Pengujian gagal. Melempar tugas kembali ke Developer untuk perbaikan kode..."
                                elif not is_passed and cur_iter >= max_iter:
                                    next_node_to_announce = "reviewer"
                                    loop_status = "max_reached"
                                    loop_msg = f"Batas Maksimum Self-Healing Tercapai ({cur_iter}/{max_iter} Loop). QA Tester mengalihkan tugas ke Code Reviewer untuk audit kegagalan dan penyajian bukti."
                                else:
                                    next_node_to_announce = "reviewer"
                                    loop_status = "passed"
                                    loop_msg = f"Pengujian Sandbox Lolos Bersih (Loop {cur_iter}/{max_iter}). Melanjutkan ke Code Reviewer untuk sertifikasi rilis."
                                    
                                await manager.send_personal(websocket, make_event("loop_status", {
                                    "current_loop": cur_iter,
                                    "max_loops": max_iter,
                                    "status": loop_status,
                                    "message": loop_msg
                                }))
                            elif node_name == "reviewer" and "review_notes" in node_output:
                                rev_notes = node_output["review_notes"]
                                is_rev_approved = "[APPROVED]" in rev_notes and "[NEEDS_REVISION]" not in rev_notes
                                rev_status = node_output.get("status", "approved" if is_rev_approved else "needs_revision")
                                await manager.send_personal(websocket, make_event("review_report", {
                                    "report": rev_notes,
                                    "status": rev_status,
                                    "is_approved": is_rev_approved,
                                    "iteration": accumulated_state.get("iteration_count", 0),
                                    "max_iterations": max_iter
                                }))
                                next_node_to_announce = None
                                
                    duration = round(time.time() - start_time, 2)
                    
                    # Simpan hasil output proyek ke folder backend/output/
                    proj_slug = run_id
                    proj_dir.mkdir(parents=True, exist_ok=True)
                    
                    all_files = {}
                    all_files.update(accumulated_state.get("code_files", {}))
                    all_files.update(accumulated_state.get("test_files", {}))
                    
                    for fname, content in all_files.items():
                        fpath = proj_dir / fname
                        fpath.parent.mkdir(parents=True, exist_ok=True)
                        fpath.write_text(content, encoding="utf-8")
                        
                    # Hitung status final misi secara objektif dan non-kontradiktif
                    test_res = accumulated_state.get("test_results", {})
                    is_test_passed = bool(test_res.get("passed", False))
                    final_rev_notes = accumulated_state.get("review_notes", "")
                    is_final_approved = ("[APPROVED]" in final_rev_notes or "APPROVED" in final_rev_notes) and "[NEEDS_REVISION]" not in final_rev_notes
                    
                    if is_test_passed and is_final_approved:
                        final_status = "completed"
                    elif not is_final_approved:
                        final_status = "needs_revision"
                    else:
                        final_status = "tests_failed"
                        
                    # Simpan metadata proyek
                    meta = {
                        "run_id": run_id,
                        "task": task_text,
                        "duration_sec": duration,
                        "iterations": accumulated_state.get("iteration_count", 0),
                        "status": final_status,
                        "tests_passed": is_test_passed,
                        "is_approved": is_final_approved,
                        "executor_intervention_enabled": executor_intervention_enabled,
                        "executor_mode": executor_mode,
                        "frozen_oracle_path": frozen_oracle_path,
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
                            "executor_intervention_enabled": executor_intervention_enabled,
                            "executor_mode": executor_mode,
                            "frozen_oracle_path": frozen_oracle_path,
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
                        "is_approved": is_final_approved
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
