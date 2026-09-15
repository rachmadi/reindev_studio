# Laporan Evaluasi Pilot — Treatment #1.2
## Universal Acceptance Invocation & Construction Compatibility v1

**Tanggal:** 2026-09-15  
**Branch:** `experiment/fastapi-recovery`  
**Commit:** `698aa8a`  
**Model:** `qwen2.5-coder:7b`  
**Percobaan:** 1x3 Controlled Pilot (fastapi_t1, cli_t1, flutter_t1)  

---

## 1. Ringkasan Eksekutif

| Task | Verdict | Tests | Loops | Duration | Trajectory |
|---|---|---|---|---|---|
| `fastapi_t1` | ❌ FAIL | 4/5 | 5 | 242.2s | divergent |
| `cli_t1` | ✅ **PASS** | **5/5** | **0** | 199.5s | convergent |
| `flutter_t1` | ✅ **PASS** | **2/2** | **0** | 322.4s | convergent |

**Stopping Rule (3/3 PASS): ❌ BELUM TERCAPAI — 2/3 PASS**

---

## 2. Bug Fixes yang Diterapkan (commit `698aa8a`)

### Fix #1 — External Modules Filter (`canonical_obligation.py`)
**Masalah:** `PythonOracleAstVisitor` mengekstrak `pytest.raises()` sebagai callable obligation aplikasi.  
**Root cause:** Visitor tidak memfilter import dari modul pengujian/stdlib.  
**Solusi:** Tambah `self.external_modules` set; track via `visit_ImportFrom`. Skip attribute calls pada modul eksternal.  
**Impact:** cli_t1 berubah dari **0/5 FAIL → 5/5 PASS** (Loops: 0, Convergent)

### Fix #2 — Dart Balanced Parentheses Scanner (`architect_validator.py`)
**Masalah:** `validate_dart_blueprint_consistency` menggunakan regex flat — menyebabkan nested constructor arguments (mis. `MetricData(title: ..., value: ...)`) dilaporkan sebagai invalid params untuk outer constructor (`CardMetric`).  
**Solusi:** Ganti dengan balanced parentheses scanner + `_extract_top_level_named_args_dart()` helper.  
**Impact:** flutter_t1 Architect Gate berubah dari **FAIL (false positive) → PASS**. Developer konvergen pada Iter 0 → **2/2 PASS**.

### Fix #3 — Blueprint Forwarding ke State (`agents/architect.py`)
**Masalah:** `architect_agent` tidak mengembalikan `architectural_blueprint` ke `SquadState`.  
**Solusi:** Return `"architectural_blueprint": bp_dict` dari `architect_agent`. Attach `files` scaffold ke `aligned_contract["files"]`.  
**Impact:** `check_call_shape_compatibility` kini dapat menginspeksi code scaffold untuk deteksi INCOMPATIBLE call shape.

---

## 3. Analisis Per Task

### ✅ cli_t1 — PASS (5/5, Loops: 0)

**Before Treatment #1.2:** Selalu FAIL karena `pytest.raises` diekstrak sebagai obligasi aplikasi.  
**After Treatment #1.2:** Obligasi bersih: `['Matrix', 'add_matrices', 'subtract_matrices', 'multiply_matrices']`. Developer menghasilkan kode yang lulus semua 5 test pada Turn 0.  
**Trajectory:** Convergent ✅

---

### ✅ flutter_t1 — PASS (2/2, Loops: 0)

**Before Treatment #1.2:** Architect Gate terus FAIL karena false positive parameter mismatch pada `CardMetric`.  
**After Treatment #1.2:** Balanced scanner membatasi ekstraksi ke top-level named args. Architect Gate PASS: coverage 2/2, 0 INCOMPATIBLE. Developer konvergen pada Iter 0.  
**Trajectory:** Convergent ✅

---

### ❌ fastapi_t1 — FAIL (4/5, Loops: 5, divergent)

**Failing Test:** `test_delete_nonexistent_product`

```
assert response.status_code == 404
AssertionError: assert 204 == 404
 +  where 204 = <Response [204 No Content]>.status_code
```

**Analisis:** Developer mengimplementasikan DELETE endpoint yang menghapus resource apapun dan mengembalikan `204 No Content`. Oracle mengharapkan `404 Not Found` untuk ID yang tidak ada.

**Klasifikasi Failure:** `A. Developer Failure` — Semantic gap LLM pada edge case REST API. Treatment #1.2 tidak menargetkan semantic correctness HTTP method. Contract FROZEN dengan benar (obligasi coverage penuh).

---

## 4. Evaluasi Stopping Rule

| Kriteria | Target | Hasil |
|---|---|---|
| Pilot berhasil dijalankan | 3 runs | 3/3 ✅ |
| Oracle SHA intact | Semua | ✅ semua intact |
| OTRR (Oracle Tampering Rate) | 0% | 0.0% ✅ |
| Tester agent invocations | 0 | 0 ✅ |
| **3/3 PASS** | **3** | **2/3 ❌** |

**Kesimpulan:** Stopping rule **BELUM TERCAPAI**. 2/3 task PASS.

---

## 5. Pre-Flight Verification Gates

Semua gates A–I lulus sebelum pilot dimulai (599 tests, 1 warning):

| Gate | Status |
|---|---|
| A: Static Code Compilation | ✅ PASS |
| B: Baseline Regression (599 tests) | ✅ PASS |
| C: Oracle SHA-256 Checksum | ✅ PASS |
| D: Tester LLM Isolation | ✅ PASS |
| E: Dry-Run Phase Transition | ✅ PASS |
| F: Phase-End Validator Boundary | ✅ PASS |
| G: Validator Failure Halt | ✅ PASS |
| H: Validator PASS Propagation | ✅ PASS |
| I: Telemetry Recording | ✅ PASS |

---

## 6. Dampak Treatment #1.2 (Assessment)

| Root Cause | Fix | Status |
|---|---|---|
| pytest.raises leak sebagai obligasi | External modules filter | ✅ Resolved (cli_t1 PASS) |
| Dart constructor false positive | Balanced paren scanner | ✅ Resolved (flutter_t1 PASS) |
| Blueprint tidak diteruskan ke state | `architectural_blueprint` forwarding | ✅ Resolved |
| LLM semantic gap: REST error semantics (204 vs 404) | Tidak ditargetkan Treatment #1.2 | ❌ Masih open |

---

## 7. Rekomendasi Treatment #1.3

**Target:** fastapi_t1 REST error semantics gap

**Root cause spesifik:** DELETE pada non-existent resource mengembalikan `204` bukan `404`. LLM tidak memiliki konteks tentang expected HTTP error behavior.

**Opsi intervensi (tanpa hardcoding):**
1. **Context enrichment:** Inject HTTP error semantics sebagai constraint generik ke context Developer (mis. "Implementasikan proper HTTP status code untuk semua error conditions — including resource not found")
2. **Obligation scenario enrichment:** Ekstrak skenario negative path dari oracle test file dan sertakan sebagai bagian dari obligation context
3. **Contract constraint field:** Tambah field `http_error_behavior` ke kontrak untuk REST API tasks

---

## 8. Metadata Pilot

| Field | Value |
|---|---|
| Experiment ID | `phase_end_validation_pilot` |
| Model | `qwen2.5-coder:7b` |
| Reps per task | 1 |
| Total runs | 3 |
| Pass count | 2 |
| Aggregate OTRR | 0.0% |
| Total duration | ~764s (~12.7 menit) |
| Branch | `experiment/fastapi-recovery` |
| Commit | `698aa8a` |
| Summary file | `dokumentasi-pengembangan/experiments/treatment1_2_pilot_summary.json` |

---

*Laporan dibuat otomatis pada 2026-09-15T11:42 WIB*
