# Laporan Eksperimen: 9-Run Controlled Frontier Ablation
## Developer Model: `google/gemma-4-26b-a4b-it` (Google DeepMind)
**Metodologi:** IIDD (Iterative Intent-Driven Development) — Siklus I-CERV  
**Tanggal Eksekusi:** 2026-09-09 19:49 – 20:11 WIB  
**Durasi Total:** 1.287,2 detik (~21,45 menit)  
**Tujuan:** Menguji performa model MoE (Mixture-of-Experts) 26B dengan parameter aktif 4B (`google/gemma-4-26b-a4b-it`) sebagai Developer Agent di bawah kondisi pipeline yang dikunci identik 100% terhadap baseline Qwen 7B dan Gemini 3.8 Flash.

---

## 1. Kondisi Eksperimen yang Dikunci (Controlled Variables)

Seluruh komponen pipeline ReinDev Studio dikunci identik tanpa variasi:
* **Squad Baseline:** `qwen2.5-coder:7b` (PM, System Architect, Reviewer) via Ollama lokal.
* **P0-2.1 Pre-Freeze Contract Integrity Gate:** ACTIVE (penegakan interface & method signatures).
* **P0-1 Semantic Diagnostic Guidance:** ACTIVE (injeksi `[ACTIONABLE HINT]` berbasis failure classification).
* **Executor Sandbox:** SAFE Mode (AST-based parsing, zero destructive regex rewriting).
* **Batas Siklus Perbaikan (Self-Healing Loop):** Maksimal 3 Loop.
* **Frozen Oracle:** 3 Task Suite terkunci kriptografis SHA-256 (Audit pre-run dan post-run: **100% MATCH**).
* **Satu-satunya Variabel Independen:** `Developer Model = google/gemma-4-26b-a4b-it`.

---

## 2. Hasil Agregat Matriks 9 Run

| Metrik | Hasil Empiris | Catatan |
|---|:---:|---|
| **Total Run** | **9 Run** | 3 Task × 3 Replikasi |
| **Gross Pass Rate** | **5 / 9 (55.6%)** | Lolos end-to-end tanpa intervensi manusia |
| **Net Reasoning Pass Rate** | **5 / 6 (83.3%)** | Dari 6 run yang tidak terkendala jaringan |
| **Infrastructure / Transport Failure** | **3 / 9 (33.3%)** | Socket dropped / upstream timeout OpenRouter |
| **Developer Reasoning Failure** | **1 / 9 (11.1%)** | Sintaks Dart tanda kurung tidak seimbang pada Flutter Rep 2 |
| **Total Biaya Komputasi API** | **~$0.0053 (~Rp 85)** | 61.349 token (sangat ekonomis) |

---

## 3. Matriks Hasil Rinci Per Task

### A. Task 1: `fastapi_t1` (CRUD REST API & Pydantic Validation)
* **Hasil:** **3 / 3 PASS (100.0%)** — Sempurna!
* **Rep 1:** ✅ **PASS** (Loop 1, 113.9s) — 5/5 assertions PASS, Reviewer `[APPROVED]`, cost $0.000644.
* **Rep 2:** ✅ **PASS (Direct Loop 0)** (86.7s) — 5/5 assertions PASS, Reviewer `[APPROVED]`, cost $0.000299.
* **Rep 3:** ✅ **PASS (Direct Loop 0)** (103.3s) — 5/5 assertions PASS, Reviewer `[APPROVED]`, cost $0.000306.
* **Analisis Kausal:** Gemma 4 26B A4B secara intuitif membedakan schema DTO `ProductCreate` vs `ProductResponse`. Tidak ada satupun kegagalan HTTP 422 atau stagnasi semantik seperti pada Qwen 7B.

### B. Task 2: `cli_t1` (Matrix Calculator OOP & Dunder Methods)
* **Hasil:** **1 / 3 Gross PASS (33.3%) | 1 / 1 Net Reasoning PASS (100.0%)**
* **Rep 1:** ✅ **PASS (Direct Loop 0)** (143.7s) — 5/5 assertions PASS, Reviewer `[APPROVED]`, latency gateway 70.6s.
* **Rep 2:** ❌ **FAIL (Infrastructure / Transport)** (82.2s) — Socket dropped OpenRouter pada transisi Loop 1.
* **Rep 3:** ❌ **FAIL (Infrastructure / Transport)** (250.3s) — Timeout upstream OpenRouter pada Loop 2 (gateway latency mencapai 201s).
* **Analisis Kausal:** Pada run di mana koneksi stabil (Rep 1), Gemma 4 26B langsung menyelesaikan seluruh implementasi Matrix OOP dan dunder methods (`__add__`, `__mul__`, `__truediv__`) pada Loop 0 dengan 5/5 lulus. Dua kegagalan murni masalah latensi jaringan upstream API OpenRouter.

### C. Task 3: `flutter_t1` (Card Metric Widget MD3 & Riverpod)
* **Hasil:** **1 / 3 Gross PASS (33.3%) | 1 / 2 Net Reasoning PASS (50.0%)**
* **Rep 1:** ❌ **FAIL (Infrastructure / Transport)** (105.0s) — Transport error saat pemanggilan Loop 2.
* **Rep 2:** ❌ **FAIL (Developer Reasoning)** (227.6s) — Model menghasilkan sintaks Dart dengan tanda kurung tutup hilang pada baris 60 (`Can't find ')' to match '('`). Reviewer Dual-Layer menolak dengan status `NEEDS_REVISION`.
* **Rep 3:** ✅ **PASS** (Loop 1, 174.2s) — 2/2 assertions PASS, Reviewer `[APPROVED]`, cost $0.000788.
* **Analisis Kausal:** Gemma 4 26B A4B mampu menulis kode Flutter Riverpod yang valid dan lulus uji widget (Rep 3), namun pada Rep 2 model mengalami defek sintaksis lokal (unbalanced parenthesis) yang gagal dipulihkan hingga batas 3 loop.

---

## 4. Perbandingan Komparatif 4 Kondisi Model (Cross-Model Benchmark)

| Task / Metrik | Baseline Qwen 7B | Qwen 7B + P0-2.1 + P0-1 | Gemini 3.8 Flash | Gemma 4 26B A4B (MoE) |
|---|:---:|:---:|:---:|:---:|
| **FastAPI T1 (CRUD)** | 0 / 3 (0.0%) | 1 / 3 (33.3%) | **3 / 3 (100.0%)** | **3 / 3 (100.0%)** |
| **CLI T1 (Matrix OOP)** | 0 / 3 (0.0%) | 0 / 3 (0.0%) | 1 / 3 (33.3% gross, 100% net) | 1 / 3 (33.3% gross, 100% net) |
| **Flutter T1 (Widget)** | 2 / 3 (66.7%) | 1 / 3 (33.3%) | **3 / 3 (100.0%)** | 1 / 3 (33.3% gross, 50% net) |
| **Gross Pass Rate** | **33.3% (3/9)** | **22.2% (2/9)** | **77.8% (7/9)** | **55.6% (5/9)** |
| **Net Reasoning Pass Rate** | **33.3% (3/9)** | **22.2% (2/9)** | **100.0% (7/7)** | **83.3% (5/6)** |
| **Reasoning Failures** | 6 run (100%) | 7 run (100%) | **0 run (0.0%)** | **1 run (11.1%)** |
| **Transport Failures** | 0 run | 0 run | 2 run (22.2%) | 3 run (33.3%) |
| **Kriptografis SHA-256 Oracle** | 100% MATCH | 100% MATCH | 100% MATCH | 100% MATCH |

---

## 5. Kesimpulan & Temuan Ilmiah

1. **Konfirmasi Tambahan untuk Skenario A:**  
   Peningkatan pass rate dari Qwen 7B (22.2% - 33.3%) ke Gemma 4 26B A4B (55.6% gross / 83.3% net) semakin mengukuhkan bahwa kapasitas parameter penalaran model adalah faktor determinan utama. Pada task arsitektural REST API (`fastapi_t1`), Gemma 4 menyamai Gemini 3.8 Flash dengan kelulusan sempurna 3/3 (100%).
2. **Karakteristik Arsitektur MoE (A4B):**  
   Dengan hanya 3.8B parameter aktif, Gemma 4 26B A4B beroperasi sangat efisien dan murah ($0.005 untuk 9 run). Namun, densitas parameter aktif ~4B terkadang masih memiliki kelemahan kecil pada ketelitian sintaksis bahasa yang sangat ketat seperti Dart (terbukti pada defek unbalanced parenthesis di Flutter Rep 2), berbeda dengan Gemini 3.8 Flash yang mencatat 0 reasoning error.
3. **Kerapuhan Transport Layer Cloud:**  
   Baik pada Gemini 3.8 Flash (2 run timeout) maupun Gemma 4 26B (3 run timeout), kegagalan transport selalu terjadi pada task-task dengan prompt panjang atau multi-loop (CLI & Flutter). Ini membuktikan bahwa mekanisme retry transport atau timeout yang lebih adaptif pada gateway adalah peningkatan teknis yang bermanfaat.