# Desain Arsitektur P0-1: Structured Diagnostic Parser & Targeted Error Feedback

**Status Dokumen:** DESIGN ONLY (Kontrak Desain Siap Diimplementasikan)  
**Versi:** 1.0.0  
**Tanggal:** 2026-09-09  
**Komponen:** Diagnostic Evidence Parser & Developer Feedback Loop  
**Inisiatif:** P0-1 (Prioritas Tertinggi Pasca-Phase 2)  
**Dokumen Rujukan:**
- [`dokumentasi-pengembangan/architecture/improvement_direction_after_phase2.md`](file:///D:/Pekerjaan/Antigravity/reindev_studio/dokumentasi-pengembangan/architecture/improvement_direction_after_phase2.md)
- [`dokumentasi-pengembangan/experiments/phase2_transformation_level_forensic_audit.md`](file:///D:/Pekerjaan/Antigravity/reindev_studio/dokumentasi-pengembangan/experiments/phase2_transformation_level_forensic_audit.md)
- [`dokumentasi-pengembangan/experiments/executor_v2_architecture_inspection.md`](file:///D:/Pekerjaan/Antigravity/reindev_studio/dokumentasi-pengembangan/experiments/executor_v2_architecture_inspection.md)
- [`backend/executor_v2.py`](file:///D:/Pekerjaan/Antigravity/reindev_studio/backend/executor_v2.py)
- [`backend/agents/developer.py`](file:///D:/Pekerjaan/Antigravity/reindev_studio/backend/agents/developer.py)

---

## 1. Problem Statement (Latar Belakang Masalah)

Berdasarkan audit forensik 30 run pada Phase 2 Main Controlled Experiment, **70.0% run (21 dari 30 run)** gagal menuntaskan tugas rekayasa dalam batas 3 iterasi self-healing loop. Pada arsitektur saat ini:
1. **Kebisingan Terminal Mentah (*Terminal Noise Dumping*):** Pasca-kegagalan pengujian sandbox (`pytest` atau `dart test`), seluruh output terminal mentah (`stdout` + `stderr`) yang mencapai **2.500 s.d. 4.200 karakter** (setara 800–1.200 token) disuntikkan secara utuh dan tanpa kurasi ke dalam prompt Developer LLM pada iterasi perbaikan.
2. **Beban Konteks & Distraksi Model 7B:** Output mentah tersebut memuat informasi lingkungan yang tidak relevan bagi perbaikan kode, seperti:
   - Header sesi pytest dan path lingkungan lokal Windows.
   - Peringatan library pihak ketiga (misal: *DeprecationWarning AnyIO BlockingPortal* pada Starlette).
   - Traceback internal framework (misal: 15 frame stack call di dalam `starlette/routing.py` dan `anyio/_backends/_asyncio.py`).
   - Format ANSI escape codes dan progress bar.
3. **Stagnasi Penalaran Multi-Loop:** Model lokal berukuran 7B (`qwen2.5-coder:7b`) tidak memiliki kapasitas untuk memisahkan antara *root cause assertion error* dengan *traceback boilerplate*. Akibatnya, Developer berulang kali memperbaiki baris yang salah, mengabaikan ekspektasi pengujian yang sebenarnya, dan terjebak dalam perulangan kode yang identik di Iterasi 1, 2, dan 3.

**Tujuan Desain P0-1:**  
Membangun komponen deterministik *read-only* bernama **Structured Diagnostic Parser** yang berada di antara Sandbox Runner dan Developer Agent. Komponen ini bertugas mengekstrak *diagnostic evidence* terstruktur dari output pengujian mentah, mengklasifikasikan tipe kegagalan, mengisolasi baris kode yang rusak, mengekstrak nilai *expected vs actual*, dan menyajikan umpan balik yang terfokus (*targeted feedback*) kepada Developer tanpa membebani jendela konteks model.

---

## 2. Current Execution-to-Developer Pipeline (Audit Alur Aktual)

Penelusuran kode sumber aktual pada repositori ReinDev Studio memperlihatkan alur umpan balik saat ini:

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           ALUR AKTUAL SAAT INI (HIGH NOISE)                             │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│  [ Subprocess Runner ] ──> pytest / dart test (Windows Subprocess)                      │
│            │                                                                            │
│            ▼                                                                            │
│  [ Raw stdout / stderr ] ──> backend/executor_v2.py (baris 602 di executor.py):        │
│                              full_output = (stdout + "\n" + stderr).strip()            │
│            │                                                                            │
│            ▼                                                                            │
│  [ test_results dict ]  ──> test_results["output"] = full_output (3.500+ karakter)    │
│            │                                                                            │
│            ▼                                                                            │
│  [ SquadState ]         ──> state["test_results"] diteruskan ke loop berikutnya         │
│            │                                                                            │
│            ▼                                                                            │
│  [ developer.py ]       ──> Baris 178–197:                                              │
│                              output_err = test_results.get("output", "")                │
│                              prompt = "... Galat: " + output_err                        │
│            │                                                                            │
│            ▼                                                                            │
│  [ Developer Prompt ]   ──> DUMP TERMINAL MENTAH 100% MASUK KE PROMPT DEVELOPER!        │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### Temuan Audit Titik Lemah:
1. **Lokasi Pembangkitan Output:** `backend/executor_v2.py` memanggil `run_sandbox_tests_legacy` (`backend/executor.py` baris 588–602), di mana `proc = subprocess.run(...)` menangkap `proc.stdout` dan `proc.stderr`.
2. **Format `test_results` Saat Ini:** Kamus flat dengan kunci:
   `passed` (bool), `total` (int), `passed_count` (int), `failed_count` (int), `output` (string mentah gabungan), `stdout`, `raw_stdout`, `raw_stderr`, `command`, `working_dir`, `exit_code`, `duration_sec`, `framework`, `code_files`, `test_files`.
3. **Penyimpanan di State:** `test_results` disimpan langsung pada `state["test_results"]` oleh node `executor`.
4. **Penyuntikan ke Developer:** Pada `backend/agents/developer.py` baris 178–209, variabel `output_err = test_results.get("output", "")` disisipkan verbatim ke blok string:
   ```python
   [PERHATIAN KRUSIAL - SIKLUS PERBAIKAN SELF-HEALING (LOOP {iteration}/{max_iterations})]:
   Pengujian QA Tester GAGAL dengan pesan galat berikut:
   {output_err}
   ```
   Bagian inilah yang menyuntikkan seluruh dump terminal mentah tanpa seleksi ke konteks Developer.

---

## 3. Design Goals (Sasaran Desain)

1. **Noise Elimination:** Memangkas volume teks umpan balik kegagalan dari ~3.500 karakter menjadi **300–600 karakter terstruktur** (reduksi token >75%).
2. **Determinism & Grounding:** Ekstraksi bukti kegagalan dilakukan dengan logika deterministik (parser regex + string structural scanning), bukan meminta model LLM lain untuk merangkum error (mencegah *hallucinated diagnostics*).
3. **Traceability & Isolation:** Memisahkan lokasi pengujian (`test_file:line`) dengan lokasi kode aplikasi (`source_file:line`).
4. **Context Prioritization:** Menyaring kegagalan multi-kasus sehingga Developer hanya menerima maksimal 3 kegagalan prioritas tertinggi per iterasi perbaikan.
5. **Raw Trace Preservation:** Mempertahankan output mentah `raw_stdout` dan `raw_stderr` secara utuh pada trace sistem untuk audit manusia dan analisis forensik.
6. **Strict Read-Only Boundary:** Parser dilarang keras memodifikasi `code_files`, `test_files`, atau Frozen Oracle.

---

## 4. Diagnostic Evidence Schema (Kontrak Data Mesin)

Schema JSON formal untuk merepresentasikan hasil diagnostik satu kali eksekusi sandbox:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "DiagnosticEvidence",
  "type": "object",
  "required": [
    "execution_status",
    "framework",
    "total_tests",
    "passed_tests",
    "failed_tests",
    "error_count",
    "duration_sec",
    "exit_code",
    "primary_failure_category",
    "failing_tests"
  ],
  "properties": {
    "execution_status": {
      "type": "string",
      "enum": ["passed", "failed", "error", "timeout"]
    },
    "framework": {
      "type": "string",
      "enum": ["pytest", "dart test", "flutter test"]
    },
    "total_tests": { "type": "integer", "minimum": 0 },
    "passed_tests": { "type": "integer", "minimum": 0 },
    "failed_tests": { "type": "integer", "minimum": 0 },
    "error_count": { "type": "integer", "minimum": 0 },
    "duration_sec": { "type": "number", "minimum": 0 },
    "exit_code": { "type": "integer" },
    "summary_line": { "type": ["string", "null"] },
    "primary_failure_category": {
      "type": "string",
      "enum": [
        "assertion_failure",
        "syntax_parse_error",
        "import_module_error",
        "compilation_error",
        "runtime_exception",
        "collection_test_discovery_error",
        "timeout",
        "unknown"
      ]
    },
    "failing_tests": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "test_name",
          "test_file",
          "failure_type",
          "message",
          "confidence"
        ],
        "properties": {
          "test_name": { "type": "string" },
          "test_file": { "type": "string" },
          "test_line": { "type": ["integer", "null"] },
          "failure_type": {
            "type": "string",
            "enum": [
              "assertion_failure",
              "syntax_parse_error",
              "import_module_error",
              "compilation_error",
              "runtime_exception",
              "collection_test_discovery_error",
              "timeout",
              "unknown"
            ]
          },
          "message": { "type": "string" },
          "expected": { "type": ["string", "null"] },
          "actual": { "type": ["string", "null"] },
          "source_file": { "type": ["string", "null"] },
          "source_line": { "type": ["integer", "null"] },
          "source_symbol": { "type": ["string", "null"] },
          "traceback_excerpt": { "type": ["string", "null"] },
          "confidence": { "type": "number", "minimum": 0.0, "maximum": 1.0 }
        }
      }
    },
    "environment_warnings": {
      "type": "array",
      "items": { "type": "string" }
    }
  }
}
```

### Tabel Atribut Lapangan (Field Cardinality & Presence):

| Nama Field | Tipe Data | Wajib / Opsional | Nullable? | Catatan Khusus |
|---|---|:---:|:---:|---|
| `execution_status` | String | **Required** | Tidak | Status makro: `passed`, `failed`, `error`, `timeout`. |
| `framework` | String | **Required** | Tidak | `pytest`, `dart test`, atau `flutter test`. |
| `total_tests` | Integer | **Required** | Tidak | Jumlah total kasus uji yang terdaftar/tereksekusi. |
| `passed_tests` | Integer | **Required** | Tidak | Jumlah kasus uji yang lulus. |
| `failed_tests` | Integer | **Required** | Tidak | Jumlah kasus uji yang gagal. |
| `error_count` | Integer | **Required** | Tidak | Jumlah error fatal / collection crash. |
| `duration_sec` | Number | **Required** | Tidak | Durasi eksekusi subproses dalam detik. |
| `exit_code` | Integer | **Required** | Tidak | Exit code subproses (0, 1, 2, dsb.). |
| `summary_line` | String | Optional | Ya | Baris ringkasan runner (misal `3 failed, 2 passed in 0.35s`). |
| `primary_failure_category` | Enum String | **Required** | Tidak | Kategori kegagalan utama dari taksonomi standar. |
| `failing_tests[].test_name` | String | **Required** | Tidak | Nama fungsi uji (misal `test_get_all_products`). |
| `failing_tests[].test_file` | String | **Required** | Tidak | Berkas uji pemanggil (misal `test_main.py`). |
| `failing_tests[].test_line` | Integer | Optional | Ya | Nomor baris assertion dalam berkas uji. |
| `failing_tests[].failure_type` | Enum String | **Required** | Tidak | Klasifikasi taksonomi spesifik kasus uji ini. |
| `failing_tests[].message` | String | **Required** | Tidak | Pesan inti kegagalan ringkas (1 baris). |
| `failing_tests[].expected` | String | Optional | Ya | Nilai yang diharapkan (`null` jika tidak terdefinisi). |
| `failing_tests[].actual` | String | Optional | Ya | Nilai aktual yang dihasilkan (`null` jika tidak terdefinisi). |
| `failing_tests[].source_file` | String | Optional | Ya | Berkas kode aplikasi penyebab (misal `main.py`). |
| `failing_tests[].source_line` | Integer | Optional | Ya | Baris spesifik pada kode aplikasi. |
| `failing_tests[].source_symbol` | String | Optional | Ya | Fungsi/metode pada kode aplikasi penyebab. |
| `failing_tests[].traceback_excerpt` | String | Optional | Ya | Cuplikan 2–4 baris frame pemanggil relevan. |
| `failing_tests[].confidence` | Number | **Required** | Tidak | Derajat keyakinan ekstraksi parser (0.0 s.d. 1.0). |
| `environment_warnings` | Array[String] | Optional | Tidak | Peringatan runtime (disimpan tapi disaring dari prompt Dev). |

---

## 5. Failure Taxonomy (Taksonomi Kegagalan Lintas Framework)

Taksonomi kegagalan dirancang seragam untuk Python dan Dart:

| Kategori Taksonomi | Definisi Operasional | Prioritas Diagnostik |
|---|---|:---:|
| `collection_test_discovery_error` | Test runner gagal memuat berkas uji atau mengumpulkan tes sebelum pengujian dimulai (misal pytest exit code 2 atau Dart test compilation failure). | **1 (Tertinggi)** |
| `syntax_parse_error` | Berkas kode produksi atau tes memiliki kesalahan sintaksis yang mencegah parsing interpreter/kompiler. | **2** |
| `import_module_error` | Modul, pustaka, atau paket dependensi yang dipanggil tidak ditemukan atau gagal diimpor. | **3** |
| `compilation_error` | Kesalahan pengetikan tipe (*static type mismatch*), parameter named tidak cocok, atau metode tidak ditemukan pada bahasa terkompilasi (khusus Dart). | **4** |
| `runtime_exception` | Eksepsi Python/Dart yang tidak tertangani meledak saat eksekusi logika (misal `TypeError`, `KeyError`, `ZeroDivisionError`, `NoSuchMethodError`). | **5** |
| `assertion_failure` | Kode berhasil dieksekusi tanpa crash, namun nilai keluaran tidak cocok dengan ekspektasi pengujian (`assert a == b` atau `expect(a, equals(b))`). | **6** |
| `timeout` | Eksekusi subproses melampaui batas waktu maksimum (default 30s / 90s). | **7** |
| `unknown` | Output kegagalan tidak cocok dengan tanda tangan pola yang dikenali. | **8 (Terendah)** |

---

## 6. Pytest Mapping Engine (Pemetaan Output Pytest)

### Tanda Tangan Pola Regex Pytest:

1. **Short Summary Info Pattern:**
   ```regex
   FAILED\s+([\w\.\/\\]+)::(\w+)\s*-\s*(.+)
   ```
   - Group 1: `test_file` (misal `test_main.py`)
   - Group 2: `test_name` (misal `test_get_all_products`)
   - Group 3: `message` (misal `assert 405 == 200`)

2. **Collection Error Pattern:**
   ```regex
   ERROR\s+collecting\s+([\w\.\/\\]+)\s*:\s*(.+)
   ```
   - Dipetakan ke: `collection_test_discovery_error`.

3. **Assertion Equality Pattern:**
   ```regex
   E\s+assert\s+(.+?)\s*==\s*(.+)
   ```
   - Group 1: `actual` (misal `405`)
   - Group 2: `expected` (misal `200`)

4. **Runtime Exception Pattern:**
   ```regex
   E\s+([A-Z]\w*Error|[A-Z]\w*Exception):\s*(.+)
   ```
   - Dipetakan ke: `runtime_exception` jika bukan `AssertionError`.
   - Dipetakan ke: `syntax_parse_error` jika `SyntaxError` atau `IndentationError`.
   - Dipetakan ke: `import_module_error` jika `ModuleNotFoundError` atau `ImportError`.

---

## 7. Dart / Flutter Test Mapping Engine (Pemetaan Output Dart)

### Tanda Tangan Pola Regex Dart / Flutter Test:

1. **Test Compilation Failure Pattern (Flutter SDK):**
   ```regex
   ([\w\.\/\\]+\.dart):(\d+):(\d+):\s*Error:\s*(.+)
   ```
   - Group 1: `source_file` atau `test_file`
   - Group 2: `source_line` atau `test_line`
   - Group 3: `column`
   - Group 4: `message` (misal: `Method not found: 'StateProvider'` atau `No named parameter with the name 'title'`)
   - Dipetakan ke: `compilation_error`.

2. **Dart Test Assertion Failure Pattern:**
   ```regex
   Expected:\s*(.+)[\r\n]+\s*Actual:\s*(.+)[\r\n]+(?:\s*Which:\s*(.+))?
   ```
   - Group 1: `expected` (misal `<200>` atau `'CPU Usage'`)
   - Group 2: `actual` (misal `<404>` atau `'Memory Usage'`)
   - Group 3: `which_clause` (penjelasan diferensiasi string)
   - Dipetakan ke: `assertion_failure`.

3. **Dart Failed Test Case Header:**
   ```regex
   (?:\d\d:\d\d\s+)?\+\d+\s+-\d+:\s*(.+?)\s*\[E\]
   ```
   - Group 1: `test_name` (nama deskripsi test case).

---

## 8. Expected vs Actual Extraction Strategy

Prinsip Utama: **Anti-Halusinasi Deterministik**. Nilai `expected` dan `actual` hanya boleh diisi jika polanya terbukti secara sintaksis. Jika ambigu, wajib diisi `null` dan disimpan sebagai pesan mentah ringkas.

```
                    ┌──────────────────────────────────────────────┐
                    │      Output Gagal Diterima Parser            │
                    └──────────────────────┬───────────────────────┘
                                           │
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │  Apakah terdapat pola persamaan eksplisit?   │
                    │   - Pytest: 'assert A == B'                  │
                    │   - Dart: 'Expected: X' & 'Actual: Y'        │
                    └──────────────┬────────────────┬──────────────┘
                                   │                │
                             [ YA ]│                │[ TIDAK ]
                                   ▼                ▼
┌────────────────────────────────────────┐ ┌────────────────────────────────────────┐
│ Ekstrak:                               │ │ Setel:                                 │
│  expected = B.strip()                  │ │  expected = null                       │
│  actual   = A.strip()                  │ │  actual   = null                       │
│  confidence = 0.95                     │ │ Simpan assertion string pada:          │
│                                        │ │  message = raw_assertion_line          │
│                                        │ │  confidence = 0.70                     │
└────────────────────────────────────────┘ └────────────────────────────────────────┘
```

### Aturan Ekstraksi Status Code HTTP (Kasus FastAPI):
- Jika `assert res.status_code == 201`:
  - `actual` = `res.status_code` aktual (misal `"405"`)
  - `expected` = `"201"`
  - `message` = `"HTTP Status Mismatch: expected 201 Created, got 405 Method Not Allowed"`

---

## 9. Source Location Extraction (Pemisahan Lokasi Uji vs Aplikasi)

Salah satu kelemahan terbesar umpan balik lama adalah Developer tidak mengetahui apakah kesalahan terjadi di berkas pengujian atau berkas implementasi miliknya.

### Algoritma Resolusi Lokasi (Bottom-Up Frame Scanner):
1. Parser membaca seluruh frame traceback dari **bawah ke atas** (*innermost frame first*).
2. **Identifikasi `source_file` & `source_line` (Kode Aplikasi):**
   - Ambil frame terbawah yang merujuk pada berkas di luar `test/` atau `tests/` dan bukan library pihak ketiga (`site-packages/` atau `sdk/flutter`).
   - Contoh: `File "main.py", line 19, in get_products` $\rightarrow$ `source_file = "main.py"`, `source_line = 19`, `source_symbol = "get_products"`.
3. **Identifikasi `test_file` & `test_line` (Orakel Pengujian):**
   - Ambil frame yang merujuk pada berkas pengujian (dimulai dengan `test_` atau di direktori `test/`).
   - Contoh: `File "test_main.py", line 28, in test_get_all_products` $\rightarrow$ `test_file = "test_main.py"`, `test_line = 28`.

---

## 10. Multi-Failure Prioritization (Pencegahan Ledakan Konteks)

Ketika suite pengujian menghasilkan banyak kegagalan (misal 5 atau 10 kegagalan sekaligus), model 7B cenderung kewalahan (*context overload*) dan mencoba memperbaiki semua masalah secara serampangan.

### Kebijakan Penanganan Multi-Kasus:
1. **Aturan "Top-3 Focus":** Maksimal hanya **3 kegagalan prioritas tertinggi** yang disajikan dalam bentuk kartu rincian diagnostik lengkap.
2. **Urutan Pengurutan (*Sorting Order*):**
   1. `collection_test_discovery_error`
   2. `syntax_parse_error`
   3. `import_module_error`
   4. `compilation_error`
   5. `runtime_exception`
   6. `assertion_failure`
3. **Ringkasan Kegagalan Sekunder:** Kegagalan ke-4 dan seterusnya diringkas dalam satu baris informatif:
   ```text
   "+ 2 pengujian lainnya gagal dengan pola serupa (HTTP Status Mismatch). Selesaikan 3 kegagalan utama di atas terlebih dahulu."
   ```

---

## 11. Developer Feedback Contract (Payload Umpan Balik Siap Pakai)

Format Markdown terstruktur yang disuntikkan ke dalam `prompt` Developer pada `backend/agents/developer.py` (menggantikan dump teks mentah `output_err`):

```markdown
[TARGETED DIAGNOSTIC EVIDENCE - ITERASI PERBAIKAN 1/3]
Ringkasan: 3 dari 5 pengujian GAGAL (Framework: pytest | Exit Code: 1 | Durasi: 0.35s)
Kategori Kegagalan Utama: assertion_failure

DAFTAR MASALAH PRIORITAS (Fokus pada perbaikan baris kode berikut):

1. [ASSERTION FAILURE] dalam test: test_get_all_products
   - Berkas Pengujian: test_main.py (baris 28)
   - Berkas Kode Aplikasi: main.py (baris 19, fungsi: get_products)
   - Nilai Ekspektasi: HTTP 200
   - Nilai Aktual: HTTP 405 (Method Not Allowed)
   - Pesan Galat: assert 405 == 200
   - Cuplikan Kode:
     main.py:19 -> @app.post("/products/")
     test_main.py:28 -> response = client.get("/products/")

2. [ASSERTION FAILURE] dalam test: test_delete_product
   - Berkas Pengujian: test_main.py (baris 54)
   - Berkas Kode Aplikasi: main.py (baris 35, fungsi: delete_product)
   - Nilai Ekspektasi: HTTP 204
   - Nilai Aktual: HTTP 422 (Unprocessable Entity)
   - Pesan Galat: assert 422 == 204

3. [ASSERTION FAILURE] dalam test: test_get_product_by_id
   - Berkas Pengujian: test_main.py (baris 41)
   - Berkas Kode Aplikasi: main.py (baris 25, fungsi: get_product)
   - Nilai Ekspektasi: HTTP 200
   - Nilai Aktual: HTTP 405 (Method Not Allowed)
   - Pesan Galat: assert 405 == 200

PETUNJUK TINDAKAN DEVELOPER:
1. Periksa metode HTTP pada decorator endpoint di main.py: pastikan fungsi pembacaan data menggunakan @app.get, bukan @app.post.
2. Periksa tipe parameter URL pada fungsi delete_product agar menerima ID integer secara valid.
```

---

## 12. Raw Evidence Preservation (Pemisahan 3 Lapis Bukti)

Untuk menjamin ketaatan tata kelola bukti ilmiah (*data provenance*), bukti eksekusi dipecah secara ketat menjadi 3 lapis independen:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      LAPIS 1: RAW EXECUTION EVIDENCE                        │
│ - Disimpan di: state["test_results"]["raw_stdout"], ["raw_stderr"], ["output"]│
│ - Direkam permanen di: backend/output/<run_id>/run_trace.jsonl               │
│ - Sifat: 100% Verbatim teks terminal mentah tanpa manipulasi string.        │
│ - Pengguna: Audit Forensik IA, Debugging Sistem, Verifikasi Checksum.       │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼ (Dianalisis oleh Diagnostic Parser)
┌─────────────────────────────────────────────────────────────────────────────┐
│                   LAPIS 2: STRUCTURED DIAGNOSTIC EVIDENCE                   │
│ - Disimpan di: state["test_results"]["diagnostic_evidence"] (JSON Object)   │
│ - Direkam di: run_trace.jsonl (event: diagnostic_parse_complete)            │
│ - Sifat: Machine-readable schema terstandarisasi lintas bahasa.             │
│ - Pengguna: Algoritma Squad, Engine Router, Metrics Collector.              │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼ (Diformat oleh Targeted Feedback Builder)
┌─────────────────────────────────────────────────────────────────────────────┐
│                        LAPIS 3: DEVELOPER FEEDBACK                          │
│ - Disimpan di: state["developer_feedback"] (Markdown String)                │
│ - Disuntikkan ke: Prompt Developer LLM (feedback_section)                   │
│ - Sifat: Token-optimized, noise-free, fokus pada actionable source lines.   │
│ - Pengguna: Developer LLM untuk perbaikan terarah.                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 13. Repair-Loop Integration Architecture

Integrasi node pada siklus perbaikan LangGraph (`backend/graph.py`):

```
                        ┌──────────────────────────────┐
                        │       DEVELOPER NODE         │
                        └──────────────┬───────────────┘
                                       │
                                       ▼
                        ┌──────────────────────────────┐
                        │   EXECUTOR V2 (SAFE MODE)    │
                        │    - Pre-flight validation   │
                        │    - Sandbox execution       │
                        └──────────────┬───────────────┘
                                       │
                                       ▼
                        ┌──────────────────────────────┐
                        │    RAW EXECUTION EVIDENCE    │
                        │    - proc.stdout / stderr    │
                        └──────────────┬───────────────┘
                                       │
                                       ▼
                        ┌──────────────────────────────┐
                        │  DIAGNOSTIC PARSER (P0-1)    │
                        │    (Read-Only Deterministic) │
                        │  - Parse, Classify, Extract  │
                        └──────────────┬───────────────┘
                                       │
                   ┌───────────────────┴───────────────────┐
                   │                                       │
             [ Tests PASS ]                          [ Tests FAIL ]
                   │                                       │
                   ▼                                       ▼
┌─────────────────────────────────────┐ ┌─────────────────────────────────────┐
│   REVIEWER / VALIDATION GATE NODE   │ │      TARGETED FEEDBACK BUILDER      │
│   (Deterministically Release Ready) │ │   - Apply Top-3 Prioritization      │
│                                     │ │   - Format Clean Markdown Payload   │
└─────────────────────────────────────┘ └──────────────────┬──────────────────┘
                                                           │
                                                           ▼
                                        ┌─────────────────────────────────────┐
                                        │      DEVELOPER REPAIR (LOOP + 1)    │
                                        │  Menerima payload bersih tanpa noise│
                                        └─────────────────────────────────────┘
```

---

## 14. Failure / Fallback Semantics (Jaring Pengaman Kegagalan Parser)

Jika Structured Diagnostic Parser mengalami kegagalan (misal: format runner berubah, regex tidak cocok, atau terjadi unhandled parsing exception):

1. **Prinsip Fail-Safe:** Parser **tidak boleh menghentikan pipeline** dan **tidak boleh mengarang diagnosis**.
2. **Fallback Level 1 (Partial Fallback):**  
   Jika status tes dan jumlah kegagalan diketahui tetapi rincian baris gagal diekstrak, kembalikan `primary_failure_category = "unknown"`, `confidence = 0.0`, dan sertakan pesan kegagalan ringkas.
3. **Fallback Level 2 (Total Fallback - Clean Tail Dump):**  
   Jika seluruh parser gagal, ambil **15 baris terakhir (*tail 15 lines*)** dari `raw_stderr` atau `raw_stdout`, bersihkan karakter ANSI escape, dan sajikan dengan label transparan:
   ```markdown
   [DIAGNOSTIC FALLBACK - UNPARSED TERMINAL OUTPUT]
   Sistem tidak dapat mengurai format galat secara terstruktur. Berikut cuplikan 15 baris terakhir terminal:
   ... (15 baris ekor terminal bersih) ...
   ```
4. **Log Insiden:** Catat kegagalan parser pada tracer dengan event `diagnostic_parse_failed` untuk keperluan investigasi engineering.

---

## 15. Observability & Tracer Events

Komponen parser wajib mencatat seluruh aktivitas diagnostik ke dalam `backend/tracer.py`:

| Event Name | Stage | Kapan Dipicu | Metadata Wajib yang Direkam |
|---|---|---|---|
| `diagnostic_parse_start` | `diagnostic_parser` | Sesaat sebelum parsing dimulai | `framework`, `raw_output_bytes`, `iteration` |
| `diagnostic_parse_complete` | `diagnostic_parser` | Parsing berhasil diselesaikan | `execution_status`, `total_tests`, `failed_tests`, `primary_failure_category`, `parsed_failing_count`, `duration_ms` |
| `diagnostic_parse_failed` | `diagnostic_parser` | Parser melempar eksepsi internal | `error_type`, `error_message`, `fallback_strategy_used` |
| `developer_feedback_generated` | `diagnostic_parser` | Payload markdown siap dikirim | `feedback_char_length`, `prioritized_failures_count`, `omitted_failures_count` |

---

## 16. Security, Immutability & Design Boundary

Untuk mencegah terulangnya regresi arsitektur lama, batas tanggung jawab (*boundary*) Structured Diagnostic Parser ditetapkan secara kaku:

### APA YANG BOLEH DILAKUKAN PARSER (PERMITTED):
- ✅ Membaca `stdout`, `stderr`, dan `exit_code` subproses sandbox.
- ✅ Membaca berkas `code_files` dan `test_files` dalam mode *read-only* untuk memvalidasi nomor baris dan nama fungsi pemanggil.
- ✅ Mengklasifikasikan error ke dalam taksonomi standar.
- ✅ Menyortir dan memotong daftar kegagalan berdasarkan prioritas.
- ✅ Memformat umpan balik teks Markdown yang ringkas dan bebas noise.

### APA YANG DILARANG KERAS DILAKUKAN PARSER (FORBIDDEN):
- ❌ **DILARANG KERAS memodifikasi berkas kode produksi (`code_files`).**
- ❌ **DILARANG KERAS memodifikasi berkas pengujian atau Frozen Oracle (`test_files`).**
- ❌ **DILARANG KERAS menebak kebutuhan bisnis yang tidak diminta pengguna.**
- ❌ **DILARANG KERAS menyarankan solusi kode pengganti secara langsung** (tugas memikirkan kode perbaikan adalah hak mutlak Developer LLM).
- ❌ **DILARANG KERAS menghapus atau memutasi bukti mentah `raw_stdout`/`raw_stderr`.**

---

## 17. Known Limitations (Batasan Desain yang Diketahui)

1. **Heuristik Ekstraksi Traceback Bahasa Dinamis:** Pada Python, traceback dinamis yang dihasilkan dari fungsi `eval()` atau exec runtime kompleks mungkin tidak memiliki pemetaan baris berkas fisik yang valid.
2. **Ketergantungan Format Output Pytest:** Jika pengguna mengonfigurasi pytest dengan plugin pengubah output radikal (misal `pytest-sugar` atau `pytest-rich`), parser regex mungkin memerlukan fallback ke Level 2. Pada ReinDev Studio, runner sandbox menggunakan flag `--color=no -v` standar sehingga output deterministik.
3. **Flakiness Stack Widget Test Flutter:** Pada widget test Flutter yang sangat dalam, traceback dapat memuat puluhan frame internal framework Flutter engine sebelum mencapai widget buatan Developer. Parser memerlukan filter eliminasi direktori SDK `packages/flutter/`.

---

## 18. Implementation Readiness Checklist

Sebelum implementasi kode P0-1 dapat dimulai pada sprint rekayasa berikutnya, kriteria kesiapan berikut harus terpenuhi:

- [x] Kontrak schema machine-readable terdefinisi lengkap (`DiagnosticEvidence`).
- [x] Taksonomi kegagalan lintas bahasa (Python & Dart) diselaraskan 100%.
- [x] Pola regex ekstraksi tanda tangan error pytest dan dart test diuji pada sampel data trace riil Phase 2.
- [x] Format payload umpan balik Developer dirancang hemat token (<600 karakter).
- [x] Mekanisme pemisahan 3 lapis bukti (Raw vs Structured vs Feedback) disepakati.
- [x] Mekanisme fallback anti-crash saat parsing gagal terdefinisi.
- [x] Skema event tracer observabilitas ditentukan.
- [x] Batasan keamanan *read-only* terkunci (larangan mutasi kode dan orakel).

---

## 19. Design Verdict

Berdasarkan kelengkapan spesifikasi, ketiadaan keputusan arsitektur besar yang menggantung, dan pemenuhan seluruh persyaratan batas keamanan sistem:

### **VERDICT:** **`READY FOR IMPLEMENTATION`**

**Rekomendasi Tahap Berikutnya:**  
Desain P0-1 ini siap untuk diimplementasikan ke dalam modul baru `backend/diagnostic_parser.py` dan diintegrasikan ke `backend/agents/developer.py` pada siklus implementasi berikutnya setelah disetujui secara resmi oleh Intent Architect.
