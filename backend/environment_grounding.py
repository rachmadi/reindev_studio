"""
environment_grounding.py
========================
Memeriksa fakta aktual environment lokal dan menghasilkan "Environment Fact Card"
yang disuntikkan ke prompt Developer agent sebelum ia mulai menulis kode.

Tujuan:
  Mengompensasi keterbatasan knowledge cutoff model LLM lokal (qwen2.5-coder:7b)
  dengan memberi akses langsung ke versi package yang BENAR-BENAR terpasang
  di environment saat ini — bukan versi yang "dihafal" model dari training data.

Kelas Kegagalan yang Ditangani:
  - Kelas A (Version/API): Model memakai deprecated API karena tidak tahu versi env
  - Kelas B (Framework Nuance): Kombinasi versi FastAPI + Pydantic v1 vs v2
  - (Kelas C — architectural reasoning — tetap ditangani di prompt & executor)
"""

import json
import re
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from typing import Optional

# Root workspace — resolusi dari lokasi file ini (backend/)
_BACKEND_DIR = Path(__file__).parent
_WORKSPACE_DIR = _BACKEND_DIR.parent
_VENV_PYTHON = _BACKEND_DIR / ".venv" / ("Scripts" if sys.platform == "win32" else "bin") / "python"


# ---------------------------------------------------------------------------
# Package version lookup helpers
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _get_installed_packages() -> dict[str, str]:
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


def _pkg_version(name: str) -> Optional[str]:
    """Kembalikan versi package `name` yang terpasang, atau None jika tidak ditemukan."""
    return _get_installed_packages().get(name.lower())


def _major(version: Optional[str]) -> Optional[int]:
    """Ekstrak major version integer dari string versi semver."""
    if not version:
        return None
    m = re.match(r"(\d+)", version)
    return int(m.group(1)) if m else None


# ---------------------------------------------------------------------------
# Dart / Flutter version lookup helpers
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _get_flutter_riverpod_version() -> Optional[str]:
    """
    Baca versi flutter_riverpod dari pubspec.lock di workspace.
    Ini lebih reliable daripada `flutter pub deps` karena tidak perlu pub get.
    """
    lock_candidates = [
        _WORKSPACE_DIR / "frontend" / "pubspec.lock",
        _WORKSPACE_DIR / "pubspec.lock",
        _WORKSPACE_DIR / "app" / "pubspec.lock",
    ]
    for lock_path in lock_candidates:
        if lock_path.exists():
            try:
                text = lock_path.read_text(encoding="utf-8", errors="replace")
                # Format pubspec.lock (YAML):
                #   flutter_riverpod:
                #     dependency: "direct main"
                #     description:
                #       name: flutter_riverpod
                #       ...
                #     source: hosted
                #     version: "3.4.3"
                # Strategi: ambil blok teks antara "flutter_riverpod:" dan package berikutnya
                m = re.search(
                    r'flutter_riverpod:\s*\n((?:[ \t]+[^\n]*\n)*)',
                    text
                )
                if m:
                    block = m.group(1)
                    v = re.search(r'version:\s*["\']?([0-9][^\s"\']+)["\']?', block)
                    if v:
                        return v.group(1).strip()
            except Exception:
                pass
    return None


@lru_cache(maxsize=1)
def _get_dart_sdk_version() -> Optional[str]:
    """Jalankan `dart --version` untuk mendapatkan versi Dart SDK aktual."""
    dart_bin = "dart"
    try:
        result = subprocess.run(
            [dart_bin, "--version"],
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
    flutter_bin = "flutter"
    try:
        result = subprocess.run(
            [flutter_bin, "--version", "--machine"],
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
# Fact Card Generator
# ---------------------------------------------------------------------------

def generate_python_fact_card(task: str = "") -> str:
    """
    Hasilkan Environment Fact Card untuk stack Python.
    Berisi versi package kritis dan aturan API yang harus dipatuhi Developer.
    """
    pkgs = _get_installed_packages()
    is_fastapi = any(k in task.lower() for k in ["fastapi", "rest", "api", "crud", "endpoint", "inventaris"]) if task else True

    fastapi_v = _pkg_version("fastapi")
    pydantic_v = _pkg_version("pydantic")
    pytest_v = _pkg_version("pytest")
    starlette_v = _pkg_version("starlette")
    uvicorn_v = _pkg_version("uvicorn")
    httpx_v = _pkg_version("httpx")

    pydantic_major = _major(pydantic_v)
    fastapi_major = _major(fastapi_v)

    lines = ["[ENVIRONMENT FACTS — PYTHON STACK]"]
    lines.append(f"Python runtime: {sys.version.split()[0]}")

    if is_fastapi and fastapi_v:
        lines.append(f"fastapi=={fastapi_v}")
    if is_fastapi and pydantic_v:
        lines.append(f"pydantic=={pydantic_v}")
    if pytest_v:
        lines.append(f"pytest=={pytest_v}")
    if is_fastapi and uvicorn_v:
        lines.append(f"uvicorn=={uvicorn_v}")
    if is_fastapi and httpx_v:
        lines.append(f"httpx=={httpx_v}")

    lines.append("")
    lines.append("ATURAN API BERDASARKAN VERSI TERDETEKSI:")

    # --- Pydantic rules ---
    if is_fastapi:
        if pydantic_major == 2:
            lines += [
                "• pydantic v2 AKTIF:",
                "  - Field id WAJIB optional: `id: int | None = None` (bukan `id: int`)",
                "  - Validator: gunakan `@field_validator` (bukan `@validator`)",
                "  - Config: gunakan `model_config = ConfigDict(...)` (bukan class Config)",
                "  - `orm_mode` diganti `from_attributes = True`",
            ]
        elif pydantic_major == 1:
            lines += [
                "• pydantic v1 AKTIF:",
                "  - Validator: gunakan `@validator` (bukan `@field_validator`)",
                "  - Config: gunakan inner `class Config: orm_mode = True`",
            ]

    # --- FastAPI rules ---
    if is_fastapi and fastapi_v:
        lines += [
            f"• fastapi=={fastapi_v} AKTIF:",
            "  - POST endpoint WAJIB: `@app.post('/path/', status_code=201)`",
            "  - DELETE endpoint: `status_code=204`, raise HTTPException(404) jika tidak ada",
            "  - GET single: raise HTTPException(status_code=404, detail='Not found') jika tidak ada",
            "  - Test: gunakan `from fastapi.testclient import TestClient` (bukan Flask test_client)",
        ]

    # --- pytest rules ---
    if pytest_v:
        lines += [
            f"• pytest=={pytest_v} AKTIF:",
            "  - Gunakan `pytest.raises(ExceptionType)` untuk test exception",
        ]
        if is_fastapi:
            lines.append("  - DILARANG: `app.test_client()` (Flask) — gunakan TestClient FastAPI")

    return "\n".join(lines)

    return "\n".join(lines)


def generate_dart_fact_card() -> str:
    """
    Hasilkan Environment Fact Card untuk stack Dart/Flutter.
    """
    riverpod_v = _get_flutter_riverpod_version()
    dart_v = _get_dart_sdk_version()
    flutter_v = _get_flutter_version()

    riverpod_major = _major(riverpod_v)

    lines = ["[ENVIRONMENT FACTS — DART/FLUTTER STACK]"]

    if dart_v:
        lines.append(f"Dart SDK: {dart_v}")
    if flutter_v:
        lines.append(f"Flutter: {flutter_v}")
    if riverpod_v:
        lines.append(f"flutter_riverpod: {riverpod_v}")

    lines.append("")
    lines.append("ATURAN API BERDASARKAN VERSI TERDETEKSI:")

    # --- Riverpod rules ---
    if riverpod_major is not None and riverpod_major >= 2:
        lines += [
            f"• flutter_riverpod=={riverpod_v} (v{riverpod_major}.x) AKTIF:",
            "  - StateNotifier TIDAK ADA di versi ini — JANGAN gunakan StateNotifier",
            "  - StateProvider DEPRECATED — JANGAN gunakan StateProvider",
            "  - GUNAKAN: `Provider<T>((ref) => ...)` untuk state yang tidak berubah",
            "  - GUNAKAN: `StateNotifierProvider` + `StateNotifier` HANYA di riverpod <2.0",
            "  - Widget: gunakan `ConsumerWidget` dengan `Widget build(BuildContext context, WidgetRef ref)`",
            "  - Provider declaration: `final myProvider = Provider<MyType>((ref) => MyType());`",
        ]
    elif riverpod_v:
        lines += [
            f"• flutter_riverpod=={riverpod_v} (v1.x) AKTIF:",
            "  - StateNotifier tersedia, tapi pertimbangkan migrasi ke Notifier API",
            "  - Gunakan `ConsumerWidget` untuk widget yang membaca provider",
        ]
    else:
        lines += [
            "• flutter_riverpod: versi tidak terdeteksi dari pubspec.lock",
            "  - Asumsikan v2+ (modern) — JANGAN gunakan StateNotifier atau StateProvider",
            "  - Gunakan Provider<T> murni untuk state management sederhana",
        ]

    # --- Dart SDK rules ---
    if dart_v:
        dart_major = _major(dart_v)
        if dart_major and dart_major >= 3:
            lines += [
                f"• Dart SDK {dart_v} (v3+):",
                "  - Sound Null Safety WAJIB (semua field harus ada nilai default atau nullable)",
                "  - Gunakan `?` untuk nullable, `!` hanya jika dijamin non-null",
                "  - Record types tersedia: `(int, String)` sebagai return type sederhana",
            ]

    return "\n".join(lines)


def generate_fact_card(target_language: str, task: str = "") -> str:
    """
    Entry point utama.
    Hasilkan fact card yang sesuai berdasarkan target_language dan context task.

    Args:
        target_language: "python", "dart", "flutter", dll.
        task: String deskripsi tugas pengguna (opsional).

    Returns:
        String fact card siap suntik ke prompt Developer.
    """
    lang = target_language.lower()
    if "dart" in lang or "flutter" in lang:
        return generate_dart_fact_card()
    else:
        return generate_python_fact_card(task=task)
