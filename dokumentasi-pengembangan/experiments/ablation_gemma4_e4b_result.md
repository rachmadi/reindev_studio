# Laporan Eksperimen: 9-Run Controlled Ablation (gemma4:e4b)
## Model: `gemma4:e4b` (100% Unified Squad)
**Tanggal:** 2026-09-09 23:41 WIB  
**Durasi Total:** 4533.3s (~75.56 menit)  
**Pass Rate:** **2/9 (22.2%)**  

## Ringkasan Per Task

| Task ID | Domain | Rep 1 | Rep 2 | Rep 3 | Pass Rate |
|---|---|:---:|:---:|:---:|:---:|
| `fastapi_t1` | python | FAIL | PASS | FAIL | **1/3** |
| `cli_t1` | python | FAIL | FAIL | PASS | **1/3** |
| `flutter_t1` | dart | FAIL | FAIL | FAIL | **0/3** |

## Rincian 9 Run

| Run ID | Task | Verdict | Oracle | Loops | Duration | Failure Category |
|---|---|:---:|:---:|:---:|:---:|---|
| `project_gemma4_fastapi_t1_rep1_20260909_222622` | `fastapi_t1` | **FAIL** | 1/5 | 3 | 510.6s | Developer Reasoning |
| `project_gemma4_fastapi_t1_rep2_20260909_223453` | `fastapi_t1` | **PASS** | 5/5 | 2 | 479.3s | None |
| `project_gemma4_fastapi_t1_rep3_20260909_224252` | `fastapi_t1` | **FAIL** | 1/5 | 3 | 512.7s | Developer Reasoning |
| `project_gemma4_cli_t1_rep1_20260909_225125` | `cli_t1` | **FAIL** | 0/5 | 3 | 497.6s | Developer Reasoning |
| `project_gemma4_cli_t1_rep2_20260909_225943` | `cli_t1` | **FAIL** | 0/1 | 3 | 511.3s | Developer Reasoning |
| `project_gemma4_cli_t1_rep3_20260909_230814` | `cli_t1` | **PASS** | 5/5 | 2 | 504.5s | None |
| `project_gemma4_flutter_t1_rep1_20260909_231638` | `flutter_t1` | **FAIL** | 0/1 | 3 | 511.2s | Developer Reasoning |
| `project_gemma4_flutter_t1_rep2_20260909_232510` | `flutter_t1` | **FAIL** | 0/1 | 3 | 493.3s | Developer Reasoning |
| `project_gemma4_flutter_t1_rep3_20260909_233323` | `flutter_t1` | **FAIL** | 0/3 | 3 | 512.5s | Developer Reasoning |