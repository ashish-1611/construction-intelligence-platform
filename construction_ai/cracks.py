"""Milestone 2 / Activity 2.2: Crack detection logic.

Two layers:
1. A transparent, deterministic *screening heuristic* (edge + dark-line density) that works offline.
2. A Gemini vision classification that returns a schema-validated CrackReport.

The heuristic is a quick triage signal, not a structural assessment.
"""
from __future__ import annotations

import io
from dataclasses import dataclass

import numpy as np
from PIL import Image

from .gemini_client import GeminiClient
from .image_utils import ImageInput
from .schemas import CrackReport

SYSTEM = (
    "You are a structural engineer inspecting concrete/masonry defects from photos, using IS 456 "
    "and IS 15988 guidance. Classify the crack pattern (hairline, shrinkage, settlement, diagonal "
    "shear, vertical, horizontal, map cracking). Estimate width only as a rough range and say that a "
    "crack gauge is needed to confirm. Flag requires_structural_engineer=true for any diagonal/shear, "
    "wide (>0.3 mm), horizontal-in-column/wall, or progressive-looking cracks. If no crack is visible, "
    "set crack_detected=false and crack_type='none'."
)


@dataclass(frozen=True)
class HeuristicResult:
    edge_density: float   # fraction of strong-gradient pixels
    dark_ratio: float     # fraction of unusually dark pixels
    score: float          # 0..1 crack-likelihood screening score
    level: str            # low / medium / high


def heuristic_crack_score(raw: bytes) -> HeuristicResult:
    """Screen an image for crack-like structure (thin, dark, high-gradient lines)."""
    gray = np.asarray(Image.open(io.BytesIO(raw)).convert("L").resize((512, 512)), dtype=np.float32)
    gx = np.abs(np.diff(gray, axis=1))[:-1, :]
    gy = np.abs(np.diff(gray, axis=0))[:, :-1]
    mag = np.hypot(gx, gy)
    thr = float(mag.mean() + 2.0 * mag.std())
    edge_density = float((mag > thr).mean()) if mag.std() > 0 else 0.0

    sd = float(gray.std())
    dark_ratio = float((gray < gray.mean() - 1.5 * sd).mean()) if sd > 0 else 0.0

    score = float(min(1.0, edge_density * 12.0 + dark_ratio * 6.0))
    level = "low" if score < 0.15 else "medium" if score < 0.45 else "high"
    return HeuristicResult(edge_density, dark_ratio, score, level)


def classify_cracks(client: GeminiClient, image: ImageInput, context: str = "") -> CrackReport:
    prompt = "Analyse this image for cracks and return the crack report."
    if context.strip():
        prompt += f"\nContext: {context}"
    return client.generate_json(prompt, CrackReport, images=[image], system=SYSTEM)
