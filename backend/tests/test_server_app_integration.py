# -*- coding: utf-8 -*-
"""
Uji Integrasi End-to-End Execution Path Aplikasi ReinDev Studio (backend/server.py)
Menguji:
1. REST API: Health, Presets, Config, Projects
2. Preset Resolver & Checksum Verifier (fastapi_t1, cli_t1, flutter_t1)
3. WebSocket /ws/squad Handshake, Ping, Error handling
4. E2E Execution Path WebSocket Streaming dengan 6 Quality Boundaries (V1-V6)
"""

import os
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.server import (
    app,
    PRESET_REGISTRY,
    resolve_preset_config,
    verify_oracle_checksum,
    CONFIG_STATE
)

client = TestClient(app)


def test_api_health():
    """Memverifikasi endpoint REST health check."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["service"] == "reindev_studio_backend"
    assert data["version"] == "1.0.0"


def test_api_presets():
    """Memverifikasi ketersediaan 3 preset misi otoritatif."""
    resp = client.get("/api/presets")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    presets = {p["preset_id"]: p for p in data["presets"]}
    
    assert "fastapi_t1" in presets
    assert "cli_t1" in presets
    assert "flutter_t1" in presets

    # Verifikasi integritas metadata dan file oracle untuk tiap preset
    for pid, p in presets.items():
        assert Path(p["oracle_path"]).exists()
        assert len(p["expected_sha"]) == 64
        assert p["n_tests"] > 0


def test_resolve_preset_config():
    """Memverifikasi resolusi otomatis preset dari task text, preset_id, atau oracle_path."""
    # 1. By preset_id
    pid, path, sha = resolve_preset_config({"preset_id": "fastapi_t1"})
    assert pid == "fastapi_t1"
    assert sha == "a1db9bb1f6eaf47d5cf56e102c4a0f6e1f49d757e9faa1485b36f2972a152d63"

    # 2. By task text keywords
    pid, path, sha = resolve_preset_config({"task": "Bangun modul REST API FastAPI untuk manajemen inventaris produk"})
    assert pid == "fastapi_t1"

    pid, path, sha = resolve_preset_config({"task": "Bangun komponen widget kartu metrik modern responsif Flutter"})
    assert pid == "flutter_t1"
    assert sha == "4589e15cfb8f37ba70642e70623ca143bceee1a44175aefd072f441d9e8a9528"

    pid, path, sha = resolve_preset_config({"task": "Bangun kalkulator CLI Python dengan operasi matriks"})
    assert pid == "cli_t1"
    assert sha == "0bd5b598afa7ae4c9cdf0e269d13136b51d35a4e0b1ac6548f0a2cf8a8eba124"

    # 3. Custom task
    pid, path, sha = resolve_preset_config({"task": "Bangun web scraping sederhana"})
    assert pid is None
    assert path is None


def test_verify_oracle_checksum():
    """Memverifikasi verifikator checksum SHA-256 pada frozen oracle fisik."""
    for pid, p in PRESET_REGISTRY.items():
        ok, actual_sha = verify_oracle_checksum(
            str(p["oracle_path"]),
            p["expected_sha"],
            p["oracle_file"]
        )
        assert ok is True
        assert actual_sha == p["expected_sha"].lower()

    # Case: mismatch
    ok, err = verify_oracle_checksum(
        str(PRESET_REGISTRY["fastapi_t1"]["oracle_path"]),
        "badhashbadhashbadhashbadhashbadhashbadhashbadhashbadhashbadhashbad",
        "test_main.py"
    )
    assert ok is False
    assert err == "SHA_MISMATCH"


def test_websocket_handshake_and_ping():
    """Memverifikasi handshake koneksi dan respons ping-pong."""
    with client.websocket_connect("/ws/squad") as ws:
        connected = ws.receive_json()
        assert connected["event"] == "connected"
        assert "available_presets" in connected
        assert "fastapi_t1" in connected["available_presets"]

        ws.send_json({"action": "ping"})
        pong = ws.receive_json()
        assert pong["event"] == "pong"


def test_websocket_error_cases():
    """Memverifikasi penanganan error input pada WebSocket."""
    with client.websocket_connect("/ws/squad") as ws:
        ws.receive_json()  # discard connected

        # 1. Unknown action
        ws.send_json({"action": "unknown_action_xyz"})
        err = ws.receive_json()
        assert err["event"] == "error"

        # 2. Empty task
        ws.send_json({"action": "start_squad", "task": "   "})
        err = ws.receive_json()
        assert err["event"] == "error"
        assert "tidak boleh kosong" in err["message"]


def test_websocket_execution_path_mocked_stream():
    """
    Memverifikasi seluruh rangkaian event WebSocket yang dipancarkan
    selama eksekusi alur StateGraph dengan 6 Quality Boundaries.
    """
    # Buat sekuens output mock dari 13 node StateGraph
    mock_steps = [
        {"pm": {"specifications": "# Spesifikasi Modul\n- REQ-01: Operasi CRUD"}},
        {"pm_validator": {
            "pm_validator_contract": {"verdict": "PASS", "violations": []},
            "logs": ["[PM Validator]: Lolos Boundary V1."]
        }},
        {"architect": {"architecture_plan": "```json\n{\"components\": []}\n```"}},
        {"architect_validator": {
            "architect_validator_contract": {"verdict": "PASS", "violations": []},
            "contract_status": "FROZEN",
            "contract_sha256": "abcdef1234567890",
            "logs": ["[Architect Validator]: Contract FROZEN."]
        }},
        {"developer": {"code_files": {"main.py": "def add(a, b): return a + b\n"}}},
        {"developer_validator": {
            "developer_validator_contract": {"verdict": "PASS", "violations": []},
            "logs": ["[Developer Validator]: Lolos Boundary V3."]
        }},
        {"frozen_oracle": {"test_files": {"test_main.py": "def test_add(): assert add(1, 2) == 3\n"}}},
        {"test_suite_validator": {
            "test_suite_validator_contract": {"verdict": "PASS", "violations": []},
            "logs": ["[Test Suite Validator]: Lolos Boundary V4."]
        }},
        {"executor": {
            "test_results": {"passed": True, "summary": "1 passed", "passed_count": 1, "failed_count": 0}
        }},
        {"executor_validator": {
            "executor_iteration_validator_contract": {
                "verdict": "PASS",
                "regressions": [],
                "locked_invariants": {}
            },
            "logs": ["[Executor Validator]: Lolos Boundary V5."]
        }},
        {"reviewer": {"review_notes": "[APPROVED] Kode bersih dan memenuhi null safety."}},
        {"reviewer_validator": {
            "reviewer_validator_contract": {
                "verdict": "PASS",
                "evaluated_review_verdict": "APPROVED"
            },
            "review_verdict": "APPROVED",
            "logs": ["[Reviewer Validator]: Lolos Boundary V6."]
        }}
    ]

    with patch("backend.server.squad_graph.stream", return_value=iter(mock_steps)):
        with client.websocket_connect("/ws/squad") as ws:
            ws.receive_json()  # discard connected

            ws.send_json({
                "action": "start_squad",
                "preset_id": "fastapi_t1",
                "task": PRESET_REGISTRY["fastapi_t1"]["task"],
                "target_language": "python",
                "max_iterations": 2
            })

            received_events = []
            while True:
                msg = ws.receive_json()
                received_events.append(msg)
                if msg["event"] == "complete":
                    break

            event_types = [e["event"] for e in received_events]

            # Verifikasi urutan dan kehadiran seluruh event utama
            assert "session_start" in event_types
            assert "agent_state" in event_types
            assert "phase_validation" in event_types
            assert "agent_thought" in event_types
            assert "code_update" in event_types
            assert "test_log" in event_types
            assert "loop_status" in event_types
            assert "review_report" in event_types
            assert "complete" in event_types

            # Verifikasi 6 boundaries dipancarkan dalam phase_validation
            pv_events = [e for e in received_events if e["event"] == "phase_validation"]
            phases = [p["phase"] for p in pv_events]
            boundaries = [p["boundary"] for p in pv_events]
            assert "PM" in phases
            assert "ARCHITECT" in phases
            assert "DEVELOPER" in phases
            assert "TEST_SUITE" in phases
            assert "EXECUTOR" in phases
            assert "REVIEWER" in phases

            assert "V1" in boundaries
            assert "V2" in boundaries
            assert "V3" in boundaries
            assert "V4" in boundaries
            assert "V5" in boundaries
            assert "V6" in boundaries

            # Verifikasi event complete
            complete_event = [e for e in received_events if e["event"] == "complete"][0]
            assert complete_event["status"] == "completed"
            assert complete_event["is_approved"] is True
            assert complete_event["tests_passed"] is True
            assert complete_event["contract_status"] == "FROZEN"
            assert complete_event["review_verdict"] == "APPROVED"
