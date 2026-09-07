# SPESIFIKASI PERANGKAT LUNAK
# ReinDev Studio
**Autonomous Multi-Agent Software Engineering Studio**  
*Implementasi Flutter Desktop (Windows) & Web dengan Engine LangGraph + FastAPI*  
**Dikembangkan dengan:** Google Antigravity (Agentic IDE)  
**Berdasarkan Metodologi:** IIDD (Iterative Intent-Driven Development) via Siklus I-CERV  
**Entitas Pengembang:** Rekayasa Informatika  
**Intent Architect:** Muhammad Rachmadi  
**Versi Dokumen:** 1.0 (Final Draft)

---

## 1. Ringkasan Eksekutif
ReinDev Studio adalah aplikasi studio rekayasa perangkat lunak multi-agent otonom yang dirancang untuk mengikis fenomena vibes coding dan menegakkan tata kelola rekayasa perangkat lunak (Software Engineering Governance). Aplikasi ini mengorkestrasi satu tim virtual spesialis (Product Manager, System Architect, Developer, QA Tester, dan Code Reviewer) yang bekerja secara terkoordinasi untuk mengubah visi/intensi manusia menjadi perangkat lunak siap produksi yang teruji.

Aplikasi ini dibangun menggunakan arsitektur decoupled:
1. **Frontend:** Dibangun menggunakan Flutter Desktop (Windows Native) dan Flutter Web dengan Material Design 3 (MD3) dan Flutter Riverpod.
2. **Backend:** Dibangun menggunakan Python 3.13, FastAPI, LangGraph StateGraph, dan Subprocess Sandbox Test Runner (pytest dan flutter test / dart analyze).
3. **Engine Hybrid:**
   - **Lokal (Ollama):** Menggunakan model resident VRAM 6GB (`qwen2.5-coder:7b`) untuk operasional 100% offline, hemat biaya, dan tanpa model-swapping.
   - **Cloud (OpenRouter):** Menggunakan Gemini Flash / Claude Sonnet / Qwen3-Coder untuk penalaran tingkat tinggi.

---

## 2. Arsitektur Sistem dan Spesifikasi Komponen

### 2.1 Stack Teknologi
- **Frontend:** Flutter SDK 3.47+, Dart 3.13+, `flutter_riverpod`, `web_socket_channel`, `google_fonts`.
- **Backend:** Python 3.13+, FastAPI, Uvicorn, LangGraph, LangChain, Pydantic, Subprocess Sandbox.
- **Protokol:** WebSocket (`ws://localhost:8000/ws/squad`) untuk streaming real-time event dan REST API untuk konfigurasi.

### 2.2 Dekomposisi Modul
```text
reindev_studio/
├── backend/
│   ├── agents/
│   │   ├── pm.py              # Product Manager logic & prompt
│   │   ├── architect.py       # System Architect logic & file tree design
│   │   ├── developer.py       # Developer code synthesizer
│   │   ├── tester.py          # QA test generator
│   │   └── reviewer.py        # Code Reviewer audit logic
│   ├── config.py              # LLM Factory (Ollama 6GB Resident & OpenRouter)
│   ├── executor.py            # Subprocess test runner (pytest & dart analyze)
│   ├── graph.py               # LangGraph StateGraph & cyclic test feedback loop
│   ├── server.py              # FastAPI server & WebSocket connection hub
│   ├── state.py               # SquadState schema (TypedDict)
│   └── output/                # Target folder project hasil generate
│
├── frontend/
│   ├── lib/
│   │   ├── main.dart          # Entry point & ProviderScope
│   │   ├── theme/             # Material Design 3 configuration
│   │   ├── models/            # Event models & agent state
│   │   ├── services/          # WebSocket client & desktop process service
│   │   └── views/             # StudioScreen, ControlPanel, AgentTimeline, CodeViewer, TerminalView
│   └── pubspec.yaml
│
└── dokumentasi-pengembangan/  # Seluruh log empiris validasi IIDD
```

---

## 3. Spesifikasi Fitur per Siklus I-CERV

Setiap iterasi mengikuti siklus baku: **Intent** -> **Context** -> **Execution (Instruksi untuk Antigravity)** -> **Re-Evaluation (Micro Loop Agen)** -> **Handoff Validation Gate (Macro Loop Intent Architect)**.

### 📌 Protokol Pengujian Pra-Handoff & Headed Interactive Testing
1. **Pengujian Mandiri Agen (Sebelum Handoff):**
   - Agen wajib merancang skenario *Test Cases* formal untuk fitur yang dibangun pada iterasi tersebut.
   - Untuk modul backend/logika: Agen mengeksekusi test suite secara riil di lingkungan terminal/subproses lokal.
   - Untuk modul antarmuka pengguna (UI/Flutter): Agen menjalankan aplikasi secara **headed interactive testing** (pada Chrome atau Windows Desktop), mengambil tangkapan layar (**screenshot**), menganalisis screenshot tersebut secara visual, dan mendokumentasikan analisisnya di dokumentasi-pengembangan/interactive_test_log.md serta menyimpan gambarnya di folder dokumentasi-pengembangan/screenshots/iterasi_[N]/.
2. **Penyediaan Test Case untuk Intent Architect (Saat Handoff):**
   - Saat handoff, agen tidak hanya melaporkan bahwa kode telah selesai, melainkan **wajib menyusun daftar skenario Test Cases terstruktur langkah-demi-langkah bagi Intent Architect**.
   - Intent Architect menjalankan skenario tersebut untuk mengevaluasi *Global Correctness* dan memberikan putusan resmi: **PASS**, **PASS WITH NOTES**, atau **FAIL**.

---

### Iterasi 1a — Backend Foundation: State & Core Agents (LangGraph, PM, Dev)

#### Intent
Membangun fondasi backend engine LangGraph: mendefinisikan wadah state terpadu (`SquadState`), mekanisme LLM Factory hemat VRAM 6GB, serta dua node agent pertama (Product Manager dan Developer) untuk memvalidasi aliran data dan inferensi teks dasar.

#### Context
- StateGraph LangGraph mengelola aliran data berbasis skema `TypedDict`.
- VRAM 6GB mengharuskan Ollama menggunakan satu model resident (`qwen2.5-coder:7b`) agar tidak terjadi penalti model-swapping.
- Product Manager bertugas memecah kebutuhan menjadi user stories dan kriteria penerimaan.
- Developer bertugas menghasilkan kode Python/Dart modular.

#### Execution (untuk Antigravity)
1. Inisialisasi struktur backend di `backend/` dan siapkan `backend/requirements.txt` (langgraph, langchain-core, langchain-ollama, langchain-openai, pydantic, python-dotenv).
2. Buat `backend/state.py` dengan class `SquadState(TypedDict)`:
   - `task: str`, `provider: str`, `specifications: str`, `architecture_plan: str`, `code_files: dict[str, str]`, `test_files: dict[str, str]`, `test_results: dict`, `iteration_count: int`, `review_notes: str`, `status: str`.
3. Buat `backend/config.py`:
   - Fungsi `get_llm(role, provider)` yang membaca `.env`. Default provider `ollama` mengarah ke `http://localhost:11434` dengan model `qwen2.5-coder:7b`.
4. Buat `backend/agents/pm.py`:
   - Node `pm_agent(state: SquadState)`: Prompt terstruktur untuk memecah `state['task']` menjadi spesifikasi teknis dan acceptance criteria.
5. Buat `backend/agents/developer.py`:
   - Node `developer_agent(state: SquadState)`: Prompt terstruktur untuk menghasilkan kode modular berdasarkan spesifikasi PM.
6. Buat skrip runner uji internal `backend/test_iterasi_1a.py` untuk menguji aliran PM -> Dev secara lokal.

#### Re-Evaluation (Micro Loop Agen)
- Script `backend/test_iterasi_1a.py` berhasil dieksekusi tanpa error crash.
- `pm_agent` menghasilkan teks spesifikasi yang memuat kriteria penerimaan.
- `developer_agent` menghasilkan kamus kode program tanpa placeholder.

#### Handoff Validation Gate ke Intent Architect
- Agen melaporkan hasil uji konsol dan output spesifikasi serta kode yang dihasilkan.
- Menunggu respons IA: `PASS` / `PASS WITH NOTES` / `FAIL`.

---

### Iterasi 1b — Squad Pipeline: Architect, QA Sandbox Runner, Reviewer, & Cyclic Feedback Loop

#### Intent
Melengkapi tim virtual menjadi 5 peran penuh (menambahkan System Architect, QA Tester, dan Code Reviewer) serta mengimplementasikan siklus umpan balik mandiri (Self-Healing Cyclic Loop) dengan eksekusi nyata subproses test runner.

#### Context
- Architect memetakan hierarki file proyek sebelum Developer menulis kode.
- QA menulis test suite otomatis (pytest untuk Python, dart analyze / flutter test untuk Dart).
- Executor menjalankan test di subprocess nyata. Jika gagal (`exit_code != 0`), alur kembali ke Developer dengan log error.
- Reviewer memberikan audit keamanan, standar penamaan, dan persetujuan rilis.

#### Execution (untuk Antigravity)
1. Buat `backend/agents/architect.py`:
   - Node `architect_agent`: Menghasilkan rencana file tree dan pemisahan modul.
2. Buat `backend/agents/tester.py`:
   - Node `tester_agent`: Menghasilkan kode unit test sesuai file yang dibuat Developer.
3. Buat `backend/executor.py`:
   - Fungsi `run_test_sandbox(project_dir, language)`: Menulis file ke `backend/output/sandbox/`, lalu mengeksekusi pytest atau dart analyze via `subprocess.run`, menangkap `stdout`, `stderr`, dan `returncode`.
4. Buat `backend/agents/reviewer.py`:
   - Node `reviewer_agent`: Menganalisis kode dan hasil test, memberikan catatan audit dan rekomendasi approval.
5. Buat `backend/graph.py`:
   - Menyusun StateGraph lengkap: `PM -> Architect -> Developer -> Tester -> [Conditional Edge: Test Pass? -> Reviewer | Test Fail? (max 3x) -> Developer] -> End`.
6. Siapkan skrip pengujian `backend/test_iterasi_1b.py`.

#### Re-Evaluation (Micro Loop Agen)
- Graph dapat mengeksekusi skenario sukses (tes lulus -> lanjut ke Reviewer).
- Graph dapat menangani skenario sengaja gagal (tes gagal -> otomatis loop kembali ke Dev untuk perbaikan hingga lulus).
- Guardrail limit iterasi (maksimal 3x) mencegah infinite loop.

#### Handoff Validation Gate ke Intent Architect
- Agen mendemonstrasikan log eksekusi siklus umpan balik di terminal.
- IA menguji apakah Developer benar-benar memperbaiki error sesuai traceback test runner.

---

### Iterasi 2 — Real-Time Communication: FastAPI & WebSocket Protocol

#### Intent
Membungkus engine LangGraph ke dalam server FastAPI dan menyediakan endpoint WebSocket `/ws/squad` untuk streaming real-time status agen, pemikiran agen, log pengujian, dan pembaruan kode.

#### Context
- Frontend Flutter membutuhkan pembaruan instan (push notification via WebSocket) setiap kali agen berpindah status atau menghasilkan teks.
- Format komunikasi menggunakan protokol JSON yang terstandarisasi.

#### Execution (untuk Antigravity)
1. Buat `backend/server.py`:
   - Inisialisasi FastAPI dengan middleware CORS.
   - Endpoint WebSocket: `/ws/squad`.
   - REST Endpoints: `GET /api/health`, `GET /api/config`, `POST /api/config`.
2. Implementasi Event Broadcaster di `server.py`:
   - Tipe event: `agent_start`, `agent_thought`, `code_update`, `test_log`, `review_report`, `complete`, `error`.
3. Integrasikan LangGraph StateGraph streaming callback ke dalam WebSocket dispatcher.
4. Buat skrip klien uji `backend/test_ws_client.py` untuk memverifikasi streaming payload event.

#### Re-Evaluation (Micro Loop Agen)
- FastAPI server berjalan di `http://127.0.0.1:8000`.
- Klien WebSocket dapat terhubung, mengirimkan task prompt, dan menerima rentetan event JSON secara berurutan hingga `complete`.

#### Handoff Validation Gate ke Intent Architect
- IA memverifikasi server berjalan dan merespons koneksi WebSocket.

---

### Iterasi 3 — Frontend Foundation: Flutter UI Shell, MD3 Theming & Responsive Layout

#### Intent
Membangun cangkang antarmuka pengguna Flutter (Desktop Windows dan Web) dengan menerapkan standar Material Design 3 (MD3), arsitektur Riverpod, dan tata letak 3-panel studio yang responsif.

#### Context
- Target platform: Windows Desktop Native dan Web.
- Desain mengikuti prinsip MD3: ColorScheme yang konsisten, dukungan Dark Mode dan Light Mode tanpa warna hardcoded, tipografi rapi.
- Layout terdiri dari: Top Header/Navbar, Left Control Hub, dan Main Tabbed Workspace.

#### Execution (untuk Antigravity)
1. Inisialisasi project Flutter di folder `frontend/`:
   - `flutter create frontend --platforms=windows,web`
2. Tambahkan dependencies di `frontend/pubspec.yaml`:
   - `flutter_riverpod`, `web_socket_channel`, `google_fonts`.
3. Buat `frontend/lib/theme/app_theme.dart`:
   - Konfigurasi `ThemeData` MD3 untuk `lightTheme` dan `darkTheme`.
4. Buat `frontend/lib/views/studio_screen.dart`:
   - Scaffold utama 3-panel: Top AppBar (judul dan engine badge), Left Panel (lebar tetap 320px), Center Workspace (fleksibel).
5. Buat widget `app_header.dart` dengan toggle Dark/Light Mode dan status indikator koneksi backend.

#### Re-Evaluation (Micro Loop Agen)
- `flutter analyze` di folder `frontend/` menghasilkan 0 error dan 0 warning.
- Aplikasi berhasil dikompilasi dan berjalan mulus di Windows Desktop (`flutter run -d windows`).

#### Handoff Validation Gate ke Intent Architect
- IA menjalankan aplikasi di desktop/web dan menguji tombol toggle tema serta responsivitas layout.

---

### Iterasi 4 — Mission Control Hub: Prompt Input, Model Switcher (Ollama 6GB / OpenRouter) & Presets

#### Intent
Mengimplementasikan panel kontrol interaktif di sisi kiri untuk memasukkan ide fitur/proyek, memilih mesin AI (Ollama resident VRAM 6GB vs OpenRouter Cloud), mengatur parameter tuning, dan tombol aksi "Deploy Squad".

#### Context
- Input field harus mendukung auto-expanding multiline text.
- Dropdown engine menampilkan model lokal (`qwen2.5-coder:7b`) dan opsi cloud (Gemini Flash, Claude Sonnet).
- Tombol preset cepat memudahkan pengujian tanpa mengetik manual.

#### Execution (untuk Antigravity)
1. Buat `frontend/lib/views/widgets/control_panel.dart`.
2. Buat `frontend/lib/views/widgets/engine_selector.dart`:
   - Dropdown pilihan LLM Provider: Ollama Local (Resident 6GB) vs OpenRouter Cloud.
3. Tambahkan kontrol tuning: Slider Max QA Loops (1-5) dan selector target bahasa (Dart vs Python).
4. Tambahkan tombol preset cepat (FastAPI CRUD, Flutter Widget/Model, CLI Calculator).
5. Tambahkan tombol utama "Deploy Squad" dengan indikator loading aktif saat sistem berjalan.

#### Re-Evaluation (Micro Loop Agen)
- Input prompt tervalidasi (tidak boleh kosong).
- Nilai konfigurasi mesin tersimpan di state Riverpod.
- `flutter analyze` 100% clean.

#### Handoff Validation Gate ke Intent Architect
- IA menguji pergantian engine di dropdown dan memastikan input prompt merespons preset dengan benar.

---

### Iterasi 5 — Agent Pipeline Visualization: Interactive Cards, Real-time Thought Stream & Status Animations

#### Intent
Menghubungkan frontend Flutter ke WebSocket backend untuk menampilkan progres langsung: 5 kartu status agen interaktif dengan animasi denyut visual dan log pemikiran (thought stream) yang bergulir otomatis.

#### Context
- 5 Kartu Agen: Product Manager, System Architect, Developer, QA Tester, Code Reviewer.
- Status dinamis: `Idle`, `Working...` (denyut biru), `Success` (hijau), `Retrying` (kuning jika pengujian gagal).
- Log stream menampilkan pemikiran mendalam agen dan pesan diskusi secara real-time.

#### Execution (untuk Antigravity)
1. Buat `frontend/lib/services/websocket_service.dart`:
   - Mengelola koneksi WebSocket, reconnect otomatis, dan parsing stream JSON event.
2. Buat `frontend/lib/models/agent_event.dart`.
3. Buat `frontend/lib/views/widgets/agent_cards.dart`:
   - Grid 5 kartu agen dengan animasi pulse ring pada agen yang aktif.
4. Buat `frontend/lib/views/widgets/thought_stream.dart`:
   - List view log auto-scroll ke bawah saat ada pesan baru dari backend.
5. Hubungkan tombol "Deploy Squad" untuk memicu pengiriman payload misi ke WebSocket backend.

#### Re-Evaluation (Micro Loop Agen)
- Saat task dikirim, kartu PM berubah menjadi `Working...`, lalu `Success`, dilanjutkan kartu Architect, Dev, QA, dan Reviewer.
- Log pemikiran muncul di stream secara real-time tanpa lag UI.

#### Handoff Validation Gate ke Intent Architect
- IA menekan tombol "Deploy Squad" dan memverifikasi alur visual kartu agen serta streaming pemikiran agen.

---

### Iterasi 6 — Code Explorer & Sandbox Terminal: File Tree, Syntax Highlighter, & Pytest/Dart Test Output

#### Intent
Membangun dua tab esensial pada workspace utama: Tab penjelajah file kode (Code Explorer) dengan pewarnaan sintaksis, dan Tab konsol terminal hitam untuk memantau eksekusi pytest / dart analyze secara nyata.

#### Context
- Pengguna ingin langsung melihat, memeriksa, dan menyalin kode yang dibuat oleh Developer Agent.
- Pengguna ingin melihat transparansi pengujian sandbox (mengetahui unit test mana yang lulus dan mana yang gagal).

#### Execution (untuk Antigravity)
1. Buat `frontend/lib/views/widgets/file_explorer.dart`:
   - Sidebar pohon file proyek yang dihasilkan (misal: `main.py`, `models.py`, `test_main.py`).
2. Buat `frontend/lib/views/widgets/code_viewer.dart`:
   - Area penampil kode dengan nomor baris, pewarnaan sintaksis, dan tombol "Copy Code".
3. Buat `frontend/lib/views/widgets/terminal_view.dart`:
   - Jendela terminal bertema hitam dengan teks font monospace berwarna hijau/merah menampilkan log eksekusi pytest atau dart analyze.
4. Buat `frontend/lib/views/widgets/diff_viewer.dart`:
   - Menampilkan ringkasan baris yang direvisi oleh Developer saat menanggapi kegagalan tes QA.

#### Re-Evaluation (Micro Loop Agen)
- File yang dihasilkan backend otomatis muncul di File Explorer.
- Mengklik file di explorer langsung memperbarui isi kode di Code Viewer.
- Log output pengujian tampil rapi di Terminal View.

#### Handoff Validation Gate ke Intent Architect
- IA mengklik tab "Project Files and Code" untuk membaca kode hasil generate, dan memeriksa keaslian log di tab "Pytest/Dart Terminal".

---

### Iterasi 7 — Native Desktop Integration, Export ZIP, & End-to-End Verification

#### Intent
Menyempurnakan kapabilitas desktop native (buka folder di Windows Explorer dan buka di IDE dengan 1 klik), fitur export proyek ke ZIP, skrip 1-klik runner (`run.bat`), dan pengujian validasi menyeluruh (End-to-End).

#### Context
- Aplikasi desktop Windows memiliki keunggulan akses native `Process.run`.
- Skrip `run.bat` di root memudahkan pengguna meluncurkan backend Uvicorn dan frontend Flutter sekaligus.

#### Execution (untuk Antigravity)
1. Buat `frontend/lib/services/desktop_service.dart`:
   - `openInExplorer(String path)` via `Process.run('explorer.exe', [path])`.
   - `openInCode(String path)` via `Process.run('code', [path])`.
2. Buat `backend/services/exporter.py`:
   - Fungsi kompresi direktori proyek hasil generate menjadi file `.zip`.
3. Buat file `run.bat` di root project:
   - Mengaktifkan venv, meluncurkan Uvicorn di background, dan meluncurkan Flutter Windows.
4. Uji skenario menyeluruh:
   - Skenario A: Pembuatan Modul REST API Python (FastAPI + Pytest).
   - Skenario B: Pembuatan Komponen Dart / Flutter (Model + Unit Test).
5. Finalisasi dokumentasi penelitian di `dokumentasi-pengembangan/`.

#### Re-Evaluation (Micro Loop Agen)
- Tombol "Buka di Explorer" membuka folder proyek di Windows Explorer.
- Tombol "Export ZIP" menghasilkan arsip ZIP yang valid dan bisa diekstrak.
- Skrip `run.bat` berhasil meluncurkan kedua sistem tanpa error.

#### Handoff Validation Gate ke Intent Architect
- IA melakukan pengujian end-to-end secara penuh, mengevaluasi kualitas sistem, dan memberikan keputusan rilis final.

---

## 4. Protokol Validasi Data Penelitian IIDD (Folder `dokumentasi-pengembangan/`)

Sesuai metodologi IIDD, Antigravity bertanggung jawab memperbarui 11 file log kumulatif setelah setiap iterasi dinyatakan PASS oleh Intent Architect:
1. `context_drift_log.md`: Mencatat drift intensi vs realisasi implementasi.
2. `validation_log.md`: Mencatat keputusan dan catatan evaluasi IA di Validation Gate.
3. `conversation_log.md`: Disediakan untuk transkrip verbatim percakapan.
4. `decision_log.md`: Mencatat keputusan arsitektural dan pertimbangan teknis agen.
5. `commit_history.md`: Ringkasan naratif riwayat commit Git.
6. `iteration_summary.md`: Rangkuman capaian fitur setiap iterasi.
7. `waktu_estimasi_vs_realisasi.md`: Perbandingan estimasi jam vs durasi riil.
8. `durasi_per_fitur.md`: Pelacakan durasi per modul fitur spesifik.
9. `human_intervention.md`: Catatan setiap intervensi manusia (Macro Loop).
10. `error_log.md`: Klasifikasi galat teknis dan tindakan koreksinya.
11. `interactive_test_log.md`: Hasil pengujian skenario interaktif beserta tangkapan layar di `screenshots/iterasi_[N]/`.

Setiap commit akhir iterasi wajib menggunakan format atomik:
`iterasi [N]: [nama iterasi singkat] — kode + dokumentasi`
