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


def validate_python_blueprint_consistency(blueprint_text: str) -> Tuple[bool, List[str]]:
    """
    Memvalidasi konsistensi resolusi simbol dan impor pada snippet Python di dalam blueprint.
    Memeriksa apakah decorator dan kelas basis yang digunakan memiliki resolusi yang jelas
    (ada di impor, deklarasi lokal, atau built-in Python).
    """
    errors: List[str] = []
    blocks = _extract_code_blocks(blueprint_text, "python")
    
    if not blocks:
        return True, []

    builtin_names: Set[str] = set(dir(builtins))
    common_types = {
        "Optional", "List", "Dict", "Set", "Tuple", "Any", "Union",
        "Callable", "Iterable", "Sequence", "Mapping", "TypeVar", "Generic"
    }

    for block_idx, code in enumerate(blocks, 1):
        try:
            tree = ast.parse(code)
        except SyntaxError:
            # Fallback analisis regex jika snippet terpotong
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
                        f"Blok {block_idx}: Simbol '@{dec}' digunakan sebagai decorator "
                        f"tetapi tidak ditemukan dalam statement import maupun deklarasi lokal."
                    )
            continue

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

        available = imported_names | defined_names | builtin_names | common_types

        for dec_name, lineno in used_decorators:
            if dec_name not in available:
                errors.append(
                    f"Blok {block_idx} (baris {lineno}): Simbol '@{dec_name}' digunakan sebagai decorator, "
                    f"namun tidak ditemukan dalam statement import maupun deklarasi lokal."
                )

        for cls_name, base_name, lineno in used_bases:
            if base_name not in available:
                errors.append(
                    f"Blok {block_idx} (baris {lineno}): Kelas basis '{base_name}' pada 'class {cls_name}({base_name})' "
                    f"tidak ditemukan dalam statement import maupun deklarasi lokal."
                )

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


def validate_architect_blueprint(blueprint_text: str, target_language: str) -> Tuple[bool, List[str]]:
    """
    Entry point universal untuk Architect Blueprint Validator.
    Memeriksa konsistensi internal blueprint secara deterministik sesuai bahasa target.
    """
    lang_clean = target_language.lower().strip()
    if "python" in lang_clean or lang_clean in ("fastapi", "pytest"):
        return validate_python_blueprint_consistency(blueprint_text)
    elif "dart" in lang_clean or "flutter" in lang_clean:
        return validate_dart_blueprint_consistency(blueprint_text)
    return True, []
