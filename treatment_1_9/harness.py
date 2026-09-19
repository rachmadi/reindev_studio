import os
import sys
import json
import time
import hashlib
import subprocess
import re
import requests
from datetime import datetime

# ==============================================================================
# CONFIGURATION & CONSTANTS
# ==============================================================================
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "qwen2.5-coder:7b"
TEMPERATURE = 0.2
NUM_CTX = 8192
NUM_PREDICT = 2048

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ORACLE_FILE = os.path.join(BASE_DIR, "oracle_test.py")
OUTPUT_BASE_DIR = os.path.join(BASE_DIR, "output")
PYTEST_EXE = os.path.join(BASE_DIR, "..", "backend", ".venv", "Scripts", "pytest.exe")
if not os.path.exists(PYTEST_EXE):
    PYTEST_EXE = sys.executable

# Production System Prompt from ReinDev Studio backend/agents/developer.py
DEV_SYSTEM_PROMPT = """Anda adalah Senior Software Developer dalam tim rekayasa perangkat lunak ReinDev Studio.
Tugas Anda adalah menulis kode program berkualitas produksi berdasarkan spesifikasi dari Product Manager dan rencana arsitektur dari System Architect.

ATURAN REKAYASA & KEBERSIHAN KODE (STRICT):
1. DILARANG KERAS menyertakan teks obrolan, salam, basa-basi, atau penjelasan di luar kode. Output Anda harus 100% berupa definisi file kode murni.
2. Tulis kode yang lengkap, modular, dengan penanganan kesalahan dan type annotation sesuai target bahasa pemrograman.
3. JANGAN PERNAH menyertakan placeholder seperti '# TODO', '# implement later', atau '...'.
4. DOKTRIN REKAYASA (ENGINEERING DOCTRINE):
   - [AUTHORITATIVE CONTRACT]: Signature dan antarmuka Oracle adalah sumber kebenaran mutlak.
   - [EXCEPTION COMPATIBILITY]: Tipe exception harus kompatibel secara hierarkis (issubclass(Actual, Expected)).
   - [BEHAVIORAL INVARIANT PRESERVATION]: Fungsionalitas/pengujian yang sudah berstatus PROVEN dilarang keras dirusak (BEHAVIORAL_MUTATION: FORBIDDEN).
   - [CAUSAL REPAIR SCOPE]: Modifikasi HANYA kode yang terbukti kausal terhadap kegagalan.
5. Format setiap file kode menggunakan blok penanda khusus persis seperti ini:
=== FILE: [nama_file] ===
[isi kode murni tanpa backtick markdown]
=== END FILE ===

Contoh Python:
=== FILE: calculator.py ===
def add(a: int, b: int) -> int:
    return a + b
=== END FILE ===

Contoh Dart:
=== FILE: lib/calculator.dart ===
class Calculator {
  double add(double a, double b) => a + b;
  double multiply(double a, double b) => a * b;
}
=== END FILE ===
"""

# ==============================================================================
# SCAFFOLDS
# ==============================================================================
SCAFFOLD_A = """def compute_total(numbers: list[int]) -> int:
    return 0
"""

SCAFFOLD_B = """from functools import reduce
import operator

def compute_total(numbers: list[int]) -> int:
    return reduce(operator.mul, numbers, 1)
"""

SCAFFOLD_C = SCAFFOLD_B

# ==============================================================================
# CAUSAL PACKET FOR CONDITION C
# ==============================================================================
CAUSAL_PACKET_C = """
[EXPLICIT CAUSAL EVIDENCE PACKET]
EXPECTED:
compute_total([1, 2, 3, 4]) returns 10.
compute_total([2, 3, 5]) returns 10.
compute_total([0, 4, 7]) returns 11.

ACTUAL:
compute_total([1, 2, 3, 4]) returns 24 when the operation combines the values by multiplication;
compute_total([2, 3, 5]) returns 30;
compute_total([0, 4, 7]) returns 0;
the implementation therefore does not establish summation semantics.

CAUSE:
The implementation combines list elements using multiplication, while the acceptance behavior requires summation.

REQUIRED CHANGE:
Change the implementation so that the elements are combined according to summation semantics.

VERIFICATION:
compute_total([1, 2, 3, 4]) must return 10, compute_total([2, 3, 5]) must return 10, compute_total([0, 4, 7]) must return 11, and the implementation must satisfy the frozen acceptance test.
"""

def compute_sha256(filepath):
    with open(filepath, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def run_pytest(solution_code, workdir):
    sol_path = os.path.join(workdir, "solution.py")
    with open(sol_path, "w", encoding="utf-8") as f:
        f.write(solution_code)

    cmd = [PYTEST_EXE, ORACLE_FILE, "-v", "--tb=short", "-p", "no:warnings"]
    t0 = time.time()
    res = subprocess.run(cmd, cwd=workdir, capture_output=True, text=True)
    duration = round(time.time() - t0, 3)

    stdout = res.stdout
    stderr = res.stderr
    output = (stdout + "\n" + stderr).strip()

    # Parse passed/failed count
    passed_m = re.search(r"(\d+)\s+passed", output)
    failed_m = re.search(r"(\d+)\s+failed", output)

    passed_count = int(passed_m.group(1)) if passed_m else 0
    failed_count = int(failed_m.group(1)) if failed_m else 0
    total_count = passed_count + failed_count

    return {
        "exit_code": res.returncode,
        "passed": res.returncode == 0,
        "passed_count": passed_count,
        "failed_count": failed_count,
        "total_count": total_count,
        "output": output,
        "duration_s": duration
    }

def build_developer_prompt(scaffold_code, test_code, failure_output, extra_causal_packet=""):
    prompt = f"""TARGET BAHASA PEMROGRAMAN: PYTHON

ATURAN PYTHON (WAJIB):
- Tulis kode Python PEP 8 modular dengan type hint murni.
- DILARANG menulis file test atau file non-kode seperti README.md atau requirements.txt (fokus hanya pada file kode .py).
- Pastikan seluruh class/model yang digunakan diimpor secara eksplisit.
- Simpan file implementasi dengan ekstensi .py di root direktori (contoh: === FILE: solution.py ===).
- Seluruh antarmuka yang didefinisikan dalam Kontrak Resmi WAJIB diimplementasikan secara utuh.
- Sesuaikan operasi mutasi internal dengan struktur data yang Anda pilih agar konsisten dengan call-site dan ekspektasi test.

Tugas Pengguna:
Bangun fungsi compute_total(numbers: list[int]) -> int yang menghitung total penjumlahan (sum) dari seluruh elemen list.

Spesifikasi Product Manager:
Fungsi compute_total(numbers: list[int]) -> int menerima sebuah list integer dan mengembalikan hasil penjumlahan seluruh elemennya.
Contoh penerimaan:
- compute_total([1, 2, 3, 4]) menghasilkan 10
- compute_total([2, 3, 5]) menghasilkan 10
- compute_total([0, 4, 7]) menghasilkan 11

[KONTRAK RESMI PROYEK (STRICTLY FROZEN - WAJIB DIPATUHI 100%)]:
- Target File Authoritative (WAJIB): solution.py
- ATURAN MUTLAK TARGET FILE: Developer WAJIB menghasilkan dan memperbaiki kode HANYA pada file target authoritative 'solution.py' (menggunakan blok === FILE: solution.py ===).
- Domain: ALGORITHMIC_UTILITY
- Antarmuka Resmi: compute_total(numbers: list[int]) -> int

[Rencana Arsitektur]: Gunakan Target File Authoritative 'solution.py' dan ikuti Kontrak Resmi di atas.

HASIL DIAGNOSTIK & FEEDBACK PERBAIKAN:
Status Pengujian Terakhir: tests_failed
Ringkasan: 3 failed pengujian acceptance.

HASIL PENGUJIAN TERAKHIR (TEST OUTPUT):
{failure_output}
{extra_causal_packet}
BERKAS KODE TERAKHIR ANDA:
=== FILE: solution.py ===
{scaffold_code.strip()}
=== END FILE ===

BERKAS TEST RUNNER:
=== FILE: test_oracle.py ===
{test_code.strip()}
=== END FILE ===

INSTRUKSI PERBAIKAN:
1. Analisis diagnostik terarah dan perbaiki kegagalan pengujian di atas.
2. Periksa akar penyebab kegagalan dan sesuaikan operasi agar memenuhi ekspektasi test runner.
3. Pastikan antarmuka kode memenuhi ekspektasi test runner dan kontrak resmi.
4. Tuliskan kembali berkas yang diperbaiki dengan Target File Authoritative: 'solution.py'. DILARANG menggunakan nama file lain!

ATURAN KETAT:
Tulis seluruh implementasi file kode HANYA dalam bahasa PYTHON.
Jangan gunakan bahasa pemrograman lain!
WAJIB selesaikan seluruh perbaikan yang diminta pada instruksi diagnostik di atas secara disiplin!
Silakan tulis kode program lengkap sesuai format penanda === FILE: solution.py === tanpa teks obrolan apapun."""
    return prompt

def call_ollama(prompt):
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": DEV_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "options": {
            "temperature": TEMPERATURE,
            "num_ctx": NUM_CTX,
            "num_predict": NUM_PREDICT
        },
        "stream": False
    }
    t0 = time.time()
    resp = requests.post(OLLAMA_URL, json=payload, timeout=120)
    latency = round(time.time() - t0, 3)

    if resp.status_code != 200:
        raise RuntimeError(f"Ollama returned HTTP {resp.status_code}: {resp.text}")

    data = resp.json()
    raw_content = data.get("message", {}).get("content", "")
    return raw_content, latency, data

def parse_code(raw_text):
    # Regex 1: === FILE: solution.py === ... === END FILE ===
    pattern1 = r"===\s*FILE:\s*solution\.py\s*===\s*\n(.*?)\s*===\s*END FILE\s*==="
    m1 = re.search(pattern1, raw_text, re.DOTALL | re.IGNORECASE)
    if m1:
        return m1.group(1).strip(), "file_block_exact"

    # Regex 2: === FILE: ... === without exact name
    pattern2 = r"===\s*FILE:[^\n]*===\s*\n(.*?)\s*===\s*END FILE\s*==="
    m2 = re.search(pattern2, raw_text, re.DOTALL | re.IGNORECASE)
    if m2:
        return m2.group(1).strip(), "file_block_generic"

    # Regex 3: Markdown fence `python ... `
    pattern3 = r"`(?:python)?\s*\n(.*?)\s*`"
    m3 = re.search(pattern3, raw_text, re.DOTALL | re.IGNORECASE)
    if m3:
        return m3.group(1).strip(), "markdown_fence"

    # Fallback: if raw_text contains 'def compute_total', return raw_text stripped
    if "def compute_total" in raw_text:
        return raw_text.strip(), "raw_fallback"

    return "", "parse_failed"

def run_experiment_condition(condition_name, scaffold_code, extra_causal_packet, run_dir, oracle_code):
    cond_dir = os.path.join(run_dir, f"condition_{condition_name.lower()}")
    os.makedirs(cond_dir, exist_ok=True)

    print(f"\n=======================================================")
    print(f"RUNNING CONDITION {condition_name}")
    print(f"=======================================================")

    # Step 1: Initial failure evidence generation
    print(f"[{condition_name}] 1. Running initial verification on scaffold...")
    init_res = run_pytest(scaffold_code, cond_dir)
    print(f"[{condition_name}] Initial tests: {init_res['passed_count']} passed, {init_res['failed_count']} failed")

    with open(os.path.join(cond_dir, "initial_scaffold.py"), "w", encoding="utf-8") as f:
        f.write(scaffold_code)
    with open(os.path.join(cond_dir, "initial_verification.json"), "w", encoding="utf-8") as f:
        json.dump(init_res, f, indent=2)

    # Step 2: Assemble developer prompt
    prompt = build_developer_prompt(
        scaffold_code=scaffold_code,
        test_code=oracle_code,
        failure_output=init_res["output"],
        extra_causal_packet=extra_causal_packet
    )
    with open(os.path.join(cond_dir, "developer_prompt.txt"), "w", encoding="utf-8") as f:
        f.write(prompt)

    # Step 3: Invoke model (1 attempt only)
    print(f"[{condition_name}] 2. Invoking {MODEL_NAME} via Ollama...")
    raw_output, latency, raw_response = call_ollama(prompt)
    print(f"[{condition_name}] Model responded in {latency}s ({len(raw_output)} chars)")

    # CRITICAL RULE: Save raw output BEFORE parsing
    with open(os.path.join(cond_dir, "attempt_1_raw_output.txt"), "w", encoding="utf-8") as f:
        f.write(raw_output)

    # Step 4: Parse code
    parsed_code, parse_method = parse_code(raw_output)
    print(f"[{condition_name}] 3. Parsed code using method: {parse_method} ({len(parsed_code)} chars)")

    with open(os.path.join(cond_dir, "attempt_1_parsed_code.py"), "w", encoding="utf-8") as f:
        f.write(parsed_code)

    # Step 5: Deterministic verification
    print(f"[{condition_name}] 4. Executing deterministic verification on repaired code...")
    verif_res = run_pytest(parsed_code, cond_dir)
    print(f"[{condition_name}] Verification: {verif_res['passed_count']}/{verif_res['total_count']} passed, exit_code={verif_res['exit_code']}")

    with open(os.path.join(cond_dir, "attempt_1_verification.json"), "w", encoding="utf-8") as f:
        json.dump(verif_res, f, indent=2)

    # Step 6: Semantic state and anchoring analysis
    is_repaired = verif_res["passed"]
    code_sha256 = hashlib.sha256(parsed_code.encode("utf-8")).hexdigest() if parsed_code else ""
    initial_sha256 = hashlib.sha256(scaffold_code.encode("utf-8")).hexdigest()

    # Detect operation in parsed code
    has_mul = bool(re.search(r"\bmul\b|\*|operator\.mul", parsed_code))
    has_add = bool(re.search(r"\bsum\(|\+|operator\.add", parsed_code))

    # Anchoring analysis (for B and C)
    if condition_name == "A":
        anchor_status = "NOT_APPLICABLE_NEUTRAL_SCAFFOLD"
    else:
        if is_repaired:
            anchor_status = "ANCHOR_BROKEN"
        elif "24" in verif_res["output"] or "30" in verif_res["output"] or (has_mul and not has_add):
            anchor_status = "ANCHOR_PERSISTED"
        else:
            anchor_status = "ANCHOR_MODIFIED_INCORRECT"

    # Secondary classification
    if parse_method == "parse_failed":
        sec_class = "REPRESENTATION_FAILURE"
    elif is_repaired:
        sec_class = "CORRECT_TARGET_REPAIR"
    elif code_sha256 == initial_sha256:
        sec_class = "NO_SEMANTIC_CHANGE"
    elif not is_repaired and has_mul:
        sec_class = "NO_SEMANTIC_CHANGE" if not has_add else "WRONG_TARGET_REPAIR"
    else:
        sec_class = "WRONG_TARGET_REPAIR"

    metric = {
        "condition": condition_name,
        "model": MODEL_NAME,
        "scaffold_type": "NEUTRAL" if condition_name == "A" else "WRONG_SEMANTIC_MULTIPLICATION",
        "evidence_type": "STANDARD_PYTEST" if condition_name in ("A", "B") else "STANDARD_PYTEST_PLUS_EXPLICIT_CAUSAL",
        "latency_s": latency,
        "raw_output_length": len(raw_output),
        "parse_method": parse_method,
        "parsed_code_sha256": code_sha256,
        "initial_sha256": initial_sha256,
        "code_changed": code_sha256 != initial_sha256,
        "has_mul_operation": has_mul,
        "has_add_operation": has_add,
        "initial_passed": init_res["passed_count"],
        "initial_failed": init_res["failed_count"],
        "repaired_passed": verif_res["passed_count"],
        "repaired_failed": verif_res["failed_count"],
        "repaired_total": verif_res["total_count"],
        "primary_outcome": "REPAIRED" if is_repaired else "NOT_REPAIRED",
        "secondary_classification": sec_class,
        "anchor_status": anchor_status
    }

    with open(os.path.join(cond_dir, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(metric, f, indent=2)

    print(f"[{condition_name}] RESULT: {metric['primary_outcome']} | {metric['secondary_classification']} | Anchor: {metric['anchor_status']}")
    return metric

def main():
    print("=================================================================")
    print("TREATMENT #1.9 — DEVELOPER SEMANTIC REPAIR MICRO-BENCHMARK v1")
    print("=================================================================")
    
    # 1. Verify frozen oracle SHA-256
    if not os.path.exists(ORACLE_FILE):
        print(f"ERROR: Oracle file not found: {ORACLE_FILE}")
        sys.exit(1)

    oracle_sha = compute_sha256(ORACLE_FILE)
    with open(ORACLE_FILE, "r", encoding="utf-8") as f:
        oracle_code = f.read()

    print(f"FROZEN ORACLE SHA-256: {oracle_sha}")

    # 2. Setup run directory
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(OUTPUT_BASE_DIR, f"t19_run_{ts}")
    os.makedirs(run_dir, exist_ok=True)

    metadata = {
        "treatment": "1.9",
        "benchmark_name": "Developer Semantic Repair Capability Controlled Micro-Benchmark v1",
        "timestamp": ts,
        "model": MODEL_NAME,
        "temperature": TEMPERATURE,
        "num_ctx": NUM_CTX,
        "num_predict": NUM_PREDICT,
        "oracle_sha256": oracle_sha,
        "oracle_file": ORACLE_FILE
    }
    with open(os.path.join(run_dir, "run_metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    # 3. Run Condition A
    res_a = run_experiment_condition("A", SCAFFOLD_A, "", run_dir, oracle_code)

    # 4. Run Condition B
    res_b = run_experiment_condition("B", SCAFFOLD_B, "", run_dir, oracle_code)

    # 5. Run Condition C
    res_c = run_experiment_condition("C", SCAFFOLD_C, CAUSAL_PACKET_C, run_dir, oracle_code)

    # Summary
    summary = {
        "metadata": metadata,
        "results": {
            "Condition_A": res_a,
            "Condition_B": res_b,
            "Condition_C": res_c
        }
    }
    with open(os.path.join(run_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n=================================================================")
    print("EXPERIMENT COMPLETED SUCCESSFULLY")
    print(f"Run directory: {run_dir}")
    print(f"Condition A: {res_a['primary_outcome']} ({res_a['secondary_classification']})")
    print(f"Condition B: {res_b['primary_outcome']} ({res_b['secondary_classification']}) Anchor: {res_b['anchor_status']}")
    print(f"Condition C: {res_c['primary_outcome']} ({res_c['secondary_classification']}) Anchor: {res_c['anchor_status']}")
    print("=================================================================")

if __name__ == "__main__":
    main()
