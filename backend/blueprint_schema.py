# -*- coding: utf-8 -*-
"""
Architectural Blueprint Schema (Strict JSON Representation)
ReinDev Studio — v2.2 (Architectural Modernization)

Mendefinisikan skema Pydantic v2 formal untuk representasi cetak biru arsitektur
berbasis JSON terstruktur (File-Centric Scaffold), mengeliminasi ambiguitas
dan fragmentasi blok kode pada Markdown bebas.
"""

from __future__ import annotations

import re
import json
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple, Union
from pydantic import BaseModel, Field, field_validator, model_validator


class BlueprintErrorClass(str, Enum):
    """Kategori klasifikasi kesalahan blueprint kanonikal (Treatment #1.8.3)."""
    REPRESENTATION_ERROR = "REPRESENTATION_ERROR"
    SEMANTIC_ERROR = "SEMANTIC_ERROR"
    STRUCTURAL_ERROR = "STRUCTURAL_ERROR"
    UNRECOVERABLE_REPRESENTATION_ERROR = "UNRECOVERABLE_REPRESENTATION_ERROR"


class BlueprintFileModule(BaseModel):
    """Representasi modul/berkas tunggal dalam cetak biru arsitektur."""
    model_config = {"extra": "allow"}

    file_path: str = Field(..., min_length=1, description="Path relatif berkas target (misal: main.py atau lib/card_metric.dart)")
    module_role: str = Field(default="Authoritative Single Module", min_length=1, description="Peran modul")
    imports: List[str] = Field(default_factory=list, description="Daftar statement import yang dibutuhkan modul")
    code_scaffold: str = Field(..., min_length=1, description="Scaffold kode lengkap dan terpadu untuk berkas ini (WAJIB ADA)")
    description: Optional[str] = Field(None, description="Deskripsi singkat tanggung jawab modul")

    @model_validator(mode="before")
    @classmethod
    def normalize_module(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        d = dict(data)

        # 1. Normalisasi file_path & alias (path, filename, file) dengan conflict detection
        has_canon_fp = "file_path" in d and d["file_path"] is not None
        canon_fp = str(d["file_path"]).strip().replace("\\", "/") if has_canon_fp else None

        for alias in ["path", "filename", "file"]:
            if alias in d and d[alias] is not None:
                alias_val = str(d[alias]).strip().replace("\\", "/")
                if has_canon_fp and canon_fp and alias_val and canon_fp != alias_val:
                    raise ValueError(f"REPRESENTATION CONFLICT: file_path='{canon_fp}' != {alias}='{alias_val}'")
                if not has_canon_fp and alias_val:
                    d["file_path"] = alias_val
                    has_canon_fp = True
                    canon_fp = alias_val

        # 2. Normalisasi module_role & alias (role) dengan conflict detection
        if "role" in d and d["role"] is not None:
            a_role = str(d["role"]).strip()
            if "module_role" in d and d["module_role"] is not None:
                c_role = str(d["module_role"]).strip()
                if c_role and a_role and c_role != a_role:
                    raise ValueError(f"REPRESENTATION CONFLICT: module_role='{c_role}' != role='{a_role}'")
            else:
                d["module_role"] = a_role

        # 3. Normalisasi imports & alias (import_statements, dependencies)
        for alias in ["import_statements", "dependencies"]:
            if "imports" not in d and alias in d and d[alias] is not None:
                d["imports"] = d[alias]
                break
        if "imports" in d:
            imp_val = d["imports"]
            if isinstance(imp_val, str):
                d["imports"] = [line.strip() for line in imp_val.splitlines() if line.strip()]
            elif isinstance(imp_val, list):
                d["imports"] = [str(x).strip() for x in imp_val if str(x).strip()]

        # 4. Normalisasi description & alias (desc, summary)
        for alias in ["desc", "summary"]:
            if "description" not in d and alias in d and d[alias] is not None:
                d["description"] = str(d[alias]).strip()
                break

        # 5. Normalisasi code_scaffold & alias (scaffold, code, content, source_code)
        has_canon_cs = "code_scaffold" in d and d["code_scaffold"] is not None
        canon_cs = d["code_scaffold"] if has_canon_cs else None

        for alias in ["scaffold", "code", "content", "source_code"]:
            if alias in d and d[alias] is not None:
                alias_val = d[alias]
                if has_canon_cs:
                    if isinstance(canon_cs, str) and isinstance(alias_val, str):
                        if canon_cs.strip() != alias_val.strip():
                            raise ValueError(f"REPRESENTATION CONFLICT: code_scaffold != {alias}")
                else:
                    d["code_scaffold"] = alias_val
                    has_canon_cs = True
                    canon_cs = alias_val

        # 6. Shape Coercion untuk code_scaffold:
        # A. str -> diterima apa adanya
        # B. list[str] -> deterministic lossless joining via "\n".join(v)
        # C. dict -> hanya jika single-key explicit code wrapper; arbitrary dict -> REJECT
        raw_cs = d.get("code_scaffold")
        if raw_cs is not None:
            if isinstance(raw_cs, str):
                d["code_scaffold"] = raw_cs
            elif isinstance(raw_cs, list):
                d["code_scaffold"] = "\n".join(str(item) for item in raw_cs)
            elif isinstance(raw_cs, dict):
                wrapper_keys = [k for k in ["code_scaffold", "scaffold", "code", "content", "source_code"] if k in raw_cs and raw_cs[k]]
                if len(raw_cs) == 1 and wrapper_keys:
                    inner_val = raw_cs[wrapper_keys[0]]
                    if isinstance(inner_val, str):
                        d["code_scaffold"] = inner_val
                    elif isinstance(inner_val, list):
                        d["code_scaffold"] = "\n".join(str(x) for x in inner_val)
                    else:
                        raise ValueError(
                            "UNRECOVERABLE_REPRESENTATION_ERROR: code_scaffold wrapper contains non-string content"
                        )
                else:
                    raise ValueError(
                        f"UNRECOVERABLE_REPRESENTATION_ERROR: Arbitrary dict in code_scaffold with keys {sorted(raw_cs.keys())} "
                        "cannot be normalized without semantic guessing. code_scaffold must be a string or list of lines."
                    )
            else:
                raise ValueError(
                    f"UNRECOVERABLE_REPRESENTATION_ERROR: Unsupported code_scaffold type: {type(raw_cs).__name__}"
                )

        return d

    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls, v: str) -> str:
        cleaned = v.strip().replace("\\", "/")
        if not cleaned:
            raise ValueError("file_path tidak boleh kosong")
        return cleaned

    @field_validator("code_scaffold")
    @classmethod
    def validate_code_scaffold(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("code_scaffold wajib diisi dan tidak boleh hanya berupa whitespace")
        return v


class BlueprintInterfaceContract(BaseModel):
    """Spesifikasi kontrak antarmuka publik."""
    model_config = {"extra": "allow"}

    identifier: str = Field(..., min_length=1, description="Nama fungsi/endpoint/metode")
    route: Optional[str] = Field(None, description="Route path (misal: /products)")
    method: Optional[str] = Field(None, description="HTTP Method (misal: GET, POST)")
    target_file: str = Field(..., min_length=1, description="Berkas tempat kontrak ini didefinisikan")

    @model_validator(mode="before")
    @classmethod
    def normalize_contract(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        d = dict(data)

        # 1. identifier & alias (name, function_name, endpoint_name, symbol)
        has_canon_id = "identifier" in d and d["identifier"] is not None
        canon_id = str(d["identifier"]).strip() if has_canon_id else None

        for alias in ["name", "function_name", "endpoint_name", "symbol"]:
            if alias in d and d[alias] is not None:
                a_val = str(d[alias]).strip()
                if has_canon_id and canon_id and a_val and canon_id != a_val:
                    raise ValueError(f"REPRESENTATION CONFLICT: identifier='{canon_id}' != {alias}='{a_val}'")
                if not has_canon_id and a_val:
                    d["identifier"] = a_val
                    has_canon_id = True
                    canon_id = a_val

        # 2. route & alias (path, endpoint)
        has_canon_route = "route" in d and d["route"] is not None
        canon_route = str(d["route"]).strip() if has_canon_route else None

        for alias in ["path", "endpoint"]:
            if alias in d and d[alias] is not None:
                a_route = str(d[alias]).strip()
                if has_canon_route and canon_route and a_route and canon_route != a_route:
                    raise ValueError(f"REPRESENTATION CONFLICT: route='{canon_route}' != {alias}='{a_route}'")
                if not has_canon_route and a_route:
                    d["route"] = a_route
                    has_canon_route = True
                    canon_route = a_route

        # 3. method & alias (http_method)
        has_canon_method = "method" in d and d["method"] is not None
        canon_method = str(d["method"]).strip().upper() if has_canon_method else None

        for alias in ["http_method"]:
            if alias in d and d[alias] is not None:
                a_method = str(d[alias]).strip().upper()
                if has_canon_method and canon_method and a_method and canon_method != a_method:
                    raise ValueError(f"REPRESENTATION CONFLICT: method='{canon_method}' != {alias}='{a_method}'")
                if not has_canon_method and a_method:
                    d["method"] = a_method
                    has_canon_method = True
                    canon_method = a_method

        # 4. target_file & alias (file, target)
        has_canon_tf = "target_file" in d and d["target_file"] is not None
        canon_tf = str(d["target_file"]).strip().replace("\\", "/") if has_canon_tf else None

        for alias in ["file", "target"]:
            if alias in d and d[alias] is not None:
                a_tf = str(d[alias]).strip().replace("\\", "/")
                if has_canon_tf and canon_tf and a_tf and canon_tf != a_tf:
                    raise ValueError(f"REPRESENTATION CONFLICT: target_file='{canon_tf}' != {alias}='{a_tf}'")
                if not has_canon_tf and a_tf:
                    d["target_file"] = a_tf
                    has_canon_tf = True
                    canon_tf = a_tf

        return d

    @field_validator("target_file")
    @classmethod
    def validate_target_file(cls, v: str) -> str:
        cleaned = v.strip().replace("\\", "/")
        if not cleaned:
            raise ValueError("target_file pada kontrak antarmuka tidak boleh kosong")
        return cleaned


class BlueprintModelField(BaseModel):
    """Spesifikasi atribut/field entitas data model dalam blueprint."""
    model_config = {"extra": "allow"}

    field_name: Optional[str] = Field(None, description="Nama atribut kanonikal")
    name: Optional[str] = Field(None, description="Alias nama atribut dalam blueprint")
    field_type: Optional[str] = Field(None, description="Tipe data kanonikal")
    type: Optional[str] = Field(None, description="Alias tipe data dalam blueprint")
    is_required: bool = Field(default=True, description="Apakah atribut wajib ada")
    constraints: Optional[Union[str, Dict[str, Any], List[Any]]] = Field(default=None, description="Batasan nilai atribut")
    description: Optional[str] = Field(default=None, description="Deskripsi semantik atribut")

    @model_validator(mode="before")
    @classmethod
    def normalize_field(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        d = dict(data)
        has_cfn = "field_name" in d and d["field_name"] is not None
        cfn = str(d["field_name"]).strip() if has_cfn else None
        if "name" in d and d["name"] is not None:
            afn = str(d["name"]).strip()
            if has_cfn and cfn and afn and cfn != afn:
                raise ValueError(f"REPRESENTATION CONFLICT: field_name='{cfn}' != name='{afn}'")
            if not has_cfn and afn:
                d["field_name"] = afn
                has_cfn = True

        has_cft = "field_type" in d and d["field_type"] is not None
        cft = str(d["field_type"]).strip() if has_cft else None
        if "type" in d and d["type"] is not None:
            aft = str(d["type"]).strip()
            if has_cft and cft and aft and cft != aft:
                raise ValueError(f"REPRESENTATION CONFLICT: field_type='{cft}' != type='{aft}'")
            if not has_cft and aft:
                d["field_type"] = aft

        if "is_required" not in d and "required" in d:
            d["is_required"] = bool(d["required"])

        return d


class BlueprintDataModel(BaseModel):
    """Spesifikasi entitas data model dalam blueprint arsitektur."""
    model_config = {"extra": "allow"}

    model_name: str = Field(..., min_length=1, description="Nama kelas/entitas data model")
    target_file: str = Field(default="main.py", description="Berkas target tempat model didefinisikan")
    fields: List[Union[BlueprintModelField, Dict[str, Any]]] = Field(
        default_factory=list,
        description="Daftar field entitas data model"
    )
    construction_shape: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Bentuk konstruksi atau instansiasi (opsional)"
    )

    @model_validator(mode="before")
    @classmethod
    def normalize_data_model(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        d = dict(data)
        has_canon = "model_name" in d and d["model_name"] is not None
        canon = str(d["model_name"]).strip() if has_canon else None
        for alias in ["name", "class_name", "entity_name"]:
            if alias in d and d[alias] is not None:
                a_val = str(d[alias]).strip()
                if has_canon and canon and a_val and canon != a_val:
                    raise ValueError(f"REPRESENTATION CONFLICT: model_name='{canon}' != {alias}='{a_val}'")
                if not has_canon and a_val:
                    d["model_name"] = a_val
                    has_canon = True
                    canon = a_val
        for alias in ["file", "target"]:
            if "target_file" not in d and alias in d and d[alias] is not None:
                d["target_file"] = str(d[alias]).strip().replace("\\", "/")
                break
        for alias in ["attributes", "properties"]:
            if "fields" not in d and alias in d and d[alias] is not None:
                d["fields"] = d[alias]
                break

        # Normalisasi dan validasi deterministik setiap field
        raw_flds = d.get("fields")
        if isinstance(raw_flds, list):
            norm_flds = []
            for f in raw_flds:
                if isinstance(f, dict):
                    norm_flds.append(BlueprintModelField.model_validate(f))
                else:
                    norm_flds.append(f)
            d["fields"] = norm_flds

        return d


class ArchitecturalBlueprint(BaseModel):
    """Skema kanonikal formal untuk cetak biru arsitektur perangkat lunak ReinDev Studio."""
    schema_version: str = Field(default="1.0.0", description="Versi skema blueprint")
    task_id: str = Field(default="default_task", min_length=1, description="ID tugas")
    target_language: str = Field(default="python", min_length=1, description="Bahasa target: python atau dart")
    authoritative_target_file: str = Field(..., min_length=1, description="File target implementasi utama")
    file_tree: List[str] = Field(default_factory=lambda: ["main.py"], min_length=1, description="Peta berkas proyek")
    architecture_summary: str = Field(default="Architectural blueprint scaffold", min_length=1, description="Ringkasan arsitektur sistem")
    files: Dict[str, BlueprintFileModule] = Field(
        ...,
        min_length=1,
        description="Peta file_path ke modul kode scaffold"
    )
    interface_contracts: List[BlueprintInterfaceContract] = Field(
        default_factory=list,
        description="Kontrak antarmuka publik yang didefinisikan"
    )
    data_models: List[Union[BlueprintDataModel, Dict[str, Any]]] = Field(
        default_factory=list,
        description="Spesifikasi data models"
    )

    @field_validator("authoritative_target_file")
    @classmethod
    def validate_auth_file(cls, v: str) -> str:
        cleaned = v.strip().replace("\\", "/")
        if not cleaned:
            raise ValueError("authoritative_target_file tidak boleh kosong")
        return cleaned

    @field_validator("file_tree")
    @classmethod
    def validate_file_tree_elements(cls, v: List[str]) -> List[str]:
        cleaned = [f.strip().replace("\\", "/") for f in v if f and f.strip()]
        if not cleaned:
            raise ValueError("file_tree tidak boleh kosong")
        return cleaned

    @model_validator(mode="before")
    @classmethod
    def normalize_input(cls, data: Any) -> Any:
        if isinstance(data, dict):
            d = dict(data)

            # Top-level aliases with conflict detection:
            # 1. authoritative_target_file (target_file, primary_file, main_file)
            has_canon_atf = "authoritative_target_file" in d and d["authoritative_target_file"] is not None
            canon_atf = str(d["authoritative_target_file"]).strip().replace("\\", "/") if has_canon_atf else None
            for alias in ["target_file", "primary_file", "main_file"]:
                if alias in d and d[alias] is not None:
                    a_val = str(d[alias]).strip().replace("\\", "/")
                    if has_canon_atf and canon_atf and a_val and canon_atf != a_val:
                        raise ValueError(f"REPRESENTATION CONFLICT: authoritative_target_file='{canon_atf}' != {alias}='{a_val}'")
                    if not has_canon_atf and a_val:
                        d["authoritative_target_file"] = a_val
                        has_canon_atf = True
                        canon_atf = a_val

            # 2. file_tree (files_list, project_files, tree)
            for alias in ["files_list", "project_files", "tree"]:
                if "file_tree" not in d and alias in d and d[alias] is not None:
                    d["file_tree"] = d[alias]
                    break

            # 3. architecture_summary (summary, description)
            for alias in ["summary", "description"]:
                if "architecture_summary" not in d and alias in d and d[alias] is not None:
                    d["architecture_summary"] = str(d[alias]).strip()
                    break

            # 4. interface_contracts (interfaces, public_interfaces, contracts)
            for alias in ["interfaces", "public_interfaces", "contracts"]:
                if "interface_contracts" not in d and alias in d and d[alias] is not None:
                    d["interface_contracts"] = d[alias]
                    break

            # 5. data_models (models, entities)
            for alias in ["models", "entities"]:
                if "data_models" not in d and alias in d and d[alias] is not None:
                    d["data_models"] = d[alias]
                    break

            # Normalisasi 'files':
            files_raw = d.get("files")
            if files_raw is None:
                for alias in ["file_modules", "file_scaffolds"]:
                    if alias in d and d[alias] is not None:
                        files_raw = d[alias]
                        d["files"] = files_raw
                        break

            if isinstance(files_raw, list):
                files_dict = {}
                for item in files_raw:
                    if isinstance(item, dict):
                        fp = item.get("file_path") or item.get("path") or item.get("filename") or item.get("file")
                        if fp:
                            norm_path = str(fp).strip().replace("\\", "/")
                            item["file_path"] = norm_path
                            files_dict[norm_path] = item
                d["files"] = files_dict
            elif isinstance(files_raw, dict):
                norm_files = {}
                for k, v in files_raw.items():
                    norm_k = str(k).strip().replace("\\", "/")
                    if isinstance(v, dict):
                        v.setdefault("file_path", norm_k)
                        v["file_path"] = str(v.get("file_path") or norm_k).strip().replace("\\", "/")
                        norm_files[norm_k] = v
                    elif isinstance(v, (str, list)):
                        norm_files[norm_k] = {
                            "file_path": norm_k,
                            "code_scaffold": v,
                            "module_role": "Authoritative Single Module"
                        }
                    else:
                        norm_files[norm_k] = v
                d["files"] = norm_files

            # Normalisasi interface_contracts jika dict
            raw_ifaces = d.get("interface_contracts")
            if isinstance(raw_ifaces, list):
                norm_ifaces = []
                for iface in raw_ifaces:
                    if isinstance(iface, dict) and "target_file" in iface:
                        iface["target_file"] = str(iface["target_file"]).strip().replace("\\", "/")
                    norm_ifaces.append(iface)
                d["interface_contracts"] = norm_ifaces

            # Normalisasi data_models
            raw_models = d.get("data_models")
            if isinstance(raw_models, list):
                norm_models = []
                for m in raw_models:
                    if isinstance(m, dict):
                        norm_models.append(BlueprintDataModel.model_validate(m))
                    else:
                        norm_models.append(m)
                d["data_models"] = norm_models

            return d
        return data

    @model_validator(mode="after")
    def validate_relational_invariants(self) -> ArchitecturalBlueprint:
        """
        Aturan Integritas Relasional Deterministik:
        1. authoritative_target_file wajib ada di file_tree dan di files.
        2. Zero Phantom Files (1-to-1 consistency):
           - Setiap berkas di file_tree wajib ada di files dan memiliki code_scaffold valid.
           - Setiap berkas di files wajib ada di file_tree.
        3. Interface contract target_file integrity:
           - Setiap contract.target_file wajib ada di files.
        4. Key-path consistency:
           - Setiap key di files wajib sama dengan module.file_path.
        """
        # Rule 1: Authoritative file consistency
        if self.authoritative_target_file not in self.files:
            raise ValueError(
                f"authoritative_target_file '{self.authoritative_target_file}' tidak ditemukan dalam kamus 'files'."
            )
        if self.authoritative_target_file not in self.file_tree:
            raise ValueError(
                f"authoritative_target_file '{self.authoritative_target_file}' tidak terdaftar dalam 'file_tree'."
            )

        # Rule 2: 1-to-1 consistency between file_tree and files
        files_keys = set(self.files.keys())
        tree_keys = set(self.file_tree)

        missing_in_files = tree_keys - files_keys
        if missing_in_files:
            raise ValueError(
                f"File dideklarasikan di 'file_tree' tetapi tidak memiliki modul scaffold di 'files': {sorted(missing_in_files)}"
            )

        missing_in_tree = files_keys - tree_keys
        if missing_in_tree:
            raise ValueError(
                f"File didefinisikan di 'files' tetapi tidak terdaftar di 'file_tree': {sorted(missing_in_tree)}"
            )

        # Rule 3: Interface contract target_file must exist in files
        for contract in self.interface_contracts:
            if contract.target_file not in self.files:
                raise ValueError(
                    f"Kontrak antarmuka '{contract.identifier}' menunjuk target_file '{contract.target_file}' "
                    f"yang tidak eksis dalam blueprint files."
                )

        # Rule 4: Key-path consistency
        for k, mod in self.files.items():
            if k != mod.file_path:
                raise ValueError(
                    f"Kunci files '{k}' tidak cocok dengan module.file_path '{mod.file_path}'"
                )

        return self


def extract_blueprint_json_text(raw_text: str) -> Optional[str]:
    """
    Mengekstrak string JSON blueprint dari output teks LLM.
    Mendukung format:
    1. === BLUEPRINT JSON === ... === END BLUEPRINT JSON ===
    2. ```json ... ```
    3. Blok objek JSON telanjang { ... } jika memuat penanda blueprint kanonikal
    """
    if not raw_text or not raw_text.strip():
        return None

    # 1. Penanda kanonikal ReinDev Studio (mendukung opsional markdown block di dalam marker)
    marker_pattern = r"=== BLUEPRINT JSON ===\s*(?:```(?:json)?\s*)?(\{.*?\})\s*(?:```)?\s*=== END BLUEPRINT JSON ==="
    match = re.search(marker_pattern, raw_text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # 2. Markdown fenced code block ```json ... ```
    md_pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
    match = re.search(md_pattern, raw_text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # 3. Raw JSON object fallback (mencari kurung kurawal terluar jika ada penanda khas)
    brace_start = raw_text.find("{")
    brace_end = raw_text.rfind("}")
    if brace_start != -1 and brace_end > brace_start:
        candidate = raw_text[brace_start:brace_end + 1].strip()
        # Verifikasi cepat apakah kandidat tampak seperti blueprint JSON
        if any(k in candidate for k in ("authoritative_target_file", "files", "file_tree", "architecture_summary")):
            return candidate

    return None


def classify_blueprint_error(err_str: Optional[str]) -> BlueprintErrorClass:
    """
    Mengklasifikasikan pesan error blueprint ke dalam taksonomi Treatment #1.8.3:
    - REPRESENTATION_ERROR: Model bermaksud membuat blueprint yang benar tetapi format representasinya
      tidak cocok (misal: single-key dict wrapper, list of lines vs string, alias vs canonical name).
    - SEMANTIC_ERROR: Conflict representation (misal field_name != name dengan value berbeda),
      missing required semantic field, contradictory target_file.
    - STRUCTURAL_ERROR: File relational invariant failed (missing authoritative file in tree,
      orphan interface contract, phantom files, key-path mismatch).
    - UNRECOVERABLE_REPRESENTATION_ERROR: Arbitrary dict in code_scaffold, unsupported data types,
      total JSON decode failure.
    """
    if not err_str:
        return BlueprintErrorClass.REPRESENTATION_ERROR

    # Jika sudah memiliki awalan tag formal
    for err_cls in BlueprintErrorClass:
        if f"[{err_cls.value}]" in err_str:
            return err_cls

    low = err_str.lower()

    if (
        "unrecoverable" in low
        or "arbitrary dict" in low
        or "tidak ditemukan blok json" in low
        or "gagal mendekode json" in low
        or "bukan berupa json object" in low
    ):
        return BlueprintErrorClass.UNRECOVERABLE_REPRESENTATION_ERROR

    if "representation conflict" in low or "conflict" in low:
        return BlueprintErrorClass.SEMANTIC_ERROR

    # Relational invariants / structural checks
    if any(k in low for k in [
        "authoritative_target_file",
        "file_tree",
        "tidak ditemukan dalam kamus 'files'",
        "tidak terdaftar dalam 'file_tree'",
        "dideklarasikan di 'file_tree' tetapi",
        "didefinisikan di 'files' tetapi",
        "tidak eksis dalam blueprint files",
        "tidak cocok dengan module.file_path",
        "phantom files",
        "orphan",
        "key-path",
        "files_keys",
        "tree_keys",
        "relational",
    ]):
        return BlueprintErrorClass.STRUCTURAL_ERROR

    # Required semantic fields
    if any(k in low for k in ["missing required", "field required", "missing field name", "missing field type"]):
        return BlueprintErrorClass.SEMANTIC_ERROR

    return BlueprintErrorClass.REPRESENTATION_ERROR


def decode_canonical_architectural_json(
    json_str: str,
    stage: str = "BLUEPRINT"
) -> Tuple[Optional[Dict[str, Any]], Optional[str], Dict[str, Any]]:
    """
    Kanonikal JSON decoding untuk seluruh representasi JSON arsitektur (Blueprint dan Stage-B Assembly).
    Menerapkan toleransi strict=False untuk karakter kontrol (misal newline/tab pada string scaffold multiline),
    disertai pembersihan deterministik trailing comma jika terjadi JSONDecodeError awal.

    Mengembalikan (data_dict, error_message, telemetry).
    """
    telemetry: Dict[str, Any] = {
        "decoder_mode": "CANONICAL_STRICT_FALSE",
        "parse_success": False,
        "parse_failure_type": None,
        "stage": stage
    }

    if not json_str or not str(json_str).strip():
        telemetry["parse_failure_type"] = "EMPTY_INPUT"
        return None, "Input JSON kosong", telemetry

    try:
        data = json.loads(json_str, strict=False)
    except json.JSONDecodeError as e:
        cleaned = re.sub(r",\s*([\]}])", r"\1", json_str)
        try:
            data = json.loads(cleaned, strict=False)
            telemetry["decoder_mode"] = "CANONICAL_STRICT_FALSE_TRAILING_COMMA_CLEANED"
        except Exception:
            telemetry["parse_failure_type"] = "UNRECOVERABLE_JSON_DECODE_ERROR"
            return None, f"Gagal mendekode JSON arsitektur: {e}", telemetry

    if not isinstance(data, dict):
        telemetry["parse_failure_type"] = "NON_OBJECT_ROOT"
        return None, "Format data bukan berupa JSON object/dictionary", telemetry

    telemetry["parse_success"] = True
    return data, None, telemetry


def parse_blueprint_json_classified(
    raw_text: str
) -> Tuple[Optional[ArchitecturalBlueprint], Optional[str], Optional[BlueprintErrorClass]]:
    """
    Mengurai dan memvalidasi ArchitecturalBlueprint dari teks mentah, disertai klasifikasi error formal.
    Mengembalikan (blueprint_obj, error_message, error_class).
    """
    json_str = extract_blueprint_json_text(raw_text)
    if not json_str:
        err = "Tidak ditemukan blok JSON blueprint yang valid dalam teks input"
        err_cls = BlueprintErrorClass.UNRECOVERABLE_REPRESENTATION_ERROR
        return None, f"[{err_cls.value}] {err}", err_cls

    data, err, _ = decode_canonical_architectural_json(json_str, stage="BLUEPRINT")
    if err or data is None:
        err_cls = BlueprintErrorClass.UNRECOVERABLE_REPRESENTATION_ERROR
        return None, f"[{err_cls.value}] {err}", err_cls

    try:
        blueprint = ArchitecturalBlueprint.model_validate(data)
        return blueprint, None, None
    except Exception as e:
        err_msg = str(e)
        err_cls = classify_blueprint_error(err_msg)
        return None, f"[{err_cls.value}] Validasi skema ArchitecturalBlueprint gagal: {err_msg}", err_cls


def parse_blueprint_json(raw_text: str) -> Tuple[Optional[ArchitecturalBlueprint], Optional[str]]:
    """
    Mengurai dan memvalidasi ArchitecturalBlueprint dari teks mentah.
    Mengembalikan (blueprint_obj, error_message).
    """
    bp, err, _ = parse_blueprint_json_classified(raw_text)
    return bp, err


def verify_blueprint_semantic_equivalence(
    raw_dict: Dict[str, Any],
    bp: ArchitecturalBlueprint
) -> Tuple[bool, List[str]]:
    """
    Verifikasi deterministik bahwa proses normalisasi Pydantic bersifat:
    - Lossless: semua informasi semantik dari raw_dict dipertahankan.
    - Zero Invention: tidak ada modul, kontrak, atau field tambahan yang dikarang.
    - Semantically Equivalent: scaffold dan identitas relasional identik.
    Mengembalikan (is_equivalent: bool, differences: List[str]).
    """
    differences: List[str] = []

    if not isinstance(raw_dict, dict):
        return False, ["raw_dict bukan merupakan dictionary"]
    if bp is None:
        return False, ["bp bernilai None"]

    # 1. Authoritative Target File Check
    raw_atf = (
        raw_dict.get("authoritative_target_file")
        or raw_dict.get("target_file")
        or raw_dict.get("primary_file")
        or raw_dict.get("main_file")
    )
    if raw_atf is not None:
        norm_raw_atf = str(raw_atf).strip().replace("\\", "/")
        if bp.authoritative_target_file != norm_raw_atf:
            differences.append(
                f"authoritative_target_file mismatch: raw='{norm_raw_atf}' vs bp='{bp.authoritative_target_file}'"
            )

    # 2. Files Check (Lossless & Zero Invention)
    raw_files = raw_dict.get("files")
    if raw_files is None:
        for alias in ["file_modules", "file_scaffolds"]:
            if alias in raw_dict and raw_dict[alias] is not None:
                raw_files = raw_dict[alias]
                break

    expected_file_paths: set = set()

    if isinstance(raw_files, dict):
        for k, v in raw_files.items():
            norm_k = str(k).strip().replace("\\", "/")
            expected_file_paths.add(norm_k)
            if norm_k not in bp.files:
                differences.append(f"Berkas '{norm_k}' dari raw input hilang dalam normalized blueprint")
                continue

            bp_mod = bp.files[norm_k]
            if isinstance(v, dict):
                # Check code_scaffold
                raw_cs = (
                    v.get("code_scaffold")
                    or v.get("scaffold")
                    or v.get("code")
                    or v.get("content")
                    or v.get("source_code")
                )
                if raw_cs is not None:
                    if isinstance(raw_cs, str):
                        if bp_mod.code_scaffold.strip() != raw_cs.strip():
                            differences.append(f"code_scaffold mismatch pada modul '{norm_k}'")
                    elif isinstance(raw_cs, list):
                        joined_raw = "\n".join(str(x) for x in raw_cs)
                        if bp_mod.code_scaffold.strip() != joined_raw.strip():
                            differences.append(f"code_scaffold (list) mismatch pada modul '{norm_k}'")
                    elif isinstance(raw_cs, dict) and len(raw_cs) == 1:
                        inner_cs = list(raw_cs.values())[0]
                        if isinstance(inner_cs, str) and bp_mod.code_scaffold.strip() != inner_cs.strip():
                            differences.append(f"code_scaffold (single-wrapper) mismatch pada modul '{norm_k}'")
            elif isinstance(v, str):
                if bp_mod.code_scaffold.strip() != v.strip():
                    differences.append(f"code_scaffold direct string mismatch pada modul '{norm_k}'")
            elif isinstance(v, list):
                joined_raw = "\n".join(str(x) for x in v)
                if bp_mod.code_scaffold.strip() != joined_raw.strip():
                    differences.append(f"code_scaffold direct list mismatch pada modul '{norm_k}'")

    elif isinstance(raw_files, list):
        for item in raw_files:
            if isinstance(item, dict):
                raw_fp = item.get("file_path") or item.get("path") or item.get("filename") or item.get("file")
                if raw_fp:
                    norm_k = str(raw_fp).strip().replace("\\", "/")
                    expected_file_paths.add(norm_k)
                    if norm_k not in bp.files:
                        differences.append(f"Berkas '{norm_k}' dari raw list hilang dalam normalized blueprint")
                        continue
                    bp_mod = bp.files[norm_k]
                    raw_cs = (
                        item.get("code_scaffold")
                        or item.get("scaffold")
                        or item.get("code")
                        or item.get("content")
                        or item.get("source_code")
                    )
                    if raw_cs is not None:
                        if isinstance(raw_cs, str):
                            if bp_mod.code_scaffold.strip() != raw_cs.strip():
                                differences.append(f"code_scaffold mismatch pada modul list '{norm_k}'")
                        elif isinstance(raw_cs, list):
                            joined_raw = "\n".join(str(x) for x in raw_cs)
                            if bp_mod.code_scaffold.strip() != joined_raw.strip():
                                differences.append(f"code_scaffold (list) mismatch pada modul list '{norm_k}'")

    # Zero file invention check
    bp_file_paths = set(bp.files.keys())
    if expected_file_paths:
        invented_files = bp_file_paths - expected_file_paths
        if invented_files:
            differences.append(f"INVENTED FILES: berkas muncul tanpa ada di raw input: {sorted(invented_files)}")

    # 3. Interface Contracts Check (Lossless & Zero Invention)
    raw_ifaces = raw_dict.get("interface_contracts")
    if raw_ifaces is None:
        for alias in ["interfaces", "public_interfaces", "contracts"]:
            if alias in raw_dict and raw_dict[alias] is not None:
                raw_ifaces = raw_dict[alias]
                break

    if isinstance(raw_ifaces, list):
        bp_contract_ids = {c.identifier for c in bp.interface_contracts}
        raw_contract_ids = set()
        for iface in raw_ifaces:
            if isinstance(iface, dict):
                c_id = (
                    iface.get("identifier")
                    or iface.get("name")
                    or iface.get("function_name")
                    or iface.get("endpoint_name")
                    or iface.get("symbol")
                )
                if c_id:
                    c_id_str = str(c_id).strip()
                    raw_contract_ids.add(c_id_str)
                    if c_id_str not in bp_contract_ids:
                        differences.append(f"Kontrak antarmuka '{c_id_str}' hilang dalam normalized blueprint")

        invented_contracts = bp_contract_ids - raw_contract_ids
        if invented_contracts:
            differences.append(f"INVENTED CONTRACTS: kontrak muncul tanpa ada di raw input: {sorted(invented_contracts)}")

    # 4. Data Models Check (Lossless & Zero Invention)
    raw_models = raw_dict.get("data_models")
    if raw_models is None:
        for alias in ["models", "entities"]:
            if alias in raw_dict and raw_dict[alias] is not None:
                raw_models = raw_dict[alias]
                break

    if isinstance(raw_models, list):
        bp_model_names = set()
        for m in bp.data_models:
            if isinstance(m, BlueprintDataModel):
                bp_model_names.add(m.model_name)
            elif isinstance(m, dict):
                bp_model_names.add(m.get("model_name"))

        raw_model_names = set()
        for m in raw_models:
            if isinstance(m, dict):
                m_name = (
                    m.get("model_name")
                    or m.get("name")
                    or m.get("class_name")
                    or m.get("entity_name")
                )
                if m_name:
                    m_name_str = str(m_name).strip()
                    raw_model_names.add(m_name_str)
                    if m_name_str not in bp_model_names:
                        differences.append(f"Data model '{m_name_str}' hilang dalam normalized blueprint")

        invented_models = bp_model_names - raw_model_names
        if invented_models:
            differences.append(f"INVENTED DATA MODELS: model muncul tanpa ada di raw input: {sorted(invented_models)}")

    return len(differences) == 0, differences


def normalize_blueprint_data_models(
    raw_models: List[Any],
    default_target_file: str = "main.py"
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Deterministic boundary adapter:
    Mentransformasikan Blueprint data_models menjadi representasi kanonikal strict ModelField
    sebelum diserahkan ke MachineReadableContract.

    Aturan Normalisasi:
    1. Deterministic & lossless: memetakan 'name' -> 'field_name' dan 'type' -> 'field_type'.
    2. Zero semantic inference: tidak menambah field yang tidak diberikan, tidak mengubah meaning.
    3. Conflict Detection: jika kedua bentuk hadir sekaligus dengan nilai berbeda
       (field_name != name atau field_type != type), ditandai sebagai 'REPRESENTATION CONFLICT'
       dan ditolak secara deterministik untuk perbaikan mandiri.
    4. Completeness: jika field_name atau field_type tidak tersedia setelah normalisasi, ditolak.
    5. Domain-agnostic: murni transformasi representasional tanpa asumsi domain (FastAPI/CLI/Flutter).
    """
    canonical_models: List[Dict[str, Any]] = []
    errors: List[str] = []

    if not raw_models:
        return canonical_models, errors

    for m_idx, raw_m in enumerate(raw_models, 1):
        if hasattr(raw_m, "model_dump"):
            m_dict = raw_m.model_dump()
        elif hasattr(raw_m, "to_dict"):
            m_dict = raw_m.to_dict()
        elif isinstance(raw_m, dict):
            m_dict = dict(raw_m)
        else:
            errors.append(f"Data model #{m_idx} bukan berupa dictionary/model valid")
            continue

        model_name = str(m_dict.get("model_name") or m_dict.get("name") or "").strip()
        if not model_name:
            errors.append(f"Data model #{m_idx} tidak memiliki 'model_name' yang valid")
            continue

        target_file = str(m_dict.get("target_file") or default_target_file).strip().replace("\\", "/")
        raw_fields = m_dict.get("fields") or []

        canonical_fields: List[Dict[str, Any]] = []
        for f_idx, raw_f in enumerate(raw_fields, 1):
            if hasattr(raw_f, "model_dump"):
                f_dict = raw_f.model_dump()
            elif hasattr(raw_f, "to_dict"):
                f_dict = raw_f.to_dict()
            elif isinstance(raw_f, dict):
                f_dict = dict(raw_f)
            else:
                errors.append(f"Model '{model_name}' field #{f_idx} bukan berupa dictionary valid")
                continue

            # 1. Resolve field_name (dengan deteksi konflik representasi)
            has_canonical_name = "field_name" in f_dict and f_dict["field_name"] is not None
            has_alias_name = "name" in f_dict and f_dict["name"] is not None

            resolved_field_name: Optional[str] = None
            if has_canonical_name and has_alias_name:
                c_val = str(f_dict["field_name"]).strip()
                a_val = str(f_dict["name"]).strip()
                if c_val != a_val:
                    errors.append(
                        f"REPRESENTATION CONFLICT pada model '{model_name}' field #{f_idx}: "
                        f"field_name='{c_val}' != name='{a_val}'"
                    )
                    continue
                resolved_field_name = c_val
            elif has_canonical_name:
                resolved_field_name = str(f_dict["field_name"]).strip()
            elif has_alias_name:
                resolved_field_name = str(f_dict["name"]).strip()
            else:
                errors.append(
                    f"MISSING FIELD NAME pada model '{model_name}' field #{f_idx}: "
                    f"wajib menyertakan 'field_name' (atau alias 'name')"
                )
                continue

            if not resolved_field_name:
                errors.append(f"Model '{model_name}' field #{f_idx} memiliki nama field kosong")
                continue

            # 2. Resolve field_type (dengan deteksi konflik representasi)
            has_canonical_type = "field_type" in f_dict and f_dict["field_type"] is not None
            has_alias_type = "type" in f_dict and f_dict["type"] is not None

            resolved_field_type: Optional[str] = None
            if has_canonical_type and has_alias_type:
                c_type = str(f_dict["field_type"]).strip()
                a_type = str(f_dict["type"]).strip()
                if c_type != a_type:
                    errors.append(
                        f"REPRESENTATION CONFLICT pada model '{model_name}' field '{resolved_field_name}': "
                        f"field_type='{c_type}' != type='{a_type}'"
                    )
                    continue
                resolved_field_type = c_type
            elif has_canonical_type:
                resolved_field_type = str(f_dict["field_type"]).strip()
            elif has_alias_type:
                resolved_field_type = str(f_dict["type"]).strip()
            else:
                errors.append(
                    f"MISSING FIELD TYPE pada model '{model_name}' field '{resolved_field_name}': "
                    f"wajib menyertakan 'field_type' (atau alias 'type')"
                )
                continue

            if not resolved_field_type:
                errors.append(f"Model '{model_name}' field '{resolved_field_name}' memiliki tipe data kosong")
                continue

            # 3. Lossless mapping atribut sekunder (memastikan constraints sesuai skema ModelField: Optional[str])
            raw_constraints = f_dict.get("constraints")
            if raw_constraints is not None:
                if isinstance(raw_constraints, (dict, list)):
                    resolved_constraints = json.dumps(raw_constraints, sort_keys=True)
                else:
                    resolved_constraints = str(raw_constraints)
            else:
                resolved_constraints = None

            raw_desc = f_dict.get("description")
            resolved_desc = str(raw_desc) if raw_desc is not None else None

            canonical_field = {
                "field_name": resolved_field_name,
                "field_type": resolved_field_type,
                "is_required": bool(f_dict.get("is_required", True)),
                "constraints": resolved_constraints,
                "description": resolved_desc
            }
            canonical_fields.append(canonical_field)

        canonical_model = {
            "model_name": model_name,
            "target_file": target_file,
            "fields": canonical_fields
        }
        if "construction_shape" in m_dict:
            canonical_model["construction_shape"] = m_dict["construction_shape"]

        canonical_models.append(canonical_model)

    return canonical_models, errors


def blueprint_to_narrative_markdown(bp: ArchitecturalBlueprint) -> str:
    """
    Mengonversi ArchitecturalBlueprint ke representasi Markdown yang mudah dibaca
    untuk diinjeksikan ke prompt Developer atau keperluan inspeksi manusia.
    """
    lines = []
    lines.append(f"### Rencana Arsitektur: {bp.authoritative_target_file.upper()}")
    if bp.architecture_summary:
        lines.append(f"\n**Ringkasan Arsitektur:**\n{bp.architecture_summary}\n")

    lines.append("#### Peta Struktur Berkas:")
    for f in bp.file_tree:
        lines.append(f"- `{f}`")

    lines.append(f"\n**Target File Authoritative:** `{bp.authoritative_target_file}`\n")

    for path, mod in bp.files.items():
        lines.append(f"#### Modul: `{path}` ({mod.module_role or 'Implementation Module'})")
        if mod.description:
            lines.append(f"*{mod.description}*")
        if mod.code_scaffold:
            lang = bp.target_language.lower()
            lines.append(f"```{lang}\n{mod.code_scaffold.strip()}\n```\n")

    return "\n".join(lines)


def serialize_blueprint_to_canonical_json(
    bp: Union[ArchitecturalBlueprint, Dict[str, Any]]
) -> str:
    """
    Serialisasi kanonikal deterministik ArchitecturalBlueprint ke format JSON tunggal.
    Menghasilkan string JSON murni tanpa delimiter eksternal atau pembungkus markdown.
    Invarian:
    - Root berupa tepat satu objek JSON valid.
    - Tidak memuat delimiter eksternal ('=== BLUEPRINT JSON ===', '=== STAGE A', dsb.).
    - Tidak memuat markdown code fence (```json ... ```).
    - Preservasi byte-for-byte multiline scaffold.
    """
    if isinstance(bp, ArchitecturalBlueprint):
        if hasattr(bp, "model_dump_json"):
            return bp.model_dump_json(indent=2)
        elif hasattr(bp, "model_dump"):
            return json.dumps(bp.model_dump(), indent=2)
        elif hasattr(bp, "dict"):
            return json.dumps(bp.dict(), indent=2)
    elif isinstance(bp, dict):
        return json.dumps(bp, indent=2)
    raise ValueError(f"Cannot serialize object of type {type(bp)} to canonical blueprint JSON")


def validate_canonical_architecture_plan_state(
    architecture_plan: str,
    canonical_blueprint: Optional[Union[ArchitecturalBlueprint, Dict[str, Any]]] = None,
    contract: Optional[Dict[str, Any]] = None
) -> Tuple[bool, List[str]]:
    """
    Validasi invarian representasi state kanonikal untuk state["architecture_plan"]:
    A. valid JSON
    B. exactly one root object (tidak ada trailing/extra data)
    C. canonical Blueprint schema valid (conforms to ArchitecturalBlueprint)
    D. no concatenated JSON blocks
    E. no Stage A/B delimiters or markdown wrappers
    F. semantic equivalence with the structured canonical blueprint
    G. no information loss (scaffold, files, interfaces preserved)
    H. no obligation loss (interfaces cover expected identifiers)
    I. no modification of frozen contract semantics

    Mengembalikan (is_valid, error_list). Jika gagal, error bertipe STATE_REPRESENTATION_FAILURE.
    """
    errors: List[str] = []
    if not isinstance(architecture_plan, str):
        return False, ["STATE_REPRESENTATION_FAILURE: architecture_plan must be a string"]

    stripped = architecture_plan.strip()
    if not stripped:
        return False, ["STATE_REPRESENTATION_FAILURE: architecture_plan is empty"]

    # Criterion E: No Stage A/B delimiters or narrative markdown code fences
    forbidden_markers = [
        "=== STAGE A",
        "=== STAGE B",
        "=== STAGE A OUTPUT ===",
        "=== STAGE B OUTPUT ===",
        "=== STAGE A REPAIR OUTPUT ===",
        "=== STAGE B REPAIR OUTPUT ===",
        "=== BLUEPRINT JSON ===",
        "=== END BLUEPRINT JSON ===",
        "=== SEMANTIC DECISION JSON ===",
        "```json",
        "```"
    ]
    for marker in forbidden_markers:
        if marker in architecture_plan:
            errors.append(f"STATE_REPRESENTATION_FAILURE: architecture_plan contains forbidden delimiter or wrapper '{marker}'")
            return False, errors

    # Criterion A & B & D: Valid JSON, exactly one root object, no concatenated JSON
    decoder = json.JSONDecoder()
    try:
        decoded_obj, end_idx = decoder.raw_decode(stripped)
    except Exception as exc:
        return False, [f"STATE_REPRESENTATION_FAILURE: architecture_plan is not valid JSON: {exc}"]

    if not isinstance(decoded_obj, dict):
        return False, ["STATE_REPRESENTATION_FAILURE: architecture_plan root is not a JSON object/dictionary"]

    remaining = stripped[end_idx:].strip()
    if remaining:
        return False, [f"STATE_REPRESENTATION_FAILURE: architecture_plan contains extra trailing data or concatenated JSON: '{remaining[:60]}'"]

    # Criterion C: Canonical Blueprint schema valid
    try:
        parsed_bp = ArchitecturalBlueprint.model_validate(decoded_obj)
    except Exception as exc:
        return False, [f"STATE_REPRESENTATION_FAILURE: architecture_plan violates ArchitecturalBlueprint schema: {exc}"]

    # Criterion F, G, H: Semantic equivalence, no info loss, no obligation loss
    if canonical_blueprint is not None:
        expected_dict = canonical_blueprint.model_dump() if hasattr(canonical_blueprint, "model_dump") else (
            canonical_blueprint if isinstance(canonical_blueprint, dict) else {}
        )

        # 1. Authoritative target file
        if decoded_obj.get("authoritative_target_file") != expected_dict.get("authoritative_target_file"):
            errors.append(
                f"STATE_REPRESENTATION_FAILURE: authoritative_target_file mismatch: "
                f"observed '{decoded_obj.get('authoritative_target_file')}' != expected '{expected_dict.get('authoritative_target_file')}'"
            )

        # 2. File tree
        obs_tree = sorted(decoded_obj.get("file_tree") or [])
        exp_tree = sorted(expected_dict.get("file_tree") or [])
        if obs_tree != exp_tree:
            errors.append(f"STATE_REPRESENTATION_FAILURE: file_tree mismatch: {obs_tree} != {exp_tree}")

        # 3. Files and scaffolds byte-for-byte preservation
        obs_files = decoded_obj.get("files") or {}
        exp_files = expected_dict.get("files") or {}
        if set(obs_files.keys()) != set(exp_files.keys()):
            errors.append(f"STATE_REPRESENTATION_FAILURE: files keys mismatch: {set(obs_files.keys())} != {set(exp_files.keys())}")
        else:
            for fpath, exp_m in exp_files.items():
                obs_m = obs_files.get(fpath) or {}
                exp_scaff = exp_m.get("code_scaffold", "") if isinstance(exp_m, dict) else getattr(exp_m, "code_scaffold", "")
                obs_scaff = obs_m.get("code_scaffold", "") if isinstance(obs_m, dict) else getattr(obs_m, "code_scaffold", "")
                if exp_scaff != obs_scaff:
                    errors.append(f"STATE_REPRESENTATION_FAILURE: code_scaffold corrupted or altered for file '{fpath}'")

        # 4. Interface contracts count and identifiers
        obs_ifaces = [ifc.get("identifier") for ifc in decoded_obj.get("interface_contracts") or [] if isinstance(ifc, dict)]
        exp_ifaces = [ifc.get("identifier") for ifc in expected_dict.get("interface_contracts") or [] if isinstance(ifc, dict)]
        if sorted(obs_ifaces) != sorted(exp_ifaces):
            errors.append(f"STATE_REPRESENTATION_FAILURE: interface_contracts identifiers mismatch: {obs_ifaces} != {exp_ifaces}")

        # 5. Data models count and names
        obs_models = [m.get("model_name") for m in decoded_obj.get("data_models") or [] if isinstance(m, dict)]
        exp_models = [m.get("model_name") for m in expected_dict.get("data_models") or [] if isinstance(m, dict)]
        if sorted(obs_models) != sorted(exp_models):
            errors.append(f"STATE_REPRESENTATION_FAILURE: data_models names mismatch: {obs_models} != {exp_models}")

    # Criterion I: No modification of frozen contract semantics
    if contract and isinstance(contract, dict):
        if contract.get("status") == "FROZEN":
            c_ifaces = [ifc.get("identifier") for ifc in contract.get("interface_contracts") or [] if isinstance(ifc, dict)]
            bp_ifaces = [ifc.get("identifier") for ifc in decoded_obj.get("interface_contracts") or [] if isinstance(ifc, dict)]
            missing = set(c_ifaces) - set(bp_ifaces)
            if missing:
                errors.append(f"STATE_REPRESENTATION_FAILURE: architecture_plan dropped frozen contract interfaces: {sorted(missing)}")

    return len(errors) == 0, errors

