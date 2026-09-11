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
from typing import Dict, List, Any, Optional, Tuple, Union
from pydantic import BaseModel, Field, field_validator, model_validator


class BlueprintFileModule(BaseModel):
    """Representasi modul/berkas tunggal dalam cetak biru arsitektur."""
    file_path: str = Field(..., min_length=1, description="Path relatif berkas target (misal: main.py atau lib/card_metric.dart)")
    module_role: str = Field(default="Authoritative Single Module", min_length=1, description="Peran modul")
    imports: List[str] = Field(default_factory=list, description="Daftar statement import yang dibutuhkan modul")
    code_scaffold: str = Field(..., min_length=1, description="Scaffold kode lengkap dan terpadu untuk berkas ini (WAJIB ADA)")
    description: Optional[str] = Field(None, description="Deskripsi singkat tanggung jawab modul")

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
    identifier: str = Field(..., min_length=1, description="Nama fungsi/endpoint/metode")
    route: Optional[str] = Field(None, description="Route path (misal: /products)")
    method: Optional[str] = Field(None, description="HTTP Method (misal: GET, POST)")
    target_file: str = Field(..., min_length=1, description="Berkas tempat kontrak ini didefinisikan")

    @field_validator("target_file")
    @classmethod
    def validate_target_file(cls, v: str) -> str:
        cleaned = v.strip().replace("\\", "/")
        if not cleaned:
            raise ValueError("target_file pada kontrak antarmuka tidak boleh kosong")
        return cleaned


class ArchitecturalBlueprint(BaseModel):
    """Skema kanonikal formal untuk cetak biru arsitektur perangkat lunak ReinDev Studio."""
    schema_version: str = Field(default="1.0.0", description="Versi skema blueprint")
    task_id: str = Field(default="default_task", min_length=1, description="ID tugas")
    target_language: str = Field(default="python", min_length=1, description="Bahasa target: python atau dart")
    authoritative_target_file: str = Field(default="main.py", min_length=1, description="File target implementasi utama")
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
    data_models: List[Dict[str, Any]] = Field(
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
            # Normalisasi jika 'files' dikirim sebagai list of dict
            files_raw = data.get("files")
            if isinstance(files_raw, list):
                files_dict = {}
                for item in files_raw:
                    if isinstance(item, dict) and "file_path" in item:
                        norm_path = item["file_path"].strip().replace("\\", "/")
                        item["file_path"] = norm_path
                        files_dict[norm_path] = item
                data["files"] = files_dict
            elif isinstance(files_raw, dict):
                norm_files = {}
                for k, v in files_raw.items():
                    norm_k = k.strip().replace("\\", "/")
                    if isinstance(v, dict):
                        v.setdefault("file_path", norm_k)
                        v["file_path"] = v["file_path"].strip().replace("\\", "/")
                    norm_files[norm_k] = v
                data["files"] = norm_files

            # Normalisasi interface_contracts jika dict
            raw_ifaces = data.get("interface_contracts")
            if isinstance(raw_ifaces, list):
                norm_ifaces = []
                for iface in raw_ifaces:
                    if isinstance(iface, dict) and "target_file" in iface:
                        iface["target_file"] = iface["target_file"].strip().replace("\\", "/")
                    norm_ifaces.append(iface)
                data["interface_contracts"] = norm_ifaces
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

    # 1. Penanda kanonikal ReinDev Studio
    marker_pattern = r"=== BLUEPRINT JSON ===\s*(\{.*?\})\s*=== END BLUEPRINT JSON ==="
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


def parse_blueprint_json(raw_text: str) -> Tuple[Optional[ArchitecturalBlueprint], Optional[str]]:
    """
    Mengurai dan memvalidasi ArchitecturalBlueprint dari teks mentah.
    Mengembalikan (blueprint_obj, error_message).
    """
    json_str = extract_blueprint_json_text(raw_text)
    if not json_str:
        return None, "Tidak ditemukan blok JSON blueprint yang valid dalam teks input"

    try:
        data = json.loads(json_str, strict=False)
    except json.JSONDecodeError as e:
        cleaned = re.sub(r",\s*([\]}])", r"\1", json_str)
        try:
            data = json.loads(cleaned, strict=False)
        except Exception:
            return None, f"Gagal mendekode JSON blueprint: {e}"

    if not isinstance(data, dict):
        return None, "Format data blueprint bukan berupa JSON object/dictionary"

    try:
        blueprint = ArchitecturalBlueprint.model_validate(data)
        return blueprint, None
    except Exception as e:
        return None, f"Validasi skema ArchitecturalBlueprint gagal: {e}"


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
