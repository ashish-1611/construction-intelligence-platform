"""Milestone 3 / Activity 3.2: Cost estimation in Indian Rupees (INR)."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .materials import DATA_DIR, MaterialLine


def format_inr(amount: float) -> str:
    """Format using the Indian digit grouping: 1234567 -> ₹12,34,567."""
    n = round(amount)
    sign = "-" if n < 0 else ""
    s = str(abs(n))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        groups: list[str] = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        s = ",".join(groups + [tail])
    return f"{sign}₹{s}"


@dataclass(frozen=True)
class CostLine:
    item: str
    quantity: float
    unit: str
    rate: float
    amount: float


@dataclass(frozen=True)
class CostBreakdown:
    material_lines: list[CostLine]
    material_total: float
    labour: float
    finishing: float
    overhead: float
    contingency: float
    subtotal: float
    gst: float
    grand_total: float
    per_sqft: float


def load_rates(path: Path | None = None) -> dict:
    return json.loads((path or DATA_DIR / "rates_inr.json").read_text(encoding="utf-8"))


def estimate_cost(
    materials: list[MaterialLine],
    built_up_sqft: float,
    quality: str = "standard",
    include_finishing: bool = False,
    rates: dict | None = None,
) -> CostBreakdown:
    rates = rates or load_rates()
    mat_lines: list[CostLine] = []
    for m in materials:
        if m.key not in rates["material_rates"]:
            raise KeyError(f"No rate defined for material '{m.key}'")
        rate = rates["material_rates"][m.key]
        mat_lines.append(CostLine(m.name, m.quantity, m.unit, rate, m.quantity * rate))

    material_total = sum(l.amount for l in mat_lines)
    labour = built_up_sqft * rates["labour_per_sqft"][quality]
    finishing = built_up_sqft * rates["finishing_per_sqft"][quality] if include_finishing else 0.0
    direct = material_total + labour + finishing
    overhead = direct * rates["overhead_pct"] / 100
    contingency = direct * rates["contingency_pct"] / 100
    subtotal = direct + overhead + contingency
    gst = subtotal * rates["gst_pct"] / 100
    grand = subtotal + gst
    return CostBreakdown(
        mat_lines, material_total, labour, finishing, overhead, contingency,
        subtotal, gst, grand, grand / built_up_sqft,
    )
