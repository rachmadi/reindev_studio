"""
Canonical Implementation Evidence Schema & Types (Layer 1)
ReinDev Studio — Iterasi 7 (Implementation Grounding & Diagnostic Evidence Hardening v1)

Menyediakan model data terstruktur dan generik untuk merepresentasikan bukti implementasi
deterministik dari compiler, analyzer, interpreter, dan runtime lingkungan aktual.

Prinsip Utama:
1. NON-PRESKRIPTIF: Menyajikan FAKTA implementasi yang dapat diverifikasi, bukan solusi kode.
2. GENERIK: Tidak terikat pada bahasa atau task tertentu.
3. PRESERVASI EVIDENCE: Tidak membuang raw diagnostic atau hubungan caller-callee.
4. KEJUJURAN EPISTEMIK: Jika causal attribution belum terbukti secara pasti, causal_status = "UNKNOWN".
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple


# ===========================================================================
# 1. Implementation Evidence Types (Generic Enum)
# ===========================================================================

class ImplementationEvidenceType(str, Enum):
    """
    Kategori tipe evidence implementasi generik lintas bahasa dan framework.
    Bukan enum ad-hoc untuk kasus saat ini, melainkan taksonomi kegagalan teknis.
    """
    SYMBOL_NOT_FOUND = "SYMBOL_NOT_FOUND"
    SIGNATURE_MISMATCH = "SIGNATURE_MISMATCH"
    CONSTRUCTOR_MISMATCH = "CONSTRUCTOR_MISMATCH"
    TYPE_MISMATCH = "TYPE_MISMATCH"
    TYPE_INCOMPATIBILITY = "TYPE_INCOMPATIBILITY"
    CALL_SHAPE_MISMATCH = "CALL_SHAPE_MISMATCH"
    API_USAGE_ERROR = "API_USAGE_ERROR"
    IMPORT_RESOLUTION_ERROR = "IMPORT_RESOLUTION_ERROR"
    IMPORT_RESOLUTION_FAILURE = "IMPORT_RESOLUTION_FAILURE"
    VERSION_COMPATIBILITY_ERROR = "VERSION_COMPATIBILITY_ERROR"
    RUNTIME_EXCEPTION = "RUNTIME_EXCEPTION"
    COMPILATION_ERROR = "COMPILATION_ERROR"
    TEST_ASSERTION_FAILURE = "TEST_ASSERTION_FAILURE"
    BEHAVIORAL_ASSERTION = "BEHAVIORAL_ASSERTION"
    SCHEMA_VALIDATION_ERROR = "SCHEMA_VALIDATION_ERROR"
    OUTPUT_FORMAT_ERROR = "OUTPUT_FORMAT_ERROR"
    GENERATION_TRUNCATION = "GENERATION_TRUNCATION"


VALID_EVIDENCE_TYPES = {e.value for e in ImplementationEvidenceType}


# ===========================================================================
# 2. Canonical Implementation Evidence Dataclass
# ===========================================================================

@dataclass
class CanonicalImplementationEvidence:
    """
    Representasi formal bukti implementasi deterministik.
    Setiap item merekam fakta yang teramati secara nyata pada execution environment.
    """
    evidence_id: str
    evidence_type: str                         # Dari ImplementationEvidenceType
    source: str                                # e.g. "python_compiler", "dart_analyzer", "pytest_runtime", "ast_inspector"
    source_version: Optional[str] = None       # e.g. "Python 3.13.15", "Flutter 3.x", "Pydantic 2.x"
    file_reference: str = ""                   # Berkas yang diobservasi (relatif atau nama berkas)
    line_reference: Optional[int] = None       # Baris kode (jika diketahui)
    symbol_reference: Optional[str] = None     # Simbol spesifik (fungsi, kelas, konstanta)
    observed: Any = None                       # Kondisi aktual yang ditemukan oleh environment
    expected: Any = None                       # Kondisi yang diwajibkan oleh kontrak/pengujian
    compatibility_status: str = "UNKNOWN"      # "COMPATIBLE", "INCOMPATIBLE", "NOT_FOUND", "UNKNOWN"
    diagnostic_message: str = ""               # Pesan diagnostik bersih dari compiler/runtime
    provenance: str = "DETERMINISTIC_TOOLING"  # Asal fakta: "DETERMINISTIC_TOOLING", "COMPILER", "RUNTIME", "AST_SCAN"
    confidence: float = 1.0                    # 0.0 - 1.0 (deterministik = 1.0)
    caller_site: Optional[str] = None          # Lokasi pemanggil (e.g. "test_main.py:12: Matrix([[1, 2]])")
    callee_site: Optional[str] = None          # Lokasi deklarasi yang dipanggil (e.g. "main.py:10: class Matrix(BaseModel)")
    causal_status: str = "UNKNOWN"             # "PROVEN", "CORRELATED", "UNKNOWN"
    raw_diagnostic_excerpt: Optional[str] = None # Cuplikan raw diagnostic asli untuk auditability

    @classmethod
    def make_id(cls, source: str, ev_type: str, file_ref: str, line_ref: Optional[int] = None, symbol_ref: Optional[str] = None) -> str:
        """Membuat evidence_id deterministik dari komponen kunci."""
        raw = f"{source}:{ev_type}:{file_ref}:{line_ref or ''}:{symbol_ref or ''}"
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:10]
        return f"EV-IMPL-{digest.upper()}"

    def format_compact(self) -> str:
        """
        Format baris tunggal ringkas dengan rasio signal-to-noise maksimal.
        Cocok untuk prompt context dengan budget token ketat.
        """
        loc = self.file_reference or "unknown_file"
        if self.line_reference:
            loc += f":{self.line_reference}"
        sym = f" [{self.symbol_reference}]" if self.symbol_reference else ""
        msg = self.diagnostic_message.replace("\n", " ").strip()
        if len(msg) > 140:
            msg = msg[:137] + "..."
        
        causal_note = f" (Causal: {self.causal_status})" if self.causal_status != "UNKNOWN" else ""
        caller_note = f" | Caller: {self.caller_site}" if self.caller_site else ""
        return f"• [{self.evidence_type}]{sym} at {loc}: {msg}{caller_note}{causal_note}"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CanonicalImplementationEvidence:
        ev_type = str(data.get("evidence_type", "UNKNOWN"))
        if ev_type in VALID_EVIDENCE_TYPES:
            pass
        return cls(
            evidence_id=str(data.get("evidence_id", "EV-IMPL-UNKNOWN")),
            evidence_type=ev_type,
            source=str(data.get("source", "environment")),
            source_version=data.get("source_version"),
            file_reference=str(data.get("file_reference", "")),
            line_reference=data.get("line_reference"),
            symbol_reference=data.get("symbol_reference"),
            observed=data.get("observed"),
            expected=data.get("expected"),
            compatibility_status=str(data.get("compatibility_status", "UNKNOWN")),
            diagnostic_message=str(data.get("diagnostic_message", "")),
            provenance=str(data.get("provenance", "DETERMINISTIC_TOOLING")),
            confidence=float(data.get("confidence", 1.0)),
            caller_site=data.get("caller_site"),
            callee_site=data.get("callee_site"),
            causal_status=str(data.get("causal_status", "UNKNOWN")),
            raw_diagnostic_excerpt=data.get("raw_diagnostic_excerpt")
        )


# ===========================================================================
# 3. Deduplication and Normalization Utilities
# ===========================================================================

def deduplicate_evidence(
    evidence_list: List[CanonicalImplementationEvidence]
) -> List[CanonicalImplementationEvidence]:
    """
    Deduplikasi hanya jika seluruh komponen struktural kunci benar-benar identik:
    (evidence_type, file_reference, line_reference, symbol_reference, diagnostic_message).
    Tidak membuang kegagalan independen atau berbeda lokasi.
    """
    seen: set = set()
    deduped: List[CanonicalImplementationEvidence] = []
    for ev in evidence_list:
        key = (
            ev.evidence_type,
            ev.file_reference,
            ev.line_reference,
            ev.symbol_reference,
            ev.diagnostic_message.strip()
        )
        if key not in seen:
            seen.add(key)
            deduped.append(ev)
    return deduped
