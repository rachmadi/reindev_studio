"""
Contextual Evidence Package (CEP) Schema & Rendering Engine
ReinDev Studio — Iterasi 7 (Deterministic Context-Aware Validation)

Menyediakan struktur data formal untuk paket bukti deterministik yang dihasilkan
oleh validator Python dan diinjeksikan ke causal owner (LLM) sebagai satu unit
konteks perbaikan terpadu.

Prinsip Fondasi:
  Python determines REALITY. LLM determines HOW TO REPAIR.

  ONE FAILURE
      → ONE DETERMINISTIC EVIDENCE PACKAGE
      → ONE CAUSAL REPAIR
      → ONE REVALIDATION
"""

from __future__ import annotations

import os
import json
import uuid
import hashlib
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional


# ===========================================================================
# Engineering Doctrine — Foundational Development Principles
# ===========================================================================

ENGINEERING_DOCTRINE: List[str] = [
    "1. [AUTHORITATIVE CONTRACT]: Oracle signatures and assertion requirements are ground truth. Never alter them.",
    "2. [EXCEPTION COMPATIBILITY]: Exception types are contracts: issubclass(Actual, Expected) is required. If Oracle expects ValueError, raise ValueError or inherit from it.",
    "3. [BEHAVIORAL INVARIANT PRESERVATION]: Proven behaviors must never be regressed (BEHAVIORAL_MUTATION: FORBIDDEN). Keep passing tests 100% intact.",
    "4. [CAUSAL REPAIR BOUNDARY]: Modify only code causal to failing tests. Do not rewrite unrelated code.",
    "5. [DETERMINISTIC VERIFICATION]: Repairs are verified deterministically against Frozen Oracle. Zero regression required.",
]
if os.environ.get("REINDEV_TREATMENT_B_R3", "0") == "1":
    if os.environ.get("REINDEV_R3_TREATMENT_AUTHORITY", "0") == "1":
        doctrine_6 = (
            "6. [CONTRACT BOUNDARY & ORACLE AUTHORITY PRINCIPLE]: Acceptance Oracle memiliki otoritas lebih tinggi daripada detail implementasi internal yang tidak secara eksplisit dibekukan. Jika Oracle secara deterministik mensyaratkan sebuah symbol/interface yang belum tercakup dalam frozen contract invariant, Developer wajib memenuhi requirement tersebut; hal itu bukan pelanggaran Contract Boundary."
        )
    else:
        doctrine_6 = (
            "6. [CONTRACT BOUNDARY PRINCIPLE]: Frozen status applies strictly to external contract elements (routes, identifiers, verbs). Implementation details (internal fields, default values, mappings) may be adjusted to satisfy Oracle evidence while preserving frozen invariants."
        )
    ENGINEERING_DOCTRINE.append(doctrine_6)


# ===========================================================================
# 1. Sub-Schema Data Classes
# ===========================================================================

@dataclass
class ViolationItem:
    """Representasi pelanggaran tunggal yang ditemukan secara deterministik."""
    violation_id: str                    # Contoh: "VIO-001"
    criterion: str                       # Contoh: "symbol_resolvability"
    severity: str                        # "CRITICAL" | "WARNING"
    location: str                        # Contoh: "architecture_plan:block_2:line_4"
    observed_state: str                  # Apa yang ditemukan (fakta)
    expected_state: str                  # Apa yang seharusnya ada (fakta)
    source_detector: str                 # Contoh: "AST_INSPECTION" | "CONTRACT_GATE_P0_2.1"
    observed_symbol: Optional[str] = None  # Simbol spesifik yang melanggar

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PreservedInvariant:
    """Invarian perilaku yang sudah terbukti benar dan WAJIB dipertahankan setelah repair (Locked Invariant)."""
    invariant_id: str                    # Contoh: "INV-001"
    category: str                        # "ORACLE_INTEGRITY" | "CONTRACT_STATUS" | "PASSING_TEST" | "AST_STRUCTURE" | "BEHAVIORAL_TEST"
    description: str                     # Deskripsi manusiawi yang jelas
    evidence_value: Any                  # Nilai/hash yang terbukti benar
    status: str = "VERIFIED_TRUE"        # "PROVEN" | "REGRESSED" | "VERIFIED_TRUE" | "UNVERIFIED"
    target: str = ""                     # Target kontrak perilaku (misal: "behavior:test_matrix_addition")
    state: str = "LOCKED"                # "LOCKED" | "ACTIVE" | "VIOLATED"
    mutation: str = "FORBIDDEN"          # "FORBIDDEN" (melarang mutasi perilaku)
    provenance_evidence: Optional[Dict[str, Any]] = None  # Bukti asal pencapaian PROVEN
    regression_evidence: Optional[Dict[str, Any]] = None  # Bukti kegagalan saat regresi
    ever_regressed: bool = False         # Flag permanen: apakah pernah mengalami regresi
    regression_count: int = 0            # Akumulasi jumlah regresi yang pernah terjadi
    regression_history: List[Dict[str, Any]] = field(default_factory=list)  # Rekaman lengkap semua regresi

    def record_regression(self, failure_evidence: Any, iteration: int = 0) -> None:
        """Mencatat kejadian regresi secara permanen tanpa menghapus riwayat."""
        self.status = "REGRESSED"
        self.state = "VIOLATED"
        self.ever_regressed = True
        self.regression_count += 1
        record = {
            "iteration": iteration,
            "failure_evidence": str(failure_evidence),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.regression_evidence = record
        self.regression_history.append(record)

    def record_recovery(self, recovery_evidence: Any, iteration: int = 0) -> None:
        """Memulihkan invariant ke status PROVEN dengan tetap mempertahankan riwayat regresi."""
        self.status = "PROVEN"
        self.state = "LOCKED"
        # ever_regressed TETAP True, regression_count TIDAK DIRESET
        if self.regression_history:
            self.regression_history[-1]["recovered_at_iteration"] = iteration
            self.regression_history[-1]["recovery_evidence"] = str(recovery_evidence)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RepairBoundary:
    """Batasan perubahan yang diperbolehkan dan yang dilarang."""
    allowed_changes: List[str] = field(default_factory=list)
    forbidden_changes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RequiredChange:
    """Instruksi perubahan spesifik dan actionable berdasarkan bukti deterministik."""
    change_id: str                       # Contoh: "REQ-001"
    target: str                          # Berkas/blok target (misal: "lib/card_metric.dart")
    violation_ref: str                   # Referensi violation ID (misal: "VIO-001")
    deterministic_requirement: str       # Instruksi berbasis bukti yang presisi
    preserve_refs: List[str] = field(default_factory=list)   # INV-IDs yang wajib dijaga
    forbidden_refs: List[str] = field(default_factory=list)  # Larangan yang wajib dipatuhi

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ViolationDependency:
    """Hubungan kausal antara dua pelanggaran."""
    dependent_violation: str             # Violation ID yang bergantung
    prerequisite: str                    # Violation ID yang harus diperbaiki lebih dahulu
    rationale: str                       # Alasan ketergantungan ini

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ActionableRepairPrescription:
    """
    Resep perbaikan deterministik terarah yang diturunkan dari bukti validator/compiler/AST.
    Menerapkan kejujuran epistemik: memisahkan fakta observasi (Oracle call site)
    dari inferensi kausal (implementation symbol & evidence basis).
    Python determines WHAT IS WRONG + WHERE + WHAT MUST BE TRUE.
    LLM determines HOW TO REPAIR.
    """
    prescription_id: str                   # Contoh: "RX-001"
    evidence_ref: str                      # Referensi violation ID / evidence source
    observed_failure: str                  # Failure aktual sebagaimana dibuktikan validator
    oracle_call_site: str                  # Fakta pemanggilan aktual dari Oracle (misal: "Matrix(data)")
    implementation_symbol: str             # Simbol pada berkas implementasi (misal: "class Matrix in main.py")
    evidence_basis: str                    # Dasar bukti deterministik (misal: "ORACLE_AST_CALL_TRACE + RUNTIME_TYPE_ERROR")
    required_change: str                   # Perubahan kontrak/perilaku yang wajib dipenuhi (requirement)
    repair_boundary_allowed: List[str]     # Area yang boleh diubah
    repair_boundary_forbidden: List[str]   # Area yang tidak boleh disentuh
    expected_post_repair_state: str        # Kondisi deterministik yang harus benar setelah repair
    verification_evidence: str             # Assertion / kegagalan yang harus hilang/PASS setelah repair

    @property
    def causal_site(self) -> str:
        """Helper backward-compatibility: menggabungkan simbol implementasi dan basis bukti."""
        return f"{self.implementation_symbol} (Basis: {self.evidence_basis})"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["causal_site"] = self.causal_site
        return d


# ===========================================================================
# 2. ContextualEvidencePackage — Skema Formal Utama
# ===========================================================================

@dataclass
class ContextualEvidencePackage:
    """
    Paket bukti deterministik terpadu yang dihasilkan oleh Python Validator
    dan diinjeksikan ke causal owner (LLM) sebagai satu unit konteks repair.

    Tidak ada field yang boleh diisi oleh LLM. Seluruh nilai harus dapat
    ditelusuri ke deterministic evidence dari state aktual sistem.
    """
    # Identity
    package_id: str                         # UUID atau run-scoped ID
    timestamp: str                          # ISO 8601 UTC

    # Validator Metadata
    validator: str                          # Contoh: "B2_ARCHITECT_PHASE_END"
    phase: str                              # "PM" | "ARCHITECT" | "DEVELOPER" | "ORACLE" | "EXECUTOR" | "REVIEWER"
    validator_type: str                     # "PHASE_END" | "ITERATION"
    verdict: str                            # "PASS" | "FAIL"
    causal_owner: str                       # "PM" | "ARCHITECT" | "DEVELOPER" | "NONE"

    # Failure Description
    failure_summary: str                    # Ringkasan 1 kalimat deterministik
    root_causes: List[str]                  # Derived deterministic diagnosis (programatik)

    # Violations (Complete Global Scan Result)
    violations: List[ViolationItem]
    violation_dependencies: List[ViolationDependency]

    # Context
    authoritative_context: Dict[str, Any]   # Target file, interface resmi, model resmi
    active_constraints: Dict[str, Any]      # Target lang, framework, max files

    # Invariants & Repair Boundaries
    preserved_invariants: List[PreservedInvariant]
    repair_boundary: RepairBoundary
    forbidden_changes: List[str]            # Ringkasan larangan mutlak

    # Repair Directives
    required_changes: List[RequiredChange]
    expected_post_repair_state: List[str]   # Kondisi yang harus terpenuhi setelah repair
    verification_criteria: List[str]        # Kriteria verifikasi deterministik ulang

    # Evidence Chain
    source_of_truth: str                    # Sumber otoritatif (misal: "CONTRACT_GATE_P0_2.1:d266453b")
    evidence: List[Dict[str, Any]]          # Raw observed vs expected items
    remaining_budget: int = 0              # Sisa anggaran repair yang tersedia
    actionable_prescriptions: List[ActionableRepairPrescription] = field(default_factory=list)

    @classmethod
    def make_id(cls, run_id: str, validator: str, iteration: int) -> str:
        """Membuat package_id yang deterministik dan berlingkup run."""
        raw = f"{run_id}:{validator}:{iteration}"
        digest = hashlib.sha256(raw.encode()).hexdigest()[:12]
        return f"EV-{digest.upper()}"

    @classmethod
    def make_timestamp(cls) -> str:
        """Menghasilkan timestamp ISO 8601 UTC."""
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def to_dict(self) -> Dict[str, Any]:
        """Serialisasi ke dictionary yang dapat dikonversi ke JSON."""
        return {
            "package_id": self.package_id,
            "timestamp": self.timestamp,
            "validator": self.validator,
            "phase": self.phase,
            "validator_type": self.validator_type,
            "verdict": self.verdict,
            "causal_owner": self.causal_owner,
            "failure_summary": self.failure_summary,
            "root_causes": self.root_causes,
            "violations": [v.to_dict() for v in self.violations],
            "violation_dependencies": [vd.to_dict() for vd in self.violation_dependencies],
            "authoritative_context": self.authoritative_context,
            "active_constraints": self.active_constraints,
            "preserved_invariants": [pi.to_dict() for pi in self.preserved_invariants],
            "repair_boundary": self.repair_boundary.to_dict(),
            "forbidden_changes": self.forbidden_changes,
            "required_changes": [rc.to_dict() for rc in self.required_changes],
            "expected_post_repair_state": self.expected_post_repair_state,
            "verification_criteria": self.verification_criteria,
            "source_of_truth": self.source_of_truth,
            "evidence": self.evidence,
            "remaining_budget": self.remaining_budget,
            "actionable_prescriptions": [rx.to_dict() for rx in getattr(self, "actionable_prescriptions", [])],
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialisasi ke JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextualEvidencePackage":
        """Deserialisasi dari dictionary (untuk loading dari fixture JSON)."""
        violations = [
            ViolationItem(
                violation_id=v.get("violation_id", "VIO-???"),
                criterion=v.get("criterion", ""),
                severity=v.get("severity", "CRITICAL"),
                location=v.get("location", ""),
                observed_state=v.get("observed_state", ""),
                expected_state=v.get("expected_state", ""),
                source_detector=v.get("source_detector", ""),
                observed_symbol=v.get("observed_symbol"),
            )
            for v in data.get("violations", [])
        ]
        violation_dependencies = [
            ViolationDependency(
                dependent_violation=vd.get("dependent_violation", ""),
                prerequisite=vd.get("prerequisite", ""),
                rationale=vd.get("rationale", ""),
            )
            for vd in data.get("violation_dependencies", [])
        ]
        preserved_invariants = [
            PreservedInvariant(
                invariant_id=pi.get("invariant_id", "INV-???"),
                category=pi.get("category", ""),
                description=pi.get("description", ""),
                evidence_value=pi.get("evidence_value", ""),
                status=pi.get("status", "PROVEN"),
                target=pi.get("target", ""),
                state=pi.get("state", "LOCKED"),
                mutation=pi.get("mutation", "FORBIDDEN"),
                provenance_evidence=pi.get("provenance_evidence"),
                regression_evidence=pi.get("regression_evidence"),
                ever_regressed=pi.get("ever_regressed", False),
                regression_count=pi.get("regression_count", 0),
                regression_history=pi.get("regression_history", []),
            )
            for pi in data.get("preserved_invariants", [])
        ]
        rb = data.get("repair_boundary", {})
        repair_boundary = RepairBoundary(
            allowed_changes=rb.get("allowed_changes", []),
            forbidden_changes=rb.get("forbidden_changes", []),
        )
        required_changes = [
            RequiredChange(
                change_id=rc.get("change_id", "REQ-???"),
                target=rc.get("target", ""),
                violation_ref=rc.get("violation_ref", ""),
                deterministic_requirement=rc.get("deterministic_requirement", ""),
                preserve_refs=rc.get("preserve_refs", []),
                forbidden_refs=rc.get("forbidden_refs", []),
            )
            for rc in data.get("required_changes", [])
        ]
        return cls(
            package_id=data.get("package_id", str(uuid.uuid4())),
            timestamp=data.get("timestamp", cls.make_timestamp()),
            validator=data.get("validator", ""),
            phase=data.get("phase", ""),
            validator_type=data.get("validator_type", "PHASE_END"),
            verdict=data.get("verdict", "FAIL"),
            causal_owner=data.get("causal_owner", "NONE"),
            failure_summary=data.get("failure_summary", ""),
            root_causes=data.get("root_causes", []),
            violations=violations,
            violation_dependencies=violation_dependencies,
            authoritative_context=data.get("authoritative_context", {}),
            active_constraints=data.get("active_constraints", {}),
            preserved_invariants=preserved_invariants,
            repair_boundary=repair_boundary,
            forbidden_changes=data.get("forbidden_changes", []),
            required_changes=required_changes,
            expected_post_repair_state=data.get("expected_post_repair_state", []),
            verification_criteria=data.get("verification_criteria", []),
            source_of_truth=data.get("source_of_truth", ""),
            evidence=data.get("evidence", []),
            remaining_budget=data.get("remaining_budget", 0),
            actionable_prescriptions=[
                ActionableRepairPrescription(
                    prescription_id=rx.get("prescription_id", "RX-???"),
                    evidence_ref=rx.get("evidence_ref", ""),
                    observed_failure=rx.get("observed_failure", ""),
                    oracle_call_site=rx.get("oracle_call_site", rx.get("causal_site", "")),
                    implementation_symbol=rx.get("implementation_symbol", rx.get("causal_site", "")),
                    evidence_basis=rx.get("evidence_basis", "DETERMINISTIC_RULE_INFERENCE"),
                    required_change=rx.get("required_change", ""),
                    repair_boundary_allowed=rx.get("repair_boundary_allowed", []),
                    repair_boundary_forbidden=rx.get("repair_boundary_forbidden", []),
                    expected_post_repair_state=rx.get("expected_post_repair_state", ""),
                    verification_evidence=rx.get("verification_evidence", ""),
                )
                for rx in data.get("actionable_prescriptions", [])
            ],
        )

    @classmethod
    def from_json(cls, json_str: str) -> "ContextualEvidencePackage":
        """Deserialisasi dari JSON string."""
        return cls.from_dict(json.loads(json_str))

    def compute_package_hash(self) -> str:
        """Menghitung SHA-256 dari konten paket bukti untuk integritas."""
        canonical = json.dumps(self.to_dict(), sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ===========================================================================
# 3. Markdown Renderer — Single-Unit Repair Directive
# ===========================================================================

_MAX_RENDER_CHARS = 7500   # Batas kompaktasi untuk num_ctx=8192 pada model 7B (parameter engineering terukur)

def _build_repair_directive_lines(
    pkg: ContextualEvidencePackage,
    include_raw_sandbox: bool = True,
    full_doctrine: bool = True,
    max_detailed_tests: int = 4,
) -> str:
    lines: List[str] = []

    _sep = "=" * 80
    header = (
        _sep + "\n"
        "[DETERMINISTIC CONTEXTUAL EVIDENCE PACKAGE — REPAIR DIRECTIVE]\n"
        + f"Validator: {pkg.validator} | Phase: {pkg.phase} | Causal Owner: {pkg.causal_owner}\n"
        + f"Verdict: {pkg.verdict} | Remaining Budget: {pkg.remaining_budget}\n"
        + f"Source of Truth: {pkg.source_of_truth}\n"
        + _sep
    )
    lines.append(header)

    # 1. Failure Summary (failure)
    lines.append("\n[1. DETERMINISTIC FACTS & FAILURE SUMMARY]")
    lines.append(pkg.failure_summary)

    # 1B. Deterministic Sandbox Failure Evidence (if available in evidence)
    sandbox_ev = None
    failing_tests_ev = None
    runtime_diag_ev = None
    for ev in getattr(pkg, "evidence", []):
        if isinstance(ev, dict):
            if ev.get("item") == "sandbox_failing_tests":
                failing_tests_ev = ev.get("observed")
            elif ev.get("item") == "sandbox_error_excerpt":
                sandbox_ev = ev.get("observed")
            elif ev.get("item") == "generic_runtime_diagnostic":
                runtime_diag_ev = ev.get("observed")

    if failing_tests_ev or sandbox_ev or runtime_diag_ev:
        lines.append("\n[DETERMINISTIC SANDBOX FAILURE EVIDENCE]")
        if failing_tests_ev and isinstance(failing_tests_ev, list):
            lines.append(f"Failing Tests ({len(failing_tests_ev)} failing):")
            detailed_tests = failing_tests_ev[:max_detailed_tests]
            for ft in detailed_tests:
                if isinstance(ft, dict):
                    tname = ft.get("test_name", "unknown")
                    ftype = ft.get("failure_type", "failure")
                    msg = ft.get("message", "")
                    lines.append(f"  ✗ {tname} [{ftype}]")
                    if msg:
                        lines.append(f"    Assertion / Message: {msg}")
                    exp = ft.get("expected")
                    act = ft.get("actual")
                    if exp or act:
                        lines.append(f"    Expected: {exp} | Actual: {act}")
                    sfile = ft.get("source_file")
                    sline = ft.get("source_line")
                    if sfile or sline:
                        lines.append(f"    Location: {sfile or ''}:{sline or ''}")
                    tb = ft.get("traceback_excerpt")
                    if tb and tb.strip() != msg.strip():
                        tb_clean = tb.strip()
                        if len(tb_clean) > 200:
                            tb_clean = tb_clean[:200] + "..."
                        lines.append(f"    Traceback: {tb_clean}")
            if len(failing_tests_ev) > max_detailed_tests:
                lines.append(f"  ... and {len(failing_tests_ev) - max_detailed_tests} more failing test(s)")

        if runtime_diag_ev and isinstance(runtime_diag_ev, list):
            lines.append("\nGeneric Runtime Diagnostics:")
            for diag in runtime_diag_ev[:3]:
                dtype = diag.get("type", "DIAGNOSTIC")
                lines.append(f"  • Type: {dtype}")
                if "status_code" in diag:
                    lines.append(f"    Status Code: {diag['status_code']}")
                if "response_body" in diag:
                    body_val = diag["response_body"]
                    body_str = json.dumps(body_val) if isinstance(body_val, (dict, list)) else str(body_val)
                    lines.append(f"    Response Body: {body_str[:300]}")
                if "validation_detail" in diag:
                    detail_val = diag["validation_detail"]
                    detail_str = json.dumps(detail_val) if isinstance(detail_val, (dict, list)) else str(detail_val)
                    lines.append(f"    Validation Detail: {detail_str[:300]}")
                if "exception_type" in diag:
                    lines.append(f"    Exception Type: {diag['exception_type']}")
                if "exception_message" in diag:
                    lines.append(f"    Exception Message: {diag['exception_message']}")
        if sandbox_ev and include_raw_sandbox:
            lines.append("\nRaw Test Runner Output Excerpt:")
            raw_s = str(sandbox_ev).strip()
            raw_lines = [l for l in raw_s.splitlines() if l.strip()]
            if len(raw_lines) > 8:
                compact_raw = "\n".join(raw_lines[:8]) + f"\n... [{len(raw_lines) - 8} more lines omitted for context efficiency]"
            else:
                compact_raw = "\n".join(raw_lines)
            if len(compact_raw) > 350:
                compact_raw = compact_raw[:350] + "... [truncated]"
            lines.append(compact_raw)

    # 2. Root Cause (causal evidence)
    lines.append("\n[2. DERIVED DETERMINISTIC DIAGNOSIS (ROOT CAUSE)]")
    for rc in pkg.root_causes:
        lines.append(f"- {rc}")

    # 3. Violations (causal evidence - complete global scan)
    lines.append(f"\n[3. COMPLETE VIOLATION ROSTER ({len(pkg.violations)} found — detect globally)]")
    for v in pkg.violations:
        sym = f" [symbol: {v.observed_symbol}]" if v.observed_symbol else ""
        lines.append(f"- [{v.violation_id}] [{v.severity}] {v.criterion} at {v.location}{sym}")
        lines.append(f"  OBSERVED: {v.observed_state}")
        lines.append(f"  EXPECTED: {v.expected_state}")
        lines.append(f"  DETECTOR: {v.source_detector}")

    # Violation dependencies (if any)
    if pkg.violation_dependencies:
        lines.append("\n  Violation Dependencies (fix in this order):")
        for vd in pkg.violation_dependencies:
            lines.append(f"  - Fix [{vd.prerequisite}] before [{vd.dependent_violation}]: {vd.rationale}")

    # 4. Actionable Repair Prescriptions (prescription - highest actionability)
    rx_list = getattr(pkg, "actionable_prescriptions", [])
    if rx_list:
        lines.append(f"\n[4. ACTIONABLE REPAIR PRESCRIPTIONS — DETERMINISTIC ({len(rx_list)} prescribed)]")
        for rx in rx_list:
            lines.append(f"- [{rx.prescription_id}] Ref: {rx.evidence_ref}")
            lines.append(f"  OBSERVED FAILURE: {rx.observed_failure}")
            lines.append(f"  ORACLE CALL SITE (FACT): {rx.oracle_call_site}")
            lines.append(f"  IMPLEMENTATION SYMBOL: {rx.implementation_symbol}")
            lines.append(f"  EVIDENCE BASIS: {rx.evidence_basis}")
            lines.append(f"  REQUIRED CHANGE (CONTRACT): {rx.required_change}")
            lines.append(f"  REPAIR BOUNDARY (ALLOWED): {', '.join(rx.repair_boundary_allowed)}")
            lines.append(f"  REPAIR BOUNDARY (FORBIDDEN): {', '.join(rx.repair_boundary_forbidden)}")
            lines.append(f"  EXPECTED POST-REPAIR STATE: {rx.expected_post_repair_state}")
            lines.append(f"  VERIFICATION EVIDENCE: {rx.verification_evidence}")

    # 5. Preserved Invariants (invariant - behavioral locks & regression watch)
    regressed_invariants = [inv for inv in pkg.preserved_invariants if getattr(inv, "status", "") == "REGRESSED"]
    locked_invariants = [inv for inv in pkg.preserved_invariants if getattr(inv, "status", "") != "REGRESSED"]

    if regressed_invariants:
        lines.append(f"\n[5A. CRITICAL REGRESSIONS DETECTED — FORMERLY PROVEN, NOW BROKEN ({len(regressed_invariants)} broken)]")
        for inv in regressed_invariants:
            lines.append(f"- [REGRESSION] [{inv.invariant_id}] [{inv.category}] {inv.description}")
            if inv.target:
                lines.append(f"  Target: {inv.target}")
            if inv.regression_evidence:
                lines.append(f"  Failure Evidence: {inv.regression_evidence}")
            lines.append(f"  Required Action: WAJIB PULIHKAN KONDISI INI! Jangan hapus atau ganti nama!")

    lines.append(f"\n[5. PRESERVED INVARIANTS & LOCKED INVARIANTS ({len(locked_invariants)} locked — ONCE PROVEN, LOCK IT)]")
    for inv in locked_invariants:
        reg_info = f" [PROVEN AGAIN — WITH PRIOR REGRESSION (count: {inv.regression_count})]" if getattr(inv, "ever_regressed", False) else ""
        lines.append(f"- [LOCKED]{reg_info} [{inv.invariant_id}] [{inv.category}] {inv.description}")
        if inv.target:
            lines.append(f"  Behavioral Target: {inv.target}")
        ev_str = str(inv.evidence_value)
        if len(ev_str) > 80:
            ev_str = ev_str[:80] + "..."
        lines.append(f"  Evidence: {ev_str}")
        lines.append(f"  Status: PROVEN (Mutation: CONDITION MUST REMAIN TRUE)")

    # 6. Engineering Doctrine (doctrine - mandatory for developer/executor)
    if getattr(pkg, "causal_owner", "") == "DEVELOPER" or getattr(pkg, "phase", "") in ("DEVELOPER", "EXECUTOR"):
        lines.append("\n[ENGINEERING DOCTRINE & COMPATIBILITY PRINCIPLES (MANDATORY)]")
        docs = ENGINEERING_DOCTRINE if full_doctrine else ENGINEERING_DOCTRINE[:2]
        for doc in docs:
            lines.append(f"- {doc}")

    # 7. Verification Criteria & Required Changes (verification)
    lines.append(f"\n[7. REQUIRED DETERMINISTIC CHANGES ({len(pkg.required_changes)} changes)]")
    for rc in pkg.required_changes:
        lines.append(f"- [{rc.change_id}] Target: {rc.target}")
        lines.append(f"  Violation Ref: {rc.violation_ref}")
        lines.append(f"  REQUIREMENT: {rc.deterministic_requirement}")
        if rc.preserve_refs:
            lines.append(f"  PRESERVE: {', '.join(rc.preserve_refs)}")
        if rc.forbidden_refs:
            lines.append(f"  FORBIDDEN: {', '.join(rc.forbidden_refs)}")

    lines.append("\n[EXPECTED POST-REPAIR STATE & VERIFICATION CRITERIA]")
    for s in pkg.expected_post_repair_state:
        lines.append(f"- {s}")
    lines.append("\n  Deterministic Verification Criteria:")
    for vc in pkg.verification_criteria:
        lines.append(f"  -> {vc}")

    # 8. Secondary Context: Repair Boundaries & Active Constraints
    lines.append("\n[8. REPAIR BOUNDARIES & ACTIVE CONSTRAINTS]")
    lines.append("ALLOWED CHANGES:")
    for ac in pkg.repair_boundary.allowed_changes:
        lines.append(f"  + {ac}")
    lines.append("FORBIDDEN CHANGES (DETERMINISTICALLY REJECTED IF VIOLATED):")
    for fc in pkg.repair_boundary.forbidden_changes:
        lines.append(f"  ! {fc}")

    lines.append("\nActive Runtime Constraints:")
    for k, val in pkg.active_constraints.items():
        lines.append(f"- {k}: {val}")

    auth = pkg.authoritative_context
    if auth:
        lines.append("\nAuthoritative Context:")
        for k, val in auth.items():
            if val:
                if isinstance(val, list):
                    val_str = ", ".join(str(x) for x in val)
                else:
                    val_str = str(val).strip()
                    if len(val_str) > 250:
                        val_str = val_str[:250] + "... [excerpt truncated]"
                lines.append(f"  - {k}: {val_str}")

    lines.append("\n" + _sep)
    return "\n".join(lines)


def render_repair_directive(pkg: ContextualEvidencePackage, max_chars: int = _MAX_RENDER_CHARS) -> str:
    """
    Menghasilkan satu unit Markdown terpadu yang diinjeksikan ke prompt causal owner.

    Urutan kanonikal linier penentu tindakan (Evidence Priority):
      1. Deterministic Facts & Failure Summary (failure)
      1B. Deterministic Sandbox Failure Evidence (failing tests, assertions, traceback)
      2. Derived Deterministic Diagnosis / Root Cause (causal evidence)
      3. Complete Violation Roster & Causal Evidence (causal evidence)
      4. Actionable Repair Prescriptions — Deterministic (prescription)
      5. Preserved Invariants & Behavioral Locks (invariant)
      6. Engineering Doctrine & Compatibility Principles (doctrine)
      7. Deterministic Verification & Required Changes (verification)
      8. Secondary Context: Repair Boundaries & Active Constraints

    Menggunakan strategi compactification bertingkat (multi-pass) agar Section 4
    (Actionable Prescriptions) dan Section 5 (Preserved Invariants) selalu terkirim utuh.
    """
    # Pass 1: Render standar terkompaksi (bounded raw excerpt & failing tests)
    text = _build_repair_directive_lines(pkg, include_raw_sandbox=True, full_doctrine=True, max_detailed_tests=4)
    if len(text) <= max_chars:
        return text

    # Pass 2: Jika melebihi max_chars, lepaskan raw excerpt sekunder dan ringkas doktrin
    # untuk memastikan Actionable Prescriptions dan Invariants tidak pernah terpotong
    text = _build_repair_directive_lines(pkg, include_raw_sandbox=False, full_doctrine=False, max_detailed_tests=2)
    if len(text) <= max_chars:
        return text

    # Pass 3: Fallback pemotongan ekor hanya jika max_chars diset ke batas artifisial sangat kecil
    _sep = "=" * 80
    suffix = "\n...(dipotong untuk efisiensi konteks)\n" + _sep
    return text[:max_chars - len(suffix)] + suffix


# ===========================================================================
# 4. Preservation Rule Checker
# ===========================================================================

def check_preservation_rule(
    original_pkg: ContextualEvidencePackage,
    revalidation_pkg: ContextualEvidencePackage,
) -> Dict[str, Any]:
    """
    Memeriksa apakah perbaikan memenuhi Preservation Rule secara deterministik.

    Repair hanya dinyatakan PASS jika:
    1. Seluruh original violations terselesaikan (tidak muncul lagi di revalidasi).
    2. Seluruh preserved invariants tetap valid (tidak ada regression).
    3. Tidak ada forbidden violation baru yang muncul.
    4. Revalidation verdict == PASS.

    Mengembalikan dict berisi:
      - preservation_passed: bool
      - resolved_violations: List[str]
      - unresolved_violations: List[str]
      - new_violations: List[str]
      - broken_invariants: List[str]
      - repair_outcome: "SUCCESS" | "UNRESOLVED" | "REGRESSED" | "FORBIDDEN_VIOLATION"
    """
    original_violation_ids = {v.violation_id for v in original_pkg.violations}
    remaining_violation_ids = {v.violation_id for v in revalidation_pkg.violations}
    new_violation_ids = remaining_violation_ids - original_violation_ids

    resolved = list(original_violation_ids - remaining_violation_ids)
    unresolved = list(original_violation_ids & remaining_violation_ids)
    new_violations = list(new_violation_ids)

    # Periksa invarian terselamatkan: jika verdict revalidasi PASS maka semua dianggap intact
    # (Python validator selalu memeriksa ulang invarian pada setiap scan)
    broken_invariants: List[str] = []
    if revalidation_pkg.verdict == "FAIL":
        # Cari pelanggaran yang berkaitan dengan kategori invarian
        inv_categories = {inv.category for inv in original_pkg.preserved_invariants}
        for v in revalidation_pkg.violations:
            if any(cat.lower() in v.criterion.lower() for cat in inv_categories):
                broken_invariants.append(v.violation_id)
        # Periksa juga jika ada invariant berstatus REGRESSED
        for inv in revalidation_pkg.preserved_invariants:
            if getattr(inv, "status", "") == "REGRESSED":
                if inv.invariant_id not in broken_invariants:
                    broken_invariants.append(inv.invariant_id)

    # Tentukan repair_outcome
    if revalidation_pkg.verdict == "PASS" and not broken_invariants:
        repair_outcome = "SUCCESS"
        preservation_passed = True
    elif broken_invariants:
        repair_outcome = "REGRESSED"
        preservation_passed = False
    elif new_violations:
        repair_outcome = "FORBIDDEN_VIOLATION"
        preservation_passed = False
    else:
        repair_outcome = "UNRESOLVED"
        preservation_passed = False

    return {
        "preservation_passed": preservation_passed,
        "resolved_violations": resolved,
        "unresolved_violations": unresolved,
        "new_violations": new_violations,
        "broken_invariants": broken_invariants,
        "repair_outcome": repair_outcome,
    }


# ===========================================================================
# 5. OTRR (One-Turn Repair Rate) Calculator
# ===========================================================================

def calculate_otrr(repair_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Menghitung One-Turn Repair Rate (OTRR) dari daftar catatan perbaikan.

    Formula:
      OTRR = jumlah kegagalan yang lulus pada putaran perbaikan pertama
             / jumlah seluruh kegagalan yang menerima perbaikan

    Setiap record dalam repair_records diharapkan memiliki:
      - failure_id: str
      - repairs: List[Dict] dengan field:
          - turn: int (1, 2, 3, ...)
          - outcome: "SUCCESS" | "UNRESOLVED" | "REGRESSED" | "FORBIDDEN_VIOLATION" | "BUDGET_EXHAUSTED"

    Mengembalikan:
      - total_failures_with_repair: int
      - first_turn_successes: int
      - otrr: float (0.0 – 1.0)
      - otrr_percent: float (0.0 – 100.0)
    """
    total = len(repair_records)
    first_turn_successes = 0

    for record in repair_records:
        repairs = record.get("repairs", [])
        if not repairs:
            continue
        first_repair = min(repairs, key=lambda r: r.get("turn", 999))
        if first_repair.get("outcome") == "SUCCESS" and first_repair.get("turn", 999) == 1:
            first_turn_successes += 1

    otrr = first_turn_successes / total if total > 0 else 0.0
    return {
        "total_failures_with_repair": total,
        "first_turn_successes": first_turn_successes,
        "otrr": round(otrr, 4),
        "otrr_percent": round(otrr * 100, 2),
    }
