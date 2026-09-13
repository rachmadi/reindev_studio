# -*- coding: utf-8 -*-
"""
V0 Canonical Schema & Structured Application Requirement Model
ReinDev Studio — v2.3 (Upstream Requirement Interpretation & Constructibility Gate)

Mendefinisikan tipe data terstruktur berbasis Pydantic v2 untuk luaran V0:
1. Metadata & Archetype Detection
2. Epistemic Ledger (FACT, INTERPRETATION, ASSUMPTION, UNRESOLVED, AMBIGUITY)
3. Application Requirement Model (Functional, Data, Interaction, Behavioral, Constraints)
4. Constructibility Assessment (WORKABLE, PARTIALLY_WORKABLE, BLOCKED)
5. Kanonikalisasi JSON deterministik (RFC 8785 aligned)
"""

from __future__ import annotations

import json
from enum import Enum
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


# ==============================================================================
# 1. Enums
# ==============================================================================

class EpistemicStatus(str, Enum):
    FACT = "FACT"
    INTERPRETATION = "INTERPRETATION"
    ASSUMPTION = "ASSUMPTION"
    UNRESOLVED = "UNRESOLVED"
    AMBIGUITY = "AMBIGUITY"


class RequirementCategory(str, Enum):
    FUNCTIONAL = "FUNCTIONAL"
    DATA = "DATA"
    INTERACTION = "INTERACTION"
    CONSTRAINT = "CONSTRAINT"
    BEHAVIORAL = "BEHAVIORAL"


class ConstructibilityStatus(str, Enum):
    WORKABLE = "WORKABLE"
    PARTIALLY_WORKABLE = "PARTIALLY_WORKABLE"
    BLOCKED = "BLOCKED"


class DetectedArchetype(str, Enum):
    REST_API = "REST_API"
    CLI_TOOL = "CLI_TOOL"
    FLUTTER_WIDGET = "FLUTTER_WIDGET"
    ALGORITHM = "ALGORITHM"
    DATA_PIPELINE = "DATA_PIPELINE"
    UNKNOWN = "UNKNOWN"


# ==============================================================================
# 2. Pydantic Models
# ==============================================================================

class EpistemicItem(BaseModel):
    """Representasi butir kebutuhan dengan status epistemik eksplisit."""
    id: str = Field(..., description="ID unik misal FACT-01, INT-01, ASM-01, UNR-01, AMB-01")
    category: RequirementCategory
    epistemic_status: EpistemicStatus
    statement: str = Field(..., min_length=3, description="Pernyataan butir kebutuhan")
    basis: str = Field(..., min_length=1, description="Kutipan teks pengguna atau alasan logis")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Tingkat keyakinan 0.0 - 1.0")


class DataEntityRequirement(BaseModel):
    """Kebutuhan entitas data dengan pemisahan field yang diketahui vs belum diketahui."""
    entity_name: str = Field(..., min_length=1)
    known_fields: List[str] = Field(default_factory=list)
    unknown_fields: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class ApplicationRequirementModel(BaseModel):
    """Model kebutuhan aplikasi terstruktur yang constructible untuk fase hilir."""
    functional_requirements: List[str] = Field(default_factory=list)
    data_requirements: List[DataEntityRequirement] = Field(default_factory=list)
    interaction_requirements: List[str] = Field(default_factory=list)
    behavioral_requirements: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)


class ConstructibilityAssessment(BaseModel):
    """Penilaian apakah requirement cukup kokoh untuk fase konstruksi hilir."""
    status: ConstructibilityStatus
    rationale: str = Field(..., min_length=5, description="Penjelasan rasional status konstruktibilitas")
    blocking_gaps: List[str] = Field(default_factory=list, description="Daftar kesenjangan yang memblokir")
    minimal_viable_interpretation: str = Field(default="", description="Interpretasi minimal yang memungkinkan konstruksi")

    @model_validator(mode="after")
    def validate_blocking_gaps_consistency(self) -> ConstructibilityAssessment:
        if self.status == ConstructibilityStatus.WORKABLE and len(self.blocking_gaps) > 0:
            raise ValueError("Status WORKABLE tidak boleh memiliki blocking_gaps.")
        if self.status == ConstructibilityStatus.BLOCKED and len(self.blocking_gaps) == 0:
            raise ValueError("Status BLOCKED wajib mencantumkan minimal satu blocking_gap.")
        return self


class V0Metadata(BaseModel):
    """Metadata proses requirement interpretation."""
    source_text: str = Field(..., description="Teks tugas mentah dari pengguna")
    detected_language: str = Field(default="python")
    detected_archetype: DetectedArchetype = Field(default=DetectedArchetype.UNKNOWN)


class V0RequirementOutput(BaseModel):
    """Dokumen kanonikal luaran V0."""
    metadata: V0Metadata
    epistemic_ledger: List[EpistemicItem] = Field(default_factory=list)
    application_requirement_model: ApplicationRequirementModel = Field(default_factory=ApplicationRequirementModel)
    constructibility: ConstructibilityAssessment

    @model_validator(mode="after")
    def validate_id_uniqueness(self) -> V0RequirementOutput:
        seen_ids = set()
        for item in self.epistemic_ledger:
            if item.id in seen_ids:
                raise ValueError(f"ID duplikat terdeteksi pada epistemic_ledger: {item.id}")
            seen_ids.add(item.id)
        return self


# ==============================================================================
# 3. Serialization Helpers
# ==============================================================================

def to_canonical_json(output: V0RequirementOutput) -> str:
    """Mengubah V0RequirementOutput menjadi string JSON deterministik terurut."""
    return json.dumps(output.model_dump(), sort_keys=True, indent=2, ensure_ascii=False)


def parse_v0_output(raw_data: Any) -> V0RequirementOutput:
    """Mem-parsing data (string JSON atau dict) ke V0RequirementOutput."""
    if isinstance(raw_data, str):
        data_dict = json.loads(raw_data)
    elif isinstance(raw_data, dict):
        data_dict = raw_data
    else:
        raise TypeError(f"Tipe data tidak didukung untuk parsing V0: {type(raw_data)}")
    return V0RequirementOutput.model_validate(data_dict)
