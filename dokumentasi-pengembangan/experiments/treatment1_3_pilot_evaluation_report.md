# Laporan Evaluasi Pilot — Treatment #1.3
## Universal Acceptance Behavior & Scenario Grounding v1

**Tanggal:** 2026-09-15  
**Branch:** `experiment/fastapi-recovery`  
**Commit:** `7bf0702`  
**Model:** `qwen2.5-coder:7b`  
**Percobaan:** 1x3 Controlled Acceptance Pilot (`fastapi_t1`, `cli_t1`, `flutter_t1`)  

---

## 1. Ringkasan Eksekutif

| Task | Domain / Target | Verdict | Tests | Loops | Duration | Trajectory | Status |
|---|---|---|---|---|---|---|---|
| `fastapi_t1` | REST API (Python) | ✅ **PASS** | **5/5** | **0** | 325.0s | convergent | Lolos Turn 0 |
| `cli_t1` | CLI / Math (Python) | ✅ **PASS** | **5/5** | **2** | 222.8s | convergent | Lolos ≤ 3 loops |
| `flutter_t1` | UI Widget (Dart) | ✅ **PASS** | **2/2** | **0** | 429.3s | convergent | Lolos Turn 0 |

### **Stopping Rule Status: ✅ TERCAPAI (3/3 PASS — 100% SUCCESS RATE)**
- **Baseline c491982 / Treatment #1.2**: 2/3 PASS (`fastapi_t1` selalu 4/5 FAIL karena mengembalikan 204 No Content alih-alih 404 Not Found pada skenario penghapusan entitas non-eksisten).
- **Treatment #1.3**: **3/3 PASS (100%)** — `fastapi_t1` langsung lulus 5/5 pada Turn 0 tanpa memerlukan repair loop tambahan.

---

## 2. Latar Belakang & Masalah Pokok

Sebelum Treatment #1.3, sistem mengalami defisit informasi observable behavior:
1. **Defisit Skenario Negatif / Edge**: Frozen Oracle memuat pengujian `test_delete_nonexistent_product` yang menuntut respon `404 Not Found`. Namun, antarmuka kontrak arsitektur lama hanya memuat tanda tangan metode (`DELETE /products/{id}`), tanpa ground truth perilaku observable yang diharapkan (`status_code == 404`).
2. **Asumsi Implementasi Default**: Developer LLM secara naif mengimplementasikan idempotent deletion (`return {"ok": True}` atau HTTP 204) yang valid secara sintaks, namun melanggar kontrak semantik penerimaan Frozen Oracle.
3. **Pemberian Solusi Tanpa Hardcoding**: Larangan keras IA melarang pembuatan solver berbasis `if task == 'fastapi': return 404`. Solusi harus bersifat **universal** dan berlaku lintas bahasa (Python, Dart) serta domain (API, CLI, UI).

---

## 3. Komponen Inti Treatment #1.3 yang Diterapkan

### A. Ekstraksi Skenario Kanonikal (`backend/canonical_scenario.py`)
- **`CanonicalScenario` Data Structure**:
  Menyimpan tupel independen ber-provenance ketat: `(caller, stimulus, precondition, expected_outcome, observable_output, expected_exception, metadata)`.
- **`PythonAstScenarioExtractor`**:
  - Mengekstrak stimulus eksekusi (`client.delete('/products/999999')`) dan ekspektasi observable (`assert response.status_code == 404`).
  - Menghormati **Koreksi IA #1**: Docstring hanya dicatat sebagai `metadata["docstring"]` dan tidak pernah menjadi autoritas semantik mandiri tanpa stimulus/assertion executable.
  - Menghormati **Koreksi IA #2**: `status_code >= 400` tidak dijadikan authority mutlak untuk klasifikasi `NEGATIVE`. Data kanonikal murni menyimpan `expected_outcome={"status_code": 404}`, klasifikasi adalah turunan.
- **`DartAstScenarioExtractor`**:
  - Mengekstrak widget stimulus (`tester.pumpWidget(CardMetric(...))`) dan expected matchers (`findsOneWidget`, `findsNothing`).
  - Menghormati **Koreksi IA #3**: `expect(tester.takeException(), isNull)` dipetakan ke `expected_exception="NONE"`, bukan otomatis `EDGE`.
- **Deterministic Comparator (`evaluate_behavioral_observations`)**:
  - Membandingkan ekspektasi vs observasi eksekusi tanpa hardcoding.
  - Menghasilkan status perbandingan: `MATCH`, `MISMATCH`, `UNDETERMINED`.
  - Mempertahankan multi-failure scenario dan membedakan kegagalan saat ini dari riwayat lama.

### B. Injeksi Ground Truth ke Architect Agent (`backend/agents/architect.py`)
- Menambahkan seksi autoritatif berbobot tinggi:
  `[ACCEPTANCE BEHAVIOR & SCENARIOS — FROZEN ORACLE GROUND TRUTH]`
- Memastikan Architect wajib memetakan setiap skenario pengujian ke dalam tanggung jawab komponen dan perilaku rancangan sebelum status kontrak di-seal (`FROZEN`).

### C. Hardening Konteks Perbaikan Developer (`backend/context_hardening.py`)
- Prioritas seksi konteks:
  1. `[1] FROZEN CONTRACT / AUTHORITATIVE ACCEPTANCE`
  2. `[ACCEPTANCE BEHAVIOR & SCENARIOS]`
  3. `[CURRENT FAILURE — BEHAVIORAL MISMATCH]`
- Omission Detection: Mendeteksi pemotongan token konteks jika seksi otoritatif esensial terpotong, mencegah developer mengabaikan kegagalan perilaku yang masih berlangsung.

---

## 4. Evaluasi Hasil Pilot 1x3 Secara Rinci

### 1. `fastapi_t1` (Python FastAPI REST API)
- **Verdict**: **PASS** (100% 5/5 tests passed)
- **Loop Repair**: **0 loops** (First-turn success / Turn 0)
- **Durasi**: 324.97 detik
- **Skenario Kritis**:
  - `test_create_product` (POST 201) -> PASS
  - `test_get_all_products` (GET 200) -> PASS
  - `test_get_product_by_id` (GET 200) -> PASS
  - `test_delete_product` (DELETE 200) -> PASS
  - `test_delete_nonexistent_product` (DELETE 404) -> **PASS** (sebelumnya selalu FAIL 204 == 404)
- **Analisis**: Kehadiran seksi skenario kanonikal `DELETE /products/999999 -> status_code: 404` pada prompt Architect & Developer membuat model langsung menulis pengecekan keberadaan produk:
  `if product_id not in db: raise HTTPException(status_code=404, detail="Product not found")`
  secara natural tanpa solver buatan.

### 2. `cli_t1` (Python CLI Matrix Calculator)
- **Verdict**: **PASS** (100% 5/5 tests passed)
- **Loop Repair**: **2 loops** (Konvergen deterministik ≤ 3 loops)
- **Durasi**: 222.81 detik
- **Skenario Kritis**:
  - Uji operasi matriks valid (add, subtract, multiply) -> PASS
  - Uji operasi dimensi tidak valid (`pytest.raises(ValueError)`) -> PASS
- **Analisis**: Pada Turn 0 developer mengalami sedikit misalignment format output CLI, namun feedback diagnostik terarah dan skenario exception membawa kode ke kelulusan penuh pada Turn 2.

### 3. `flutter_t1` (Dart Flutter CardMetric Widget)
- **Verdict**: **PASS** (100% 2/2 tests passed)
- **Loop Repair**: **0 loops** (Developer Turn 0)
- **Durasi**: 429.29 detik
- **Skenario Kritis**:
  - Render CardMetric dengan title, value, unit -> PASS
  - Null/empty handling dan styling tokens -> PASS
- **Analisis**: Architect Gate mendeteksi ketidaksesuaian kontrak pada percobaan awal, CEP memicu perbaikan mandiri di level arsitektur, dan ketika diteruskan ke Developer, kode Dart lulus eksekusi sandbox `flutter test` dalam 34.1 detik pada percobaan pertama.

---

## 5. Audit Kepatuhan Non-Fungsional & Forensik

1. **Integritas Frozen Oracle (Gate C & V)**:
   - Checksum SHA-256 seluruh berkas oracle terbukti **100% identik** dengan kontrol `main` / `c491982`.
   - `fastapi_t1`: `a1db9bb1f6eaf47d5cf56e102c4a0f6e1f49d757e9faa1485b36f2972a152d63` (INTACT)
   - `cli_t1`: `0bd5b598afa7ae4c9cdf0e269d13136b51d35a4e0b1ac6548f0a2cf8a8eba124` (INTACT)
   - `flutter_t1`: `4589e15cfb8f37ba70642e70623ca143bceee1a44175aefd072f441d9e8a9528` (INTACT)
2. **Sterile Executor & LLM Tester Isolation (Gate D & W)**:
   - `sterile_executor.py` murni tidak berubah (`git diff main -- backend/sterile_executor.py` kosong).
   - Tester LLM sepenuhnya dibypass, delegasi penuh ke pengujian deterministik `pytest` dan `flutter test`.
3. **Ketiadaan Hardcoded Solver (Gate U & Forensic Test)**:
   - Tidak ada branch `if "fastapi" in task`, `if endpoint == "/products"`, maupun hardcoding `return 404`.
   - Mekanisme berbasiskan sepenuhnya pada AST parsing dan komparasi nilai skenario kanonikal umum.
4. **Regresi Kode Global**:
   - Seluruh **623 unit test** pada repositori backend berstatus **PASS** (0 failures).
   - Seluruh **24 gates** pada `test_behavioral_scenarios_v1.py` berstatus **PASS**.

---

## 6. Kesimpulan & Rekomendasi Selanjutnya

Treatment #1.3 berhasil memecahkan hambatan konvergensi pada `fastapi_t1` dengan menghubungkan aliran bukti perilaku observable dari Frozen Oracle ke Architect dan Developer context.

**Status Akhir**:
- **Tingkat Kelulusan Pilot**: **3/3 PASS (100%)**
- **Semua task konvergen dalam batas loop (≤ 3 loops)**.
- **Branch `experiment/fastapi-recovery` siap untuk ditinjau oleh IA**.
