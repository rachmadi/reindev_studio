import os
import json
import hashlib
import threading
import logging
import uuid
from contextvars import ContextVar
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


_UNSPECIFIED_RUN_ID = object()
_TRACE_CONTEXT = ContextVar("reindev_trace_context", default=None)


def set_trace_context(correlation_id: str, parent_event_id: Optional[str] = None):
    """Associate events emitted inside one graph-node execution with that node."""
    return _TRACE_CONTEXT.set({
        "correlation_id": correlation_id,
        "parent_event_id": parent_event_id,
    })


def reset_trace_context(token) -> None:
    """Restore the previous trace context after a node finishes."""
    _TRACE_CONTEXT.reset(token)


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
        self._event_sequence = 0
        self._write_failures = 0
        self._logger = logging.getLogger(__name__)

    @classmethod
    def register(cls, run_id: str, output_dir: Path | str) -> "RunTracer":
        with cls._lock:
            tracer = cls(run_id, output_dir)
            cls._instances[run_id] = tracer
            cls._active_run_id = run_id
            return tracer

    @classmethod
    def get(cls, run_id: Any = _UNSPECIFIED_RUN_ID) -> Optional["RunTracer"]:
        with cls._lock:
            # An explicit value (including None) is authoritative; never attribute
            # an unscoped event to whichever run registered most recently.
            if run_id is not _UNSPECIFIED_RUN_ID:
                return cls._instances.get(run_id) if isinstance(run_id, str) else None
            if cls._active_run_id and cls._active_run_id in cls._instances:
                return cls._instances[cls._active_run_id]
            return None

    @property
    def write_failures(self) -> int:
        """Jumlah kegagalan append yang diketahui selama umur instance ini."""
        return self._write_failures

    def log_event(
        self,
        stage: str,
        event_type: str,
        iteration: int,
        data: Dict[str, Any],
        correlation_id: Optional[str] = None,
        parent_event_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Append satu event JSONL. Mengembalikan event_id untuk menghubungkan event.
        Kegagalan observability dilaporkan melalui logger dan tidak dilempar ke pipeline.
        """
        context = _TRACE_CONTEXT.get()
        if context:
            if correlation_id is None:
                correlation_id = context.get("correlation_id")
            if parent_event_id is None:
                parent_event_id = context.get("parent_event_id")
        timestamp = datetime.now().astimezone().isoformat()
        event_id = uuid.uuid4().hex
        event = {
            "event_id": event_id,
            "run_id": self.run_id,
            "timestamp": timestamp,
            "stage": stage,
            "event_type": event_type,
            "iteration": iteration,
            "data": data,
        }
        if correlation_id is not None:
            event["correlation_id"] = correlation_id
        if parent_event_id is not None:
            event["parent_event_id"] = parent_event_id

        try:
            json.dumps(event, default=str, ensure_ascii=False)
        except Exception as exc:
            event["stage"] = stage
            event["event_type"] = "serialization_failure"
            event["data"] = {
                "original_stage": stage,
                "original_event_type": event_type,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            }

        try:
            with self._file_lock:
                self._event_sequence += 1
                event["sequence"] = self._event_sequence
                line = json.dumps(event, default=str, ensure_ascii=False)
                with open(self.trace_file, "a", encoding="utf-8") as trace:
                    trace.write(line + "\n")
                    trace.flush()
            return event_id
        except Exception as exc:
            with self._file_lock:
                self._write_failures += 1
            # Do not recursively write to a file whose append just failed.
            # Report the loss through process logging without stopping the pipeline.
            self._logger.error(
                "AUDIT_TRACE_WRITE_FAILURE run_id=%s sequence=%s stage=%s event_type=%s path=%s error=%s",
                self.run_id, self._event_sequence, stage, event_type,
                self.trace_file, exc, exc_info=True,
            )
            return None

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


def get_tracer(run_id: Any = _UNSPECIFIED_RUN_ID) -> Optional[RunTracer]:
    """Ambil tracer berdasarkan run_id; hanya pemanggilan tanpa argumen memakai tracer aktif."""
    return RunTracer.get(run_id)


def log_model_interaction(
    tracer: Optional[RunTracer],
    role: str,
    messages: Any,
    response: Any,
    raw_output: Any,
    duration_sec: float,
    iteration: int = 0,
    provider: Optional[str] = None,
    requested_model: Optional[str] = None,
    model_client: Any = None,
    backend_metadata: Optional[Dict[str, Any]] = None,
    error: Optional[BaseException] = None,
) -> None:
    """Record the actual prompt, raw model output, timing and non-secret call metadata."""
    if tracer is None:
        return
    try:
        message_snapshot = []
        for message in messages or []:
            message_snapshot.append({
                "role": getattr(message, "type", type(message).__name__),
                "content": getattr(message, "content", str(message)),
            })
        raw_text = raw_output if isinstance(raw_output, str) else str(raw_output)
        client_model = None
        for attr in ("model", "model_name", "model_id"):
            try:
                client_model = getattr(model_client, attr, None)
            except Exception:
                client_model = None
            if client_model:
                break
        client_config = {}
        if model_client is not None:
            for attr in ("base_url", "temperature", "num_ctx", "num_predict", "max_tokens", "max_retries", "top_p"):
                try:
                    value = getattr(model_client, attr, None)
                except Exception:
                    value = None
                if isinstance(value, (str, int, float, bool)) or value is None:
                    if value is not None:
                        client_config[attr] = value
        response_metadata = {}
        usage_metadata = {}
        if response is not None:
            try:
                response_metadata = getattr(response, "response_metadata", {}) or {}
            except Exception:
                response_metadata = {}
            try:
                usage_metadata = getattr(response, "usage_metadata", {}) or {}
            except Exception:
                usage_metadata = {}
        data = {
            "role": role,
            "provider": provider,
            "requested_model": requested_model,
            "resolved_model": client_model,
            "model_client_type": type(model_client).__name__ if model_client is not None else None,
            "model_client_config": client_config,
            "prompt_messages": message_snapshot,
            "prompt_sha256": compute_object_hash(message_snapshot),
            "raw_output": raw_text,
            "raw_output_sha256": compute_sha256(raw_text),
            "duration_sec": round(float(duration_sec), 6),
            "response_metadata": response_metadata,
            "usage_metadata": usage_metadata,
            "backend_metadata": backend_metadata or {},
        }
        if error is not None:
            data["error"] = {
                "type": type(error).__name__,
                "message": str(error),
            }
        tracer.log_event(
            stage=role,
            event_type="model_call_error" if error is not None else "model_call",
            iteration=iteration,
            data=data,
        )
    except Exception:
        # Instrumentation must never mask model results or the original exception.
        return


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
