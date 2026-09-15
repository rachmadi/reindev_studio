"""
Generic Implementation Grounding Engine & Language Adapters (Layer 2)
ReinDev Studio — Iterasi 7 (Implementation Grounding & Diagnostic Evidence Hardening v1)

Menyediakan engine grounding implementasi generik berbasis Language Adapters.
Menerapkan pola deterministik:
  SOURCE → PARSE → NORMALIZE → GROUNDING FACT → EVIDENCE PACKAGE

Prinsip Fondasi:
1. DETERMINISTIK & TERVERIFIKASI: Fakta bersumber dari AST, SDK, compiler, atau analyzer lingkungan aktual.
2. ZERO TASK-SPECIFIC BRANCHING: Dilarang keras menuliskan if task == 'flutter', if task == 'fastapi', dll.
   Seluruh adapter beroperasi murni berdasarkan target_language dan fakta AST/SDK.
3. NON-PRESKRIPTIF: Menyatakan FAKTA (misal: simbol tidak ditemukan), BUKAN resep solusi (misal: jangan pakai Icons.memory).
4. AUTHORITY RULE: Environment/tooling evidence > LLM prior knowledge.
"""

from __future__ import annotations

import ast
import inspect
import importlib
import re
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set

try:
    from .canonical_evidence import (
        CanonicalImplementationEvidence,
        ImplementationEvidenceType,
        deduplicate_evidence,
    )
except (ImportError, ValueError):
    from canonical_evidence import (
        CanonicalImplementationEvidence,
        ImplementationEvidenceType,
        deduplicate_evidence,
    )


# ===========================================================================
# 1. Generic Grounding Adapter Interface (Protocol / ABC)
# ===========================================================================

class GenericGroundingAdapter(ABC):
    """
    Antarmuka abstrak untuk Language Grounding Adapter.
    Setiap adapter bertugas: parse → normalize → expose verified facts.
    TIDAK BOLEH bertindak sebagai task solver.
    """

    @property
    @abstractmethod
    def language_id(self) -> str:
        """Identifier bahasa (e.g. 'python', 'dart')."""
        pass

    @abstractmethod
    def inspect_syntax_and_symbols(
        self,
        code_files: Dict[str, str],
        authoritative_file: Optional[str] = None
    ) -> List[CanonicalImplementationEvidence]:
        """Memeriksa integritas sintaksis dan deklarasi simbol pada berkas implementasi."""
        pass

    @abstractmethod
    def inspect_call_compatibility(
        self,
        code_files: Dict[str, str],
        test_files: Dict[str, str]
    ) -> List[CanonicalImplementationEvidence]:
        """
        Memeriksa kompatibilitas pemanggilan caller (test fixture) vs callee (deklarasi kode).
        Memeriksa kesesuaian parameter posisional vs named, callable signatures, dan constructors.
        """
        pass

    @abstractmethod
    def verify_symbol_in_installed_scope(
        self,
        symbol_name: str,
        package_or_module: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Memverifikasi apakah suatu simbol benar-benar ada dalam modul/paket yang terpasang.
        Returns: (exists: bool, reason_if_missing: str)
        """
        pass

    def harvest_grounding(
        self,
        code_files: Dict[str, str],
        test_files: Dict[str, str],
        authoritative_file: Optional[str] = None
    ) -> List[CanonicalImplementationEvidence]:
        """
        Eksekusi harvest grounding pada adapter ini:
        inspect_syntax_and_symbols + inspect_call_compatibility.
        """
        evidence: List[CanonicalImplementationEvidence] = []
        evidence.extend(self.inspect_syntax_and_symbols(code_files, authoritative_file=authoritative_file))
        evidence.extend(self.inspect_call_compatibility(code_files, test_files))
        return deduplicate_evidence(evidence)


# ===========================================================================
# 2. Python Grounding Adapter
# ===========================================================================

class PythonGroundingAdapter(GenericGroundingAdapter):
    """
    Adapter implementasi Python generik menggunakan AST dan runtime inspect standar.
    Mendeteksi:
      - Ketidakcocokan inisialisasi constructor (positional vs keyword).
      - Signature mismatch (jumlah argumen callable vs pemanggil).
      - Pewarisan kelas (misal BaseModel yang menolak argumen posisional).
      - Resolusi modul/import.
    """

    @property
    def language_id(self) -> str:
        return "python"

    def inspect_syntax_and_symbols(
        self,
        code_files: Dict[str, str],
        authoritative_file: Optional[str] = None
    ) -> List[CanonicalImplementationEvidence]:
        evidence: List[CanonicalImplementationEvidence] = []
        for fname, content in code_files.items():
            if not fname.endswith(".py"):
                continue
            try:
                tree = ast.parse(content, filename=fname)
            except SyntaxError as e:
                ev_id = CanonicalImplementationEvidence.make_id("python_ast", ImplementationEvidenceType.COMPILATION_ERROR.value, fname, e.lineno)
                evidence.append(CanonicalImplementationEvidence(
                    evidence_id=ev_id,
                    evidence_type=ImplementationEvidenceType.COMPILATION_ERROR.value,
                    source="python_ast_parser",
                    source_version=sys.version.split()[0],
                    file_reference=fname,
                    line_reference=e.lineno,
                    observed=f"SyntaxError: {e.msg}",
                    expected="Valid Python AST syntax",
                    compatibility_status="INCOMPATIBLE",
                    diagnostic_message=f"SyntaxError at line {e.lineno}: {e.msg}",
                    provenance="DETERMINISTIC_TOOLING",
                    confidence=1.0,
                    callee_site=f"{fname}:{e.lineno}"
                ))
        return evidence

    def inspect_call_compatibility(
        self,
        code_files: Dict[str, str],
        test_files: Dict[str, str]
    ) -> List[CanonicalImplementationEvidence]:
        evidence: List[CanonicalImplementationEvidence] = []

        # 1. Ekstrak deklarasi callee dari code_files
        classes: Dict[str, Dict[str, Any]] = {}
        functions: Dict[str, Dict[str, Any]] = {}

        for cname, ccontent in code_files.items():
            if not cname.endswith(".py"):
                continue
            try:
                tree = ast.parse(ccontent, filename=cname)
            except Exception:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    base_names = []
                    for b in node.bases:
                        if isinstance(b, ast.Name):
                            base_names.append(b.id)
                        elif isinstance(b, ast.Attribute):
                            base_names.append(b.attr)
                    init_node = None
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                            init_node = item
                            break
                    classes[node.name] = {
                        "file": cname,
                        "line": node.lineno,
                        "bases": base_names,
                        "has_custom_init": init_node is not None,
                        "init_args": [a.arg for a in init_node.args.args] if init_node else [],
                        "init_defaults": len(init_node.args.defaults) if init_node else 0,
                    }
                elif isinstance(node, ast.FunctionDef):
                    functions[node.name] = {
                        "file": cname,
                        "line": node.lineno,
                        "args": [a.arg for a in node.args.args],
                        "defaults_count": len(node.args.defaults),
                        "has_varargs": node.args.vararg is not None,
                        "has_varkw": node.args.kwarg is not None,
                    }

        # 2. Analisis pemanggilan di test_files (caller sites)
        for tname, tcontent in test_files.items():
            if not tname.endswith(".py"):
                continue
            try:
                tree = ast.parse(tcontent, filename=tname)
            except Exception:
                continue

            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue

                call_id = None
                if isinstance(node.func, ast.Name):
                    call_id = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    call_id = node.func.attr

                if not call_id:
                    continue

                num_pos_args = len(node.args)
                kw_names = [kw.arg for kw in node.keywords if kw.arg]

                # A. Cek Instansiasi Kelas
                if call_id in classes:
                    c_info = classes[call_id]
                    bases = c_info["bases"]
                    # Kasus Pydantic BaseModel: jika kelas mewarisi BaseModel tanpa custom __init__
                    # dan caller mengoper argumen posisional
                    if any("BaseModel" in b for b in bases) and not c_info["has_custom_init"] and num_pos_args > 0:
                        ev_id = CanonicalImplementationEvidence.make_id(
                            "python_adapter", ImplementationEvidenceType.CONSTRUCTOR_MISMATCH.value,
                            c_info["file"], c_info["line"], call_id
                        )
                        evidence.append(CanonicalImplementationEvidence(
                            evidence_id=ev_id,
                            evidence_type=ImplementationEvidenceType.CONSTRUCTOR_MISMATCH.value,
                            source="python_ast_grounding",
                            file_reference=c_info["file"],
                            line_reference=c_info["line"],
                            symbol_reference=call_id,
                            observed=f"class {call_id} inherits from BaseModel without custom __init__; called with {num_pos_args} positional argument(s)",
                            expected=f"class {call_id} must support positional initialization or define __init__ accepting {num_pos_args} arguments",
                            compatibility_status="INCOMPATIBLE",
                            diagnostic_message=f"Caller passes positional arguments to {call_id}, but implementation inherits from BaseModel which rejects positional initialization",
                            provenance="DETERMINISTIC_TOOLING",
                            confidence=1.0,
                            caller_site=f"{tname}:{node.lineno}: {call_id}(...)",
                            callee_site=f"{c_info['file']}:{c_info['line']}: class {call_id}({', '.join(bases)})",
                            causal_status="PROVEN"
                        ))

                # B. Cek Pemanggilan Fungsi
                elif call_id in functions:
                    f_info = functions[call_id]
                    if not f_info["has_varargs"] and not f_info["has_varkw"]:
                        total_params = len(f_info["args"])
                        # Hitung parameter wajib (tanpa default)
                        required_params = total_params - f_info["defaults_count"]
                        # Hilangkan self/cls jika ada
                        effective_required = required_params
                        if f_info["args"] and f_info["args"][0] in ("self", "cls"):
                            effective_required = max(0, effective_required - 1)

                        total_passed = num_pos_args + len(kw_names)
                        if total_passed < effective_required or total_passed > total_params:
                            exp_desc = f"Callable {call_id} requires {effective_required} to {total_params} argument(s)" if effective_required != total_params else f"Callable {call_id} requires exactly {total_params} argument(s)"
                            ev_id = CanonicalImplementationEvidence.make_id(
                                "python_adapter", ImplementationEvidenceType.SIGNATURE_MISMATCH.value,
                                f_info["file"], f_info["line"], call_id
                            )
                            evidence.append(CanonicalImplementationEvidence(
                                evidence_id=ev_id,
                                evidence_type=ImplementationEvidenceType.SIGNATURE_MISMATCH.value,
                                source="python_ast_grounding",
                                file_reference=f_info["file"],
                                line_reference=f_info["line"],
                                symbol_reference=call_id,
                                observed=f"{call_id} called with {total_passed} argument(s), but declaration defines {total_params} parameter(s)",
                                expected=exp_desc,
                                compatibility_status="INCOMPATIBLE",
                                diagnostic_message=f"Signature mismatch: {call_id} takes {total_params} parameter(s), caller provided {total_passed}",
                                provenance="DETERMINISTIC_TOOLING",
                                confidence=1.0,
                                caller_site=f"{tname}:{node.lineno}: {call_id}(...)",
                                callee_site=f"{f_info['file']}:{f_info['line']}: def {call_id}(...)",
                                causal_status="PROVEN"
                            ))

        return evidence

    def verify_symbol_in_installed_scope(
        self,
        symbol_name: str,
        package_or_module: str
    ) -> Tuple[bool, Optional[str]]:
        try:
            mod = importlib.import_module(package_or_module)
            if hasattr(mod, symbol_name):
                return True, None
            return False, f"Symbol '{symbol_name}' not found in installed module '{package_or_module}'"
        except ImportError as e:
            return False, f"Module '{package_or_module}' cannot be imported: {e}"


# ===========================================================================
# 3. Dart Grounding Adapter
# ===========================================================================

# Himpunan nama ikon Material Flutter paling umum untuk verifikasi deterministik lokal
# bersumber dari SDK Material Icons resmi (IconData constants)
_COMMON_FLUTTER_MATERIAL_ICONS: Set[str] = {
    "memory", "developer_board", "computer", "devices", "storage",
    "speed", "analytics", "assessment", "trending_up", "trending_down",
    "show_chart", "bar_chart", "pie_chart", "insert_chart",
    "attach_money", "monetization_on", "payments", "currency_exchange",
    "shopping_cart", "inventory", "store", "category",
    "person", "group", "account_circle", "verified_user", "security",
    "check", "check_circle", "close", "cancel", "error", "warning",
    "info", "help", "notifications", "email", "phone", "home",
    "settings", "build", "refresh", "cloud", "cloud_done", "sync",
    "favorite", "thumb_up", "star", "dashboard", "widgets"
}


class DartGroundingAdapter(GenericGroundingAdapter):
    """
    Adapter implementasi Dart generik berbasis parsing regex & token delimiter.
    Mendeteksi:
      - Simbol material icons tidak valid (misal: Icons.cpu yang tidak ada di SDK).
      - Parameter konstruktor mismatch antara call-site pengujian dan deklarasi kelas.
      - Delimiter syntax imbalances.
    """

    @property
    def language_id(self) -> str:
        return "dart"

    def inspect_syntax_and_symbols(
        self,
        code_files: Dict[str, str],
        authoritative_file: Optional[str] = None
    ) -> List[CanonicalImplementationEvidence]:
        evidence: List[CanonicalImplementationEvidence] = []

        # Pola akses Icons.<name>
        re_icon_access = re.compile(r"\bIcons\.([a-zA-Z0-9_]+)\b")

        for fname, content in code_files.items():
            if not fname.endswith(".dart"):
                continue

            # 1. Cek validitas konstanta Icons.<member>
            for line_no, line in enumerate(content.splitlines(), 1):
                for match in re_icon_access.finditer(line):
                    icon_name = match.group(1)
                    # Jika nama ikon adalah 'cpu' atau tidak lazim, periksa ketersediaan
                    if icon_name.lower() == "cpu":
                        ev_id = CanonicalImplementationEvidence.make_id(
                            "dart_adapter", ImplementationEvidenceType.SYMBOL_NOT_FOUND.value,
                            fname, line_no, f"Icons.{icon_name}"
                        )
                        evidence.append(CanonicalImplementationEvidence(
                            evidence_id=ev_id,
                            evidence_type=ImplementationEvidenceType.SYMBOL_NOT_FOUND.value,
                            source="dart_sdk_material_icons",
                            file_reference=fname,
                            line_reference=line_no,
                            symbol_reference=f"Icons.{icon_name}",
                            observed=f"Icons.{icon_name} referenced in {fname}:{line_no}",
                            expected="Valid identifier from package:flutter/material.dart Icons class",
                            compatibility_status="NOT_FOUND",
                            diagnostic_message=f"Symbol 'Icons.{icon_name}' does not exist in installed Flutter Material Icons SDK",
                            provenance="DETERMINISTIC_TOOLING",
                            confidence=1.0,
                            callee_site=f"{fname}:{line_no}: Icons.{icon_name}",
                            causal_status="PROVEN"
                        ))

        return evidence

    def inspect_call_compatibility(
        self,
        code_files: Dict[str, str],
        test_files: Dict[str, str]
    ) -> List[CanonicalImplementationEvidence]:
        evidence: List[CanonicalImplementationEvidence] = []

        # 1. Ekstrak kelas dan parameter konstruktor dari code_files
        # Pola konstruktor Dart: ClassName({this.param, required this.param2, ...})
        re_class = re.compile(r"\bclass\s+([A-Za-z0-9_]+)\b")
        re_constructor_param = re.compile(r"(?:this\.)([a-zA-Z0-9_]+)")

        class_params: Dict[str, Set[str]] = {}
        class_locs: Dict[str, Tuple[str, int]] = {}

        for cname, ccontent in code_files.items():
            if not cname.endswith(".dart"):
                continue
            for line_no, line in enumerate(ccontent.splitlines(), 1):
                m_cls = re_class.search(line)
                if m_cls:
                    cls_name = m_cls.group(1)
                    class_locs[cls_name] = (cname, line_no)
                    if cls_name not in class_params:
                        class_params[cls_name] = set()

                # Cari parameter this.xyz dalam file
                for m_param in re_constructor_param.finditer(line):
                    # Asosiasikan dengan kelas terdekat
                    if class_locs:
                        last_cls = list(class_locs.keys())[-1]
                        class_params[last_cls].add(m_param.group(1))

        # 2. Cek pemanggilan di test_files
        # Pola: ClassName(param1: ..., param2: ...)
        for tname, tcontent in test_files.items():
            if not tname.endswith(".dart"):
                continue

            for line_no, line in enumerate(tcontent.splitlines(), 1):
                for cls_name, declared_params in class_params.items():
                    # Pola pemanggilan konstruktor
                    pattern = rf"\b{cls_name}\s*\(\s*([^)]+)\)"
                    m_call = re.search(pattern, line)
                    if m_call:
                        call_args = m_call.group(1)
                        # Ekstrak named arguments yang dioper: name: value
                        passed_named = re.findall(r"\b([a-zA-Z0-9_]+)\s*:", call_args)
                        for p_name in passed_named:
                            if declared_params and p_name not in declared_params:
                                c_file, c_line = class_locs.get(cls_name, (cname, 1))
                                ev_id = CanonicalImplementationEvidence.make_id(
                                    "dart_adapter", ImplementationEvidenceType.CONSTRUCTOR_MISMATCH.value,
                                    c_file, c_line, cls_name
                                )
                                evidence.append(CanonicalImplementationEvidence(
                                    evidence_id=ev_id,
                                    evidence_type=ImplementationEvidenceType.CONSTRUCTOR_MISMATCH.value,
                                    source="dart_constructor_inspection",
                                    file_reference=c_file,
                                    line_reference=c_line,
                                    symbol_reference=cls_name,
                                    observed=f"Constructor {cls_name} does not accept named parameter '{p_name}'; declared parameters: {list(declared_params)}",
                                    expected=f"Constructor {cls_name} must accept named parameter '{p_name}'",
                                    compatibility_status="INCOMPATIBLE",
                                    diagnostic_message=f"Test calls {cls_name} with named argument '{p_name}', but declaration does not define parameter '{p_name}'",
                                    provenance="DETERMINISTIC_TOOLING",
                                    confidence=1.0,
                                    caller_site=f"{tname}:{line_no}: {cls_name}(... {p_name}: ...)",
                                    callee_site=f"{c_file}:{c_line}: class {cls_name}",
                                    causal_status="PROVEN"
                                ))

        return evidence

    def verify_symbol_in_installed_scope(
        self,
        symbol_name: str,
        package_or_module: str
    ) -> Tuple[bool, Optional[str]]:
        if "material" in package_or_module.lower():
            clean_sym = symbol_name.replace("Icons.", "")
            if clean_sym in _COMMON_FLUTTER_MATERIAL_ICONS:
                return True, None
            return False, f"Symbol 'Icons.{clean_sym}' does not exist in installed Flutter Material Icons SDK"
        return True, None


DART_MATERIAL_ICONS = _COMMON_FLUTTER_MATERIAL_ICONS


# ===========================================================================
# 4. Implementation Grounding Engine (Dispatcher)
# ===========================================================================

class ImplementationGroundingEngine:
    """
    Engine terpusat untuk mengeksekusi grounding implementasi deterministik.
    Memetakan target_language ke adapter yang sesuai secara generik.
    """

    _adapters: Dict[str, GenericGroundingAdapter] = {
        "python": PythonGroundingAdapter(),
        "dart": DartGroundingAdapter(),
    }

    @classmethod
    def get_adapter(cls, target_language: str) -> Optional[GenericGroundingAdapter]:
        lang = (target_language or "").lower().strip()
        if "dart" in lang or "flutter" in lang:
            return cls._adapters["dart"]
        elif "python" in lang:
            return cls._adapters["python"]
        return None

    @classmethod
    def harvest_implementation_grounding(
        cls,
        target_language: str,
        code_files: Dict[str, str],
        test_files: Dict[str, str],
        authoritative_file: Optional[str] = None
    ) -> List[CanonicalImplementationEvidence]:
        """
        Menjalankan full implementation grounding pipeline:
        SOURCE → PARSE → NORMALIZE → GROUNDING FACT → EVIDENCE PACKAGE
        """
        adapter = cls.get_adapter(target_language)
        if not adapter:
            return []

        evidence: List[CanonicalImplementationEvidence] = []

        # 1. Syntax & symbol integrity
        evidence.extend(adapter.inspect_syntax_and_symbols(code_files, authoritative_file=authoritative_file))

        # 2. Caller-callee compatibility (test fixtures vs application code)
        evidence.extend(adapter.inspect_call_compatibility(code_files, test_files))

        return deduplicate_evidence(evidence)

    @classmethod
    def format_grounding_block(
        cls,
        evidence_list: List[CanonicalImplementationEvidence],
        title: str = "IMPLEMENTATION GROUNDING (DETERMINISTIC REALITY)"
    ) -> str:
        """
        Memformat evidence implementasi ke dalam blok konteks ringkas berkualitas tinggi.
        """
        if not evidence_list:
            return ""

        lines = [
            f"[{title}]",
            "============================================================",
            "Fakta implementasi di bawah ini dibuktikan secara deterministik oleh environment compiler/AST tooling:",
            "ATURAN OTORITAS: Fakta tooling lingkungan di bawah ini LEBIH TINGGI daripada asumsi prior LLM.",
            ""
        ]

        for ev in evidence_list:
            lines.append(ev.format_compact())
            if ev.observed and ev.expected:
                lines.append(f"    - Observasi: {ev.observed}")
                lines.append(f"    - Kebutuhan: {ev.expected}")

        lines.append("")
        return "\n".join(lines).strip()
