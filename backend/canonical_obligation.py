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
        self.obligations: Dict[str, CanonicalObligation] = {}
        self.imported_from_main: Set[str] = set()
        self.proven_class_symbols: Set[str] = set()
        self.external_modules: Set[str] = {
            "pytest", "unittest", "mock", "os", "sys", "re", "json", "math",
            "time", "logging", "warnings", "subprocess", "shutil", "tempfile",
            "pathlib", "asyncio", "typing", "collections", "itertools", "functools"
        }

    def visit_FunctionDef(self, node: ast.FunctionDef):
        prev = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = prev

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        prev = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = prev

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
                        if ep_key not in self.obligations:
                            clean_id = norm_path.strip("/").replace("/", "_").replace("{", "").replace("}", "") or "root"
                            ob_id = f"OBL-HTTP-{method_name}-{clean_id}"
                            exp_status = self.func_status_map.get((method_name, norm_path))
                            outputs = {"expected_status": exp_status} if exp_status else {}
                            status_info = f" (expected status: {exp_status})" if exp_status else ""
                            num_pos = len(node.args)
                            kw_names = [kw.arg for kw in node.keywords if kw.arg]
                            self.obligations[ep_key] = CanonicalObligation(
                                obligation_id=ob_id,
                                authority=ObligationAuthority.FROZEN_ORACLE.value,
                                provenance=ObligationProvenance.ORACLE_FACT.value,
                                obligation_kind=ObligationKind.INTERACTION.value,
                                invocation_kind=InvocationKind.CALL.value,
                                caller=self.current_function or "",
                                callee=norm_path,
                                public_identity=norm_path,
                                inputs={"http_method": method_name, "raw_path": path_val},
                                outputs=outputs,
                                positional_arguments=num_pos,
                                keyword_arguments=kw_names,
                                argument_count=num_pos + len(kw_names),
                                argument_names=kw_names,
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

    final_results: List[ObligationCoverageResult] = []
    for r in results:
        ob_pos = r.obligation.positional_arguments or 0
        ob_kw = r.obligation.keyword_arguments or []
        if r.status == CoverageStatus.COVERED and (ob_pos > 0 or len(ob_kw) > 0):
            call_shape_status, call_shape_reason, _ = check_call_shape_compatibility(
                r.obligation,
                contract_dict,
                blueprint=blueprint
            )
            if call_shape_status in (CoverageStatus.INCOMPATIBLE, "INCOMPATIBLE"):
                r = ObligationCoverageResult(
                    obligation=r.obligation,
                    status=CoverageStatus.INCOMPATIBLE,
                    matched_declaration_id=r.matched_declaration_id,
                    reason=call_shape_reason,
                    missing_aspects=[f"Call shape compatible with {r.obligation.positional_arguments} pos / {r.obligation.keyword_arguments} kw"]
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

