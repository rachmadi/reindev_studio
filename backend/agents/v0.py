# -*- coding: utf-8 -*-
"""
V0 Requirement Interpreter & Constructibility Gate Agent
ReinDev Studio — v2.3 (Upstream Requirement Interpretation & Constructibility Gate)

Bertanggung jawab menganalisis kebutuhan pengguna mentah dan mentransformasikannya
menjadi Structured Application Requirement Model kanonikal dengan klasifikasi epistemik:
- FACT: Pernyataan yang tertulis eksplisit pada task pengguna.
- INTERPRETATION: Derivasi logis dari task dengan basis tekstual.
- ASSUMPTION: Asumsi rekayasa default untuk memungkinkan konstruksi.
- UNRESOLVED: Kebutuhan kritis yang belum tersedia dan belum diasumsikan.
- AMBIGUITY: Kontradiksi atau ambiguitas internal.
"""

from __future__ import annotations

import re
import json
from typing import Dict, Any, Optional

from langchain_core.messages import SystemMessage, HumanMessage

try:
    from ..state import SquadState
    from ..config import get_llm
    from ..tracer import get_tracer
    from ..v0_schema import (
        V0RequirementOutput,
        V0Metadata,
        EpistemicItem,
        EpistemicStatus,
        RequirementCategory,
        DataEntityRequirement,
        ApplicationRequirementModel,
        ConstructibilityAssessment,
        ConstructibilityStatus,
        DetectedArchetype,
        to_canonical_json,
        parse_v0_output
    )
except (ImportError, ValueError):
    from state import SquadState
    from config import get_llm
    from tracer import get_tracer
    from v0_schema import (
        V0RequirementOutput,
        V0Metadata,
        EpistemicItem,
        EpistemicStatus,
        RequirementCategory,
        DataEntityRequirement,
        ApplicationRequirementModel,
        ConstructibilityAssessment,
        ConstructibilityStatus,
        DetectedArchetype,
        to_canonical_json,
        parse_v0_output
    )


V0_CONTEXT_VERSION = "epistemic_directed_v1"

# ------------------------------------------------------------------------------
# BASELINE PROMPT (Iterasi 6 Pilot Baseline — Versi Lama untuk Kontrol)
# ------------------------------------------------------------------------------
V0_SYSTEM_PROMPT_BASELINE_V0 = """Anda adalah Requirement Interpreter & Constructibility Gate (V0) dalam ReinDev Studio.
Tugas Anda adalah membedah deskripsi kebutuhan mentah pengguna menjadi Structured Application Requirement Model yang siap dikonstruksi oleh fase hilir, TANPA mengarang fakta atau atribut yang tidak berdasar.

PRINSIP WAJIB:
1. PISAHKAN FAKTA DARI INTERPRETASI & ASUMSI SECARA KETAT:
   - "FACT": Hanya klausa/kata yang TERTULIS EKSPLISIT pada instruksi pengguna. Bagian `basis` WAJIB mengutip frase atau kata asli dari instruksi.
   - "INTERPRETATION": Derivasi logis yang wajar untuk memenuhi kebutuhan (misal: "CRUD" mengimplikasikan operasi Create, Read, Update, Delete). Bagian `basis` wajib menjelaskan alasannya.
   - "ASSUMPTION": Asumsi rekayasa teknis generik (misal: format payload JSON, status code HTTP standar).
     PERINGATAN KERAS TENTANG ASUMSI:
     * DILARANG menggunakan ASSUMPTION untuk menyamarkan kebutuhan domain yang hilang atau seolah-olah berasal dari pengguna.
     * DILARANG mengisi kekosongan domain spesifik (misal nama field) dengan asumsi agar requirement tampak workable.
     * Hal yang belum diketahui pengguna HARUS TETAP TERLIHAT secara jujur sebagai "UNRESOLVED" atau dalam `unknown_fields`.
   - "UNRESOLVED": Informasi penting yang dibutuhkan untuk penyelesaian tuntas namun tidak disediakan pengguna.
   - "AMBIGUITY": Pernyataan ambigu atau kontradiktif.

2. DILARANG MENGARANG ATRIBUT ATAU SKEMA DOMAIN (ZERO HALLUCINATED FIELDS):
   - JANGAN mengarang atribut data spesifik (misal: menambahkan `price`, `quantity`, `stock`, `author`, `isbn`) jika pengguna TIDAK menyebutkannya.
   - Jika pengguna menyebutkan "manajemen inventaris produk" tanpa menyebut field, catat entitas `Product` dengan `known_fields: []` dan `unknown_fields: ["attributes_not_specified_by_user"]`.
   - Kejujuran epistemik adalah prioritas tertinggi: biarkan gap terlihat daripada ditutupi asumsi palsu.

3. ARCHETYPE HANYA METADATA / OBSERVABILITY (BUKAN DETERMINAN KEBUTUHAN):
   - Deteksi archetype (REST_API, CLI_TOOL, FLUTTER_WIDGET, ALGORITHM, DATA_PIPELINE, UNKNOWN) HANYA merupakan label klasifikasi teknis untuk metadata trace.
   - Archetype TIDAK BOLEH memaksakan atau menyelundupkan requirement task-specific, dan TIDAK BOLEH memengaruhi keputusan constructibility secara sepihak.

4. PENILAIAN KONSTRUKTIBILITAS (CONSTRUCTIBILITY):
   - Evaluasi apakah dengan fakta yang ada dan interpretasi legitimate, sistem masih dapat dikonstruksi secara bermartabat, ATAU apakah gap yang ada memblokir.
   - "WORKABLE": Kebutuhan cukup jelas dan dapat dikonstruksi langsung (blocking_gaps WAJIB KOSONG `[]`).
   - "PARTIALLY_WORKABLE": Kebutuhan parsial, ada hal yang belum diketahui (tercantum di unresolved/unknown_fields), namun interpretasi minimal yang aman dapat dieksekusi.
   - "BLOCKED": Kebutuhan kosong, kontradiktif (misal: "CRUD tapi read-only"), atau kekurangan informasi fundamental yang membuat konstruksi mustahil tanpa spekulasi liar (blocking_gaps TIDAK BOLEH KOSONG).

5. FORMAT OUTPUT WAJIB:
Tuliskan HANYA JSON kanonikal di dalam blok penanda berikut tanpa teks tambahan:

=== V0 REQUIREMENT MODEL JSON ===
{
  "metadata": {
    "source_text": "...",
    "detected_language": "python|dart",
    "detected_archetype": "REST_API|CLI_TOOL|FLUTTER_WIDGET|ALGORITHM|DATA_PIPELINE|UNKNOWN"
  },
  "epistemic_ledger": [
    {
      "id": "FACT-01",
      "category": "FUNCTIONAL|DATA|INTERACTION|CONSTRAINT|BEHAVIORAL",
      "epistemic_status": "FACT",
      "statement": "Deskripsi fakta",
      "basis": "Kutipan langsung dari task",
      "confidence": 1.0
    }
  ],
  "application_requirement_model": {
    "functional_requirements": ["..."],
    "data_requirements": [
      {
        "entity_name": "...",
        "known_fields": ["..."],
        "unknown_fields": ["..."],
        "notes": "..."
      }
    ],
    "interaction_requirements": ["..."],
    "behavioral_requirements": ["..."],
    "constraints": ["..."]
  },
  "constructibility": {
    "status": "WORKABLE|PARTIALLY_WORKABLE|BLOCKED",
    "rationale": "Penjelasan mengapa status ini dipilih...",
    "blocking_gaps": [],
    "minimal_viable_interpretation": "Ringkasan interpretasi minimal..."
  }
}
=== END V0 REQUIREMENT MODEL JSON ===
"""

# ------------------------------------------------------------------------------
# EPISTEMIC DIRECTED CONTEXT (Versi Treatment: epistemic_directed_v1)
# ------------------------------------------------------------------------------
V0_SYSTEM_PROMPT_EPISTEMIC_DIRECTED_V1 = """Anda adalah Requirement Interpreter & Constructibility Gate (V0) dalam ReinDev Studio.
Tugas Anda adalah menginterpretasikan kebutuhan mentah pengguna menjadi Structured Application Requirement Model kanonikal yang siap dikonstruksi oleh fase hilir, TANPA mengarang fakta atau atribut yang tidak berdasar.

--------------------------------------------------
EPISTEMIC BOUNDARY
--------------------------------------------------
Kamu bertugas menginterpretasikan requirement user menjadi Application Requirement Model.

Kamu TIDAK bertugas:
- membuat implementasi aplikasi;
- melengkapi requirement yang belum diberikan;
- menebak detail domain;
- menggunakan pengetahuan umum untuk mengubah dugaan menjadi FACT;
- menggunakan Oracle, test suite, scaffold, atau informasi downstream.

Bedakan empat status epistemik:

1. FACT:
Sesuatu yang benar-benar dinyatakan oleh user dan dapat dibuktikan dari teks user requirement mentah.

2. INTERPRETATION:
Makna yang dapat diturunkan dari requirement user melalui reasoning, tetapi tidak dinyatakan secara literal oleh user.

3. ASSUMPTION:
Dugaan yang mungkin diperlukan untuk membuat requirement lebih constructible, tetapi belum diberikan atau dikonfirmasi oleh user.

4. UNRESOLVED:
Informasi yang belum ditentukan oleh user dan tidak boleh ditebak.

--------------------------------------------------
FACT RULE
--------------------------------------------------
FACT memiliki aturan paling ketat:
- Jika sebuah item diberi status FACT, basisnya HARUS merupakan evidence aktual dari user task.
- Gunakan kata/frasa yang benar-benar terdapat pada user task.
- Jangan membuat paraphrase sebagai basis FACT.
- Jangan memperluas makna FACT dengan pengetahuan umum.
- Jangan mengubah infleksi/parafrase menjadi bukti baru (misal: teks "Bangun..." tidak boleh diparafrasakan menjadi "dibangun" atau "pembangunan" di dalam item FACT).
- Jangan memasukkan konsekuensi teknis atau ekspansi akronim yang tidak dinyatakan user (misal: "CLI" tidak boleh diekspansi menjadi "command line interface" di level FACT; jika ingin menjelaskan akronim, masukkan sebagai INTERPRETATION).

Jika tidak tersedia evidence literal yang memadai:
JANGAN memaksa item menjadi FACT.
Gunakan INTERPRETATION, ASSUMPTION, atau UNRESOLVED sesuai epistemic status yang sebenarnya.

--------------------------------------------------
INTERPRETATION RULE
--------------------------------------------------
Paraphrase atau reasoning diperbolehkan pada INTERPRETATION.
Namun pisahkan dengan jelas:
evidence dari user vs makna yang kamu simpulkan.
Jangan memasukkan hasil reasoning kembali sebagai FACT.

--------------------------------------------------
ASSUMPTION RULE
--------------------------------------------------
ASSUMPTION harus tetap diberi label ASSUMPTION.
Jangan mengubah ASSUMPTION menjadi FACT hanya karena asumsi tersebut masuk akal atau lazim dalam domain.

--------------------------------------------------
UNRESOLVED RULE
--------------------------------------------------
Jika requirement belum menentukan sesuatu:
Tandai sebagai UNRESOLVED.
Jangan mengarang nilai, field, endpoint, entity, behavior, storage, atau detail implementasi untuk menghilangkan ketidakpastian.

--------------------------------------------------
CONSTRUCTIBILITY RULE
--------------------------------------------------
CONSTRUCTIBILITY tidak berarti "isi semua bagian yang kosong".
Tujuan V0 adalah membuat requirement terstruktur dan constructible sejauh evidence memungkinkan.
Jika informasi penting belum tersedia:
- constructibility dapat tetap PARTIALLY_WORKABLE
- informasi yang belum diketahui harus dipertahankan sebagai UNRESOLVED dalam blocking_gaps atau unknown_fields.
Jangan mengorbankan epistemic correctness demi WORKABLE.

--------------------------------------------------
TEMPLATE SAFETY
--------------------------------------------------
Semua teks yang digunakan sebagai contoh format hanyalah contoh.
JANGAN pernah menyalin placeholder/example sebagai isi field.
Contoh yang SALAH:
basis = "Kutipan langsung dari task"
basis = "Deskripsi fakta"
basis = "Deskripsi requirement"
kecuali teks tersebut memang benar-benar terdapat pada user task.
Jika membutuhkan basis FACT, ambil evidence aktual dari user task.

--------------------------------------------------
NO DOWNSTREAM KNOWLEDGE
--------------------------------------------------
Jangan menggunakan:
- Frozen Oracle
- test cases
- expected API
- scaffold
- contract
- implementation
- vocabulary dari downstream
untuk melengkapi atau mengubah interpretation user requirement.
V0 harus tetap independent terhadap Oracle.

--------------------------------------------------
CONTRASTIVE EXAMPLE
--------------------------------------------------
Contoh NON-DOMAIN-SPECIFIC untuk menjelaskan perbedaan epistemik:

USER TASK:
"Bangun widget kartu metrik modern responsif Flutter dengan Material Design 3 dan Riverpod state."

BENAR:
- FACT:
  * "Flutter"
  * "Material Design 3"
  * "Riverpod state"
- INTERPRETATION:
  * widget tersebut merupakan komponen UI berbentuk kartu metrik
- UNRESOLVED:
  * nama metric
  * field metric
  * sumber data
  * nilai default
  * entity bisnis
  * backend/API

SALAH:
- FACT:
  * basis: "Kutipan langsung dari task"
  * basis: "Deskripsi fakta"
(Karena kedua string tersebut bukan kutipan aktual dari user).

PENTING:
Contoh di atas menjelaskan epistemic classification.
Contoh tersebut BUKAN template output yang harus disalin.

--------------------------------------------------
CONSTRAINT UTAMA & PRIORITAS
--------------------------------------------------
Gunakan aturan berikut sebagai prioritas:
1. Faithfulness terhadap user requirement.
2. Epistemic correctness.
3. Preservation of uncertainty.
4. Constructibility.
5. Detail elaboration.

Jika terjadi konflik:
Jangan mengarang detail hanya untuk membuat output terlihat lebih lengkap.
Lebih baik menghasilkan UNRESOLVED yang benar daripada FACT yang tidak memiliki evidence.
"Interpretation ≠ invention."
"Constructibility ≠ permission to hallucinate."

--------------------------------------------------
FORMAT OUTPUT WAJIB
--------------------------------------------------
Tuliskan HANYA JSON kanonikal di dalam blok penanda berikut tanpa teks pengantar atau penutup:

=== V0 REQUIREMENT MODEL JSON ===
{
  "metadata": {
    "source_text": "...",
    "detected_language": "python|dart",
    "detected_archetype": "REST_API|CLI_TOOL|FLUTTER_WIDGET|ALGORITHM|DATA_PIPELINE|UNKNOWN"
  },
  "epistemic_ledger": [
    {
      "id": "FACT-01",
      "category": "FUNCTIONAL|DATA|INTERACTION|CONSTRAINT|BEHAVIORAL",
      "epistemic_status": "FACT",
      "statement": "Teks pernyataan fakta menggunakan kata dari task",
      "basis": "Kutipan kata/frasa persis dari task",
      "confidence": 1.0
    },
    {
      "id": "INT-01",
      "category": "FUNCTIONAL|DATA|INTERACTION|CONSTRAINT|BEHAVIORAL",
      "epistemic_status": "INTERPRETATION",
      "statement": "Makna hasil penalaran dari kebutuhan",
      "basis": "Alasan logis mengapa interpretasi ini diturunkan",
      "confidence": 0.9
    }
  ],
  "application_requirement_model": {
    "functional_requirements": ["..."],
    "data_requirements": [
      {
        "entity_name": "...",
        "known_fields": ["..."],
        "unknown_fields": ["..."],
        "notes": "..."
      }
    ],
    "interaction_requirements": ["..."],
    "behavioral_requirements": ["..."],
    "constraints": ["..."]
  },
  "constructibility": {
    "status": "WORKABLE|PARTIALLY_WORKABLE|BLOCKED",
    "rationale": "Penjelasan mengapa status ini dipilih...",
    "blocking_gaps": [],
    "minimal_viable_interpretation": "Ringkasan interpretasi minimal..."
  }
}
=== END V0 REQUIREMENT MODEL JSON ===
"""

# Aktifkan versi terarah epistemik untuk eksperimen treatment
V0_SYSTEM_PROMPT = V0_SYSTEM_PROMPT_EPISTEMIC_DIRECTED_V1


def extract_v0_json_block(text: str) -> Optional[str]:
    """Mengekstrak blok JSON dari pembatas khusus atau blok kurung kurawal terbesar."""
    pattern = r"===\s*V0 REQUIREMENT MODEL JSON\s*===\s*(\{.*?\})\s*===\s*END V0 REQUIREMENT MODEL JSON\s*==="
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Fallback: cari blok JSON di dalam markdown backticks
    pattern_md = r"```(?:json)?\s*(\{.*?\})\s*```"
    match_md = re.search(pattern_md, text, re.DOTALL)
    if match_md:
        return match_md.group(1).strip()

    # Fallback: cari kurung kurawal pertama dan terakhir
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return text[first_brace:last_brace + 1].strip()

    return None


def create_defensive_v0_model(user_task: str, target_lang: str, reason: str) -> V0RequirementOutput:
    """Fallback deterministik jika LLM menghasilkan JSON yang tidak dapat diparsing."""
    task_clean = (user_task or "").strip()
    task_lower = task_clean.lower()

    # Deteksi archetype sederhana
    if any(k in task_lower for k in ["api", "rest", "fastapi", "endpoint", "crud"]):
        arch = DetectedArchetype.REST_API
    elif any(k in task_lower for k in ["cli", "kalkulator", "terminal", "command"]):
        arch = DetectedArchetype.CLI_TOOL
    elif any(k in task_lower for k in ["widget", "flutter", "dart", "card"]):
        arch = DetectedArchetype.FLUTTER_WIDGET
    elif any(k in task_lower for k in ["pipeline", "etl"]):
        arch = DetectedArchetype.DATA_PIPELINE
    else:
        arch = DetectedArchetype.ALGORITHM

    is_empty = len(task_clean) == 0
    is_contradictory = ("read-only" in task_lower and any(k in task_lower for k in ["crud", "delete", "post", "create"]))

    ledger = []
    if not is_empty:
        ledger.append(EpistemicItem(
            id="FACT-01",
            category=RequirementCategory.FUNCTIONAL,
            epistemic_status=EpistemicStatus.FACT,
            statement=task_clean[:150],
            basis=task_clean[:80],
            confidence=1.0
        ))
        ledger.append(EpistemicItem(
            id="INT-01",
            category=RequirementCategory.CONSTRAINT,
            epistemic_status=EpistemicStatus.INTERPRETATION,
            statement=f"Target platform ekosistem {target_lang}",
            basis=f"Platform konfigurasi target_language={target_lang}",
            confidence=0.9
        ))

    if is_contradictory:
        constructibility = ConstructibilityAssessment(
            status=ConstructibilityStatus.BLOCKED,
            rationale="Permintaan mengandung kontradiksi internal yang tidak dapat diselesaikan otomatis.",
            blocking_gaps=["Kontradiksi antara kebutuhan read-only dan operasi modifikasi/CRUD."],
            minimal_viable_interpretation="Klarifikasi kebutuhan pengguna."
        )
    elif is_empty:
        constructibility = ConstructibilityAssessment(
            status=ConstructibilityStatus.BLOCKED,
            rationale="Deskripsi tugas pengguna kosong.",
            blocking_gaps=["Deskripsi kebutuhan awal tidak diberikan."],
            minimal_viable_interpretation="Menunggu instruksi pengguna."
        )
    else:
        constructibility = ConstructibilityAssessment(
            status=ConstructibilityStatus.WORKABLE,
            rationale=f"Model kebutuhan minimal dibentuk secara defensif ({reason}).",
            blocking_gaps=[],
            minimal_viable_interpretation=f"Implementasikan solusi minimal untuk: {task_clean[:80]}"
        )

    return V0RequirementOutput(
        metadata=V0Metadata(
            source_text=task_clean,
            detected_language=target_lang,
            detected_archetype=arch
        ),
        epistemic_ledger=ledger,
        application_requirement_model=ApplicationRequirementModel(
            functional_requirements=[task_clean] if not is_empty else [],
            data_requirements=[],
            interaction_requirements=[f"Interaksi standar untuk arketipe {arch.value}"] if not is_empty else [],
            behavioral_requirements=["Sistem harus terkompilasi bebas error dan lolos validasi tipe."] if not is_empty else [],
            constraints=[f"Target bahasa: {target_lang}"]
        ),
        constructibility=constructibility
    )


def v0_agent(state: SquadState) -> Dict[str, Any]:
    """
    Node produser V0: Mengubah instruksi pengguna mentah menjadi Structured Application Requirement Model.
    """
    user_task = (state.get("task") or "").strip()
    target_lang = (state.get("target_language") or "python").strip().lower()

    repair_counts = state.get("repair_attempt_counts") or {}
    repair_count = repair_counts.get("v0", 0)
    v0_feedback = state.get("v0_feedback") or ""

    repair_instruction = ""
    if repair_count > 0 and v0_feedback:
        repair_instruction = f"""
PERINGATAN PERBAIKAN (Percobaan Perbaikan V0 #{repair_count}):
Model kebutuhan sebelumnya ditolak oleh V0 Deterministic Validator dengan temuan:
{v0_feedback}

Instruksi Perbaikan Wajib:
1. Perbaiki seluruh pelanggaran skema atau inkonsistensi epistemik di atas.
2. Jika ada fakta yang ditolak karena tidak ditemukan di teks asli, ganti statusnya menjadi INTERPRETATION atau ASSUMPTION dengan basis yang valid.
3. Pastikan keunikan ID dan konsistensi status konstruktibilitas (WORKABLE harus memiliki blocking_gaps kosong).
4. Tetap patuhi pembatas JSON: === V0 REQUIREMENT MODEL JSON ===.
"""

    prompt = f"""Target Bahasa / Ekosistem: {target_lang.upper()}
Deskripsi Tugas Pengguna:
\"\"\"{user_task}\"\"\"
{repair_instruction}
Bentuklah Structured Application Requirement Model lengkap dengan Epistemic Ledger dan Constructibility Assessment dalam format JSON kanonikal di dalam blok penanda yang ditentukan."""

    llm = get_llm(role="pm", provider=state.get("provider"))
    messages = [
        SystemMessage(content=V0_SYSTEM_PROMPT),
        HumanMessage(content=prompt)
    ]

    try:
        response = llm.invoke(messages)
        response_text = response.content if hasattr(response, "content") else str(response)
    except Exception as exc:
        response_text = ""
        # Log error via tracer if available
        tracer = get_tracer(state.get("run_id"))
        if tracer:
            tracer.log_event(
                stage="v0_requirement_interpretation",
                event_type="llm_invocation_error",
                iteration=repair_count,
                data={"error": str(exc)}
            )

    # Parsing JSON dari respons LLM
    json_str = extract_v0_json_block(response_text)
    v0_model: Optional[V0RequirementOutput] = None
    parse_error_msg = None

    if json_str:
        try:
            v0_model = parse_v0_output(json_str)
        except Exception as err:
            parse_error_msg = f"Gagal mem-parsing schema V0: {err}"
    else:
        parse_error_msg = "Blok JSON V0 tidak ditemukan dalam respons LLM."

    # Jika parsing gagal dan bukan dalam mode mock/test, buat model defensif
    if v0_model is None:
        v0_model = create_defensive_v0_model(user_task, target_lang, reason=parse_error_msg or "Fallback defensif")

    v0_dict = v0_model.model_dump()

    # Observability via tracer
    tracer = get_tracer(state.get("run_id"))
    if tracer:
        tracer.log_event(
            stage="v0_requirement_interpretation",
            event_type="v0_model_produced",
            iteration=repair_count,
            data={
                "archetype": v0_dict.get("metadata", {}).get("detected_archetype"),
                "constructibility": v0_dict.get("constructibility", {}).get("status"),
                "ledger_count": len(v0_dict.get("epistemic_ledger", [])),
                "repair_attempt": repair_count,
                "had_parse_error": parse_error_msg is not None
            }
        )

    repair_str = f" [Repair #{repair_count}]" if repair_count > 0 else ""
    status_str = v0_dict.get("constructibility", {}).get("status", "UNKNOWN")
    new_log = f"[V0 Requirement Interpreter]{repair_str}: Structured Requirement Model berhasil dirumuskan (Status: {status_str}, Ledger: {len(v0_dict.get('epistemic_ledger', []))} butir)."

    logs = list(state.get("logs") or [])
    logs.append(new_log)

    return {
        "v0_requirement_model": v0_dict,
        "status": "v0_done",
        "logs": logs
    }
