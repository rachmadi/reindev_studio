"""
Canonical Symbol Resolution Module
ReinDev Studio — Architecture Hardening v2

Mekanisme resolusi simbol kanonikal universal berbasis tata bahasa (grammar-aware, task-agnostic).
Digunakan secara konsisten oleh:
- Developer Phase-End Validator (phase_validators.py)
- Reviewer Gate (reviewer.py)
- Locked Invariants Tracker (locked_invariants.py)

Mendukung:
- Kelas (dengan ekstraksi parameter konstruktor)
- Fungsi/Metode blok
- Ekspresi fungsi panah (arrow expressions `=>`)
- Getter & Setter
- Deklarasi tingkat modul/top-level (final, const, var, late, assignment)
- Impor pustaka
"""

import ast
import re
import textwrap
from dataclasses import dataclass, field
from typing import Dict, List, Set, Any, Optional


@dataclass
class CanonicalSymbolResolution:
    """Representasi kanonikal simbol hasil pemindaian kode."""
    classes: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    functions: List[str] = field(default_factory=list)
    top_level_declarations: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)

    @property
    def class_names(self) -> List[str]:
        return list(self.classes.keys())

    @property
    def all_symbols(self) -> Set[str]:
        return set(self.class_names) | set(self.functions) | set(self.top_level_declarations)

    def to_legacy_dict(self) -> Dict[str, List[str]]:
        """
        Kamus backward-compatible untuk pemanggil legasi.
        'functions' memuat gabungan fungsi dan deklarasi top-level
        agar pemanggil yang memeriksa `classes + functions` memperoleh seluruh simbol publik.
        """
        all_funcs_and_vars = sorted(list(set(self.functions) | set(self.top_level_declarations)))
        return {
            "classes": self.class_names,
            "functions": all_funcs_and_vars,
            "imports": sorted(list(set(self.imports))),
            "top_level_declarations": sorted(list(set(self.top_level_declarations))),
        }


# ===========================================================================
# 1. Grammar-Aware Python Scanner
# ===========================================================================

def _scan_python_symbols(code_content: str) -> CanonicalSymbolResolution:
    """Pemindai simbol Python berbasis ast.parse dengan ekstraksi komprehensif."""
    res = CanonicalSymbolResolution()
    try:
        tree = ast.parse(textwrap.dedent(code_content))
    except SyntaxError:
        return res

    for node in tree.body:
        # A. Class definitions
        if isinstance(node, ast.ClassDef):
            params: Set[str] = set()
            methods: List[str] = []
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                    params = {arg.arg for arg in item.args.args if arg.arg != "self"}
                    for kw in getattr(item.args, "kwonlyargs", []):
                        params.add(kw.arg)
                elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.append(item.name)
                    res.functions.append(item.name)
            res.classes[node.name] = {
                "parameters": sorted(list(params)),
                "methods": sorted(methods),
            }

        # B. Module-level Functions
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            res.functions.append(node.name)

        # C. Module-level Variable Assignments (Top-level declarations)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    res.top_level_declarations.append(target.id)
                elif isinstance(target, (ast.Tuple, ast.List)):
                    for elt in target.elts:
                        if isinstance(elt, ast.Name):
                            res.top_level_declarations.append(elt.id)

        # D. Module-level Annotated Variable Assignments (e.g. `x: int = 1` or `app: FastAPI`)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                res.top_level_declarations.append(node.target.id)

        # E. Imports
        elif isinstance(node, ast.Import):
            for alias in node.names:
                res.imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            for alias in node.names:
                res.imports.append(f"{mod}.{alias.name}" if mod else alias.name)

    # Walk remaining nested nodes for functions if any
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name not in res.functions:
                res.functions.append(node.name)

    return res


# ===========================================================================
# 2. Grammar-Aware Dart / Flutter Scanner
# ===========================================================================

def _scan_dart_symbols(code_content: str) -> CanonicalSymbolResolution:
    """Pemindai simbol Dart/Flutter gramatikal bebas solver."""
    res = CanonicalSymbolResolution()

    # A. Classes & Constructors
    class_matches = re.finditer(
        r"\bclass\s+([A-Za-z0-9_]+)(?:\s+extends\s+[A-Za-z0-9_<>]+)?(?:\s+with\s+[A-Za-z0-9_<,\s>]+)?(?:\s+implements\s+[A-Za-z0-9_<,\s>]+)?\s*\{",
        code_content
    )
    for m in class_matches:
        cname = m.group(1)
        ctor_pattern = rf"\b(?:const\s+)?{cname}\s*\(([^)]*)\)"
        ctor_match = re.search(ctor_pattern, code_content)
        params: Set[str] = set()
        if ctor_match:
            raw_params = ctor_match.group(1).strip()
            raw_params = re.sub(r"^[\{\[]|[\}\]]$", "", raw_params).strip()
            for p_item in raw_params.split(","):
                p_str = p_item.strip(" {}\r\n\t")
                if not p_str or p_str.startswith("super."):
                    continue
                this_match = re.search(r"\bthis\.([A-Za-z0-9_]+)", p_str)
                if this_match:
                    params.add(this_match.group(1))
                else:
                    var_match = re.search(r"(?:required\s+)?(?:[A-Za-z0-9_<>?]+\s+)?([A-Za-z0-9_]+)\s*$", p_str)
                    if var_match and var_match.group(1) not in ("key", "super"):
                        params.add(var_match.group(1))
        param_list = sorted(list(params))
        res.classes[cname] = {
            "parameters": param_list,
            "constructor_params": param_list,
        }

    # B. Block Functions / Methods
    func_brace_matches = re.findall(
        r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\([^)]*\)\s*(?:async\s*)?\{",
        code_content
    )
    for f in func_brace_matches:
        if f not in ("if", "for", "while", "switch", "catch"):
            res.functions.append(f)

    # C. Arrow Expressions (functions, methods, getters, setters)
    arrow_fn_matches = re.findall(
        r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\([^)]*\)\s*(?:async\s*)?=>",
        code_content
    )
    arrow_getter_matches = re.findall(
        r"\bget\s+([A-Za-z_][A-Za-z0-9_]*)\s*=>",
        code_content
    )
    arrow_setter_matches = re.findall(
        r"\bset\s+([A-Za-z_][A-Za-z0-9_]*)\s*\([^)]*\)\s*=>",
        code_content
    )
    for a in arrow_fn_matches + arrow_getter_matches + arrow_setter_matches:
        if a not in ("if", "for", "while", "switch", "catch", "async", "await", "return"):
            res.functions.append(a)

    # D. Block Getters & Setters
    getter_matches = re.findall(r"\bget\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{", code_content)
    setter_matches = re.findall(r"\bset\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", code_content)
    res.functions.extend(getter_matches)
    res.functions.extend(setter_matches)

    # E. Top-level Variable / Constant Declarations
    var_matches = re.findall(
        r"^\s*(?:late\s+)?(?:final|const|var)\s+(?:[A-Za-z_][A-Za-z0-9_]*(?:<[^>]+>)?\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*[=;]",
        code_content,
        re.MULTILINE
    )
    res.top_level_declarations.extend(var_matches)

    # F. Imports
    import_matches = re.findall(r"import\s+['\"]([^'\"]+)['\"]", code_content)
    res.imports.extend(import_matches)

    return res


# ===========================================================================
# 3. Universal Public API
# ===========================================================================

def scan_symbols_from_code(code_content: str, target_lang: str = "python") -> CanonicalSymbolResolution:
    """Mengekstrak simbol dari satu string kode berdasarkan bahasa target."""
    if not code_content:
        return CanonicalSymbolResolution()

    is_dart = any(k in target_lang.lower() for k in ("dart", "flutter"))
    if is_dart:
        return _scan_dart_symbols(code_content)
    else:
        return _scan_python_symbols(code_content)


def scan_symbols_from_files(code_files: Dict[str, str], target_lang: str = "python") -> CanonicalSymbolResolution:
    """Mengekstrak dan menggabungkan simbol dari kamus file kode."""
    combined = CanonicalSymbolResolution()
    if not code_files:
        return combined

    is_dart = any(k in target_lang.lower() for k in ("dart", "flutter"))

    for fname, content in code_files.items():
        if not content:
            continue
        file_is_dart = is_dart or fname.endswith(".dart")
        file_lang = "dart" if file_is_dart else target_lang

        file_res = scan_symbols_from_code(content, file_lang)
        combined.classes.update(file_res.classes)
        combined.functions.extend(file_res.functions)
        combined.top_level_declarations.extend(file_res.top_level_declarations)
        combined.imports.extend(file_res.imports)

    combined.functions = sorted(list(set(combined.functions)))
    combined.top_level_declarations = sorted(list(set(combined.top_level_declarations)))
    combined.imports = sorted(list(set(combined.imports)))

    return combined


def scan_code_symbols(code_files: Dict[str, str], target_lang: str = "python") -> Dict[str, List[str]]:
    """
    Fungsi kanonikal drop-in untuk menggantikan implementasi lama di phase_validators.py,
    reviewer.py, dan locked_invariants.py.
    """
    res = scan_symbols_from_files(code_files, target_lang)
    return res.to_legacy_dict()


def has_symbol(code_files: Dict[str, str], symbol_name: str, target_lang: str = "python") -> bool:
    """Memeriksa secara deterministik apakah suatu simbol terdefinisi di code_files."""
    res = scan_symbols_from_files(code_files, target_lang)
    return symbol_name in res.all_symbols
