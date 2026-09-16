# Laporan Riset Forensik Pilot Terkontrol 1×3: Treatment #1.8.1 — Universal Structural Blueprint Fidelity & Repair Preservation v1

## 1. Metadata Eksperimen

| Atribut | Nilai |
| :--- | :--- |
| **Tanggal Eksperimen** | 16 September 2026 |
| **Branch Eksperimen** | `experiment/treatment-1.8-agent-capability` |
| **Parent LKG Frozen** | Treatment #1.8 (`a5589a7` — 3/3 Flutter FROZEN, LKG Baseline 714 passed) |
| **Treatment Commit** | `24eb1b2` (*Universal Structural Blueprint Fidelity & Repair Preservation v1*) |
| **Model Pengujian** | `qwen2.5-coder:7b` (num_predict: 3000, num_ctx: 8192, Ollama) |
| **Evaluator / Peneliti** | Intent Architect / Agent Capability Research Team ReinDev Studio |
| **Desain Pengujian** | Pilot Terkontrol 1×3 (3 Domain Task × 1 Repetisi = 3 Runs Total) |
| **Target Intervensi** | **Agent Architect** (Relational Blueprint Representation [F], Two-Stage Synthesis, Representation Contract, Generic Repair Preservation, Observable Behavior Guidance) |
| **Status Tata Kelola** | **Governance #1.6 FROZEN** (Zero modification pada validator, fail-closed constitution) |
| **Status Upstream PM** | **PM #1.7 FROZEN** (Input upstream tetap, zero modification pada PM) |
| **Status Oracle** | **IMMUTABLE** (SHA-256 terverifikasi 100% identik pada ketiga task) |
| **Kondisi Berhenti (Stop Condition)**| **STOP REACHED (1×3 Pilot Selesai -> Forensic Analysis -> Human Review)** |

---

## 2. Ringkasan Eksekutif & Temuan Empiris

Pilot terkontrol 1×3 dilaksanakan secara ketat berdasarkan protokol ilmiah untuk menguji **Hipotesis H1.8.1**:
> *"Apakah representasi relasional generic Blueprint dan preservasi perbaikan meningkatkan fidelitas struktural Architect, khususnya pada stress case Python (FastAPI & CLI), sembari mempertahankan perilaku sukses pada Flutter?"*

Sesuai dengan ketentuan tata kelola dan koreksi dari Human Reviewer (*Section 16 Protokol*), eksekusi **DIHENTIKAN (STOP)** setelah 1×3 runs selesai untuk analisis forensik mendalam sebelum keputusan GO/NO-GO replikasi 3×3.

### Matriks Hasil Pilot 1×3:

| Run # | Task ID | Target Bahasa | Verdict Akhir | Status Kontrak | Tests Passed | Loops | Durasi | Titik Penghentian & Root Cause |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **1/3** | `fastapi_t1` | Python | **FAIL** | REJECTED | 0/5 | 0 | 344.8s | **Architect Phase (Turn 2)** — `file_tree` diserialisasi sebagai `list[dict]` alih-alih `list[str]`, dan key `files` hilang pada top-level JSON. |
| **2/3** | `cli_t1` | Python | **FAIL** | REJECTED | 0/5 | 0 | 338.9s | **Architect Phase (Turn 2)** — `file_tree` berhasil diperbaiki menjadi `['main.py']`, `interface_contracts` valid, namun key `files` terhapus dari top-level JSON. |
| **3/3** | `flutter_t1` | Dart | **FAIL** | N/A (Null) | 0/2 | 0 | 140.0s | **V0 Requirement Gate (Turn 2)** — LLM mereplikasi string placeholder prompt `'Kutipan langsung dari task'` ke dalam field `basis` pada epistemic ledger, memicu kegagalan provenance V0 sebelum sempat mencapai fase Architect. |

---

## 3. Analisis Forensik Mendalam per Task

### 3.1. Stress Case 1: `fastapi_t1` (Python / REST API)
- **Turn 0 (Initial Blueprint Synthesis)**:
  - Model `qwen2.5-coder:7b` menghasilkan sintaks JSON yang cacat akibat delimiter koma/tanda petik di dalam string `code_scaffold`:
    ```
    SCHEMA_VIOLATION: Blueprint JSON parse failure: Gagal mendekode JSON blueprint: Expecting ',' delimiter: line 15 column 47 (char 492)
    ```
- **Turn 1 (First Repair Turn)**:
  - Model menerima pesan kegagalan decode JSON dan memperbaiki sintaks parsing JSON.
  - Namun, model mengalami **kolaps representasi**: model menggabungkan `files` ke dalam `file_tree` sebagai kamus (dictionary):
    ```json
    "file_tree": {
      "main.py": {
        "code_scaffold": "..."
      }
    }
    ```
  - Pydantic validator menolak secara deterministik:
    ```
    file_tree: Input should be a valid list [type=list_type, input_value={'main.py': {'code_scaffold': ...}}]
    ```
- **Turn 2 (Second Repair Turn)**:
  - Model membaca pesan bahwa `file_tree` harus berupa `list`.
  - Respons model: model mengubah `file_tree` menjadi list, tetapi berupa **list of dictionaries** alih-alih list of strings:
    ```json
    "file_tree": [
      {
        "module": "main",
        "file_name": "main.py",
        ...
      }
    ]
    ```
  - Dan karena scaffold sudah ditaruh di dalam objek `file_tree`, model **menghilangkan key `files`** dari root JSON.
  - Validator Pydantic menolak:
    ```
    file_tree.0: Input should be a valid string [type=string_type, input_value={'module': 'main', ...}]
    files: Field required [type=missing, input_value={'file_tree': [{'module': ...}]}]
    ```
  - Alur mencapai batas maksimal perbaikan Architect (`max_repairs=2`) dan berhenti (*fail-closed*).

---

### 3.2. Stress Case 2: `cli_t1` (Python / CLI Matrix Calculator)
- **Turn 0 (Initial Blueprint Synthesis)**:
  - Model menghasilkan narasi tanpa penanda blok kanonikal `=== BLUEPRINT JSON ===`:
    ```
    SCHEMA_VIOLATION: Blueprint JSON parse failure: Tidak ditemukan blok JSON blueprint yang valid dalam teks input
    ```
- **Turn 1 (First Repair Turn)**:
  - Model membungkus output ke dalam `=== BLUEPRINT JSON ===`.
  - Namun, persis seperti FastAPI Turn 1, model mendistorsi `file_tree` menjadi kamus scaffold:
    ```
    file_tree: Input should be a valid list [type=list_type, input_value={'main.py': {'code_scaffold': ...}}]
    interface_contracts.0.identifier: Field required
    interface_contracts.0.target_file: Field required
    ```
- **Turn 2 (Second Repair Turn — Near-Miss Discovery)**:
  - Model berhasil memperbaiki `file_tree` menjadi `List[str]`:
    ```json
    "file_tree": ["main.py"]
    ```
  - Model berhasil mendefinisikan seluruh `interface_contracts` dengan identifier valid (`Matrix`, `add_matrices`, `subtract_matrices`, `multiply_matrices`).
  - **Namun, model mengalami Field-Loss (penghapusan field)**: Karena pada Turn 1 scaffold berada di dalam `file_tree`, ketika model membersihkan `file_tree` menjadi `["main.py"]`, model lupa memindahkan scaffold ke key root `"files"`!
  - Akibatnya, root JSON kehilangan field wajib `files`:
    ```
    files: Field required [type=missing, input_value={'file_tree': ['main.py'], 'interface_contracts': [...]}]
    ```
  - Alur mencapai batas perbaikan dan berhenti (*fail-closed*).

---

### 3.3. Comparative Case: `flutter_t1` (Dart / Flutter Widget)
- **Investigasi Kejadian**:
  - Pada Treatment #1.8 sebelumnya, `flutter_t1` mencatatkan 3/3 (100%) FROZEN.
  - Pada Pilot 1×3 kali ini, `flutter_t1` berhenti pada **Fase V0 (Requirement Interpretation)** pada Turn 0, 1, dan 2:
    ```
    Item FACT-01 mengklaim FACT tetapi basis tidak memiliki jangkar pada tugas pengguna: 'Kutipan langsung dari task'
    -> Setiap FACT wajib mengutip basis langsung dari teks tugas pengguna.
    ```
  - **Temuan Root Cause**:
    - Kode V0 tidak dimodifikasi sama sekali pada Treatment #1.8.1 (komit `24eb1b2` hanya menyentuh `architect.py`, `context_hardening.py`, dan tes).
    - Kegagalan ini merupakan **anomali stokastik murni pada model 7B di fase V0**: model menyalin string placeholder dari sistem prompt (`"basis": "Kutipan langsung dari task"`) secara harfiah alih-alih mengutip kalimat pengguna ("Bangun komponen widget kartu metrik...").
    - Berdasarkan data historis, anomali V0 ini terjadi secara sporadis pada run-run terdahulu (e.g. `20260913_140816` dan `20260913_144323`).
    - **Penting**: Agen Architect **belum pernah dieksekusi sama sekali** pada task Flutter di Pilot 1×3 ini karena pipeline menghentikan eksekusi (*zero downstream leakage*) saat V0 gagal 3 kali berturut-turut.

---

## 4. Evaluasi Metrik Keberhasilan Protokol (Metrics A–I)

| Metrik | Target Evaluasi | Hasil Empiris Pilot 1×3 | Evaluasi |
| :--- | :--- | :---: | :--- |
| **Metric A: Blueprint Schema Conformance Rate** | Peningkatan validitas skema JSON pada Python stress cases | **0 / 3 (0.0%)** | **FAIL** — `file_tree` vs `files` structural collision berulang pada kedua task Python. |
| **Metric B: Two-Stage Synthesis Evidence** | Trace menunjukkan penalaran model semantik sebelum serialisasi | **TERLIHAT SEBAGIAN** | Model merancang antarmuka dan modul secara semantik, namun gagal memisahkan `file_tree` (path list) dan `files` (scaffold mapping) saat serialisasi tahap kedua. |
| **Metric C: Layer [F] Relational Blueprint State** | Injeksi Layer [F] diabsorpsi tanpa eror atau hallusinasi | **PASS PADA TURN 0** | Layer [F] berhasil dirakit secara deterministik dari Acceptance Authority tanpa inventasi artefak. |
| **Metric D: Invariant Preservation Rate** | Tidak ada field valid yang dihapus saat repair turn | **FAIL PADA TURN 2** | Terjadi *field-loss*: Pada CLI Turn 2, field `files` terhapus total setelah model memperbaiki `file_tree`. |
| **Metric E: Scaffold Observable Behavior** | Scaffold memuat perilaku observable yang memadai | **UNDETERMINED** | Belum sempat dievaluasi oleh behavioral validator karena terhenti di schema gate. |
| **Metric F: Anti-Solver / Generic Compliance** | Bebas percabangan spesifik Python/FastAPI/CLI | **100% PASS** | 5/5 static audit tests lulus (`test_architect_static_audit_v1.py`). Zero solver code. |
| **Metric G: Contract Freeze Rate** | Target: >= 2/3 task FROZEN | **0 / 3 (0.0%)** | **FAIL** — 0/3 kontrak berhasil dibekukan pada Pilot 1×3. |
| **Metric H: Downstream & E2E Outcome** | Evaluasi eksekusi Developer & Executor | **N/A (0 runs)** | Fail-closed boundary menahan seluruh downstream execution. Zero leakage. |
| **Metric I: Regression & Invariant Stability** | Nol regresi pada suite eksisting | **100% PASS** | 724 passed, 0 failures. Oracle SHA-256 intact 100%. |

---

## 5. Diagnosa Akar Masalah (Root Cause Analysis)

Analisis mendalam terhadap trace, prompt, dan mekanisme perakitan konteks mengungkap **4 faktor utama**:

### Faktor 1: Ambiguitas Konseptual antara `file_tree` dan `files` pada Model 7B
Dalam skema kanonikal `ArchitecturalBlueprint`:
1. `file_tree`: Didefinisikan sebagai `List[str]` (hanya daftar path berkas, contoh: `["main.py"]`).
2. `files`: Didefinisikan sebagai `Dict[str, BlueprintFileModule]` (kamus pemetaan path ke objek scaffold kode, contoh: `{"main.py": {"module_role": "...", "code_scaffold": "..."}}`).

Bagi model 7B (`qwen2.5-coder:7b`):
- Istilah *"file tree"* diinterpretasikan sebagai hierarki/struktur data file, sehingga model menaruh kamus scaffold langsung di dalam `"file_tree": { "main.py": { ... } }`.
- Ketika Pydantic memberi error `file_tree: Input should be a valid list`, model mengubah dictionary tersebut menjadi list of objects `[{"module": "main", ...}]` alih-alih list of strings `["main.py"]`.
- Ketika model akhirnya mengubahnya menjadi `["main.py"]` (seperti pada CLI Turn 2), model membuang scaffold yang sebelumnya ada di dalam `file_tree` tanpa memindahkannya ke root key `"files"`.

### Faktor 2: Asimetri Konteks Turn 0 vs Turn Repair (Turn 1 & 2)
Dalam implementasi `backend/context_hardening.py`:
- Pada Turn 0, `build_architect_decision_context` menyertakan Layer `[F]` dan `format_canonical_blueprint_schema_constraints()`.
- Namun, pada Turn 1 dan Turn 2, fungsi tersebut mendelegasikan secara langsung ke:
  ```python
  if pkg is not None or rev_count > 0:
      return build_architect_repair_context(state, pkg=pkg, max_chars=max_chars)
  ```
- **Kelemahan Kritis**: `build_architect_repair_context` **TIDAK MENYERTAKAN** `format_canonical_blueprint_schema_constraints()` maupun Layer `[F]`!
- Akibatnya, pada saat model berada dalam giliran perbaikan (Turn 1 dan Turn 2) untuk memperbaiki kesalahan skema, konteks keputusan yang diterima model sama sekali tidak memuat definisi tipe data dan daftar field wajib skema kanonikal! Model harus menebak struktur skema dari pesan error Pydantic yang terisolasi.

### Faktor 3: Panjang Prompt dan Efek Atenuasi Perhatian (Attention Dilution)
Total panjang prompt yang dikirimkan ke model pada giliran perbaikan mencapai **~20.000 karakter (~5.000 token)**:
- `structure_rule` (~800 char)
- `env_section` (~500 char)
- `user_task` (~200 char)
- `oracle_ledger_section` (~2.000 char)
- `oracle_scenario_section` (~2.000 char)
- `specs` (~2.000 char)
- `feedback_section` (~4.000 char, memuat full rendered directive + pydantic tracebacks)
- `decision_text` (~6.500 char, memuat 10 repair sections)

Pada akhir prompt, pengingat penutup (`PRE-SEAL SELF-REVIEW`) mengingatkan 8 poin filosofis, namun **tidak mengingatkan 2 struktur level teratas** yang menjadi kontrak serialisasi kanonikal:
- `"file_tree": ["path1", "path2"]` (HANYA list of string paths)
- `"files": {"path1": {"code_scaffold": "..."}}` (Kamus konten modul)

### Faktor 4: Anomali Stokastik V0 pada Flutter
Kegagalan Flutter pada Pilot 1×3 ini murni akibat model 7B menyalin string placeholder `"Kutipan langsung dari task"` pada fase V0. Hal ini telah diamati sebelumnya pada riwayat pengujian, dan bukan merupakan regresi dari Treatment #1.8.1.

---

## 6. Usulan Solusi Rekayasa (Proposed Remediation)

Untuk mengatasi akar masalah di atas secara generik dan elegan **tanpa membuat Python-specific solver**:

### Solusi 1: Simetri Konteks Skema pada Repair Context (Universal)
Suntikkan `format_canonical_blueprint_schema_constraints()` ke dalam `build_architect_repair_context` (khususnya pada `sec_06_repair_target` atau `sec_07_repair_boundary`).
Dengan demikian, ketika terjadi kegagalan skema, model pada Turn 1 dan Turn 2 secara eksplisit melihat batasan tipe data kanonikal:
- `file_tree`: `List[str]` (Daftar path string)
- `files`: `Dict[str, BlueprintFileModule]` (Kamus pemetaan path ke objek scaffold — REQUIRED)
- `interface_contracts`: `List[BlueprintInterfaceContract]`

### Solusi 2: Penegasan Representasi Dual-Level Berkas pada Trailing Reminder Prompt
Di akhir prompt input Architect (`architect_agent`), tambahkan pengingat ringkas mengenai kontrak representasi berkas kanonikal:
- `file_tree` WAJIB berupa `List[str]` (daftar nama berkas).
- `files` WAJIB ada di root JSON sebagai `Dict[str, BlueprintFileModule]` yang memetakan setiap berkas di `file_tree` ke modul scaffold-nya.
- Ini diturunkan langsung dari definisi skema kanonikal `ArchitecturalBlueprint`, bukan aturan ad-hoc.

### Solusi 3: Perbaikan Preservasi Root Field pada Anti-Field-Loss
Pertegas instruksi Anti-Field-Loss pada repair context bahwa memperbaiki salah satu elemen (misal `file_tree`) **TIDAK BOLEH** menghilangkan elemen level teratas lainnya (`files`, `interface_contracts`, `data_models`).

---

## 7. Titik Keputusan Pengguna (Decision Point)

Sesuai dengan Stop Condition Protokol #1.8.1, pelaksanaan eksperimen saat ini berada dalam status **PAUSED (STOP)** menunggu konfirmasi Human Reviewer:

1. **OPSI A (Rekomendasi)**:
   Terapkan Solusi Rekayasa 1, 2, dan 3 (perbaikan simetri repair context dan penegasan representasi dual-level berkas yang bersumber dari skema kanonikal). Jalankan ulang Pilot 1×3 untuk verifikasi sebelum melangkah ke replikasi 3×3.

2. **OPSI B**:
   Pertahankan implementasi saat ini tanpa perubahan dan langsung jalankan replikasi penuh 3×3 (Tidak direkomendasikan karena stress case Python kemungkinan besar akan mengulang pola kegagalan yang sama).

3. **OPSI C**:
   Penyesuaian lain sesuai arahan spesifik pengguna.
