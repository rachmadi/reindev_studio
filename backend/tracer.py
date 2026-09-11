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

    # Iterasi 7: Helper Telemetry Methods for Deterministic Context-Aware Validation
    def log_validation_failure(self, validator: str, verdict: str, violations_count: int, package_hash: str = "", iteration: int = 0) -> None:
        self.log_event(
            stage="deterministic_validation",
            event_type="validation_failure",
            iteration=iteration,
            data={
                "validator": validator,
                "verdict": verdict,
                "violations_count": violations_count,
                "package_hash": package_hash,
            }
        )

    def log_contextual_evidence_assembled(self, package_id: str, package_hash: str, causal_owner: str, size_bytes: int = 0, iteration: int = 0) -> None:
        self.log_event(
            stage="contextual_evidence",
            event_type="contextual_evidence_assembled",
            iteration=iteration,
            data={
                "package_id": package_id,
                "package_hash": package_hash,
                "causal_owner": causal_owner,
                "size_bytes": size_bytes,
            }
        )

    def log_repair_directive_issued(self, package_id: str, target_agent: str, length_chars: int = 0, iteration: int = 0) -> None:
        self.log_event(
            stage="contextual_evidence",
            event_type="repair_directive_issued",
            iteration=iteration,
            data={
                "package_id": package_id,
                "target_agent": target_agent,
                "length_chars": length_chars,
            }
        )

    def log_repair_attempt(self, turn: int, package_id: str, iteration: int = 0) -> None:
        self.log_event(
            stage="repair_loop",
            event_type="repair_attempt",
            iteration=iteration,
            data={
                "turn": turn,
                "package_id": package_id,
            }
        )

    def log_revalidation(self, package_id: str, validator: str, previous_verdict: str, iteration: int = 0) -> None:
        self.log_event(
            stage="deterministic_validation",
            event_type="revalidation",
            iteration=iteration,
            data={
                "package_id": package_id,
                "validator": validator,
                "previous_verdict": previous_verdict,
            }
        )

    def log_repair_outcome(self, package_id: str, outcome: str, turns_to_pass: int = 0, iteration: int = 0) -> None:
        self.log_event(
            stage="repair_loop",
            event_type="repair_outcome",
            iteration=iteration,
            data={
                "package_id": package_id,
                "outcome": outcome,
                "turns_to_pass": turns_to_pass,
            }
        )

    def log_actionable_prescription(
        self,
        package_id: str,
        prescription_id: str,
        oracle_call_site: str,
        implementation_symbol: str,
        required_change: str,
        iteration: int = 0,
    ) -> None:
        self.log_event(
            stage="contextual_evidence",
            event_type="actionable_prescription_emitted",
            iteration=iteration,
            data={
                "package_id": package_id,
                "prescription_id": prescription_id,
                "oracle_call_site": oracle_call_site,
                "implementation_symbol": implementation_symbol,
                "required_change": required_change,
            }
        )

    def log_diagnostic_evidence(
        self,
        package_id: str,
        validator: str,
        raw_evidence: Any,
        iteration: int = 0,
    ) -> None:
        self.log_event(
            stage="deterministic_validation",
            event_type="diagnostic_evidence_collected",
            iteration=iteration,
            data={
                "package_id": package_id,
                "validator": validator,
                "raw_evidence": str(raw_evidence)[:500],
            }
        )


def get_tracer(run_id: Optional[str] = None) -> Optional[RunTracer]:
    """Helper fungsi global untuk mendapatkan instance tracer aktif."""
    return RunTracer.get(run_id)


def calculate_trace_otrr(trace_file: Path | str) -> Dict[str, Any]:
    """
    Menghitung One-Turn Repair Rate (OTRR) dari berkas trace JSONL.
    OTRR = (jumlah failure yang teratasi dalam 1 turn) / (total failure yang dicoba di-repair)
    """
    trace_path = Path(trace_file)
    if not trace_path.exists():
        return {
            "otrr": 0.0,
            "otrr_percent": 0.0,
            "total_failures_with_repair": 0,
            "first_turn_successes": 0,
            "repair_records": []
        }

    repair_outcomes = []
    try:
        with open(trace_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("event_type") == "repair_outcome":
                        data = entry.get("data", {})
                        repair_outcomes.append({
                            "package_id": data.get("package_id", ""),
                            "outcome": data.get("outcome", ""),
                            "turns_to_pass": data.get("turns_to_pass", 0)
                        })
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass

    if not repair_outcomes:
        return {
            "otrr": 0.0,
            "otrr_percent": 0.0,
            "total_failures_with_repair": 0,
            "first_turn_successes": 0,
            "repair_records": []
        }

    first_turn_successes = sum(1 for r in repair_outcomes if r.get("turns_to_pass") == 1 and r.get("outcome") == "SUCCESS")
    total_failures = len(repair_outcomes)
    otrr = first_turn_successes / total_failures if total_failures > 0 else 0.0

    return {
        "otrr": round(otrr, 4),
        "otrr_percent": round(otrr * 100.0, 2),
        "total_failures_with_repair": total_failures,
        "first_turn_successes": first_turn_successes,
        "repair_records": repair_outcomes
    }
