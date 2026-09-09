# Laporan Eksperimen: 9-Run Controlled Ablation Qwen 2.5 Coder 7B vNext

**Model Squad & Developer:** `qwen2.5-coder:7b` (100% Unified Local Squad)  
**Architect Version:** `vNext + Blueprint Validator (v1.1.0)`  
**Tanggal Eksekusi:** 2026-09-10 01:33:48 WIB  
**Total Durasi:** 2446.7s (~40.8 menit)  
**Gross Pass Rate:** **0 / 9 (0.0%)**  

---

## 1. Ringkasan Eksekutif & Failure Transition

| Dimensi Evaluasi | Qwen 7B Baseline (Sebelumnya) | Qwen 7B vNext (Sekarang) |
|---|---|---|
| **FastAPI T1** | 0 / 3 (0.0%) | 0 / 3 (0.0%) |
| **CLI T1** | 0 / 3 (0.0%) | 0 / 3 (0.0%) |
| **Flutter T1** | 0 / 3 (0.0%) | 0 / 3 (0.0%) |
| **Total Pass Rate** | **0 / 9 (0.0%)** | **0 / 9 (0.0%)** |
| **Rata-rata Durasi** | ~217 s / run | 271.9 s / run |
| **Total Blueprint Revisions** | 0 (Tanpa Validator) | 8 |

---

## 2. Rincian Eksekusi per Run

| Run | Task | Rep | Status | Tests Pass | Loops | Duration | Contract | BP Rev | Failure Category | Detail Error |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | fastapi_t1 | 1 | **FAIL** | 1/5 | 3 | 335.0s | FROZEN | 2 | Developer Reasoning | `test_main.py::test_create_product FAILED                    ` |
| 2 | fastapi_t1 | 2 | **FAIL** | 0/1 | 3 | 363.1s | FROZEN | 2 | Developer Reasoning | `E   NameError: name 'field_validator' is not defined` |
| 3 | fastapi_t1 | 3 | **FAIL** | 0/1 | 3 | 306.3s | FROZEN | 2 | Developer Reasoning | `E   NameError: name 'field_validator' is not defined` |
| 4 | cli_t1 | 1 | **FAIL** | 0/0 | 0 | 135.3s | REJECTED | 0 | Contract / Specification | `Pilar 4 (Oracle Consistency): CONTRACT_VALIDATION_FAILED

re` |
| 5 | cli_t1 | 2 | **FAIL** | 0/1 | 3 | 464.4s | FROZEN | 2 | Developer Reasoning | `E   NameError: name 'field_validator' is not defined` |
| 6 | cli_t1 | 3 | **FAIL** | 0/0 | 0 | 117.4s | REJECTED | 0 | Contract / Specification | `Pilar 2 (Integritas): Duplikasi model_name terdeteksi: 'Matr` |
| 7 | flutter_t1 | 1 | **FAIL** | 0/1 | 3 | 241.1s | FROZEN | 0 | Developer Reasoning | `  Compilation failed for testPath=D:/Pekerjaan/Antigravity/r` |
| 8 | flutter_t1 | 2 | **FAIL** | 0/1 | 3 | 231.5s | FROZEN | 0 | Developer Reasoning | `  Compilation failed for testPath=D:/Pekerjaan/Antigravity/r` |
| 9 | flutter_t1 | 3 | **FAIL** | 0/1 | 3 | 252.4s | FROZEN | 0 | Developer Reasoning | `  Compilation failed for testPath=D:/Pekerjaan/Antigravity/r` |

---
*Laporan ini dihasilkan secara otomatis oleh runner eksperimen terkontrol ReinDev Studio.*
