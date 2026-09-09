"""
environment_grounding.py
========================
Memeriksa fakta aktual environment lokal (sandbox & workspace) dan menghasilkan
"Environment Fact Card" untuk Architect dan Developer sebelum mereka merancang atau menulis kode.

Fitur:
  - Universal Manifest Scanner (pubspec.lock, package.json, pip/requirements.txt)
  - Declarative Knowledge Catalog integration (knowledge_catalog.py)
  - Positive Canonical Substitution Templates
  - Pipeline-Wide Grounding (Architect Fact Card & Developer Fact Card)
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from .knowledge_catalog import catalog, DeprecationRule
except (ImportError, ValueError):
    try:
        from knowledge_catalog import catalog, DeprecationRule
    except ImportError:
        catalog = None  # type: ignore[assignment]

# Root workspace — resolusi dari lokasi file ini (backend/)
_BACKEND_DIR = Path(__file__).parent
_WORKSPACE_DIR = _BACKEND_DIR.parent
_SANDBOX_DIR = _BACKEND_DIR / "sandbox"
_VENV_PYTHON = _BACKEND_DIR / ".venv" / ("Scripts" if sys.platform == "win32" else "bin") / "python"


# ---------------------------------------------------------------------------
# Manifest Scanner & Package Lookup Helpers
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _get_python_installed_packages() -> Dict[str, str]:
    """
    Jalankan `pip list --format=json` di venv backend, kembalikan dict {name: version}.
    Di-cache agar tidak spawn subprocess berulang kali dalam satu sesi.
    """
    python_exe = str(_VENV_PYTHON) if _VENV_PYTHON.exists() else sys.executable
    try:
        result = subprocess.run(
            [python_exe, "-m", "pip", "list", "--format=json"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
        if result.returncode == 0:
            packages = json.loads(result.stdout)
            return {pkg["name"].lower(): pkg["version"] for pkg in packages}
    except Exception:
        pass
    return {}


def parse_pubspec_lock(lock_path: Path) -> Dict[str, str]:
    """
    Ekstrak nama paket dan versi dari berkas pubspec.lock (YAML).
    """
    packages: Dict[str, str] = {}
    if not lock_path.exists():
        return packages
    try:
        text = lock_path.read_text(encoding="utf-8", errors="replace")
        # Format pubspec.lock:
        #   package_name:
        #     ...
        #     version: "x.y.z"
        pattern = re.compile(
            r"^[ ]{2}([a-zA-Z0-9_]+):\s*\n(?:[ ]{4}[^\n]*\n)*?[ ]{4}version:\s*[\"']?([^\"'\s]+)[\"']?",
            re.MULTILINE,
        )
        for m in pattern.finditer(text):
            packages[m.group(1).lower()] = m.group(2).strip()
    except Exception:
        pass
    return packages


def parse_package_json(pkg_json_path: Path) -> Dict[str, str]:
    """
    Ekstrak dependencies dari package.json (Node/JS/TS).
    """
    packages: Dict[str, str] = {}
    if not pkg_json_path.exists():
        return packages
    try:
        data = json.loads(pkg_json_path.read_text(encoding="utf-8", errors="replace"))
        deps = data.get("dependencies", {})
        dev_deps = data.get("devDependencies", {})
        for k, v in {**deps, **dev_deps}.items():
            clean_v = re.sub(r"^[\^~>=<]+", "", str(v)).strip()
            packages[k.lower()] = clean_v
    except Exception:
        pass
    return packages


def find_active_manifest_packages(
    ecosystem: str,
    target_dir: Optional[str] = None,
) -> Dict[str, str]:
    """
    Pindai dan kumpulkan dependensi paket yang terpasang pada sandbox/workspace
    berdasarkan ekosistem bahasa.
    """
    eco = ecosystem.lower().strip()
    packages: Dict[str, str] = {}

    search_dirs: List[Path] = []
    if target_dir:
        search_dirs.append(Path(target_dir))
    search_dirs.extend([
        _SANDBOX_DIR,
        _WORKSPACE_DIR / "frontend",
        _WORKSPACE_DIR,
        _WORKSPACE_DIR / "app",
    ])

    if "dart" in eco or "flutter" in eco:
        for d in search_dirs:
            lock_file = d / "pubspec.lock"
            if lock_file.exists():
                found = parse_pubspec_lock(lock_file)
                if found:
                    packages.update(found)
                    break

    elif "python" in eco:
        packages.update(_get_python_installed_packages())

    elif "javascript" in eco or "typescript" in eco or "node" in eco:
        for d in search_dirs:
            pkg_file = d / "package.json"
            if pkg_file.exists():
                found = parse_package_json(pkg_file)
                if found:
                    packages.update(found)
                    break

    return packages


@lru_cache(maxsize=1)
def _get_dart_sdk_version() -> Optional[str]:
    """Jalankan `dart --version` untuk mendapatkan versi Dart SDK aktual."""
    try:
        result = subprocess.run(
            ["dart", "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
        output = (result.stdout + result.stderr).strip()
        m = re.search(r"Dart SDK version:\s*([\d\.]+)", output)
        if m:
            return m.group(1)
    except Exception:
        pass
    return None


@lru_cache(maxsize=1)
def _get_flutter_version() -> Optional[str]:
    """Coba baca versi Flutter dari flutter --version."""
    try:
        result = subprocess.run(
            ["flutter", "--version", "--machine"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return data.get("frameworkVersion")
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Fact Card Generator: Architect vs Developer
# ---------------------------------------------------------------------------

def generate_fact_card_for_architect(
    target_language: str,
    task: str = "",
    target_dir: Optional[str] = None,
    dynamic_facts: Optional[List[str]] = None,
) -> str:
    """
    Hasilkan Environment Fact Card khusus untuk System Architect.
    Memberi batasan keras agar Architect TIDAK merancang struktur, kelas,
    atau modul yang menggunakan API/pustaka yang dilarang di runtime aktif.
    """
    lang = target_language.lower()
    is_dart = "dart" in lang or "flutter" in lang
    is_py = "python" in lang
    eco = "dart" if is_dart else ("python" if is_py else "javascript")

    packages = find_active_manifest_packages(eco, target_dir=target_dir)
    matched_rules = catalog.get_matching_rules(eco, packages) if catalog else []

    lines = [f"[ENVIRONMENT FACTS — ARCHITECTURAL CONSTRAINTS ({target_language.upper()})]"]

    if is_dart:
        dart_v = _get_dart_sdk_version()
        flutter_v = _get_flutter_version()
        if dart_v:
            lines.append(f"Dart SDK: {dart_v}")
        if flutter_v:
            lines.append(f"Flutter: {flutter_v}")
        if "flutter_riverpod" in packages:
            lines.append(f"flutter_riverpod: {packages['flutter_riverpod']} (TERPASANG)")
        lines.append("Struktur: Single cohesive module di lib/ (maksimal 1 file produksi).")
    elif is_py:
        lines.append(f"Python runtime: {sys.version.split()[0]}")
        for p in ["fastapi", "pydantic", "pytest"]:
            if p in packages:
                lines.append(f"{p}: {packages[p]} (TERPASANG)")

    lines.append("")
    lines.append("BATASAN ARSITEKTUR WAJIB (DILARANG DILANGGAR DALAM RANCANGAN):")

    for r in matched_rules:
        if r.architect_instruction:
            lines.append(f"• Pustaka '{r.package}': {r.architect_instruction}")
        if r.prohibited_patterns:
            lines.append(f"  - SIMBOL TERLARANG: {', '.join(r.prohibited_patterns)}")

    if dynamic_facts:
        lines.append("")
        lines.append("FAKTA DINAMIS DARI COMPILER/RUNTIME:")
        for df in dynamic_facts:
            lines.append(f"• {df}")

    return "\n".join(lines)


def generate_fact_card_for_developer(
    target_language: str,
    task: str = "",
    target_dir: Optional[str] = None,
    dynamic_facts: Optional[List[str]] = None,
) -> str:
    """
    Hasilkan Environment Fact Card khusus untuk Developer Agent.
    Memuat Aturan Preseden, Larangan Token, dan Template Kanonikal Pengganti.
    """
    lang = target_language.lower()
    is_dart = "dart" in lang or "flutter" in lang
    is_py = "python" in lang
    eco = "dart" if is_dart else ("python" if is_py else "javascript")

    packages = find_active_manifest_packages(eco, target_dir=target_dir)
    matched_rules = catalog.get_matching_rules(eco, packages) if catalog else []

    lines = [f"[ENVIRONMENT FACT CARD — RUNTIME CONSTRAINTS ({target_language.upper()})]"]

    # Fakta Runtime
    if is_dart:
        dart_v = _get_dart_sdk_version()
        flutter_v = _get_flutter_version()
        if dart_v:
            lines.append(f"Runtime: Dart SDK {dart_v}")
        if flutter_v:
            lines.append(f"Framework: Flutter {flutter_v}")
        if "flutter_riverpod" in packages:
            lines.append(f"Package: flutter_riverpod=={packages['flutter_riverpod']} AKTIF")
    elif is_py:
        lines.append(f"Runtime: Python {sys.version.split()[0]}")
        for p in ["fastapi", "pydantic", "pytest"]:
            if p in packages:
                lines.append(f"Package: {p}=={packages[p]} AKTIF")

    lines.append("")
    lines.append("ATURAN PRESEDEN TINGGI (AUTHORITATIVE PRECEDENCE):")
    lines.append(
        "Jika Rencana Arsitektur merekomendasikan API, kelas, atau pustaka yang BERTENTANGAN dengan "
        "FACT CARD di bawah ini, FACT CARD MUTLAK MENGALAHKAN ARSITEKTUR. Patuhi FACT CARD 100%."
    )
    lines.append("")

    lines.append("ATURAN IMPLEMENTASI & POLA KANONIKAL:")
    for r in matched_rules:
        lines.append(f"• Pustaka {r.package}:")
        if r.developer_instruction:
            lines.append(f"  {r.developer_instruction}")
        if r.prohibited_patterns:
            lines.append(f"  DILARANG MENGGUNAKAN SIMBOL INI: {', '.join(r.prohibited_patterns)}")
        if r.positive_template:
            lines.append("  POLA KANONIKAL YANG WAJIB DIGUNAKAN:")
            for t_line in r.positive_template.strip().split("\n"):
                lines.append(f"    {t_line}")
        lines.append("")

    if dynamic_facts:
        lines.append("FAKTA KEGAGALAN DARI PUTARAN SEBELUMNYA (JANGAN DIULANG):")
        for df in dynamic_facts:
            lines.append(f"• {df}")
        lines.append("")

    return "\n".join(lines)


def generate_fact_card(
    target_language: str,
    task: str = "",
    target_dir: Optional[str] = None,
) -> str:
    """
    Fungsi kompatibilitas ke belakang (backwards-compatible).
    Secara default menghasilkan Developer Fact Card.
    """
    return generate_fact_card_for_developer(
        target_language=target_language,
        task=task,
        target_dir=target_dir,
    )
