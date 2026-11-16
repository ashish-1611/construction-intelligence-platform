"""Milestone 3 / Activity 3.1: Material estimation (deterministic, auditable)."""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
QUALITIES = ("economy", "standard", "premium")


@dataclass(frozen=True)
class MaterialLine:
    key: str
    name: str
    unit: str
    quantity: int


def load_norms(path: Path | None = None) -> dict:
    return json.loads((path or DATA_DIR / "material_norms.json").read_text(encoding="utf-8"))


def estimate_materials(
    built_up_sqft: float,
    floors: int = 1,
    quality: str = "standard",
    wastage_pct: float = 5.0,
    norms: dict | None = None,
) -> list[MaterialLine]:
    """Estimate bulk material quantities from total built-up area (all floors combined)."""
    if built_up_sqft <= 0:
        raise ValueError("built_up_sqft must be positive")
    if floors < 1:
        raise ValueError("floors must be >= 1")
    if quality not in QUALITIES:
        raise ValueError(f"quality must be one of {QUALITIES}")
    if wastage_pct < 0:
        raise ValueError("wastage_pct cannot be negative")

    norms = norms or load_norms()
    q_mult = norms["quality_multiplier"][quality]
    lines: list[MaterialLine] = []
    for key, spec in norms["per_sqft"].items():
        uplift = 1 + norms["extra_floor_uplift"].get(key, 0.0) * (floors - 1)
        qty = built_up_sqft * spec["qty"] * q_mult * uplift * (1 + wastage_pct / 100)
        lines.append(MaterialLine(key, spec["name"], spec["unit"], math.ceil(qty)))
    return lines
