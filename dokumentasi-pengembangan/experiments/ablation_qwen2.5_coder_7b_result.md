# Laporan Eksperimen: 9-Run Controlled Ablation (qwen2.5-coder:7b)
## Model: `qwen2.5-coder:7b` (100% Unified Squad)
**Tanggal:** 2026-09-10 00:17 WIB  
**Durasi Total:** 1951.7s (~32.53 menit)  
**Pass Rate:** **0/9 (0.0%)**  

## Ringkasan Per Task

| Task ID | Domain | Rep 1 | Rep 2 | Rep 3 | Pass Rate |
|---|---|:---:|:---:|:---:|:---:|
| `fastapi_t1` | python | FAIL | FAIL | FAIL | **0/3** |
| `cli_t1` | python | FAIL | FAIL | FAIL | **0/3** |
| `flutter_t1` | dart | FAIL | FAIL | FAIL | **0/3** |

## Rincian 9 Run

| Run ID | Task | Verdict | Oracle | Loops | Duration | Failure Category |
|---|---|:---:|:---:|:---:|:---:|---|
| `project_qwen7b_fastapi_t1_rep1_20260909_234440` | `fastapi_t1` | **FAIL** | 0/1 | 3 | 197.6s | Developer Reasoning |
| `project_qwen7b_fastapi_t1_rep2_20260909_234758` | `fastapi_t1` | **FAIL** | 0/1 | 3 | 200.9s | Developer Reasoning |
| `project_qwen7b_fastapi_t1_rep3_20260909_235119` | `fastapi_t1` | **FAIL** | 0/1 | 3 | 213.3s | Developer Reasoning |
| `project_qwen7b_cli_t1_rep1_20260909_235452` | `cli_t1` | **FAIL** | 3/5 | 3 | 386.4s | Developer Reasoning |
| `project_qwen7b_cli_t1_rep2_20260910_000119` | `cli_t1` | **FAIL** | 0/0 | 0 | 84.2s | Contract / Specification |
| `project_qwen7b_cli_t1_rep3_20260910_000243` | `cli_t1` | **FAIL** | 0/0 | 0 | 91.5s | Contract / Specification |
| `project_qwen7b_flutter_t1_rep1_20260910_000415` | `flutter_t1` | **FAIL** | 0/1 | 3 | 240.0s | Developer Reasoning |
| `project_qwen7b_flutter_t1_rep2_20260910_000815` | `flutter_t1` | **FAIL** | 0/1 | 3 | 268.4s | Developer Reasoning |
| `project_qwen7b_flutter_t1_rep3_20260910_001243` | `flutter_t1` | **FAIL** | 0/1 | 3 | 269.2s | Developer Reasoning |