import os
import pytest
from pathlib import Path

# Pastikan mock LLM aktif untuk unit test instan
os.environ["MOCK_LLM"] = "true"

from fastapi.testclient import TestClient
from backend.server import app, OUTPUT_DIR

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "reindev_studio_backend"
    assert data["version"] == "1.0.0"

def test_config_endpoints():
    # 1. GET Config
    get_res = client.get("/api/config")
    assert get_res.status_code == 200
    cfg = get_res.json()["config"]
    assert "provider" in cfg
    assert "max_iterations" in cfg

    # 2. POST Update Config
    post_res = client.post("/api/config", json={
        "provider": "ollama",
        "max_iterations": 4,
        "target_language": "python"
    })
    assert post_res.status_code == 200
    updated_cfg = post_res.json()["config"]
    assert updated_cfg["max_iterations"] == 4
    assert updated_cfg["target_language"] == "python"

def test_projects_endpoints(tmp_path):
    # Buat dummy project di folder output
    dummy_proj = OUTPUT_DIR / "test_dummy_project"
    dummy_proj.mkdir(parents=True, exist_ok=True)
    (dummy_proj / "main.py").write_text("print('hello')", encoding="utf-8")

    try:
        # GET List Projects
        list_res = client.get("/api/projects")
        assert list_res.status_code == 200
        projs = list_res.json()["projects"]
        assert any(p["name"] == "test_dummy_project" for p in projs)

        # GET Project Detail
        detail_res = client.get("/api/projects/test_dummy_project")
        assert detail_res.status_code == 200
        files = detail_res.json()["files"]
        assert "main.py" in files
        assert files["main.py"] == "print('hello')"
    finally:
        # Bersihkan dummy project
        import shutil
        shutil.rmtree(dummy_proj, ignore_errors=True)

def test_websocket_ping_pong():
    with client.websocket_connect("/ws/squad") as ws:
        init_event = ws.receive_json()
        assert init_event["event"] == "connected"
        assert "active_config" in init_event

        ws.send_json({"action": "ping"})
        pong_event = ws.receive_json()
        assert pong_event["event"] == "pong"

def test_websocket_start_squad_pipeline():
    with client.websocket_connect("/ws/squad") as ws:
        # 1. Terima event koneksi
        init_event = ws.receive_json()
        assert init_event["event"] == "connected"

        # 2. Kirim perintah start_squad
        ws.send_json({
            "action": "start_squad",
            "task": "Kalkulator vektor sederhana untuk menghitung dot product",
            "provider": "ollama"
        })

        # 3. Kumpulkan seluruh event yang dikirimkan oleh backend
        received_events = []
        is_completed = False

        while not is_completed:
            event = ws.receive_json()
            received_events.append(event)
            event_type = event.get("event")

            if event_type == "complete":
                is_completed = True
                assert event["status"] == "completed"
                assert "files" in event
                assert len(event["files"]) > 0
                assert "project_dir" in event
            elif event_type == "error":
                pytest.fail(f"WebSocket error received: {event.get('message')}")

        # 4. Validasi keberadaan tipe-tipe event JSON Protocol sesuai REQ-013
        event_types = [e["event"] for e in received_events]
        assert "session_start" in event_types
        assert "agent_state" in event_types
        assert "agent_thought" in event_types
        assert "code_update" in event_types
        assert "test_log" in event_types
        assert "review_report" in event_types
        assert "complete" in event_types
