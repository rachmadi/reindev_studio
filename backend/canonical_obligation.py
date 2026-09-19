# -*- coding: utf-8 -*-
"""
Canonical Acceptance Obligation Representation & Coverage Checker
ReinDev Studio — Architect Contract Binding v2

PRINSIP NON-NEGOTIABLE & DOKTRIN ARSITEKTURAL:
1. Oracle adalah IMMUTABLE ACCEPTANCE AUTHORITY (WHAT).
2. Architect adalah DESIGN AUTHORITY (HOW).
3. Provenance eksklusif: HANYA ORACLE_FACT yang memegang otoritas penerimaan.
4. Koreksi 1: 100% Coverage bukan 100% string equality naif; coverage membuktikan
   kompatibilitas struktural/semantik deterministik antara obligasi dan kontrak.
5. Koreksi 2: Language Adapters murni PARSE -> NORMALIZE -> REPRESENT (Dilarang INVENT/SOLVE).
6. Koreksi 3: Coverage Engine & CEP hanya memberikan DIAGNOSIS (WHAT is missing/incompatible),
   BUKAN DESAIN SOLUSI (HOW to implement).
7. Invariant: CANONICAL OBLIGATION INTEGRITY. Obligasi dari immutable Oracle tidak boleh
   dimutasi, dipangkas, atau diturunkan ulang dari rejected artifacts.
8. Aturan Utama:
   "No FROZEN unless every mandatory immutable Oracle obligation has deterministic evidence
   of COVERED compatibility with the proposed public acceptance contract, with no unresolved
   or incompatible obligation."
"""

from __future__ import annotations

import ast
import os
import re
from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

try:
    from .canonical_scenario import (
        CanonicalScenario,
        BehavioralObservation,
        ScenarioKind,
        ComparisonStatus,
        CausalStatus,
        extract_canonical_scenarios,
        evaluate_behavioral_observations,
        format_scenarios_for_architect,
        format_behavioral_mismatches_for_developer,
        ScaffoldCompatibilityStatus,
        ScaffoldStructuralStatus,
        ScaffoldBehavioralStatus,
        ScaffoldCallableFact,
        ScaffoldScenarioCompatibilityItem,
        ScaffoldScenarioMatrix,
        evaluate_scaffold_scenario_compatibility,
        format_scaffold_compatibility_for_architect,
        extract_all_scaffold_facts,
    )
except (ImportError, ValueError):
    try:
        from canonical_scenario import (
            CanonicalScenario,
            BehavioralObservation,
            ScenarioKind,
            ComparisonStatus,
            CausalStatus,
            extract_canonical_scenarios,
            evaluate_behavioral_observations,
            format_scenarios_for_architect,
            format_behavioral_mismatches_for_developer,
            ScaffoldCompatibilityStatus,
            ScaffoldStructuralStatus,
            ScaffoldBehavioralStatus,
            ScaffoldCallableFact,
            ScaffoldScenarioCompatibilityItem,
            ScaffoldScenarioMatrix,
            evaluate_scaffold_scenario_compatibility,
            format_scaffold_compatibility_for_architect,
            extract_all_scaffold_facts,
        )
    except ImportError:
        pass


# ===========================================================================
# 1. Custom Exceptions
# ===========================================================================

class CanonicalObligationIntegrityError(Exception):
    """Dilempar jika integritas atau provenance CanonicalObligation dilanggar."""
    pass


# ===========================================================================
# 2. Canonical Enums & Constants
# ===========================================================================

class ObligationAuthority(str, Enum):
    ORACLE = "FROZEN_ORACLE"
    FROZEN_ORACLE = "FROZEN_ORACLE"
    PM = "PM"
    ARCHITECT = "ARCHITECT"


class ObligationProvenance(str, Enum):
    ORACLE_FACT = "ORACLE_FACT"
    PM_PROPOSAL = "PM_PROPOSAL"
    ARCHITECT_INFERENCE = "ARCHITECT_INFERENCE"


class ObligationKind(str, Enum):
    CALLABLE_INTERFACE = "CALLABLE_INTERFACE"
    DATA_MODEL = "DATA_MODEL"
    INTERACTION = "INTERACTION"
    BEHAVIORAL = "BEHAVIORAL"
    OBSERVABLE_RUNTIME = "OBSERVABLE_RUNTIME"
    UNKNOWN = "UNKNOWN"


class InvocationKind(str, Enum):
    CALL = "CALL"
    CONSTRUCTOR = "CONSTRUCTOR"
    FUNCTION = "FUNCTION"
    METHOD = "METHOD"
    UNKNOWN = "UNKNOWN"


class EpistemicStatus(str, Enum):
    PROVEN_FACT = "PROVEN_FACT"
    HEURISTIC = "HEURISTIC"
    UNKNOWN = "UNKNOWN"


class CoverageStatus(str, Enum):
    COVERED = "COVERED"
    PARTIALLY_COVERED = "PARTIALLY_COVERED"
    MISSING = "MISSING"
    INCOMPATIBLE = "INCOMPATIBLE"
    UNDETERMINED = "UNDETERMINED"


class AuthorityMismatchDimension(str, Enum):
    SEMANTIC_IDENTITY = "SEMANTIC_IDENTITY"
    CALLABLE_IDENTITY = "CALLABLE_IDENTITY"
    PARAMETER_IDENTITY = "PARAMETER_IDENTITY"
    PARAMETER_TYPE = "PARAMETER_TYPE"
    RETURN_IDENTITY = "RETURN_IDENTITY"
    TARGET_ARTIFACT = "TARGET_ARTIFACT"
    ROUTE_METHOD = "ROUTE_METHOD"
    AMBIGUOUS_MATCH = "AMBIGUOUS_MATCH"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


@dataclass(frozen=True)
class AuthorityBindingEvidence:
    """
    Bukti diagnosis deterministik authority binding.
    Memuat WHAT yang inkompatibel atau tidak selaras dengan Frozen Acceptance Authority,
    tanpa memberikan instruksi atau preskripsi HOW to implement.
    """
    authority_source: str = "FROZEN_ACCEPTANCE_ORACLE"
    obligation_id: str = ""
    authoritative_value: Any = ""
    blueprint_value: Any = ""
    mismatch_dimension: Union[AuthorityMismatchDimension, str] = ""
    affected_element: str = ""
    status: str = "INCOMPATIBLE"
    reason: str = ""
    authority_symbol: Optional[str] = None
    blueprint_symbol: Optional[str] = None
    expected_value: Any = None
    actual_value: Any = None
    target_artifact: Optional[str] = None

    def to_diagnostic_block(self) -> str:
        auth_val = self.expected_value if self.expected_value is not None else self.authoritative_value
        blue_val = self.actual_value if self.actual_value is not None else self.blueprint_value
        dim_str = self.mismatch_dimension.value if isinstance(self.mismatch_dimension, AuthorityMismatchDimension) else str(self.mismatch_dimension)
        lines = [
            "AUTHORITY_BINDING_DIAGNOSTIC:",
            f"- Authority Source: {self.authority_source}",
            f"- Obligation ID: {self.obligation_id or self.authority_symbol or 'UNKNOWN'}",
            f"- Mismatch Dimension: {dim_str}",
            f"- Authoritative Expected: {auth_val}",
            f"- Blueprint Provided: {blue_val}",
        ]
        if self.blueprint_symbol:
            lines.append(f"- Blueprint Symbol: {self.blueprint_symbol}")
        if self.target_artifact:
            lines.append(f"- Target Artifact: {self.target_artifact}")
        if self.reason:
            lines.append(f"- Reason: {self.reason}")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "authority_source": self.authority_source,
            "obligation_id": self.obligation_id,
            "authority_symbol": self.authority_symbol,
            "blueprint_symbol": self.blueprint_symbol,
            "mismatch_dimension": self.mismatch_dimension.value if isinstance(self.mismatch_dimension, AuthorityMismatchDimension) else str(self.mismatch_dimension),
            "authoritative_value": str(self.expected_value if self.expected_value is not None else self.authoritative_value),
            "blueprint_value": str(self.actual_value if self.actual_value is not None else self.blueprint_value),
            "status": self.status,
            "reason": self.reason,
            "target_artifact": self.target_artifact
        }



# ===========================================================================
# 3. Canonical Acceptance Obligation Dataclass
# ===========================================================================

@dataclass(frozen=True)
class CanonicalObligation:
    """
    Representasi kanonikal deterministik dari sebuah obligasi penerimaan Oracle.
    Frozen untuk menjamin imutabilitas (CANONICAL OBLIGATION INTEGRITY).
    Mendefinisikan WHAT yang wajib dipenuhi oleh kontrak publik tanpa mendikte HOW.
    """
    obligation_id: str
    authority: str = ObligationAuthority.FROZEN_ORACLE.value
    provenance: str = ObligationProvenance.ORACLE_FACT.value
    obligation_kind: str = ObligationKind.CALLABLE_INTERFACE.value
    public_identity: str = ""
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    observable_behavior: str = ""
    acceptance_evidence: str = ""
    source_reference: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    # First-Class Acceptance Usage & Call Shape Evidence (Treatment #1.2)
    invocation_kind: str = InvocationKind.UNKNOWN.value
    caller: str = ""
    callee: str = ""
    positional_arguments: int = 0
    keyword_arguments: List[str] = field(default_factory=list)
    argument_count: int = 0
    argument_names: List[str] = field(default_factory=list)
    epistemic_status: str = EpistemicStatus.PROVEN_FACT.value

    def __post_init__(self):
        # Penegakan Invariant: Otoritas ORACLE / FROZEN_ORACLE WAJIB ber-provenance ORACLE_FACT
        if self.authority in (ObligationAuthority.ORACLE.value, ObligationAuthority.FROZEN_ORACLE.value, "ORACLE", "FROZEN_ORACLE"):
            if self.provenance != ObligationProvenance.ORACLE_FACT.value:
                raise CanonicalObligationIntegrityError(
                    f"Violation of Canonical Obligation Integrity: Authority {self.authority} "
                    f"must have provenance ORACLE_FACT, got '{self.provenance}' on {self.obligation_id}"
                )
        if not self.obligation_id:
            raise CanonicalObligationIntegrityError("obligation_id cannot be empty")
        if not self.public_identity:
            raise CanonicalObligationIntegrityError("public_identity cannot be empty")
        if not self.callee and self.public_identity:
            object.__setattr__(self, "callee", self.public_identity)
        if not self.argument_count and (self.positional_arguments or self.keyword_arguments):
            object.__setattr__(self, "argument_count", self.positional_arguments + len(self.keyword_arguments))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "obligation_id": self.obligation_id,
            "authority": self.authority,
            "provenance": self.provenance,
            "obligation_kind": self.obligation_kind,
            "public_identity": self.public_identity,
            "inputs": dict(self.inputs),
            "outputs": dict(self.outputs),
            "observable_behavior": self.observable_behavior,
            "acceptance_evidence": self.acceptance_evidence,
            "source_reference": self.source_reference,
            "metadata": dict(self.metadata),
            "invocation_kind": self.invocation_kind,
            "caller": self.caller,
            "callee": self.callee,
            "positional_arguments": self.positional_arguments,
            "keyword_arguments": list(self.keyword_arguments),
            "argument_count": self.argument_count,
            "argument_names": list(self.argument_names),
            "epistemic_status": self.epistemic_status,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> CanonicalObligation:
        return cls(
            obligation_id=d.get("obligation_id", ""),
            authority=d.get("authority", ObligationAuthority.ORACLE.value),
            provenance=d.get("provenance", ObligationProvenance.ORACLE_FACT.value),
            obligation_kind=d.get("obligation_kind", ObligationKind.CALLABLE_INTERFACE.value),
            public_identity=d.get("public_identity", ""),
            inputs=dict(d.get("inputs") or {}),
            outputs=dict(d.get("outputs") or {}),
            observable_behavior=d.get("observable_behavior", ""),
            acceptance_evidence=d.get("acceptance_evidence", ""),
            source_reference=d.get("source_reference", ""),
            metadata=dict(d.get("metadata") or {}),
            invocation_kind=d.get("invocation_kind", InvocationKind.UNKNOWN.value),
            caller=d.get("caller", ""),
            callee=d.get("callee", ""),
            positional_arguments=d.get("positional_arguments", 0),
            keyword_arguments=list(d.get("keyword_arguments") or []),
            argument_count=d.get("argument_count", 0),
            argument_names=list(d.get("argument_names") or []),
            epistemic_status=d.get("epistemic_status", EpistemicStatus.PROVEN_FACT.value),
        )

    def to_prompt_line(self) -> str:
        """
        Format ringkas untuk injeksi ke context prompt Architect (WHAT, bukan HOW).
        HANYA menyatakan public identity, kind, inputs/outputs, dan observable behavior.
        TIDAK membocorkan kode atau instruksi implementasi.
        """
        extra_info = []
        if self.inputs:
            if "http_method" in self.inputs:
                extra_info.append(f"HTTP Method: {self.inputs['http_method']}")
            elif "parameters" in self.inputs:
                extra_info.append(f"Expected Parameters: {self.inputs['parameters']}")
        if self.outputs:
            if "expected_status" in self.outputs:
                extra_info.append(f"Expected Status: {self.outputs['expected_status']}")
            elif "return_type" in self.outputs:
                extra_info.append(f"Expected Return: {self.outputs['return_type']}")
        if self.invocation_kind and self.invocation_kind != InvocationKind.UNKNOWN.value:
            extra_info.append(f"Invocation: {self.invocation_kind}")
        if self.positional_arguments:
            extra_info.append(f"Positional Args: {self.positional_arguments}")
        if self.keyword_arguments:
            extra_info.append(f"Keyword Args: {self.keyword_arguments}")
        if self.caller:
            extra_info.append(f"Caller: {self.caller}")

        extra_str = f" ({', '.join(extra_info)})" if extra_info else ""
        return (
            f"  - [{self.provenance}] {self.obligation_id}: "
            f"[{self.obligation_kind}] '{self.public_identity}'{extra_str} "
            f"— {self.observable_behavior}"
        )


def normalize_route_path(path: str) -> str:
    """
    Menormalkan path HTTP untuk mempertahankan distinct public identities:
    - Menghilangkan query string dan trailing slash (kecuali root '/')
    - Memetakan segmen parameter '{...}' atau literal numeric id menjadi '{id}'
    - Contoh:
        '/products' -> '/products'
        '/products/' -> '/products'
        '/products/{id}' -> '/products/{id}'
        '/products/{prod_id}' -> '/products/{id}'
        '/products/999999' -> '/products/{id}'
        '/' -> '/'
    """
    if not path:
        return "/"
    path = path.split("?")[0].strip()
    if not path.startswith("/"):
        path = "/" + path
    parts = [p for p in path.split("/") if p]
    if not parts:
        return "/"

    norm_parts = []
    for p in parts:
        if (p.startswith("{") and p.endswith("}")) or p.isdigit():
            norm_parts.append("{id}")
        else:
            norm_parts.append(p)
    return "/" + "/".join(norm_parts)


@dataclass
class CanonicalInterfaceDeclaration:
    """
    Representasi kanonikal tunggal untuk interface contract yang dideklarasikan Architect.
    Menjamin Coverage Engine bekerja di atas bentuk kanonikal yang seragam tanpa bergantung
    pada variasi nama field (seperti 'method' vs 'http_method').
    """
    identifier: str
    target_file: str = ""
    interface_type: str = ""
    canonical_route: Optional[str] = None
    canonical_method: Optional[str] = None  # Uppercase string (misal: 'GET', 'POST') atau None
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    raw_declaration: Dict[str, Any] = field(default_factory=dict)


def normalize_interface_declaration(raw_ifc: Any) -> Optional[CanonicalInterfaceDeclaration]:
    """
    Normalisasi satu deklarasi interface contract ke CanonicalInterfaceDeclaration.
    Mengekstrak method kanonikal dari 'method' atau 'http_method' dan route kanonikal.
    """
    if not isinstance(raw_ifc, dict):
        if hasattr(raw_ifc, "model_dump"):
            raw_ifc = raw_ifc.model_dump()
        elif hasattr(raw_ifc, "to_dict"):
            raw_ifc = raw_ifc.to_dict()
        elif isinstance(raw_ifc, str):
            raw_ifc = {"identifier": raw_ifc.strip(), "interface_id": raw_ifc.strip()}
        else:
            return None

    ident = str(raw_ifc.get("identifier") or raw_ifc.get("name") or raw_ifc.get("interface_id") or "").strip()
    itype = str(raw_ifc.get("interface_type", "")).upper().strip()
    target_file = str(raw_ifc.get("target_file", "")).strip()

    # Canonical HTTP method: konsolidasi 'http_method' dan 'method' ke satu nilai kanonikal
    raw_m = raw_ifc.get("http_method") or raw_ifc.get("method")
    canonical_m = str(raw_m).upper().strip() if raw_m else None

    # Canonical route:
    raw_route = raw_ifc.get("route") or raw_ifc.get("path") or raw_ifc.get("endpoint")
    if not raw_route and (itype == "HTTP_ENDPOINT" or ident.startswith("/")):
        raw_route = ident
    canonical_r = normalize_route_path(str(raw_route)) if raw_route else None

    return CanonicalInterfaceDeclaration(
        identifier=ident,
        target_file=target_file,
        interface_type=itype,
        canonical_route=canonical_r,
        canonical_method=canonical_m,
        parameters=raw_ifc.get("parameters") or [],
        raw_declaration=raw_ifc
    )


def find_deterministic_callable_fact(
    identifier: str,
    target_file: Optional[str],
    facts: List[ScaffoldCallableFact]
) -> Optional[ScaffoldCallableFact]:
    """
    Mencari ScaffoldCallableFact deterministik untuk sebuah callable identifier.
    Aturan Epistemik (Treatment #1.8.10 Part A):
    1. Identitas callable harus cocok secara eksak (name == identifier).
    2. Jika target_file didefinisikan, harus cocok dengan file_path fakta (jika fakta mencantumkan file).
    3. Jika terdapat beberapa fakta dengan route/method berbeda untuk callable yang sama,
       dianggap ambigu dan return None (fail-closed, Rule A.4).
    4. Kemiripan nama tanpa route AST tidak menghasilkan route (Rule A.3).
    """
    if not identifier or not facts:
        return None

    matching = [f for f in facts if f.name == identifier]
    if not matching:
        return None

    # Filter berdasarkan target file jika ada
    if target_file:
        norm_tf = str(target_file).replace("\\", "/").strip()
        file_matching = [
            f for f in matching
            if not f.file_path or f.file_path.replace("\\", "/").strip() == norm_tf
        ]
        if file_matching:
            matching = file_matching

    # Periksa ambiguitas route / method di antara fakta-fakta yang cocok
    facts_with_route = [f for f in matching if f.route]
    if not facts_with_route:
        return matching[0]

    routes = {normalize_route_path(f.route) for f in facts_with_route if f.route}
    methods = {str(f.http_method).upper() for f in facts_with_route if f.http_method}
    if len(routes) > 1 or len(methods) > 1:
        # Ambigu: Rule A.4 melarang auto-resolve pada binding multi-definisi yang berkonflik
        return None

    return facts_with_route[0]


def bind_scaffold_callable_facts_to_interfaces(
    interfaces: List[CanonicalInterfaceDeclaration],
    facts: List[ScaffoldCallableFact]
) -> List[CanonicalInterfaceDeclaration]:
    """
    Menghubungkan fakta AST scaffold (ScaffoldCallableFact) ke deklarasi antarmuka kanonikal
    secara deterministik tanpa inferensi kemiripan nama naif.
    """
    if not interfaces or not facts:
        return interfaces

    for c_ifc in interfaces:
        # Jika route dan method sudah eksplisit dideklarasikan pada kontrak, pertahankan
        if c_ifc.canonical_route is not None and c_ifc.canonical_method is not None:
            continue

        fact = find_deterministic_callable_fact(c_ifc.identifier, c_ifc.target_file, facts)
        if fact and fact.route:
            if c_ifc.canonical_route is None:
                c_ifc.canonical_route = normalize_route_path(fact.route)
            if c_ifc.canonical_method is None and fact.http_method:
                c_ifc.canonical_method = str(fact.http_method).upper().strip()
            if not c_ifc.interface_type or c_ifc.interface_type in ("FUNCTION", ""):
                c_ifc.interface_type = "HTTP_ENDPOINT"

            if isinstance(c_ifc.raw_declaration, dict):
                c_ifc.raw_declaration["route"] = c_ifc.canonical_route
                if c_ifc.canonical_method:
                    c_ifc.raw_declaration["http_method"] = c_ifc.canonical_method
                c_ifc.raw_declaration["interface_type"] = c_ifc.interface_type

    return interfaces


# ===========================================================================
# 4. Canonical Obligation Integrity Guard
# ===========================================================================

def validate_canonical_obligation_integrity(obligations: List[CanonicalObligation]) -> bool:
    """
    Memverifikasi rantai integritas seluruh CanonicalObligation:
    - Provenance WAJIB ORACLE_FACT untuk authority ORACLE / FROZEN_ORACLE
    - Tidak boleh kosong jika Acceptance Oracle ada
    - Memiliki source_reference valid
    """
    for ob in obligations:
        if ob.authority in (ObligationAuthority.ORACLE.value, ObligationAuthority.FROZEN_ORACLE.value, "ORACLE", "FROZEN_ORACLE") and ob.provenance != ObligationProvenance.ORACLE_FACT.value:
            raise CanonicalObligationIntegrityError(
                f"Tainted obligation detected: {ob.obligation_id} claims authority {ob.authority} but has provenance {ob.provenance}"
            )
        if not ob.source_reference:
            raise CanonicalObligationIntegrityError(
                f"Untraceable obligation detected: {ob.obligation_id} has no source_reference"
            )
    return True


def assert_canonical_obligation_unmodified(
    authoritative_obligations: List[CanonicalObligation],
    candidate_obligations: List[CanonicalObligation]
) -> None:
    """
    Memastikan tidak ada obligasi yang diubah, dihapus, atau disuntikkan secara sepihak
    oleh artefak hilir (PM, Architect, rejected artifacts) untuk memalsukan coverage.
    """
    auth_map = {ob.obligation_id: ob.to_dict() for ob in authoritative_obligations}
    cand_map = {ob.obligation_id: ob.to_dict() for ob in candidate_obligations}

    if set(auth_map.keys()) != set(cand_map.keys()):
        missing = set(auth_map.keys()) - set(cand_map.keys())
        extra = set(cand_map.keys()) - set(auth_map.keys())
        raise CanonicalObligationIntegrityError(
            f"Post-hoc compliance violation: Obligations set modified. Missing: {missing}, Injected: {extra}"
        )

    for ob_id, auth_dict in auth_map.items():
        cand_dict = cand_map[ob_id]
        if auth_dict != cand_dict:
            raise CanonicalObligationIntegrityError(
                f"Post-hoc compliance violation: Obligation {ob_id} was modified. Original: {auth_dict}, Candidate: {cand_dict}"
            )


# ===========================================================================
# 5. Coverage Result & Coverage Matrix (Diagnosis Only, Zero HOW)
# ===========================================================================

@dataclass
class ObligationCoverageResult:
    """
    Hasil evaluasi cakupan untuk satu CanonicalObligation.
    Berisi diagnosis WHAT (apa yang cocok/hilang/inkompatibel), BUKAN instruksi HOW.
    """
    obligation: CanonicalObligation
    status: CoverageStatus
    matched_declaration_id: Optional[str] = None
    reason: str = ""
    missing_aspects: List[str] = field(default_factory=list)
    binding_evidence: Optional[AuthorityBindingEvidence] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "obligation_id": self.obligation.obligation_id,
            "obligation_kind": self.obligation.obligation_kind,
            "public_identity": self.obligation.public_identity,
            "status": self.status.value if isinstance(self.status, CoverageStatus) else str(self.status),
            "matched_declaration_id": self.matched_declaration_id,
            "reason": self.reason,
            "missing_aspects": self.missing_aspects,
            "source_reference": self.obligation.source_reference,
        }
        if self.binding_evidence:
            d["binding_evidence"] = {
                "authority_source": self.binding_evidence.authority_source,
                "obligation_id": self.binding_evidence.obligation_id,
                "authoritative_value": self.binding_evidence.authoritative_value,
                "blueprint_value": self.binding_evidence.blueprint_value,
                "mismatch_dimension": self.binding_evidence.mismatch_dimension,
                "affected_element": self.binding_evidence.affected_element,
                "status": self.binding_evidence.status,
                "reason": self.binding_evidence.reason,
            }
        return d


@dataclass
class CoverageMatrix:
    """
    Matriks cakupan deterministik menyeluruh.
    Mencatat hitungan agregat dan rincian diagnosis tiap obligasi.
    """
    obligations_count: int = 0
    declarations_count: int = 0
    covered_count: int = 0
    partial_count: int = 0
    missing_count: int = 0
    incompatible_count: int = 0
    undetermined_count: int = 0
    is_fully_covered: bool = False
    results: List[ObligationCoverageResult] = field(default_factory=list)
    summary_reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "obligations_count": self.obligations_count,
            "declarations_count": self.declarations_count,
            "covered_count": self.covered_count,
            "partial_count": self.partial_count,
            "missing_count": self.missing_count,
            "incompatible_count": self.incompatible_count,
            "undetermined_count": self.undetermined_count,
            "is_fully_covered": self.is_fully_covered,
            "results": [r.to_dict() for r in self.results],
            "summary_reasons": self.summary_reasons,
        }

    def to_telemetry_dict(self) -> Dict[str, Any]:
        return {
            "oracle_obligations_count": self.obligations_count,
            "contract_declarations_count": self.declarations_count,
            "covered_count": self.covered_count,
            "partial_count": self.partial_count,
            "missing_count": self.missing_count,
            "incompatible_count": self.incompatible_count,
            "undetermined_count": self.undetermined_count,
            "is_fully_covered": self.is_fully_covered,
        }

    def to_error_messages(self) -> List[str]:
        """Menghasilkan pesan diagnosis terstruktur untuk Pre-Freeze Gate & CEP."""
        msgs = []
        for r in self.results:
            if r.status != CoverageStatus.COVERED:
                st_val = r.status.value if isinstance(r.status, CoverageStatus) else str(r.status)
                msg = (
                    f"obligation_id: {r.obligation.obligation_id}\n"
                    f"obligation_kind: {r.obligation.obligation_kind}\n"
                    f"public_identity: {r.obligation.public_identity}\n"
                    f"coverage_status: {st_val}\n"
                    f"source_reference: {r.obligation.source_reference}\n"
                    f"causal_reason: {r.reason}"
                )
                if r.missing_aspects:
                    msg += f"\nmissing_aspects: {', '.join(r.missing_aspects)}"
                msgs.append(msg)
        return msgs


# ===========================================================================
# 6. Language & Framework Adapters (PARSE -> NORMALIZE -> REPRESENT)
# ===========================================================================

class BaseOracleTestAdapter:
    """Interface dasar untuk adapter ekstraksi obligasi acceptance test."""

    def can_handle(self, file_name: str) -> bool:
        raise NotImplementedError

    def extract_obligations(self, file_name: str, content: str) -> List[CanonicalObligation]:
        raise NotImplementedError


class PythonOracleAstVisitor(ast.NodeVisitor):
    """
    NodeVisitor deterministik untuk test suite Python.
    Mengekstrak observable usage & invocation shape:
    - caller (fungsi test aktif)
    - callee (simbol yang dipanggil)
    - positional_arguments count
    - keyword_arguments names
    - invocation_kind (CALL, CONSTRUCTOR, METHOD, UNKNOWN)
    - obligation_kind (INTERACTION, DATA_MODEL, CALLABLE_INTERFACE, UNKNOWN)
    - TANPA heuristik huruf kapital (isupper() dilarang).
    """

    def __init__(self, file_name: str, func_status_map: Dict[Tuple[str, str], int]):
        self.file_name = file_name
        self.func_status_map = func_status_map
        self.current_function: Optional[str] = None
        self.current_function_dicts: Dict[str, List[str]] = {}
        self.current_function_asserted_keys: List[str] = []
        self.obligations: Dict[str, CanonicalObligation] = {}
        self.imported_from_main: Set[str] = set()
        self.proven_class_symbols: Set[str] = set()
        self.external_modules: Set[str] = {
            "pytest", "unittest", "mock", "os", "sys", "re", "json", "math",
            "time", "logging", "warnings", "subprocess", "shutil", "tempfile",
            "pathlib", "asyncio", "typing", "collections", "itertools", "functools"
        }

    def _pre_scan_function_body(self, body: List[ast.stmt]) -> Tuple[Dict[str, List[str]], List[str]]:
        fn_dicts: Dict[str, List[str]] = {}
        asserted_keys: List[str] = []
        for stmt in body:
            if isinstance(stmt, ast.Assign):
                for t in stmt.targets:
                    if isinstance(t, ast.Name) and isinstance(stmt.value, ast.Dict):
                        keys = [
                            k.value for k in stmt.value.keys
                            if isinstance(k, ast.Constant) and isinstance(k.value, str)
                        ]
                        fn_dicts[t.id] = keys
            elif isinstance(stmt, ast.Assert):
                for n in ast.walk(stmt.test):
                    if isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Constant) and isinstance(n.slice.value, str):
                        asserted_keys.append(n.slice.value)
                    elif isinstance(n, ast.Compare):
                        for op, comp in zip(n.ops, n.comparators):
                            if isinstance(op, ast.In) and isinstance(n.left, ast.Constant) and isinstance(n.left.value, str):
                                asserted_keys.append(n.left.value)
        return fn_dicts, asserted_keys

    def visit_FunctionDef(self, node: ast.FunctionDef):
        prev = self.current_function
        prev_dicts = self.current_function_dicts
        prev_asserts = self.current_function_asserted_keys

        self.current_function = node.name
        fn_dicts, asserted_keys = self._pre_scan_function_body(node.body)
        self.current_function_dicts = fn_dicts
        self.current_function_asserted_keys = asserted_keys

        self.generic_visit(node)
        self.current_function = prev
        self.current_function_dicts = prev_dicts
        self.current_function_asserted_keys = prev_asserts

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        prev = self.current_function
        prev_dicts = self.current_function_dicts
        prev_asserts = self.current_function_asserted_keys

        self.current_function = node.name
        fn_dicts, asserted_keys = self._pre_scan_function_body(node.body)
        self.current_function_dicts = fn_dicts
        self.current_function_asserted_keys = asserted_keys

        self.generic_visit(node)
        self.current_function = prev
        self.current_function_dicts = prev_dicts
        self.current_function_asserted_keys = prev_asserts

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            name = alias.asname or alias.name
            if name not in ("main", "app"):
                self.external_modules.add(name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        mod = node.module or ""
        if mod in ("main", "app"):
            for alias in node.names:
                sym = alias.name
                if sym not in ("app", "main"):
                    self.imported_from_main.add(sym)
                    if sym not in self.obligations:
                        # ZERO HEURISTICS: Default role is UNKNOWN (tidak menebak DATA_MODEL / FUNCTION)
                        ob_id = f"OBL-SYM-{sym}"
                        self.obligations[sym] = CanonicalObligation(
                            obligation_id=ob_id,
                            authority=ObligationAuthority.FROZEN_ORACLE.value,
                            provenance=ObligationProvenance.ORACLE_FACT.value,
                            obligation_kind=ObligationKind.UNKNOWN.value,
                            invocation_kind=InvocationKind.UNKNOWN.value,
                            caller=self.current_function or "",
                            callee=sym,
                            public_identity=sym,
                            inputs={},
                            outputs={},
                            positional_arguments=0,
                            keyword_arguments=[],
                            argument_count=0,
                            argument_names=[],
                            epistemic_status=EpistemicStatus.UNKNOWN.value,
                            observable_behavior=f"Symbol '{sym}' imported from authoritative module '{node.module}' without explicit invocation evidence",
                            acceptance_evidence=f"from {node.module} import {sym}",
                            source_reference=f"{self.file_name}:{node.lineno}",
                            metadata={"target_module": node.module, "symbol_type": "import"}
                        )
        else:
            for alias in node.names:
                name = alias.asname or alias.name
                self.external_modules.add(name)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        # 1. isinstance(x, Symbol) / issubclass(x, Symbol) -> Proves Symbol is a class/DATA_MODEL
        if isinstance(node.func, ast.Name) and node.func.id in ("isinstance", "issubclass"):
            if len(node.args) >= 2:
                arg1 = node.args[1]
                target_sym = None
                if isinstance(arg1, ast.Name):
                    target_sym = arg1.id
                elif isinstance(arg1, ast.Attribute) and isinstance(arg1.value, ast.Name) and arg1.value.id in ("main", "app"):
                    target_sym = arg1.attr
                if target_sym and target_sym in self.obligations:
                    self.proven_class_symbols.add(target_sym)
                    ob = self.obligations[target_sym]
                    self.obligations[target_sym] = replace(
                        ob,
                        obligation_kind=ObligationKind.DATA_MODEL.value,
                        epistemic_status=EpistemicStatus.PROVEN_FACT.value,
                        observable_behavior=f"Symbol '{target_sym}' proven to be a type/class via {node.func.id} inspection"
                    )

        # 2. client.<method>("/path", ...) -> HTTP Interaction Obligation
        if isinstance(node.func, ast.Attribute):
            method_name = node.func.attr.upper()
            if method_name in ("GET", "POST", "PUT", "DELETE", "PATCH"):
                is_client = False
                if isinstance(node.func.value, ast.Name) and "client" in node.func.value.id.lower():
                    is_client = True
                elif isinstance(node.func.value, ast.Attribute) and "client" in node.func.value.attr.lower():
                    is_client = True

                if is_client and node.args:
                    first_arg = node.args[0]
                    path_val = None
                    if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                        path_val = first_arg.value
                    elif isinstance(first_arg, ast.JoinedStr):
                        parts = [str(p.value) if isinstance(p, ast.Constant) else "{id}" for p in first_arg.values]
                        path_val = "".join(parts)

                    if path_val and path_val.startswith("/"):
                        norm_path = normalize_route_path(path_val)
                        ep_key = f"HTTP:{method_name}:{norm_path}"
                        clean_id = norm_path.strip("/").replace("/", "_").replace("{", "").replace("}", "") or "root"
                        ob_id = f"OBL-HTTP-{method_name}-{clean_id}"
                        exp_status = self.func_status_map.get((method_name, norm_path))
                        outputs = {"expected_status": exp_status} if exp_status else {}
                        status_info = f" (expected status: {exp_status})" if exp_status else ""
                        num_pos = len(node.args)
                        kw_names = [kw.arg for kw in node.keywords if kw.arg]

                        # Ekstraksi payload fields dan query parameters secara deterministik
                        kw_payload_fields: List[str] = []
                        kw_query_params: List[str] = []
                        for kw in node.keywords:
                            if kw.arg in ("json", "data"):
                                if isinstance(kw.value, ast.Dict):
                                    kw_payload_fields.extend([
                                        k.value for k in kw.value.keys
                                        if isinstance(k, ast.Constant) and isinstance(k.value, str)
                                    ])
                                elif isinstance(kw.value, ast.Name) and kw.value.id in self.current_function_dicts:
                                    kw_payload_fields.extend(self.current_function_dicts[kw.value.id])
                            elif kw.arg == "params":
                                if isinstance(kw.value, ast.Dict):
                                    kw_query_params.extend([
                                        k.value for k in kw.value.keys
                                        if isinstance(k, ast.Constant) and isinstance(k.value, str)
                                    ])
                                elif isinstance(kw.value, ast.Name) and kw.value.id in self.current_function_dicts:
                                    kw_query_params.extend(self.current_function_dicts[kw.value.id])

                        kw_payload_fields = list(dict.fromkeys(kw_payload_fields))
                        kw_query_params = list(dict.fromkeys(kw_query_params))
                        resp_fields = list(dict.fromkeys(self.current_function_asserted_keys))

                        inputs_payload: Dict[str, Any] = {"http_method": method_name, "raw_path": path_val}
                        if kw_payload_fields:
                            inputs_payload["payload_fields"] = kw_payload_fields
                        if kw_query_params:
                            inputs_payload["query_parameters"] = kw_query_params

                        if resp_fields:
                            outputs["response_fields"] = resp_fields

                        canonical_arg_names = kw_payload_fields if kw_payload_fields else kw_names

                        if ep_key in self.obligations:
                            existing = self.obligations[ep_key]
                            merged_inputs = dict(existing.inputs)
                            if kw_payload_fields:
                                curr_p = merged_inputs.get("payload_fields", [])
                                merged_inputs["payload_fields"] = list(dict.fromkeys(curr_p + kw_payload_fields))
                            if kw_query_params:
                                curr_q = merged_inputs.get("query_parameters", [])
                                merged_inputs["query_parameters"] = list(dict.fromkeys(curr_q + kw_query_params))

                            merged_outputs = dict(existing.outputs)
                            if exp_status and not merged_outputs.get("expected_status"):
                                merged_outputs["expected_status"] = exp_status
                            if resp_fields:
                                curr_r = merged_outputs.get("response_fields", [])
                                merged_outputs["response_fields"] = list(dict.fromkeys(curr_r + resp_fields))

                            merged_args = list(dict.fromkeys(existing.argument_names + canonical_arg_names))
                            merged_kw = list(dict.fromkeys(existing.keyword_arguments + kw_names))

                            self.obligations[ep_key] = replace(
                                existing,
                                inputs=merged_inputs,
                                outputs=merged_outputs,
                                argument_names=merged_args,
                                keyword_arguments=merged_kw,
                                argument_count=max(existing.argument_count, len(merged_args))
                            )
                        else:
                            self.obligations[ep_key] = CanonicalObligation(
                                obligation_id=ob_id,
                                authority=ObligationAuthority.FROZEN_ORACLE.value,
                                provenance=ObligationProvenance.ORACLE_FACT.value,
                                obligation_kind=ObligationKind.INTERACTION.value,
                                invocation_kind=InvocationKind.CALL.value,
                                caller=self.current_function or "",
                                callee=norm_path,
                                public_identity=norm_path,
                                inputs=inputs_payload,
                                outputs=outputs,
                                positional_arguments=num_pos,
                                keyword_arguments=kw_names,
                                argument_count=max(num_pos, len(canonical_arg_names)),
                                argument_names=canonical_arg_names,
                                epistemic_status=EpistemicStatus.PROVEN_FACT.value,
                                observable_behavior=f"HTTP endpoint '{norm_path}' accepting {method_name} method{status_info}",
                                acceptance_evidence=f"client.{method_name.lower()}('{path_val}')",
                                source_reference=f"{self.file_name}:{node.lineno}",
                                metadata={"http_method": method_name, "path": norm_path}
                            )

            # 3. main.<sym>(*args, **kwargs) -> Callable invocation on module main
            elif isinstance(node.func.value, ast.Name) and node.func.value.id in ("main", "app"):
                sym = node.func.attr
                if sym not in ("app", "main"):
                    self._record_symbol_call(sym, node)

            # 4. Method invocation: obj.<method>(*args, **kwargs) where obj is not an external module/client
            elif isinstance(node.func.value, ast.Name):
                obj_name = node.func.value.id
                method_name = node.func.attr
                if (
                    obj_name not in self.external_modules and
                    obj_name not in ("self", "cls") and
                    not method_name.startswith("__") and
                    method_name not in ("status_code", "json", "text", "content", "get", "post", "put", "delete", "patch")
                ):
                    self._record_method_call(method_name, node)
            elif isinstance(node.func.value, (ast.Attribute, ast.Call)):
                method_name = node.func.attr
                if not method_name.startswith("__") and method_name not in ("status_code", "json", "text", "content", "get", "post", "put", "delete", "patch"):
                    self._record_method_call(method_name, node)

        # 5. Direct call on imported symbol: e.g. Matrix(data) or add_numbers(1, 2)
        elif isinstance(node.func, ast.Name) and node.func.id in self.imported_from_main:
            sym = node.func.id
            self._record_symbol_call(sym, node)

        # 6. hasattr(main, 'sym')
        elif isinstance(node.func, ast.Name) and node.func.id == "hasattr":
            if len(node.args) >= 2 and isinstance(node.args[0], ast.Name) and node.args[0].id in ("main", "app"):
                if isinstance(node.args[1], ast.Constant) and isinstance(node.args[1].value, str):
                    sym = node.args[1].value
                    if sym not in ("app", "main") and sym not in self.obligations:
                        self.obligations[sym] = CanonicalObligation(
                            obligation_id=f"OBL-CALL-{sym}",
                            authority=ObligationAuthority.FROZEN_ORACLE.value,
                            provenance=ObligationProvenance.ORACLE_FACT.value,
                            obligation_kind=ObligationKind.CALLABLE_INTERFACE.value,
                            invocation_kind=InvocationKind.UNKNOWN.value,
                            caller=self.current_function or "",
                            callee=sym,
                            public_identity=sym,
                            inputs={},
                            outputs={},
                            positional_arguments=0,
                            keyword_arguments=[],
                            argument_count=0,
                            argument_names=[],
                            epistemic_status=EpistemicStatus.UNKNOWN.value,
                            observable_behavior=f"Symbol '{sym}' verified via hasattr inspection on authoritative module",
                            acceptance_evidence=f"hasattr(main, '{sym}')",
                            source_reference=f"{self.file_name}:{node.lineno}",
                            metadata={"symbol_type": "hasattr"}
                        )

        self.generic_visit(node)

    def _record_symbol_call(self, sym: str, node: ast.Call):
        num_pos = len(node.args)
        kw_names = [kw.arg for kw in node.keywords if kw.arg]
        total_args = num_pos + len(kw_names)
        arg_str = f" with {num_pos} positional argument(s)" if num_pos else ""
        if kw_names:
            arg_str += f", keywords: {kw_names}"

        inv_kind = InvocationKind.CONSTRUCTOR.value if sym in self.proven_class_symbols else InvocationKind.CALL.value
        ob_kind = ObligationKind.DATA_MODEL.value if sym in self.proven_class_symbols else ObligationKind.CALLABLE_INTERFACE.value

        existing = self.obligations.get(sym)
        if existing:
            self.obligations[sym] = replace(
                existing,
                obligation_kind=ob_kind if existing.obligation_kind == ObligationKind.UNKNOWN.value else existing.obligation_kind,
                invocation_kind=inv_kind,
                caller=self.current_function or existing.caller,
                callee=sym,
                positional_arguments=max(existing.positional_arguments, num_pos),
                keyword_arguments=list(set(existing.keyword_arguments + kw_names)),
                argument_count=max(existing.argument_count, total_args),
                argument_names=list(set(existing.argument_names + kw_names)),
                epistemic_status=EpistemicStatus.PROVEN_FACT.value,
                observable_behavior=f"Symbol '{sym}' invoked as callable{arg_str}",
                acceptance_evidence=f"{sym}(...)",
                inputs={"positional_args": num_pos, "keyword_args": kw_names, "call_type": "callable"} if (num_pos or kw_names) else dict(existing.inputs, call_type="callable"),
                metadata={"symbol_type": "callable_invocation"}
            )
        else:
            self.obligations[sym] = CanonicalObligation(
                obligation_id=f"OBL-CALL-{sym}",
                authority=ObligationAuthority.FROZEN_ORACLE.value,
                provenance=ObligationProvenance.ORACLE_FACT.value,
                obligation_kind=ob_kind,
                invocation_kind=inv_kind,
                caller=self.current_function or "",
                callee=sym,
                public_identity=sym,
                inputs={"positional_args": num_pos, "keyword_args": kw_names, "call_type": "callable"},
                outputs={},
                positional_arguments=num_pos,
                keyword_arguments=kw_names,
                argument_count=total_args,
                argument_names=kw_names,
                epistemic_status=EpistemicStatus.PROVEN_FACT.value,
                observable_behavior=f"Symbol '{sym}' invoked as callable{arg_str}",
                acceptance_evidence=f"{sym}(...)",
                source_reference=f"{self.file_name}:{node.lineno}",
                metadata={"symbol_type": "callable_invocation"}
            )

    def _record_method_call(self, method_name: str, node: ast.Call):
        num_pos = len(node.args)
        kw_names = [kw.arg for kw in node.keywords if kw.arg]
        total_args = num_pos + len(kw_names)
        m_key = f"METHOD:{method_name}"
        if m_key not in self.obligations:
            self.obligations[m_key] = CanonicalObligation(
                obligation_id=f"OBL-METHOD-{method_name}",
                authority=ObligationAuthority.FROZEN_ORACLE.value,
                provenance=ObligationProvenance.ORACLE_FACT.value,
                obligation_kind=ObligationKind.CALLABLE_INTERFACE.value,
                invocation_kind=InvocationKind.METHOD.value,
                caller=self.current_function or "",
                callee=method_name,
                public_identity=method_name,
                inputs={"positional_args": num_pos, "keyword_args": kw_names} if (num_pos or kw_names) else {},
                outputs={},
                positional_arguments=num_pos,
                keyword_arguments=kw_names,
                argument_count=total_args,
                argument_names=kw_names,
                epistemic_status=EpistemicStatus.PROVEN_FACT.value,
                observable_behavior=f"Method '{method_name}' invoked on object instance",
                acceptance_evidence=f"obj.{method_name}(...)",
                source_reference=f"{self.file_name}:{node.lineno}",
                metadata={"symbol_type": "method_invocation"}
            )


class PythonAstOracleAdapter(BaseOracleTestAdapter):
    """
    Adapter ekstraksi AST untuk test suite Python (pytest / unittest).
    MURNI bertugas: PARSE -> NORMALIZE -> REPRESENT.
    TIDAK memiliki heuristik task (tidak tahu 'FastAPI wajib GET' dsb).
    Hanya membaca apa yang benar-benar dibuktikan oleh source test.
    """

    def can_handle(self, file_name: str) -> bool:
        return file_name.endswith(".py") and (file_name.startswith("test_") or file_name.endswith("_test.py"))

    def extract_obligations(self, file_name: str, content: str) -> List[CanonicalObligation]:
        func_status_map: Dict[Tuple[str, str], int] = {}
        try:
            tree_scan = ast.parse(content, filename=file_name)
            for fn in tree_scan.body:
                if not isinstance(fn, ast.FunctionDef):
                    continue
                local_vars: Dict[str, Tuple[str, str]] = {}
                for stmt in fn.body:
                    if isinstance(stmt, ast.Assign):
                        if isinstance(stmt.value, ast.Call) and isinstance(stmt.value.func, ast.Attribute):
                            m = stmt.value.func.attr.upper()
                            if m in ("GET", "POST", "PUT", "DELETE", "PATCH") and stmt.value.args:
                                arg0 = stmt.value.args[0]
                                url = None
                                if isinstance(arg0, ast.Constant) and isinstance(arg0.value, str):
                                    url = arg0.value
                                elif isinstance(arg0, ast.JoinedStr):
                                    parts = [str(p.value) if isinstance(p, ast.Constant) else "{id}" for p in arg0.values]
                                    url = "".join(parts)
                                if url and url.startswith("/"):
                                    norm_u = normalize_route_path(url)
                                    for t in stmt.targets:
                                        if isinstance(t, ast.Name):
                                            local_vars[t.id] = (m, norm_u)
                    elif isinstance(stmt, ast.Assert) and isinstance(stmt.test, ast.Compare):
                        left = stmt.test.left
                        code = None
                        for op, comp in zip(stmt.test.ops, stmt.test.comparators):
                            if isinstance(op, ast.Eq) and isinstance(comp, ast.Constant) and isinstance(comp.value, int):
                                code = comp.value
                                break
                        if code is not None and isinstance(left, ast.Attribute) and left.attr == "status_code":
                            target_endpoint = None
                            if isinstance(left.value, ast.Name) and left.value.id in local_vars:
                                target_endpoint = local_vars[left.value.id]
                            elif isinstance(left.value, ast.Call) and isinstance(left.value.func, ast.Attribute):
                                m_direct = left.value.func.attr.upper()
                                if m_direct in ("GET", "POST", "PUT", "DELETE", "PATCH") and left.value.args:
                                    arg0_d = left.value.args[0]
                                    u_direct = None
                                    if isinstance(arg0_d, ast.Constant) and isinstance(arg0_d.value, str):
                                        u_direct = arg0_d.value
                                    elif isinstance(arg0_d, ast.JoinedStr):
                                        parts_d = [str(p.value) if isinstance(p, ast.Constant) else "{id}" for p in arg0_d.values]
                                        u_direct = "".join(parts_d)
                                    if u_direct and u_direct.startswith("/"):
                                        target_endpoint = (m_direct, normalize_route_path(u_direct))
                            if target_endpoint:
                                curr = func_status_map.get(target_endpoint)
                                if curr is None or (curr >= 400 and code < 400):
                                    func_status_map[target_endpoint] = code
                                elif code < 400 and curr < 400:
                                    func_status_map[target_endpoint] = code
        except Exception:
            pass

        visitor = PythonOracleAstVisitor(file_name, func_status_map)
        try:
            tree = ast.parse(content, filename=file_name)
            visitor.visit(tree)
        except Exception:
            pass

        # Regex fallback for client calls if not already captured
        for method, ep in re.findall(r"client\.(get|post|put|delete|patch)\(\s*f?[\"'](/[^\"'\s?#]+)[\"']", content, re.IGNORECASE):
            m_upper = method.upper()
            norm_path = normalize_route_path(ep)
            ep_key = f"HTTP:{m_upper}:{norm_path}"
            if ep_key not in visitor.obligations:
                clean_id = norm_path.strip("/").replace("/", "_").replace("{", "").replace("}", "") or "root"
                ob_id = f"OBL-HTTP-{m_upper}-{clean_id}"
                exp_status = func_status_map.get((m_upper, norm_path))
                outputs = {"expected_status": exp_status} if exp_status else {}
                status_info = f" (expected status: {exp_status})" if exp_status else ""
                visitor.obligations[ep_key] = CanonicalObligation(
                    obligation_id=ob_id,
                    authority=ObligationAuthority.FROZEN_ORACLE.value,
                    provenance=ObligationProvenance.ORACLE_FACT.value,
                    obligation_kind=ObligationKind.INTERACTION.value,
                    invocation_kind=InvocationKind.CALL.value,
                    caller="",
                    callee=norm_path,
                    public_identity=norm_path,
                    inputs={"http_method": m_upper, "raw_path": ep},
                    outputs=outputs,
                    positional_arguments=1,
                    keyword_arguments=[],
                    argument_count=1,
                    argument_names=[],
                    epistemic_status=EpistemicStatus.PROVEN_FACT.value,
                    observable_behavior=f"HTTP endpoint '{norm_path}' accepting {m_upper} method{status_info}",
                    acceptance_evidence=f"client.{method.lower()}('{ep}')",
                    source_reference=file_name,
                    metadata={"http_method": m_upper, "path": norm_path}
                )

        return list(visitor.obligations.values())


class DartAstOracleAdapter(BaseOracleTestAdapter):
    """
    Adapter ekstraksi AST untuk test suite Dart (flutter_test / dart test).
    MURNI bertugas: PARSE -> NORMALIZE -> REPRESENT.
    TIDAK memiliki heuristik task.
    """

    # Generic framework types to exclude from user obligations
    DART_FRAMEWORK_TYPES: Set[str] = {
        "MaterialApp", "Scaffold", "ThemeData", "ProviderScope", "SizedBox",
        "Container", "Card", "Text", "Center", "Row", "Column", "Padding",
        "WidgetTester", "Key", "Colors", "Icon", "Icons", "ConsumerWidget",
        "StatelessWidget", "StatefulWidget", "State", "BuildContext", "Widget",
        "Expanded", "Flexible", "ListView", "SingleChildScrollView", "AppBar",
        "FloatingActionButton", "ElevatedButton", "TextButton", "IconButton",
        "Stack", "Positioned", "Align", "Duration", "Future", "Stream",
        "ValueNotifier", "ChangeNotifier", "StateNotifier", "Provider",
        "StateProvider", "FutureProvider", "StreamProvider", "NotifierProvider",
        "AsyncValue", "BoxConstraints", "ConstrainedBox", "EdgeInsets",
        "FontWeight", "TextStyle", "BorderRadius", "RoundedRectangleBorder",
    }

    def can_handle(self, file_name: str) -> bool:
        return file_name.endswith(".dart") and (file_name.endswith("_test.dart") or file_name.startswith("test_"))

    def _parse_dart_call_args(self, args_str: str) -> Tuple[int, List[str]]:
        """Parses Dart invocation arguments into positional count and keyword argument names."""
        if not args_str or not args_str.strip():
            return 0, []
        tokens: List[str] = []
        depth = 0
        current: List[str] = []
        for ch in args_str:
            if ch in "({[":
                depth += 1
                current.append(ch)
            elif ch in ")}]":
                depth -= 1
                current.append(ch)
            elif ch == "," and depth == 0:
                tokens.append("".join(current).strip())
                current = []
            else:
                current.append(ch)
        if current:
            tokens.append("".join(current).strip())

        pos_count = 0
        kw_names: List[str] = []
        for token in tokens:
            if not token:
                continue
            m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:", token)
            if m:
                kw_names.append(m.group(1))
            else:
                pos_count += 1
        return pos_count, kw_names

    def _extract_dart_invocations(self, content: str) -> List[Tuple[str, str, int]]:
        """Extracts (symbol, args_str, lineno) with balanced parentheses."""
        results = []
        for m in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", content):
            sym = m.group(1)
            start = m.end()
            depth = 1
            i = start
            while i < len(content) and depth > 0:
                if content[i] == '(':
                    depth += 1
                elif content[i] == ')':
                    depth -= 1
                i += 1
            if depth == 0:
                args_str = content[start:i-1]
                lineno = content.count("\n", 0, m.start()) + 1
                results.append((sym, args_str, lineno))
        return results

    def extract_obligations(self, file_name: str, content: str) -> List[CanonicalObligation]:
        obligations: Dict[str, CanonicalObligation] = {}

        # Extract active test name for caller tracking
        test_match = re.search(r"(?:testWidgets|test)\s*\(\s*['\"]([^'\"]+)['\"]", content)
        caller_name = test_match.group(1) if test_match else ""

        # 1. Widget obligations via find.byType(WidgetName)
        for sym in re.findall(r"find\.byType\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)", content):
            if sym not in self.DART_FRAMEWORK_TYPES and sym not in obligations:
                ob_id = f"OBL-WIDGET-{sym}"
                obligations[sym] = CanonicalObligation(
                    obligation_id=ob_id,
                    authority=ObligationAuthority.FROZEN_ORACLE.value,
                    provenance=ObligationProvenance.ORACLE_FACT.value,
                    obligation_kind=ObligationKind.OBSERVABLE_RUNTIME.value,
                    invocation_kind=InvocationKind.UNKNOWN.value,
                    caller=caller_name,
                    callee=sym,
                    public_identity=sym,
                    inputs={},
                    outputs={"return_type": "Widget"},
                    positional_arguments=0,
                    keyword_arguments=[],
                    argument_count=0,
                    argument_names=[],
                    epistemic_status=EpistemicStatus.PROVEN_FACT.value,
                    observable_behavior=f"UI Widget '{sym}' located and verified via widget tester find.byType",
                    acceptance_evidence=f"find.byType({sym})",
                    source_reference=file_name,
                    metadata={"target_type": "widget"}
                )

        # 2. Extract balanced invocations for widgets, models, and constructors
        invocations = self._extract_dart_invocations(content)
        for sym, args_str, lineno in invocations:
            if sym in self.DART_FRAMEWORK_TYPES or sym.startswith("Test"):
                continue

            pos_count, kw_names = self._parse_dart_call_args(args_str)
            total_args = pos_count + len(kw_names)

            is_widget = sym in obligations and obligations[sym].obligation_kind == ObligationKind.OBSERVABLE_RUNTIME.value
            if is_widget:
                existing = obligations[sym]
                obligations[sym] = replace(
                    existing,
                    invocation_kind=InvocationKind.CONSTRUCTOR.value,
                    caller=caller_name or existing.caller,
                    positional_arguments=pos_count,
                    keyword_arguments=kw_names,
                    argument_count=total_args,
                    argument_names=kw_names,
                    observable_behavior=f"UI Widget '{sym}' mounted in test tree",
                    acceptance_evidence=f"{sym}({args_str.strip()})",
                    source_reference=f"{file_name}:{lineno}",
                )
            elif sym[0].isupper():
                existing = obligations.get(sym)
                if existing:
                    obligations[sym] = replace(
                        existing,
                        invocation_kind=InvocationKind.CONSTRUCTOR.value,
                        positional_arguments=max(existing.positional_arguments, pos_count),
                        keyword_arguments=list(set(existing.keyword_arguments + kw_names)),
                        argument_count=max(existing.argument_count, total_args),
                        argument_names=list(set(existing.argument_names + kw_names)),
                        epistemic_status=EpistemicStatus.PROVEN_FACT.value,
                    )
                else:
                    ob_id = f"OBL-MODEL-{sym}"
                    obligations[sym] = CanonicalObligation(
                        obligation_id=ob_id,
                        authority=ObligationAuthority.FROZEN_ORACLE.value,
                        provenance=ObligationProvenance.ORACLE_FACT.value,
                        obligation_kind=ObligationKind.DATA_MODEL.value,
                        invocation_kind=InvocationKind.CONSTRUCTOR.value,
                        caller=caller_name,
                        callee=sym,
                        public_identity=sym,
                        inputs={},
                        outputs={},
                        positional_arguments=pos_count,
                        keyword_arguments=kw_names,
                        argument_count=total_args,
                        argument_names=kw_names,
                        epistemic_status=EpistemicStatus.PROVEN_FACT.value,
                        observable_behavior=f"Data model / entity '{sym}' instantiated with constructor parameters in acceptance test",
                        acceptance_evidence=f"{sym}({args_str.strip()})",
                        source_reference=f"{file_name}:{lineno}",
                        metadata={"target_type": "model"}
                    )

        # 3. Provider read / watch: e.g. container.read(metricDataProvider)
        for sym in re.findall(r"(?:container\.read|ref\.watch|ref\.read)\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)", content):
            if sym not in self.DART_FRAMEWORK_TYPES and sym not in obligations:
                ob_id = f"OBL-PROVIDER-{sym}"
                obligations[sym] = CanonicalObligation(
                    obligation_id=ob_id,
                    authority=ObligationAuthority.FROZEN_ORACLE.value,
                    provenance=ObligationProvenance.ORACLE_FACT.value,
                    obligation_kind=ObligationKind.CALLABLE_INTERFACE.value,
                    invocation_kind=InvocationKind.CALL.value,
                    caller=caller_name,
                    callee=sym,
                    public_identity=sym,
                    inputs={},
                    outputs={},
                    positional_arguments=0,
                    keyword_arguments=[],
                    argument_count=0,
                    argument_names=[],
                    epistemic_status=EpistemicStatus.PROVEN_FACT.value,
                    observable_behavior=f"State Provider '{sym}' read/watched by acceptance test",
                    acceptance_evidence=f"container.read({sym})",
                    source_reference=file_name,
                    metadata={"target_type": "provider"}
                )

        return list(obligations.values())


# ===========================================================================
# 7. Generic Extraction Dispatcher
# ===========================================================================

def extract_canonical_oracle_obligations(
    frozen_oracle_path: Optional[str] = None,
    test_files: Optional[Dict[str, str]] = None
) -> List[CanonicalObligation]:
    """
    Mengekstrak seluruh obligasi acceptance secara kanonikal langsung dari
    immutable Frozen Acceptance Oracle test suite.
    HANYA memproses berkas pengujian nyata.
    """
    adapters: List[BaseOracleTestAdapter] = [
        PythonAstOracleAdapter(),
        DartAstOracleAdapter(),
    ]

    test_contents: List[Tuple[str, str]] = []
    seen_fnames: Set[str] = set()

    # 1. Dari in-memory test_files dictionary atau list (jika ada)
    if test_files:
        if isinstance(test_files, dict):
            for fname, content in test_files.items():
                if content and fname not in seen_fnames:
                    test_contents.append((fname, content))
                    seen_fnames.add(fname)
        elif isinstance(test_files, list):
            for item in test_files:
                if isinstance(item, tuple) and len(item) == 2:
                    fname, content = item
                    if content and fname not in seen_fnames:
                        test_contents.append((fname, content))
                        seen_fnames.add(fname)
                elif isinstance(item, str) and item not in seen_fnames:
                    p = Path(item)
                    if p.exists() and p.is_file():
                        try:
                            test_contents.append((p.name, p.read_text(encoding="utf-8")))
                            seen_fnames.add(p.name)
                        except Exception:
                            pass

    # 2. Dari directory frozen_oracle_path di filesystem
    if frozen_oracle_path:
        f_dir = Path(frozen_oracle_path)
        if f_dir.exists() and f_dir.is_dir():
            for root, _, files in os.walk(f_dir):
                for f in files:
                    if f not in seen_fnames:
                        for adapter in adapters:
                            if adapter.can_handle(f):
                                try:
                                    fpath = Path(root) / f
                                    test_contents.append((f, fpath.read_text(encoding="utf-8")))
                                    seen_fnames.add(f)
                                except Exception:
                                    pass
                                break

    obligations: List[CanonicalObligation] = []
    seen_ob_ids: Set[str] = set()

    for fname, content in test_contents:
        for adapter in adapters:
            if adapter.can_handle(fname):
                extracted = adapter.extract_obligations(fname, content)
                for ob in extracted:
                    if ob.obligation_id not in seen_ob_ids:
                        seen_ob_ids.add(ob.obligation_id)
                        obligations.append(ob)
                break

    # Validasi integritas obligasi hasil ekstraksi
    validate_canonical_obligation_integrity(obligations)
    return obligations


# ===========================================================================
# 8. Deterministic Obligation Coverage Checker (Semantics, Not Blind String Equality)
# ===========================================================================

def check_call_shape_compatibility(
    ob: CanonicalObligation,
    contract: Any,
    blueprint: Optional[Any] = None
) -> Tuple[str, str, Dict[str, Any]]:
    """
    Deterministic compatibility checker membandingkan:
        ACCEPTANCE USAGE EVIDENCE (ob)
                VS
        PROPOSED PUBLIC CONTRACT & CODE SCAFFOLD

    Mengembalikan: (status, reason, evidence_dict)
    di mana status adalah: "COMPATIBLE", "INCOMPATIBLE", atau "UNDETERMINED".
    TIDAK menghasilkan instruksi implementasi HOW.
    """
    ob_sym = ob.public_identity
    ob_pos = ob.positional_arguments
    ob_kw = ob.keyword_arguments or []

    # If no specific call shape evidence exists (e.g. only imported or hasattr), return UNDETERMINED
    if (ob_pos is None or ob_pos == 0) and not ob_kw and ob.invocation_kind in (InvocationKind.UNKNOWN.value, ""):
        return CoverageStatus.UNDETERMINED, f"Insufficient observable invocation evidence for symbol '{ob_sym}'", {}

    # Extract all code scaffolds available
    scaffolds: List[str] = []
    if blueprint:
        if isinstance(blueprint, dict):
            if "scaffold_code" in blueprint and isinstance(blueprint["scaffold_code"], str):
                scaffolds.append(blueprint["scaffold_code"])
            if "code_scaffold" in blueprint and isinstance(blueprint["code_scaffold"], str):
                scaffolds.append(blueprint["code_scaffold"])
            if "files" in blueprint and isinstance(blueprint["files"], dict):
                for _, mod in blueprint["files"].items():
                    if isinstance(mod, dict) and mod.get("code_scaffold"):
                        scaffolds.append(mod["code_scaffold"])
                    elif hasattr(mod, "code_scaffold") and mod.code_scaffold:
                        scaffolds.append(mod.code_scaffold)
        elif hasattr(blueprint, "files"):
            for _, mod in blueprint.files.items():
                if hasattr(mod, "code_scaffold") and mod.code_scaffold:
                    scaffolds.append(mod.code_scaffold)

    if isinstance(contract, dict):
        if "code_scaffold" in contract and isinstance(contract["code_scaffold"], str):
            scaffolds.append(contract["code_scaffold"])
        if "scaffold_code" in contract and isinstance(contract["scaffold_code"], str):
            scaffolds.append(contract["scaffold_code"])
        if "scaffold" in contract and isinstance(contract["scaffold"], str):
            scaffolds.append(contract["scaffold"])
        if "files" in contract and isinstance(contract["files"], dict):
            for _, mod in contract["files"].items():
                if isinstance(mod, dict) and mod.get("code_scaffold"):
                    scaffolds.append(mod["code_scaffold"])
                elif isinstance(mod, str):
                    scaffolds.append(mod)

    # 1. Inspect Python AST scaffolds
    for sc in scaffolds:
        try:
            tree = ast.parse(sc)
        except Exception:
            continue

        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == ob_sym:
                init_node = None
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                        init_node = item
                        break

                if init_node is not None:
                    params = [a.arg for a in init_node.args.args if a.arg != "self"]
                    has_vararg = init_node.args.vararg is not None
                    has_kwarg = init_node.args.kwarg is not None
                    defaults_count = len(init_node.args.defaults)
                    req_pos_count = len(params) - defaults_count
                    max_pos_count = 9999 if has_vararg else len(params)
                    kw_params = set([a.arg for a in init_node.args.kwonlyargs] + params)

                    if ob_pos < req_pos_count:
                        return (
                            "INCOMPATIBLE",
                            f"CALL_SHAPE_INCOMPATIBILITY: Symbol '{ob_sym}' invoked with {ob_pos} positional argument(s), but proposed constructor requires at least {req_pos_count}.",
                            {"required_positional": ob_pos, "proposed_min_positional": req_pos_count}
                        )
                    if ob_pos > max_pos_count:
                        return (
                            "INCOMPATIBLE",
                            f"CALL_SHAPE_INCOMPATIBILITY: Symbol '{ob_sym}' invoked with {ob_pos} positional argument(s), but proposed constructor accepts at most {max_pos_count}.",
                            {"required_positional": ob_pos, "proposed_max_positional": max_pos_count}
                        )
                    if ob_kw and not has_kwarg:
                        missing = [k for k in ob_kw if k not in kw_params]
                        if missing:
                            return (
                                "INCOMPATIBLE",
                                f"CALL_SHAPE_INCOMPATIBILITY: Symbol '{ob_sym}' invoked with keyword argument(s) {missing}, which are not accepted by proposed constructor.",
                                {"required_keywords": ob_kw, "missing_keywords": missing}
                            )
                    return "COMPATIBLE", f"Constructor '{ob_sym}' call shape is compatible with acceptance usage.", {"required_pos": ob_pos}

                else:
                    # Class without custom __init__
                    base_names = [b.id if isinstance(b, ast.Name) else b.attr if isinstance(b, ast.Attribute) else "" for b in node.bases]
                    is_pydantic = any("BaseModel" in b for b in base_names)
                    if is_pydantic:
                        if ob_pos > 0:
                            return (
                                "INCOMPATIBLE",
                                f"CALL_SHAPE_INCOMPATIBILITY: Symbol '{ob_sym}' invoked with {ob_pos} positional argument(s), but proposed constructor accepts 0 positional argument(s) (BaseModel keyword-only constructor without custom positional __init__).",
                                {"required_positional": ob_pos, "proposed_positional": 0}
                            )
                        if ob_kw:
                            fields = [stmt.target.id for stmt in node.body if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name)]
                            missing = [k for k in ob_kw if k not in fields]
                            if missing:
                                return (
                                    "INCOMPATIBLE",
                                    f"CALL_SHAPE_INCOMPATIBILITY: Symbol '{ob_sym}' invoked with keyword argument(s) {missing} not defined in model fields.",
                                    {"required_keywords": ob_kw, "missing_keywords": missing}
                                )
                        return "COMPATIBLE", f"Pydantic model '{ob_sym}' keyword call shape is compatible.", {"required_pos": ob_pos}

            elif isinstance(node, ast.FunctionDef) and node.name == ob_sym:
                params = [a.arg for a in node.args.args]
                has_vararg = node.args.vararg is not None
                has_kwarg = node.args.kwarg is not None
                defaults_count = len(node.args.defaults)
                req_pos_count = len(params) - defaults_count
                max_pos_count = 9999 if has_vararg else len(params)
                kw_params = set([a.arg for a in node.args.kwonlyargs] + params)

                if ob_pos < req_pos_count:
                    return (
                        "INCOMPATIBLE",
                        f"CALL_SHAPE_INCOMPATIBILITY: Symbol '{ob_sym}' invoked with {ob_pos} positional argument(s), but proposed function requires at least {req_pos_count}.",
                        {"required_positional": ob_pos, "proposed_min_positional": req_pos_count}
                    )
                if ob_pos > max_pos_count:
                    return (
                        "INCOMPATIBLE",
                        f"CALL_SHAPE_INCOMPATIBILITY: Symbol '{ob_sym}' invoked with {ob_pos} positional argument(s), but proposed function accepts at most {max_pos_count}.",
                        {"required_positional": ob_pos, "proposed_max_positional": max_pos_count}
                    )
                if ob_kw and not has_kwarg:
                    missing = [k for k in ob_kw if k not in kw_params]
                    if missing:
                        return (
                            "INCOMPATIBLE",
                            f"CALL_SHAPE_INCOMPATIBILITY: Symbol '{ob_sym}' invoked with keyword argument(s) {missing}, which are not accepted by proposed function.",
                            {"required_keywords": ob_kw, "missing_keywords": missing}
                        )
                return "COMPATIBLE", f"Function '{ob_sym}' call shape is compatible with acceptance usage.", {"required_pos": ob_pos}

    # 2. Inspect Dart scaffolds
    for sc in scaffolds:
        if f"class {ob_sym}" in sc:
            ctor_match = re.search(rf"\b{ob_sym}\s*\(([^)]*)\)", sc)
            if ctor_match:
                param_str = ctor_match.group(1)
                is_named = "{" in param_str and "}" in param_str
                if is_named:
                    named_params = re.findall(r"this\.([A-Za-z0-9_]+)", param_str)
                    if ob_pos > 0:
                        return (
                            "INCOMPATIBLE",
                            f"CALL_SHAPE_INCOMPATIBILITY: Symbol '{ob_sym}' constructor accepts named arguments, but was invoked with {ob_pos} positional argument(s).",
                            {"required_positional": ob_pos, "proposed_positional": 0}
                        )
                    if ob_kw:
                        missing = [k for k in ob_kw if k not in named_params]
                        if missing:
                            return (
                                "INCOMPATIBLE",
                                f"CALL_SHAPE_INCOMPATIBILITY: Symbol '{ob_sym}' constructor missing named argument(s): {missing}.",
                                {"required_keywords": ob_kw, "missing_keywords": missing}
                            )
                    return "COMPATIBLE", f"Dart constructor '{ob_sym}' named call shape is compatible.", {}
                else:
                    params = [p.strip() for p in param_str.split(",") if p.strip()]
                    if ob_pos != len(params):
                        return (
                            "INCOMPATIBLE",
                            f"CALL_SHAPE_INCOMPATIBILITY: Symbol '{ob_sym}' constructor expected {ob_pos} positional argument(s), but proposed constructor accepts {len(params)}.",
                            {"required_positional": ob_pos, "proposed_positional": len(params)}
                        )
                    return "COMPATIBLE", f"Dart constructor '{ob_sym}' positional call shape is compatible.", {}

    # 3. Check interface_contracts and data_models parameter metadata
    declared_ifcs = contract.get("interface_contracts", []) if isinstance(contract, dict) else getattr(contract, "interface_contracts", []) or []
    for ifc in declared_ifcs:
        ident = ifc.get("identifier") if isinstance(ifc, dict) else getattr(ifc, "identifier", "")
        if ident == ob_sym:
            params = ifc.get("parameters", []) if isinstance(ifc, dict) else getattr(ifc, "parameters", [])
            if params:
                req_params = [p for p in params if (p.get("is_required", True) if isinstance(p, dict) else getattr(p, "is_required", True))]
                if ob_pos > 0 and len(req_params) != ob_pos:
                    return (
                        "INCOMPATIBLE",
                        f"CALL_SHAPE_INCOMPATIBILITY: Interface '{ob_sym}' requires {len(req_params)} parameter(s) in contract, but acceptance test invoked it with {ob_pos} argument(s).",
                        {"required_positional": ob_pos, "proposed_positional": len(req_params)}
                    )
                return "COMPATIBLE", f"Interface contract '{ob_sym}' parameters compatible with invocation.", {}

    return "UNDETERMINED", f"Insufficient structural evidence to prove call shape compatibility for '{ob_sym}'.", {}


def _extract_all_scaffold_symbols(
    scaffold_files: Dict[str, Any]
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
    """
    Ekstraksi simbol, kelas (fields, types, init parameters), fungsi (parameters, types, return type, status_code),
    dan route endpoints secara deterministik dari kumpulan file scaffold (.py dan .dart).
    Murni generic AST/token parser tanpa domain hardcoding.
    """
    classes: Dict[str, Dict[str, Any]] = {}
    functions: Dict[str, Dict[str, Any]] = {}
    route_endpoints: Dict[str, List[Dict[str, Any]]] = {}

    for fp, content in scaffold_files.items():
        if not isinstance(content, str) or not content.strip():
            continue

        if fp.endswith(".dart"):
            for cb in re.finditer(r"\bclass\s+([A-Za-z0-9_]+)[^{]*\{", content):
                cname = cb.group(1)
                snippet = content[cb.end():cb.end() + 2000]
                named: List[str] = []
                ctor_m = re.search(rf"\b{cname}\s*\((.*?)\)", snippet, re.DOTALL)
                if ctor_m:
                    p_str = ctor_m.group(1)
                    named = re.findall(r"this\.([A-Za-z0-9_]+)", p_str)
                fields: List[str] = [m.group(1) for m in re.finditer(r"\bfinal\s+(?:[A-Za-z0-9_<>]+)\s+([A-Za-z0-9_]+)\s*;", snippet)]
                all_f = list(dict.fromkeys(fields + named))
                classes[cname] = {
                    "name": cname,
                    "fields": all_f,
                    "named_params": named,
                    "target_file": fp
                }
            for fm in re.finditer(r"(?:^|\n)\s*(?:[A-Za-z0-9_<>, ]+)\s+([a-z][A-Za-z0-9_]*)\s*\((.*?)\)\s*\{", content):
                fname = fm.group(1)
                functions[fname] = {
                    "name": fname,
                    "target_file": fp,
                    "params": [],
                    "param_types": {},
                    "route": None,
                    "method": None,
                    "status_code": None
                }
        else:
            try:
                tree = ast.parse(content)
                for node in tree.body:
                    if isinstance(node, ast.ClassDef):
                        fields: List[str] = []
                        field_types: Dict[str, str] = {}
                        init_params: List[str] = []
                        for item in node.body:
                            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                                fields.append(item.target.id)
                                try:
                                    field_types[item.target.id] = ast.unparse(item.annotation)
                                except Exception:
                                    field_types[item.target.id] = "Any"
                            elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == "__init__":
                                init_params = [a.arg for a in item.args.args if a.arg != "self"]
                        classes[node.name] = {
                            "name": node.name,
                            "fields": list(dict.fromkeys(fields + init_params)),
                            "field_types": field_types,
                            "init_params": init_params,
                            "target_file": fp
                        }
                    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        r = None
                        m = None
                        sc = None
                        for dec in node.decorator_list:
                            if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                                cand_m = dec.func.attr.upper()
                                if cand_m in ("GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"):
                                    m = cand_m
                                    if dec.args and isinstance(dec.args[0], ast.Constant) and isinstance(dec.args[0].value, str):
                                        r = dec.args[0].value
                                    for kw in dec.keywords:
                                        if kw.arg == "status_code" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, int):
                                            sc = kw.value.value
                        p_names = [a.arg for a in node.args.args if a.arg not in ("self", "cls")]
                        p_types: Dict[str, str] = {}
                        for a in node.args.args:
                            if a.annotation:
                                try:
                                    p_types[a.arg] = ast.unparse(a.annotation)
                                except Exception:
                                    pass
                        ret_type = None
                        if node.returns:
                            try:
                                ret_type = ast.unparse(node.returns)
                            except Exception:
                                pass
                        fn_info = {
                            "name": node.name,
                            "target_file": fp,
                            "params": p_names,
                            "param_types": p_types,
                            "return_type": ret_type,
                            "route": r,
                            "method": m,
                            "status_code": sc
                        }
                        functions[node.name] = fn_info
                        if r:
                            norm_r = normalize_route_path(r)
                            route_endpoints.setdefault(norm_r, []).append(fn_info)
            except Exception:
                pass

    return classes, functions, route_endpoints


def check_obligation_coverage(
    obligations: List[CanonicalObligation],
    contract: Any,
    blueprint: Optional[Any] = None
) -> CoverageMatrix:
    """
    Memeriksa cakupan (*coverage*) obligasi Oracle terhadap deklarasi kontrak kanonikal.

    PRINSIP KOREKSI 1:
    100% Coverage bukan berarti 100% string equality naif.
    Yang wajib 100% adalah: SELURUH mandatory acceptance obligations Oracle terbukti COVERED.
    Satu obligation dapat memiliki representasi Architect yang berbeda tetapi tetap valid
    jika deterministic checker dapat membuktikan kompatibilitasnya.
    Ekuivalensi tidak boleh diasumsikan tanpa bukti, dan tidak boleh ditolak hanya karena
    perbedaan string nama jika bukti struktural/semantik kompatibilitas tersedia (misal: route mapping).

    PRINSIP KOREKSI 3:
    Coverage engine hanya memberikan DIAGNOSIS (WHAT is missing/incompatible), BUKAN instruksi HOW.
    """
    # Normalisasi contract input menjadi dictionary
    contract_dict: Dict[str, Any] = {}
    if isinstance(contract, dict):
        contract_dict = contract
    elif hasattr(contract, "to_dict"):
        contract_dict = contract.to_dict()
    elif hasattr(contract, "model_dump"):
        contract_dict = contract.model_dump()
    elif isinstance(contract, list):
        contract_dict = {"interface_contracts": contract}

    declared_interfaces = contract_dict.get("interface_contracts") or []
    declared_models = contract_dict.get("data_models") or []

    # Map public interfaces by normalized identity
    # 1. HTTP endpoints map: {base_path: list of CanonicalInterfaceDeclaration}
    http_endpoints: Dict[str, List[CanonicalInterfaceDeclaration]] = {}
    # 2. Named callable/symbol map: {identifier: list of CanonicalInterfaceDeclaration}
    symbol_interfaces: Dict[str, List[CanonicalInterfaceDeclaration]] = {}

    declarations_count = len(declared_interfaces) + len(declared_models)

    # Ekstraksi file scaffold dari blueprint dan/atau contract untuk ekstraksi fakta deterministik (Treatment #1.8.10 Part A)
    scaffold_files: Dict[str, Any] = {}
    if blueprint:
        if hasattr(blueprint, "files") and getattr(blueprint, "files"):
            for fp, mod in blueprint.files.items():
                sc = getattr(mod, "code_scaffold", None) or (mod.get("code_scaffold") if isinstance(mod, dict) else str(mod))
                if sc:
                    scaffold_files[fp] = sc
        elif isinstance(blueprint, dict) and "files" in blueprint and isinstance(blueprint["files"], dict):
            for fp, mod in blueprint["files"].items():
                sc = mod.get("code_scaffold") if isinstance(mod, dict) else (getattr(mod, "code_scaffold", None) or str(mod))
                if sc:
                    scaffold_files[fp] = sc
        elif isinstance(blueprint, dict):
            for k in ("code_scaffold", "scaffold_code", "scaffold"):
                if k in blueprint and isinstance(blueprint[k], str):
                    scaffold_files["main.py"] = blueprint[k]
                    break

    if isinstance(contract_dict, dict) and "files" in contract_dict and isinstance(contract_dict["files"], dict):
        for fp, mod in contract_dict["files"].items():
            if fp not in scaffold_files:
                sc = mod.get("code_scaffold") if isinstance(mod, dict) else (getattr(mod, "code_scaffold", None) or str(mod))
                if sc:
                    scaffold_files[fp] = sc
    elif isinstance(contract_dict, dict):
        for k in ("code_scaffold", "scaffold_code", "scaffold"):
            if k in contract_dict and isinstance(contract_dict[k], str):
                if "main.py" not in scaffold_files:
                    scaffold_files["main.py"] = contract_dict[k]
                break

    scaffold_facts: List[ScaffoldCallableFact] = []
    if scaffold_files and extract_all_scaffold_facts is not None:
        try:
            scaffold_facts = extract_all_scaffold_facts(scaffold_files)
        except Exception:
            pass

    scaffold_classes, scaffold_functions, scaffold_route_endpoints = _extract_all_scaffold_symbols(scaffold_files)

    canonical_interfaces: List[CanonicalInterfaceDeclaration] = []
    for raw_ifc in declared_interfaces:
        c_ifc = normalize_interface_declaration(raw_ifc)
        if not c_ifc:
            continue
        canonical_interfaces.append(c_ifc)

    if scaffold_facts:
        bind_scaffold_callable_facts_to_interfaces(canonical_interfaces, scaffold_facts)

    for c_ifc in canonical_interfaces:
        if c_ifc.canonical_route:
            norm_r = normalize_route_path(c_ifc.canonical_route)
            http_endpoints.setdefault(norm_r, []).append(c_ifc)

        symbol_interfaces.setdefault(c_ifc.identifier, []).append(c_ifc)
        if "." in c_ifc.identifier:
            for part in c_ifc.identifier.split("."):
                p_clean = part.strip()
                if p_clean:
                    symbol_interfaces.setdefault(p_clean, []).append(c_ifc)

    # Map models by name: {model_name: model dict}
    data_models_map: Dict[str, Dict[str, Any]] = {}
    for m in declared_models:
        if not isinstance(m, dict):
            if hasattr(m, "model_dump"):
                m = m.model_dump()
            elif hasattr(m, "to_dict"):
                m = m.to_dict()
            else:
                continue
        m_name = str(m.get("model_name", "")).strip()
        if m_name:
            data_models_map[m_name] = m

    results: List[ObligationCoverageResult] = []
    covered_cnt = 0
    partial_cnt = 0
    missing_cnt = 0
    incompatible_cnt = 0
    undetermined_cnt = 0
    summary_reasons: List[str] = []

    for ob in obligations:
        # Provenance verification: HANYA ORACLE_FACT yang diverifikasi sebagai acceptance obligation
        if ob.authority not in (ObligationAuthority.ORACLE.value, ObligationAuthority.FROZEN_ORACLE.value, "ORACLE", "FROZEN_ORACLE") or ob.provenance != ObligationProvenance.ORACLE_FACT.value:
            res = ObligationCoverageResult(
                obligation=ob,
                status=CoverageStatus.UNDETERMINED,
                reason=f"Obligation authority/provenance is not ORACLE_FACT ({ob.authority}/{ob.provenance})"
            )
            results.append(res)
            undetermined_cnt += 1
            continue

        # A. INTERACTION OBLIGATION (e.g. HTTP POST /products or GET /products/{id})
        if ob.obligation_kind == ObligationKind.INTERACTION.value:
            req_path = normalize_route_path(ob.public_identity)
            req_method = ob.inputs.get("http_method", "").upper().strip() if ob.inputs else ""

            # Pembuktian Kompatibilitas Semantik (Distinct Public Identities):
            # 1. Exact match pada normalized route path
            matched_ifcs: List[CanonicalInterfaceDeclaration] = list(http_endpoints.get(req_path, []))

            # 2. Semantic match: parameterized endpoint (/users/{id}) vs base route (/users) dengan PATH parameter
            if not matched_ifcs and "{id}" in req_path:
                base_req = req_path.replace("/{id}", "").rstrip("/")
                for candidate in http_endpoints.get(base_req, []):
                    has_path_param = any(
                        (isinstance(p, dict) and p.get("param_location") == "PATH") or
                        (hasattr(p, "param_location") and getattr(p, "param_location") == "PATH")
                        for p in candidate.parameters
                    )
                    if has_path_param:
                        matched_ifcs.append(candidate)

            if not matched_ifcs:
                # Cek apakah ada antarmuka dengan canonical_route yang cocok
                for sym_name, ifc_list in symbol_interfaces.items():
                    for c_ifc in ifc_list:
                        if c_ifc.canonical_route:
                            norm_c = normalize_route_path(c_ifc.canonical_route)
                            if norm_c == req_path:
                                matched_ifcs.append(c_ifc)
                            elif "{id}" in req_path and norm_c.rstrip("/") == req_path.replace("/{id}", "").rstrip("/"):
                                has_path_param = any(
                                    (isinstance(p, dict) and p.get("param_location") == "PATH") or
                                    (hasattr(p, "param_location") and getattr(p, "param_location") == "PATH")
                                    for p in c_ifc.parameters
                                )
                                if has_path_param:
                                    matched_ifcs.append(c_ifc)

            if not matched_ifcs and scaffold_facts:
                matching_rf = [
                    f for f in scaffold_facts
                    if f.route and normalize_route_path(f.route) == req_path
                ]
                if req_method and len(matching_rf) > 1:
                    matching_rf_m = [f for f in matching_rf if f.http_method and f.http_method.upper() == req_method]
                    if matching_rf_m:
                        matching_rf = matching_rf_m

                distinct_names = {f.name for f in matching_rf}
                if len(matching_rf) >= 1 and len(distinct_names) == 1:
                    rf = matching_rf[0]
                    synth_ifc = CanonicalInterfaceDeclaration(
                        identifier=rf.name,
                        target_file=rf.file_path,
                        interface_type="HTTP_ENDPOINT",
                        canonical_route=normalize_route_path(rf.route),
                        canonical_method=str(rf.http_method).upper() if rf.http_method else None,
                        raw_declaration={"identifier": rf.name, "route": rf.route, "http_method": rf.http_method}
                    )
                    matched_ifcs.append(synth_ifc)

            if not matched_ifcs:
                clean_name = req_path.strip("/").replace("/", "_")
                potential_internal = [s for s in symbol_interfaces.keys() if clean_name in s.lower()]
                reason_extra = ""
                if potential_internal:
                    reason_extra = (
                        f" (Notice: Found internal function(s) {potential_internal}, but no public route/endpoint "
                        f"binding proof connects them to public endpoint '{req_path}')"
                    )

                evidence = AuthorityBindingEvidence(
                    authority_source=ob.source_reference,
                    authority_symbol=ob.public_identity,
                    mismatch_dimension=AuthorityMismatchDimension.ROUTE_METHOD,
                    expected_value=f"{req_method} {req_path}" if req_method else req_path,
                    actual_value=None,
                    reason=f"Public HTTP endpoint '{req_path}' has no declared interface coverage in contract{reason_extra}",
                    target_artifact=ob.source_reference
                )

                res = ObligationCoverageResult(
                    obligation=ob,
                    status=CoverageStatus.MISSING,
                    reason=f"Public HTTP endpoint '{req_path}' has no declared interface coverage in contract{reason_extra}",
                    missing_aspects=[f"HTTP endpoint: {req_path}"],
                    binding_evidence=evidence
                )
                results.append(res)
                missing_cnt += 1
                summary_reasons.append(f"MISSING: {ob.obligation_id} ({ob.public_identity})")

            else:
                # Path found, now evaluate method compatibility and authority binding dimensions
                if req_method:
                    compatible_ifc: Optional[CanonicalInterfaceDeclaration] = None
                    declared_methods: List[str] = []

                    for c_ifc in matched_ifcs:
                        m = c_ifc.canonical_method
                        if m:
                            declared_methods.append(m)
                            if m == req_method:
                                compatible_ifc = c_ifc
                                break

                    if compatible_ifc is not None:
                        matched_id = compatible_ifc.raw_declaration.get("interface_id") or compatible_ifc.identifier
                        mismatch_evidence: Optional[AuthorityBindingEvidence] = None
                        mismatch_status: Optional[CoverageStatus] = None
                        mismatch_reason = ""

                        # 1. Dimension: RETURN_IDENTITY / STATUS_CODE
                        exp_status = ob.outputs.get("expected_status") if ob.outputs else None
                        if exp_status is not None:
                            dec_status = compatible_ifc.raw_declaration.get("status_code")
                            if dec_status is None and isinstance(compatible_ifc.raw_declaration.get("returns"), dict):
                                dec_status = compatible_ifc.raw_declaration["returns"].get("status_code")
                            if dec_status is None:
                                for fn in scaffold_route_endpoints.get(req_path, []):
                                    if (not req_method or fn.get("method") == req_method) and fn.get("status_code") is not None:
                                        dec_status = fn.get("status_code")
                                        break
                            if dec_status is not None and dec_status != exp_status:
                                mismatch_status = CoverageStatus.INCOMPATIBLE
                                mismatch_reason = (
                                    f"HTTP endpoint '{req_path}' [{req_method}] declares status code {dec_status}, "
                                    f"but acceptance tests assert status code {exp_status}"
                                )
                                mismatch_evidence = AuthorityBindingEvidence(
                                    authority_source=ob.source_reference,
                                    authority_symbol=ob.public_identity,
                                    blueprint_symbol=matched_id,
                                    mismatch_dimension=AuthorityMismatchDimension.RETURN_IDENTITY,
                                    expected_value=exp_status,
                                    actual_value=dec_status,
                                    reason=mismatch_reason,
                                    target_artifact=compatible_ifc.target_file
                                )

                        # 2. Dimension: PARAMETER_IDENTITY (payload fields)
                        auth_payload_fields = ob.inputs.get("payload_fields") if ob.inputs else None
                        if mismatch_status is None and auth_payload_fields:
                            declared_payload_fields: Set[str] = set()
                            for p in compatible_ifc.parameters:
                                p_name = p.get("name") if isinstance(p, dict) else (p.get("param_name") if isinstance(p, dict) else getattr(p, "name", ""))
                                p_type = p.get("type") if isinstance(p, dict) else (p.get("param_type") if isinstance(p, dict) else getattr(p, "type", ""))
                                if p_type and p_type in data_models_map:
                                    m_fields = data_models_map[p_type].get("fields", [])
                                    for f in m_fields:
                                        f_name = f.get("name") if isinstance(f, dict) else (f.get("field_name") if isinstance(f, dict) else getattr(f, "name", str(f)))
                                        if f_name:
                                            declared_payload_fields.add(f_name)
                                elif p_type and p_type in scaffold_classes:
                                    declared_payload_fields.update(scaffold_classes[p_type].get("fields", []))
                                elif p_name and p_name not in ("request", "response", "db", "session"):
                                    declared_payload_fields.add(p_name)

                            for fn in scaffold_route_endpoints.get(req_path, []):
                                if not req_method or fn.get("method") == req_method:
                                    for p_name, p_type in fn.get("param_types", {}).items():
                                        if p_type in scaffold_classes:
                                            declared_payload_fields.update(scaffold_classes[p_type].get("fields", []))
                                        elif p_type in data_models_map:
                                            m_fields = data_models_map[p_type].get("fields", [])
                                            for f in m_fields:
                                                f_name = f.get("name") if isinstance(f, dict) else (f.get("field_name") if isinstance(f, dict) else getattr(f, "name", str(f)))
                                                if f_name:
                                                    declared_payload_fields.add(f_name)
                                    for p_name in fn.get("params", []):
                                        if p_name not in ("request", "response", "db", "session"):
                                            declared_payload_fields.add(p_name)

                            if not declared_payload_fields:
                                res_clean = req_path.strip("/").split("/")[0].rstrip("s")
                                for m_name, m_data in data_models_map.items():
                                    if res_clean.lower() in m_name.lower():
                                        for f in m_data.get("fields", []):
                                            f_name = f.get("name") if isinstance(f, dict) else (f.get("field_name") if isinstance(f, dict) else getattr(f, "name", str(f)))
                                            if f_name:
                                                declared_payload_fields.add(f_name)
                                        break

                            if not declared_payload_fields:
                                res_clean = req_path.strip("/").split("/")[0].rstrip("s")
                                for c_name, c_data in scaffold_classes.items():
                                    if res_clean.lower() in c_name.lower():
                                        declared_payload_fields.update(c_data.get("fields", []))
                                        break

                            if declared_payload_fields:
                                missing_payload = [f for f in auth_payload_fields if f not in declared_payload_fields]
                                if missing_payload:
                                    mismatch_status = CoverageStatus.INCOMPATIBLE
                                    mismatch_reason = (
                                        f"Authoritative payload field(s) {missing_payload} are not accepted by endpoint/model "
                                        f"for '{req_path}' [{req_method}] (declared fields: {sorted(list(declared_payload_fields))})"
                                    )
                                    mismatch_evidence = AuthorityBindingEvidence(
                                        authority_source=ob.source_reference,
                                        authority_symbol=ob.public_identity,
                                        blueprint_symbol=matched_id,
                                        mismatch_dimension=AuthorityMismatchDimension.PARAMETER_IDENTITY,
                                        expected_value=auth_payload_fields,
                                        actual_value=sorted(list(declared_payload_fields)),
                                        reason=mismatch_reason,
                                        target_artifact=compatible_ifc.target_file
                                    )

                        # 3. Dimension: TARGET_ARTIFACT
                        if mismatch_status is None and ob.metadata and ob.metadata.get("target_artifact"):
                            exp_art = ob.metadata["target_artifact"]
                            if compatible_ifc.target_file and Path(compatible_ifc.target_file).name != Path(exp_art).name:
                                mismatch_status = CoverageStatus.INCOMPATIBLE
                                mismatch_reason = (
                                    f"Target artifact mismatch for '{req_path}': expected {exp_art}, "
                                    f"but declared in {compatible_ifc.target_file}"
                                )
                                mismatch_evidence = AuthorityBindingEvidence(
                                    authority_source=ob.source_reference,
                                    authority_symbol=ob.public_identity,
                                    blueprint_symbol=matched_id,
                                    mismatch_dimension=AuthorityMismatchDimension.TARGET_ARTIFACT,
                                    expected_value=exp_art,
                                    actual_value=compatible_ifc.target_file,
                                    reason=mismatch_reason,
                                    target_artifact=compatible_ifc.target_file
                                )

                        if mismatch_status is not None:
                            res = ObligationCoverageResult(
                                obligation=ob,
                                status=mismatch_status,
                                matched_declaration_id=matched_id,
                                reason=mismatch_reason,
                                missing_aspects=[mismatch_reason],
                                binding_evidence=mismatch_evidence
                            )
                            results.append(res)
                            incompatible_cnt += 1
                            summary_reasons.append(f"INCOMPATIBLE: {ob.obligation_id} ({mismatch_reason})")
                        else:
                            res = ObligationCoverageResult(
                                obligation=ob,
                                status=CoverageStatus.COVERED,
                                matched_declaration_id=matched_id,
                                reason=f"HTTP endpoint '{req_path}' [{req_method}] has proven coverage by interface contract '{matched_id}'"
                            )
                            results.append(res)
                            covered_cnt += 1

                    elif declared_methods:
                        matched_id = matched_ifcs[0].raw_declaration.get("interface_id") or matched_ifcs[0].identifier
                        evidence = AuthorityBindingEvidence(
                            authority_source=ob.source_reference,
                            authority_symbol=ob.public_identity,
                            blueprint_symbol=matched_id,
                            mismatch_dimension=AuthorityMismatchDimension.ROUTE_METHOD,
                            expected_value=req_method,
                            actual_value=declared_methods,
                            reason=f"HTTP endpoint '{req_path}' declared with method(s) {declared_methods}, but expected method [{req_method}] is missing from contract",
                            target_artifact=matched_ifcs[0].target_file
                        )
                        res = ObligationCoverageResult(
                            obligation=ob,
                            status=CoverageStatus.MISSING,
                            matched_declaration_id=matched_id,
                            reason=f"HTTP endpoint '{req_path}' declared with method(s) {declared_methods}, but expected method [{req_method}] is missing from contract",
                            missing_aspects=[f"HTTP method: {req_method}"],
                            binding_evidence=evidence
                        )
                        results.append(res)
                        missing_cnt += 1
                        summary_reasons.append(f"MISSING: {ob.obligation_id} (Method [{req_method}] missing, found {declared_methods})")
                    else:
                        matched_id = matched_ifcs[0].raw_declaration.get("interface_id") or matched_ifcs[0].identifier
                        evidence = AuthorityBindingEvidence(
                            authority_source=ob.source_reference,
                            authority_symbol=ob.public_identity,
                            blueprint_symbol=matched_id,
                            mismatch_dimension=AuthorityMismatchDimension.INSUFFICIENT_EVIDENCE,
                            expected_value=req_method,
                            actual_value=None,
                            reason=f"HTTP endpoint '{req_path}' declared in contract without explicit HTTP method (cannot prove compatibility with expected method [{req_method}])",
                            target_artifact=matched_ifcs[0].target_file
                        )
                        res = ObligationCoverageResult(
                            obligation=ob,
                            status=CoverageStatus.UNDETERMINED,
                            matched_declaration_id=matched_id,
                            reason=f"HTTP endpoint '{req_path}' declared in contract without explicit HTTP method (cannot prove compatibility with expected method [{req_method}])",
                            missing_aspects=[f"Explicit HTTP method [{req_method}] on {req_path}"],
                            binding_evidence=evidence
                        )
                        results.append(res)
                        undetermined_cnt += 1
                        summary_reasons.append(f"UNDETERMINED: {ob.obligation_id} (HTTP method absent on contract declaration)")
                else:
                    matched_id = matched_ifcs[0].raw_declaration.get("interface_id") or matched_ifcs[0].identifier
                    res = ObligationCoverageResult(
                        obligation=ob,
                        status=CoverageStatus.COVERED,
                        matched_declaration_id=matched_id,
                        reason=f"HTTP endpoint '{req_path}' has proven coverage by interface contract '{matched_id}'"
                    )
                    results.append(res)
                    covered_cnt += 1

        # B. DATA MODEL OBLIGATION (e.g. MetricData, Product, Matrix)
        elif ob.obligation_kind == ObligationKind.DATA_MODEL.value:
            model_name = ob.public_identity
            matched_model: Optional[Dict[str, Any]] = None
            matched_id: Optional[str] = None
            target_file: Optional[str] = None

            if model_name in data_models_map:
                matched_model = data_models_map[model_name]
                matched_id = matched_model.get("model_name")
                target_file = matched_model.get("target_file")
            elif model_name in symbol_interfaces:
                c_ifc = symbol_interfaces[model_name][0]
                matched_id = c_ifc.raw_declaration.get("interface_id") or c_ifc.identifier
                target_file = c_ifc.target_file
            elif model_name in scaffold_classes:
                c_sc = scaffold_classes[model_name]
                matched_id = model_name
                target_file = c_sc.get("target_file")

            if matched_id is None:
                all_declared = sorted(list(data_models_map.keys()) + list(symbol_interfaces.keys()) + list(scaffold_classes.keys()))
                evidence = AuthorityBindingEvidence(
                    authority_source=ob.source_reference,
                    authority_symbol=model_name,
                    mismatch_dimension=AuthorityMismatchDimension.CALLABLE_IDENTITY,
                    expected_value=model_name,
                    actual_value=all_declared,
                    reason=f"Data model / entity '{model_name}' is not declared in contract data_models or interface_contracts",
                    target_artifact=ob.source_reference
                )
                res = ObligationCoverageResult(
                    obligation=ob,
                    status=CoverageStatus.MISSING,
                    reason=f"Data model/class '{model_name}' is not declared in contract data_models or interface_contracts",
                    missing_aspects=[f"Data model: {model_name}"],
                    binding_evidence=evidence
                )
                results.append(res)
                missing_cnt += 1
                summary_reasons.append(f"MISSING: {ob.obligation_id} ({model_name})")
            else:
                mismatch_evidence = None
                mismatch_status = None
                mismatch_reason = ""

                # Dimension: PARAMETER_IDENTITY (model fields)
                auth_fields = ob.keyword_arguments or ob.argument_names or (ob.inputs.get("fields") if ob.inputs else [])
                if auth_fields and (model_name in scaffold_classes or blueprint is not None or scaffold_files):
                    declared_fields: Set[str] = set()
                    if matched_model:
                        for f in matched_model.get("fields", []):
                            f_name = f.get("name") if isinstance(f, dict) else (f.get("field_name") if isinstance(f, dict) else getattr(f, "name", str(f)))
                            if f_name:
                                declared_fields.add(f_name)
                    if model_name in scaffold_classes:
                        declared_fields.update(scaffold_classes[model_name].get("fields", []))

                    if declared_fields:
                        missing_fields = [f for f in auth_fields if f not in declared_fields]
                        if missing_fields:
                            mismatch_status = CoverageStatus.INCOMPATIBLE
                            mismatch_reason = (
                                f"Data model '{model_name}' is missing required field(s): {missing_fields} "
                                f"(declared fields: {sorted(list(declared_fields))})"
                            )
                            mismatch_evidence = AuthorityBindingEvidence(
                                authority_source=ob.source_reference,
                                authority_symbol=model_name,
                                blueprint_symbol=matched_id,
                                mismatch_dimension=AuthorityMismatchDimension.PARAMETER_IDENTITY,
                                expected_value=auth_fields,
                                actual_value=sorted(list(declared_fields)),
                                reason=mismatch_reason,
                                target_artifact=target_file
                            )

                # Dimension: TARGET_ARTIFACT
                if mismatch_status is None and ob.metadata and ob.metadata.get("target_artifact"):
                    exp_art = ob.metadata["target_artifact"]
                    if target_file and Path(target_file).name != Path(exp_art).name:
                        mismatch_status = CoverageStatus.INCOMPATIBLE
                        mismatch_reason = (
                            f"Target artifact mismatch for data model '{model_name}': expected {exp_art}, "
                            f"but declared in {target_file}"
                        )
                        mismatch_evidence = AuthorityBindingEvidence(
                            authority_source=ob.source_reference,
                            authority_symbol=model_name,
                            blueprint_symbol=matched_id,
                            mismatch_dimension=AuthorityMismatchDimension.TARGET_ARTIFACT,
                            expected_value=exp_art,
                            actual_value=target_file,
                            reason=mismatch_reason,
                            target_artifact=target_file
                        )

                if mismatch_status is not None:
                    res = ObligationCoverageResult(
                        obligation=ob,
                        status=mismatch_status,
                        matched_declaration_id=matched_id,
                        reason=mismatch_reason,
                        missing_aspects=[mismatch_reason],
                        binding_evidence=mismatch_evidence
                    )
                    results.append(res)
                    incompatible_cnt += 1
                    summary_reasons.append(f"INCOMPATIBLE: {ob.obligation_id} ({mismatch_reason})")
                else:
                    res = ObligationCoverageResult(
                        obligation=ob,
                        status=CoverageStatus.COVERED,
                        matched_declaration_id=matched_id,
                        reason=f"Data model '{model_name}' covered in contract/scaffold"
                    )
                    results.append(res)
                    covered_cnt += 1

        # C. CALLABLE INTERFACE (e.g. add_matrices, metricDataProvider)
        elif ob.obligation_kind == ObligationKind.CALLABLE_INTERFACE.value:
            symbol_name = ob.public_identity
            matched_id: Optional[str] = None
            target_file: Optional[str] = None

            if symbol_name in symbol_interfaces:
                c_ifc = symbol_interfaces[symbol_name][0]
                matched_id = c_ifc.raw_declaration.get("interface_id") or c_ifc.identifier
                target_file = c_ifc.target_file
            elif symbol_name in data_models_map:
                matched_id = data_models_map[symbol_name].get("model_name")
                target_file = data_models_map[symbol_name].get("target_file")
            elif symbol_name in scaffold_functions:
                matched_id = symbol_name
                target_file = scaffold_functions[symbol_name].get("target_file")
            elif symbol_name in scaffold_classes:
                matched_id = symbol_name
                target_file = scaffold_classes[symbol_name].get("target_file")

            if matched_id is None:
                all_declared = sorted(list(symbol_interfaces.keys()) + list(data_models_map.keys()) + list(scaffold_functions.keys()) + list(scaffold_classes.keys()))
                evidence = AuthorityBindingEvidence(
                    authority_source=ob.source_reference,
                    authority_symbol=symbol_name,
                    mismatch_dimension=AuthorityMismatchDimension.CALLABLE_IDENTITY,
                    expected_value=symbol_name,
                    actual_value=all_declared,
                    reason=f"Callable symbol/interface '{symbol_name}' is missing from contract interface_contracts",
                    target_artifact=ob.source_reference
                )
                res = ObligationCoverageResult(
                    obligation=ob,
                    status=CoverageStatus.MISSING,
                    reason=f"Callable symbol/interface '{symbol_name}' is missing from contract interface_contracts",
                    missing_aspects=[f"Callable interface: {symbol_name}"],
                    binding_evidence=evidence
                )
                results.append(res)
                missing_cnt += 1
                summary_reasons.append(f"MISSING: {ob.obligation_id} ({symbol_name})")
            else:
                mismatch_evidence = None
                mismatch_status = None
                mismatch_reason = ""

                # Dimension: TARGET_ARTIFACT
                if ob.metadata and ob.metadata.get("target_artifact"):
                    exp_art = ob.metadata["target_artifact"]
                    if target_file and Path(target_file).name != Path(exp_art).name:
                        mismatch_status = CoverageStatus.INCOMPATIBLE
                        mismatch_reason = (
                            f"Target artifact mismatch for callable '{symbol_name}': expected {exp_art}, "
                            f"but declared in {target_file}"
                        )
                        mismatch_evidence = AuthorityBindingEvidence(
                            authority_source=ob.source_reference,
                            authority_symbol=symbol_name,
                            blueprint_symbol=matched_id,
                            mismatch_dimension=AuthorityMismatchDimension.TARGET_ARTIFACT,
                            expected_value=exp_art,
                            actual_value=target_file,
                            reason=mismatch_reason,
                            target_artifact=target_file
                        )

                if mismatch_status is not None:
                    res = ObligationCoverageResult(
                        obligation=ob,
                        status=mismatch_status,
                        matched_declaration_id=matched_id,
                        reason=mismatch_reason,
                        missing_aspects=[mismatch_reason],
                        binding_evidence=mismatch_evidence
                    )
                    results.append(res)
                    incompatible_cnt += 1
                    summary_reasons.append(f"INCOMPATIBLE: {ob.obligation_id} ({mismatch_reason})")
                else:
                    res = ObligationCoverageResult(
                        obligation=ob,
                        status=CoverageStatus.COVERED,
                        matched_declaration_id=matched_id,
                        reason=f"Callable interface '{symbol_name}' covered by contract/scaffold '{matched_id}'"
                    )
                    results.append(res)
                    covered_cnt += 1

        # D. OBSERVABLE RUNTIME (e.g. UI Widget CardMetric)
        elif ob.obligation_kind == ObligationKind.OBSERVABLE_RUNTIME.value:
            widget_name = ob.public_identity
            matched_id: Optional[str] = None
            target_file: Optional[str] = None

            if widget_name in symbol_interfaces:
                c_ifc = symbol_interfaces[widget_name][0]
                matched_id = c_ifc.raw_declaration.get("interface_id") or c_ifc.identifier
                target_file = c_ifc.target_file
            elif widget_name in data_models_map:
                matched_id = data_models_map[widget_name].get("model_name")
                target_file = data_models_map[widget_name].get("target_file")
            elif widget_name in scaffold_classes:
                matched_id = widget_name
                target_file = scaffold_classes[widget_name].get("target_file")

            if matched_id is None:
                all_declared = sorted(list(symbol_interfaces.keys()) + list(data_models_map.keys()) + list(scaffold_classes.keys()))
                evidence = AuthorityBindingEvidence(
                    authority_source=ob.source_reference,
                    authority_symbol=widget_name,
                    mismatch_dimension=AuthorityMismatchDimension.CALLABLE_IDENTITY,
                    expected_value=widget_name,
                    actual_value=all_declared,
                    reason=f"Observable runtime component/widget '{widget_name}' is not declared in interface_contracts",
                    target_artifact=ob.source_reference
                )
                res = ObligationCoverageResult(
                    obligation=ob,
                    status=CoverageStatus.MISSING,
                    reason=f"Observable runtime component/widget '{widget_name}' is not declared in interface_contracts",
                    missing_aspects=[f"Component/Widget: {widget_name}"],
                    binding_evidence=evidence
                )
                results.append(res)
                missing_cnt += 1
                summary_reasons.append(f"MISSING: {ob.obligation_id} ({widget_name})")
            else:
                mismatch_evidence = None
                mismatch_status = None
                mismatch_reason = ""

                # Dimension: PARAMETER_IDENTITY (e.g. named arguments like data)
                auth_args = ob.keyword_arguments or ob.argument_names or []
                if auth_args:
                    declared_args: Set[str] = set()
                    if widget_name in symbol_interfaces:
                        for p in symbol_interfaces[widget_name][0].parameters:
                            p_name = p.get("name") if isinstance(p, dict) else getattr(p, "name", "")
                            if p_name:
                                declared_args.add(p_name)
                    if widget_name in scaffold_classes:
                        declared_args.update(scaffold_classes[widget_name].get("named_params", []))
                        declared_args.update(scaffold_classes[widget_name].get("fields", []))

                    if declared_args:
                        missing_args = [a for a in auth_args if a not in declared_args]
                        if missing_args:
                            mismatch_status = CoverageStatus.INCOMPATIBLE
                            mismatch_reason = (
                                f"Widget constructor '{widget_name}' missing required named parameter(s): {missing_args} "
                                f"(declared parameters: {sorted(list(declared_args))})"
                            )
                            mismatch_evidence = AuthorityBindingEvidence(
                                authority_source=ob.source_reference,
                                authority_symbol=widget_name,
                                blueprint_symbol=matched_id,
                                mismatch_dimension=AuthorityMismatchDimension.PARAMETER_IDENTITY,
                                expected_value=auth_args,
                                actual_value=sorted(list(declared_args)),
                                reason=mismatch_reason,
                                target_artifact=target_file
                            )

                # Dimension: TARGET_ARTIFACT
                if mismatch_status is None and ob.metadata and ob.metadata.get("target_artifact"):
                    exp_art = ob.metadata["target_artifact"]
                    if target_file and Path(target_file).name != Path(exp_art).name:
                        mismatch_status = CoverageStatus.INCOMPATIBLE
                        mismatch_reason = (
                            f"Target artifact mismatch for widget '{widget_name}': expected {exp_art}, "
                            f"but declared in {target_file}"
                        )
                        mismatch_evidence = AuthorityBindingEvidence(
                            authority_source=ob.source_reference,
                            authority_symbol=widget_name,
                            blueprint_symbol=matched_id,
                            mismatch_dimension=AuthorityMismatchDimension.TARGET_ARTIFACT,
                            expected_value=exp_art,
                            actual_value=target_file,
                            reason=mismatch_reason,
                            target_artifact=target_file
                        )

                if mismatch_status is not None:
                    res = ObligationCoverageResult(
                        obligation=ob,
                        status=mismatch_status,
                        matched_declaration_id=matched_id,
                        reason=mismatch_reason,
                        missing_aspects=[mismatch_reason],
                        binding_evidence=mismatch_evidence
                    )
                    results.append(res)
                    incompatible_cnt += 1
                    summary_reasons.append(f"INCOMPATIBLE: {ob.obligation_id} ({mismatch_reason})")
                else:
                    res = ObligationCoverageResult(
                        obligation=ob,
                        status=CoverageStatus.COVERED,
                        matched_declaration_id=matched_id,
                        reason=f"Observable runtime widget '{widget_name}' covered by interface contract {matched_id}"
                    )
                    results.append(res)
                    covered_cnt += 1

        # E. DEFAULT / BEHAVIORAL
        else:
            identity = ob.public_identity
            if identity in symbol_interfaces or identity in data_models_map or identity in scaffold_classes or identity in scaffold_functions:
                res = ObligationCoverageResult(
                    obligation=ob,
                    status=CoverageStatus.COVERED,
                    reason=f"Obligation '{identity}' covered by matching public contract symbol"
                )
                results.append(res)
                covered_cnt += 1
            else:
                evidence = AuthorityBindingEvidence(
                    authority_source=ob.source_reference,
                    authority_symbol=identity,
                    mismatch_dimension=AuthorityMismatchDimension.CALLABLE_IDENTITY,
                    expected_value=identity,
                    actual_value=sorted(list(symbol_interfaces.keys()) + list(data_models_map.keys())),
                    reason=f"Obligation '{identity}' has no corresponding public interface contract",
                    target_artifact=ob.source_reference
                )
                res = ObligationCoverageResult(
                    obligation=ob,
                    status=CoverageStatus.MISSING,
                    reason=f"Obligation '{identity}' has no corresponding public interface contract",
                    missing_aspects=[f"Identity: {identity}"],
                    binding_evidence=evidence
                )
                results.append(res)
                missing_cnt += 1
                summary_reasons.append(f"MISSING: {ob.obligation_id} ({identity})")

    final_results: List[ObligationCoverageResult] = []
    for r in results:
        ob_pos = r.obligation.positional_arguments or 0
        ob_kw = r.obligation.keyword_arguments or []
        if r.status == CoverageStatus.COVERED and (ob_pos > 0 or len(ob_kw) > 0):
            call_shape_status, call_shape_reason, call_shape_meta = check_call_shape_compatibility(
                r.obligation,
                contract_dict,
                blueprint=blueprint
            )
            if call_shape_status in (CoverageStatus.INCOMPATIBLE, "INCOMPATIBLE"):
                evidence = AuthorityBindingEvidence(
                    authority_source=r.obligation.source_reference,
                    authority_symbol=r.obligation.public_identity,
                    blueprint_symbol=r.matched_declaration_id,
                    mismatch_dimension=AuthorityMismatchDimension.PARAMETER_IDENTITY,
                    expected_value={"positional": ob_pos, "keywords": ob_kw},
                    actual_value=call_shape_meta,
                    reason=call_shape_reason,
                    target_artifact=r.obligation.source_reference
                )
                r = ObligationCoverageResult(
                    obligation=r.obligation,
                    status=CoverageStatus.INCOMPATIBLE,
                    matched_declaration_id=r.matched_declaration_id,
                    reason=call_shape_reason,
                    missing_aspects=[f"Call shape compatible with {r.obligation.positional_arguments} pos / {r.obligation.keyword_arguments} kw"],
                    binding_evidence=evidence
                )
                covered_cnt -= 1
                incompatible_cnt += 1
                summary_reasons.append(f"INCOMPATIBLE: {r.obligation.obligation_id} ({r.obligation.public_identity}) - {call_shape_reason}")
        final_results.append(r)

    is_fully = (
        len(obligations) > 0 and
        covered_cnt == len(obligations) and
        missing_cnt == 0 and
        partial_cnt == 0 and
        incompatible_cnt == 0 and
        undetermined_cnt == 0
    )

    return CoverageMatrix(
        obligations_count=len(obligations),
        declarations_count=declarations_count,
        covered_count=covered_cnt,
        partial_count=partial_cnt,
        missing_count=missing_cnt,
        incompatible_count=incompatible_cnt,
        undetermined_count=undetermined_cnt,
        is_fully_covered=is_fully,
        results=final_results,
        summary_reasons=summary_reasons
    )


# ===========================================================================
# 9. Canonical Read-Only Obligation Ledger Formatter
# ===========================================================================

def format_authoritative_obligation_ledger(obligations: List[CanonicalObligation]) -> str:
    """
    Memformat seluruh Canonical Acceptance Obligations menjadi ledger teks kanonikal
    yang terstruktur, informatif, dan murni READ-ONLY untuk diinjeksikan ke konteks Architect.

    DOKTRIN & BATASAN KERAS:
    - Otoritas: FROZEN_ORACLE (Acceptance Authority).
    - Menjelaskan WHAT (apa yang diuji dan wajib dipenuhi oleh kontrak publik).
    - DILARANG memberikan HOW (solusi, kode implementasi, atau aturan task-specific).
    - Memuat minimal 9 field: obligation_id, authority, source_reference,
      obligation_kind, public_identity, inputs, outputs, observable_behavior, acceptance_evidence.
    """
    if not obligations:
        return ""

    lines = [
        "=== [AUTHORITATIVE ACCEPTANCE OBLIGATIONS] ===",
        "Authority: FROZEN_ORACLE (Immutable Acceptance Authority — Read-Only)",
        "Doktrin Arsitektur:",
        "1. Oracle menentukan WHAT (apa yang diuji dan wajib dipenuhi).",
        "2. Architect menentukan HOW (desain arsitektur, pemisahan modul, dan struktur kode).",
        "3. Seluruh obligasi publik berikut WAJIB terwakili dalam `interface_contracts` atau `data_models`",
        "   sebelum kontrak arsitektur diizinkan mencapai status FROZEN.",
        "",
        "Ledger Obligasi Penerimaan Orakel:",
    ]

    for idx, ob in enumerate(obligations, 1):
        lines.append(f"{idx}. Obligation ID: {ob.obligation_id}")
        lines.append(f"   Authority: {ob.authority}")
        lines.append(f"   Kind: {ob.obligation_kind}")
        lines.append(f"   Public Identity: {ob.public_identity}")
        if ob.inputs:
            lines.append(f"   Inputs: {ob.inputs}")
        if ob.outputs:
            lines.append(f"   Outputs: {ob.outputs}")
        lines.append(f"   Observable Behavior: {ob.observable_behavior}")
        lines.append(f"   Acceptance Evidence: {ob.acceptance_evidence}")
        lines.append(f"   Source Reference: {ob.source_reference}")
        lines.append("")

    lines.append("=== END [AUTHORITATIVE ACCEPTANCE OBLIGATIONS] ===")
    return "\n".join(lines)


# ===========================================================================
# 10. Canonical Read-Only Acceptance Usage Evidence Formatter (Treatment #1.2)
# ===========================================================================

def format_acceptance_usage_evidence(obligations: List[CanonicalObligation]) -> str:
    """
    Memformat observable acceptance usage & call shape evidence menjadi section read-only
    yang diinjeksikan ke konteks Architect (Treatment #1.2).
    """
    usage_obs = [ob for ob in obligations if ob.positional_arguments > 0 or ob.keyword_arguments or ob.caller]
    if not usage_obs:
        return ""

    lines = [
        "=== [ACCEPTANCE USAGE EVIDENCE] ===",
        "Authority: FROZEN_ORACLE (Immutable Observable Usage Evidence — Read-Only)",
        "Doktrin Kompatibilitas Pemanggilan (Treatment #1.2):",
        "1. Acceptance tests membuktikan ekspektasi pemanggilan nyata (observable invocation WHAT).",
        "2. Architect bebas menentukan HOW (classes, models, functions, internal decomposition).",
        "3. Rancangan HOW Anda (tipe parameter, konstruktor, argumen posisional/keyword) WAJIB kompatibel",
        "   dengan observable usage evidence di bawah ini.",
        "4. Bagian ini memuat BUKTI pemanggilan nyata, BUKAN instruksi implementasi (zero solver).",
        "",
        "Daftar Bukti Pemanggilan & Bentuk Argumen:",
    ]

    for idx, ob in enumerate(usage_obs, 1):
        lines.append(f"{idx}. Public Identity: {ob.public_identity}")
        lines.append(f"   Invocation Kind: {ob.invocation_kind}")
        lines.append(f"   Caller: {ob.caller or '(unspecified test)'}")
        lines.append(f"   Callee: {ob.callee or ob.public_identity}")
        lines.append(f"   Positional Arguments Count: {ob.positional_arguments}")
        lines.append(f"   Keyword Arguments: {ob.keyword_arguments}")
        lines.append(f"   Total Argument Count: {ob.argument_count}")
        lines.append(f"   Epistemic Status: {ob.epistemic_status}")
        lines.append(f"   Acceptance Evidence: {ob.acceptance_evidence}")
        lines.append(f"   Source Reference: {ob.source_reference}")
        lines.append("")

    lines.append("=== END [ACCEPTANCE USAGE EVIDENCE] ===")
    return "\n".join(lines)

