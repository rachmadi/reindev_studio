"""
Context Integrity & Task Isolation Engine (Part 3 - Architectural Hardening v1)
ReinDev Studio

Menegakkan integritas konteks dan isolasi task pada pipeline perakitan konteks:
1. Cross-domain / Cross-task Contamination Protection:
   Mencegah artefak, kode, atau pola dari domain lain (mis. Flutter/Dart di Python REST API,
   atau FastAPI di CLI/Flutter) merembes ke prompt konteks aktif.
2. Rejected Artifact Authority Leakage Protection:
   Menjamin artefak dengan status REJECTED (mis. proposal kontrak yang gagal divalidasi)
   tidak pernah disajikan sebagai otoritas atau fakta kanonikal.
3. Draft Proposal as Frozen Fact Prevention:
   Mencegah draf proposal yang belum disegel (ALIGNED/DRAFT) disajikan sebagai kontrak FROZEN.
4. Stale Context / Dead Artifact Elimination:
   Mencegah artefak usang dari iterasi gagal sebelumnya yang tidak lagi relevan
   mengaburkan penalaran agen.
5. Epistemic Boundary Enforcement:
   Menyusun konteks bersih dengan batas otoritas eksplisit.
"""

import re
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class ContextItem:
    """Representasi atomik dari sebuah unit konteks dalam pipeline."""
    item_id: str
    item_type: str  # USER_INTENT, REQUIREMENT, ORACLE_FACT, CONTRACT, BLUEPRINT, SOURCE_CODE, TEST_EVIDENCE, PRESCRIPTION, ENVIRONMENT_FACT
    domain: str     # REST_API, CLI_TOOL, FLUTTER_WIDGET, DATA_PIPELINE, ALGORITHM, GENERIC
    phase: str      # V0, PM, ARCHITECT, DEVELOPER, EXECUTOR, REVIEWER
    content: str
    authority_status: str  # PROVEN, FROZEN, ORACLE, DRAFT, PROPOSED, REJECTED, RUNTIME, ENVIRONMENT
    provenance: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AuditResult:
    """Hasil audit integritas konteks."""
    is_clean: bool
    violations: List[str]
    filtered_items: List[ContextItem]
    rejected_items: List[Tuple[ContextItem, str]]  # (item, reason)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_clean": self.is_clean,
            "violations": self.violations,
            "filtered_items_count": len(self.filtered_items),
            "rejected_items_count": len(self.rejected_items),
            "rejected_details": [
                {"item_id": it.item_id, "reason": reason}
                for it, reason in self.rejected_items
            ]
        }


# Signatures khas per-domain untuk deteksi cross-domain leakage
DOMAIN_SIGNATURES: Dict[str, List[re.Pattern]] = {
    "FLUTTER_WIDGET": [
        re.compile(r"package:flutter", re.IGNORECASE),
        re.compile(r"\bWidgetTester\b"),
        re.compile(r"\bfind\.byType\b"),
        re.compile(r"\bBuildContext\b"),
        re.compile(r"\bStatelessWidget\b"),
        re.compile(r"\bStatefulWidget\b"),
        re.compile(r"\bMaterialApp\b"),
        re.compile(r"\bScaffold\b"),
    ],
    "REST_API": [
        re.compile(r"\bFastAPI\b"),
        re.compile(r"\bTestClient\b"),
        re.compile(r"client\.(get|post|put|delete|patch)\(", re.IGNORECASE),
        re.compile(r"@app\.(get|post|put|delete|patch)\(", re.IGNORECASE),
        re.compile(r"\bstatus_code\b"),
        re.compile(r"\bHTTPException\b"),
    ],
    "CLI_TOOL": [
        re.compile(r"\bArgumentParser\b"),
        re.compile(r"\bparse_args\b"),
        re.compile(r"\bsys\.argv\b"),
    ],
}


class ContextIntegrityAuditor:
    """
    Auditor deterministik untuk integritas konteks dan isolasi task.
    """

    @classmethod
    def audit_context(
        cls,
        items: List[ContextItem],
        target_domain: str,
        target_phase: str,
        state: Optional[Dict[str, Any]] = None
    ) -> AuditResult:
        """
        Mengaudit daftar ContextItem terhadap aturan integritas dan isolasi.
        """
        violations: List[str] = []
        filtered: List[ContextItem] = []
        rejected: List[Tuple[ContextItem, str]] = []

        norm_target_domain = (target_domain or "GENERIC").upper().strip()

        for item in items:
            item_viol: Optional[str] = None

            # 1. Aturan Otoritas Artefak REJECTED:
            # Artefak berstatus REJECTED dilarang disajikan sebagai fakta kanonikal/otoritatif
            if item.authority_status.upper() == "REJECTED":
                if item.authority_status in ("FROZEN", "PROVEN", "ORACLE"):
                    item_viol = (
                        f"CRITICAL: Item '{item.item_id}' memiliki status REJECTED tetapi "
                        f"mengklaim otoritas {item.authority_status}."
                    )
                else:
                    # Secara otomatis downgrade atau tolak jika disajikan sebagai requirement aktif
                    if item.item_type in ("REQUIREMENT", "CONTRACT", "BLUEPRINT"):
                        item_viol = (
                            f"ISOLATION: Item '{item.item_id}' berstatus REJECTED dan "
                            f"tidak boleh disajikan sebagai {item.item_type} aktif."
                        )

            # 2. Aturan DRAFT vs FROZEN:
            # Kontrak draf dilarang mengklaim status FROZEN atau ORACLE
            if not item_viol:
                if item.item_type == "CONTRACT" and item.authority_status.upper() in ("DRAFT", "PROPOSED", "ALIGNED"):
                    if "FROZEN" in item.content and "Status: FROZEN" in item.content:
                        item_viol = (
                            f"EPISTEMIC_VIOLATION: Item '{item.item_id}' adalah draf proposal "
                            f"namun mengklaim status 'FROZEN' dalam kontennya."
                        )

            # 3. Aturan Isolasi Cross-Domain:
            # Jika target_domain spesifik (bukan GENERIC), cek apakah konten item memuat pola domain yang bertentangan
            if not item_viol and norm_target_domain != "GENERIC":
                # Cek domain label item
                item_norm_domain = item.domain.upper().strip()
                if item_norm_domain not in ("GENERIC", "UNKNOWN", ""):
                    if item_norm_domain != norm_target_domain:
                        item_viol = (
                            f"CROSS_DOMAIN_CONTAMINATION: Item '{item.item_id}' berasal dari domain "
                            f"'{item_norm_domain}' padahal task aktif berdomain '{norm_target_domain}'."
                        )

                # Cek signature leakage konten
                if not item_viol:
                    for dom, sigs in DOMAIN_SIGNATURES.items():
                        if dom != norm_target_domain:
                            # Jika item bukan dari domain ini tapi mengandung pola kuat dari domain lain
                            leak_count = sum(1 for p in sigs if p.search(item.content))
                            if leak_count >= 2:
                                item_viol = (
                                    f"CROSS_DOMAIN_LEAKAGE: Konten item '{item.item_id}' memuat {leak_count} "
                                    f"pola khas domain '{dom}' yang tidak kompatibel dengan '{norm_target_domain}'."
                                )
                                break

            # 4. Evaluasi hasil pemeriksaan untuk item ini
            if item_viol:
                violations.append(item_viol)
                rejected.append((item, item_viol))
            else:
                filtered.append(item)

        is_clean = (len(violations) == 0)
        return AuditResult(
            is_clean=is_clean,
            violations=violations,
            filtered_items=filtered,
            rejected_items=rejected
        )

    @classmethod
    def audit_context_dict(
        cls,
        sections: Dict[str, str],
        target_domain: str,
        target_phase: str,
        state: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, str], List[str]]:
        """
        Helper untuk mengaudit dictionary sections (mis. dari context_hardening.py).
        Mengembalikan: (cleaned_sections, list_of_violations)
        """
        violations: List[str] = []
        cleaned: Dict[str, str] = {}
        norm_target_domain = (target_domain or "GENERIC").upper().strip()

        # Deteksi status kontrak dari state jika ada
        contract_status = ""
        if state and isinstance(state, dict):
            contract_status = (state.get("contract_status") or "").upper().strip()

        for sec_name, content in sections.items():
            sec_viol: Optional[str] = None

            # 1. Cek rejected contract leakage
            if "contract" in sec_name.lower():
                if contract_status == "REJECTED":
                    # Kontrak ditolak tidak boleh ditampilkan sebagai otoritatif
                    if "ORACLE_FACT" in content or "FROZEN" in content:
                        sec_viol = (
                            f"REJECTED_ARTIFACT_LEAKAGE: Section '{sec_name}' menyajikan kontrak REJECTED "
                            f"sebagai fakta otoritatif (ORACLE_FACT / FROZEN)."
                        )
                        # Netralkan section
                        content = (
                            "[REJECTED ARTIFACT — NON-AUTHORITATIVE]\n"
                            "Contract status: REJECTED.\n"
                            "This draft proposal failed pre-freeze verification and must NOT be used as acceptance ground truth."
                        )

            # 2. Cek cross-domain contamination dalam teks
            if norm_target_domain != "GENERIC":
                for dom, sigs in DOMAIN_SIGNATURES.items():
                    if dom != norm_target_domain:
                        matches = [p.pattern for p in sigs if p.search(content)]
                        if len(matches) >= 2:
                            sec_viol = (
                                f"CROSS_DOMAIN_CONTAMINATION: Section '{sec_name}' memuat pola domain '{dom}' "
                                f"({matches[:2]}) dalam task berdomain '{norm_target_domain}'."
                            )
                            # Bersihkan garis yang bocor atau berikan warning
                            cleaned_lines = []
                            for line in content.splitlines():
                                if any(p.search(line) for p in sigs):
                                    continue
                                cleaned_lines.append(line)
                            content = "\n".join(cleaned_lines)

            if sec_viol:
                violations.append(sec_viol)

            cleaned[sec_name] = content

        return cleaned, violations