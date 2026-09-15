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
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union


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


class CoverageStatus(str, Enum):
    COVERED = "COVERED"
    PARTIALLY_COVERED = "PARTIALLY_COVERED"
    MISSING = "MISSING"
    INCOMPATIBLE = "INCOMPATIBLE"
    UNDETERMINED = "UNDETERMINED"


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

    def to_dict(self) -> Dict[str, Any]:
        return {
            "obligation_id": self.obligation.obligation_id,
            "obligation_kind": self.obligation.obligation_kind,
            "public_identity": self.obligation.public_identity,
            "status": self.status.value if isinstance(self.status, CoverageStatus) else str(self.status),
            "matched_declaration_id": self.matched_declaration_id,
            "reason": self.reason,
            "missing_aspects": self.missing_aspects,
            "source_reference": self.obligation.source_reference,
        }


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
        obligations: List[CanonicalObligation] = []
        seen_identities: Set[str] = set()

        # Pre-scan functions to capture expected status codes per endpoint
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

        # 1. AST-based parsing
        try:
            tree = ast.parse(content, filename=file_name)
            for node in ast.walk(tree):
                # A. from main import X, Y (Callable or Model imports)
                if isinstance(node, ast.ImportFrom):
                    if node.module in ("main", "app"):
                        for alias in node.names:
                            sym = alias.name
                            if sym not in ("app", "main") and sym not in seen_identities:
                                seen_identities.add(sym)
                                is_model = sym[0].isupper() if sym else False
                                kind = ObligationKind.DATA_MODEL.value if is_model else ObligationKind.CALLABLE_INTERFACE.value
                                ob_id = f"OBL-{'MODEL' if is_model else 'CALL'}-{sym}"
                                obligations.append(CanonicalObligation(
                                    obligation_id=ob_id,
                                    authority=ObligationAuthority.FROZEN_ORACLE.value,
                                    provenance=ObligationProvenance.ORACLE_FACT.value,
                                    obligation_kind=kind,
                                    public_identity=sym,
                                    inputs={},
                                    outputs={},
                                    observable_behavior=f"Symbol '{sym}' directly imported and tested from authoritative module",
                                    acceptance_evidence=f"from {node.module} import {sym}",
                                    source_reference=f"{file_name}:{node.lineno}",
                                    metadata={"target_module": node.module, "symbol_type": "import"}
                                ))

                # B. client.<method>("/path", ...) (Interaction calls)
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute):
                        method_name = node.func.attr.upper()
                        if method_name in ("GET", "POST", "PUT", "DELETE", "PATCH"):
                            is_client_call = False
                            if isinstance(node.func.value, ast.Name) and "client" in node.func.value.id.lower():
                                is_client_call = True
                            elif isinstance(node.func.value, ast.Attribute) and "client" in node.func.value.attr.lower():
                                is_client_call = True

                            if is_client_call and node.args:
                                first_arg = node.args[0]
                                path_val = None
                                if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                                    path_val = first_arg.value
                                elif isinstance(first_arg, ast.JoinedStr):
                                    parts = []
                                    for p in first_arg.values:
                                        if isinstance(p, ast.Constant):
                                            parts.append(str(p.value))
                                        else:
                                            parts.append("{id}")
                                    path_val = "".join(parts)

                                if path_val and path_val.startswith("/"):
                                    norm_path = normalize_route_path(path_val)
                                    ep_key = f"HTTP:{method_name}:{norm_path}"
                                    if ep_key not in seen_identities:
                                        seen_identities.add(ep_key)
                                        clean_id = norm_path.strip("/").replace("/", "_").replace("{", "").replace("}", "") or "root"
                                        ob_id = f"OBL-HTTP-{method_name}-{clean_id}"
                                        exp_status = func_status_map.get((method_name, norm_path))
                                        outputs = {"expected_status": exp_status} if exp_status else {}
                                        status_info = f" (expected status: {exp_status})" if exp_status else ""
                                        obligations.append(CanonicalObligation(
                                            obligation_id=ob_id,
                                            authority=ObligationAuthority.FROZEN_ORACLE.value,
                                            provenance=ObligationProvenance.ORACLE_FACT.value,
                                            obligation_kind=ObligationKind.INTERACTION.value,
                                            public_identity=norm_path,
                                            inputs={"http_method": method_name, "raw_path": path_val},
                                            outputs=outputs,
                                            observable_behavior=f"HTTP endpoint '{norm_path}' accepting {method_name} method{status_info}",
                                            acceptance_evidence=f"client.{method_name.lower()}('{path_val}')",
                                            source_reference=f"{file_name}:{node.lineno}",
                                            metadata={"http_method": method_name, "path": norm_path}
                                        ))
        except Exception:
            pass

        # 2. Regex fallbacks for hasattr / getattr / client calls
        for sym in re.findall(r"hasattr\s*\(\s*main\s*,\s*['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]", content):
            if sym not in ("app", "main") and sym not in seen_identities:
                seen_identities.add(sym)
                is_model = sym[0].isupper()
                kind = ObligationKind.DATA_MODEL.value if is_model else ObligationKind.CALLABLE_INTERFACE.value
                ob_id = f"OBL-{'MODEL' if is_model else 'CALL'}-{sym}"
                obligations.append(CanonicalObligation(
                    obligation_id=ob_id,
                    authority=ObligationAuthority.FROZEN_ORACLE.value,
                    provenance=ObligationProvenance.ORACLE_FACT.value,
                    obligation_kind=kind,
                    public_identity=sym,
                    inputs={},
                    outputs={},
                    observable_behavior=f"Symbol '{sym}' verified via hasattr inspection",
                    acceptance_evidence=f"hasattr(main, '{sym}')",
                    source_reference=file_name,
                    metadata={"symbol_type": "hasattr"}
                ))

        for sym in re.findall(r"main\.([A-Za-z_][A-Za-z0-9_]*)", content):
            if sym not in ("app", "main") and sym not in seen_identities:
                seen_identities.add(sym)
                is_model = sym[0].isupper()
                kind = ObligationKind.DATA_MODEL.value if is_model else ObligationKind.CALLABLE_INTERFACE.value
                ob_id = f"OBL-{'MODEL' if is_model else 'CALL'}-{sym}"
                obligations.append(CanonicalObligation(
                    obligation_id=ob_id,
                    authority=ObligationAuthority.FROZEN_ORACLE.value,
                    provenance=ObligationProvenance.ORACLE_FACT.value,
                    obligation_kind=kind,
                    public_identity=sym,
                    inputs={},
                    outputs={},
                    observable_behavior=f"Symbol '{sym}' called directly on module 'main'",
                    acceptance_evidence=f"main.{sym}",
                    source_reference=file_name,
                    metadata={"symbol_type": "attribute_call"}
                ))

        for method, ep in re.findall(r"client\.(get|post|put|delete|patch)\(\s*f?[\"'](/[^\"'\s?#]+)[\"']", content, re.IGNORECASE):
            m_upper = method.upper()
            norm_path = normalize_route_path(ep)
            ep_key = f"HTTP:{m_upper}:{norm_path}"
            if ep_key not in seen_identities:
                seen_identities.add(ep_key)
                clean_id = norm_path.strip("/").replace("/", "_").replace("{", "").replace("}", "") or "root"
                ob_id = f"OBL-HTTP-{m_upper}-{clean_id}"
                exp_status = func_status_map.get((m_upper, norm_path))
                outputs = {"expected_status": exp_status} if exp_status else {}
                status_info = f" (expected status: {exp_status})" if exp_status else ""
                obligations.append(CanonicalObligation(
                    obligation_id=ob_id,
                    authority=ObligationAuthority.FROZEN_ORACLE.value,
                    provenance=ObligationProvenance.ORACLE_FACT.value,
                    obligation_kind=ObligationKind.INTERACTION.value,
                    public_identity=norm_path,
                    inputs={"http_method": m_upper, "raw_path": ep},
                    outputs=outputs,
                    observable_behavior=f"HTTP endpoint '{norm_path}' accepting {m_upper} method{status_info}",
                    acceptance_evidence=f"client.{method.lower()}('{ep}')",
                    source_reference=file_name,
                    metadata={"http_method": m_upper, "path": norm_path}
                ))

        return obligations


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

    def extract_obligations(self, file_name: str, content: str) -> List[CanonicalObligation]:
        obligations: List[CanonicalObligation] = []
        seen_identities: Set[str] = set()

        # 1. Widget obligations via find.byType(WidgetName)
        for sym in re.findall(r"find\.byType\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)", content):
            if sym not in self.DART_FRAMEWORK_TYPES and sym not in seen_identities:
                seen_identities.add(sym)
                ob_id = f"OBL-WIDGET-{sym}"
                obligations.append(CanonicalObligation(
                    obligation_id=ob_id,
                    authority=ObligationAuthority.FROZEN_ORACLE.value,
                    provenance=ObligationProvenance.ORACLE_FACT.value,
                    obligation_kind=ObligationKind.OBSERVABLE_RUNTIME.value,
                    public_identity=sym,
                    inputs={},
                    outputs={"return_type": "Widget"},
                    observable_behavior=f"UI Widget '{sym}' located and verified via widget tester find.byType",
                    acceptance_evidence=f"find.byType({sym})",
                    source_reference=file_name,
                    metadata={"target_type": "widget"}
                ))

        # 2. Widget instantiations in test body: e.g. home: CardMetric(...)
        for sym in re.findall(r"(?:body|child|home)\s*:\s*([A-Za-z_][A-Za-z0-9_]*)\s*\(", content):
            if sym not in self.DART_FRAMEWORK_TYPES and sym not in seen_identities:
                seen_identities.add(sym)
                ob_id = f"OBL-WIDGET-{sym}"
                obligations.append(CanonicalObligation(
                    obligation_id=ob_id,
                    authority=ObligationAuthority.FROZEN_ORACLE.value,
                    provenance=ObligationProvenance.ORACLE_FACT.value,
                    obligation_kind=ObligationKind.OBSERVABLE_RUNTIME.value,
                    public_identity=sym,
                    inputs={},
                    outputs={"return_type": "Widget"},
                    observable_behavior=f"UI Widget '{sym}' mounted in test tree",
                    acceptance_evidence=f"child/home: {sym}()",
                    source_reference=file_name,
                    metadata={"target_type": "widget"}
                ))

        # 3. Provider read / watch: e.g. container.read(metricDataProvider)
        for sym in re.findall(r"(?:container\.read|ref\.watch|ref\.read)\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)", content):
            if sym not in self.DART_FRAMEWORK_TYPES and sym not in seen_identities:
                seen_identities.add(sym)
                ob_id = f"OBL-PROVIDER-{sym}"
                obligations.append(CanonicalObligation(
                    obligation_id=ob_id,
                    authority=ObligationAuthority.FROZEN_ORACLE.value,
                    provenance=ObligationProvenance.ORACLE_FACT.value,
                    obligation_kind=ObligationKind.CALLABLE_INTERFACE.value,
                    public_identity=sym,
                    inputs={},
                    outputs={},
                    observable_behavior=f"State Provider '{sym}' read/watched by acceptance test",
                    acceptance_evidence=f"container.read({sym})",
                    source_reference=file_name,
                    metadata={"target_type": "provider"}
                ))

        # 4. Data Model instantiation: e.g. MetricData(title: 'Revenue', ...)
        for sym in re.findall(r"\b([A-Z][A-Za-z0-9_]*)\s*\(", content):
            if sym not in self.DART_FRAMEWORK_TYPES and sym not in seen_identities and not sym.startswith("Test"):
                seen_identities.add(sym)
                ob_id = f"OBL-MODEL-{sym}"
                obligations.append(CanonicalObligation(
                    obligation_id=ob_id,
                    authority=ObligationAuthority.FROZEN_ORACLE.value,
                    provenance=ObligationProvenance.ORACLE_FACT.value,
                    obligation_kind=ObligationKind.DATA_MODEL.value,
                    public_identity=sym,
                    inputs={},
                    outputs={},
                    observable_behavior=f"Data model / entity '{sym}' instantiated with constructor parameters in acceptance test",
                    acceptance_evidence=f"{sym}(...)",
                    source_reference=file_name,
                    metadata={"target_type": "model"}
                ))

        return obligations


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

def check_obligation_coverage(
    obligations: List[CanonicalObligation],
    contract: Any
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

    canonical_interfaces: List[CanonicalInterfaceDeclaration] = []
    for raw_ifc in declared_interfaces:
        c_ifc = normalize_interface_declaration(raw_ifc)
        if not c_ifc:
            continue
        canonical_interfaces.append(c_ifc)

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
            # 1. Exact match pada normalized route path (misal /products vs /products, /products/{id} vs /products/{id})
            matched_ifcs: List[CanonicalInterfaceDeclaration] = list(http_endpoints.get(req_path, []))

            # 2. Semantic match: jika obligation adalah parameterized endpoint (/users/{id}) dan interface dideklarasikan pada base route (/users) dengan PATH parameter
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

            if not matched_ifcs:
                clean_name = req_path.strip("/").replace("/", "_")
                potential_internal = [s for s in symbol_interfaces.keys() if clean_name in s.lower()]
                reason_extra = ""
                if potential_internal:
                    reason_extra = (
                        f" (Notice: Found internal function(s) {potential_internal}, but no public route/endpoint "
                        f"binding proof connects them to public endpoint '{req_path}')"
                    )

                res = ObligationCoverageResult(
                    obligation=ob,
                    status=CoverageStatus.MISSING,
                    reason=f"Public HTTP endpoint '{req_path}' has no declared interface coverage in contract{reason_extra}",
                    missing_aspects=[f"HTTP endpoint: {req_path}"]
                )
                results.append(res)
                missing_cnt += 1
                summary_reasons.append(f"MISSING: {ob.obligation_id} ({ob.public_identity})")

            else:
                # Path found, now evaluate method compatibility rigorously (NO WILDCARD)
                if req_method:
                    compatible_ifc: Optional[CanonicalInterfaceDeclaration] = None
                    declared_methods: List[str] = []
                    has_absent_method = False

                    for c_ifc in matched_ifcs:
                        m = c_ifc.canonical_method
                        if m:
                            declared_methods.append(m)
                            if m == req_method:
                                compatible_ifc = c_ifc
                                break
                        else:
                            has_absent_method = True

                    if compatible_ifc is not None:
                        matched_id = compatible_ifc.raw_declaration.get("interface_id") or compatible_ifc.identifier
                        res = ObligationCoverageResult(
                            obligation=ob,
                            status=CoverageStatus.COVERED,
                            matched_declaration_id=matched_id,
                            reason=f"HTTP endpoint '{req_path}' [{req_method}] has proven coverage by interface contract '{matched_id}'"
                        )
                        results.append(res)
                        covered_cnt += 1
                    elif declared_methods:
                        # Endpoint dideklarasikan, tetapi method eksplisit berbeda (INCOMPATIBLE / MISSING method)
                        # Contoh: Oracle demands GET, contract only declared ['POST', 'DELETE']
                        matched_id = matched_ifcs[0].raw_declaration.get("interface_id") or matched_ifcs[0].identifier
                        res = ObligationCoverageResult(
                            obligation=ob,
                            status=CoverageStatus.MISSING,
                            matched_declaration_id=matched_id,
                            reason=f"HTTP endpoint '{req_path}' declared with method(s) {declared_methods}, but expected method [{req_method}] is missing from contract",
                            missing_aspects=[f"HTTP method: {req_method}"]
                        )
                        results.append(res)
                        missing_cnt += 1
                        summary_reasons.append(f"MISSING: {ob.obligation_id} (Method [{req_method}] missing, found {declared_methods})")
                    else:
                        # Route cocok tetapi method absent pada deklarasi contract (bukan wildcard!)
                        matched_id = matched_ifcs[0].raw_declaration.get("interface_id") or matched_ifcs[0].identifier
                        res = ObligationCoverageResult(
                            obligation=ob,
                            status=CoverageStatus.UNDETERMINED,
                            matched_declaration_id=matched_id,
                            reason=f"HTTP endpoint '{req_path}' declared in contract without explicit HTTP method (cannot prove compatibility with expected method [{req_method}])",
                            missing_aspects=[f"Explicit HTTP method [{req_method}] on {req_path}"]
                        )
                        results.append(res)
                        undetermined_cnt += 1
                        summary_reasons.append(f"UNDETERMINED: {ob.obligation_id} (HTTP method absent on contract declaration)")
                else:
                    # Obligation tidak mensyaratkan method spesifik (hanya eksistensi route/endpoint)
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
            if model_name in data_models_map:
                res = ObligationCoverageResult(
                    obligation=ob,
                    status=CoverageStatus.COVERED,
                    matched_declaration_id=data_models_map[model_name].get("model_name"),
                    reason=f"Data model '{model_name}' covered in contract data_models"
                )
                results.append(res)
                covered_cnt += 1
            elif model_name in symbol_interfaces:
                c_ifc = symbol_interfaces[model_name][0]
                matched_id = c_ifc.raw_declaration.get("interface_id") or c_ifc.identifier
                res = ObligationCoverageResult(
                    obligation=ob,
                    status=CoverageStatus.COVERED,
                    matched_declaration_id=matched_id,
                    reason=f"Data model/class '{model_name}' covered in contract interface_contracts"
                )
                results.append(res)
                covered_cnt += 1
            else:
                res = ObligationCoverageResult(
                    obligation=ob,
                    status=CoverageStatus.MISSING,
                    reason=f"Data model/class '{model_name}' is not declared in contract data_models or interface_contracts",
                    missing_aspects=[f"Data model: {model_name}"]
                )
                results.append(res)
                missing_cnt += 1
                summary_reasons.append(f"MISSING: {ob.obligation_id} ({model_name})")

        # C. CALLABLE INTERFACE (e.g. add_matrices, metricDataProvider)
        elif ob.obligation_kind == ObligationKind.CALLABLE_INTERFACE.value:
            symbol_name = ob.public_identity
            if symbol_name in symbol_interfaces:
                c_ifc = symbol_interfaces[symbol_name][0]
                matched_id = c_ifc.raw_declaration.get("interface_id") or c_ifc.identifier
                res = ObligationCoverageResult(
                    obligation=ob,
                    status=CoverageStatus.COVERED,
                    matched_declaration_id=matched_id,
                    reason=f"Callable interface '{symbol_name}' covered by interface contract {matched_id}"
                )
                results.append(res)
                covered_cnt += 1
            elif symbol_name in data_models_map:
                res = ObligationCoverageResult(
                    obligation=ob,
                    status=CoverageStatus.COVERED,
                    matched_declaration_id=data_models_map[symbol_name].get("model_name"),
                    reason=f"Callable/constructible symbol '{symbol_name}' covered by data model"
                )
                results.append(res)
                covered_cnt += 1
            else:
                res = ObligationCoverageResult(
                    obligation=ob,
                    status=CoverageStatus.MISSING,
                    reason=f"Callable symbol/interface '{symbol_name}' is missing from contract interface_contracts",
                    missing_aspects=[f"Callable interface: {symbol_name}"]
                )
                results.append(res)
                missing_cnt += 1
                summary_reasons.append(f"MISSING: {ob.obligation_id} ({symbol_name})")

        # D. OBSERVABLE RUNTIME (e.g. UI Widget CardMetric)
        elif ob.obligation_kind == ObligationKind.OBSERVABLE_RUNTIME.value:
            widget_name = ob.public_identity
            if widget_name in symbol_interfaces:
                c_ifc = symbol_interfaces[widget_name][0]
                matched_id = c_ifc.raw_declaration.get("interface_id") or c_ifc.identifier
                res = ObligationCoverageResult(
                    obligation=ob,
                    status=CoverageStatus.COVERED,
                    matched_declaration_id=matched_id,
                    reason=f"Observable runtime widget '{widget_name}' covered by interface contract {matched_id}"
                )
                results.append(res)
                covered_cnt += 1
            elif widget_name in data_models_map:
                res = ObligationCoverageResult(
                    obligation=ob,
                    status=CoverageStatus.COVERED,
                    matched_declaration_id=data_models_map[widget_name].get("model_name"),
                    reason=f"Observable component '{widget_name}' declared in contract models"
                )
                results.append(res)
                covered_cnt += 1
            else:
                res = ObligationCoverageResult(
                    obligation=ob,
                    status=CoverageStatus.MISSING,
                    reason=f"Observable runtime component/widget '{widget_name}' is not declared in interface_contracts",
                    missing_aspects=[f"Component/Widget: {widget_name}"]
                )
                results.append(res)
                missing_cnt += 1
                summary_reasons.append(f"MISSING: {ob.obligation_id} ({widget_name})")

        # E. DEFAULT / BEHAVIORAL
        else:
            identity = ob.public_identity
            if identity in symbol_interfaces or identity in data_models_map:
                res = ObligationCoverageResult(
                    obligation=ob,
                    status=CoverageStatus.COVERED,
                    reason=f"Obligation '{identity}' covered by matching public contract symbol"
                )
                results.append(res)
                covered_cnt += 1
            else:
                res = ObligationCoverageResult(
                    obligation=ob,
                    status=CoverageStatus.MISSING,
                    reason=f"Obligation '{identity}' has no corresponding public interface contract",
                    missing_aspects=[f"Identity: {identity}"]
                )
                results.append(res)
                missing_cnt += 1
                summary_reasons.append(f"MISSING: {ob.obligation_id} ({identity})")

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
        results=results,
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

