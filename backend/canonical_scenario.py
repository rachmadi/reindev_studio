# -*- coding: utf-8 -*-
"""
Canonical Acceptance Scenario Representation & Behavioral Mismatch Engine
ReinDev Studio — Treatment #1.3: Universal Acceptance Behavior & Scenario Grounding v1

PRINSIP NON-NEGOTIABLE & DOKTRIN ARSITEKTURAL:
1. Frozen Oracle adalah IMMUTABLE ACCEPTANCE AUTHORITY (WHAT).
2. Skenario penerimaan mengekstrak executable stimulus/input -> expected observable outcome.
3. Docstring adalah contextual metadata semata, BUKAN acceptance authority. Skenario
   tidak boleh diciptakan dari docstring tanpa executable invocation/assertion.
4. Pemisahan ketat: ACCEPTANCE EXPECTATION (Oracle ground truth) vs RUNTIME OBSERVATION (Execution evidence).
5. Tidak ada semantic guessing / domain-specific solver (status >= 400 BUKAN aturan semantik otoritatif;
   fakta kanonikal adalah expected outcome = 404).
6. Dart takeException() == isNull membuktikan expected_exception = NONE, bukan otomatis EDGE.
   Tidak tahu -> UNKNOWN. Jangan menebak.
7. Language adapters bertanggung jawab atas parsing sumber deterministik; representasi kanonikal identik lintas bahasa.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union


# ===========================================================================
# 1. Custom Exceptions
# ===========================================================================

class CanonicalScenarioIntegrityError(Exception):
    """Dilempar jika integritas atau provenance CanonicalScenario dilanggar."""
    pass


# ===========================================================================
# 2. Canonical Enums
# ===========================================================================

class ScenarioKind(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    EDGE = "EDGE"
    UNKNOWN = "UNKNOWN"


class ComparisonStatus(str, Enum):
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    UNDETERMINED = "UNDETERMINED"


class CausalStatus(str, Enum):
    RESOLVED = "RESOLVED"
    UNRESOLVED = "UNRESOLVED"
    VIOLATED = "VIOLATED"


# ===========================================================================
# 3. Canonical Acceptance Scenario Dataclass (Acceptance Expectation)
# ===========================================================================

@dataclass(frozen=True)
class CanonicalScenario:
    """
    Representasi kanonikal deterministik dari sebuah skenario penerimaan Frozen Oracle.
    Frozen untuk menjamin imutabilitas (CANONICAL ACCEPTANCE INTEGRITY).
    Mendefinisikan WHAT yang harus observable pada stimulus tertentu tanpa mendikte HOW.
    """
    scenario_id: str
    authority: str = "FROZEN_ORACLE"
    provenance: str = "ORACLE_FACT"
    source_reference: str = ""
    caller: str = ""
    scenario_kind: str = ScenarioKind.UNKNOWN.value

    # Stimulus & Input
    stimulus: str = ""
    input_shape: Dict[str, Any] = field(default_factory=dict)
    precondition: str = "NONE"

    # Expected Observable Outcome (Authority)
    expected_outcome: Dict[str, Any] = field(default_factory=dict)
    observable_output: str = ""
    expected_exception: Optional[str] = None

    # Contextual Metadata (Non-authoritative: docstrings, hints, notes)
    metadata: Dict[str, Any] = field(default_factory=dict)
    confidence: str = "DETERMINISTIC"

    def __post_init__(self):
        if not self.scenario_id:
            raise CanonicalScenarioIntegrityError("scenario_id cannot be empty")
        if self.authority in ("FROZEN_ORACLE", "ORACLE") and self.provenance != "ORACLE_FACT":
            raise CanonicalScenarioIntegrityError(
                f"Violation of Scenario Integrity: Authority {self.authority} must have provenance ORACLE_FACT"
            )

    @property
    def docstring_metadata(self) -> str:
        """Contextual metadata dari docstring (bukan acceptance authority)."""
        return self.metadata.get("docstring", "")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "authority": self.authority,
            "provenance": self.provenance,
            "source_reference": self.source_reference,
            "caller": self.caller,
            "scenario_kind": self.scenario_kind,
            "stimulus": self.stimulus,
            "input_shape": dict(self.input_shape),
            "precondition": self.precondition,
            "expected_outcome": dict(self.expected_outcome),
            "observable_output": self.observable_output,
            "expected_exception": self.expected_exception,
            "confidence": self.confidence,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> CanonicalScenario:
        return cls(
            scenario_id=d.get("scenario_id", ""),
            authority=d.get("authority", "FROZEN_ORACLE"),
            provenance=d.get("provenance", "ORACLE_FACT"),
            source_reference=d.get("source_reference", ""),
            caller=d.get("caller", ""),
            scenario_kind=d.get("scenario_kind", ScenarioKind.UNKNOWN.value),
            stimulus=d.get("stimulus", ""),
            input_shape=dict(d.get("input_shape") or {}),
            precondition=d.get("precondition", "NONE"),
            expected_outcome=dict(d.get("expected_outcome") or {}),
            observable_output=d.get("observable_output", ""),
            expected_exception=d.get("expected_exception"),
            confidence=d.get("confidence", "DETERMINISTIC"),
            metadata=dict(d.get("metadata") or {}),
        )

    def to_prompt_line(self) -> str:
        """Format satu baris ringkas untuk prompt."""
        doc = self.docstring_metadata
        parts = [f"[{self.scenario_kind}] {self.caller}"]
        if doc:
            parts.append(f" (context: \"{doc}\")")
        parts.append(f"\n    Stimulus: {self.stimulus}")
        if self.precondition and self.precondition != "NONE":
            parts.append(f"\n    Precondition: {self.precondition}")
        if self.expected_exception:
            parts.append(f"\n    Expected Exception: {self.expected_exception}")
        if self.observable_output:
            parts.append(f"\n    Observable Outcome: {self.observable_output}")
        elif self.expected_outcome:
            parts.append(f"\n    Expected Outcome: {json.dumps(self.expected_outcome)}")
        return "".join(parts)


# ===========================================================================
# 4. Behavioral Observation Dataclass (Runtime Observation vs Expectation)
# ===========================================================================

@dataclass
class BehavioralObservation:
    """
    Representasi observasi runtime terstruktur hasil perbandingan
    antara EXPECTED OUTCOME skenario penerimaan dan ACTUAL OBSERVATION eksekusi tes.
    """
    observation_id: str
    scenario_ref: str
    caller: str
    stimulus: str
    expected: Any
    observed: Any
    comparison_status: str = ComparisonStatus.UNDETERMINED.value
    causal_status: str = CausalStatus.UNRESOLVED.value
    source_reference: str = ""
    mismatch_detail: str = ""
    raw_diagnostic_snippet: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> BehavioralObservation:
        return cls(**d)

    def to_prompt_block(self) -> str:
        """Format blok untuk developer repair context."""
        lines = [
            f"• Scenario: {self.scenario_ref} ({self.caller})",
            f"  Stimulus: {self.stimulus}",
            f"  Status: {self.comparison_status}",
            f"  Expected: {self.expected}",
            f"  Observed: {self.observed}",
        ]
        if self.mismatch_detail:
            lines.append(f"  Mismatch: {self.mismatch_detail}")
        if self.source_reference:
            lines.append(f"  Location: {self.source_reference}")
        if self.raw_diagnostic_snippet:
            lines.append(f"  Diagnostic: {self.raw_diagnostic_snippet}")
        return "\n".join(lines)


# ===========================================================================
# 5. Deterministic Scenario Extraction — Helpers & AST Extractors
# ===========================================================================

def _make_scenario_id(
    prefix: str,
    source_ref: str,
    caller: str,
    stimulus: str,
    expected_key: str,
    exc_key: Optional[str]
) -> str:
    """Menghasilkan scenario_id deterministik stabil berdasarkan observable identity."""
    raw = f"{source_ref}:{caller}:{stimulus}:{expected_key}:{exc_key or ''}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8].upper()
    return f"SCN-{prefix}-{digest}"


class PythonAstScenarioExtractor:
    """
    Ekstraktor deterministik skenario penerimaan dari berkas pengujian Python (pytest).
    Mengekstrak fungsi tes, stimulus executable, assertions, dan exception expectations.
    Docstring disimpan sebagai metadata semata (bukan acceptance authority).
    """

    def extract_scenarios(self, file_path: str, source_code: str) -> List[CanonicalScenario]:
        scenarios: List[CanonicalScenario] = []
        try:
            tree = ast.parse(source_code, filename=file_path)
        except SyntaxError:
            return scenarios

        fname = Path(file_path).name

        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and (node.name.startswith("test_") or node.name.endswith("_test")):
                sc = self._extract_function_scenario(fname, node, source_code)
                if sc:
                    scenarios.extend(sc)

        return scenarios

    def _extract_function_scenario(
        self,
        source_file: str,
        func_node: ast.FunctionDef,
        source_code: str
    ) -> List[CanonicalScenario]:
        caller = func_node.name
        # Koreksi 1: Docstring disimpan sebagai contextual metadata, BUKAN acceptance authority
        docstring = ast.get_docstring(func_node) or ""
        metadata: Dict[str, Any] = {}
        if docstring:
            metadata["docstring"] = docstring

        lineno = getattr(func_node, "lineno", 1)
        source_ref = f"{source_file}:{lineno}"

        # 1. Analisis statements dalam fungsi untuk stimulus dan ekspektasi executable
        action_calls: List[Tuple[str, Dict[str, Any], int]] = []
        assertions: List[Tuple[Dict[str, Any], str, int]] = []
        expected_exceptions: List[Tuple[str, int]] = []

        for stmt in func_node.body:
            # Detect with pytest.raises(Exc): -> explicit negative exception path
            if isinstance(stmt, ast.With):
                for item in stmt.items:
                    expr = item.context_expr
                    if isinstance(expr, ast.Call):
                        fn_repr = self._node_to_str(expr.func)
                        if "raises" in fn_repr:
                            exc_type = "Exception"
                            if expr.args:
                                exc_type = self._node_to_str(expr.args[0])
                            expected_exceptions.append((exc_type, stmt.lineno))
                # Call di dalam body with
                for w_stmt in stmt.body:
                    c = self._find_action_call_in_stmt(w_stmt)
                    if c:
                        action_calls.append(c)

            # Detect assert statements
            elif isinstance(stmt, ast.Assert):
                outcome, obs_str = self._parse_assert(stmt)
                if outcome or obs_str:
                    assertions.append((outcome, obs_str, stmt.lineno))

            # Detect action calls (client HTTP calls, module/operator invocations)
            else:
                c = self._find_action_call_in_stmt(stmt)
                if c:
                    action_calls.append(c)

        # 2. Sintesis skenario dari temuan executable
        # Kasus A: with pytest.raises (Explicit Exception Expectation)
        if expected_exceptions:
            results = []
            for exc_type, exc_line in expected_exceptions:
                stimulus = action_calls[-1][0] if action_calls else f"invocation in {caller}"
                input_shape = action_calls[-1][1] if action_calls else {}
                sc_id = _make_scenario_id("NEG", source_ref, caller, stimulus, exc_type, exc_type)
                results.append(CanonicalScenario(
                    scenario_id=sc_id,
                    source_reference=f"{source_file}:{exc_line}",
                    caller=caller,
                    scenario_kind=ScenarioKind.NEGATIVE.value,
                    stimulus=stimulus,
                    input_shape=input_shape,
                    precondition="NONE",
                    expected_outcome={"raises": exc_type},
                    observable_output=f"raises {exc_type}",
                    expected_exception=exc_type,
                    metadata=metadata,
                ))
            return results

        # Kasus B: Tes dengan stimulus executable dan assertions
        stimulus = "UNKNOWN"
        input_shape: Dict[str, Any] = {}
        precondition = "NONE"

        if len(action_calls) == 1:
            stimulus, input_shape, _ = action_calls[0]
        elif len(action_calls) > 1:
            # Panggilan terakhir sebelum verifikasi adalah stimulus utama, sebelumnya adalah precondition
            pre_calls = [c[0] for c in action_calls[:-1]]
            precondition = "; ".join(pre_calls)
            stimulus, input_shape, _ = action_calls[-1]
        elif assertions:
            stimulus = f"expression in {caller}"

        # Gabungkan outcomes dan observable output
        combined_outcome: Dict[str, Any] = {}
        observable_lines: List[str] = []

        for outcome, obs_str, _ in assertions:
            combined_outcome.update(outcome)
            if obs_str:
                observable_lines.append(obs_str)

        # Koreksi 2: status_code >= 400 adalah fakta expected_outcome, BUKAN semantic authority NEGATIVE
        # Jangan memaksakan aturan HTTP sebagai kebenaran semantik global.
        # scenario_kind tetap default POSITIVE untuk regular execution, atau UNKNOWN jika tidak jelas.
        kind = ScenarioKind.POSITIVE.value
        if not action_calls and not assertions:
            kind = ScenarioKind.UNKNOWN.value

        obs_output = ", ".join(observable_lines) if observable_lines else json.dumps(combined_outcome)
        outcome_key = json.dumps(combined_outcome, sort_keys=True)
        sc_id = _make_scenario_id(
            "POS" if kind == ScenarioKind.POSITIVE.value else "SCN",
            source_ref,
            caller,
            stimulus,
            outcome_key,
            None
        )

        return [CanonicalScenario(
            scenario_id=sc_id,
            source_reference=source_ref,
            caller=caller,
            scenario_kind=kind,
            stimulus=stimulus,
            input_shape=input_shape,
            precondition=precondition,
            expected_outcome=combined_outcome,
            observable_output=obs_output,
            expected_exception=None,
            metadata=metadata,
        )]

    def _find_action_call_in_stmt(self, stmt: ast.AST) -> Optional[Tuple[str, Dict[str, Any], int]]:
        """Mengekstrak pemanggilan aksi fungsi/metode (bukan response parser helpers)."""
        call_nodes: List[ast.Call] = []
        for n in ast.walk(stmt):
            if isinstance(n, ast.Call):
                call_nodes.append(n)
        if not call_nodes:
            return None

        # Filter: abaikan parser helper seperti .json(), len(), isinstance(), hasattr()
        for call_node in call_nodes:
            fn_str = self._node_to_str(call_node.func)
            if any(fn_str.endswith(h) for h in ('.json', '.raise_for_status', '.read', 'isinstance', 'len', 'hasattr')):
                continue

            args_str = ", ".join(self._node_to_str(a) for a in call_node.args)
            kwargs_str = ", ".join(f"{k.arg}={self._node_to_str(k.value)}" for k in call_node.keywords if k.arg)
            all_args = ", ".join(filter(None, [args_str, kwargs_str]))
            stimulus_repr = f"{fn_str}({all_args})"

            # Normalisasi HTTP stimulus jika client.method
            if any(fn_str.endswith(f".{m}") for m in ("get", "post", "put", "delete", "patch")):
                parts = fn_str.rsplit(".", 1)
                method = parts[1].upper()
                url = self._node_to_str(call_node.args[0]) if call_node.args else "/"
                if (url.startswith('"') and url.endswith('"')) or (url.startswith("'") and url.endswith("'")):
                    url = url[1:-1]
                stimulus_repr = f"{method} {url}"

            input_shape: Dict[str, Any] = {
                "function": fn_str,
                "positional_args": [self._node_to_str(a) for a in call_node.args],
                "keyword_args": {k.arg: self._node_to_str(k.value) for k in call_node.keywords if k.arg},
            }
            return (stimulus_repr, input_shape, getattr(stmt, "lineno", 1))

        return None

    def _parse_assert(self, assert_node: ast.Assert) -> Tuple[Dict[str, Any], str]:
        """Mengekstrak outcome terstruktur dan observable string dari node ast.Assert."""
        test = assert_node.test
        outcome: Dict[str, Any] = {}
        obs_str = self._node_to_str(test)

        if isinstance(test, ast.Compare):
            left_str = self._node_to_str(test.left)
            ops = test.ops
            comparators = test.comparators
            if comparators:
                right_val = self._evaluate_constant(comparators[0])
                right_str = self._node_to_str(comparators[0])

                if isinstance(ops[0], ast.Eq):
                    if "status_code" in left_str:
                        outcome["status_code"] = right_val
                        obs_str = f"status_code == {right_val}"
                    elif "[" in left_str and "]" in left_str:
                        key_match = re.search(r"\[['\"]([^'\"]+)['\"]\]", left_str)
                        if key_match:
                            field_name = key_match.group(1)
                            outcome[field_name] = right_val
                            obs_str = f"{field_name} == {right_str}"
                        else:
                            outcome["equals"] = right_val
                    else:
                        outcome[left_str] = right_val
                elif isinstance(ops[0], ast.In):
                    outcome["value_in"] = right_str
                    obs_str = f"{left_str} in {right_str}"
                elif isinstance(ops[0], (ast.Gt, ast.GtE)):
                    outcome["min_bound"] = right_val
                    obs_str = f"{left_str} >= {right_val}"

        return outcome, obs_str

    def _evaluate_constant(self, node: ast.AST) -> Any:
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, (ast.List, ast.Tuple)):
            return [self._evaluate_constant(elt) for elt in node.elts]
        elif isinstance(node, ast.Dict):
            return {
                self._evaluate_constant(k): self._evaluate_constant(v)
                for k, v in zip(node.keys, node.values)
                if k is not None
            }
        return self._node_to_str(node)

    def _node_to_str(self, node: ast.AST) -> str:
        try:
            return ast.unparse(node)
        except Exception:
            if isinstance(node, ast.Name):
                return node.id
            elif isinstance(node, ast.Attribute):
                return f"{self._node_to_str(node.value)}.{node.attr}"
            elif isinstance(node, ast.Constant):
                return repr(node.value)
            return "<expr>"


class DartAstScenarioExtractor:
    """
    Ekstraktor deterministik skenario penerimaan dari berkas pengujian Dart (flutter_test).
    Mengekstrak blok testWidgets/test, stimulus widget, matchers expect, dan exception expectations.
    """

    def extract_scenarios(self, file_path: str, source_code: str) -> List[CanonicalScenario]:
        scenarios: List[CanonicalScenario] = []
        fname = Path(file_path).name

        pattern = re.compile(
            r"(?:testWidgets|test)\s*\(\s*['\"]([^'\"]+)['\"]\s*,\s*(?:\([^)]*\)\s*async)?\s*\{([\s\S]*?)\n\s*\}\s*\);",
            re.MULTILINE
        )

        matches = list(pattern.finditer(source_code))
        if not matches:
            pattern_loose = re.compile(
                r"(?:testWidgets|test)\s*\(\s*['\"]([^'\"]+)['\"]",
                re.MULTILINE
            )
            for m in pattern_loose.finditer(source_code):
                caller = m.group(1)
                sc_id = _make_scenario_id("POS", f"{fname}:1", caller, caller, "default", None)
                scenarios.append(CanonicalScenario(
                    scenario_id=sc_id,
                    source_reference=f"{fname}:1",
                    caller=caller,
                    scenario_kind=ScenarioKind.UNKNOWN.value,
                    stimulus=caller,
                    observable_output="widget tree verification",
                ))
            return scenarios

        for m in matches:
            caller = m.group(1)
            body = m.group(2)
            lineno = source_code[:m.start()].count("\n") + 1
            source_ref = f"{fname}:{lineno}"

            sc = self._extract_dart_test_scenario(source_ref, caller, body)
            if sc:
                scenarios.append(sc)

        return scenarios

    def _extract_dart_test_scenario(
        self,
        source_ref: str,
        caller: str,
        body: str
    ) -> CanonicalScenario:
        stimulus = caller
        input_shape: Dict[str, Any] = {}
        precondition = "NONE"

        # Deteksi widget mount di dalam pumpWidget (mengabaikan framework widgets)
        framework_widgets = {
            "ProviderScope", "MaterialApp", "ThemeData", "Scaffold", "SizedBox",
            "Center", "Padding", "Column", "Row", "Container", "Card"
        }
        # Cari widget pertama yang bukan framework widget
        widget_calls = re.findall(r"\b([A-Z][A-Za-z0-9_]*)\s*\(", body)
        for w in widget_calls:
            if w not in framework_widgets and w not in ("WidgetTester", "Key", "Colors"):
                stimulus = f"Widget: {w}"
                input_shape = {"target_widget": w}
                break

        if "SizedBox" in body:
            precondition = "Constrained SizedBox container"
        elif "ProviderScope" in body:
            precondition = "ProviderScope container"

        # Ekstrak expect(...) matchers
        expect_matches = re.findall(r"expect\s*\(\s*([^,\n]+)\s*,\s*([^)\n]+)\s*\)", body)
        observable_lines: List[str] = []
        expected_outcome: Dict[str, Any] = {}
        expected_exception: Optional[str] = None

        for finder, matcher in expect_matches:
            finder_clean = finder.strip()
            matcher_clean = matcher.strip()
            observable_lines.append(f"{finder_clean} == {matcher_clean}")

            # Koreksi 3: takeException() == isNull membuktikan expected_exception = NONE
            # TIDAK otomatis menjadi EDGE. Tidak tahu -> UNKNOWN.
            if "takeException" in finder_clean:
                if "isNull" in matcher_clean:
                    expected_exception = "NONE"
                    expected_outcome["exception"] = "NONE"
                else:
                    expected_exception = matcher_clean
                    expected_outcome["exception"] = matcher_clean
            elif "find.text" in finder_clean:
                text_match = re.search(r"find\.text\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", finder_clean)
                if text_match:
                    expected_outcome[f"text:{text_match.group(1)}"] = matcher_clean
            elif "find.byType" in finder_clean:
                type_match = re.search(r"find\.byType\s*\(\s*([A-Za-z0-9_]+)\s*\)", finder_clean)
                if type_match:
                    expected_outcome[f"widget:{type_match.group(1)}"] = matcher_clean

        # Koreksi 3: scenario_kind default POSITIVE atau UNKNOWN jika tidak ada klasifikasi tegas
        scenario_kind = ScenarioKind.POSITIVE.value if observable_lines else ScenarioKind.UNKNOWN.value

        obs_output = ", ".join(observable_lines) if observable_lines else "widget tree assertions"
        outcome_key = json.dumps(expected_outcome, sort_keys=True)
        sc_id = _make_scenario_id(
            "POS",
            source_ref,
            caller,
            stimulus,
            outcome_key,
            expected_exception
        )

        return CanonicalScenario(
            scenario_id=sc_id,
            source_reference=source_ref,
            caller=caller,
            scenario_kind=scenario_kind,
            stimulus=stimulus,
            input_shape=input_shape,
            precondition=precondition,
            expected_outcome=expected_outcome,
            observable_output=obs_output,
            expected_exception=expected_exception,
        )


# ===========================================================================
# 6. Unified Scenario Extraction Entry Point
# ===========================================================================

def extract_canonical_scenarios(
    frozen_oracle_path: Optional[str] = None,
    test_files: Optional[Dict[str, str]] = None
) -> List[CanonicalScenario]:
    """
    Mengekstrak seluruh skenario penerimaan kanonikal dari Frozen Oracle (Python & Dart).
    Menjamin stabilitas identitas dan imutabilitas otoritas (ORACLE_FACT).
    """
    scenarios: List[CanonicalScenario] = []
    py_extractor = PythonAstScenarioExtractor()
    dart_extractor = DartAstScenarioExtractor()

    # Sumber 1: Berkas dari test_files dictionary
    if test_files and isinstance(test_files, dict):
        for path_str, content in test_files.items():
            if not content:
                continue
            if path_str.endswith(".py"):
                scenarios.extend(py_extractor.extract_scenarios(path_str, content))
            elif path_str.endswith(".dart"):
                scenarios.extend(dart_extractor.extract_scenarios(path_str, content))

    # Sumber 2: Berkas dari direktori frozen_oracle_path jika test_files belum memuat
    if not scenarios and frozen_oracle_path:
        oracle_dir = Path(frozen_oracle_path)
        if oracle_dir.exists() and oracle_dir.is_dir():
            for p in sorted(oracle_dir.rglob("*")):
                if not p.is_file():
                    continue
                if p.suffix == ".py" and (p.name.startswith("test_") or p.name.endswith("_test.py")):
                    try:
                        content = p.read_text(encoding="utf-8")
                        scenarios.extend(py_extractor.extract_scenarios(str(p), content))
                    except Exception:
                        pass
                elif p.suffix == ".dart" and (p.name.endswith("_test.dart") or "test" in p.name):
                    try:
                        content = p.read_text(encoding="utf-8")
                        scenarios.extend(dart_extractor.extract_scenarios(str(p), content))
                    except Exception:
                        pass

    return scenarios


# ===========================================================================
# 7. Deterministic Behavioral Mismatch Evaluator
# ===========================================================================

def evaluate_behavioral_observations(
    scenarios: List[CanonicalScenario],
    test_results: Dict[str, Any]
) -> List[BehavioralObservation]:
    """
    Membandingkan ekspektasi skenario penerimaan dengan observasi runtime aktual secara deterministik.
    Menghasilkan BehavioralObservation dengan perbandingan EXPECTED vs OBSERVED.
    Mempertahankan seluruh kegagalan independen (Multi-Failure Preservation).
    """
    observations: List[BehavioralObservation] = []
    if not scenarios:
        return observations

    output = test_results.get("output") or test_results.get("stdout") or ""
    stderr = test_results.get("stderr") or ""
    combined_output = f"{output}\n{stderr}"

    # Ekstrak data failing tests dari test_results
    diag_ev = test_results.get("diagnostic_evidence") or {}
    failing_tests_from_diag = diag_ev.get("failing_tests") or []

    # Map nama tes yang gagal -> detail kegagalan
    failed_tests_map: Dict[str, Dict[str, Any]] = {}
    for ft in failing_tests_from_diag:
        if isinstance(ft, dict) and ft.get("test_name"):
            failed_tests_map[ft["test_name"]] = ft

    # Ekstraksi regex fallback dari output pytest jika diag_ev kosong
    if not failed_tests_map and output:
        # FAILED test_main.py::test_delete_nonexistent_product - assert 204 == 404
        py_fails = re.findall(r"FAILED\s+([^\s:]+)::([^\s]+)\s*-\s*([^\n\r]+)", output)
        for _, tname, msg in py_fails:
            failed_tests_map[tname] = {"test_name": tname, "message": msg}

    # Evaluasi setiap skenario kanonikal
    for sc in scenarios:
        caller = sc.caller
        obs_id = f"OBS-{sc.scenario_id}"

        # Periksa apakah tes ini termasuk yang gagal
        matched_failure = None
        for ft_name, ft_info in failed_tests_map.items():
            if caller in ft_name or ft_name in caller:
                matched_failure = ft_info
                break

        if matched_failure:
            # GAGAL: Terjadi MISMATCH antara expected outcome dan actual observation
            msg = matched_failure.get("message", "")
            raw_tb = matched_failure.get("traceback_excerpt") or msg

            actual_val = "UNSPECIFIED_FAILURE"
            expected_val = sc.expected_outcome or sc.observable_output

            status_mismatch = re.search(r"assert\s+(\d+)\s*==\s*(\d+)", msg)
            if status_mismatch:
                actual_val = int(status_mismatch.group(1))
                expected_from_msg = int(status_mismatch.group(2))
                expected_val = expected_from_msg
            elif "assert" in msg:
                actual_val = msg.strip()

            mismatch_detail = (
                f"Observable mismatch on stimulus '{sc.stimulus}': "
                f"Expected {expected_val}, but observed {actual_val}."
            )

            observations.append(BehavioralObservation(
                observation_id=obs_id,
                scenario_ref=sc.scenario_id,
                caller=caller,
                stimulus=sc.stimulus,
                expected=expected_val,
                observed=actual_val,
                comparison_status=ComparisonStatus.MISMATCH.value,
                causal_status=CausalStatus.VIOLATED.value,
                source_reference=sc.source_reference,
                mismatch_detail=mismatch_detail,
                raw_diagnostic_snippet=msg[:300] if msg else raw_tb[:300],
            ))

        elif test_results.get("exit_code") == 0 and test_results.get("passed_count", 0) > 0:
            # BERHASIL: MATCH
            observations.append(BehavioralObservation(
                observation_id=obs_id,
                scenario_ref=sc.scenario_id,
                caller=caller,
                stimulus=sc.stimulus,
                expected=sc.expected_outcome or sc.observable_output,
                observed="VERIFIED_PASSING",
                comparison_status=ComparisonStatus.MATCH.value,
                causal_status=CausalStatus.RESOLVED.value,
                source_reference=sc.source_reference,
                mismatch_detail="",
            ))
        else:
            # Belum dieksekusi atau tidak terpetakan: UNDETERMINED
            observations.append(BehavioralObservation(
                observation_id=obs_id,
                scenario_ref=sc.scenario_id,
                caller=caller,
                stimulus=sc.stimulus,
                expected=sc.expected_outcome or sc.observable_output,
                observed=None,
                comparison_status=ComparisonStatus.UNDETERMINED.value,
                causal_status=CausalStatus.UNRESOLVED.value,
                source_reference=sc.source_reference,
                mismatch_detail="",
            ))

    return observations


# ===========================================================================
# 8. Prompt Formatters for Architect & Developer Contexts
# ===========================================================================

def format_scenarios_for_architect(scenarios: List[CanonicalScenario]) -> str:
    """
    Format seksi baca-saja [ACCEPTANCE BEHAVIOR & SCENARIOS] untuk Architect prompt.
    Mendefinisikan WHAT yang harus observable pada stimulus/skenario tanpa resep implementasi HOW.
    """
    if not scenarios:
        return ""

    lines = [
        "[ACCEPTANCE BEHAVIOR & SCENARIOS — FROZEN ORACLE GROUND TRUTH]",
        "===============================================================",
        "Berikut adalah skenario perilaku penerimaan yang diekstraksi secara deterministik dari Frozen Oracle.",
        "Arsitektur WAJIB mengakomodasi alur pengujian, nilai return, status, dan penanganan kesalahan di bawah ini:\n"
    ]

    for i, sc in enumerate(scenarios, 1):
        lines.append(f"  {i}. {sc.to_prompt_line()}")

    lines.append("\nPEDOMAN ARSITEKTURAL:")
    lines.append("- Seluruh status respons, penanganan pengecualian, dan binding data di atas adalah fakta penerimaan otoritatif.")
    lines.append("- Rancang modul dan antarmuka agar dapat mengembalikan hasil atau pengecualian yang sesuai secara deterministik.")
    lines.append("===============================================================")
    return "\n".join(lines)


def format_behavioral_mismatches_for_developer(
    observations: List[BehavioralObservation],
    scenarios: Optional[List[CanonicalScenario]] = None
) -> str:
    """
    Format seksi [CURRENT FAILURE — BEHAVIORAL MISMATCH] untuk Developer repair context.
    Memperlihatkan relasi: Scenario -> Stimulus -> Expected Outcome -> Actual Observation -> Mismatch.
    """
    mismatches = [o for o in observations if o.comparison_status == ComparisonStatus.MISMATCH.value]
    if not mismatches:
        return ""

    lines = [
        "[CURRENT FAILURE — BEHAVIORAL MISMATCH (EXPECTED vs OBSERVED)]",
        "===============================================================",
        "Terdeteksi ketidakcocokan perilaku antara ekspektasi Frozen Oracle dan observasi runtime aktual:\n"
    ]

    for i, m in enumerate(mismatches, 1):
        lines.append(f"[{i}] {m.to_prompt_block()}\n")

    lines.append("PETUNJUK REPAIR:")
    lines.append("- Fokuskan perbaikan HANYA pada logika yang menyebabkan ketidakcocokan hasil/status di atas.")
    lines.append("- Pertahankan seluruh invarian perilaku yang telah berstatus PROVEN (mutation FORBIDDEN).")
    lines.append("===============================================================")
    return "\n".join(lines)
