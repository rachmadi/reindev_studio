# Requirement Traceability Matrix (RTM) - ReinDev Studio
**Metodologi:** IIDD (Iterative Intent-Driven Development) via Siklus I-CERV  
**Status Saat Ini:** Iterasi 2 Selesai (REQ-001 s.d. REQ-014: ✅ Selesai)  
**Terakhir Diperbarui:** 2026-09-07

---

| ID Req | Deskripsi Kebutuhan | Iterasi | Status | File / Modul Implementasi |
|---|---|---|---|---|
| **REQ-001** | Inisialisasi struktur backend Python, venv, dan dependensi (LangGraph, FastAPI, Ollama/OpenAI SDK) | 1a | ✅ Selesai | backend/requirements.txt |
| **REQ-002** | Perancangan Schema State LangGraph (SquadState) untuk pelacakan konteks terpadu | 1a | ✅ Selesai | backend/state.py |
| **REQ-003** | LLM Factory provider-agnostic yang mendukung Ollama (VRAM 6GB Resident) dan OpenRouter Cloud | 1a | ✅ Selesai | backend/config.py |
| **REQ-004** | Product Manager Agent Node: memecah prompt bebas menjadi user story dan acceptance criteria | 1a | ✅ Selesai | backend/agents/pm.py |
| **REQ-005** | Developer Agent Node: menghasilkan implementasi kode modular tanpa placeholder/TODO | 1a | ✅ Selesai | backend/agents/developer.py |
| **REQ-006** | System Architect Agent Node: merancang peta struktur file (*file tree*) dan spesifikasi modul | 1b | ✅ Selesai | backend/agents/architect.py |
| **REQ-007** | QA / Tester Agent Node: menyusun test suite otomatis (pytest / flutter test) | 1b | ✅ Selesai | backend/agents/tester.py |
| **REQ-008** | Subprocess Sandbox Test Runner: eksekusi langsung test runner di lingkungan subproses lokal | 1b | ✅ Selesai | backend/executor.py |
| **REQ-009** | Cyclic Feedback Edge (Self-Healing Loop): routing otomatis log error dari QA kembali ke Dev (max 3x) | 1b | ✅ Selesai | backend/graph.py |
| **REQ-010** | Code Reviewer Agent Node: audit kepatuhan kode, keamanan dasar, dan pemberian status persetujuan rilis | 1b | ✅ Selesai | backend/agents/reviewer.py |
| **REQ-011** | FastAPI server initialization dengan middleware CORS dan endpoint health-check | 2 | ✅ Selesai | backend/server.py |
| **REQ-012** | WebSocket Hub & Connection Manager untuk streaming real-time ke client (/ws/squad) | 2 | ✅ Selesai | backend/server.py |
| **REQ-013** | Standarisasi JSON Event Protocol (agent_state, agent_thought, code_update, test_log, complete) | 2 | ✅ Selesai | backend/server.py |
| **REQ-014** | REST Endpoints untuk membaca/mengubah konfigurasi engine dan daftar project output | 2 | ✅ Selesai | backend/server.py |
| **REQ-015** | Inisialisasi proyek Flutter (Desktop Windows & Web) dengan arsitektur Riverpod | 3 | [ ] Belum Dimulai | frontend/pubspec.yaml |
| **REQ-016** | Konfigurasi ThemeData Material Design 3 (MD3) dengan dukungan Light & Dark Mode | 3 | [ ] Belum Dimulai | frontend/lib/theme/app_theme.dart |
| **REQ-017** | Layout Scaffold Studio 3-Panel Responsif (Control Hub, Workspace Canvas, Header Bar) | 3 | [ ] Belum Dimulai | frontend/lib/views/studio_screen.dart |
| **REQ-018** | Global Status Bar, Engine Indicator, dan Tombol Toggle Tema (Dark/Light) | 3 | [ ] Belum Dimulai | frontend/lib/views/widgets/app_header.dart |
| **REQ-019** | Mission Request Input Form dengan auto-expanding text field dan validasi input | 4 | [ ] Belum Dimulai | frontend/lib/views/widgets/control_panel.dart |
| **REQ-020** | Engine Switcher Dropdown (Ollama Local 6GB Resident vs OpenRouter Cloud) | 4 | [ ] Belum Dimulai | frontend/lib/views/widgets/engine_selector.dart |
| **REQ-021** | Kontrol tuning squad (slider max QA loop, selector target bahasa: Dart/Python) | 4 | [ ] Belum Dimulai | frontend/lib/views/widgets/control_panel.dart |
| **REQ-022** | Tombol Preset Cepat (FastAPI CRUD, Flutter Module, CLI Tool) & Tombol Deploy Squad | 4 | [ ] Belum Dimulai | frontend/lib/views/widgets/control_panel.dart |
| **REQ-023** | 5 Kartu Status Agent Interaktif (PM, Architect, Dev, QA, Reviewer) dengan status badge dinamis | 5 | [ ] Belum Dimulai | frontend/lib/views/widgets/agent_cards.dart |
| **REQ-024** | WebSocket Client Service (web_socket_channel) dengan Riverpod StreamProvider | 5 | [ ] Belum Dimulai | frontend/lib/services/websocket_service.dart |
| **REQ-025** | Live Auto-scrolling Agent Thought & Discussion Stream Viewer | 5 | [ ] Belum Dimulai | frontend/lib/views/widgets/thought_stream.dart |
| **REQ-026** | Animasi denyut visual (pulsing indicator) pada kartu agent yang sedang aktif mengeksekusi | 5 | [ ] Belum Dimulai | frontend/lib/views/widgets/agent_cards.dart |
| **REQ-027** | Interactive File Tree Explorer untuk menavigasi file proyek yang di-generate | 6 | [ ] Belum Dimulai | frontend/lib/views/widgets/file_explorer.dart |
| **REQ-028** | Syntax-Highlighted Code Canvas Viewer dengan opsi Copy Code dan info ukuran file | 6 | [ ] Belum Dimulai | frontend/lib/views/widgets/code_viewer.dart |
| **REQ-029** | Console Sandbox Terminal (output berwarna untuk unit test passed/failed) | 6 | [ ] Belum Dimulai | frontend/lib/views/widgets/terminal_view.dart |
| **REQ-030** | Visual Diff / Revision Viewer untuk melacak perbaikan bug yang dilakukan Dev atas feedback QA | 6 | [ ] Belum Dimulai | frontend/lib/views/widgets/diff_viewer.dart |
| **REQ-031** | Aksi Desktop Native: Buka Folder di Windows Explorer via Process.run(explorer.exe) | 7 | [ ] Belum Dimulai | frontend/lib/services/desktop_service.dart |
| **REQ-032** | Aksi Desktop Native: Buka di VS Code / Antigravity via Process.run(code) | 7 | [ ] Belum Dimulai | frontend/lib/services/desktop_service.dart |
| **REQ-033** | Fitur Export Project Bundle ke dalam arsip ZIP siap pakai | 7 | [ ] Belum Dimulai | backend/services/exporter.py |
| **REQ-034** | Skrip 1-Klik Runner (run.bat) untuk meluncurkan backend dan frontend secara bersamaan | 7 | [ ] Belum Dimulai | run.bat |
| **REQ-035** | Validasi End-to-End Pengujian Menyeluruh (Skenario Pembuatan Modul Flutter & Python) | 7 | [ ] Belum Dimulai | test/e2e_verification_test.dart |
