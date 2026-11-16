import pytest

from construction_ai.costing import estimate_cost, format_inr
from construction_ai.materials import estimate_materials


def test_material_quantities_standard():
    m = {l.key: l.quantity for l in estimate_materials(1000, 1, "standard", 0)}
    assert m["cement"] == 400 and m["steel"] == 4000 and m["bricks"] == 8000


def test_wastage_quality_and_floors_increase_quantities():
    base = {l.key: l.quantity for l in estimate_materials(1000, 1, "standard", 0)}
    waste = {l.key: l.quantity for l in estimate_materials(1000, 1, "standard", 10)}
    prem = {l.key: l.quantity for l in estimate_materials(1000, 1, "premium", 0)}
    multi = {l.key: l.quantity for l in estimate_materials(1000, 3, "standard", 0)}
    assert waste["cement"] > base["cement"]
    assert prem["steel"] > base["steel"]
    assert multi["steel"] > base["steel"]


@pytest.mark.parametrize("kwargs", [dict(built_up_sqft=0), dict(built_up_sqft=100, floors=0),
                                    dict(built_up_sqft=100, quality="gold")])
def test_invalid_inputs(kwargs):
    with pytest.raises(ValueError):
        estimate_materials(**kwargs)


@pytest.mark.parametrize("n,expected", [(0, "₹0"), (999, "₹999"), (1000, "₹1,000"),
                                        (123456, "₹1,23,456"), (12345678, "₹1,23,45,678"), (-5000, "-₹5,000")])
def test_format_inr(n, expected):
    assert format_inr(n) == expected


def test_cost_totals_are_consistent():
    mats = estimate_materials(1500, 2, "standard")
    c = estimate_cost(mats, 1500, "standard", include_finishing=True)
    assert c.subtotal == pytest.approx(c.material_total + c.labour + c.finishing + c.overhead + c.contingency)
    assert c.grand_total == pytest.approx(c.subtotal + c.gst)
    assert c.per_sqft == pytest.approx(c.grand_total / 1500)
    assert estimate_cost(mats, 1500).grand_total < c.grand_total
