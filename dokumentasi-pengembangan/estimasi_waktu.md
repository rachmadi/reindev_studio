# Estimasi Waktu per Iterasi — ReinDev Studio
**Metodologi:** IIDD (Iterative Intent-Driven Development) via Siklus I-CERV  
**Platform Target:** Flutter Desktop (Windows) & Web + Python (FastAPI & LangGraph)

---

## Iterasi 1a — Core Multi-Agent Architecture & StateGraph Engine
| Fitur / Komponen | Estimasi (jam) |
|---|---|
| Inisialisasi struktur backend & virtual environment (.venv) | 1.0 |
| Schema State LangGraph (state.py - SquadState) | 1.0 |
| LLM Factory provider-agnostic (config.py - Ollama 6GB Resident & OpenRouter) | 1.5 |
| Product Manager Agent node & prompt engineering (gents/pm.py) | 1.5 |
| Developer Agent node & modular code synthesizer (gents/developer.py) | 1.5 |
| **Total Estimasi Iterasi 1a** | **6.5 jam** |

---

## Iterasi 1b — Complete Squad Pipeline & Self-Healing Cyclic Test Loop
| Fitur / Komponen | Estimasi (jam) |
|---|---|
| System Architect Agent node & file tree blueprint (gents/architect.py) | 1.5 |
| QA / Tester Agent node & test generator (gents/tester.py) | 1.5 |
| Subprocess Sandbox Test Runner (executor.py - pytest & dart analyze) | 2.0 |
| Cyclic Feedback Loop (Conditional Edge routing QA fail -> Dev) | 1.5 |
| Code Reviewer Agent node & audit logic (gents/reviewer.py) | 1.0 |
| **Total Estimasi Iterasi 1b** | **7.5 jam** |

---

## Iterasi 2 — FastAPI Server & Real-time WebSocket Protocol
| Fitur / Komponen | Estimasi (jam) |
|---|---|
| FastAPI server scaffold & CORS configuration (server.py) | 1.0 |
| WebSocket Hub & event connection manager (/ws/squad) | 1.5 |
| JSON Event Protocol design & streaming dispatcher | 1.5 |
| REST Endpoints (config read/update & generated projects management) | 1.0 |
| Integration tests untuk WebSocket communication | 1.0 |
| **Total Estimasi Iterasi 2** | **6.0 jam** |

---

## Iterasi 3 — Flutter UI Shell, MD3 Theming & Responsive Layout
| Fitur / Komponen | Estimasi (jam) |
|---|---|
| Inisialisasi Flutter project (Windows Desktop & Web) + Riverpod | 1.5 |
| Konfigurasi Material Design 3 (MD3) ThemeData (Light/Dark & ColorScheme) | 1.5 |
| Three-Panel Studio Layout Scaffold (Control, Main Workspace, Header) | 2.0 |
| Top Navbar, Global Status Badge, & Dark/Light Mode Switcher | 1.5 |
| **Total Estimasi Iterasi 3** | **6.5 jam** |

---

## Iterasi 4 — Control Hub & Engine Switcher Panel
| Fitur / Komponen | Estimasi (jam) |
|---|---|
| Mission Request Input Field dengan auto-expanding & character counter | 1.5 |
| Engine Switcher UI (Ollama Local 6GB Resident vs OpenRouter Cloud) | 1.5 |
| Squad Tuning Controls (Max QA loops, target language selector) | 1.0 |
| Quick Preset Mission Buttons (FastAPI, Flutter Module, CLI) | 0.5 |
| Deploy Squad Button dengan loading visual & state guardrails | 1.0 |
| **Total Estimasi Iterasi 4** | **5.5 jam** |

---

## Iterasi 5 — Live Pipeline & Interactive Agent Cards Timeline
| Fitur / Komponen | Estimasi (jam) |
|---|---|
| 5 Interactive Agent Status Cards (PM, Architect, Dev, QA, Reviewer) | 2.0 |
| WebSocket Client Service (web_socket_channel + Riverpod state stream) | 2.0 |
| Live Auto-scrolling Agent Thought & Discussion Stream Widget | 2.0 |
| Pulsing Animation & dynamic state badge rendering | 1.0 |
| **Total Estimasi Iterasi 5** | **7.0 jam** |

---

## Iterasi 6 — Code Explorer & Sandbox Terminal
| Fitur / Komponen | Estimasi (jam) |
|---|---|
| Interactive File Tree Explorer untuk generated project | 2.0 |
| Syntax-Highlighted Code Canvas Viewer dengan copy to clipboard | 2.0 |
| Black Terminal Sandbox Viewer (real-time test output & logs) | 2.0 |
| Visual diff / error indicator viewer saat perbaikan bug QA | 1.0 |
| **Total Estimasi Iterasi 6** | **7.0 jam** |

---

## Iterasi 7 — Native Desktop Integration, Export, & End-to-End Verification
| Fitur / Komponen | Estimasi (jam) |
|---|---|
| Native Windows Actions (Open in Explorer & Open in VS Code via Process) | 1.5 |
| Export Generated Project as ZIP Archive | 1.5 |
| One-Click Launch Script (
un.bat for Backend + Flutter Desktop) | 1.0 |
| End-to-End Testing & Comprehensive Scenario Validation | 2.0 |
| **Total Estimasi Iterasi 7** | **6.0 jam** |

---

## Ringkasan Total Estimasi Proyek
| Iterasi | Nama Iterasi | Estimasi (jam) |
|---|---|---|
| Iterasi 1a | Core Multi-Agent Architecture & StateGraph Engine | 6.5 |
| Iterasi 1b | Complete Squad Pipeline & Self-Healing Cyclic Test Loop | 7.5 |
| Iterasi 2 | FastAPI Server & Real-time WebSocket Protocol | 6.0 |
| Iterasi 3 | Flutter UI Shell, MD3 Theming & Responsive Layout | 6.5 |
| Iterasi 4 | Control Hub & Engine Switcher Panel | 5.5 |
| Iterasi 5 | Live Pipeline & Interactive Agent Cards Timeline | 7.0 |
| Iterasi 6 | Code Explorer & Sandbox Terminal | 7.0 |
| Iterasi 7 | Native Desktop Integration, Export, & End-to-End Verification | 6.0 |
| **TOTAL KESELURUHAN** | | **52.0 jam** |
