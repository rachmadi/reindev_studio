"""
Locked Invariants Engine — Once Proven, Lock It
ReinDev Studio — Deterministic Invariant Preservation & Anti-Oscillation System

Menerapkan prinsip eksplisit:
PROVEN -> LOCKED -> PRESERVE -> REVALIDATE

Fitur Kunci:
1. Invariant hanya berstatus PROVEN jika ada bukti deterministik dari validator/compiler/AST.
2. Invariant yang terkunci (LOCKED) dievaluasi ulang pada setiap putaran perbaikan.
3. Jika kondisi yang sudah PROVEN rusak, validator deterministik mendeteksi REGRESSION.
4. REGRESSION otomatis masuk ke CURRENT_FAILURES dan membatalkan status perbaikan sukses.
5. Telemetri mendeteksi pola osilasi (A PASS -> A FAIL -> A PASS).
6. 100% Bebas Heuristik / Bebas Solver Khusus Task: bekerja generik untuk Python, Dart, FastAPI, CLI, dll.
"""

from __future__ import annotations

import ast
import re
import textwrap
import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple, Set


# ===========================================================================
# Module-Level Constants — Candidate Extraction Guards
# ===========================================================================

# Tokens yang TIDAK BOLEH menjadi kandidat SYMBOL_DECLARATION (class name)
# (meta-tokens pipeline, primitif bahasa, atau keyword yang bukan nama kelas)
_BLOCKED_CLASS_TOKENS: frozenset = frozenset({
    # Meta-tokens pipeline internal
    "exit_code_1", "exit_code_0", "exit_code_2",
    # Identifier umum bukan nama kelas
    "data", "key", "super",
    # Primitif Dart
    "null", "true", "false", "void", "int", "double", "bool", "String",
    # Primitif Python
    "str", "float", "list", "dict", "set", "tuple", "bytes",
    # Keyword umum
    "final", "const", "required", "this", "new", "class",
    "var", "dynamic", "async", "await", "return",
    "extends", "implements", "with", "abstract", "override",
    "static", "late", "external", "factory",
})

# Tokens yang TIDAK BOLEH menjadi kandidat CONSTRUCTOR_PARAM (nama parameter)
# (lebih permisif dari _BLOCKED_CLASS_TOKENS — "data" valid sebagai param name)
_BLOCKED_PARAM_TOKENS: frozenset = frozenset({
    # Meta-tokens pipeline internal
    "exit_code_1", "exit_code_0", "exit_code_2",
    # Keyword yang muncul di posisi parameter tapi bukan nama parameter
    "super", "this", "new",
    "null", "true", "false", "void",
})

# Regex: simbol yang mengikuti kata kunci galat kompilasi (keyword-before-symbol format)
# Contoh: "Method not found: 'MetricData'"
_COMPILER_KEYWORD_SYMBOL_RE = re.compile(
    r"(?:Method not found"
    r"|isn't a type"
    r"|isn't defined"
    r"|Undefined name"
    r"|NameError:"
    r"|AttributeError:"
    r"|cannot find symbol"
    r"|The getter\s+['\"]?[A-Za-z0-9_]+['\"]?\s+isn't defined"
    r"|The setter\s+['\"]?[A-Za-z0-9_]+['\"]?\s+isn't defined"
    r"|The name\s+['\"]?[A-Za-z0-9_]+['\"]?\s+isn't defined"
    r")"
    r"[^'\"]*['\"]([A-Za-z][A-Za-z0-9_]+)['\"]",
    re.IGNORECASE
)

# Regex: simbol yang mendahului kata kunci galat (symbol-before-keyword format)
# Contoh: "'CardMetricData' isn't a type."
_SYMBOL_BEFORE_KEYWORD_RE = re.compile(
    r"['\"]([A-Za-z][A-Za-z0-9_]+)['\"]\s*"
    r"(?:isn't a type|isn't defined|is not defined|is undefined)",
    re.IGNORECASE
)

# Regex: fallback — identifier apapun dalam tanda kutip (lebar, difilter oleh dual gate)
_QUOTED_IDENTIFIER_RE = re.compile(r"['\"]([A-Za-z][A-Za-z0-9_]{1,})['\"]")

# Regex: ekstrak nama parameter dari pesan "No named parameter with the name 'X'"
_NAMED_PARAM_RE = re.compile(
    r"[Nn]o named parameter with the name\s*['\"]([A-Za-z][A-Za-z0-9_]*)['\"]"
)


def _extract_symbol_candidates_from_text(text: str) -> Set[str]:
    """
    Generik: Ekstrak kandidat simbol kelas dari teks galat kompilasi/runtime.

    Urutan prioritas:
    1. Simbol setelah kata kunci galat yang dikenal (keyword-before-symbol).
    2. Simbol sebelum kata kunci galat yang dikenal (symbol-before-keyword).
    3. Fallback: identifier apapun dalam tanda kutip.

    PENTING: Kandidat ini HANYA menentukan apa yang DIPERIKSA oleh dual gate.
    Status PROVEN ditentukan sepenuhnya oleh:
        AST present (Gate 1) AND compiler clean (Gate 2).
    Bukan oleh kemunculan simbol di evidence source.
    """
    if not text:
        return set()
    candidates: Set[str] = set()

    # Pass 1: keyword-before-symbol patterns (presisi tinggi)
    for m in _COMPILER_KEYWORD_SYMBOL_RE.finditer(text):
        sym = m.group(1).strip()
        if sym and sym not in _BLOCKED_CLASS_TOKENS and len(sym) > 1:
            candidates.add(sym)

    # Pass 2: symbol-before-keyword patterns (e.g., "'Foo' isn't a type")
    for m in _SYMBOL_BEFORE_KEYWORD_RE.finditer(text):
        sym = m.group(1).strip()
        if sym and sym not in _BLOCKED_CLASS_TOKENS and len(sym) > 1:
            candidates.add(sym)

    # Pass 3: fallback — any quoted identifier (dual gate akan memfilter false positives)
    for m in _QUOTED_IDENTIFIER_RE.finditer(text):
        sym = m.group(1).strip()
        if sym and sym not in _BLOCKED_CLASS_TOKENS and len(sym) > 1:
            candidates.add(sym)

    return candidates


def _extract_named_param_candidates_from_text(text: str) -> Set[str]:
    """
    Generik: Ekstrak kandidat nama parameter dari pesan galat konstruktor.

    Menangani format: "No named parameter with the name 'paramName'"

    PENTING: Kandidat ini HANYA menentukan apa yang DIPERIKSA.
    Status PROVEN ditentukan oleh kehadiran param di AST konstruktor
    DAN kebersihan compiler output dari galat terkait.
    """
    if not text:
        return set()
    candidates: Set[str] = set()
    for m in _NAMED_PARAM_RE.finditer(text):
        pname = m.group(1).strip()
        if pname and pname not in _BLOCKED_PARAM_TOKENS:
            candidates.add(pname)
    return candidates


@dataclass
class LockedInvariant:
    """Representasi eksplisit invarian yang telah terbukti benar dan terkunci."""
    invariant_id: str                      # e.g., "INV-SYM-MetricData", "INV-PARAM-CardMetric-data"
    category: str                          # "SYMBOL_DECLARATION" | "CONSTRUCTOR_PARAM" | "PASSING_TEST" | "CONTRACT_STATUS" | "ORACLE_INTEGRITY"
    description: str                       # Deskripsi spesifik kondisi yang terbukti
    target_symbol: str                     # Simbol atau identifier target
    target_file: str                       # Berkas tempat simbol berada
    condition: str                         # Pernyataan kondisi deterministik
    status: str = "PROVEN"                 # "PROVEN" | "REGRESSION" | "PENDING"
    state: str = "LOCKED"                  # "LOCKED" | "RESOLVED" | "VIOLATED"
    evidence_source: str = ""              # Sumber bukti deterministik (e.g. "DART_AST_INSPECTION")
    evidence: Any = None                   # Bukti faktual
    proven_at_turn: int = 0                # Putaran saat pertama kali terbukti
    proven_by_validator: str = "B5_EXECUTOR_ITERATION"  # Validator yang mengesahkan
    provenance: Dict[str, Any] = field(default_factory=dict)  # Metadata asal usul bukti
    revalidated_at_turn: Optional[int] = None  # Putaran terakhir evaluasi ulang
    regression_count: int = 0              # Jumlah kali mengalami regresi
    regression_history: List[Dict[str, Any]] = field(default_factory=list)  # Riwayat regresi
    oscillation_detected: bool = False     # Flag jika terdeteksi osilasi (flip-flop)
    mutation: str = "FORBIDDEN"            # Melarang mutasi perilaku terbukti
    ever_regressed: bool = False           # Flag permanen apakah pernah regresi

    def record_regression(self, failure_evidence: Any, turn: int = 0) -> None:
        """Mencatat kejadian regresi secara permanen."""
        was_previously_regressed = self.regression_count > 0
        self.status = "REGRESSION"
        self.state = "VIOLATED"
        self.ever_regressed = True
        self.regression_count += 1
        if was_previously_regressed:
            self.oscillation_detected = True
        record = {
            "turn": turn,
            "failure_evidence": str(failure_evidence),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.regression_history.append(record)

    def record_recovery(self, recovery_evidence: Any, turn: int = 0) -> None:
        """Memulihkan invariant kembali ke status PROVEN / LOCKED."""
        if self.status == "REGRESSION":
            self.oscillation_detected = True
        self.status = "PROVEN"
        self.state = "LOCKED"
        self.revalidated_at_turn = turn
        if self.regression_history:
            self.regression_history[-1]["recovered_at_turn"] = turn
            self.regression_history[-1]["recovery_evidence"] = str(recovery_evidence)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> LockedInvariant:
        clean = dict(data)
        if "target_symbol" not in clean:
            clean["target_symbol"] = clean.get("invariant_id", "")
        if "target_file" not in clean:
            clean["target_file"] = "main.py"
        if "condition" not in clean:
            clean["condition"] = clean.get("description", "")
        import inspect
        valid_keys = set(inspect.signature(cls).parameters.keys())
        filtered = {k: v for k, v in clean.items() if k in valid_keys}
        return cls(**filtered)


# ===========================================================================
# 1. Deterministic AST / Symbol Extractors (Generic Python & Dart)
# ===========================================================================

try:
    from .canonical_symbol_scanner import scan_symbols_from_code as _canonical_scan_symbols_from_code
except ImportError:
    from canonical_symbol_scanner import scan_symbols_from_code as _canonical_scan_symbols_from_code


def scan_code_symbols(code_content: str, target_lang: str) -> Dict[str, Any]:
    """
    Ekstraksi simbol kelas, fungsi, dan parameter konstruktor secara deterministik
    menggunakan Canonical Symbol Resolution Module.
    """
    res = _canonical_scan_symbols_from_code(code_content, target_lang)
    all_funcs = sorted(list(set(res.functions) | set(res.top_level_declarations)))
    return {
        "classes": res.classes,
        "functions": all_funcs
    }



# ===========================================================================
# 2. Invariant Condition Evaluators
# ===========================================================================

def evaluate_symbol_invariant(
    inv: LockedInvariant,
    code_files: Dict[str, str],
    target_lang: str
) -> Tuple[bool, str]:
    """Mengevaluasi apakah simbol kelas/fungsi yang terkunci masih ada di kode."""
    tf = inv.target_file
    content = code_files.get(tf, "")
    if not content:
        return False, f"Berkas target '{tf}' tidak ditemukan dalam code_files"

    symbols = scan_code_symbols(content, target_lang)
    target_sym = inv.target_symbol

    if inv.category == "SYMBOL_DECLARATION":
        if target_sym in symbols["classes"] or target_sym in symbols["functions"]:
            return True, f"Simbol '{target_sym}' terverifikasi ada dalam AST berkas '{tf}'"
        return False, f"Simbol '{target_sym}' TIDAK ditemukan dalam AST berkas '{tf}' (telah dihapus/diubah)"

    elif inv.category == "CONSTRUCTOR_PARAM":
        parts = target_sym.split(".")
        if len(parts) == 2:
            cname, pname = parts[0], parts[1]
            if cname not in symbols["classes"]:
                return False, f"Kelas '{cname}' tidak ditemukan di '{tf}' saat memeriksa parameter '{pname}'"
            params = symbols["classes"][cname].get("parameters", [])
            if pname in params:
                return True, f"Parameter '{pname}' terverifikasi ada pada konstruktor '{cname}' di '{tf}'"
            return False, f"Parameter '{pname}' TIDAK ditemukan pada konstruktor '{cname}' di '{tf}' (tersedia: {params})"

    return False, f"Evaluator tidak mengenali kombinasi category='{inv.category}' dan target='{target_sym}'"


def evaluate_compiler_error_freedom(
    inv: LockedInvariant,
    compiler_output: str
) -> Tuple[bool, str]:
    """Memverifikasi bahwa compiler tidak lagi mengeluhkan simbol terkait."""
    sym = inv.target_symbol
    pattern = rf"(?:Method not found|isn't a type|isn't defined|No named parameter).*'{re.escape(sym)}'"
    if re.search(pattern, compiler_output, re.IGNORECASE):
        return False, f"Kompilator masih melaporkan galat pada simbol '{sym}'"
    return True, f"Kompilator tidak melaporkan galat pada simbol '{sym}'"


# ===========================================================================
# 3. Deterministic Invariant Discovery & Lifecycle Manager
# ===========================================================================

def discover_newly_proven_invariants(
    code_files: Dict[str, str],
    test_results: Dict[str, Any],
    compiler_output: str,
    target_lang: str,
    authoritative_file: str,
    previous_violations: List[Dict[str, Any]],
    current_violations: List[Dict[str, Any]],
    turn: int = 0,
    # Param baru — evidence sources untuk pengumpulan kandidat (bukan bukti PROVEN langsung)
    diagnostic_evidence: Optional[Dict[str, Any]] = None,
    previous_diagnostic_evidence: Optional[Dict[str, Any]] = None,
    previous_stderr: Optional[str] = None,
) -> List[LockedInvariant]:
    """
    Menemukan kondisi baru yang telah terbukti benar (PROVEN) secara deterministik.

    Prinsip Utama:
    - Evidence sources (previous_violations, previous_diagnostic_evidence, previous_stderr)
      HANYA menghasilkan KANDIDAT simbol untuk diperiksa — bukan bukti bahwa kondisi PROVEN.
    - Status PROVEN HANYA ditentukan oleh dual gate deterministik pada state kode SAAT INI:
        Gate 1: Simbol ada dalam AST kode saat ini (scan_code_symbols).
        Gate 2: Output kompilasi saat ini bersih dari galat terkait simbol tersebut.
    - Kandidat dari turn sebelumnya TIDAK secara otomatis menjadi PROVEN.
    - LLM dilarang mendeklarasikan sendiri status PROVEN.
    - 'exit_code_1' dan token meta pipeline TIDAK pernah menjadi kandidat.

    Aliran Data:
        [previous_violations] ┐
        [previous_diagnostic_evidence] ├─→ candidate symbols
        [previous_stderr]     ┘
                ↓
        current AST (Gate 1: symbol exists?)
                ↓
        current compiler_output (Gate 2: no error for symbol?)
                ↓
        PROVEN → LOCKED
    """
    discovered: List[LockedInvariant] = []
    content = code_files.get(authoritative_file, "")
    if not content:
        return discovered

    symbols = scan_code_symbols(content, target_lang)

    # -----------------------------------------------------------------------
    # Tahap 1: Kumpulkan kandidat simbol dari SEMUA evidence sources
    #
    # Kandidat = identifier yang sebelumnya gagal dan perlu diverifikasi
    # apakah sudah tersedia di kode saat ini (diputuskan oleh dual gate).
    # -----------------------------------------------------------------------
    class_candidates: Set[str] = set()   # Kandidat SYMBOL_DECLARATION
    param_candidates: Set[str] = set()    # Kandidat CONSTRUCTOR_PARAM (nama parameter)

    # Source A: previous_violations (jalur backward-compatible)
    for prev_v in previous_violations:
        observed_sym = prev_v.get("observed_symbol") or ""
        msg = prev_v.get("message", "")
        if observed_sym and observed_sym not in _BLOCKED_CLASS_TOKENS:
            class_candidates.add(observed_sym)
        class_candidates.update(_extract_symbol_candidates_from_text(msg))
        param_candidates.update(_extract_named_param_candidates_from_text(msg))

    # Source B: previous_diagnostic_evidence["failing_tests"]
    # (Evidence dari putaran N-1 — HANYA sumber kandidat, bukan bukti PROVEN)
    prev_diag: Dict[str, Any] = previous_diagnostic_evidence or {}
    for ft in (prev_diag.get("failing_tests") or []):
        if not isinstance(ft, dict):
            continue
        ft_msg = ft.get("message", "")
        ft_src = ft.get("source_symbol", "")
        # source_symbol yang sudah diparsed oleh DiagnosticParser
        if ft_src and ft_src not in _BLOCKED_CLASS_TOKENS:
            class_candidates.add(ft_src)
        # Ekstraksi generik dari teks pesan galat
        class_candidates.update(_extract_symbol_candidates_from_text(ft_msg))
        param_candidates.update(_extract_named_param_candidates_from_text(ft_msg))

    # Source C: previous_stderr (output kompilasi mentah dari putaran sebelumnya)
    if previous_stderr:
        class_candidates.update(_extract_symbol_candidates_from_text(previous_stderr))
        param_candidates.update(_extract_named_param_candidates_from_text(previous_stderr))

    # Source D: current diagnostic_evidence (untuk deteksi param dari turn saat ini juga)
    # Hanya dipakai untuk CONSTRUCTOR_PARAM discovery — class candidates dari sini
    # belum bisa jadi kandidat PROVEN karena mereka masih failing di turn ini
    curr_diag: Dict[str, Any] = diagnostic_evidence or {}
    for ft in (curr_diag.get("failing_tests") or []):
        if not isinstance(ft, dict):
            continue
        param_candidates.update(_extract_named_param_candidates_from_text(ft.get("message", "")))

    # -----------------------------------------------------------------------
    # Tahap 2: Dual Gate Deterministik
    #
    # Gate 1: Simbol ADA di AST kode saat ini?
    # Gate 2: compiler_output saat ini BERSIH dari galat terkait simbol?
    #
    # PROVEN hanya jika KEDUA gate terpenuhi.
    # -----------------------------------------------------------------------

    # --- Gate SYMBOL_DECLARATION ---
    for cand_sym in class_candidates:
        # Gate 1: Harus ada di AST kode saat ini
        if cand_sym not in symbols["classes"]:
            continue

        # Gate 2: Kompilasi saat ini harus bersih dari galat undefined symbol ini
        temp_inv = LockedInvariant(
            invariant_id="",
            category="SYMBOL_DECLARATION",
            description="",
            target_symbol=cand_sym,
            target_file=authoritative_file,
            condition=""
        )
        clean, _reason = evaluate_compiler_error_freedom(temp_inv, compiler_output)
        if not clean:
            continue

        inv_id = f"INV-SYM-{cand_sym}"
        discovered.append(LockedInvariant(
            invariant_id=inv_id,
            category="SYMBOL_DECLARATION",
            description=(
                f"Kelas '{cand_sym}' dideklarasikan dalam AST '{authoritative_file}' "
                f"dan bebas dari galat kompilasi undefined symbol"
            ),
            target_symbol=cand_sym,
            target_file=authoritative_file,
            condition=f"Symbol '{cand_sym}' exists in AST and compiler output is clean",
            status="PROVEN",
            state="LOCKED",
            evidence_source="DETERMINISTIC_DIAGNOSTIC_EVALUATION",
            evidence=(
                f"AST: class '{cand_sym}' present in '{authoritative_file}'; "
                f"Compiler: no missing-symbol error for '{cand_sym}'"
            ),
            proven_at_turn=turn,
            proven_by_validator="B5_EXECUTOR_ITERATION",
            provenance={
                "candidate_sources": ["evidence_extraction"],
                "turn_proven": turn,
                "evidence_class": "DETERMINISTIC"
            }
        ))

    # --- Gate CONSTRUCTOR_PARAM ---
    for pname in param_candidates:
        for cname, cdata in symbols["classes"].items():
            # Gate 1: Parameter harus ada di konstruktor kelas ini di AST saat ini
            if pname not in cdata.get("parameters", []):
                continue

            # Gate 2: Kompilasi saat ini bersih dari galat "No named parameter 'pname'"
            pname_error_pattern = (
                rf"No named parameter with the name\s*['\"]?{re.escape(pname)}['\"]?"
            )
            if re.search(pname_error_pattern, compiler_output, re.IGNORECASE):
                continue

            inv_id = f"INV-PARAM-{cname}-{pname}"
            discovered.append(LockedInvariant(
                invariant_id=inv_id,
                category="CONSTRUCTOR_PARAM",
                description=(
                    f"Konstruktor '{cname}' menerima named parameter '{pname}' "
                    f"di '{authoritative_file}'"
                ),
                target_symbol=f"{cname}.{pname}",
                target_file=authoritative_file,
                condition=f"Constructor for '{cname}' accepts named parameter '{pname}'",
                status="PROVEN",
                state="LOCKED",
                evidence_source="DETERMINISTIC_DIAGNOSTIC_EVALUATION",
                evidence=(
                    f"Constructor '{cname}' accepts param '{pname}' "
                    f"in '{authoritative_file}'; Compiler: no named-parameter error"
                ),
                proven_at_turn=turn,
                proven_by_validator="B5_EXECUTOR_ITERATION",
                provenance={
                    "candidate_sources": ["evidence_extraction"],
                    "violation_resolved": "named_parameter_mismatch",
                    "turn_proven": turn,
                    "evidence_class": "DETERMINISTIC"
                }
            ))

    # --- Gate PASSING_TEST (unchanged) ---
    current_passed = list(test_results.get("passed_test_names") or [])
    for tname in current_passed:
        clean_name = tname.split("::")[-1].strip()
        inv_id = f"INV-BEHAVIOR-{clean_name[:30].replace(' ', '_')}"
        discovered.append(LockedInvariant(
            invariant_id=inv_id,
            category="PASSING_TEST",
            description=f"Unit test '{clean_name}' lulus di sandbox runner (behavioral contract satisfied)",
            target_symbol=clean_name,
            target_file=authoritative_file,
            condition=f"Test '{clean_name}' passes in sandbox execution",
            status="PROVEN",
            state="LOCKED",
            evidence_source="SANDBOX_TEST_RUNNER",
            evidence=f"Test result: {tname} PASSED",
            proven_at_turn=turn,
            proven_by_validator="B5_EXECUTOR_ITERATION",
            provenance={
                "test_name": tname,
                "turn_proven": turn,
                "evidence_class": "DETERMINISTIC"
            }
        ))

    unique_discovered: Dict[str, LockedInvariant] = {}
    for inv in discovered:
        unique_discovered[inv.invariant_id] = inv
    return list(unique_discovered.values())



def revalidate_locked_invariants(
    locked_invariants: Dict[str, Any],
    code_files: Dict[str, str],
    test_results: Dict[str, Any],
    target_lang: str,
    turn: int = 0
) -> Tuple[Dict[str, LockedInvariant], List[LockedInvariant], List[LockedInvariant]]:
    """
    Evaluasi ulang SELURUH invariant yang terkunci terhadap kondisi kode aktual saat ini.
    Mengembalikan:
    (updated_registry, newly_regressed_list, maintained_proven_list)
    """
    updated_registry: Dict[str, LockedInvariant] = {}
    newly_regressed: List[LockedInvariant] = []
    maintained_proven: List[LockedInvariant] = []

    current_passed_tests = set(test_results.get("passed_test_names") or [])

    for inv_id, raw_inv in locked_invariants.items():
        inv = LockedInvariant.from_dict(raw_inv) if isinstance(raw_inv, dict) else raw_inv

        if inv.category in ("SYMBOL_DECLARATION", "CONSTRUCTOR_PARAM"):
            ok, reason = evaluate_symbol_invariant(inv, code_files, target_lang)
            if not ok:
                inv.record_regression(failure_evidence=reason, turn=turn)
                newly_regressed.append(inv)
            else:
                if inv.status == "REGRESSION":
                    inv.record_recovery(recovery_evidence=reason, turn=turn)
                else:
                    inv.revalidated_at_turn = turn
                    inv.status = "PROVEN"
                    inv.state = "LOCKED"
                maintained_proven.append(inv)

        elif inv.category == "PASSING_TEST":
            tname = inv.target_symbol
            is_still_passing = any(tname in pt for pt in current_passed_tests)
            if not is_still_passing and test_results.get("exit_code") != 0:
                inv.record_regression(
                    failure_evidence=f"Test '{tname}' tidak lagi lulus pada sandbox putaran {turn}",
                    turn=turn
                )
                newly_regressed.append(inv)
            else:
                if inv.status == "REGRESSION" and is_still_passing:
                    inv.record_recovery(recovery_evidence=f"Test '{tname}' kembali lulus", turn=turn)
                maintained_proven.append(inv)

        elif inv.category in ("CONTRACT_STATUS", "ORACLE_INTEGRITY"):
            maintained_proven.append(inv)

        else:
            maintained_proven.append(inv)

        updated_registry[inv_id] = inv

    return updated_registry, newly_regressed, maintained_proven


# ===========================================================================
# 4. Context Separator & Formatter (Section D & J Mandat IA)
# ===========================================================================

def format_separated_repair_context(
    locked_invariants: List[LockedInvariant],
    current_failures: List[Dict[str, Any]],
    regressions: List[LockedInvariant],
    repair_boundary_allowed: List[str],
    repair_boundary_forbidden: List[str],
    target_file: str = "main.py"
) -> str:
    """
    Menghasilkan 4 Dimensi Konteks Perbaikan Eksplisit sesuai Section D & J Mandat IA:
    [LOCKED / PROVEN INVARIANTS]
    [CURRENT FAILURES]
    [REPAIR BOUNDARY]
    [EXPECTED POST-REPAIR STATE]
    """
    sections: List[str] = []

    proven_invs = [inv for inv in locked_invariants if inv.status == "PROVEN"]
    sections.append(f"[LOCKED / PROVEN INVARIANTS ({len(proven_invs)} locked — ONCE PROVEN, LOCK IT)]")
    if proven_invs:
        for inv in proven_invs:
            osc_tag = " [OSCILLATION DETECTED - PREVIOUSLY FLIPPED]" if inv.oscillation_detected else ""
            sections.append(f"- [{inv.invariant_id}]{osc_tag}")
            sections.append(f"  Condition: {inv.condition}")
            sections.append(f"  Description: {inv.description}")
            sections.append(f"  Evidence: {str(inv.evidence)[:120]}")
            sections.append(f"  Status: {inv.status} (Proven at Turn {inv.proven_at_turn})")
            sections.append(f"  Mutation: CONDITION MUST REMAIN TRUE (BEHAVIORAL_MUTATION: FORBIDDEN)")
    else:
        sections.append("(Belum ada invarian terkunci pada putaran ini)")

    total_failures = len(current_failures) + len(regressions)
    sections.append(f"\n[CURRENT FAILURES ({total_failures} failures require repair)]")
    if regressions:
        sections.append("CRITICAL REGRESSIONS (Kondisi yang sebelumnya PROVEN kini dirusak):")
        for reg in regressions:
            sections.append(f"- [REGRESSION] [{reg.invariant_id}] {reg.description}")
            sections.append(f"  Target: {reg.target_symbol} in '{reg.target_file}'")
            if reg.regression_history:
                sections.append(f"  Failure Evidence: {reg.regression_history[-1].get('failure_evidence')}")
            sections.append(f"  Required Action: WAJIB PULIHKAN KONDISI INI! Jangan hapus atau ganti nama!")

    if current_failures:
        sections.append("ACTIVE FAILURES:")
        for idx, f in enumerate(current_failures, 1):
            msg = f.get("message") or f.get("observed_state") or str(f)
            sym = f.get("observed_symbol") or ""
            sym_str = f" [symbol: {sym}]" if sym else ""
            sections.append(f"- [FAIL-{idx:03d}]{sym_str} {msg}")

    sections.append("\n[REPAIR BOUNDARY]")
    sections.append("ALLOWED CHANGES (Apa yang boleh diubah):")
    for ac in repair_boundary_allowed:
        sections.append(f"  + {ac}")
    sections.append("FORBIDDEN CHANGES (DILARANG KERAS / DETERMINISTICALLY REJECTED):")
    for fc in repair_boundary_forbidden:
        sections.append(f"  ! {fc}")
    sections.append("  ! DO NOT break any condition listed under [LOCKED / PROVEN INVARIANTS]")
    sections.append("  ! DO NOT delete or rename previously proven symbols to satisfy new failures")

    sections.append("\n[EXPECTED POST-REPAIR STATE]")
    sections.append("- Seluruh active failures teratasi dan kompilasi sandbox bersih (exit_code == 0).")
    sections.append("- SEMUA kondisi di dalam [LOCKED / PROVEN INVARIANTS] tetap terpenuhi 100% (Zero Regression).")
    if proven_invs:
        inv_names = [inv.target_symbol for inv in proven_invs if inv.target_symbol]
        sections.append(f"- Simbol/kondisi yang wajib tetap eksis: {', '.join(inv_names)}")
    sections.append("- Tidak ada osilasi atau pembalikan status invariant.")

    return "\n".join(sections)
