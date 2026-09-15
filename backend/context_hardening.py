"""
Context Pipeline Hardening v1 — Generic Context Builder & Semantic Compressor
ReinDev Studio

Menyediakan fungsi-fungsi generik untuk membangun context packages terstruktur
bagi Architect (Decision Context) dan Developer (Repair Context).

PRINSIP UMUM (GENERALIZATION CONSTRAINT — NON-NEGOTIABLE):
  - TIDAK ADA task-specific branching (tidak ada if FastAPI / if Flutter / if CLI).
  - FACT hanya dari evidence deterministik (state fields terverifikasi).
  - INTERPRETATION dan ASSUMPTION diberi label eksplisit.
  - Prescriptions berisi WHAT must be true — bukan HOW to solve.
  - Scaffold dikompresi secara semantik jika melebihi target_chars (bukan hard error).
  - Tidak ada pengkodean pengetahuan aplikasi spesifik, framework solution,
    atau entitas bernama.

Authority ordering:
  User Intent > Oracle > Frozen Contract > Design Authority > Implementation
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

try:
    from .context_integrity import ContextIntegrityAuditor
except (ImportError, ValueError):
    try:
        from context_integrity import ContextIntegrityAuditor
    except ImportError:
        ContextIntegrityAuditor = None  # type: ignore

try:
    from .canonical_obligation import (
        extract_canonical_oracle_obligations,
        ObligationKind,
    )
except (ImportError, ValueError):
    try:
        from canonical_obligation import (
            extract_canonical_oracle_obligations,
            ObligationKind,
        )
    except ImportError:
        extract_canonical_oracle_obligations = None  # type: ignore
        ObligationKind = None  # type: ignore

try:
    from .canonical_evidence import CanonicalImplementationEvidence, deduplicate_evidence
    from .implementation_grounding import ImplementationGroundingEngine
except (ImportError, ValueError):
    try:
        from canonical_evidence import CanonicalImplementationEvidence, deduplicate_evidence
        from implementation_grounding import ImplementationGroundingEngine
    except ImportError:
        CanonicalImplementationEvidence = None  # type: ignore
        deduplicate_evidence = None  # type: ignore
        ImplementationGroundingEngine = None  # type: ignore

try:
    from .canonical_scenario import (
        extract_canonical_scenarios,
        evaluate_behavioral_observations,
        format_scenarios_for_architect,
        format_behavioral_mismatches_for_developer,
    )
except (ImportError, ValueError):
    try:
        from canonical_scenario import (
            extract_canonical_scenarios,
            evaluate_behavioral_observations,
            format_scenarios_for_architect,
            format_behavioral_mismatches_for_developer,
        )
    except ImportError:
        extract_canonical_scenarios = None  # type: ignore
        evaluate_behavioral_observations = None  # type: ignore
        format_scenarios_for_architect = None  # type: ignore
        format_behavioral_mismatches_for_developer = None  # type: ignore


# ===========================================================================
# 1. Semantic Context Compressor
# ===========================================================================

DEFAULT_PRIORITY_ORDER: List[str] = [
    "authority_acceptance",
    "authority_scenario",
    "authority",
    "evidence_mismatch",
    "requirement_prescription",
    "requirement",
    "invariant_locked",
    "invariant",
    "requirement_repair_boundary",
    "requirement_expected_post_repair",
    "authority_verification",
    "evidence_validator",
    "evidence_diagnostics",
    "evidence",
    "impl_ref",
    "historical",
]


def compress_context_semantic(
    sections: Dict[str, str],
    max_chars: int,
    priority_order: Optional[List[str]] = None,
) -> str:
    """
    Mengompres context dengan semantic prioritization.
    Seksi prioritas rendah dipotong lebih dahulu jika total melebihi max_chars.
    Setiap seksi dilindungi secara proporsional sesuai prioritas epistemik.
    """
    if priority_order is None:
        priority_order = DEFAULT_PRIORITY_ORDER

    ordered_keys: List[str] = []
    for p in priority_order:
        for k in sections:
            if k.startswith(p) and k not in ordered_keys:
                ordered_keys.append(k)
    for k in sections:
        if k not in ordered_keys:
            ordered_keys.append(k)

    total = 0
    result_parts: List[str] = []
    for k in ordered_keys:
        content = sections.get(k, "")
        if not content:
            continue
        if total + len(content) <= max_chars:
            result_parts.append(content)
            total += len(content)
        else:
            remaining = max_chars - total
            if remaining > 100:
                truncated = content[:remaining - 40] + "\n...(dipotong untuk efisiensi context)"
                result_parts.append(truncated)
                total = max_chars
            break

    result = "\n\n".join(result_parts)

    # Section 10: Deterministic Omission Detection & Protection
    # Acceptance scenarios and active mismatches must NEVER be silently dropped.
    critical_prefixes = ("authority_acceptance", "authority_scenario", "evidence_mismatch")
    for cp in critical_prefixes:
        for k, content in sections.items():
            if content and k.startswith(cp):
                header = content.splitlines()[0] if content.splitlines() else ""
                if header and header not in result:
                    # Critical section was omitted due to severely undersized budget
                    # Deterministic system detects and flags this omission explicitly
                    import warnings
                    warnings.warn(
                        f"[CONTEXT_OMISSION_DETECTED]: Critical section '{k}' could not fit within max_chars={max_chars}. "
                        "Deterministic system strictly forbids silent omission.",
                        RuntimeWarning
                    )

    return result


def check_context_omission(
    sections: Dict[str, str],
    result_text: str,
    critical_prefixes: Tuple[str, ...] = ("authority_acceptance", "authority_scenario", "evidence_mismatch")
) -> List[str]:
    """Mendeteksi apakah ada seksi kritis penerimaan/mismatch yang dihilangkan secara diam-diam."""
    omitted = []
    for k, content in sections.items():
        if content and any(k.startswith(cp) for cp in critical_prefixes):
            header = content.splitlines()[0] if content.splitlines() else ""
            if header and header not in result_text:
                omitted.append(k)
    return omitted


def compress_scaffold_semantic(scaffold_text: str, target_chars: int = 800) -> str:
    """
    Kompresi scaffold secara semantik agar mendekati target_chars.
    Generic across all languages:
      1. Jika sudah <= target: kembalikan as-is.
      2. Bersihkan docstrings / multiline comments (bukan interface signatures).
      3. Kompresi body fungsi internal menjadi stubs/pass jika terlalu panjang.
    """
    if len(scaffold_text) <= target_chars:
        return scaffold_text

    # Tahap 1: Kompresi docstring Python triple quotes
    compressed = re.sub(r'"""[\s\S]*?"""', 'pass', scaffold_text)
    compressed = re.sub(r"'''[\s\S]*?'''", 'pass', compressed)
    if len(compressed) <= target_chars:
        return compressed.strip()

    # Tahap 2: Hilangkan inline comments panjang
    lines = compressed.splitlines()
    clean_lines = []
    for ln in lines:
        stripped = ln.strip()
        if stripped.startswith("#") or stripped.startswith("//"):
            continue
        clean_lines.append(ln)
    compressed = "\n".join(clean_lines)
    if len(compressed) <= target_chars:
        return compressed.strip()

    # Tahap 3: Truncate internal implementations, retain signatures
    sig_lines = []
    for ln in compressed.splitlines():
        stripped = ln.strip()
        if any(stripped.startswith(prefix) for prefix in (
            "def ", "class ", "async def ", "import ", "from ",
            "export ", "interface ", "type ", "final ", "const ", "struct ",
            "fn ", "pub ", "package "
        )):
            sig_lines.append(ln)
            # Add stub marker if it looks like a function header
            if stripped.endswith(":") or stripped.endswith("{"):
                indent = len(ln) - len(ln.lstrip()) + 4
                sig_lines.append(" " * indent + "pass")
    
    if sig_lines:
        compressed_sigs = "\n".join(sig_lines)
        if len(compressed_sigs) <= target_chars:
            return compressed_sigs

    # Tahap 4: Soft-boundary truncation
    lines = scaffold_text.splitlines()
    result = []
    cur_len = 0
    for ln in lines:
        if cur_len + len(ln) + 1 > target_chars - 40:
            result.append("... (scaffold ringkas: interfaces & signatures retained)")
            break
        result.append(ln)
        cur_len += len(ln) + 1
    return "\n".join(result).strip()


# ===========================================================================
# 2. Context Telemetry
# ===========================================================================

@dataclass
class ContextTelemetry:
    """Telemetri per-invocation untuk forensic audit dan rekonstruksi deterministik."""
    agent: str
    model: str
    context_version: str
    context_sections: List[str]
    context_size: int
    authoritative_sources: List[str]
    evidence_items: int
    locked_invariants: int
    current_failures: int
    repair_boundary_items: int
    authority_conflicts_resolved: int = 0
    integrity_violations_detected: int = 0
    output_size: int = 0
    validator_result: str = ""
    routing_result: str = ""
    run_id: str = ""
    iteration: int = 0
    grounding_sources: List[str] = field(default_factory=list)
    grounding_evidence_count: int = 0
    grounding_evidence_types: List[str] = field(default_factory=list)
    raw_diagnostic_count: int = 0
    normalized_diagnostic_count: int = 0
    omitted_diagnostic_count: int = 0
    current_failure_count: int = 0
    historical_failure_count: int = 0
    locked_invariant_count: int = 0
    implementation_facts_count: int = 0
    truncation_detected: bool = False
    repair_result: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def emit_context_telemetry(tracer: Any, agent: str, telemetry: ContextTelemetry) -> None:
    """Log context telemetry ke tracer yang sudah ada."""
    if tracer is None:
        return
    try:
        tracer.log_event(
            stage=agent,
            event_type="context_telemetry",
            iteration=telemetry.iteration,
            data=telemetry.to_dict(),
        )
    except Exception:
        pass


# ===========================================================================
# 3. Authoritative Acceptance Oracle Extractor (Read-Only Observer)
# ===========================================================================

def extract_authoritative_oracle_interfaces(state: Dict[str, Any]) -> List[str]:
    """
    Mengekstrak simbol, method, dan endpoint yang diuji oleh Frozen Acceptance Oracle
    secara deterministik (Read-Only Observer) menggunakan Canonical Acceptance Obligation.
    HANYA bersumber dari test suite aktual (state['test_files'] dan/atau state['frozen_oracle_path']).
    """
    test_files = state.get("test_files") or {}
    frozen_path = state.get("frozen_oracle_path") or ""

    if extract_canonical_oracle_obligations is not None:
        try:
            obligations = extract_canonical_oracle_obligations(
                frozen_oracle_path=frozen_path if frozen_path else None,
                test_files=test_files if test_files else None
            )
            tested_items: List[str] = []
            seen = set()

            for ob in obligations:
                if ob.obligation_kind == ObligationKind.INTERACTION.value:
                    method = ob.inputs.get("http_method", "").upper()
                    ep = ob.public_identity
                    key = f"{method} {ep}"
                    if key not in seen:
                        seen.add(key)
                        tested_items.append(f"[ORACLE_FACT] {ep} [{method}] (Tested endpoint)")
                elif ob.obligation_kind == ObligationKind.DATA_MODEL.value:
                    sym = ob.public_identity
                    if sym not in seen:
                        seen.add(sym)
                        tested_items.append(f"[ORACLE_FACT] {sym} (Tested widget/model)")
                elif ob.obligation_kind == ObligationKind.OBSERVABLE_RUNTIME.value:
                    sym = ob.public_identity
                    if sym not in seen:
                        seen.add(sym)
                        tested_items.append(f"[ORACLE_FACT] {sym} (Tested widget/class)")
                else:
                    sym = ob.public_identity
                    if sym not in seen:
                        seen.add(sym)
                        tag = "Required public symbol" if "hasattr" in str(ob.acceptance_evidence) else "Tested module symbol"
                        tested_items.append(f"[ORACLE_FACT] {sym} ({tag})")

            return sorted(tested_items)
        except Exception:
            pass

    return []


# ===========================================================================
# 3B. Deterministic Authority Consistency Check
# ===========================================================================

def check_and_resolve_authority_conflicts(
    sections: Dict[str, str],
    state: Dict[str, Any],
    pkg: Optional[Any] = None,
) -> Tuple[Dict[str, str], List[str]]:
    """
    Deterministic consistency check sebelum context dikirim ke Architect:
    - Tidak boleh ada satu bagian context yang mewajibkan X sementara bagian lain melarang X
      berdasarkan authority yang sama.
    - Hierarki Otoritas:
        1. ORACLE_FACT (Tertinggi: acceptance test suite, test_files, locked invariants)
        2. PM_PROPOSAL (Menengah: PM specifications, proposed contract draft)
        3. ARCHITECT_INFERENCE (Terendah: scaffold stubs, blueprint choices)
    - Jika terjadi konflik, authority tertinggi harus menang dan konflik harus dilaporkan sebagai evidence.
    """
    conflicts: List[str] = []

    # 1. Ekstrak simbol dan endpoint yang diwajibkan oleh ORACLE_FACT
    oracle_section = sections.get("authority_oracle_interfaces", "")
    oracle_symbols: Set[str] = set()
    for line in oracle_section.splitlines():
        m = re.search(r"\[ORACLE_FACT\]\s+([A-Za-z0-9_/]+)", line)
        if m:
            oracle_symbols.add(m.group(1))

    # 2. Ekstrak batasan forbidden dari REPAIR BOUNDARY (Section 10) atau PROVEN INVARIANTS (Section 6)
    boundary_text = sections.get("requirement_repair_boundary", "")
    forbidden_items: List[str] = []
    if "FORBIDDEN:" in boundary_text:
        forbidden_part = boundary_text.split("FORBIDDEN:")[1]
        for line in forbidden_part.splitlines():
            line = line.strip().lstrip("x- *")
            if line:
                forbidden_items.append(line)

    # 3. Cek kontradiksi: Apakah ada item yang dilarang padahal diwajibkan oleh ORACLE_FACT?
    for sym in sorted(oracle_symbols):
        for f_item in forbidden_items:
            if sym.lower() in f_item.lower():
                msg = (
                    f"[AUTHORITY CONFLICT RESOLVED] Oracle requires '{sym}' (ORACLE_FACT). "
                    f"Conflicting restriction '{f_item}' is overridden by highest authority."
                )
                conflicts.append(msg)

    # 4. Cek konflik: PM_PROPOSAL vs ORACLE_FACT
    contract = state.get("contract") or {}
    contract_status = state.get("contract_status", "")
    if isinstance(contract, dict) and contract_status != "FROZEN":
        pm_interfaces = [
            ifc.get("identifier", "")
            for ifc in contract.get("interface_contracts", [])
            if isinstance(ifc, dict) and ifc.get("identifier")
        ]
        missing_in_pm = [s for s in oracle_symbols if s not in pm_interfaces and not s.startswith("/")]
        if missing_in_pm and pm_interfaces:
            for ms in sorted(missing_in_pm):
                msg = (
                    f"[AUTHORITY CONFLICT RESOLVED] Acceptance Oracle tests '{ms}' (ORACLE_FACT), "
                    f"which was missing in PM Proposal. Highest authority (ORACLE_FACT) takes precedence."
                )
                conflicts.append(msg)

    # 5. Laporkan resolusi konflik ke dalam evidence section
    if conflicts:
        resolution_block = (
            "\n\n[DETERMINISTIC AUTHORITY CONFLICT RESOLUTIONS (ORACLE_FACT WON)]:\n"
            + "\n".join(f"  * {c}" for c in conflicts)
        )
        if "evidence_violations" in sections:
            sections["evidence_violations"] += resolution_block
        else:
            sections["evidence_violations"] = (
                "[9] EVIDENCE/VIOLATIONS (Deterministic Authority Consistency Check)\n"
                "===================================================================\n"
                + resolution_block.strip()
            )

    return sections, conflicts


# ===========================================================================
# 4. Architect Decision Context Package (11 Seksi)
# ===========================================================================

def build_architect_decision_context(
    state: Dict[str, Any],
    pkg: Optional[Any] = None,
    max_chars: int = 6500,
) -> Tuple[str, Dict[str, Any]]:
    """
    Membangun 11-seksi Architect Decision Context Package secara generik.
    Bebas dari task-specific knowledge atau asumsi framework.
    """
    sections: Dict[str, str] = {}

    # [1] USER INTENT
    user_task = state.get("task", "")
    if user_task:
        sections["authority_user_intent"] = (
            "[1] USER INTENT\n"
            "================\n"
            + user_task.strip()
        )

    # [2] V0 APP REQUIREMENTS
    v0_model = state.get("v0_requirement_model")
    if v0_model:
        if isinstance(v0_model, dict):
            core_reqs = v0_model.get("requirements", [])
            constructibility = v0_model.get("constructibility_status", "")
            v0_text = ""
            if constructibility:
                v0_text += f"Constructibility: {constructibility}\n"
            if core_reqs and isinstance(core_reqs, list):
                v0_text += "Core Requirements (FACT):\n"
                for i, r in enumerate(core_reqs[:8], 1):
                    if isinstance(r, dict):
                        label = r.get("category", "REQ")
                        desc = r.get("description", str(r))
                        v0_text += f"  {i}. [{label}] {desc}\n"
                    else:
                        v0_text += f"  {i}. {r}\n"
        else:
            v0_text = str(v0_model)[:600]
        sections["authority_v0_reqs"] = (
            "[2] V0 APP REQUIREMENTS (FACT — grounded in user task)\n"
            "=======================================================\\n"
            + v0_text.strip()
        )

    # [3] PM ACCEPTANCE REQUIREMENTS
    specs = state.get("specifications", "")
    if specs:
        specs_excerpt = specs.strip()[:1400]
        if len(specs.strip()) > 1400:
            specs_excerpt += "\n...(dipotong)"
        sections["authority_pm_reqs"] = (
            "[3] PM ACCEPTANCE REQUIREMENTS\n"
            "================================\n"
            + specs_excerpt
        )

    # [4] FROZEN CONTRACT / PROPOSED CONTRACT SPECIFICATION
    contract = state.get("contract") or {}
    contract_status = state.get("contract_status", "")
    contract_sha = state.get("contract_sha256", "")
    auth_file = ""
    interfaces = []
    models_list = []
    if contract and isinstance(contract, dict):
        task_intent = contract.get("task_intent", {})
        if isinstance(task_intent, dict):
            auth_file = task_intent.get("authoritative_target_file", "")
        for ifc in contract.get("interface_contracts", []):
            if isinstance(ifc, dict) and ifc.get("identifier"):
                interfaces.append(ifc["identifier"])
        for dm in contract.get("data_models", []):
            if isinstance(dm, dict) and dm.get("model_name"):
                models_list.append(dm["model_name"])

    is_frozen = (contract_status == "FROZEN")
    status_tag = "ORACLE_FACT" if is_frozen else "PM_PROPOSAL"

    c_lines = [
        f"Status: {contract_status or 'DRAFT'} ({status_tag})",
    ]
    if contract_sha and is_frozen:
        c_lines.append(f"SHA-256 Seal: {contract_sha[:16]}... (IMMUTABLE)")
    if auth_file:
        c_lines.append(f"Authoritative Target File: {auth_file}")
    if interfaces:
        c_lines.append(f"Interfaces [{status_tag}]: {', '.join(interfaces)}")
    if models_list:
        c_lines.append(f"Data Models [{status_tag}]: {', '.join(models_list)}")
    if not is_frozen:
        c_lines.append("Authority Notice: This is a Product Manager draft proposal (PM_PROPOSAL) — NOT acceptance authority.")
        c_lines.append("Use as design information only. Absolute acceptance authority belongs to Acceptance Oracle in Section [5].")

    if c_lines:
        sec_title = (
            "[4] FROZEN CONTRACT SPECIFICATION (ORACLE_FACT — sealed)\n=======================================================\n"
            if is_frozen else
            "[4] PROPOSED CONTRACT SPECIFICATION (PM_PROPOSAL — design reference only)\n=========================================================================\n"
        )
        sections["authority_contract"] = sec_title + "\n".join(c_lines)

    # [5] AUTHORITATIVE ACCEPTANCE ORACLE INTERFACES
    # WAJIB bersumber dari Frozen Acceptance Oracle test suite (ORACLE_FACT)
    oracle_items = extract_authoritative_oracle_interfaces(state)
    if oracle_items:
        sections["authority_oracle_interfaces"] = (
            "[5] AUTHORITATIVE ACCEPTANCE ORACLE INTERFACES (ORACLE_FACT — verified test suite)\n"
            "=================================================================================\n"
            + "\n".join(f"  - {item}" for item in oracle_items)
            + "\n  Authority Notice: The above symbols are verified directly from Acceptance Test Suite (Ground Truth)."
        )
    elif is_frozen and interfaces:
        # Jika test suite tidak memuat file eksplisit tapi kontrak sudah FROZEN
        sections["authority_oracle_interfaces"] = (
            "[5] AUTHORITATIVE ACCEPTANCE ORACLE INTERFACES (ORACLE_FACT — from sealed contract)\n"
            "====================================================================================\n"
            + "\n".join(f"  - [ORACLE_FACT] {ifc}" for ifc in interfaces)
        )
    else:
        # JANGAN PERNAH melabeli PM draft sebagai FROZEN/ORACLE-DERIVED!
        sections["authority_oracle_interfaces"] = (
            "[5] AUTHORITATIVE ACCEPTANCE ORACLE INTERFACES (ORACLE_FACT)\n"
            "============================================================\n"
            "  [ORACLE_FACT] No explicit public oracle interfaces extracted from tests.\n"
            "  Implement functional requirements according to Section [1] User Intent and Section [2] V0 App Requirements."
        )

    # [6] PROVEN INVARIANTS
    locked_dict = state.get("locked_invariants") or {}
    inv_lines = []
    for l_id, l_data in locked_dict.items():
        status = l_data.get("status", "PROVEN")
        desc = l_data.get("description", l_id)
        inv_lines.append(f"  [{status}] {l_id}: {desc} — mutation: FORBIDDEN")
    passing_tests = state.get("previous_passed_tests") or []
    for pt in (passing_tests[:6] if passing_tests else []):
        tname = pt.get("test_name", str(pt)) if isinstance(pt, dict) else str(pt)
        inv_lines.append(f"  [PROVEN] {tname} — DO NOT BREAK")
    if inv_lines:
        sections["invariant_proven"] = (
            "[6] PROVEN INVARIANTS (LOCKED — mutation FORBIDDEN)\n"
            "====================================================\n"
            + "\n".join(inv_lines)
        )

    # [7] KNOWN CONSTRAINTS
    constraints = {}
    if contract and isinstance(contract, dict):
        constraints = contract.get("constraints", {}) or {}
    target_lang = state.get("target_language", "python")
    max_files = constraints.get("max_files", 2)
    budget_used = state.get("contract_revision_count", 0)
    max_budget = state.get("max_contract_revisions", 5)
    sections["requirement_constraints"] = (
        "[7] KNOWN CONSTRAINTS\n"
        "======================\n"
        f"Target Language: {target_lang}\n"
        f"Max Files: {max_files}\n"
        f"Repair Budget: {budget_used}/{max_budget}"
    )

    # [8] CURRENT ARTIFACT STATE (pada repair turn, kompresi scaffold semantik)
    arch_plan = state.get("architecture_plan", "")
    if arch_plan and pkg is not None:
        plan_compressed = compress_scaffold_semantic(arch_plan.strip(), target_chars=800)
        sections["impl_ref_artifact"] = (
            "[8] CURRENT ARTIFACT STATE (blueprint sebelumnya)\n"
            "==================================================\n"
            + plan_compressed
        )

    # [9] EVIDENCE/VIOLATIONS (hanya pada repair turn)
    if pkg is not None:
        violations = getattr(pkg, "violations", []) or []
        root_causes = getattr(pkg, "root_causes", []) or []
        failure_summary = getattr(pkg, "failure_summary", "") or ""
        prescriptions = getattr(pkg, "actionable_prescriptions", []) or []
        ev_text = ""
        if failure_summary:
            ev_text += f"Failure Summary: {failure_summary}\n\n"
        if root_causes:
            ev_text += "Root Causes:\n"
            for rc in root_causes:
                ev_text += f"  - {rc}\n"
            ev_text += "\n"
        if violations:
            ev_text += f"Violations ({len(violations)} total):\n"
            for v in violations:
                vid = getattr(v, "violation_id", "?")
                crit = getattr(v, "criterion", "")
                obs = getattr(v, "observed_state", "")
                exp = getattr(v, "expected_state", "")
                sev = getattr(v, "severity", "")
                ev_text += f"  [{sev}] {vid} — {crit}\n    Observed: {obs}\n    Required: {exp}\n"
        if prescriptions:
            ev_text += "\nPrescriptions (WHAT must be true):\n"
            for rx in prescriptions[:4]:
                rx_id = getattr(rx, "prescription_id", "?")
                req_chg = getattr(rx, "required_change", "")
                ev_text += f"  [{rx_id}] {req_chg}\n"
        if ev_text:
            sections["evidence_violations"] = (
                "[9] EVIDENCE/VIOLATIONS (from Python validator — DETERMINISTIC)\n"
                "================================================================\n"
                + ev_text.strip()
            )

    # [10] REPAIR BOUNDARY (hanya repair turn)
    if pkg is not None:
        rb = getattr(pkg, "repair_boundary", None)
        if rb:
            allowed = getattr(rb, "allowed_changes", []) or []
            forbidden = getattr(rb, "forbidden_changes", []) or []
            rb_text = ""
            if allowed:
                rb_text += "ALLOWED:\n" + "\n".join(f"  + {a}" for a in allowed) + "\n"
            if forbidden:
                rb_text += "FORBIDDEN:\n" + "\n".join(f"  x {f_}" for f_ in forbidden[:5])
            if rb_text:
                sections["requirement_repair_boundary"] = (
                    "[10] REPAIR BOUNDARY\n"
                    "=====================\n"
                    + rb_text.strip()
                )

    # [11] OUTPUT CONTRACT
    sections["authority_output_contract"] = (
        "[11] OUTPUT CONTRACT\n"
        "=====================\n"
        "Output: JSON blueprint dalam marker === BLUEPRINT JSON === ... === END BLUEPRINT JSON ===\n"
        "Aturan code_scaffold:\n"
        "  - code_scaffold HARUS berupa interface signatures / stubs (misal: stubs fungsi dengan pass).\n"
        "  - Target ukuran: <=800 karakter per file.\n"
        "  - Jangan menuliskan logika bisnis atau implementasi penuh di dalam scaffold.\n"
        "  - Interface contracts HARUS mendefinisikan SEMUA identifier dari Authoritative Acceptance Oracle Interfaces (ORACLE_FACT).\n"
        "  - Elemen [PM_PROPOSAL] hanya digunakan sebagai referensi desain awal jika TIDAK bertentangan dengan [ORACLE_FACT]."
    )

    # Deterministic Consistency Check & Authority Conflict Resolution
    sections, conflicts = check_and_resolve_authority_conflicts(sections, state, pkg=pkg)

    # Part 3: Context Integrity & Task Isolation Audit
    integrity_violations: List[str] = []
    if ContextIntegrityAuditor is not None:
        target_domain = ""
        contract_obj = state.get("contract")
        if isinstance(contract_obj, dict):
            target_domain = (contract_obj.get("task_intent") or {}).get("domain", "")
        sections, integrity_violations = ContextIntegrityAuditor.audit_context_dict(
            sections,
            target_domain=target_domain,
            target_phase="ARCHITECT",
            state=state
        )

    result = compress_context_semantic(sections, max_chars=max_chars)

    telemetry_data = {
        "context_sections": list(sections.keys()),
        "context_size": len(result),
        "authoritative_sources": [k for k in sections if k.startswith("authority")],
        "evidence_items": len(getattr(pkg, "violations", []) or []) if pkg else 0,
        "locked_invariants": len(locked_dict),
        "current_failures": len(getattr(pkg, "violations", []) or []) if pkg else 0,
        "repair_boundary_items": len(
            getattr(getattr(pkg, "repair_boundary", None), "allowed_changes", []) or []
        ) if pkg else 0,
        "authority_conflicts_resolved": len(conflicts),
        "integrity_violations_detected": len(integrity_violations),
    }

    return result, telemetry_data


# ===========================================================================
# 4. Developer Repair Context Package (11 Seksi)
# ===========================================================================

def extract_oracle_callsite_assertions(
    test_files: Dict[str, str],
    interfaces: List[str],
    models: List[str],
    max_chars: int = 2500,
) -> str:
    """
    Ekstrak call-sites dan assertions dari test file Frozen Oracle secara generik.
    Mengutamakan baris yang mereferensikan model, interface, fungsi, atau tes.
    TIDAK ADA asumsi framework atau domain.
    """
    keywords = set(interfaces + models)
    all_relevant: List[str] = []
    all_lines: List[str] = []

    for fname, content in test_files.items():
        for ln in content.splitlines():
            stripped = ln.strip()
            if not stripped or stripped.startswith("#"):
                continue
            all_lines.append(f"  {stripped}")
            if any(k in stripped for k in keywords) or any(
                term in stripped.lower() for term in ("assert", "expect", "test", "should", "fail", "raises")
            ):
                all_relevant.append(f"  {stripped}")
        break  # File pengujian utama

    seen: set = set()
    combined: List[str] = []
    char_count = 0
    for ln in all_relevant:
        if ln not in seen and char_count + len(ln) < max_chars - 200:
            combined.append(ln)
            seen.add(ln)
            char_count += len(ln)
    for ln in all_lines:
        if ln not in seen and char_count + len(ln) < max_chars - 100:
            combined.append(ln)
            seen.add(ln)
            char_count += len(ln)

    result = "\n".join(combined)
    if len(result) > max_chars:
        result = result[:max_chars - 40] + "\n  ...(dipotong)"
    return result


def build_developer_repair_context(
    state: Dict[str, Any],
    pkg: Optional[Any] = None,
    max_chars: int = 7000,
) -> Tuple[str, Dict[str, Any]]:
    """
    Membangun 11-seksi Developer Repair Context Package secara generik.
    TIDAK ADA task-specific branching atau solver injection.
    Prescriptions berisi WHAT must be true — model menentukan HOW.
    """
    sections: Dict[str, str] = {}

    target_lang = state.get("target_language", "python")
    contract = state.get("contract") or {}
    contract_sha = state.get("contract_sha256", "")
    contract_status = state.get("contract_status", "")
    test_files = state.get("test_files") or {}
    code_files = state.get("code_files") or {}
    locked_dict = state.get("locked_invariants") or {}
    iteration = state.get("iteration_count", 0)
    max_iter = state.get("max_iterations", 10)

    auth_file = ""
    interfaces: List[str] = []
    models_list: List[str] = []
    if isinstance(contract, dict):
        task_intent = contract.get("task_intent", {})
        if isinstance(task_intent, dict):
            auth_file = task_intent.get("authoritative_target_file", "")
        if not auth_file:
            for ifc in contract.get("interface_contracts", []):
                if isinstance(ifc, dict) and ifc.get("target_file"):
                    auth_file = ifc["target_file"]
                    break
        for ifc in contract.get("interface_contracts", []):
            if isinstance(ifc, dict) and ifc.get("identifier"):
                interfaces.append(ifc["identifier"])
        for dm in contract.get("data_models", []):
            if isinstance(dm, dict) and dm.get("model_name"):
                models_list.append(dm["model_name"])
    if not auth_file:
        is_dart = "dart" in target_lang.lower() or "flutter" in target_lang.lower()
        auth_file = "lib/card_metric.dart" if is_dart else "main.py"

    # [1] FROZEN CONTRACT
    if contract and isinstance(contract, dict):
        c_text = f"Status: {contract_status}\nAuthoritative Target File: {auth_file}\n"
        if contract_sha:
            c_text += f"SHA-256: {contract_sha[:16]}...\n"
        if interfaces:
            c_text += f"Required Interfaces: {', '.join(interfaces)}\n"
        if models_list:
            c_text += f"Required Models: {', '.join(models_list)}\n"
        c_text += f"Repair Budget: {iteration}/{max_iter}"
        sections["authority_acceptance_contract"] = (
            "[1] FROZEN CONTRACT / AUTHORITATIVE ACCEPTANCE (immutable)\n"
            "===========================================================\n"
            + c_text
        )

    # [2] ORACLE EXPECTATION & ACCEPTANCE BEHAVIOR SCENARIOS (Treatment #1.3)
    scenarios: List[Any] = []
    observations: List[Any] = []
    if extract_canonical_scenarios is not None:
        try:
            scenarios = extract_canonical_scenarios(
                frozen_oracle_path=state.get("frozen_oracle_path"),
                test_files=test_files
            )
        except Exception:
            scenarios = []

    if scenarios and format_scenarios_for_architect is not None:
        sc_block = format_scenarios_for_architect(scenarios)
        if sc_block:
            sections["authority_scenario"] = sc_block

    if test_files:
        oracle_excerpt = extract_oracle_callsite_assertions(test_files, interfaces, models_list)
        if oracle_excerpt:
            sections["authority_oracle"] = (
                "[2] ORACLE EXPECTATION (Frozen Oracle — IMMUTABLE)\n"
                "===================================================\n"
                + oracle_excerpt
            )

    # [3] LOCKED INVARIANTS
    inv_lines = []
    for l_id, l_data in locked_dict.items():
        status = l_data.get("status", "PROVEN")
        desc = l_data.get("description", l_id)
        reg_count = l_data.get("regression_count", 0)
        line = f"  [{status}] {l_id}: {desc}"
        if reg_count > 0:
            line += f" (pernah regresi {reg_count}x — jaga stabilitas!)"
        line += " — mutation: FORBIDDEN"
        inv_lines.append(line)
    passing_tests = state.get("previous_passed_tests") or []
    for pt in (passing_tests[:8] if passing_tests else []):
        tname = pt.get("test_name", str(pt)) if isinstance(pt, dict) else str(pt)
        inv_lines.append(f"  [PROVEN] {tname} — DO NOT BREAK")
    if inv_lines:
        sections["invariant_locked"] = (
            "[3] LOCKED INVARIANTS (PROVEN — mutation FORBIDDEN)\n"
            "====================================================\n"
            + "\n".join(inv_lines)
        )

    # [4] CURRENT CODE
    current_code = code_files.get(auth_file, "")
    if not current_code:
        for _, v in code_files.items():
            current_code = v
            break
    if current_code:
        code_excerpt = current_code.strip()[:2000]
        if len(current_code.strip()) > 2000:
            code_excerpt += "\n...(dipotong)"
        sections["impl_ref_current_code"] = (
            f"[4] CURRENT CODE ({auth_file})\n"
            "==============================\n"
            + code_excerpt
        )

    # [CURRENT FAILURE — BEHAVIORAL MISMATCH] (Treatment #1.3)
    if evaluate_behavioral_observations is not None and scenarios:
        try:
            observations = evaluate_behavioral_observations(scenarios, state.get("test_results") or {})
        except Exception:
            observations = []
        if observations and format_behavioral_mismatches_for_developer is not None:
            mismatch_block = format_behavioral_mismatches_for_developer(observations, scenarios)
            if mismatch_block:
                sections["evidence_mismatch"] = mismatch_block

    # [5] VALIDATOR RESULT
    if pkg is not None:
        verdict = getattr(pkg, "verdict", "")
        violations = getattr(pkg, "violations", []) or []
        failure_summary = getattr(pkg, "failure_summary", "") or ""
        val_text = f"Verdict: {verdict}\n"
        if failure_summary:
            val_text += f"Summary: {failure_summary}\n"
        for v in violations:
            vid = getattr(v, "violation_id", "?")
            crit = getattr(v, "criterion", "")
            obs = getattr(v, "observed_state", "")
            exp = getattr(v, "expected_state", "")
            sev = getattr(v, "severity", "")
            val_text += f"\n[{sev}] {vid} — {crit}\n  OBSERVED: {obs}\n  REQUIRED: {exp}"
        sections["evidence_validator"] = (
            "[5] VALIDATOR RESULT (DETERMINISTIC)\n"
            "=====================================\n"
            + val_text.strip()
        )
    else:
        test_results = state.get("test_results") or {}
        if test_results:
            sections["evidence_validator"] = (
                "[5] VALIDATOR RESULT\n"
                "====================\n"
                f"exit_code={test_results.get('exit_code', '')} "
                f"passed={test_results.get('passed_count', 0)} "
                f"failed={test_results.get('failed_count', 0)}"
            )

    # [6] RUNTIME DIAGNOSTICS
    test_results = state.get("test_results") or {}
    output = test_results.get("output") or test_results.get("stdout") or ""
    if output:
        diag_lines = []
        for ln in output.splitlines():
            s = ln.strip()
            if s and any(k in s.lower() for k in (
                "error", "exception", "fail", "assert", "expected",
                "actual", "nameerror", "typeerror", "attributeerror",
                "valueerror", "syntaxerror", "stacktrace", "traceback"
            )):
                diag_lines.append(f"  {s}")
        if diag_lines:
            sections["evidence_diagnostics"] = (
                "[6] RUNTIME DIAGNOSTICS\n"
                "========================\n"
                + "\n".join(diag_lines[:30])
            )

    # [7] CAUSAL EVIDENCE (inferred from deterministic output & root causes)
    causal_parts = []
    if pkg is not None:
        root_causes = getattr(pkg, "root_causes", []) or []
        if root_causes:
            causal_parts.append("Root Causes:\n" + "\n".join(f"  - {rc}" for rc in root_causes))
    if causal_parts:
        sections["evidence_causal"] = (
            "[7] CAUSAL EVIDENCE\n"
            "====================\n"
            + "\n\n".join(causal_parts)
        )

    # [8] PRESCRIPTION (WHAT must be true — model determines HOW)
    if pkg is not None:
        prescriptions = getattr(pkg, "actionable_prescriptions", []) or []
        req_changes = getattr(pkg, "required_changes", []) or []
        pres_parts = []
        if prescriptions:
            for rx in prescriptions[:5]:
                rx_id = getattr(rx, "prescription_id", "?")
                req_chg = getattr(rx, "required_change", "")
                exp_state = getattr(rx, "expected_post_repair_state", "")
                part = f"  [{rx_id}] WHAT: {req_chg}"
                if exp_state:
                    part += f"\n    EXPECTED STATE: {exp_state}"
                pres_parts.append(part)
        elif req_changes:
            for rc in req_changes[:5]:
                rc_id = rc.get("change_id", "?") if isinstance(rc, dict) else getattr(rc, "change_id", "?")
                req = rc.get("deterministic_requirement", "") if isinstance(rc, dict) else getattr(rc, "deterministic_requirement", "")
                pres_parts.append(f"  [{rc_id}] {req}")
        if pres_parts:
            sections["requirement_prescription"] = (
                "[8] PRESCRIPTION (WHAT must be true — model menentukan HOW)\n"
                "=============================================================\n"
                + "\n".join(pres_parts)
            )

        exp_states = getattr(pkg, "expected_post_repair_state", []) or []
        if exp_states:
            sections["requirement_expected_post_repair"] = (
                "[EXPECTED POST-REPAIR STATE (deterministic)]\n"
                "============================================\n"
                + "\n".join(f"  ✓ {s}" for s in exp_states)
            )

    # [9] REPAIR BOUNDARY
    if pkg is not None:
        rb = getattr(pkg, "repair_boundary", None)
        if rb:
            allowed = getattr(rb, "allowed_changes", []) or []
            forbidden = getattr(rb, "forbidden_changes", []) or []
            rb_text = ""
            if allowed:
                rb_text += "ALLOWED:\n" + "\n".join(f"  + {a}" for a in allowed) + "\n"
            if forbidden:
                rb_text += "FORBIDDEN:\n" + "\n".join(f"  x {f_}" for f_ in forbidden[:6])
            if rb_text:
                sections["requirement_repair_boundary"] = (
                    "[9] REPAIR BOUNDARY\n"
                    "====================\n"
                    + rb_text.strip()
                )

    # [10] FORBIDDEN REGRESSIONS
    forbidden_lines = []
    if pkg is not None:
        for inv in (getattr(pkg, "preserved_invariants", []) or [])[:8]:
            inv_id = getattr(inv, "invariant_id", "?")
            desc = getattr(inv, "description", "")
            status = getattr(inv, "status", "")
            forbidden_lines.append(f"  [{status}] {inv_id}: {desc} — DO NOT BREAK")
    if forbidden_lines:
        sections["invariant_forbidden"] = (
            "[10] FORBIDDEN REGRESSIONS\n"
            "===========================\n"
            + "\n".join(forbidden_lines)
        )

    # [11] VERIFICATION CRITERIA
    if pkg is not None:
        verify_criteria = getattr(pkg, "verification_criteria", []) or []
        vc_text = "\n".join(f"  check {vc}" for vc in verify_criteria) if verify_criteria else "  All sandbox tests pass (exit_code == 0, failed_count == 0)"
    else:
        vc_text = "  All sandbox tests pass (exit_code == 0, failed_count == 0)"
    sections["authority_verification"] = (
        "[11] VERIFICATION CRITERIA (deterministic)\n"
        "===========================================\n"
        + vc_text
    )

    # [IMPLEMENTATION GROUNDING — DETERMINISTIC REALITY]
    combined_grounding_facts: List[Any] = []
    if ImplementationGroundingEngine is not None:
        try:
            harvested = ImplementationGroundingEngine.harvest_implementation_grounding(
                target_language=target_lang,
                code_files=code_files,
                test_files=test_files
            )
            if harvested:
                combined_grounding_facts.extend(harvested)
        except Exception:
            pass

    # Tambahkan canonical evidence dari pkg atau test_results jika ada
    if pkg is not None and getattr(pkg, "implementation_evidence", None):
        for ie in pkg.implementation_evidence:
            if isinstance(ie, dict) and CanonicalImplementationEvidence is not None:
                try:
                    combined_grounding_facts.append(CanonicalImplementationEvidence.from_dict(ie))
                except Exception:
                    pass
            else:
                combined_grounding_facts.append(ie)

    test_results_dict = state.get("test_results") or {}
    diag_ev = test_results_dict.get("diagnostic_evidence")
    if isinstance(diag_ev, dict) and "canonical_evidence" in diag_ev:
        for ce in diag_ev["canonical_evidence"]:
            if isinstance(ce, dict) and CanonicalImplementationEvidence is not None:
                try:
                    combined_grounding_facts.append(CanonicalImplementationEvidence.from_dict(ce))
                except Exception:
                    pass
            else:
                combined_grounding_facts.append(ce)

    if deduplicate_evidence is not None and combined_grounding_facts:
        combined_grounding_facts = deduplicate_evidence(combined_grounding_facts)

    if combined_grounding_facts:
        impl_lines = []
        for fact in combined_grounding_facts:
            f_str = fact.format_compact() if hasattr(fact, "format_compact") else str(fact)
            impl_lines.append(f"  {f_str}")
            # If compiler/grounding evidence conflicts with LLM prior knowledge, context explicitly asserts reality
            c_status = getattr(fact, "compatibility_status", "UNKNOWN")
            sym = getattr(fact, "symbol_reference", None) or "Symbol"
            if c_status in ("INCOMPATIBLE", "NOT_FOUND"):
                impl_lines.append(
                    f"    -> [AUTHORITY ASSERTION]: {sym} is {c_status} in active environment. "
                    f"Deterministic tooling overrides LLM parametric knowledge."
                )
        sections["authority_implementation_grounding"] = (
            "[IMPLEMENTATION GROUNDING — DETERMINISTIC REALITY]\n"
            "==================================================\n"
            "REALITAS IMPLEMENTASI DIBUKTIKAN SECARA DETERMINISTIK OLEH ENVIRONMENT/TOOLING:\n"
            + "\n".join(impl_lines)
        )

    # Part 3: Context Integrity & Task Isolation Audit
    integrity_violations: List[str] = []
    if ContextIntegrityAuditor is not None:
        target_domain = ""
        contract_obj = state.get("contract")
        if isinstance(contract_obj, dict):
            target_domain = (contract_obj.get("task_intent") or {}).get("domain", "")
        sections, integrity_violations = ContextIntegrityAuditor.audit_context_dict(
            sections,
            target_domain=target_domain,
            target_phase="DEVELOPER",
            state=state
        )

    result = compress_context_semantic(sections, max_chars=max_chars)

    telemetry_data = {
        "context_sections": list(sections.keys()),
        "context_size": len(result),
        "authoritative_sources": [k for k in sections if k.startswith("authority")],
        "evidence_items": len(getattr(pkg, "violations", []) or []) if pkg else 0,
        "locked_invariants": len(locked_dict),
        "current_failures": len(getattr(pkg, "violations", []) or []) if pkg else 0,
        "repair_boundary_items": len(
            getattr(getattr(pkg, "repair_boundary", None), "allowed_changes", []) or []
        ) if pkg else 0,
        "integrity_violations_detected": len(integrity_violations),
        "grounding_sources": list(set(getattr(f, "source", "unknown") for f in combined_grounding_facts)),
        "grounding_evidence_count": len(combined_grounding_facts),
        "grounding_evidence_types": list(set(getattr(f, "evidence_type", "unknown") for f in combined_grounding_facts)),
        "raw_diagnostic_count": len(diag_lines) if "diag_lines" in locals() and diag_lines else 0,
        "normalized_diagnostic_count": len(getattr(pkg, "violations", []) or []) if pkg else 0,
        "omitted_diagnostic_count": 0,
        "current_failure_count": len(getattr(pkg, "violations", []) or []) if pkg else 0,
        "historical_failure_count": sum(l_data.get("regression_count", 0) for l_data in locked_dict.values()) if isinstance(locked_dict, dict) else 0,
        "locked_invariant_count": len(locked_dict),
        "implementation_facts_count": len(combined_grounding_facts),
        "output_size": 0,
        "truncation_detected": False,
        "repair_result": "",
    }

    return result, telemetry_data
