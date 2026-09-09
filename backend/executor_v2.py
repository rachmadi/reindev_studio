"""Executor V2: conservative pre-flight validation and safe mechanical fixes.

Design rule: never rewrite business logic, schemas, endpoints, parsers, arithmetic,
or test/oracle artifacts. Transformations must be narrowly justified and validated.
"""
from __future__ import annotations

import ast
import copy
import hashlib
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class SafeTransformation:
    file: str
    kind: str
    reason: str
    before_sha256: str
    after_sha256: str


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def validate_python_syntax(code_files: Dict[str, str]) -> List[dict]:
    """Return deterministic syntax diagnostics without changing source."""
    diagnostics: List[dict] = []
    for filename, source in sorted(code_files.items()):
        if not filename.endswith(".py"):
            continue
        try:
            ast.parse(source, filename=filename)
        except SyntaxError as exc:
            diagnostics.append({
                "file": filename,
                "kind": "syntax_error",
                "line": exc.lineno,
                "column": exc.offset,
                "message": exc.msg,
            })
    return diagnostics


def _imports_and_definitions(tree: ast.AST) -> Tuple[set, set]:
    imported = set()
    defined = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                imported.add(alias.asname or alias.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            defined.add(node.name)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            defined.add(node.id)
    return imported, defined


def detect_known_missing_imports(code_files: Dict[str, str]) -> List[dict]:
    """Detect only a tiny allow-listed class of missing standard/dependency imports.

    This function is diagnostic by default. It deliberately does not infer arbitrary
    project-module imports and does not rewrite code.
    """
    allowlist = {"BaseModel": "from pydantic import BaseModel"}
    diagnostics: List[dict] = []
    for filename, source in sorted(code_files.items()):
        if not filename.endswith(".py"):
            continue
        try:
            tree = ast.parse(source, filename=filename)
        except SyntaxError:
            continue
        imported, defined = _imports_and_definitions(tree)
        loaded_names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
        for symbol, statement in allowlist.items():
            if symbol in loaded_names and symbol not in imported and symbol not in defined:
                diagnostics.append({"file": filename, "kind": "missing_import", "symbol": symbol, "statement": statement})
    return diagnostics


def apply_safe_missing_imports(code_files: Dict[str, str], diagnostics: List[dict]) -> Tuple[Dict[str, str], List[SafeTransformation]]:
    """Apply only allow-listed import additions, then validate syntax.

    If validation worsens, all transformations are rolled back atomically.
    """
    result = copy.deepcopy(code_files)
    transformations: List[SafeTransformation] = []
    for item in diagnostics:
        filename = item["file"]
        if item["kind"] != "missing_import" or filename not in result:
            continue
        before = result[filename]
        statement = item["statement"]
        if any(line.strip() == statement for line in before.splitlines()):
            continue
        result[filename] = statement + "\n" + before
        transformations.append(SafeTransformation(filename, "missing_import", f"allowlisted:{item['symbol']}", _sha256(before), _sha256(result[filename])))

    if validate_python_syntax(result):
        return copy.deepcopy(code_files), []
    return result, transformations


def run_safe_preflight(code_files: Dict[str, str], test_files: Dict[str, str]) -> dict:
    """Pure pre-flight operation; test_files are observed but never modified."""
    original_tests = copy.deepcopy(test_files)
    syntax_before = validate_python_syntax(code_files)
    diagnostics = detect_known_missing_imports(code_files)
    fixed_code, transformations = apply_safe_missing_imports(code_files, diagnostics)
    syntax_after = validate_python_syntax(fixed_code)
    return {
        "code_files": fixed_code,
        "test_files": original_tests,
        "syntax_before": syntax_before,
        "syntax_after": syntax_after,
        "diagnostics": diagnostics,
        "transformations": [asdict(t) for t in transformations],
        "test_files_unchanged": original_tests == test_files,
        "rollback": bool(syntax_after),
    }
