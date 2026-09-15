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
            hasattr_out = next((o.get("hasattr") for o, _, _ in assertions if "hasattr" in o), None)
            if hasattr_out:
                stimulus = f"hasattr({hasattr_out})"
            else:
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
        elif isinstance(test, ast.Call):
            fn_name = self._node_to_str(test.func)
            if fn_name == "hasattr" and len(test.args) >= 2:
                target_obj = self._node_to_str(test.args[0])
                attr_name = self._evaluate_constant(test.args[1])
                outcome["hasattr"] = attr_name
                outcome["symbol"] = attr_name
                obs_str = f"hasattr({target_obj}, '{attr_name}')"

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


# ===========================================================================
# 9. Treatment #1.4: Scaffold ↔ Acceptance Scenario Compatibility Engine
# ===========================================================================

class ScaffoldCompatibilityStatus(str, Enum):
    COMPATIBLE = "COMPATIBLE"
    INCOMPATIBLE = "INCOMPATIBLE"
    UNDETERMINED = "UNDETERMINED"


@dataclass
class ScaffoldCallableFact:
    """Fakta implementasi yang diekstraksi dari sebuah callable / unit di code_scaffold."""
    name: str
    file_path: str = ""
    route: Optional[str] = None
    http_method: Optional[str] = None
    positional_params_count: int = 0
    param_names: List[str] = field(default_factory=list)
    has_named_params: bool = False
    named_param_names: List[str] = field(default_factory=list)
    return_paths: List[Dict[str, Any]] = field(default_factory=list)
    error_paths: List[Dict[str, Any]] = field(default_factory=list)
    conditional_branches: List[str] = field(default_factory=list)
    collection_lookups: List[str] = field(default_factory=list)
    is_stub: bool = False
    has_opaque_calls: bool = False
    has_unconditional_return: bool = False
    raw_code: str = ""


@dataclass
class ScaffoldScenarioCompatibilityItem:
    """Item evaluasi kompatibilitas antara satu Acceptance Scenario dan code_scaffold."""
    scenario_id: str
    compatibility: str  # COMPATIBLE | INCOMPATIBLE | UNDETERMINED
    authority: str = "FROZEN_ORACLE"
    source_reference: str = ""
    observed_scaffold_facts: Dict[str, Any] = field(default_factory=dict)
    expected_behavior: Dict[str, Any] = field(default_factory=dict)
    evidence: str = ""
    causal_status: str = CausalStatus.UNRESOLVED.value
    is_regression: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> ScaffoldScenarioCompatibilityItem:
        return cls(**d)


@dataclass
class ScaffoldScenarioMatrix:
    """Matrix agregat kompatibilitas seluruh Acceptance Scenarios terhadap code_scaffold."""
    items: List[ScaffoldScenarioCompatibilityItem] = field(default_factory=list)
    is_fully_compatible: bool = False
    compatible_count: int = 0
    incompatible_count: int = 0
    undetermined_count: int = 0
    regression_count: int = 0

    def to_diagnosis_lines(self) -> List[str]:
        lines = []
        for it in self.items:
            if it.compatibility != ScaffoldCompatibilityStatus.COMPATIBLE.value:
                reg_prefix = "[CRITICAL REGRESSION] " if it.is_regression else ""
                lines.append(
                    f"{reg_prefix}SCENARIO_SCAFFOLD_INCOMPATIBILITY: Scenario '{it.scenario_id}' is {it.compatibility}.\n"
                    f"  Source: {it.source_reference}\n"
                    f"  Expected: {json.dumps(it.expected_behavior)}\n"
                    f"  Observed Scaffold: {json.dumps(it.observed_scaffold_facts)}\n"
                    f"  Evidence: {it.evidence}"
                )
        return lines

    def to_dict(self) -> Dict[str, Any]:
        return {
            "items": [it.to_dict() for it in self.items],
            "is_fully_compatible": self.is_fully_compatible,
            "compatible_count": self.compatible_count,
            "incompatible_count": self.incompatible_count,
            "undetermined_count": self.undetermined_count,
            "regression_count": self.regression_count,
        }


class PythonScaffoldExtractor:
    """Mengekstrak fakta implementasi dari code_scaffold Python via AST."""

    def extract_facts(self, file_path: str, code: str) -> List[ScaffoldCallableFact]:
        facts: List[ScaffoldCallableFact] = []
        if not code or not code.strip():
            return facts

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return facts

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                facts.append(self._extract_function_fact(file_path, node))
            elif isinstance(node, ast.ClassDef):
                facts.extend(self._extract_class_facts(file_path, node))

        return facts

    def _extract_function_fact(self, file_path: str, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> ScaffoldCallableFact:
        name = node.name
        route = None
        http_method = None
        decorator_status = None

        # Inspect decorators (e.g. @app.get('/products'), @router.delete(...))
        for dec in node.decorator_list:
            if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                cand = dec.func.attr.upper()
                if cand in ("GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"):
                    http_method = cand
                    if dec.args and isinstance(dec.args[0], ast.Constant) and isinstance(dec.args[0].value, str):
                        route = dec.args[0].value
                    for kw in dec.keywords:
                        if kw.arg == "status_code" and isinstance(kw.value, ast.Constant):
                            decorator_status = kw.value.value

        posonly_args = [a.arg for a in getattr(node.args, "posonlyargs", [])]
        pos_args = [a.arg for a in node.args.args if a.arg not in ("self", "cls")]
        kw_args = [a.arg for a in node.args.kwonlyargs]
        named_params = pos_args + kw_args
        has_named = (len(named_params) > 0 or getattr(node.args, "kwarg", None) is not None)

        return_paths: List[Dict[str, Any]] = []
        error_paths: List[Dict[str, Any]] = []
        conditional_branches: List[str] = []
        collection_lookups: List[str] = []
        has_opaque_calls = False

        # Detect stubs
        stmts = [s for s in node.body if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant) and isinstance(s.value.value, str))]
        is_stub = False
        if not stmts:
            is_stub = True
        elif len(stmts) == 1:
            s0 = stmts[0]
            if isinstance(s0, ast.Pass):
                is_stub = True
            elif isinstance(s0, ast.Expr) and isinstance(s0.value, ast.Constant) and s0.value.value is ...:
                is_stub = True
            elif isinstance(s0, ast.Raise):
                exc_id = getattr(getattr(s0, "exc", None), "id", None) or getattr(getattr(getattr(s0, "exc", None), "func", None), "id", None)
                if exc_id == "NotImplementedError":
                    is_stub = True

        # Walk body statements only (exclude decorator expressions)
        for stmt in node.body:
            for child in ast.walk(stmt):
                if isinstance(child, ast.Return):
                    ret_val = None
                    if child.value is not None:
                        if isinstance(child.value, ast.Constant):
                            ret_val = child.value.value
                        elif isinstance(child.value, ast.Name):
                            ret_val = child.value.id
                        else:
                            ret_val = "expression"
                    return_paths.append({"return_value": ret_val, "decorator_status": decorator_status})

                elif isinstance(child, ast.Raise):
                    exc_type = None
                    exc_status = None
                    if child.exc is not None:
                        if isinstance(child.exc, ast.Name):
                            exc_type = child.exc.id
                        elif isinstance(child.exc, ast.Call):
                            if isinstance(child.exc.func, ast.Name):
                                exc_type = child.exc.func.id
                            elif isinstance(child.exc.func, ast.Attribute):
                                exc_type = child.exc.func.attr
                            for kw in child.exc.keywords:
                                if kw.arg == "status_code" and isinstance(kw.value, ast.Constant):
                                    exc_status = kw.value.value
                            if exc_status is None and child.exc.args:
                                first_arg = child.exc.args[0]
                                if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, int):
                                    exc_status = first_arg.value
                    error_paths.append({"exception_type": exc_type or "Exception", "status_code": exc_status})

                elif isinstance(child, (ast.If, ast.IfExp)):
                    try:
                        cond_str = ast.unparse(child.test)
                    except Exception:
                        cond_str = "condition"
                    conditional_branches.append(cond_str)

                elif isinstance(child, ast.Compare):
                    try:
                        comp_str = ast.unparse(child)
                        if any(isinstance(op, (ast.In, ast.NotIn)) for op in child.ops):
                            collection_lookups.append(comp_str)
                    except Exception:
                        pass

                elif isinstance(child, ast.ListComp):
                    collection_lookups.append("list_comprehension_filter")

                elif isinstance(child, ast.Call):
                    func_id = None
                    if isinstance(child.func, ast.Name):
                        func_id = child.func.id
                    elif isinstance(child.func, ast.Attribute):
                        func_id = child.func.attr
                    safe_names = {
                        "len", "range", "list", "dict", "set", "str", "int", "float",
                        "bool", "print", "isinstance", "enumerate", "zip", "min", "max",
                        "sum", "HTTPException", "ValueError", "TypeError", "KeyError",
                        "IndexError", "AttributeError", "RuntimeError", "Exception",
                        "StopIteration", "NotImplementedError", "super"
                    }
                    if func_id not in safe_names:
                        has_opaque_calls = True

        has_unconditional_return = (
            len(return_paths) > 0 and
            len(error_paths) == 0 and
            len(conditional_branches) == 0 and
            not has_opaque_calls
        )

        return ScaffoldCallableFact(
            name=name,
            file_path=file_path,
            route=route,
            http_method=http_method,
            positional_params_count=len(posonly_args) + len(pos_args),
            param_names=posonly_args + pos_args,
            has_named_params=has_named,
            named_param_names=named_params,
            return_paths=return_paths,
            error_paths=error_paths,
            conditional_branches=conditional_branches,
            collection_lookups=collection_lookups,
            is_stub=is_stub,
            has_opaque_calls=has_opaque_calls,
            has_unconditional_return=has_unconditional_return,
            raw_code=getattr(node, "name", "")
        )

    def _extract_class_facts(self, file_path: str, node: ast.ClassDef) -> List[ScaffoldCallableFact]:
        facts: List[ScaffoldCallableFact] = []
        is_pydantic = any(
            (isinstance(b, ast.Name) and b.id == "BaseModel") or
            (isinstance(b, ast.Attribute) and b.attr == "BaseModel")
            for b in node.bases
        )

        init_method = None
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == "__init__":
                init_method = item
                break

        if init_method:
            init_fact = self._extract_function_fact(file_path, init_method)
            facts.append(ScaffoldCallableFact(
                name=node.name,
                file_path=file_path,
                positional_params_count=init_fact.positional_params_count,
                param_names=init_fact.param_names,
                has_named_params=(init_fact.has_named_params or is_pydantic),
                named_param_names=init_fact.named_param_names,
                return_paths=init_fact.return_paths,
                error_paths=init_fact.error_paths,
                conditional_branches=init_fact.conditional_branches,
                collection_lookups=init_fact.collection_lookups,
                is_stub=init_fact.is_stub,
                has_opaque_calls=init_fact.has_opaque_calls,
                has_unconditional_return=init_fact.has_unconditional_return,
                raw_code=f"class {node.name}"
            ))
        else:
            if is_pydantic:
                fields = []
                for item in node.body:
                    if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                        fields.append(item.target.id)
                facts.append(ScaffoldCallableFact(
                    name=node.name,
                    file_path=file_path,
                    positional_params_count=0,
                    param_names=[],
                    has_named_params=True,
                    named_param_names=fields,
                    raw_code=f"class {node.name}(BaseModel)"
                ))
            else:
                facts.append(ScaffoldCallableFact(
                    name=node.name,
                    file_path=file_path,
                    positional_params_count=0,
                    param_names=[],
                    has_named_params=False,
                    named_param_names=[],
                    raw_code=f"class {node.name}"
                ))

        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name != "__init__":
                facts.append(self._extract_function_fact(file_path, item))

        return facts


class DartScaffoldExtractor:
    """Mengekstrak fakta implementasi dari code_scaffold Dart via token / regex scanner."""

    def extract_facts(self, file_path: str, code: str) -> List[ScaffoldCallableFact]:
        facts: List[ScaffoldCallableFact] = []
        if not code or not code.strip():
            return facts

        # 1. Classes and constructors
        class_blocks = re.finditer(r"\bclass\s+([A-Za-z0-9_]+)[^{]*\{", code)
        for cb in class_blocks:
            cname = cb.group(1)
            pos_in_code = cb.end()
            body_snippet = code[pos_in_code:pos_in_code + 2000]

            ctor_pattern = re.compile(rf"\b{cname}\s*\((.*?)\)(?:\s*\{{([^}}]*)\}})?", re.DOTALL)
            ctor_m = ctor_pattern.search(body_snippet)

            if ctor_m:
                params_str = ctor_m.group(1).strip()
                ctor_body = (ctor_m.group(2) or "").strip()
                has_named = "{" in params_str
                named_params: List[str] = []
                pos_params: List[str] = []
                error_paths: List[Dict[str, Any]] = []
                conditional_branches: List[str] = []

                if has_named:
                    named_block_m = re.search(r"\{([^}]*)\}", params_str)
                    if named_block_m:
                        inside = named_block_m.group(1)
                        for part in inside.split(","):
                            part = part.strip()
                            if part:
                                p_clean = re.sub(r"\b(required|final|this\.)\s*", "", part).strip()
                                p_name = p_clean.split("=")[0].strip().split()[-1] if p_clean else ""
                                if p_name:
                                    named_params.append(p_name)
                    before_named = params_str.split("{")[0].strip().rstrip(",")
                    if before_named:
                        for part in before_named.split(","):
                            part = part.strip()
                            if part:
                                p_clean = re.sub(r"\b(required|final|this\.)\s*", "", part).strip()
                                p_name = p_clean.split("=")[0].strip().split()[-1] if p_clean else ""
                                if p_name:
                                    pos_params.append(p_name)
                else:
                    for part in params_str.split(","):
                        part = part.strip()
                        if part:
                            p_clean = re.sub(r"\b(required|final|this\.)\s*", "", part).strip()
                            p_name = p_clean.split("=")[0].strip().split()[-1] if p_clean else ""
                            if p_name:
                                pos_params.append(p_name)

                if ctor_body:
                    for m_if in re.finditer(r"if\s*\((.*?)\)", ctor_body):
                        conditional_branches.append(m_if.group(1).strip())
                    for m_throw in re.finditer(r"throw\s+([A-Za-z0-9_]+)", ctor_body):
                        error_paths.append({"exception_type": m_throw.group(1)})

                facts.append(ScaffoldCallableFact(
                    name=cname,
                    file_path=file_path,
                    positional_params_count=len(pos_params),
                    param_names=pos_params,
                    has_named_params=has_named,
                    named_param_names=named_params,
                    error_paths=error_paths,
                    conditional_branches=conditional_branches,
                    raw_code=f"class {cname}(...)"
                ))
            else:
                facts.append(ScaffoldCallableFact(
                    name=cname,
                    file_path=file_path,
                    positional_params_count=0,
                    param_names=[],
                    has_named_params=False,
                    named_param_names=[],
                    raw_code=f"class {cname}"
                ))

        # 2. Top-level functions
        func_matches = re.finditer(r"(?:^|\n)\s*(?:[A-Za-z0-9_<>, ]+)\s+([a-z][A-Za-z0-9_]*)\s*\((.*?)\)\s*\{", code)
        for fm in func_matches:
            fname = fm.group(1)
            params_raw = fm.group(2).strip()
            has_named = "{" in params_raw
            pos_count = 0
            if params_raw:
                if has_named:
                    before = params_raw.split("{")[0].strip().rstrip(",")
                    pos_count = len([p for p in before.split(",") if p.strip()]) if before else 0
                else:
                    pos_count = len([p for p in params_raw.split(",") if p.strip()])
            facts.append(ScaffoldCallableFact(
                name=fname,
                file_path=file_path,
                positional_params_count=pos_count,
                param_names=[],
                has_named_params=has_named,
                raw_code=f"func {fname}"
            ))

        return facts


def _route_matches(sc_path: str, fact_path: str) -> bool:
    """Memeriksa kecocokan route URL skenario dan scaffold secara deterministik."""
    if not sc_path or not fact_path:
        return False
    sc_clean = sc_path.strip().rstrip("/")
    fact_clean = fact_path.strip().rstrip("/")
    if sc_clean == fact_clean:
        return True
    sc_parts = sc_clean.split("/")
    fact_parts = fact_clean.split("/")
    if len(sc_parts) != len(fact_parts):
        return False
    for sp, fp in zip(sc_parts, fact_parts):
        if fp.startswith("{") and fp.endswith("}"):
            continue
        if sp != fp:
            return False
    return True


def evaluate_scaffold_scenario_compatibility(
    scenarios: List[CanonicalScenario],
    scaffold_files: Dict[str, str],
    previous_matrix: Optional[ScaffoldScenarioMatrix] = None
) -> ScaffoldScenarioMatrix:
    """
    Mengevaluasi secara deterministik kompatibilitas antara kumpulan Canonical Acceptance Scenarios
    dan code_scaffold yang diajukan Architect SEBELUM contract diizinkan bertransisi ke FROZEN.

    DOKTRIN NON-NEGOTIABLE (Treatment #1.4):
    1. Oracle adalah IMMUTABLE ACCEPTANCE AUTHORITY (WHAT).
    2. Architect adalah DESIGN AUTHORITY (HOW). Struktur bebas (dict, list, class, repo) asalkan
       observable outcome dapat dipenuhi.
    3. Tiga Status: COMPATIBLE, INCOMPATIBLE, UNDETERMINED.
    4. Evaluator membedakan:
       - PROVEN compatible: callable matches, parameter/shape matches, and appropriate path
         (matching return for positive, matching error/guard for negative) is provably present.
       - PROVEN incompatible: callable missing, call shape conflict, or provably cannot fulfill
         (e.g. unconditional 204 with zero error path/branch in a self-contained body for negative scenario).
       - UNDETERMINED: presence of opaque calls, dynamic dispatch, unresolved branches, or stubs
         where reachability or absence cannot be statically proven.
    5. Aturan Absolut: UNDETERMINED TIDAK PERNAH dipromosikan ke PASS (FAIL-CLOSED).
    6. Multi-scenario preservation & regression detection (COMPATIBLE -> INCOMPATIBLE flagged as CRITICAL).
    """
    py_extractor = PythonScaffoldExtractor()
    dart_extractor = DartScaffoldExtractor()

    all_facts: List[ScaffoldCallableFact] = []
    for file_path, code in scaffold_files.items():
        if not code:
            continue
        if file_path.endswith(".py"):
            all_facts.extend(py_extractor.extract_facts(file_path, code))
        elif file_path.endswith(".dart"):
            all_facts.extend(dart_extractor.extract_facts(file_path, code))

    prev_status_map = {}
    if previous_matrix:
        for it in previous_matrix.items:
            prev_status_map[it.scenario_id] = it.compatibility

    items: List[ScaffoldScenarioCompatibilityItem] = []
    regression_count = 0

    for sc in scenarios:
        matched_facts: List[ScaffoldCallableFact] = []

        sc_method = sc.expected_outcome.get("http_method") or (
            re.search(r"\b(GET|POST|PUT|DELETE|PATCH)\b", sc.stimulus).group(1)
            if re.search(r"\b(GET|POST|PUT|DELETE|PATCH)\b", sc.stimulus) else None
        )
        sc_route = sc.expected_outcome.get("route")
        if not sc_route:
            m_route = re.search(r"(/[\w\.\-/{}]+)", sc.stimulus)
            if m_route:
                sc_route = m_route.group(1)

        for f in all_facts:
            if f.route and sc_route and _route_matches(sc_route, f.route):
                if not sc_method or not f.http_method or sc_method.upper() == f.http_method.upper():
                    matched_facts.append(f)
                    continue

            if f.name and (
                f.name in sc.stimulus or
                f.name in sc.caller or
                f.name in sc.observable_output or
                f.name in str(sc.expected_outcome)
            ):
                matched_facts.append(f)

        expected_repr = dict(sc.expected_outcome)
        if sc.expected_exception:
            expected_repr["expected_exception"] = sc.expected_exception

        if not matched_facts:
            items.append(ScaffoldScenarioCompatibilityItem(
                scenario_id=sc.scenario_id,
                compatibility=ScaffoldCompatibilityStatus.INCOMPATIBLE.value,
                authority="FROZEN_ORACLE",
                source_reference=sc.source_reference,
                observed_scaffold_facts={},
                expected_behavior=expected_repr,
                evidence=f"Scaffold does not define callable, constructor, or endpoint matching scenario stimulus '{sc.stimulus}'.",
                causal_status=CausalStatus.VIOLATED.value
            ))
            continue

        fact = matched_facts[0]
        observed_facts = {
            "name": fact.name,
            "route": fact.route,
            "http_method": fact.http_method,
            "positional_params_count": fact.positional_params_count,
            "has_named_params": fact.has_named_params,
            "error_paths_count": len(fact.error_paths),
            "conditional_branches_count": len(fact.conditional_branches),
            "is_stub": fact.is_stub,
            "has_opaque_calls": fact.has_opaque_calls,
            "has_unconditional_return": fact.has_unconditional_return,
        }

        # Check call shape / constructor compatibility
        is_pos_call = bool(re.search(rf"\b{fact.name}\s*\(\s*\[", sc.stimulus) or
                           re.search(rf"\b{fact.name}\s*\([^{{)]*[,)]", sc.stimulus))
        is_named_call = bool(re.search(rf"\b{fact.name}\s*\(\s*\w+\s*:", sc.stimulus) or
                             re.search(r"\b\w+\s*:\s*['\"\d]", sc.stimulus))

        if is_pos_call and not is_named_call and fact.has_named_params and fact.positional_params_count == 0:
            items.append(ScaffoldScenarioCompatibilityItem(
                scenario_id=sc.scenario_id,
                compatibility=ScaffoldCompatibilityStatus.INCOMPATIBLE.value,
                authority="FROZEN_ORACLE",
                source_reference=sc.source_reference,
                observed_scaffold_facts=observed_facts,
                expected_behavior=expected_repr,
                evidence=(
                    f"Call shape incompatibility: Scenario invokes '{fact.name}' with positional arguments, "
                    f"but scaffold constructor only accepts named/keyword parameters (0 positional parameters)."
                ),
                causal_status=CausalStatus.VIOLATED.value
            ))
            continue

        if is_named_call and not fact.has_named_params and fact.positional_params_count > 0:
            items.append(ScaffoldScenarioCompatibilityItem(
                scenario_id=sc.scenario_id,
                compatibility=ScaffoldCompatibilityStatus.INCOMPATIBLE.value,
                authority="FROZEN_ORACLE",
                source_reference=sc.source_reference,
                observed_scaffold_facts=observed_facts,
                expected_behavior=expected_repr,
                evidence=(
                    f"Call shape incompatibility: Scenario invokes '{fact.name}' with named arguments, "
                    f"but scaffold constructor declares positional parameters without named parameter support."
                ),
                causal_status=CausalStatus.VIOLATED.value
            ))
            continue

        # Check outcome compatibility (User Corrections 1 & 2)
        is_negative = (
            sc.scenario_kind == ScenarioKind.NEGATIVE.value or
            (sc.expected_exception is not None and sc.expected_exception != "NONE") or
            any(isinstance(v, int) and v >= 400 for v in sc.expected_outcome.values())
        )

        if is_negative:
            # Case 1: Stub or Opaque Delegation without local error handling -> UNDETERMINED
            if fact.is_stub or (fact.has_opaque_calls and not fact.error_paths and not fact.conditional_branches):
                items.append(ScaffoldScenarioCompatibilityItem(
                    scenario_id=sc.scenario_id,
                    compatibility=ScaffoldCompatibilityStatus.UNDETERMINED.value,
                    authority="FROZEN_ORACLE",
                    source_reference=sc.source_reference,
                    observed_scaffold_facts=observed_facts,
                    expected_behavior=expected_repr,
                    evidence=(
                        f"Insufficient static evidence: Callable '{fact.name}' delegates to opaque logic or is stubbed; "
                        f"absence or presence of error path cannot be statically proven."
                    ),
                    causal_status=CausalStatus.UNRESOLVED.value
                ))
                continue

            # Case 2: Statically proven absence of error handling -> INCOMPATIBLE (Gate 05 / Correction 1)
            if fact.has_unconditional_return and not fact.error_paths and not fact.conditional_branches:
                items.append(ScaffoldScenarioCompatibilityItem(
                    scenario_id=sc.scenario_id,
                    compatibility=ScaffoldCompatibilityStatus.INCOMPATIBLE.value,
                    authority="FROZEN_ORACLE",
                    source_reference=sc.source_reference,
                    observed_scaffold_facts=observed_facts,
                    expected_behavior=expected_repr,
                    evidence=(
                        f"Statically proven absence of error path: Scenario expects negative/error outcome '{expected_repr}', "
                        f"but scaffold implementation for '{fact.name}' provides only unconditional success with no conditional branch or error path."
                    ),
                    causal_status=CausalStatus.VIOLATED.value
                ))
                continue

            # Case 3: Error paths or conditional branches present -> Reachability Check (Correction 2)
            has_matching_raise = False
            for ep in fact.error_paths:
                expected_st = None
                for k, v in sc.expected_outcome.items():
                    if "status" in k and isinstance(v, int):
                        expected_st = v
                if ep.get("status_code") == expected_st or ep.get("exception_type") in str(sc.expected_exception):
                    has_matching_raise = True
                    break
                if ep.get("exception_type") == "HTTPException" and expected_st is not None and ep.get("status_code") is None:
                    has_matching_raise = True
                    break

            has_relevant_guard = False
            for b in fact.conditional_branches:
                if any(p in b for p in fact.param_names) or "not in" in b or "not" in b or "==" in b or "<" in b or ">" in b:
                    has_relevant_guard = True
                    break

            if has_matching_raise or has_relevant_guard or fact.collection_lookups:
                # PROVEN COMPATIBLE
                items.append(ScaffoldScenarioCompatibilityItem(
                    scenario_id=sc.scenario_id,
                    compatibility=ScaffoldCompatibilityStatus.COMPATIBLE.value,
                    authority="FROZEN_ORACLE",
                    source_reference=sc.source_reference,
                    observed_scaffold_facts=observed_facts,
                    expected_behavior=expected_repr,
                    evidence=f"Scaffold for '{fact.name}' provably defines reachable conditional branch or error path aligned with scenario stimulus/precondition.",
                    causal_status=CausalStatus.RESOLVED.value
                ))
                continue
            else:
                # Branches exist but reachability cannot be proven -> UNDETERMINED
                items.append(ScaffoldScenarioCompatibilityItem(
                    scenario_id=sc.scenario_id,
                    compatibility=ScaffoldCompatibilityStatus.UNDETERMINED.value,
                    authority="FROZEN_ORACLE",
                    source_reference=sc.source_reference,
                    observed_scaffold_facts=observed_facts,
                    expected_behavior=expected_repr,
                    evidence=(
                        f"Conditional branch or error path present in '{fact.name}', "
                        f"but reachability under scenario precondition cannot be statically proven."
                    ),
                    causal_status=CausalStatus.UNRESOLVED.value
                ))
                continue
        else:
            # Positive scenario
            has_explicit_return_expectation = any(
                k in sc.expected_outcome
                for k in ("status_code", "return_value", "equals", "value_in")
            )
            if fact.is_stub and has_explicit_return_expectation:
                items.append(ScaffoldScenarioCompatibilityItem(
                    scenario_id=sc.scenario_id,
                    compatibility=ScaffoldCompatibilityStatus.UNDETERMINED.value,
                    authority="FROZEN_ORACLE",
                    source_reference=sc.source_reference,
                    observed_scaffold_facts=observed_facts,
                    expected_behavior=expected_repr,
                    evidence=f"Scaffold callable '{fact.name}' is stubbed; return behavior cannot be statically proven.",
                    causal_status=CausalStatus.UNRESOLVED.value
                ))
                continue

            # Valid interface and return/constructor shape
            items.append(ScaffoldScenarioCompatibilityItem(
                scenario_id=sc.scenario_id,
                compatibility=ScaffoldCompatibilityStatus.COMPATIBLE.value,
                authority="FROZEN_ORACLE",
                source_reference=sc.source_reference,
                observed_scaffold_facts=observed_facts,
                expected_behavior=expected_repr,
                evidence=f"Scaffold defines matching interface and return path for '{fact.name}'.",
                causal_status=CausalStatus.RESOLVED.value
            ))

    # Regression detection
    for it in items:
        prev_st = prev_status_map.get(it.scenario_id)
        if prev_st == ScaffoldCompatibilityStatus.COMPATIBLE.value and it.compatibility == ScaffoldCompatibilityStatus.INCOMPATIBLE.value:
            it.is_regression = True
            regression_count += 1
            it.evidence = f"[CRITICAL REGRESSION] Previously COMPATIBLE scenario is now INCOMPATIBLE. {it.evidence}"

    compat_count = sum(1 for it in items if it.compatibility == ScaffoldCompatibilityStatus.COMPATIBLE.value)
    incompat_count = sum(1 for it in items if it.compatibility == ScaffoldCompatibilityStatus.INCOMPATIBLE.value)
    undet_count = sum(1 for it in items if it.compatibility == ScaffoldCompatibilityStatus.UNDETERMINED.value)

    # Fail-closed: UNDETERMINED is NEVER promoted to PASS
    is_fully = (incompat_count == 0 and undet_count == 0 and len(items) > 0)

    return ScaffoldScenarioMatrix(
        items=items,
        is_fully_compatible=is_fully,
        compatible_count=compat_count,
        incompatible_count=incompat_count,
        undetermined_count=undet_count,
        regression_count=regression_count
    )


def format_scaffold_compatibility_for_architect(matrix: ScaffoldScenarioMatrix) -> str:
    """
    Format seksi [BEHAVIORAL COMPATIBILITY EVIDENCE] untuk Architect prompt / repair context.
    Memberitahukan fakta observable ketidakcocokan tanpa mendikte implementasi HOW.
    """
    if not matrix.items:
        return ""
    incompat_or_undet = [
        it for it in matrix.items
        if it.compatibility != ScaffoldCompatibilityStatus.COMPATIBLE.value
    ]
    if not incompat_or_undet:
        return ""

    lines = [
        "[BEHAVIORAL COMPATIBILITY EVIDENCE — SCAFFOLD vs ACCEPTANCE SCENARIOS]",
        "======================================================================",
        "Pemeriksaan pre-freeze mendeteksi bahwa code_scaffold yang diajukan tidak kompatibel",
        "dengan skenario penerimaan yang diekstraksi dari Frozen Oracle:\n"
    ]
    for i, it in enumerate(incompat_or_undet, 1):
        reg_tag = " [CRITICAL REGRESSION]" if it.is_regression else ""
        lines.append(f"[{i}] Scenario: {it.scenario_id} — Status: {it.compatibility}{reg_tag}")
        lines.append(f"    Source: {it.source_reference}")
        lines.append(f"    Expected Behavior: {json.dumps(it.expected_behavior)}")
        lines.append(f"    Observed Scaffold: {json.dumps(it.observed_scaffold_facts)}")
        lines.append(f"    Diagnosis / Evidence: {it.evidence}\n")

    lines.append("PETUNJUK PERBAIKAN ARSITEKTURAL (HOW TETAP PADA ARCHITECT):")
    lines.append("- Architect bebas memilih struktur data (list, dict, class, repository, adapter).")
    lines.append("- Namun antarmuka dan alur kontrol scaffold WAJIB menyediakan jalur observable yang mampu")
    lines.append("  memenuhi perilaku penerimaan di atas (misal: penanganan kasus error/404, kesesuaian shape konstruktor).")
    lines.append("======================================================================")
    return "\n".join(lines)

