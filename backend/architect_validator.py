"""
Architect Blueprint Validator (Generic Static Consistency Check)
ReinDev Studio — Iterasi 6

Memvalidasi cetak biru arsitektur (blueprint) secara deterministik sebelum kontrak disegel
dan sebelum kode diserahkan kepada Developer Agent.

Capability:
1. Python: Symbol / Import Resolution Consistency (decorator, base class, types).
2. Dart/Flutter: Declaration ↔ Invocation Consistency (constructors, named parameters, abstract classes).
"""

import ast
import re
import builtins
from typing import Tuple, List, Set, Dict, Any, Optional

try:
    from .blueprint_schema import (
        ArchitecturalBlueprint,
        parse_blueprint_json,
        extract_blueprint_json_text
    )
except (ImportError, ValueError):
    from blueprint_schema import (
        ArchitecturalBlueprint,
        parse_blueprint_json,
        extract_blueprint_json_text
    )


def _extract_code_blocks(text: str, language: str) -> List[str]:
    """Mengekstrak blok kode markdown untuk bahasa tertentu."""
    lang_clean = language.lower().strip()
    if lang_clean in ("python", "py"):
        pattern = r"```(?:python|py)\b(.*?)```"
    elif lang_clean in ("dart", "flutter"):
        pattern = r"```(?:dart|flutter)\b(.*?)```"
    else:
        pattern = rf"```{lang_clean}\b(.*?)```"
    
    blocks = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
    return [b.strip() for b in blocks if b.strip()]


def validate_python_code_ast(code: str, file_label: str = "Blok") -> List[str]:
    """
    Memeriksa keabsahan AST, resolusi dekorator, dan kelas basis pada sebuah modul kode Python.
    Memeriksa apakah decorator dan kelas basis yang digunakan memiliki resolusi yang jelas
    (ada di impor, deklarasi lokal, atau built-in Python).
    """
    errors: List[str] = []
    builtin_names: Set[str] = set(dir(builtins))
    common_types = {
        "Optional", "List", "Dict", "Set", "Tuple", "Any", "Union",
        "Callable", "Iterable", "Sequence", "Mapping", "TypeVar", "Generic"
    }

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        # Fallback analisis regex jika snippet terpotong atau memiliki syntax error
        dec_matches = re.findall(r"@([A-Za-z_][A-Za-z0-9_]*)", code)
        import_statements = re.findall(r"(?:from\s+[\w\.]+\s+import\s+([^;\n]+)|import\s+([^;\n]+))", code)
        imported_raw = set()
        for imp1, imp2 in import_statements:
            for item in (imp1 or imp2).split(","):
                name = item.strip().split(" as ")[-1].strip()
                if name:
                    imported_raw.add(name)
        
        for dec in dec_matches:
            if dec not in ("property", "classmethod", "staticmethod") and dec not in imported_raw:
                errors.append(
                    f"{file_label}: Simbol '@{dec}' digunakan sebagai decorator "
                    f"tetapi tidak ditemukan dalam statement import maupun deklarasi lokal."
                )
        if not errors:
            errors.append(f"{file_label} (baris {e.lineno}): SyntaxError pada kode Python: {e}")
        return errors

    imported_names: Set[str] = set()
    defined_names: Set[str] = set()
    used_decorators: List[Tuple[str, int]] = []
    used_bases: List[Tuple[str, str, int]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                imported_names.add(n.asname or n.name)
        elif isinstance(node, ast.ImportFrom):
            for n in node.names:
                imported_names.add(n.asname or n.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defined_names.add(node.name)
            for dec in node.decorator_list:
                if isinstance(dec, ast.Name):
                    used_decorators.append((dec.id, dec.lineno))
                elif isinstance(dec, ast.Call):
                    if isinstance(dec.func, ast.Name):
                        used_decorators.append((dec.func.id, dec.lineno))
                    elif isinstance(dec.func, ast.Attribute) and isinstance(dec.func.value, ast.Name):
                        used_decorators.append((dec.func.value.id, dec.lineno))
        elif isinstance(node, ast.ClassDef):
            defined_names.add(node.name)
            for dec in node.decorator_list:
                if isinstance(dec, ast.Name):
                    used_decorators.append((dec.id, dec.lineno))
                elif isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name):
                    used_decorators.append((dec.func.id, dec.lineno))
            for base in node.bases:
                if isinstance(base, ast.Name):
                    used_bases.append((node.name, base.id, node.lineno))
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    defined_names.add(target.id)
                elif isinstance(target, (ast.Tuple, ast.List)):
                    for elt in target.elts:
                        if isinstance(elt, ast.Name):
                            defined_names.add(elt.id)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                defined_names.add(node.target.id)

    available = imported_names | defined_names | builtin_names | common_types

    for dec_name, lineno in used_decorators:
        if dec_name not in available:
            errors.append(
                f"{file_label} (baris {lineno}): Simbol '@{dec_name}' digunakan sebagai decorator, "
                f"namun tidak ditemukan dalam statement import maupun deklarasi lokal."
            )

    for cls_name, base_name, lineno in used_bases:
        if base_name not in available:
            errors.append(
                f"{file_label} (baris {lineno}): Kelas basis '{base_name}' pada 'class {cls_name}({base_name})' "
                f"tidak ditemukan dalam statement import maupun deklarasi lokal."
            )

    return errors


def validate_python_blueprint_consistency(blueprint_text: str) -> Tuple[bool, List[str]]:
    """
    Memvalidasi konsistensi resolusi simbol dan impor pada snippet Python di dalam blueprint markdown warisan.
    Memeriksa apakah decorator dan kelas basis yang digunakan memiliki resolusi yang jelas.
    """
    errors: List[str] = []
    blocks = _extract_code_blocks(blueprint_text, "python")
    
    if not blocks:
        return True, []

    for block_idx, code in enumerate(blocks, 1):
        block_errs = validate_python_code_ast(code, file_label=f"Blok {block_idx}")
        errors.extend(block_errs)

    return len(errors) == 0, errors


def validate_dart_blueprint_consistency(blueprint_text: str) -> Tuple[bool, List[str]]:
    """
    Memvalidasi konsistensi deklarasi dan pemanggilan (Declaration ↔ Invocation) pada Dart/Flutter.
    Memeriksa:
    1. Instansiasi kelas yang dideklarasikan sebagai abstract.
    2. Parameter bernama yang dilewatkan saat instansiasi kelas lokal harus sesuai deklarasi constructor.
    """
    errors: List[str] = []
    blocks = _extract_code_blocks(blueprint_text, "dart")
    
    if not blocks:
        return True, []

    full_code = "\n\n".join(blocks)

    abstract_classes = set(re.findall(r"\babstract\s+class\s+([A-Za-z_][A-Za-z0-9_]*)", full_code))

    for ac in abstract_classes:
        for m in re.finditer(rf"\b{ac}\s*\(", full_code):
            start = max(0, m.start() - 30)
            before = full_code[start:m.start()]
            if not re.search(r"\b(?:factory|const)\s+$", before):
                errors.append(
                    f"Kelas '{ac}' dideklarasikan sebagai 'abstract class', tetapi diinstansiasi langsung pada blueprint."
                )
                break

    constructors: Dict[str, Dict[str, Any]] = {}
    for block in blocks:
        class_matches = re.finditer(r"\bclass\s+([A-Za-z_][A-Za-z0-9_]*)", block)
        for cm in class_matches:
            cname = cm.group(1)
            ctor_match = re.search(rf"\b{cname}\s*\(\s*\{{([^}}]*)\}}\s*\)", block)
            if ctor_match:
                params_str = ctor_match.group(1)
                declared_params: Set[str] = set()
                required_params: Set[str] = set()
                for p in params_str.split(","):
                    p_clean = p.strip()
                    if not p_clean:
                        continue
                    is_req = "required " in p_clean
                    name_match = re.search(r"(?:this\.)?([A-Za-z_][A-Za-z0-9_]*)(?:\s*=|$)", p_clean)
                    if name_match:
                        pname = name_match.group(1)
                        if pname not in ("required", "final", "super"):
                            declared_params.add(pname)
                            if is_req:
                                required_params.add(pname)
                constructors[cname] = {
                    "declared": declared_params,
                    "required": required_params
                }

    for cname, cinfo in constructors.items():
        declared = cinfo["declared"]
        call_pattern = rf"\b{cname}\s*\(\s*([^{{][^)]*)\)"
        for cm in re.finditer(call_pattern, full_code):
            args_str = cm.group(1).strip()
            named_args = re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*:", args_str)
            for arg in named_args:
                if arg not in declared and arg not in ("key",):
                    errors.append(
                        f"Parameter '{arg}' dilewatkan saat instansiasi '{cname}', "
                        f"tetapi tidak terdaftar pada deklarasi constructor {cname} {sorted(declared)}."
                    )

    return len(errors) == 0, errors


def legacy_validate_markdown_blueprint(blueprint_text: str, target_language: str) -> Tuple[bool, List[str]]:
    """Helper terisolasi untuk memvalidasi blueprint markdown warisan."""
    raw_str = str(blueprint_text or "")
    lang_clean = (target_language or "").lower().strip()
    if "python" in lang_clean or lang_clean in ("fastapi", "pytest"):
        return validate_python_blueprint_consistency(raw_str)
    elif "dart" in lang_clean or "flutter" in lang_clean:
        return validate_dart_blueprint_consistency(raw_str)
    return True, []


def validate_json_blueprint(blueprint_input: Any, target_language: str = "python") -> Tuple[bool, List[str]]:
    """
    Memvalidasi ArchitecturalBlueprint terstruktur berbasis JSON.
    Mengevaluasi skema Pydantic ketat dan konsistensi AST per berkas scaffold utuh.
    """
    if isinstance(blueprint_input, ArchitecturalBlueprint):
        bp = blueprint_input
    elif isinstance(blueprint_input, dict):
        try:
            bp = ArchitecturalBlueprint.model_validate(blueprint_input)
        except Exception as e:
            return False, [f"SCHEMA_VIOLATION: Skema ArchitecturalBlueprint tidak valid: {e}"]
    else:
        bp, err = parse_blueprint_json(str(blueprint_input))
        if bp is None:
            return False, [f"SCHEMA_VIOLATION: {err or 'Format JSON blueprint tidak dapat diproses'}"]

    errors: List[str] = []
    if not bp.files:
        errors.append("SCHEMA_VIOLATION: Blueprint JSON tidak mendefinisikan berkas kode pada field 'files'.")
        return False, errors

    lang_clean = (target_language or bp.target_language).lower().strip()
    is_python = "python" in lang_clean or lang_clean in ("fastapi", "pytest")
    is_dart = "dart" in lang_clean or "flutter" in lang_clean

    if is_python:
        for file_path, module in bp.files.items():
            scaffold = module.code_scaffold or ""
            if not scaffold.strip():
                errors.append(f"SCHEMA_VIOLATION: Berkas '{file_path}': code_scaffold kosong atau tidak didefinisikan.")
                continue
            file_errs = validate_python_code_ast(scaffold, file_label=f"Berkas '{file_path}'")
            errors.extend(file_errs)
    elif is_dart:
        full_dart_code = "\n\n".join(m.code_scaffold for m in bp.files.values() if m.code_scaffold)
        if full_dart_code:
            is_ok, dart_errs = validate_dart_blueprint_consistency(f"```dart\n{full_dart_code}\n```")
            errors.extend(dart_errs)
        else:
            errors.append("SCHEMA_VIOLATION: Blueprint JSON Dart tidak mendefinisikan code_scaffold pada files.")

    return len(errors) == 0, errors


def validate_architect_blueprint(blueprint_text: Any, target_language: str) -> Tuple[bool, List[str]]:
    """
    Entry point kanonikal untuk Architect Blueprint Validator.
    Mewajibkan format ArchitecturalBlueprint JSON terstruktur.
    Format non-JSON atau malformed langsung ditolak (FAIL V2) secara deterministik,
    tanpa fallback otomatis ke parser Markdown.
    """
    if isinstance(blueprint_text, (ArchitecturalBlueprint, dict)):
        return validate_json_blueprint(blueprint_text, target_language)

    raw_str = str(blueprint_text or "")
    json_candidate = extract_blueprint_json_text(raw_str)
    if json_candidate is not None:
        return validate_json_blueprint(raw_str, target_language)

    # REJECT NON-JSON (No silent Markdown fallback in canonical validation)
    return False, [
        "SCHEMA_VIOLATION: Cetak biru arsitektur tidak memuat blok JSON kanonikal ('=== BLUEPRINT JSON ===' atau skema ArchitecturalBlueprint). "
        "Representasi arsitektur kanonikal wajib berformat ArchitecturalBlueprint JSON yang valid."
    ]
