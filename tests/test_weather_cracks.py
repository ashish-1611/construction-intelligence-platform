import io
from datetime import date

import numpy as np
from PIL import Image

from construction_ai.cracks import heuristic_crack_score
from construction_ai.weather import DayForecast, assess_day, rain_stop_dates


def fc(**kw):
    base = dict(day=date(2026, 7, 1), temp_max_c=30, temp_min_c=22, rain_mm=0, rain_prob_pct=0, wind_max_kmh=10)
    base.update(kw)
    return DayForecast(**base)


def test_weather_levels():
    assert assess_day(fc()).level == "ok"
    assert assess_day(fc(rain_mm=4)).level == "caution"
    assert assess_day(fc(rain_mm=20)).level == "stop"
    assert assess_day(fc(wind_max_kmh=55)).level == "stop"
    assert assess_day(fc(temp_max_c=42)).level == "caution"


def test_rain_stop_dates():
    assert rain_stop_dates([fc(), fc(day=date(2026, 7, 2), rain_mm=30)]) == {date(2026, 7, 2)}


def _png(arr):
    buf = io.BytesIO()
    Image.fromarray(arr.astype("uint8")).save(buf, "PNG")
    return buf.getvalue()


def test_crack_heuristic_flags_dark_line_over_blank_wall():
    wall = np.full((256, 256), 200)
    cracked = wall.copy()
    for i in range(256):
        cracked[i, min(255, 60 + i // 2)] = 10
        cracked[i, min(255, 61 + i // 2)] = 10
    assert heuristic_crack_score(_png(wall)).score == 0
    assert heuristic_crack_score(_png(cracked)).score > 0.15
