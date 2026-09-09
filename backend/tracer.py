import os
import json
import hashlib
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

def compute_sha256(content: str | bytes) -> str:
    """Menghitung hash SHA-256 dari teks atau byte untuk verifikasi integritas artefak."""
    if isinstance(content, str):
        content = content.encode("utf-8", errors="replace")
    return hashlib.sha256(content).hexdigest()

def compute_dict_hashes(files: Dict[str, str]) -> Dict[str, str]:
    """Menghitung hash SHA-256 untuk setiap file dalam dictionary {'filename': 'content'}."""
    return {fname: compute_sha256(content) for fname, content in files.items()}

def compute_object_hash(obj: Any) -> str:
    """Menghitung hash SHA-256 dari objek dictionary/list data (diserialisasi json terurut)."""
    try:
        serialized = json.dumps(obj, sort_keys=True, default=str)
        return compute_sha256(serialized)
    except Exception:
        return ""

class RunTracer:
    """
    Tracer append-only berbasis JSONL untuk observabilitas mendalam alur multi-agent ReinDev Studio.
    Seluruh operasi logging dilindungi fail-safe agar tidak pernah menghentikan pipeline utama.
    """
    _instances: Dict[str, "RunTracer"] = {}
    _lock = threading.Lock()
    _active_run_id: Optional[str] = None

    def __init__(self, run_id: str, output_dir: Path | str):
        self.run_id = run_id
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.trace_file = self.output_dir / "run_trace.jsonl"
        self._file_lock = threading.Lock()

    @classmethod
    def register(cls, run_id: str, output_dir: Path | str) -> "RunTracer":
        with cls._lock:
            tracer = cls(run_id, output_dir)
            cls._instances[run_id] = tracer
            cls._active_run_id = run_id
            return tracer

    @classmethod
    def get(cls, run_id: Optional[str] = None) -> Optional["RunTracer"]:
        with cls._lock:
            if run_id and run_id in cls._instances:
                return cls._instances[run_id]
            if cls._active_run_id and cls._active_run_id in cls._instances:
                return cls._instances[cls._active_run_id]
            return None

    def log_event(self, stage: str, event_type: str, iteration: int, data: Dict[str, Any]) -> None:
        """
        Merekam satu event observabilitas ke dalam berkas run_trace.jsonl secara thread-safe dan aman.
        Jika serialisasi gagal, event logging_error akan dicatat sebagai pengganti tanpa melempar exception.
        """
        timestamp = datetime.now().isoformat()
        event = {
            "run_id": self.run_id,
            "timestamp": timestamp,
            "stage": stage,
            "event_type": event_type,
            "iteration": iteration,
            "data": data
        }

        try:
            line = json.dumps(event, default=str, ensure_ascii=False)
        except Exception as e:
            fallback_event = {
                "run_id": self.run_id,
                "timestamp": timestamp,
                "stage": stage,
                "event_type": "logging_error",
                "iteration": iteration,
                "data": {
                    "error_message": str(e),
                    "original_stage": stage,
                    "original_event_type": event_type
                }
            }
            try:
                line = json.dumps(fallback_event, default=str, ensure_ascii=False)
            except Exception:
                return

        try:
            with self._file_lock:
                with open(self.trace_file, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
        except Exception:
            pass

def get_tracer(run_id: Optional[str] = None) -> Optional[RunTracer]:
    """Helper fungsi global untuk mendapatkan instance tracer aktif."""
    return RunTracer.get(run_id)
