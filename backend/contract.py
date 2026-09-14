"""
Machine-Readable Contract Engine (P0-2) — v1.0.2
ReinDev Studio — Cross-Agent Semantic Contract & Deterministic Validation Gate

Modul ini mengimplementasikan kontrak machine-readable formal (JSON / Pydantic v2),
kanonikalisasi RFC 8785 (JCS) anti-circular hashing, 4 pilar gerbang validasi deterministik,
penguncian immutabilitas FROZEN, checkpoint verifikasi integritas, dan sanitasi feedback
Pilar 4 bebas kebocoran Oracle (Oracle-Independent Evaluation).

Dokumen Desain:
dokumentasi-pengembangan/architecture/machine_readable_contract_design.md (v1.0.2)
"""

from __future__ import annotations

import os
import re
import json
import copy
import hashlib
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple, Set

from pydantic import BaseModel, Field, field_validator, model_validator

try:
    from .canonical_obligation import (
        extract_canonical_oracle_obligations,
        check_obligation_coverage,
        CoverageStatus,
        CoverageMatrix,
        CanonicalObligation,
        ObligationKind,
        ObligationAuthority,
        ObligationProvenance,
    )
except ImportError:
    from canonical_obligation import (
        extract_canonical_oracle_obligations,
        check_obligation_coverage,
        CoverageStatus,
        CoverageMatrix,
        CanonicalObligation,
        ObligationKind,
        ObligationAuthority,
        ObligationProvenance,
    )



# ===========================================================================
# 1. Enums & Constants
# ===========================================================================

class ContractStatus(str, Enum):
    DRAFT = "DRAFT"
    ALIGNED = "ALIGNED"
    FROZEN = "FROZEN"
    EXECUTING = "EXECUTING"
    VALIDATED = "VALIDATED"
    REJECTED = "REJECTED"


class DomainType(str, Enum):
    REST_API = "REST_API"
    FLUTTER_WIDGET = "FLUTTER_WIDGET"
    CLI_TOOL = "CLI_TOOL"
    ALGORITHM = "ALGORITHM"
    DATA_PIPELINE = "DATA_PIPELINE"


class TargetLanguage(str, Enum):
    PYTHON = "python"
    DART = "dart"


class TestFramework(str, Enum):
    PYTEST = "pytest"
    FLUTTER_TEST = "flutter_test"
    DART_TEST = "dart_test"


class InterfaceType(str, Enum):
    HTTP_ENDPOINT = "HTTP_ENDPOINT"
    FUNCTION = "FUNCTION"
    CLASS_METHOD = "CLASS_METHOD"
    WIDGET = "WIDGET"


class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


class ParamLocation(str, Enum):
    PATH = "PATH"
    QUERY = "QUERY"
    BODY = "BODY"
    ARGUMENT = "ARGUMENT"
    PROP = "PROP"


class OutcomeType(str, Enum):
    VALUE_EQUALS = "VALUE_EQUALS"
    HTTP_STATUS = "HTTP_STATUS"
    EXCEPTION_THROWN = "EXCEPTION_THROWN"
    WIDGET_FOUND = "WIDGET_FOUND"


class AmbiguityResolution(str, Enum):
    DEFAULT_CONVENTION = "DEFAULT_CONVENTION"
    BLOCK_FOR_CLARIFICATION = "BLOCK_FOR_CLARIFICATION"


# ===========================================================================
# 2. Exceptions
# ===========================================================================

class ContractError(Exception):
    """Base exception for all contract-related errors."""
    pass


class ContractValidationError(ContractError):
    """Raised when a contract fails validation gate checks."""
    def __init__(self, message: str, errors: List[str], warnings: List[str] = None):
        super().__init__(message)
        self.errors = errors
        self.warnings = warnings or []


class ContractIntegrityError(ContractError):
    """Raised when canonical SHA-256 hash verification fails (stealth mutation or corruption)."""
    pass


class ContractImmutabilityError(ContractError):
    """Raised when attempting to modify a FROZEN contract without version amendment."""
    pass


# ===========================================================================
# 3. Canonical JSON Representation (RFC 8785 / JCS Principles)
# ===========================================================================

def canonicalize_json(obj: Any) -> str:
    """
    Menghasilkan representasi string JSON kanonikal deterministik sesuai prinsip RFC 8785:
    - Sorting keys secara leksikografis UTF-8
    - Tanpa spasi berlebih pada separator (',', ':')
    - Unicode karakter asli dipertahankan (ensure_ascii=False)
    - Representasi angka terstandar
    """
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str
    )


def compute_contract_canonical_hash(contract_dict: Dict[str, Any]) -> str:
    """
    Menghitung hash SHA-256 dari representasi JSON kanonikal kontrak.
    KRUSIAL (R1 - Anti-Circular):
    Atribut `provenance.contract_sha256` secara eksplisit dieksklusikan dari payload input hash!
    C_stripped = C minus {"provenance.contract_sha256"}
    """
    if not isinstance(contract_dict, dict):
        raise TypeError("contract_dict must be a dictionary")

    stripped = copy.deepcopy(contract_dict)
    if "provenance" in stripped and isinstance(stripped["provenance"], dict):
        stripped["provenance"].pop("contract_sha256", None)

    canonical_str = canonicalize_json(stripped)
    return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()


def verify_contract_integrity(contract_dict: Dict[str, Any]) -> bool:
    """
    Memverifikasi integritas kriptografis kontrak terhadap provenance.contract_sha256.
    Mengembalikan True jika cocok, melempar ContractIntegrityError jika mismatch atau kosong.
    """
    if not isinstance(contract_dict, dict):
        raise ContractIntegrityError("Contract is not a dictionary.")

    provenance = contract_dict.get("provenance", {})
    expected_hash = provenance.get("contract_sha256")
    if not expected_hash:
        raise ContractIntegrityError("Contract has no provenance.contract_sha256 seal.")

    computed_hash = compute_contract_canonical_hash(contract_dict)
    if computed_hash != expected_hash:
        raise ContractIntegrityError(
            f"Contract integrity violation (SHA-256 mismatch)!\n"
            f"Expected: {expected_hash}\n"
            f"Computed: {computed_hash}"
        )
    return True


# ===========================================================================
# 4. Pydantic Models for Contract Schema
# ===========================================================================

class Provenance(BaseModel):
    model_config = {"extra": "allow"}
    parent_intent_sha256: str = ""
    created_by: str = "System Architect"
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    contract_sha256: Optional[str] = None
    coverage_matrix: Optional[Dict[str, Any]] = None
    active_validation_errors: List[str] = Field(default_factory=list)
    validation_history: List[Dict[str, Any]] = Field(default_factory=list)
    contract_validation_errors: List[str] = Field(default_factory=list)


class TaskIntent(BaseModel):
    raw_intent: str
    domain: str  # REST_API, FLUTTER_WIDGET, CLI_TOOL, ALGORITHM
    goal_summary: str

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        valid_domains = {d.value for d in DomainType}
        if v not in valid_domains:
            raise ValueError(f"Domain must be one of {valid_domains}, got '{v}'")
        return v


class TargetEcosystem(BaseModel):
    language: str  # python, dart
    language_version: Optional[str] = None
    framework: str
    test_framework: str  # pytest, flutter_test, dart_test
    entrypoint: str

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        v_clean = v.lower().strip()
        if v_clean not in {"python", "dart"}:
            raise ValueError(f"Language must be 'python' or 'dart', got '{v}'")
        return v_clean

    @field_validator("test_framework")
    @classmethod
    def validate_test_framework(cls, v: str) -> str:
        valid_frameworks = {"pytest", "flutter_test", "dart_test"}
        v_clean = v.lower().strip()
        if v_clean not in valid_frameworks:
            raise ValueError(f"test_framework must be one of {valid_frameworks}, got '{v}'")
        return v_clean


class ModelField(BaseModel):
    field_name: str
    field_type: str
    is_required: bool = True
    constraints: Optional[str] = None
    description: Optional[str] = None

    @field_validator("field_type")
    @classmethod
    def validate_field_type(cls, v: str) -> str:
        if not v or v.lower() in ("any", "unknown"):
            raise ValueError(f"Field type cannot be empty or 'any', got '{v}'")
        return v


class DataModel(BaseModel):
    model_name: str
    target_file: str
    fields: List[ModelField] = Field(default_factory=list)


class InterfaceParameter(BaseModel):
    param_name: str
    param_type: str
    param_location: str  # PATH, QUERY, BODY, ARGUMENT, PROP
    is_required: bool = True

    @field_validator("param_location")
    @classmethod
    def validate_location(cls, v: str) -> str:
        valid_locs = {"PATH", "QUERY", "BODY", "ARGUMENT", "PROP"}
        if v.upper() not in valid_locs:
            raise ValueError(f"param_location must be one of {valid_locs}, got '{v}'")
        return v.upper()


class StatusCodeError(BaseModel):
    code: int
    condition: str


class ExpectedReturn(BaseModel):
    return_type: str
    status_code_success: Optional[int] = None
    status_code_errors: List[StatusCodeError] = Field(default_factory=list)


class InterfaceContract(BaseModel):
    model_config = {"extra": "allow"}
    interface_id: str
    interface_type: str  # HTTP_ENDPOINT, FUNCTION, CLASS_METHOD, WIDGET
    identifier: str
    route: Optional[str] = None
    http_method: Optional[str] = None  # GET, POST, PUT, DELETE, PATCH, None
    target_file: str
    parameters: List[InterfaceParameter] = Field(default_factory=list)
    expected_return: Optional[ExpectedReturn] = None

    @field_validator("interface_type")
    @classmethod
    def validate_interface_type(cls, v: str) -> str:
        valid_types = {"HTTP_ENDPOINT", "FUNCTION", "CLASS_METHOD", "WIDGET"}
        if v.upper() not in valid_types:
            raise ValueError(f"interface_type must be one of {valid_types}, got '{v}'")
        return v.upper()

    @field_validator("http_method")
    @classmethod
    def validate_http_method(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        valid_methods = {"GET", "POST", "PUT", "DELETE", "PATCH"}
        if v.upper() not in valid_methods:
            raise ValueError(f"http_method must be one of {valid_methods} or None, got '{v}'")
        return v.upper()


class FunctionalRequirement(BaseModel):
    req_id: str
    description: str
    acceptance_semantics: List[str] = Field(default_factory=list)


class ExpectedOutcome(BaseModel):
    outcome_type: str  # VALUE_EQUALS, HTTP_STATUS, EXCEPTION_THROWN, WIDGET_FOUND
    expected_value: Optional[str] = None
    expected_status: Optional[int] = None
    expected_exception: Optional[str] = None

    @field_validator("outcome_type")
    @classmethod
    def validate_outcome_type(cls, v: str) -> str:
        valid_outcomes = {"VALUE_EQUALS", "HTTP_STATUS", "EXCEPTION_THROWN", "WIDGET_FOUND"}
        if v.upper() not in valid_outcomes:
            raise ValueError(f"outcome_type must be one of {valid_outcomes}, got '{v}'")
        return v.upper()


class TestableAssertion(BaseModel):
    assertion_id: str
    linked_req_id: str
    linked_interface_id: Optional[str] = None
    test_scenario: str
    target_symbol: str
    input_fixture: Optional[str] = None
    expected_outcome: ExpectedOutcome


class ContractConstraints(BaseModel):
    max_files: int = 5
    allowed_directories: List[str] = Field(default_factory=list)
    forbidden_patterns: List[str] = Field(default_factory=list)


class UnresolvedAmbiguity(BaseModel):
    ambiguity_id: str
    description: str
    resolution_strategy: str = "DEFAULT_CONVENTION"  # DEFAULT_CONVENTION, BLOCK_FOR_CLARIFICATION

    @field_validator("resolution_strategy")
    @classmethod
    def validate_strategy(cls, v: str) -> str:
        valid_strategies = {"DEFAULT_CONVENTION", "BLOCK_FOR_CLARIFICATION"}
        if v not in valid_strategies:
            raise ValueError(f"resolution_strategy must be one of {valid_strategies}, got '{v}'")
        return v


class MachineReadableContract(BaseModel):
    model_config = {"extra": "allow"}
    contract_version: str = "1.0.1"
    contract_id: str
    status: str = "DRAFT"  # DRAFT, ALIGNED, FROZEN, EXECUTING, VALIDATED, REJECTED
    provenance: Provenance = Field(default_factory=Provenance)
    task_intent: Optional[TaskIntent] = None
    target_ecosystem: Optional[TargetEcosystem] = None
    data_models: List[DataModel] = Field(default_factory=list)
    interface_contracts: List[InterfaceContract] = Field(default_factory=list)
    functional_requirements: List[FunctionalRequirement] = Field(default_factory=list)
    testable_assertions: List[TestableAssertion] = Field(default_factory=list)
    constraints: ContractConstraints = Field(default_factory=ContractConstraints)
    unresolved_ambiguities: List[UnresolvedAmbiguity] = Field(default_factory=list)
    target_file: Optional[str] = None
    coverage_matrix: Optional[Dict[str, Any]] = None

    @field_validator("contract_version")
    @classmethod
    def validate_version_format(cls, v: str) -> str:
        if not re.match(r"^\d+\.\d+\.\d+$", v):
            raise ValueError(f"contract_version must match pattern '^\\d+\\.\\d+\\.\\d+$', got '{v}'")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        valid_statuses = {"DRAFT", "ALIGNED", "FROZEN", "EXECUTING", "VALIDATED", "REJECTED"}
        if v.upper() not in valid_statuses:
            raise ValueError(f"status must be one of {valid_statuses}, got '{v}'")
        return v.upper()

    def to_dict(self) -> Dict[str, Any]:
        """Konversi model Pydantic ke dictionary murni."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MachineReadableContract:
        """Instansiasi model dari dictionary data."""
        return cls.model_validate(data)

    def canonical_hash(self) -> str:
        """Menghitung hash kanonikal dari instance kontrak ini."""
        return compute_contract_canonical_hash(self.to_dict())


def is_non_ui_computational_task(contract_dict: Dict[str, Any], task_text: Optional[str] = None) -> bool:
    """
    Menentukan apakah suatu task tergolong kategori non-UI computational/module
    (API, CLI, Library, computational/module) yang mewajibkan interface_contracts non-kosong (P0-2.1).
    """
    if not isinstance(contract_dict, dict):
        return True

    # 1. Cek domain pada task_intent
    task_intent = contract_dict.get("task_intent", {})
    if isinstance(task_intent, dict):
        domain = task_intent.get("domain", "")
        if domain == "FLUTTER_WIDGET":
            return False
        if domain in ("REST_API", "CLI_TOOL", "ALGORITHM"):
            return True

    # 2. Cek target_ecosystem
    target_eco = contract_dict.get("target_ecosystem", {})
    if isinstance(target_eco, dict):
        framework = (target_eco.get("framework") or "").lower()
        language = (target_eco.get("language") or "").lower()
        if "flutter" in framework or language == "dart":
            return False

    # 3. Cek teks deskripsi task
    raw_text = ""
    if task_text:
        raw_text = task_text.lower()
    elif isinstance(task_intent, dict):
        raw_text = (str(task_intent.get("raw_intent", "")) + " " + str(task_intent.get("goal_summary", ""))).lower()

    if any(k in raw_text for k in ["api", "cli", "library", "computational", "module", "matrix", "matriks", "kalkulator", "math", "fastapi", "rest"]):
        return True

    return True


def extract_oracle_tested_symbols(frozen_oracle_path: str, target_lang: str = "") -> Set[str]:
    """
    Mengekstrak simbol, kelas, antarmuka, atau endpoint yang diuji oleh Frozen Oracle
    secara deterministik (Read-Only Observer) menggunakan Canonical Acceptance Adapter.
    """
    if not frozen_oracle_path:
        return set()
    try:
        obligations = extract_canonical_oracle_obligations(frozen_oracle_path=frozen_oracle_path)
        symbols = set()
        for ob in obligations:
            symbols.add(ob.public_identity)
            if ob.obligation_kind == ObligationKind.INTERACTION.value:
                clean = ob.public_identity.strip("/").replace("/", "_")
                if clean:
                    symbols.add(clean)
        return symbols
    except Exception:
        return set()



def check_pre_freeze_authority_compatibility(
    contract_obj: MachineReadableContract,
    frozen_oracle_path: str
) -> Tuple[bool, List[str], List[Dict[str, Any]]]:
    """
    PRE-FREEZE AUTHORITY COMPATIBILITY GATE (Part 2 - Architect Contract Binding v2).
    Memeriksa secara deterministik apakah seluruh kewajiban Acceptance Oracle
    (authoritative Oracle obligations) telah terbukti terwakili dalam Contract SEBELUM
    kontrak diizinkan bertransisi ke status FROZEN.

    DOKTRIN NON-NEGOTIABLE & KOREKSI:
    - 1. Oracle adalah IMMUTABLE ACCEPTANCE AUTHORITY (WHAT).
    - 2. Architect adalah DESIGN AUTHORITY (HOW).
    - 3. Provenance eksklusif: HANYA ORACLE_FACT yang memegang otoritas penerimaan.
    - 4. Koreksi 1: 100% Coverage membuktikan kompatibilitas struktural/semantik deterministik.
    - 5. Koreksi 2: Adapters murni PARSE -> NORMALIZE -> REPRESENT (Dilarang INVENT/SOLVE).
    - 6. Koreksi 3: Engine hanya memberikan DIAGNOSIS (WHAT), BUKAN instruksi HOW.
    - 7. Invariant: CANONICAL OBLIGATION INTEGRITY.
    """
    import os
    from pathlib import Path

    oracle_dir = Path(frozen_oracle_path)
    if not oracle_dir.exists() or not oracle_dir.is_dir():
        return True, [], []

    try:
        obligations = extract_canonical_oracle_obligations(frozen_oracle_path=str(oracle_dir))
    except Exception as e:
        return False, [f"Failed to extract canonical obligations from Oracle: {e}"], []

    if not obligations:
        return True, [], []

    cov_matrix = check_obligation_coverage(obligations, contract_obj)

    missing_obligations: List[Dict[str, Any]] = []
    error_messages: List[str] = []

    declared_symbols: Set[str] = set()
    for ifc in (contract_obj.interface_contracts or []):
        if hasattr(ifc, "identifier") and ifc.identifier:
            declared_symbols.add(ifc.identifier.strip())
        elif isinstance(ifc, dict) and ifc.get("identifier"):
            declared_symbols.add(str(ifc["identifier"]).strip())
    for dm in (contract_obj.data_models or []):
        if hasattr(dm, "model_name") and dm.model_name:
            declared_symbols.add(dm.model_name.strip())
        elif isinstance(dm, dict) and dm.get("model_name"):
            declared_symbols.add(str(dm["model_name"]).strip())

    for r in cov_matrix.results:
        if r.status != CoverageStatus.COVERED:
            ob = r.obligation
            st_val = r.status.value if isinstance(r.status, CoverageStatus) else str(r.status)

            if ob.obligation_kind == ObligationKind.INTERACTION.value:
                method = ob.inputs.get("http_method", "").upper()
                ob_desc = f"HTTP {method} {ob.public_identity}".strip()
            elif ob.obligation_kind == ObligationKind.DATA_MODEL.value:
                ob_desc = f"Data model / entity '{ob.public_identity}'"
            elif ob.obligation_kind == ObligationKind.OBSERVABLE_RUNTIME.value:
                ob_desc = f"Widget/Model '{ob.public_identity}'"
            else:
                ob_desc = f"Callable symbol '{ob.public_identity}'"

            cov_status_label = "MISSING" if r.status == CoverageStatus.MISSING else "INCOMPATIBLE"
            item = {
                "obligation": ob_desc,
                "coverage": cov_status_label,
                "result": "INCOMPATIBLE — CONTRACT MUST NOT FREEZE",
                "source_file": ob.source_reference,
                "obligation_id": ob.obligation_id,
                "reason": r.reason,
                "missing_aspects": r.missing_aspects,
            }
            missing_obligations.append(item)

            msg = (
                f"\nORACLE_OBLIGATION:\n{ob_desc}\n\n"
                f"CONTRACT_DECLARED_INTERFACES:\n{sorted(declared_symbols) if declared_symbols else '[]'}\n\n"
                f"CONTRACT_COVERAGE:\n{cov_status_label}\n\n"
                f"DIAGNOSIS:\n{r.reason}\n\n"
                f"RESULT:\nINCOMPATIBLE — CONTRACT MUST NOT FREEZE (File: {ob.source_reference})"
            )
            error_messages.append(msg)

    is_compatible = cov_matrix.is_fully_covered
    return is_compatible, error_messages, missing_obligations



def check_oracle_interface_consistency(
    interface_contracts: List[InterfaceContract],
    frozen_oracle_path: str
) -> Tuple[bool, Optional[str]]:
    """
    Backward-compatible wrapper di sekitar check_pre_freeze_authority_compatibility.
    """
    temp_contract = MachineReadableContract(
        contract_id="temp_compat_check",
        interface_contracts=interface_contracts
    )
    is_compat, errors, _ = check_pre_freeze_authority_compatibility(temp_contract, frozen_oracle_path)
    if not is_compat and errors:
        return False, errors[0]
    return True, None



def extract_proven_semantic_interfaces(
    interface_contracts: List[Any],
    frozen_oracle_path: str,
    target_lang: str = ""
) -> List[str]:
    """
    Mengekstrak nama antarmuka yang telah TERBUKTI konsisten secara deterministik
    terhadap Frozen Acceptance Oracle (PROVEN_SEMANTIC_INVARIANT).
    HANYA mengembalikan antarmuka jika:
    1. check_oracle_interface_consistency bernilai True (lulus konsistensi).
    2. Antarmuka benar-benar bersesuaian dengan simbol/endpoint yang diuji oleh Oracle.
    Draft atau rejected interface tanpa bukti keselarasan TIDAK AKAN PERNAH dikembalikan.
    """
    if not interface_contracts or not frozen_oracle_path:
        return []

    iface_objs: List[InterfaceContract] = []
    for idx, iface in enumerate(interface_contracts, 1):
        if isinstance(iface, InterfaceContract):
            iface_objs.append(iface)
        elif isinstance(iface, dict):
            try:
                d = dict(iface)
                if not d.get("interface_id"):
                    d["interface_id"] = f"IFC-{idx:02d}"
                if not d.get("interface_type"):
                    d["interface_type"] = "WIDGET" if "dart" in (target_lang or "").lower() else "FUNCTION"
                if not d.get("target_file"):
                    d["target_file"] = "lib/main.dart" if "dart" in (target_lang or "").lower() else "main.py"
                iface_objs.append(InterfaceContract(**d))
            except Exception:
                pass

    if not iface_objs:
        return []

    consistent, _ = check_oracle_interface_consistency(iface_objs, frozen_oracle_path)
    if not consistent:
        return []

    oracle_symbols = extract_oracle_tested_symbols(frozen_oracle_path, target_lang)
    if not oracle_symbols:
        return []

    proven: List[str] = []
    for ifc in iface_objs:
        ident = ifc.identifier.strip()
        if ifc.interface_type == "HTTP_ENDPOINT":
            base_ep = re.sub(r"/\{[^}]+\}", "", ident).rstrip("/")
            if base_ep in oracle_symbols or any(base_ep == os or os.startswith(base_ep) or base_ep.startswith(os) for os in oracle_symbols):
                proven.append(ident)
        else:
            parts = re.split(r"[.\(]", ident)
            clean_parts = [p.strip(" )\"'") for p in parts if p.strip(" )\"'")]
            if any(cp in oracle_symbols for cp in clean_parts):
                proven.append(ident)

    return sorted(list(set(proven)))


# ===========================================================================
# 5. Deterministic Contract Validation Gate (4 Pilar)
# ===========================================================================

def validate_contract_gate(
    contract_data: Any,
    frozen_oracle_path: Optional[str] = None,
    task_text: Optional[str] = None
) -> Tuple[bool, List[str], List[str]]:
    """
    Memvalidasi dokumen kontrak secara deterministik melalui empat pilar pengujian:
    Pilar 1: Schema Validity Check
    Pilar 2: Referential Integrity Check
    Pilar 3: Requirement Coverage Check & Mandatory Interface Contract (P0-2.1)
    Pilar 4: Assertion Verifiability, Internal Consistency Check & Oracle Consistency (P0-2.1)

    Mengembalikan: (is_valid: bool, errors: List[str], warnings: List[str])
    """
    errors: List[str] = []
    warnings: List[str] = []

    # -----------------------------------------------------------------------
    # PILAR 1: SCHEMA VALIDITY
    # -----------------------------------------------------------------------
    if not isinstance(contract_data, dict):
        if hasattr(contract_data, "to_dict"):
            contract_dict = contract_data.to_dict()
        else:
            return False, ["Pilar 1 (Skema): Dokumen kontrak bukan merupakan dictionary atau model yang valid."], []
    else:
        contract_dict = contract_data

    required_sections = [
        "contract_version", "contract_id", "status", "provenance",
        "task_intent", "target_ecosystem", "data_models",
        "interface_contracts", "functional_requirements",
        "testable_assertions", "constraints"
    ]
    for sec in required_sections:
        if sec not in contract_dict:
            errors.append(f"Pilar 1 (Skema): Bagian wajib '{sec}' hilang dari kontrak.")

    # Jika bagian utama hilang, stop early pada Pilar 1
    if errors:
        return False, errors, warnings

    # Validasi Pydantic model komprehensif
    try:
        contract_obj = MachineReadableContract.from_dict(contract_dict)
    except Exception as e:
        errors.append(f"Pilar 1 (Skema): Pelanggaran tipe/skema: {str(e)}")
        return False, errors, warnings

    # Periksa unresolved_ambiguities yang memblokir
    for amb in contract_obj.unresolved_ambiguities:
        if amb.resolution_strategy == "BLOCK_FOR_CLARIFICATION":
            errors.append(
                f"Pilar 1 (Skema): Terdapat ambiguitas belum terselesaikan yang memblokir: "
                f"'{amb.ambiguity_id}: {amb.description}'"
            )

    # -----------------------------------------------------------------------
    # PILAR 2: REFERENTIAL INTEGRITY
    # -----------------------------------------------------------------------
    # 1. Keunikan req_id
    req_ids: List[str] = []
    for r in contract_obj.functional_requirements:
        rid = r.req_id.strip()
        if not rid:
            errors.append("Pilar 2 (Integritas): req_id tidak boleh kosong.")
        elif rid in req_ids:
            errors.append(f"Pilar 2 (Integritas): Duplikasi req_id terdeteksi: '{rid}'.")
        req_ids.append(rid)
    set_req_ids = set(req_ids)

    # 2. Keunikan interface_id
    interface_ids: List[str] = []
    known_interfaces: Dict[str, InterfaceContract] = {}
    known_symbols: Set[str] = set()
    for iface in contract_obj.interface_contracts:
        ifid = iface.interface_id.strip()
        if not ifid:
            errors.append("Pilar 2 (Integritas): interface_id tidak boleh kosong.")
        elif ifid in interface_ids:
            errors.append(f"Pilar 2 (Integritas): Duplikasi interface_id terdeteksi: '{ifid}'.")
        interface_ids.append(ifid)
        known_interfaces[ifid] = iface
        if iface.identifier:
            known_symbols.add(iface.identifier.strip())

    # 3. Keunikan model_name
    model_names: List[str] = []
    for m in contract_obj.data_models:
        mname = m.model_name.strip()
        if not mname:
            errors.append("Pilar 2 (Integritas): model_name tidak boleh kosong.")
        elif mname in model_names:
            errors.append(f"Pilar 2 (Integritas): Duplikasi model_name terdeteksi: '{mname}'.")
        model_names.append(mname)
        known_symbols.add(mname)

    # 4. Keunikan assertion_id & Validitas Referensi
    assertion_ids: List[str] = []
    linked_req_seen: Set[str] = set()

    for a in contract_obj.testable_assertions:
        aid = a.assertion_id.strip()
        if not aid:
            errors.append("Pilar 2 (Integritas): assertion_id tidak boleh kosong.")
        elif aid in assertion_ids:
            errors.append(f"Pilar 2 (Integritas): Duplikasi assertion_id terdeteksi: '{aid}'.")
        assertion_ids.append(aid)

        # Cek linked_req_id (Anti-Dangling / Orphan Assertion)
        lrid = a.linked_req_id.strip()
        if not lrid:
            errors.append(f"Pilar 2 (Integritas): Assertion '{aid}' tidak memiliki linked_req_id (Orphan Assertion).")
        elif lrid not in set_req_ids:
            errors.append(
                f"Pilar 2 (Integritas): Assertion '{aid}' merujuk ke linked_req_id fiktif: '{lrid}'."
            )
        else:
            linked_req_seen.add(lrid)

        # Cek linked_interface_id jika dispesifikasikan
        liface = (a.linked_interface_id or "").strip()
        if liface and liface not in known_interfaces:
            errors.append(
                f"Pilar 2 (Integritas): Assertion '{aid}' merujuk ke linked_interface_id fiktif: '{liface}'."
            )

        # Cek target_symbol
        tsym = a.target_symbol.strip()
        if not tsym:
            errors.append(f"Pilar 2 (Integritas): Assertion '{aid}' tidak memiliki target_symbol.")
        elif tsym not in known_symbols:
            # Periksa apakah simbol ada di method/function atau field model
            # Jika tidak terdaftar sama sekali, ini referensial dangling
            errors.append(
                f"Pilar 2 (Integritas): target_symbol '{tsym}' pada assertion '{aid}' "
                f"tidak terdaftar pada interface_contracts atau data_models."
            )

    # -----------------------------------------------------------------------
    # PILAR 3: REQUIREMENT COVERAGE & ASSERTION VERIFIABILITY
    # -----------------------------------------------------------------------
    # Mandatory Interface Contract (Requirement 1 - P0-2.1)
    if is_non_ui_computational_task(contract_dict, task_text):
        if not contract_obj.interface_contracts or len(contract_obj.interface_contracts) == 0:
            structured_err = (
                "CONTRACT_VALIDATION_FAILED\n\n"
                "reason:\n"
                "interface_contracts is empty for a non-UI computational task.\n\n"
                "required_action:\n"
                "Define the externally observable interfaces that the Developer\n"
                "must implement and that the Frozen Oracle may invoke.\n\n"
                "required_fields:\n"
                "- module/function/class name\n"
                "- callable signature\n"
                "- expected input\n"
                "- expected output\n"
                "- public invocation mechanism"
            )
            errors.append(f"Pilar 3 (Mandatory Interface Contract): {structured_err}")

    # Setiap functional_requirement wajib memiliki minimal 1 assertion
    untested_reqs = set_req_ids - linked_req_seen
    if untested_reqs:
        errors.append(
            f"Pilar 3 (Cakupan): Persyaratan fungsional tanpa assertion pengujian: {sorted(untested_reqs)}."
        )

    for a in contract_obj.testable_assertions:
        outcome = a.expected_outcome
        if not outcome or not outcome.outcome_type:
            errors.append(
                f"Pilar 3 (Verifiability): Assertion '{a.assertion_id}' tidak memiliki outcome_type terukur."
            )

    # -----------------------------------------------------------------------
    # PILAR 4: INTERNAL CONSISTENCY (NON-PRESCRIPTIVE)
    # -----------------------------------------------------------------------
    set_known_models = set(model_names)
    primitive_types = {
        "dict", "list", "str", "int", "float", "bool", "none",
        "void", "widget", "dynamic", "any", "response", "json"
    }

    # 1. return_type consistency
    for iface in contract_obj.interface_contracts:
        if iface.expected_return and iface.expected_return.return_type:
            ret_type = iface.expected_return.return_type.strip()
            # Bersihkan wrapper generic seperti List[Product] atau Optional[Product]
            inner_type = re.sub(r"^(List|Optional|Set|Iterable|Future)<|^(List|Optional|Set|Iterable)\[", "", ret_type)
            inner_type = re.sub(r"[\]>]$", "", inner_type).strip()
            
            if inner_type.lower() in primitive_types or not inner_type:
                pass
            elif inner_type not in set_known_models:
                warnings.append(
                    f"Pilar 4 (Konsistensi): return_type '{ret_type}' pada interface '{iface.identifier}' "
                    f"tidak merujuk ke data_models yang dideklarasikan."
                )

    # 2. HTTP Endpoint vs Assertion Status Code Consistency
    for a in contract_obj.testable_assertions:
        if a.expected_outcome.outcome_type == "HTTP_STATUS":
            exp_status = a.expected_outcome.expected_status
            if exp_status is None:
                errors.append(
                    f"Pilar 4 (Konsistensi): Assertion '{a.assertion_id}' bertipe HTTP_STATUS "
                    f"namun expected_status bernilai None."
                )
            elif a.linked_interface_id and a.linked_interface_id in known_interfaces:
                iface = known_interfaces[a.linked_interface_id]
                if iface.expected_return:
                    success_code = iface.expected_return.status_code_success
                    error_codes = [e.code for e in iface.expected_return.status_code_errors]
                    all_declared = set()
                    if success_code is not None:
                        all_declared.add(success_code)
                    all_declared.update(error_codes)

                    if all_declared and exp_status not in all_declared:
                        errors.append(
                            f"Pilar 4 (Konsistensi): Assertion '{a.assertion_id}' mengharapkan HTTP status {exp_status}, "
                            f"tetapi interface '{iface.identifier}' hanya mendeklarasikan status {sorted(all_declared)}."
                        )

    # 3. Advisory Warnings for REST Conventions (NON-BLOCKING)
    for iface in contract_obj.interface_contracts:
        if iface.interface_type == "HTTP_ENDPOINT" and iface.http_method:
            method = iface.http_method.upper()
            if iface.expected_return and iface.expected_return.status_code_success:
                code = iface.expected_return.status_code_success
                if method == "POST" and code == 200:
                    warnings.append(
                        f"Pilar 4 (Advisory): Endpoint POST '{iface.identifier}' mengembalikan status 200 "
                        f"(Konvensi REST umum menyarankan 201 Created)."
                    )
                elif method == "GET" and code != 200:
                    warnings.append(
                        f"Pilar 4 (Advisory): Endpoint GET '{iface.identifier}' mengembalikan status {code} "
                        f"(Konvensi REST umum menyarankan 200 OK)."
                    )

    # 4. Pre-Freeze Authority Compatibility Gate (Part 2 - Architectural Hardening v1)
    if frozen_oracle_path:
        is_compat, err_msgs, missing_obs = check_pre_freeze_authority_compatibility(
            contract_obj,
            frozen_oracle_path
        )
        if not is_compat:
            structured_err = (
                "CONTRACT_VALIDATION_FAILED: PRE_FREEZE_AUTHORITY_INCOMPATIBLE\n\n"
                "reason:\n"
                "Architect interface contract is inconsistent with the frozen test interface. (does not cover authoritative obligations demanded by the Frozen Oracle)."
            )
            if err_msgs:
                structured_err += "\n\ndetails:\n" + "\n".join(err_msgs)
            errors.append(f"Pilar 4 (Oracle Consistency): {structured_err}")

    is_valid = (len(errors) == 0)
    return is_valid, errors, warnings


# ===========================================================================
# 6. Lifecycle Transitions & Seal Engine
# ===========================================================================

def seal_and_freeze_contract(
    contract_data: Any,
    frozen_oracle_path: Optional[str] = None,
    task_text: Optional[str] = None
) -> Tuple[bool, Dict[str, Any], List[str], List[str]]:
    """
    Mengeksekusi transisi kritis ALIGNED -> FROZEN:
    1. Memvalidasi kontrak melalui 4 pilar Validation Gate (termasuk P0-2.1).
    2. Jika lulus 100%:
       - Menghitung canonical hash SHA-256 (RFC 8785) dengan mengeluarkan provenance.contract_sha256.
       - Menyuntikkan hash ke provenance.contract_sha256.
       - Mengubah status kontrak menjadi FROZEN.
    3. Jika gagal:
       - Mengubah status kontrak menjadi REJECTED.
    
    Mengembalikan: (success: bool, contract_dict: dict, errors: List[str], warnings: List[str])
    """
    if isinstance(contract_data, dict):
        c_dict = copy.deepcopy(contract_data)
    elif hasattr(contract_data, "to_dict"):
        c_dict = contract_data.to_dict()
    else:
        return False, {}, ["Input kontrak bukan dictionary atau model valid."], []

    # Authoritative Target File Binding (Intervensi 1)
    domain = c_dict.get("task_intent", {}).get("domain", "")
    target_lang = c_dict.get("target_ecosystem", {}).get("language", "")
    is_dart = "dart" in target_lang.lower() or domain == "FLUTTER_WIDGET"

    if not c_dict.get("target_file"):
        for iface in c_dict.get("interface_contracts", []):
            if isinstance(iface, dict) and iface.get("target_file"):
                c_dict["target_file"] = iface["target_file"]
                break
        if not c_dict.get("target_file"):
            for m in c_dict.get("data_models", []):
                if isinstance(m, dict) and m.get("target_file"):
                    c_dict["target_file"] = m["target_file"]
                    break
        if not c_dict.get("target_file"):
            default_ep = "lib/main.dart" if is_dart else "main.py"
            c_dict["target_file"] = c_dict.get("target_ecosystem", {}).get("entrypoint", default_ep)

    auth_tf = c_dict["target_file"]
    for iface in c_dict.get("interface_contracts", []):
        if isinstance(iface, dict) and not iface.get("target_file"):
            iface["target_file"] = auth_tf
    for m in c_dict.get("data_models", []):
        if isinstance(m, dict) and not m.get("target_file"):
            m["target_file"] = auth_tf

    # Validasi 4 Pilar
    is_valid, errors, warnings = validate_contract_gate(
        c_dict,
        frozen_oracle_path=frozen_oracle_path,
        task_text=task_text
    )

    # Periksa HANYA error pra-segel aktif pada kandidat saat ini (misal: JSON parse failure atau model mapping error pada turn aktif)
    # JANGAN membaca atau mewariskan historical failure evidence dari turn sebelumnya.
    active_boundary_errors = c_dict.get("provenance", {}).get("active_validation_errors")
    if active_boundary_errors is None:
        # Fallback kompatibilitas jika caller langsung memasukkan contract_validation_errors pada turn saat ini
        active_boundary_errors = c_dict.get("provenance", {}).get("contract_validation_errors", [])

    if active_boundary_errors and isinstance(active_boundary_errors, list):
        for ae in active_boundary_errors:
            ae_str = str(ae)
            if ae_str not in errors:
                errors.append(ae_str)
        is_valid = False

    # Compute and attach canonical coverage matrix telemetry
    if frozen_oracle_path and os.path.exists(frozen_oracle_path):
        try:
            obs = extract_canonical_oracle_obligations(frozen_oracle_path=frozen_oracle_path)
            if obs:
                cov_mat = check_obligation_coverage(obs, c_dict)
                c_dict["coverage_matrix"] = cov_mat.to_dict()
                if "provenance" not in c_dict or not isinstance(c_dict["provenance"], dict):
                    c_dict["provenance"] = {}
                c_dict["provenance"]["coverage_matrix"] = cov_mat.to_telemetry_dict()
        except Exception:
            pass

    if not is_valid:
        c_dict["status"] = ContractStatus.REJECTED.value
        if "provenance" not in c_dict or not isinstance(c_dict["provenance"], dict):
            c_dict["provenance"] = {}
        c_dict["provenance"]["active_validation_errors"] = list(errors)
        c_dict["provenance"]["contract_validation_errors"] = list(errors)
        val_hist = list(c_dict["provenance"].get("validation_history") or [])
        val_hist.append({
            "timestamp": datetime.now().isoformat(),
            "phase": "CONTRACT_SEAL",
            "status": ContractStatus.REJECTED.value,
            "errors": list(errors)
        })
        c_dict["provenance"]["validation_history"] = val_hist
        return False, c_dict, errors, warnings

    # Transisi status ke FROZEN sebelum menghitung canonical hash agar segel mengunci state FROZEN
    c_dict["status"] = ContractStatus.FROZEN.value
    if "provenance" not in c_dict or not isinstance(c_dict["provenance"], dict):
        c_dict["provenance"] = {}
    c_dict["provenance"]["active_validation_errors"] = []
    c_dict["provenance"]["contract_validation_errors"] = []
    val_hist = list(c_dict["provenance"].get("validation_history") or [])
    val_hist.append({
        "timestamp": datetime.now().isoformat(),
        "phase": "CONTRACT_SEAL",
        "status": ContractStatus.FROZEN.value,
        "errors": []
    })
    c_dict["provenance"]["validation_history"] = val_hist

    # Hitung Canonical SHA-256 (Anti-Circular)
    c_hash = compute_contract_canonical_hash(c_dict)
    c_dict["provenance"]["contract_sha256"] = c_hash

    return True, c_dict, [], warnings


def verify_contract_checkpoint(
    contract_dict: Dict[str, Any],
    checkpoint_name: str,
    raise_on_error: bool = False
) -> Tuple[bool, Optional[str]]:
    """
    Memverifikasi integritas kontrak pada checkpoint tertentu:
    1. Status wajib FROZEN, EXECUTING, atau VALIDATED.
    2. Hash kanonikal SHA-256 wajib cocok 100% dengan provenance.contract_sha256.
    Mengembalikan (is_valid: bool, error_message: Optional[str]).
    Jika raise_on_error=True, melempar ContractIntegrityError jika verifikasi gagal.
    """
    if not isinstance(contract_dict, dict):
        msg = f"[{checkpoint_name}] Contract is not a dictionary."
        if raise_on_error:
            raise ContractIntegrityError(msg)
        return False, msg

    status = contract_dict.get("status", "")
    if status not in (ContractStatus.FROZEN.value, ContractStatus.EXECUTING.value, ContractStatus.VALIDATED.value):
        msg = f"[{checkpoint_name}] Invalid contract status: expected FROZEN/EXECUTING/VALIDATED, got '{status}'."
        if raise_on_error:
            raise ContractIntegrityError(msg)
        return False, msg

    try:
        verify_contract_integrity(contract_dict)
        return True, None
    except Exception as e:
        msg = f"[{checkpoint_name}] {str(e)}"
        if raise_on_error:
            raise ContractIntegrityError(msg)
        return False, msg


def enforce_contract_immutability(
    frozen_contract: Dict[str, Any],
    candidate_contract: Dict[str, Any]
) -> None:
    """
    Menegakkan immutabilitas kontrak tersegel (FROZEN):
    Jika kandidat mencoba mengubah isi kontrak tanpa version bump resmi, melempar ContractImmutabilityError.
    """
    if frozen_contract.get("status") != ContractStatus.FROZEN.value:
        return

    frozen_hash = frozen_contract.get("provenance", {}).get("contract_sha256")
    candidate_hash = compute_contract_canonical_hash(candidate_contract)

    if frozen_hash != candidate_hash:
        # Periksa apakah versi ditingkatkan (version amendment)
        old_v = frozen_contract.get("contract_version", "1.0.0")
        new_v = candidate_contract.get("contract_version", "1.0.0")
        if old_v == new_v:
            raise ContractImmutabilityError(
                f"FROZEN contract is strictly immutable! Attempted to modify version '{old_v}' "
                f"without bumping contract_version.\n"
                f"Original Hash: {frozen_hash}\n"
                f"Modified Hash: {candidate_hash}"
            )


# ===========================================================================
# 7. Helper: Factory / Builders for PM & Architect Agents
# ===========================================================================

def create_draft_contract(
    raw_intent: str,
    target_language: str,
    domain: str = "REST_API",
    goal_summary: str = "",
    contract_id: str = "",
    reqs: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Helper untuk PM Agent: Menyusun dokumen kontrak awal berstatus DRAFT.
    """
    lang = target_language.lower().strip()
    is_dart = "dart" in lang or "flutter" in lang
    test_framework = "flutter_test" if is_dart else "pytest"
    framework = "flutter" if is_dart else "fastapi"
    entrypoint = "lib/main.dart" if is_dart else "main.py"
    cid = contract_id or f"contract_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    intent_hash = hashlib.sha256(raw_intent.encode("utf-8")).hexdigest()

    default_reqs = reqs or [
        {
            "req_id": "REQ-01",
            "description": goal_summary or raw_intent,
            "acceptance_semantics": ["Sistem dapat dijalankan dan memenuhi fungsi dasar."]
        }
    ]

    c = MachineReadableContract(
        contract_version="1.0.1",
        contract_id=cid,
        status=ContractStatus.DRAFT.value,
        provenance=Provenance(
            parent_intent_sha256=intent_hash,
            created_by="Product Manager",
            created_at=datetime.now().isoformat()
        ),
        task_intent=TaskIntent(
            raw_intent=raw_intent,
            domain=domain,
            goal_summary=goal_summary or raw_intent[:100]
        ),
        target_ecosystem=TargetEcosystem(
            language="dart" if is_dart else "python",
            framework=framework,
            test_framework=test_framework,
            entrypoint=entrypoint
        ),
        data_models=[],
        interface_contracts=[],
        functional_requirements=[
            FunctionalRequirement(**r) for r in default_reqs
        ],
        testable_assertions=[],
        constraints=ContractConstraints(
            max_files=3,
            allowed_directories=["lib", "test"] if is_dart else ["."],
            forbidden_patterns=["app/api/", "app/schemas/", "submodules/"]
        ),
        unresolved_ambiguities=[]
    )
    return c.to_dict()


def complete_aligned_contract(
    draft_dict: Dict[str, Any],
    data_models: List[Dict[str, Any]],
    interface_contracts: List[Dict[str, Any]],
    testable_assertions: List[Dict[str, Any]],
    constraints: Optional[Dict[str, Any]] = None,
    ambiguities: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Helper untuk System Architect Agent: Melengkapi DRAFT contract menjadi ALIGNED contract.
    Prinsip: PERSIST HISTORY, RECOMPUTE ACTIVE VALIDITY.
    Mewariskan konteks desain relevan, tetapi mengarsipkan active errors lama ke validation_history
    dan menginisialisasi active_validation_errors kandidat baru menjadi [].
    """
    aligned = copy.deepcopy(draft_dict)
    aligned["status"] = ContractStatus.ALIGNED.value
    if "provenance" not in aligned or not isinstance(aligned["provenance"], dict):
        aligned["provenance"] = {}
    aligned["provenance"]["created_by"] = "System Architect"

    # Lifecycle management: arsipkan active errors lama jika belum tercatat di history
    prev_active = (
        aligned["provenance"].get("active_validation_errors")
        or aligned["provenance"].get("contract_validation_errors", [])
    )
    val_history = list(aligned["provenance"].get("validation_history") or [])
    if prev_active and isinstance(prev_active, list):
        val_history.append({
            "timestamp": datetime.now().isoformat(),
            "phase": "ARCHITECT_PREVIOUS_TURN",
            "status": draft_dict.get("status", "REJECTED"),
            "errors": list(prev_active)
        })

    aligned["provenance"]["validation_history"] = val_history
    # Reset active validation errors untuk kandidat baru (akan diuji oleh gate turn berjalan)
    aligned["provenance"]["active_validation_errors"] = []
    aligned["provenance"]["contract_validation_errors"] = []

    aligned["data_models"] = data_models
    aligned["interface_contracts"] = interface_contracts
    aligned["testable_assertions"] = testable_assertions
    if constraints:
        aligned["constraints"] = constraints
    if ambiguities is not None:
        aligned["unresolved_ambiguities"] = ambiguities

    return aligned


def extract_contract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Mengekstrak blok JSON kontrak dari luaran LLM secara aman:
    Mendukung blok ```json ... ``` atau === CONTRACT === ... === END CONTRACT ===
    atau blok JSON kurung kurawal terluar.
    """
    if not text:
        return None

    # 1. Cek penanda === CONTRACT === ... === END CONTRACT ===
    m_marker = re.search(r"===\s*CONTRACT\s*===\s*(\{.*?\})\s*===\s*END CONTRACT\s*===", text, re.DOTALL)
    if m_marker:
        try:
            return json.loads(m_marker.group(1))
        except Exception:
            pass

    # 2. Cek blok fenced code ```json ... ```
    m_fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m_fence:
        try:
            return json.loads(m_fence.group(1))
        except Exception:
            pass

    # 3. Cek kurung kurawal terluar
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        candidate = text[first_brace:last_brace + 1]
        try:
            return json.loads(candidate)
        except Exception:
            pass

    return None


# Prevent pytest from attempting to collect data classes as test suites
TestFramework.__test__ = False  # type: ignore[attr-defined]
TestableAssertion.__test__ = False  # type: ignore[attr-defined]
