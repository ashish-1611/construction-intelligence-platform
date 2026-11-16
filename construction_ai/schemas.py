"""Pydantic schemas used for JSON-schema-enforced Gemini output (Activity 4.2)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, field_validator

Severity = Literal["low", "medium", "high", "critical"]


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


class Violation(BaseModel):
    category: Literal[
        "ppe", "fall_protection", "scaffolding", "housekeeping",
        "electrical", "excavation", "machinery", "fire", "other",
    ]
    description: str
    severity: Severity
    location_hint: str
    corrective_action: str


class SafetyReport(BaseModel):
    overall_risk: Severity
    workers_detected: int
    ppe_summary: str
    violations: list[Violation]
    compliant_observations: list[str]
    confidence: float

    _clamp = field_validator("confidence")(_clamp01)


class CrackReport(BaseModel):
    crack_detected: bool
    crack_type: Literal[
        "none", "hairline", "shrinkage", "settlement", "diagonal",
        "vertical", "horizontal", "map_cracking", "structural", "other",
    ]
    severity: Severity
    estimated_width_mm: str
    affected_element: str
    likely_causes: list[str]
    recommended_action: str
    requires_structural_engineer: bool
    confidence: float

    _clamp = field_validator("confidence")(_clamp01)


class SiteInsight(BaseModel):
    construction_stage: str
    summary: str
    observations: list[str]
    risks: list[str]
    recommended_actions: list[str]
    assumptions: list[str]
    confidence: float

    _clamp = field_validator("confidence")(_clamp01)


class PlanExtraction(BaseModel):
    """Details read from a floor plan / drawing. Zero means 'not found'."""
    built_up_area_sqft: float
    floors: int
    rooms: list[str]
    structural_system: str
    notes: str
    confidence: float

    _clamp = field_validator("confidence")(_clamp01)


class DailyBriefing(BaseModel):
    headline: str
    priorities: list[str]
    safety_focus: list[str]
    material_and_equipment_checks: list[str]
    manpower_notes: str
    weather_considerations: list[str]
    risks: list[str]
    end_of_day_checklist: list[str]
