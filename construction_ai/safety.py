"""Milestone 2 / Activity 2.1: Safety image analysis."""
from __future__ import annotations

from typing import Sequence

from .gemini_client import GeminiClient
from .image_utils import ImageInput
from .schemas import SafetyReport

SYSTEM = (
    "You are a certified construction safety officer familiar with Indian standards "
    "(BOCW Act, IS 3764 excavation safety, IS 4130 demolition, NBC 2016 Part 7). "
    "Judge ONLY what is visible. If something cannot be assessed from the photo, do not invent it; "
    "mention the limitation in ppe_summary. Be specific about where in the image each issue appears."
)

PROMPT = (
    "Inspect the construction site image(s) for safety compliance. Check helmets, "
    "high-visibility vests, footwear, harness/fall protection at height, scaffolding and "
    "edge protection, housekeeping, exposed wiring, excavation shoring, machinery exclusion "
    "zones and fire hazards. Return the safety report."
)


def analyze_safety(
    client: GeminiClient, images: Sequence[ImageInput], notes: str = ""
) -> SafetyReport:
    prompt = PROMPT + (f"\nSite notes from the engineer: {notes}" if notes.strip() else "")
    return client.generate_json(prompt, SafetyReport, images=images, system=SYSTEM)


SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def sort_violations(report: SafetyReport):
    """Most severe first, for display."""
    return sorted(report.violations, key=lambda v: -SEVERITY_ORDER[v.severity])
