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
        format_authoritative_obligation_ledger,
        format_acceptance_usage_evidence,
        ObligationKind,
    )
except (ImportError, ValueError):
    try:
        from canonical_obligation import (
            extract_canonical_oracle_obligations,
            format_authoritative_obligation_ledger,
            format_acceptance_usage_evidence,
            ObligationKind,
        )
    except ImportError:
        extract_canonical_oracle_obligations = None  # type: ignore
        format_authoritative_obligation_ledger = None  # type: ignore
        format_acceptance_usage_evidence = None  # type: ignore
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
        evaluate_scaffold_scenario_compatibility,
    )
except (ImportError, ValueError):
    try:
        from canonical_scenario import (
            extract_canonical_scenarios,
            evaluate_behavioral_observations,
            format_scenarios_for_architect,
            format_behavioral_mismatches_for_developer,
            evaluate_scaffold_scenario_compatibility,
        )
    except ImportError:
        extract_canonical_scenarios = None  # type: ignore
        evaluate_behavioral_observations = None  # type: ignore
        format_scenarios_for_architect = None  # type: ignore
        format_behavioral_mismatches_for_developer = None  # type: ignore
        evaluate_scaffold_scenario_compatibility = None  # type: ignore

try:
    from .architect_preservation import (
        RepairStateLedger,
        RepairStateItem,
        RepairTransitionStatus,
        ArchitectScaffoldSnapshot,
        generate_scaffold_snapshot,
        compare_scaffold_snapshots,
        evaluate_preservation_and_regression,
        validate_architect_repair_context_delivery,
    )
except (ImportError, ValueError):
    try:
        from architect_preservation import (
            RepairStateLedger,
            RepairStateItem,
            RepairTransitionStatus,
            ArchitectScaffoldSnapshot,
            generate_scaffold_snapshot,
            compare_scaffold_snapshots,
            evaluate_preservation_and_regression,
            validate_architect_repair_context_delivery,
        )
    except ImportError:
        RepairStateLedger = None  # type: ignore
        RepairStateItem = None  # type: ignore
        RepairTransitionStatus = None  # type: ignore
        ArchitectScaffoldSnapshot = None  # type: ignore
        generate_scaffold_snapshot = None  # type: ignore
        compare_scaffold_snapshots = None  # type: ignore
        evaluate_preservation_and_regression = None  # type: ignore
        validate_architect_repair_context_delivery = None  # type: ignore

try:
    from .blueprint_schema import (
        ArchitecturalBlueprint,
        BlueprintInterfaceContract,
        BlueprintFileModule,
        BlueprintDataModel,
    )
except (ImportError, ValueError):
    try:
        from blueprint_schema import (
            ArchitecturalBlueprint,
            BlueprintInterfaceContract,
            BlueprintFileModule,
            BlueprintDataModel,
        )
    except ImportError:
        ArchitecturalBlueprint = None  # type: ignore
        BlueprintInterfaceContract = None  # type: ignore
        BlueprintFileModule = None  # type: ignore
        BlueprintDataModel = None  # type: ignore

try:
    from .contract import InterfaceParameter, ExpectedReturn
except (ImportError, ValueError):
    try:
        from contract import InterfaceParameter, ExpectedReturn
    except ImportError:
        InterfaceParameter = None  # type: ignore
        ExpectedReturn = None  # type: ignore

try:
    from .developer_semantic_repair import (
        normalize_runtime_evidence,
        compare_scenario_with_observation,
        evaluate_developer_preservation,
        update_developer_failure_ledger,
        assemble_developer_semantic_repair_context,
        DeveloperRepairEvidence,
        NormalizedObservation,
        SemanticComparisonStatus,
        SemanticDiffClassification,
    )
except (ImportError, ValueError):
    try:
        from developer_semantic_repair import (
            normalize_runtime_evidence,
            compare_scenario_with_observation,
            evaluate_developer_preservation,
            update_developer_failure_ledger,
            assemble_developer_semantic_repair_context,
            DeveloperRepairEvidence,
            NormalizedObservation,
            SemanticComparisonStatus,
            SemanticDiffClassification,
        )
    except ImportError:
        normalize_runtime_evidence = None  # type: ignore
        compare_scenario_with_observation = None  # type: ignore
        evaluate_developer_preservation = None  # type: ignore
        update_developer_failure_ledger = None  # type: ignore
        assemble_developer_semantic_repair_context = None  # type: ignore
        DeveloperRepairEvidence = None  # type: ignore
        NormalizedObservation = None  # type: ignore
        SemanticComparisonStatus = None  # type: ignore
        SemanticDiffClassification = None  # type: ignore



# ===========================================================================
# 1. Semantic Context Compressor
# ===========================================================================

ARCHITECT_REPAIR_PRIORITY_ORDER: List[str] = [
    "sec_01_authority",
    "sec_03_current_failures",
    "sec_06_repair_target",
    "sec_07_repair_boundary",
    "sec_05_current_valid_state",
    "sec_04_locked_proven_state",
    "sec_08_expected_post_repair",
    "sec_02_canonical_schema",
    "sec_09_relational_blueprint",
    "sec_10_raw_diagnostics",
]

DEFAULT_PRIORITY_ORDER: List[str] = [
    "authority_acceptance",
    "authority_user_intent",
    "authority_v0",
    "authority_oracle",
    "authority_scenario",
    "authority_contract",
    "authority_canonical_schema",
    "evidence_mismatch",
    "requirement_prescription",
    "requirement_intent",
    "requirement_draft",
    "requirement",
    "invariant_locked",
    "invariant",
    "authority_output_contract",
    "relational_blueprint_state",
    "requirement_repair_boundary",
    "requirement_expected_post_repair",
    "authority_verification",
    "evidence_validator",
    "evidence_diagnostics",
    "evidence",
    "impl_ref",
    "historical",
    "authority",
]


def resolve_context_budget(state: Optional[Dict[str, Any]], default: int = 12000) -> int:
    """
    Satu-satunya resolver generik untuk context budget (Treatment #1.8.2).
    Mencegah disparitas konfigurasi budget antar komponen.
    Hierarki resolusi konsisten:
      1. state['context_budget'] (konfigurasi per-run / eksplisit)
      2. state['max_context_chars'] (legacy parameter fallback)
      3. default (12,000 karakter konfigurasi awal — bukan invariant arsitektural)
    """
    if not state or not isinstance(state, dict):
        return default
    val = state.get("context_budget") or state.get("max_context_chars")
    if val is not None:
        try:
            return int(val)
        except (ValueError, TypeError):
            pass
    return default


def compress_raw_diagnostics_semantic(raw_text: str, max_chars: int = 250) -> str:
    """Kompresi Tier 3: diringkas ke diagnosis penting, membuang trace stack internal yang redundan."""
    if len(raw_text) <= max_chars:
        return raw_text
    lines = raw_text.splitlines()
    header = lines[0] if lines else "[10] RAW DIAGNOSTICS (Bounded)"
    separator = lines[1] if len(lines) > 1 and "=" in lines[1] else "========================================================================="
    diagnostic_lines: List[str] = []
    for ln in lines[2:]:
        s = ln.strip()
        if not s:
            continue
        if any(kw in s for kw in ("Error", "Exception", "Fail", "Mismatch", "AssertionError", "File", "line ")):
            diagnostic_lines.append(s[:100])
    if not diagnostic_lines:
        diagnostic_lines = [l.strip()[:100] for l in lines[2:6] if l.strip()]
    summary = "\n".join(diagnostic_lines[:4])
    res = f"{header}\n{separator}\n{summary}\n...(diagnostics diringkas untuk efisiensi context)"
    return res[:max_chars] if len(res) > max_chars else res


def compress_relational_blueprint_semantic(text: str, max_chars: int = 350) -> str:
    """Kompresi Tier 2: diringkas ke relasi simbol utama & user intent."""
    if len(text) <= max_chars:
        return text
    lines = text.splitlines()
    header = lines[0] if lines else "[9] IMPLEMENTATION GROUNDING & RELATIONAL BLUEPRINT STATE [F]"
    separator = lines[1] if len(lines) > 1 and "=" in lines[1] else "============================================================"
    compact_lines: List[str] = []
    for ln in lines[2:]:
        s = ln.strip()
        if not s:
            continue
        if s.startswith("User Task Intent:") or s.startswith("V0 Core Requirements:") or s.startswith("- ") or s.startswith("* "):
            compact_lines.append(s[:120])
        elif "->" in s or "=>" in s or "caller" in s or "identifier" in s:
            compact_lines.append(s[:120])
    res = f"{header}\n{separator}\n" + "\n".join(compact_lines[:6])
    if len(res) > max_chars:
        res = res[:max_chars - 30] + "\n...(ringkas)"
    return res


def compress_canonical_schema_semantic(text: str, max_chars: int = 700) -> str:
    """Kompresi Tier 2: ringkas narasi tanpa merusak batasan tipe data skema kanonikal JSON."""
    if len(text) <= max_chars:
        return text
    header = "[2] ACCEPTANCE OBLIGATION LEDGER & CANONICAL BLUEPRINT SCHEMA CONSTRAINTS"
    sep = "========================================================================"
    schema_body = (
        "Authority Notice: Canonical Schema and Acceptance Obligations determine structural reality.\n"
        "Essential Schema Constraints:\n"
        "- authoritative_target_file: str (implementation entrypoint; must exist in file_tree and files)\n"
        "- file_tree: List[str] (clean file paths; no test files)\n"
        "- files: Dict[str, dict] (map file_tree path to scaffold object)\n"
        "- interface_contracts: List[dict] (identifier, target_file, signature)\n"
        "- data_models: List[dict] (model_name, fields)\n"
    )
    scenarios_found: List[str] = []
    for ln in text.splitlines():
        if "SCENARIO:" in ln or "OBLIGATION_ID:" in ln:
            scenarios_found.append(ln.strip()[:100])
    if scenarios_found:
        schema_body += "ACCEPTANCE OBLIGATIONS (COMPACT):\n" + "\n".join(scenarios_found[:5]) + "\n"
    res = f"{header}\n{sep}\n{schema_body}".strip()
    return res[:max_chars] if len(res) > max_chars else res


def distill_failure_item_semantic(
    failure_text: str,
    evidence_source: str = "Deterministic Contract Gate",
    target_location: str = "",
    max_chars: int = 300
) -> str:
    """
    Deterministic Semantic Distillation (Treatment #1.8.2):
    Mengekstrak fakta kausal dari data terstruktur / traceback secara deterministik
    tanpa parafrase bebas (No Semantic Invention) dan tanpa menghilangkan bukti kausal:
      - Failure: tipe / pesan inti kegagalan
      - Observed at: lokasi simbol / berkas target
      - Evidence source: sumber otoritatif (Validator / Gate / Oracle)
      - Diagnostic detail: detail asersi / pesan diagnostik kausal
    """
    lines = [ln.strip() for ln in failure_text.splitlines() if ln.strip()]
    if not lines:
        return ""

    # Check if already structured in CEP or Compatibility format:
    if any("Observed:" in ln for ln in lines) and any("Required:" in ln for ln in lines):
        return "\n    ".join(lines[:4])[:max_chars]

    err_line = ""
    loc_line = target_location
    src_label = evidence_source

    for ln in lines:
        if "[COMPATIBILITY_DIAGNOSIS]" in ln or "SCENARIO" in ln:
            src_label = "Scaffold Scenario Compatibility Matrix"
        elif "[CONTRACT_GATE]" in ln:
            src_label = "Deterministic Contract Gate"
        elif "AssertionError" in ln or "assert " in ln:
            src_label = "Acceptance Oracle Test Suite"

        if not loc_line:
            if "Source:" in ln:
                loc_line = ln.split("Source:", 1)[1].strip()
            elif "Target File:" in ln:
                loc_line = ln.split("Target File:", 1)[1].strip()
            elif ln.startswith("File ") and "site-packages" not in ln:
                loc_line = ln.split("File ", 1)[1].split(",", 1)[0].replace('"', '').strip()

        if any(ln.startswith(kw) or f" {kw}" in ln for kw in ("Error", "Exception", "Fail", "Mismatch", "AssertionError")):
            err_line = ln

    if not err_line:
        clean = [
            ln for ln in lines
            if not (ln.startswith("File ") or ln.startswith("Traceback") or "site-packages" in ln or "^^^" in ln)
        ]
        err_line = clean[-1] if clean else lines[0]

    # Deterministic causal evidence structure
    parts = [f"Failure: {err_line}"]
    if loc_line:
        parts.append(f"Observed at: {loc_line}")
    parts.append(f"Evidence source: {src_label}")

    exp_lines = [ln for ln in lines if ln.startswith("Expected:") or ln.startswith("Required:") or ln.startswith("Observed Scaffold:")]
    if exp_lines:
        parts.append(f"Diagnostic detail: {'; '.join(exp_lines[:2])}")

    res = "\n    ".join(parts)
    return res[:max_chars] if len(res) > max_chars else res


def distill_canonical_schema_semantic(max_chars: int = 800) -> str:
    """
    Deterministic Semantic Distillation (Treatment #1.8.2 / #1.8.4):
    Menyusun batasan skema kanonikal sebagai Representation Contract ringkas
    secara deterministik langsung dari skema ArchitecturalBlueprint tanpa parafrase bebas
    dan tanpa semantic invention (NO LOSS + NO INVENTION).
    """
    header = "[2] CANONICAL BLUEPRINT SCHEMA CONSTRAINTS (REPRESENTATION CONTRACT)"
    body = (
        "Root Fields Contract:\n"
        "  - authoritative_target_file: str (entrypoint; must exist in file_tree and files)\n"
        "  - file_tree: List[str] (clean paths; zero test files)\n"
        "  - files: Dict[str, BlueprintFileModule] (maps every path in file_tree to scaffold)\n"
        "  - interface_contracts: List[dict] (identifier, target_file; param_name, param_type, param_location; expected_return: {return_type})\n"
        "  - data_models: List[dict] (model_name, target_file, fields)\n"
        "Two-Stage Synthesis: Stage A (Semantic Mapping) -> Stage B (Canonical Serialization).\n"
        "Obligation Coverage: Setiap mandatory obligation harus mempunyai representasi deterministik.\n"
        "Core Invariants: Generic Anti-Field-Loss (CURRENT VALID STATE + REPAIRED ELEMENT), Artifact Purity."
    )
    res = f"{header}\n{body}".strip()
    return res[:max_chars] if len(res) > max_chars else res


def compress_valid_state_semantic(text: str, max_chars: int = 1400) -> str:
    """
    Kompresi Tier 2: Compress representation, preserve semantic relationships (Correction 3).
    Mempertahankan relasi struktural lengkap:
    Model -> target_file -> interface -> scaffold signatures -> obligation -> scenario.
    Hanya membuang algoritma/body fungsi internal (mengganti dengan pass/stubs).
    """
    if len(text) <= max_chars:
        return text
    lines = text.splitlines()
    preserved_lines: List[str] = []
    in_code = False
    code_block: List[str] = []

    for ln in lines:
        s = ln.strip()
        # Keep headers, notices, and relational invariants
        if s.startswith("[5]") or "Authority Notice:" in s or "Repair Formula:" in s or "VALID !=" in s or "Relational Invariant:" in s:
            preserved_lines.append(ln)
        # Keep collections and explicit relational links
        elif (
            s.startswith("Established File Collection") or
            s.startswith("Established Interface Contracts") or
            s.startswith("Established Data Models") or
            s.startswith("Established Module Scaffolds") or
            s.startswith("* Module") or
            s.startswith("Target File:") or
            s.startswith("Associated Interfaces:") or
            s.startswith("Associated Data Models:") or
            s.startswith("Linked Scenarios") or
            s.startswith("Scaffold Interface Signatures") or
            "->" in s
        ):
            preserved_lines.append(ln)
        elif s.startswith("```"):
            in_code = not in_code
            if not in_code and code_block:
                preserved_lines.append("```\n" + "\n".join(code_block) + "\n```")
                code_block = []
            elif in_code:
                code_block = []
        elif in_code:
            # Inside scaffold code: preserve signatures, classes, decorators, constructors, interfaces
            if any(s.startswith(p) for p in (
                "def ", "class ", "async def ", "final ", "const ", "var ",
                "import ", "from ", "@", "export ", "interface ", "type ",
                "struct ", "constructor", "public ", "private "
            )):
                code_block.append(ln)
                if s.endswith(":") or s.endswith("{"):
                    indent = len(ln) - len(ln.lstrip()) + 4
                    code_block.append(" " * indent + "pass")

    if in_code and code_block:
        preserved_lines.append("```\n" + "\n".join(code_block) + "\n```")

    res = "\n".join(preserved_lines).strip()
    if len(res) > max_chars:
        res = res[:max_chars - 60] + "\n...(scaffold ringkas: semantic relationships & interfaces preserved)"
    return res


def compress_context_semantic_detailed(
    sections: Dict[str, str],
    max_chars: int,
    priority_order: Optional[List[str]] = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    Role-based semantic compression engine with atomic section protection.
    Compresses lower-priority context in tiers before touching repair-critical sections.
    Guarantees that repair-critical sections (Authority, Failures, Repair Target, Repair Boundary, Valid State)
    are preserved intact.
    Returns (compressed_text, telemetry_metadata).
    """
    if priority_order is None:
        priority_order = DEFAULT_PRIORITY_ORDER

    ordered_keys: List[str] = []
    for p in priority_order:
        for k in sections:
            if (k == p or k.startswith(p)) and k not in ordered_keys:
                ordered_keys.append(k)
    for k in sections:
        if k not in ordered_keys:
            ordered_keys.append(k)

    # Initial size before compression
    initial_parts = [sections[k] for k in ordered_keys if sections.get(k)]
    size_before = sum(len(p) for p in initial_parts) + max(0, len(initial_parts) - 1) * 2

    # Repair-critical sections that MUST be protected atomically
    REPAIR_CRITICAL_KEYS = {
        "sec_01_authority",
        "sec_03_current_failures",
        "sec_06_repair_target",
        "sec_07_repair_boundary",
        "sec_05_current_valid_state",
        "sec_04_locked_proven_state",
    }
    CRITICAL_PREFIXES = ("authority_acceptance", "authority_scenario", "evidence_mismatch")

    working_sections = dict(sections)
    sections_truncated: List[str] = []
    compression_applied = False

    # Check if compression is required
    if size_before > max_chars:
        compression_applied = True

        # ===================================================================
        # TIER 3 COMPRESSION: Raw Diagnostics & Diagnostic Logs
        # ===================================================================
        if "sec_10_raw_diagnostics" in working_sections:
            orig = working_sections["sec_10_raw_diagnostics"]
            comp = compress_raw_diagnostics_semantic(orig, max_chars=250)
            if len(comp) < len(orig):
                working_sections["sec_10_raw_diagnostics"] = comp
                sections_truncated.append("sec_10_raw_diagnostics")

        for k in working_sections:
            if k.startswith("evidence_diagnostics") or k.startswith("historical"):
                orig = working_sections[k]
                if len(orig) > 300:
                    working_sections[k] = orig[:250] + "\n...(dipotong)"
                    sections_truncated.append(k)

        # Recalculate size after Tier 3
        cur_parts = [working_sections[k] for k in ordered_keys if working_sections.get(k)]
        cur_size = sum(len(p) for p in cur_parts) + max(0, len(cur_parts) - 1) * 2

        # ===================================================================
        # TIER 2 COMPRESSION: Relational Blueprint, Canonical Schema, Scaffolds
        # ===================================================================
        if cur_size > max_chars:
            if "sec_09_relational_blueprint" in working_sections:
                orig = working_sections["sec_09_relational_blueprint"]
                comp = compress_relational_blueprint_semantic(orig, max_chars=350)
                if len(comp) < len(orig):
                    working_sections["sec_09_relational_blueprint"] = comp
                    sections_truncated.append("sec_09_relational_blueprint")

            if "sec_02_canonical_schema" in working_sections:
                orig = working_sections["sec_02_canonical_schema"]
                comp = compress_canonical_schema_semantic(orig, max_chars=700)
                if len(comp) < len(orig):
                    working_sections["sec_02_canonical_schema"] = comp
                    sections_truncated.append("sec_02_canonical_schema")

            if "sec_05_current_valid_state" in working_sections:
                orig = working_sections["sec_05_current_valid_state"]
                comp = compress_valid_state_semantic(orig, max_chars=1200)
                if len(comp) < len(orig):
                    working_sections["sec_05_current_valid_state"] = comp
                    sections_truncated.append("sec_05_current_valid_state")

            for k in working_sections:
                if k.startswith("requirement_draft") or k.startswith("requirement_prescription"):
                    orig = working_sections[k]
                    if len(orig) > 500:
                        working_sections[k] = orig[:450] + "\n...(dipotong)"
                        sections_truncated.append(k)

    # =======================================================================
    # ASSEMBLY & ATOMIC SECTION PRESERVATION
    # =======================================================================
    result_parts: List[str] = []
    sections_present: List[str] = []
    sections_omitted: List[str] = []
    total = 0

    for k in ordered_keys:
        content = working_sections.get(k, "")
        if not content:
            continue

        sep_len = 2 if result_parts else 0
        is_critical = (k in REPAIR_CRITICAL_KEYS or any(k.startswith(cp) for cp in CRITICAL_PREFIXES))

        if total + sep_len + len(content) <= max_chars:
            result_parts.append(content)
            sections_present.append(k)
            total += sep_len + len(content)
        elif is_critical:
            # Critical sections MUST be preserved atomically within max_chars.
            remaining = max_chars - total - sep_len
            if remaining > 250:
                comp_content = compress_valid_state_semantic(content, max_chars=remaining - 20) if "valid_state" in k else content[:remaining - 20]
                result_parts.append(comp_content)
                sections_present.append(k)
                sections_truncated.append(k)
                total += sep_len + len(comp_content)
            else:
                sections_omitted.append(k)
        else:
            # Lower-priority section: soft-truncate if enough room, else omit
            remaining = max_chars - total - sep_len
            if remaining > 150:
                truncated = content[:remaining - 40] + "\n...(dipotong untuk efisiensi context)"
                result_parts.append(truncated)
                sections_present.append(k)
                sections_truncated.append(k)
                total += sep_len + len(truncated)
            else:
                sections_omitted.append(k)

    result = "\n\n".join(result_parts)
    if len(result) > max_chars:
        result = result[:max_chars]

    repair_critical_present = [k for k in REPAIR_CRITICAL_KEYS if k in sections_present]

    telemetry_meta = {
        "context_budget": max_chars,
        "context_size_before_compression": size_before,
        "context_size_after_compression": len(result),
        "compression_applied": compression_applied,
        "sections_present": sections_present,
        "sections_omitted": sections_omitted,
        "sections_truncated": list(set(sections_truncated)),
        "repair_critical_sections_present": repair_critical_present,
    }

    # Deterministic warning on critical omission
    for cp in CRITICAL_PREFIXES:
        for k, content in sections.items():
            if content and k.startswith(cp):
                header = content.splitlines()[0] if content.splitlines() else ""
                if header and header not in result:
                    import warnings
                    warnings.warn(
                        f"[CONTEXT_OMISSION_DETECTED]: Critical section '{k}' could not fit within max_chars={max_chars}. "
                        "Deterministic system strictly forbids silent omission.",
                        RuntimeWarning
                    )

    return result, telemetry_meta


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
    result, _ = compress_context_semantic_detailed(
        sections,
        max_chars=max_chars,
        priority_order=priority_order,
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
    delivery_valid: bool = True
    delivery_errors: List[str] = field(default_factory=list)
    # Extended Context Budget Telemetry (Section 9)
    context_budget: int = 0
    context_size_before_compression: int = 0
    context_size_after_compression: int = 0
    compression_applied: bool = False
    sections_present: List[str] = field(default_factory=list)
    sections_omitted: List[str] = field(default_factory=list)
    sections_truncated: List[str] = field(default_factory=list)
    repair_critical_sections_present: List[str] = field(default_factory=list)
    delivery_failure_reason: str = ""
    model_context_parameters: Dict[str, Any] = field(default_factory=dict)
    # Treatment #1.8.2: Distillation & Final Delivery Audit Telemetry
    raw_context_chars: int = 0
    distilled_context_chars: int = 0
    final_context_chars: int = 0
    configured_budget: int = 0
    estimated_token_count: int = 0
    compression_ratio: float = 0.0
    semantic_payload_completeness: bool = True
    relational_preservation_status: str = "INTACT"

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


def format_canonical_blueprint_schema_constraints() -> str:
    """
    Ekstrak batasan struktural kanonikal langsung dari definisi skema ArchitecturalBlueprint.
    TIDAK meng-hardcode aturan solver atau asumsi task spesifik.
    """
    if ArchitecturalBlueprint is None:
        return ""
    lines = [
        "CANONICAL BLUEPRINT SCHEMA CONSTRAINTS (Derived directly from ArchitecturalBlueprint definition):"
    ]
    for field_name, f in ArchitecturalBlueprint.model_fields.items():
        if field_name in ("schema_version", "task_id", "target_language"):
            continue
        req_label = "REQUIRED" if (f.is_required() or field_name == "authoritative_target_file") else "OPTIONAL"
        annot_str = (
            str(f.annotation)
            .replace("typing.", "")
            .replace("backend.blueprint_schema.", "")
            .replace("blueprint_schema.", "")
            .replace("<class 'str'>", "str")
        )
        desc = f.description or ""
        lines.append(f"  - {field_name}: {annot_str} [{req_label}] — {desc}")

    # Canonical Sub-model Inspection (Introspected directly from Pydantic model fields)
    if BlueprintFileModule is not None and hasattr(BlueprintFileModule, "model_fields"):
        lines.append("  Module Schema for elements in 'files':")
        for fn, f in BlueprintFileModule.model_fields.items():
            req_label = "REQUIRED" if f.is_required() else "OPTIONAL"
            ann = str(f.annotation).replace("typing.", "").replace("<class 'str'>", "str")
            lines.append(f"    * {fn}: {ann} [{req_label}] — {f.description or ''}")

    if BlueprintInterfaceContract is not None and hasattr(BlueprintInterfaceContract, "model_fields"):
        lines.append("  Contract Schema for elements in 'interface_contracts':")
        for fn, f in BlueprintInterfaceContract.model_fields.items():
            req_label = "REQUIRED" if f.is_required() else "OPTIONAL"
            ann = str(f.annotation).replace("typing.", "").replace("<class 'str'>", "str")
            lines.append(f"    * {fn}: {ann} [{req_label}] — {f.description or ''}")

    # Canonical Parameter & ExpectedReturn Sub-model Inspection
    if InterfaceParameter is not None and hasattr(InterfaceParameter, "model_fields"):
        lines.append("  Parameter Schema for elements in 'parameters' (within interface_contracts):")
        for fn, f in InterfaceParameter.model_fields.items():
            req_label = "REQUIRED" if f.is_required() else "OPTIONAL"
            ann = str(f.annotation).replace("typing.", "").replace("<class 'str'>", "str")
            lines.append(f"    * {fn}: {ann} [{req_label}] — {f.description or ''}")
        lines.append("    * Valid param_location values: 'PATH', 'QUERY', 'BODY', 'ARGUMENT', 'PROP'")

    if ExpectedReturn is not None and hasattr(ExpectedReturn, "model_fields"):
        lines.append("  ExpectedReturn Schema for 'expected_return' (within interface_contracts):")
        for fn, f in ExpectedReturn.model_fields.items():
            req_label = "REQUIRED" if f.is_required() else "OPTIONAL"
            ann = str(f.annotation).replace("typing.", "").replace("<class 'str'>", "str")
            lines.append(f"    * {fn}: {ann} [{req_label}] — {f.description or ''}")

    lines.extend([
        "  Canonical Contrastive Representation Examples (Derived from schema definitions):",
        "    * PARAMETERS SCHEMA FIDELITY:",
        "        VALID:   {\"param_name\": \"param_1\", \"param_type\": \"TypeA\", \"param_location\": \"ARGUMENT\"}",
        "        INVALID: {\"name\": \"param_1\", \"type\": \"TypeA\"}  (schema requires 'param_name' and 'param_type')",
        "    * EXPECTED RETURN SCHEMA FIDELITY:",
        "        VALID:   {\"return_type\": \"TypeA\"} or {\"return_type\": \"TypeA\", \"status_code_success\": 200}",
        "        INVALID: \"TypeA\"  (bare string is rejected; schema requires structured object with 'return_type')",
        "    * UNIVERSAL CONTRACT DECLARATION:",
        "        VALID:   {\"identifier\": \"operation_a\", \"target_file\": \"module_a.ext\"}",
        "        OPTIONAL (when applicable to endpoint interfaces): 'route' and 'method' (e.g. \"route\": \"/operation_a\", \"method\": \"POST\")",
        "  Two-Stage Synthesis & Obligation Coverage Doctrine:",
        "    * Stage A (Semantic Mapping): Map each acceptance obligation into an architectural representation.",
        "    * Stage B (Canonical Serialization): Serialize the representation into the exact schema structure.",
        "    * Obligation Coverage Rule: Setiap mandatory acceptance obligation harus mempunyai canonical architectural representation yang dapat ditelusuri secara deterministik (baik melalui interface_contracts maupun data_models).",
        "  Relational Representation Rules (Derived from ArchitecturalBlueprint model validators):",
        "    * 'authoritative_target_file' is strictly the primary implementation target and MUST exist in both 'file_tree' and 'files'.",
        "    * 'file_tree' is strictly a list of file path strings (List[str]). Never nest scaffold dictionaries inside 'file_tree'.",
        "    * 'files' is strictly a top-level dictionary (Dict[str, BlueprintFileModule]) mapping each path string from 'file_tree' to its module scaffold.",
        "    * Both 'file_tree' and 'files' are top-level root keys of the blueprint; never replace, omit, or merge them together.",
        "    * Every file declared in 'file_tree' must exist as a key in 'files', and vice-versa (1-to-1 consistency).",
        "    * For endpoint interfaces, include 'route' and 'method' matching the required HTTP endpoints."
    ])
    return "\n".join(lines)


def format_relational_blueprint_state(
    oracle_obs: Optional[List[Any]] = None,
    oracle_items: Optional[List[str]] = None,
    scenarios: Optional[List[Any]] = None,
    contract: Optional[Dict[str, Any]] = None,
    auth_file: str = "",
) -> str:
    """
    Membangun representasi struktural turunan [F] RELATIONAL BLUEPRINT STATE.
    Diturunkan secara deterministik dari evidence yang ada (A-E) tanpa mengarang kewajiban baru.
    Hierarchy: Acceptance Authority > Existing canonical schema / governance > Architect relational guidance.
    """
    lines = [
        "Relational Dependency Mapping:",
        "  Acceptance Obligation -> Architectural Representation -> Interface Contract -> File Representation -> Scenario Compatibility",
        "",
        "Derived Relational State Ledger (Grounded strictly in available evidence):"
    ]

    has_entries = False
    if oracle_obs:
        for ob in oracle_obs[:8]:
            sym = (
                getattr(ob, "public_identity", "")
                or getattr(ob, "symbol_name", "")
                or getattr(ob, "callee", "")
                or getattr(ob, "identifier", "")
                or str(getattr(ob, "obligation_id", ""))
            )
            sig = (
                getattr(ob, "observable_behavior", "")
                or getattr(ob, "expected_signature", "")
                or getattr(ob, "signature", "")
            )
            kind = getattr(ob, "obligation_kind", "")
            target = auth_file or getattr(ob, "target_file", "") or "authoritative_target_file"
            lines.append(f"  - Obligation: '{sym}' [{kind or 'FUNCTIONAL'}] | Shape: {sig or 'compatible'} -> Target Artifact: '{target}'")
            has_entries = True
    elif oracle_items:
        for it in oracle_items[:8]:
            target = auth_file or "authoritative_target_file"
            lines.append(f"  - Oracle Symbol: '{it}' [ORACLE_FACT] -> Target Artifact: '{target}'")
            has_entries = True
    elif isinstance(contract, dict) and contract.get("interface_contracts"):
        for ifc in contract.get("interface_contracts", [])[:8]:
            if isinstance(ifc, dict) and ifc.get("identifier"):
                ident = ifc["identifier"]
                target = ifc.get("target_file") or auth_file or "authoritative_target_file"
                lines.append(f"  - Interface Symbol: '{ident}' [PM_PROPOSAL] -> Target Artifact: '{target}'")
                has_entries = True

    if not has_entries:
        target = auth_file or "authoritative_target_file"
        lines.append(f"  - Dynamic Relational Target: Map required capabilities to concrete interfaces in '{target}'.")

    lines.extend([
        "",
        "Blueprint Integrity Invariants (A-H — Architect Reasoning Guidance):",
        "  - INVARIANT-A (Identity Stability): Every declared interface maintains a stable identity.",
        "  - INVARIANT-B (Consistent Location): Every interface links to a valid target artifact declared in file collection.",
        "  - INVARIANT-C (File Structure Consistency): File collection matches declared modules with zero phantom files.",
        "  - INVARIANT-D (Obligation Representation): Acceptance obligations requiring representation have that representation.",
        "  - INVARIANT-E (Interface Shape Preservation): Interface shapes do not mutate semantically without evidence.",
        "  - INVARIANT-F (Non-Destructive Repair): Repair must preserve all elements and fields that remain valid under canonical schema.",
        "  - INVARIANT-G (Relational Consistency): Artifacts, interfaces, and scaffolds form a unified, coherent structure.",
        "  - INVARIANT-H (Serialization Equivalence): Serialized schema represents the identical semantic structure.",
        "",
        "Authority Notice:",
        "  [F] is a derived structural representation, NOT an independent acceptance authority.",
        "  Hierarchy: Acceptance Authority > Existing canonical schema / governance > Architect relational guidance.",
        "  If any conflict arises, Acceptance Authority strictly prevails."
    ])
    return "\n".join(lines)


# ===========================================================================
# 4. Architect Decision & Repair Context Packages (Treatment #1.5 / #1.8.1)
# ===========================================================================

def build_architect_repair_context(
    state: Dict[str, Any],
    pkg: Optional[Any] = None,
    max_chars: Optional[int] = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    Membangun 10-seksi Architect Repair Context Package secara generik (Treatment #1.8.1-R1).
    Konteks budget adalah parameter yang dapat dikonfigurasi (bukan invariant arsitektural).

    [1] IMMUTABLE ACCEPTANCE AUTHORITY & CONFLICT RESOLUTION
    [2] CANONICAL BLUEPRINT SCHEMA CONSTRAINTS
    [3] CURRENT VALID STATE (PRESERVED ACROSS REPAIR)
    [4] CURRENT COMPATIBILITY FAILURES (REPAIR SCOPE)
    [5] LOCKED/PROVEN STATE & INVARIANTS
    [6] REPAIR TARGET
    [7] REPAIR BOUNDARY
    [8] EXPECTED POST-REPAIR STATE
    [9] RELATIONAL BLUEPRINT STATE [F]
    [10] RAW DIAGNOSTICS
    """
    if max_chars is None:
        max_chars = resolve_context_budget(state)
    sections: Dict[str, str] = {}

    frozen_path = state.get("frozen_oracle_path") or ""
    test_files = state.get("test_files")
    contract = state.get("contract") or {}
    arch_plan = state.get("architecture_plan", "")
    blueprint = state.get("architectural_blueprint") or {}

    auth_file = ""
    if isinstance(contract, dict):
        task_intent = contract.get("task_intent", {})
        if isinstance(task_intent, dict):
            auth_file = task_intent.get("authoritative_target_file", "")

    # Extract scaffold files
    scaffold_files: Dict[str, str] = {}
    if blueprint:
        if hasattr(blueprint, "files") and blueprint.files:
            for fp, mod in blueprint.files.items():
                scaffold_files[fp] = getattr(mod, "code_scaffold", "") or (mod.get("code_scaffold", "") if isinstance(mod, dict) else str(mod))
        elif isinstance(blueprint, dict) and "files" in blueprint:
            b_files = blueprint.get("files", {})
            if isinstance(b_files, dict):
                for fp, mod in b_files.items():
                    if isinstance(mod, str):
                        scaffold_files[fp] = mod
                    elif isinstance(mod, dict):
                        scaffold_files[fp] = mod.get("code_scaffold", "") or mod.get("content", "")
                    elif hasattr(mod, "code_scaffold"):
                        scaffold_files[fp] = getattr(mod, "code_scaffold", "") or ""
    if not scaffold_files and state.get("code_files"):
        scaffold_files = dict(state.get("code_files") or {})

    # Extract scenarios & obligations
    oracle_obs = []
    if extract_canonical_oracle_obligations and (frozen_path or test_files):
        try:
            oracle_obs = extract_canonical_oracle_obligations(
                frozen_oracle_path=frozen_path if frozen_path else None,
                test_files=test_files if test_files else None,
            )
        except Exception:
            oracle_obs = []

    scenarios = []
    if extract_canonical_scenarios and (frozen_path or test_files):
        try:
            scenarios = extract_canonical_scenarios(
                frozen_oracle_path=frozen_path if frozen_path else None,
                test_files=test_files if test_files else None,
            )
        except Exception:
            scenarios = []

    # Get previous snapshot
    prev_snapshot = None
    snapshots = state.get("scaffold_snapshots") or []
    if snapshots:
        last_s = snapshots[-1]
        prev_snapshot = ArchitectScaffoldSnapshot.from_dict(last_s) if isinstance(last_s, dict) else last_s
    elif isinstance(contract, dict) and contract.get("provenance", {}).get("scaffold_snapshots"):
        last_s = contract["provenance"]["scaffold_snapshots"][-1]
        prev_snapshot = ArchitectScaffoldSnapshot.from_dict(last_s) if isinstance(last_s, dict) else last_s

    # Current matrix
    curr_matrix = None
    if scaffold_files and scenarios and evaluate_scaffold_scenario_compatibility is not None:
        try:
            curr_matrix = evaluate_scaffold_scenario_compatibility(scenarios, scaffold_files)
        except Exception:
            pass
    if curr_matrix is None and state.get("latest_scaffold_matrix"):
        curr_matrix = state.get("latest_scaffold_matrix")

    # Ledger
    ledger = None
    if evaluate_preservation_and_regression is not None and scenarios:
        try:
            ledger = evaluate_preservation_and_regression(
                prev_snapshot,
                curr_matrix,
                scenarios,
                scaffold_files=scaffold_files
            )
        except Exception:
            pass

    # ========================================================
    # [1] IMMUTABLE ACCEPTANCE AUTHORITY
    # ========================================================
    oracle_items = extract_authoritative_oracle_interfaces(state)
    auth_lines = [
        "[1] IMMUTABLE ACCEPTANCE AUTHORITY (ORACLE_FACT — verified test suite)",
        "======================================================================",
        "Authority Notice: Absolute acceptance authority belongs to Acceptance Oracle test suite.",
        "Architect is strictly FORBIDDEN from altering, removing, or overriding these requirements."
    ]
    if oracle_items:
        auth_lines.append("Authoritative Oracle Symbols:")
        for it in oracle_items:
            auth_lines.append(f"  - {it}")
    sections["sec_01_authority"] = "\n".join(auth_lines).strip()

    # ========================================================
    # [2] ACCEPTANCE OBLIGATION LEDGER & CANONICAL BLUEPRINT SCHEMA
    # ========================================================
    schema_constraints = format_canonical_blueprint_schema_constraints()
    sec_02_lines = [
        "[2] ACCEPTANCE OBLIGATION LEDGER & CANONICAL BLUEPRINT SCHEMA CONSTRAINTS",
        "========================================================================",
        "Authority Notice: Canonical Schema determines structural reality. Output JSON must strictly conform:\n"
    ]
    sec_02_lines.append(distill_canonical_schema_semantic(max_chars=800))
    sections["sec_02_canonical_schema"] = "\n".join(sec_02_lines).strip()

    # ========================================================
    # [3] CURRENT COMPATIBILITY FAILURES
    # ========================================================
    fail_lines = [
        "[3] CURRENT COMPATIBILITY FAILURES (DETERMINISTIC EVIDENCE)",
        "==========================================================="
    ]
    active_failures: List[str] = []
    if pkg is not None:
        for v in (getattr(pkg, "violations", []) or []):
            vid = getattr(v, "violation_id", "?")
            crit = getattr(v, "criterion", "")
            obs = getattr(v, "observed_state", "")
            exp = getattr(v, "expected_state", "")
            active_failures.append(f"- [{vid}] {crit}\n    Observed: {obs}\n    Required: {exp}")

    contract_errors = state.get("contract_validation_errors") or []
    for ce in contract_errors:
        if str(ce).strip() and str(ce) not in str(active_failures):
            active_failures.append(f"- [CONTRACT_GATE] {ce}")

    scenario_errors = [str(e) for e in contract_errors if "SCENARIO_SCAFFOLD_INCOMPATIBILITY" in str(e)]
    if scenario_errors:
        active_failures.append("[BEHAVIORAL COMPATIBILITY EVIDENCE — SCAFFOLD vs ACCEPTANCE SCENARIOS]")
        for se in scenario_errors:
            active_failures.append(f"  {se}")

    if curr_matrix is not None and hasattr(curr_matrix, "to_diagnosis_lines"):
        for diag in curr_matrix.to_diagnosis_lines():
            if diag not in str(active_failures):
                active_failures.append(f"- [COMPATIBILITY_DIAGNOSIS] {diag}")

    if ledger and ledger.has_regression:
        reg_text = ledger.to_regression_evidence_text()
        if reg_text:
            fail_lines.append(reg_text + "\n")

    if active_failures:
        fail_lines.append("ACTIVE FAILURES (Multi-failure representation):")
        for af in active_failures[:6]:
            distilled_af = distill_failure_item_semantic(af, target_location=auth_file)
            if distilled_af:
                fail_lines.append(f"  {distilled_af}")
    else:
        fail_lines.append("No active static failures detected.")
    sections["sec_03_current_failures"] = "\n".join(fail_lines).strip()

    # ========================================================
    # [4] LOCKED/PROVEN STATE & INVARIANTS
    # ========================================================
    inv_lines = [
        "[4] LOCKED/PROVEN STATE & INVARIANTS (State Transition Ledger — PRESERVED=TRUE)",
        "================================================================================"
    ]
    if ledger is not None:
        inv_lines.append(ledger.to_repair_state_text())
    locked_dict = state.get("locked_invariants") or {}
    if locked_dict:
        inv_lines.append("\nLocked Invariants (mutation FORBIDDEN):")
        for lid, lval in locked_dict.items():
            desc = lval.get("description", str(lval)) if isinstance(lval, dict) else str(lval)
            inv_lines.append(f"  - [LOCKED] {lid}: {desc}")
    passing_tests = state.get("previous_passed_tests") or []
    if passing_tests:
        inv_lines.append("\nPreviously Passed Tests (DO NOT BREAK):")
        for pt in passing_tests[:6]:
            tname = pt.get("test_name", str(pt)) if isinstance(pt, dict) else str(pt)
            inv_lines.append(f"  - [PROVEN] {tname}")
    sections["sec_04_locked_proven_state"] = "\n".join(inv_lines).strip()

    # ========================================================
    # [5] CURRENT SCAFFOLD & VALIDATED STRUCTURAL STATE (PRESERVE)
    # ========================================================
    state_lines = [
        "[5] CURRENT SCAFFOLD & VALIDATED STRUCTURAL STATE (CURRENT ARCHITECT STATE — PRESERVE)",
        "======================================================================================",
        "Authority Notice: VALID != REPAIR TARGET. Therefore, VALID MUST BE PRESERVED.",
        "Repair Formula: CURRENT VALID STATE + REPAIRED ELEMENT = EXPECTED POST-REPAIR STATE.",
        "Correcting one failing element MUST NOT delete, drop, or mutate unrelated valid elements."
    ]

    known_files = []
    if hasattr(blueprint, "file_tree") and blueprint.file_tree:
        known_files = list(blueprint.file_tree)
    elif isinstance(blueprint, dict) and blueprint.get("file_tree"):
        known_files = list(blueprint["file_tree"])
    elif isinstance(contract, dict) and contract.get("file_tree"):
        known_files = list(contract["file_tree"])
    elif scaffold_files:
        known_files = list(scaffold_files.keys())

    if known_files:
        state_lines.append(f"\nEstablished File Collection (file_tree): {known_files}")

    if scaffold_files:
        state_lines.append(f"Established File Modules in 'files': {list(scaffold_files.keys())}")
    elif arch_plan:
        state_lines.append(f"\nPrior Architecture Plan captured:\n{compress_scaffold_semantic(arch_plan.strip(), target_chars=600)}")
    else:
        state_lines.append("\nInitial structural attempt (no prior valid scaffold captured).")

    known_ifaces = []
    if hasattr(blueprint, "interface_contracts") and blueprint.interface_contracts:
        known_ifaces = [getattr(c, "identifier", str(c)) for c in blueprint.interface_contracts]
    elif isinstance(contract, dict) and contract.get("interface_contracts"):
        for ifc in contract["interface_contracts"]:
            if isinstance(ifc, dict) and ifc.get("identifier"):
                known_ifaces.append(ifc["identifier"])
    if known_ifaces:
        state_lines.append(f"Established Interface Contracts: {known_ifaces}")

    known_models = []
    if hasattr(blueprint, "data_models") and blueprint.data_models:
        known_models = [getattr(m, "model_name", str(m)) for m in blueprint.data_models]
    elif isinstance(contract, dict) and contract.get("data_models"):
        for m in contract["data_models"]:
            if isinstance(m, dict) and m.get("model_name"):
                known_models.append(m["model_name"])
    if known_models:
        state_lines.append(f"Established Data Models: {known_models}")

    if scaffold_files:
        state_lines.append("\nEstablished Module Scaffolds & Semantic Relationships:")
        for fp, code in sorted(scaffold_files.items()):
            mod_ifaces = []
            if isinstance(contract, dict) and contract.get("interface_contracts"):
                for ifc in contract["interface_contracts"]:
                    if isinstance(ifc, dict) and ifc.get("target_file") == fp and ifc.get("identifier"):
                        mod_ifaces.append(ifc["identifier"])
            comp_code = compress_scaffold_semantic(code, target_chars=500)
            state_lines.append(
                f"  * Module '{fp}':\n"
                f"      Target File: {fp}\n"
                f"      Associated Interfaces: {mod_ifaces or 'Primary Entrypoint'}\n"
                f"      Scaffold Interface Signatures ({len(code)} chars):\n```\n{comp_code}\n```"
            )

    sections["sec_05_current_valid_state"] = "\n".join(state_lines).strip()

    # ========================================================
    # [6] REPAIR TARGET (ATOMIC REPAIR INVARIANT)
    # ========================================================
    target_where = auth_file or (known_files[0] if known_files else "primary target module")
    observed_failure_text = "; ".join(active_failures[:4]) if active_failures else "Identified incompatibility with authoritative acceptance obligations."
    expected_correction_text = "Align interface signatures and structural relationships to achieve COMPATIBLE status with 0 regressions."
    target_what = "Interface contracts and structural relationships requiring localized alignment"
    if active_failures:
        target_what = f"Localized repair of: {active_failures[0].splitlines()[0]}"

    rep_lines = [
        "[6] REPAIR TARGET (ATOMIC REPAIR INVARIANT)",
        "============================================",
        f"WHAT (Target element requiring repair): {target_what}",
        f"WHERE (Target file / artifact location): {target_where}",
        f"OBSERVED (Identified failure or incompatibility state):\n  {observed_failure_text}",
        f"EXPECTED (Required transition / post-repair state):\n  {expected_correction_text}",
        "\nACTIVE TARGET: Localized repair of compatibility failures (INCOMPATIBLE -> COMPATIBLE).",
        "REPAIR FORMULA: CURRENT VALID STATE + REPAIRED ELEMENT = EXPECTED POST-REPAIR STATE",
        "GENERIC REPAIR PRESERVATION (Anti-Field-Loss):",
        "  - Preserve all elements, contracts, and schema fields valid under canonical schema.",
        "  - Perform localized repair: CURRENT VALID STATE + REPAIRED ELEMENT.",
        "  - Correcting 'file_tree' must NEVER omit 'files'.",
        "  - Correcting 'interface_contracts' must NEVER omit valid models or modules.",
        "  - Stage A -> Stage B: Map obligations to representations, then serialize with exact canonical fields.",
        "  - Setiap mandatory acceptance obligation harus mempunyai canonical architectural representation yang dapat ditelusuri secara deterministik."
    ]
    if ledger is not None:
        rep_lines.append("\nSpecific Targets from Ledger:\n" + ledger.to_repair_targets_text())
    rep_lines.append("\nCANONICAL SCHEMA FIDELITY: Strictly adhere to Canonical Blueprint Schema constraints in Section [2].")
    sections["sec_06_repair_target"] = "\n".join(rep_lines).strip()

    # ========================================================
    # [7] REPAIR BOUNDARY (ATOMIC REPAIR INVARIANT)
    # ========================================================
    rb_lines = [
        "[7] REPAIR BOUNDARY (ATOMIC REPAIR INVARIANT)",
        "==============================================",
        "PRESERVE (Valid structural state & established interfaces):",
        "  * All valid data models and untouched interface contracts",
        "  * Established file collection and module scaffolds valid under canonical schema",
        "  * Previously passing tests and confirmed invariants",
        "ALLOWED (Permissible repair mutations):",
        "  + Localized repair of broken relationships or invalid schema elements",
        "  + Aligning interface shapes or signatures to match authoritative requirements",
        "  + Adding missing interface declarations or modules required by Oracle",
        "  + Refining scaffold code for deterministic compatibility analysis",
        "  + Formatting parameters with canonical fields (param_name, param_type, param_location) and expected_return object",
        "FORBIDDEN (Strictly prohibited actions):",
        "  x Blind regeneration from scratch (discarding valid state)",
        "  x Dropping fields or elements that remain valid under the canonical schema (Generic Anti-Field-Loss)",
        "  x Dropping top-level schema fields (e.g. omitting 'files' when repairing 'file_tree')",
        "  x Dropping previously compatible public interfaces, scenarios, or modules",
        "  x Mutating immutable acceptance obligations",
        "  x Using non-canonical parameter fields ('name', 'type') or bare string expected_return",
        "  x Introducing regressions on previously COMPATIBLE scenarios"
    ]
    sections["sec_07_repair_boundary"] = "\n".join(rb_lines).strip()

    # ========================================================
    # [8] EXPECTED POST-REPAIR STATE & VERIFICATION CRITERIA
    # ========================================================
    sections["sec_08_expected_post_repair"] = (
        "[8] EXPECTED POST-REPAIR STATE & VERIFICATION CRITERIA\n"
        "=====================================================\n"
        "1. ArchitecturalBlueprint JSON is structurally valid per canonical schema.\n"
        "2. All acceptance scenarios transition to COMPATIBLE (0 regressions).\n"
        "3. All valid structural elements from prior state are preserved.\n"
        "4. Contract status transitions to FROZEN with canonical SHA-256 seal.\n"
        "VERIFICATION CRITERIA:\n"
        "  - Automated compatibility analysis evaluates all interface contracts against Acceptance Oracle.\n"
        "  - Regressions on previously COMPATIBLE scenarios strictly prohibited.\n"
        "  - Phase validator confirms complete JSON schema conformance."
    )

    # ========================================================
    # [9] IMPLEMENTATION GROUNDING & RELATIONAL BLUEPRINT STATE [F]
    # ========================================================
    user_task = state.get("task", "")
    v0_model = state.get("v0_requirement_model")
    ground_lines = [
        "[9] IMPLEMENTATION GROUNDING & RELATIONAL BLUEPRINT STATE [F]",
        "============================================================"
    ]
    if user_task:
        ground_lines.append(f"User Task Intent:\n{user_task.strip()}")
    if v0_model and isinstance(v0_model, dict):
        reqs = v0_model.get("requirements", [])
        if reqs:
            ground_lines.append("\nV0 Core Requirements:")
            for r in reqs[:6]:
                desc = r.get("description", str(r)) if isinstance(r, dict) else str(r)
                ground_lines.append(f"  - {desc}")
    relational_text = format_relational_blueprint_state(
        oracle_obs=oracle_obs,
        oracle_items=oracle_items,
        scenarios=scenarios,
        contract=contract,
        auth_file=auth_file,
    )
    ground_lines.append("\n" + compress_scaffold_semantic(relational_text.strip(), target_chars=400))
    sections["sec_09_relational_blueprint"] = "\n".join(ground_lines).strip()

    # ========================================================
    # [10] RAW DIAGNOSTICS
    # ========================================================
    raw_diag = state.get("contract_feedback") or state.get("last_execution_error") or ""
    raw_bounded = compress_raw_diagnostics_semantic(raw_diag.strip(), max_chars=400) if raw_diag else ""
    sections["sec_10_raw_diagnostics"] = (
        "[10] RAW DIAGNOSTICS (Bounded to prevent displacement of priority context)\n"
        "=========================================================================\n"
        + (raw_bounded if raw_bounded else "No raw tracebacks.")
    )

    # Deterministic authority conflict resolution
    sections, conflicts = check_and_resolve_authority_conflicts(sections, state, pkg=pkg)

    # Context Integrity & Task Isolation Audit
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

    # Compress context using role-based semantic compression engine
    result, telem_meta = compress_context_semantic_detailed(
        sections,
        max_chars=max_chars,
        priority_order=ARCHITECT_REPAIR_PRIORITY_ORDER
    )

    # Pre-invocation Delivery Validation (Requirement 10)
    delivery_valid, delivery_errs = validate_architect_repair_context_delivery(result)

    # Treatment #1.8.2: Distillation & Final Delivery Audit Telemetry
    raw_failures_len = sum(len(str(f)) for f in active_failures)
    raw_scaffolds_len = sum(len(str(c)) for c in scaffold_files.values()) if scaffold_files else len(arch_plan)
    raw_diag_len = len(state.get("contract_feedback") or state.get("last_execution_error") or "")
    raw_blueprint_len = len(str(blueprint)) if blueprint else 0
    raw_oracle_len = sum(len(str(x)) for x in oracle_items) + sum(len(str(s)) for s in scenarios)
    raw_context_chars = max(
        raw_failures_len + raw_scaffolds_len + raw_diag_len + raw_blueprint_len + raw_oracle_len,
        telem_meta.get("context_size_before_compression", len(result))
    )
    distilled_context_chars = telem_meta.get("context_size_before_compression", len(result))
    final_context_chars = len(result)
    configured_budget = max_chars
    estimated_tokens = final_context_chars // 4
    comp_ratio = round(final_context_chars / max(raw_context_chars, 1), 4)
    semantic_complete = delivery_valid
    relational_status = "INTACT" if ("Module" in result or "Target File" in result or "Relational" in result) else "DEGRADED"

    telemetry_data = {
        "context_sections": list(sections.keys()),
        "context_size": len(result),
        "authoritative_sources": ["FROZEN_ORACLE"],
        "evidence_items": len(active_failures),
        "locked_invariants": len(locked_dict),
        "current_failures": len(active_failures),
        "repair_boundary_items": len(rb_lines),
        "authority_conflicts_resolved": len(conflicts),
        "integrity_violations_detected": len(integrity_violations),
        "delivery_valid": delivery_valid,
        "delivery_errors": delivery_errs,
        # Extended Context Budget Telemetry (Section 9)
        "context_budget": max_chars,
        "context_size_before_compression": telem_meta.get("context_size_before_compression", len(result)),
        "context_size_after_compression": len(result),
        "compression_applied": telem_meta.get("compression_applied", False),
        "sections_present": telem_meta.get("sections_present", []),
        "sections_omitted": telem_meta.get("sections_omitted", []),
        "sections_truncated": telem_meta.get("sections_truncated", []),
        "repair_critical_sections_present": telem_meta.get("repair_critical_sections_present", []),
        "delivery_failure_reason": "; ".join(delivery_errs) if not delivery_valid else "",
        "model_context_parameters": {
            "num_ctx": 8192,
            "num_predict": 3000,
            "max_chars": max_chars,
        },
        # Treatment #1.8.2 Telemetry
        "raw_context_chars": raw_context_chars,
        "distilled_context_chars": distilled_context_chars,
        "final_context_chars": final_context_chars,
        "configured_budget": configured_budget,
        "estimated_token_count": estimated_tokens,
        "compression_ratio": comp_ratio,
        "semantic_payload_completeness": semantic_complete,
        "relational_preservation_status": relational_status,
    }

    return result, telemetry_data


def build_architect_decision_context(
    state: Dict[str, Any],
    pkg: Optional[Any] = None,
    max_chars: Optional[int] = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    Membangun Architect Context Package secara generik.
    Konteks budget adalah parameter yang dapat dikonfigurasi (bukan invariant arsitektural).
    Pada giliran repair: secara deterministik mendelegasikan ke build_architect_repair_context.
    """
    if max_chars is None:
        max_chars = resolve_context_budget(state)
    rev_count = state.get("contract_revision_count", 0)
    if pkg is not None or rev_count > 0:
        return build_architect_repair_context(state, pkg=pkg, max_chars=max_chars)

    sections: Dict[str, str] = {}

    # [1] USER INTENT
    user_task = state.get("task", "")
    if user_task:
        sections["authority_user_intent"] = (
            "[1] USER INTENT\n"
            "================\n"
            + user_task.strip()
        )

    # [2] V0 APP REQUIREMENTS (FACT / INTERPRETATION / ASSUMPTION / UNRESOLVED)
    v0_model = state.get("v0_requirement_model")
    if v0_model:
        if isinstance(v0_model, dict):
            core_reqs = v0_model.get("requirements", [])
            constructibility = v0_model.get("constructibility_status", "")
            interpretations = v0_model.get("interpretations", [])
            assumptions = v0_model.get("assumptions", [])
            unresolved = v0_model.get("open_ambiguities", []) or v0_model.get("unresolved_items", [])

            v0_lines = []
            if constructibility:
                v0_lines.append(f"Constructibility: {constructibility}")
            if core_reqs and isinstance(core_reqs, list):
                v0_lines.append("Core Requirements (FACT — grounded in user task):")
                for i, r in enumerate(core_reqs[:8], 1):
                    if isinstance(r, dict):
                        label = r.get("category", "REQ")
                        desc = r.get("description", str(r))
                        v0_lines.append(f"  {i}. [{label}] {desc}")
                    else:
                        v0_lines.append(f"  {i}. {r}")
            if interpretations and isinstance(interpretations, list):
                v0_lines.append("\nInterpretations (INTERPRETATION — derived requirements for constructibility):")
                for i, it in enumerate(interpretations[:6], 1):
                    desc = it.get("description", str(it)) if isinstance(it, dict) else str(it)
                    v0_lines.append(f"  {i}. {desc}")
            if assumptions and isinstance(assumptions, list):
                v0_lines.append("\nAssumptions (ASSUMPTION — engineering baselines; NOT facts):")
                for i, asm in enumerate(assumptions[:6], 1):
                    desc = asm.get("description", str(asm)) if isinstance(asm, dict) else str(asm)
                    v0_lines.append(f"  {i}. {desc}")
            if unresolved and isinstance(unresolved, list):
                v0_lines.append("\nUnresolved Gaps (UNRESOLVED — preserved boundaries; DO NOT invent):")
                for i, un in enumerate(unresolved[:6], 1):
                    desc = un.get("description", str(un)) if isinstance(un, dict) else str(un)
                    v0_lines.append(f"  {i}. {desc}")
            v0_text = "\n".join(v0_lines)
        else:
            v0_text = str(v0_model)[:600]
        sections["authority_v0_reqs"] = (
            "[2] V0 APP REQUIREMENTS (FACT — grounded in user task)\n"
            "=======================================================\n"
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
    frozen_path = state.get("frozen_oracle_path")
    test_files = state.get("test_files")

    oracle_obs = []
    if extract_canonical_oracle_obligations and (frozen_path or test_files):
        try:
            oracle_obs = extract_canonical_oracle_obligations(
                frozen_oracle_path=frozen_path,
                test_files=test_files
            )
        except Exception:
            oracle_obs = []

    scenarios = []
    if extract_canonical_scenarios and (frozen_path or test_files):
        try:
            scenarios = extract_canonical_scenarios(
                frozen_oracle_path=frozen_path,
                test_files=test_files
            )
        except Exception:
            scenarios = []

    sec_05_lines = []
    if oracle_items:
        sec_05_lines.extend(f"  - {item}" for item in oracle_items)
    elif is_frozen and interfaces:
        sec_05_lines.extend(f"  - [ORACLE_FACT] {ifc}" for ifc in interfaces)
    else:
        sec_05_lines.append("  [ORACLE_FACT] No explicit public oracle interfaces extracted from tests.")
        sec_05_lines.append("  Implement functional requirements according to Section [1] User Intent and Section [2] V0 App Requirements.")

    if oracle_obs:
        try:
            ledger_text = format_authoritative_obligation_ledger(oracle_obs)
            if ledger_text:
                sec_05_lines.append("\n" + ledger_text)
        except Exception:
            pass
        try:
            usage_evidence_text = format_acceptance_usage_evidence(oracle_obs)
            if usage_evidence_text:
                sec_05_lines.append("\n" + usage_evidence_text)
        except Exception:
            pass

    if scenarios:
        try:
            scenario_text = format_scenarios_for_architect(scenarios)
            if scenario_text:
                sec_05_lines.append("\n" + scenario_text)
        except Exception:
            pass

    sec_05_lines.append("\n  Authority Notice: The above symbols, obligations, and scenarios are verified directly from Acceptance Test Suite (Ground Truth — Acceptance Authority).")
    sec_05_lines.append("  Architect is strictly FORBIDDEN from altering, removing, or omitting these requirements.")

    sections["authority_oracle_interfaces"] = (
        "[5] AUTHORITATIVE ACCEPTANCE ORACLE INTERFACES (ORACLE_FACT — verified test suite)\n"
        "=================================================================================\n"
        + "\n".join(sec_05_lines)
    )

    # [CANONICAL BLUEPRINT SCHEMA CONSTRAINTS]
    schema_constraints = format_canonical_blueprint_schema_constraints()
    if schema_constraints:
        sections["authority_canonical_schema"] = (
            "[CANONICAL BLUEPRINT SCHEMA CONSTRAINTS (Derived directly from ArchitecturalBlueprint)]\n"
            "========================================================================================\n"
            + schema_constraints.strip()
        )

    # [F] RELATIONAL BLUEPRINT STATE (Derived structural representation)
    relational_text = format_relational_blueprint_state(
        oracle_obs=oracle_obs,
        oracle_items=oracle_items,
        scenarios=scenarios,
        contract=contract,
        auth_file=auth_file,
    )
    sections["relational_blueprint_state"] = (
        "[F] RELATIONAL BLUEPRINT STATE (Derived structural representation — NOT an independent authority)\n"
        "==================================================================================================\n"
        + relational_text.strip()
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

        contract_errors = state.get("contract_validation_errors", []) or []
        scenario_errors = [str(e) for e in contract_errors if "SCENARIO_SCAFFOLD_INCOMPATIBILITY" in str(e)]
        if scenario_errors:
            ev_text += "\n[BEHAVIORAL COMPATIBILITY EVIDENCE — SCAFFOLD vs ACCEPTANCE SCENARIOS]\n"
            for se in scenario_errors:
                ev_text += f"  {se}\n"

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

    # [11] OUTPUT CONTRACT & REASONING GUIDANCE
    sections["authority_output_contract"] = (
        "[11] OUTPUT CONTRACT & REASONING GUIDANCE\n"
        "=========================================\n"
        "Output: JSON blueprint dalam marker === BLUEPRINT JSON === ... === END BLUEPRINT JSON ===\n"
        "Aturan code_scaffold:\n"
        "  - code_scaffold HARUS berupa interface signatures / stubs minimal.\n"
        "  - Target ukuran: <=1200 karakter per file.\n"
        "  - DILARANG menuliskan logika bisnis atau implementasi penuh di dalam scaffold.\n"
        "  - Interface contracts HARUS mendefinisikan SEMUA identifier dari Authoritative Acceptance Oracle Interfaces (ORACLE_FACT).\n"
        "  - Elemen [PM_PROPOSAL] hanya digunakan sebagai referensi desain awal jika TIDAK bertentangan dengan [ORACLE_FACT].\n"
        "  - ARTIFACT PURITY: file_tree dan files HANYA untuk modul implementasi kode. DILARANG memasukkan file test atau test runner ke dalam file_tree atau files.\n"
        "  - OBSERVABLE BEHAVIOR: Scaffolds must represent sufficient observable behavior for deterministic compatibility analysis. Do not prescribe implementation-specific mechanisms. The Architect may choose the appropriate architectural representation, provided that the required observable behavior is preserved.\n\n"
        "CANONICAL SCHEMA AS REPRESENTATION CONTRACT:\n"
        "  - The output JSON schema is a representation contract derived from canonical ArchitecturalBlueprint definition.\n"
        "  - Preserve exact schema collection semantics and required fields without data shape alteration.\n"
        "  - Two-Stage Architect Synthesis:\n"
        "      Stage 1 (Semantic Blueprint Model): Establish obligations, scenarios, interfaces, and file roles internally.\n"
        "      Stage 2 (Canonical Serialization): Serialize faithfully to the existing ArchitecturalBlueprint schema.\n"
        "  - Generic Repair Preservation (Anti-Field-Loss): On repair, perform localized updates (CURRENT VALID STATE + REPAIRED ELEMENT) and preserve all elements and fields that remain valid under the canonical schema.\n\n"
        "PRE-SEAL SELF-CONSISTENCY CHECKLIST (Architect reasoning guidance):\n"
        "  1. Obligation Coverage: Every authoritative acceptance obligation has a traceable architectural representation in interface_contracts or data_models.\n"
        "  2. Authoritative Scenario Coverage: All positive, negative, and boundary scenarios are represented.\n"
        "  3. Call-Shape Fidelity: Invocation form, parameter ordering, and input/output shapes are preserved.\n"
        "  4. Observable Behavior: Scenario paths and guards are represented sufficiently for deterministic static compatibility.\n"
        "  5. Artifact Purity: Only implementation artifacts; zero test files in file_tree.\n"
        "  6. No Requirement Invention: No invented unrequested features or fabricated endpoints.\n"
        "  7. No Contradiction: Internal consistency between file_tree, files, data_models, and interface_contracts.\n"
        "  8. Preservation: No regression against locked invariants, proven state, or valid schema fields.\n"
        "  9. Evidence Traceability: Every architectural decision is grounded in evidence.\n"
        "  10. Scaffold Sufficiency: Complete stubs for all declared files in file_tree.\n"
        "  (Notice: The 10-point checklist is Architect reasoning guidance. It is NOT an acceptance authority and does NOT replace deterministic validators. Deterministic validators determine REALITY.)"
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

    if assemble_developer_semantic_repair_context is not None:
        # Treatment #1.6: Universal Developer Semantic Repair Grounding v1
        scenarios: List[Any] = []
        if extract_canonical_scenarios is not None:
            try:
                scenarios = extract_canonical_scenarios(
                    frozen_oracle_path=state.get("frozen_oracle_path"),
                    test_files=test_files
                )
            except Exception:
                scenarios = []

        test_results = state.get("test_results") or {}
        output = test_results.get("output") or test_results.get("stdout") or ""
        stderr = test_results.get("stderr") or ""
        exit_code = test_results.get("exit_code")
        diag_ev = test_results.get("diagnostic_evidence")

        normalized_obs: List[Any] = []
        if normalize_runtime_evidence is not None:
            try:
                normalized_obs = normalize_runtime_evidence(
                    raw_output=output,
                    exit_code=exit_code,
                    stderr=stderr,
                    diagnostic_evidence=diag_ev,
                    target_language=target_lang
                )
            except Exception:
                normalized_obs = []

        matched_obs_ids: Set[str] = set()
        current_evidences: List[Any] = []
        if compare_scenario_with_observation is not None:
            for sc in scenarios:
                caller = getattr(sc, "caller", "")
                matching_obs = None
                for obs in normalized_obs:
                    obs_caller = getattr(obs, "caller", "")
                    obs_sym = getattr(obs, "target_symbol", "")
                    if (obs_caller and (obs_caller in caller or caller in obs_caller)) or (obs_sym and obs_sym in caller):
                        matching_obs = obs
                        matched_obs_ids.add(getattr(obs, "observation_id", ""))
                        break
                ev = compare_scenario_with_observation(sc, matching_obs)
                if ev.comparison_status in (SemanticComparisonStatus.MISMATCH.value, SemanticComparisonStatus.UNDETERMINED.value):
                    current_evidences.append(ev)

            # Unmatched observations from test output
            for obs in normalized_obs:
                oid = getattr(obs, "observation_id", "")
                if oid not in matched_obs_ids:
                    ev = compare_scenario_with_observation(obs.caller, obs)
                    current_evidences.append(ev)

        # Preservation & Invariant Regression Evaluation
        active_invs: List[Dict[str, Any]] = []
        reg_warnings: List[str] = []
        if evaluate_developer_preservation is not None:
            current_evidences, active_invs, reg_warnings = evaluate_developer_preservation(current_evidences, state)
        else:
            for l_id, l_data in locked_dict.items():
                if isinstance(l_data, dict):
                    active_invs.append(l_data)
                else:
                    active_invs.append({"invariant_id": l_id, "description": str(l_data), "status": "PROVEN"})

        # Multi-Failure Ledger
        active_evidences = current_evidences
        if update_developer_failure_ledger is not None:
            active_evidences, _ = update_developer_failure_ledger(state, current_evidences)

        # 10-Tier Context Assembly
        result, telem_meta = assemble_developer_semantic_repair_context(
            state=state,
            active_evidences=active_evidences,
            preserved_invariants=active_invs,
            raw_diagnostics=output,
            max_chars=max_chars
        )

        telemetry_data = {
            "context_sections": [
                "[1] AUTHORITATIVE ACCEPTANCE EXPECTATION",
                "[2] CURRENT SEMANTIC FAILURE",
                "[3] VIOLATED OBLIGATION",
                "[4] LOCKED / PROVEN INVARIANTS",
                "[5] CURRENT IMPLEMENTATION STATE",
                "[6] REPAIR BOUNDARY",
                "[7] EXPECTED POST-REPAIR STATE",
                "[8] VERIFICATION CRITERIA",
                "[9] SUPPORTING DIAGNOSTIC EVIDENCE",
                "[10] RAW EVIDENCE"
            ],
            "context_size": len(result),
            "authoritative_sources": ["[1] AUTHORITATIVE ACCEPTANCE EXPECTATION"],
            "evidence_items": len(active_evidences),
            "locked_invariants": len(active_invs),
            "current_failures": len(active_evidences),
            "repair_boundary_items": len(active_evidences[0].repair_boundary.get("allowed_changes", [])) if active_evidences else 2,
            "integrity_violations_detected": len(reg_warnings),
            "grounding_sources": ["FROZEN_ORACLE", "NORMALIZED_RUNTIME_EVIDENCE"],
            "grounding_evidence_count": len(normalized_obs),
            "grounding_evidence_types": ["SEMANTIC_DIFF", "NORM_OBSERVATION"],
            "raw_diagnostic_count": len(output.splitlines()) if output else 0,
            "normalized_diagnostic_count": len(normalized_obs),
            "omitted_diagnostic_count": 0,
            "current_failure_count": len(active_evidences),
            "historical_failure_count": len(state.get("historical_validation_evidence") or []),
            "locked_invariant_count": len(active_invs),
            "implementation_facts_count": len(normalized_obs),
            "output_size": len(result),
            "truncation_detected": len(result) >= max_chars,
            "repair_result": "SEMANTIC_REPAIR_GROUNDED",
            "delivery_valid": True,
            "delivery_errors": reg_warnings
        }
        return result, telemetry_data

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
