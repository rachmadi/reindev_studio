"""
knowledge_catalog.py
====================
Katalog deklaratif aturan deprecation, breaking changes, dan positive canonical templates
lintas ekosistem (Dart/Flutter, Python, JavaScript/TypeScript).

Memisahkan data pengetahuan library dan template pengganti dari logika prosedural engine,
sehingga penambahan pustaka/versi baru cukup dilakukan dengan mendaftarkan aturan di sini.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class DeprecationRule:
    """Aturan deklaratif untuk satu pustaka / batasan versi."""
    id: str
    ecosystem: str                       # "dart", "python", "javascript", dll.
    package: str                         # nama paket huruf kecil, misal "flutter_riverpod", "pydantic"
    version_min: Optional[str] = None    # semver inklusif, misal "2.0.0"
    version_max: Optional[str] = None    # semver eksklusif, misal "3.0.0"
    prohibited_patterns: List[str] = field(default_factory=list) # Simbol/token yang dilarang
    rationale: str = ""                  # Alasan teknis
    positive_template: str = ""          # Contoh kode konkret yang valid dan siap ditiru
    architect_instruction: str = ""      # Panduan spesifik untuk System Architect
    developer_instruction: str = ""      # Panduan spesifik untuk Developer


def parse_semver(v_str: Optional[str]) -> Tuple[int, int, int]:
    """Ekstrak (major, minor, patch) dari semver string."""
    if not v_str:
        return (0, 0, 0)
    m = re.match(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?", v_str.strip())
    if not m:
        return (0, 0, 0)
    major = int(m.group(1)) if m.group(1) else 0
    minor = int(m.group(2)) if m.group(2) else 0
    patch = int(m.group(3)) if m.group(3) else 0
    return (major, minor, patch)


def semver_matches(
    version: Optional[str],
    version_min: Optional[str] = None,
    version_max: Optional[str] = None,
) -> bool:
    """
    Cek apakah `version` memenuhi kriteria:
    version_min <= version < version_max (jika ditentukan).
    """
    if not version:
        return False
    v = parse_semver(version)
    if version_min:
        if v < parse_semver(version_min):
            return False
    if version_max:
        if v >= parse_semver(version_max):
            return False
    return True


# ============================================================================
# Default Knowledge Catalog Registry
# ============================================================================

DEFAULT_RULES: List[DeprecationRule] = [
    # ------------------------------------------------------------------------
    # DART / FLUTTER: flutter_riverpod >= 2.0.0
    # ------------------------------------------------------------------------
    DeprecationRule(
        id="riverpod_v2_plus_no_state_notifier",
        ecosystem="dart",
        package="flutter_riverpod",
        version_min="2.0.0",
        prohibited_patterns=[
            "StateNotifier",
            "StateNotifierProvider",
            "StateProvider",
        ],
        rationale=(
            "Di flutter_riverpod v2+ dan v3+, StateNotifier dan StateProvider sudah usang (deprecated/split). "
            "Model dilarang keras membuat class turunan StateNotifier."
        ),
        positive_template=(
            "// POLA RIVERPOD KANONIKAL:\n"
            "final itemProvider = Provider<ItemState>((ref) => ItemState());\n\n"
            "// ConsumerWidget membaca provider secara langsung via ref.watch():\n"
            "class ItemWidget extends ConsumerWidget {\n"
            "  const ItemWidget({super.key});\n"
            "  @override\n"
            "  Widget build(BuildContext context, WidgetRef ref) {\n"
            "    final data = ref.watch(itemProvider);\n"
            "    return Card(child: Text(data.toString()));\n"
            "  }\n"
            "}"
        ),
        architect_instruction=(
            "DILARANG KERAS merancang class yang mewarisi StateNotifier atau menggunakan StateNotifierProvider. "
            "Rancang state management menggunakan `Provider<T>` murni atau class controller berbasis ChangeNotifier/ValueNotifier."
        ),
        developer_instruction=(
            "GUNAKAN `Provider<T>((ref) => ...)` murni. DILARANG menggunakan `StateNotifier`, `StateNotifierProvider`, atau `StateProvider`. "
            "Jika method build menerima (BuildContext context, WidgetRef ref), kelas WAJIB `extends ConsumerWidget`."
        ),
    ),
    # ------------------------------------------------------------------------
    # PYTHON: pydantic >= 2.0.0
    # ------------------------------------------------------------------------
    DeprecationRule(
        id="pydantic_v2_modern_validators",
        ecosystem="python",
        package="pydantic",
        version_min="2.0.0",
        prohibited_patterns=[
            "@validator",
            "class Config:",
            "orm_mode",
            "regex=",
        ],
        rationale=(
            "Pydantic v2 menggantikan @validator dengan @field_validator, class Config dengan model_config, "
            "dan orm_mode dengan from_attributes = True."
        ),
        positive_template=(
            "from pydantic import BaseModel, ConfigDict, field_validator\n\n"
            "class ItemModel(BaseModel):\n"
            "    model_config = ConfigDict(from_attributes=True)\n"
            "    id: int | None = None\n"
            "    name: str\n\n"
            "    @field_validator('name')\n"
            "    @classmethod\n"
            "    def validate_name(cls, v: str) -> str:\n"
            "        return v.strip()"
        ),
        architect_instruction=(
            "Rancang skema model sesuai standar Pydantic v2: id bertipe `int | None = None`, konfigurasi model_config = ConfigDict, "
            "dan method validasi menggunakan @field_validator."
        ),
        developer_instruction=(
            "Gunakan @field_validator dan ConfigDict(from_attributes=True). "
            "DILARANG menggunakan @validator, class Config, atau orm_mode."
        ),
    ),
    # ------------------------------------------------------------------------
    # PYTHON: pydantic < 2.0.0 (v1 legacy)
    # ------------------------------------------------------------------------
    DeprecationRule(
        id="pydantic_v1_legacy_support",
        ecosystem="python",
        package="pydantic",
        version_max="2.0.0",
        prohibited_patterns=[
            "@field_validator",
            "model_config",
            "from_attributes",
        ],
        rationale="Pydantic v1 menggunakan @validator dan inner class Config.",
        positive_template=(
            "from pydantic import BaseModel, validator\n\n"
            "class ItemModel(BaseModel):\n"
            "    id: int = None\n"
            "    class Config:\n"
            "        orm_mode = True"
        ),
        architect_instruction="Rancang skema Pydantic v1 dengan inner class Config.",
        developer_instruction="Gunakan @validator dan inner class Config: orm_mode = True.",
    ),
    # ------------------------------------------------------------------------
    # PYTHON: fastapi (General Best Practice Grounding)
    # ------------------------------------------------------------------------
    DeprecationRule(
        id="fastapi_endpoint_conventions",
        ecosystem="python",
        package="fastapi",
        prohibited_patterns=[
            "app.test_client()",
            "flask",
        ],
        rationale="FastAPI menggunakan HTTPException dan TestClient dari starlette/fastapi, bukan Flask.",
        positive_template=(
            "from fastapi import FastAPI, HTTPException, status\n"
            "from fastapi.testclient import TestClient\n\n"
            "app = FastAPI()\n\n"
            "@app.post('/items/', status_code=status.HTTP_201_CREATED)\n"
            "def create_item(item: dict):\n"
            "    return item\n\n"
            "@app.delete('/items/{item_id}', status_code=status.HTTP_204_NO_CONTENT)\n"
            "def delete_item(item_id: int):\n"
            "    return None"
        ),
        architect_instruction=(
            "Rancang endpoint REST FastAPI dengan status code eksplisit (201 untuk POST, 204 untuk DELETE, 404 untuk Not Found)."
        ),
        developer_instruction=(
            "Gunakan FastAPI dan TestClient. POST wajib status_code=201, DELETE wajib status_code=204, "
            "dan 404 wajib menggunakan HTTPException."
        ),
    ),
]


class KnowledgeCatalog:
    """Mesin pengelola aturan lingkungan dan pencocokan versi."""

    def __init__(self, rules: Optional[List[DeprecationRule]] = None):
        self._rules = list(rules) if rules is not None else list(DEFAULT_RULES)

    def register_rule(self, rule: DeprecationRule) -> None:
        """Daftarkan aturan baru secara dinamis."""
        self._rules.append(rule)

    def get_matching_rules(
        self,
        ecosystem: str,
        installed_packages: Dict[str, str],
    ) -> List[DeprecationRule]:
        """
        Cari seluruh aturan yang cocok berdasarkan ekosistem dan paket yang terpasang.
        """
        eco_norm = ecosystem.lower().strip()
        matched = []
        for r in self._rules:
            # Cocokkan ekosistem
            if r.ecosystem.lower() != eco_norm and not (
                ("flutter" in eco_norm and r.ecosystem == "dart") or
                ("dart" in eco_norm and r.ecosystem == "flutter")
            ):
                continue

            pkg_name = r.package.lower()
            if pkg_name not in installed_packages:
                continue

            installed_ver = installed_packages[pkg_name]
            if semver_matches(installed_ver, r.version_min, r.version_max):
                matched.append(r)

        return matched


# Global singleton instance
catalog = KnowledgeCatalog()
