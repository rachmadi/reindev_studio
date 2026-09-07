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
                model_name = data.get("model_name", CONFIG_STATE["ollama_model"])
                target_lang = data.get("target_language", CONFIG_STATE["target_language"])
                max_iter = data.get("max_iterations", CONFIG_STATE["max_iterations"])
                
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
                    "logs": []
                }
                
                start_time = time.time()
                await manager.send_personal(websocket, make_event("session_start", {
                    "task": task_text,
                    "provider": provider,
                    "model_name": model_name,
                    "target_language": target_lang
                }))
                
                # Eksekusi StateGraph secara asynchronous dan broadcast tiap transisi node
                loop = asyncio.get_event_loop()
                
                try:
                    # Jalankan stream di thread terpisah agar async loop WebSocket tetap responsif
                    def run_stream():
                        events = []
                        for step_event in squad_graph.stream(initial_state):
                            events.append(step_event)
                        return events
                    
                    stream_generator = squad_graph.stream(initial_state)
                    
                    # Kita proses generator dengan thread executor per step
                    def get_next(gen):
                        try:
                            return next(gen), False
                        except StopIteration:
                            return None, True

                    accumulated_state = initial_state.copy()
                    
                    while True:
                        step_result, is_done = await loop.run_in_executor(None, get_next, stream_generator)
                        if is_done or not step_result:
                            break
                            
                        for node_name, node_output in step_result.items():
                            accumulated_state.update(node_output)
                            last_log = node_output.get("logs", [""])[-1] if node_output.get("logs") else ""
                            
                            # 1. Notifikasi Agent Start / Progress
                            await manager.send_personal(websocket, make_event("agent_state", {
                                "node": node_name,
                                "status": node_output.get("status", "running"),
                                "iteration": accumulated_state.get("iteration_count", 0),
                                "log": last_log
                            }))
                            
                            # 2. Spesifik Event berdasarkan Node
                            if node_name == "pm" and "specifications" in node_output:
                                await manager.send_personal(websocket, make_event("agent_thought", {
                                    "agent": "pm",
                                    "thought": node_output["specifications"]
                                }))
                            elif node_name == "architect" and "architecture_plan" in node_output:
                                await manager.send_personal(websocket, make_event("agent_thought", {
                                    "agent": "architect",
                                    "thought": node_output["architecture_plan"]
                                }))
                            elif node_name == "developer" and "code_files" in node_output:
                                await manager.send_personal(websocket, make_event("code_update", {
                                    "agent": "developer",
                                    "files": node_output["code_files"]
                                }))
                            elif node_name == "tester" and "test_files" in node_output:
                                await manager.send_personal(websocket, make_event("code_update", {
                                    "agent": "tester",
                                    "files": node_output["test_files"]
                                }))
                            elif node_name == "executor" and "test_results" in node_output:
                                await manager.send_personal(websocket, make_event("test_log", {
                                    "results": node_output["test_results"],
                                    "iteration": node_output.get("iteration_count", 0)
                                }))
                            elif node_name == "reviewer" and "review_notes" in node_output:
                                await manager.send_personal(websocket, make_event("review_report", {
                                    "report": node_output["review_notes"],
                                    "status": node_output.get("status", "completed")
                                }))
                                
                    duration = round(time.time() - start_time, 2)
                    
                    # Simpan hasil output proyek ke folder backend/output/
                    proj_slug = "project_" + datetime.now().strftime("%Y%m%d_%H%M%S")
                    proj_dir = OUTPUT_DIR / proj_slug
                    proj_dir.mkdir(parents=True, exist_ok=True)
                    
                    all_files = {}
                    all_files.update(accumulated_state.get("code_files", {}))
                    all_files.update(accumulated_state.get("test_files", {}))
                    
                    for fname, content in all_files.items():
                        fpath = proj_dir / fname
                        fpath.parent.mkdir(parents=True, exist_ok=True)
                        fpath.write_text(content, encoding="utf-8")
                        
                    # Simpan metadata proyek
                    meta = {
                        "task": task_text,
                        "duration_sec": duration,
                        "iterations": accumulated_state.get("iteration_count", 0),
                        "status": accumulated_state.get("status", "completed"),
                        "timestamp": datetime.now().isoformat()
                    }
                    (proj_dir / "project_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
                    
                    # Kirim event Complete
                    await manager.send_personal(websocket, make_event("complete", {
                        "status": accumulated_state.get("status", "completed"),
                        "duration_sec": duration,
                        "iterations": accumulated_state.get("iteration_count", 0),
                        "project_name": proj_slug,
                        "project_dir": str(proj_dir.resolve()),
                        "files": all_files,
                        "test_results": accumulated_state.get("test_results", {}),
                        "review_notes": accumulated_state.get("review_notes", "")
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
