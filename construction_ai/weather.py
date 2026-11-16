"""Milestone 5 / Activity 5.3: Weather advisory (Open-Meteo, no API key needed)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import requests

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT = 15


class WeatherError(RuntimeError):
    pass


@dataclass(frozen=True)
class DayForecast:
    day: date
    temp_max_c: float
    temp_min_c: float
    rain_mm: float
    rain_prob_pct: float
    wind_max_kmh: float


@dataclass(frozen=True)
class Advisory:
    level: str  # ok / caution / stop
    messages: list[str]


def geocode(city: str) -> tuple[float, float, str]:
    try:
        r = requests.get(GEOCODE_URL, params={"name": city, "count": 1}, timeout=TIMEOUT)
        r.raise_for_status()
        results = r.json().get("results") or []
    except requests.RequestException as exc:
        raise WeatherError(f"Could not reach geocoding service: {exc}") from exc
    if not results:
        raise WeatherError(f"City '{city}' not found.")
    top = results[0]
    label = ", ".join(p for p in (top.get("name"), top.get("admin1"), top.get("country")) if p)
    return top["latitude"], top["longitude"], label


def fetch_forecast(lat: float, lon: float, days: int = 7) -> list[DayForecast]:
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,"
                 "precipitation_probability_max,wind_speed_10m_max",
        "timezone": "auto",
        "forecast_days": days,
    }
    try:
        r = requests.get(FORECAST_URL, params=params, timeout=TIMEOUT)
        r.raise_for_status()
        d = r.json()["daily"]
    except (requests.RequestException, KeyError) as exc:
        raise WeatherError(f"Could not fetch forecast: {exc}") from exc
    out = []
    for i, day in enumerate(d["time"]):
        out.append(DayForecast(
            day=date.fromisoformat(day),
            temp_max_c=d["temperature_2m_max"][i] or 0.0,
            temp_min_c=d["temperature_2m_min"][i] or 0.0,
            rain_mm=d["precipitation_sum"][i] or 0.0,
            rain_prob_pct=d["precipitation_probability_max"][i] or 0.0,
            wind_max_kmh=d["wind_speed_10m_max"][i] or 0.0,
        ))
    return out


def assess_day(f: DayForecast) -> Advisory:
    """Rule-based site advisory (thresholds follow common site practice)."""
    msgs: list[str] = []
    level = "ok"

    def raise_to(new: str):
        nonlocal level
        order = {"ok": 0, "caution": 1, "stop": 2}
        if order[new] > order[level]:
            level = new

    if f.rain_mm >= 10 or f.rain_prob_pct >= 80:
        raise_to("stop")
        msgs.append("Heavy rain likely: postpone concreting, plastering and external painting; cover cement and steel; pump out excavations.")
    elif f.rain_mm >= 2.5 or f.rain_prob_pct >= 50:
        raise_to("caution")
        msgs.append("Rain possible: keep tarpaulins ready, avoid fresh concrete pours unless covered, secure loose materials.")

    if f.wind_max_kmh >= 50:
        raise_to("stop")
        msgs.append("Very strong winds: suspend crane lifts, work at height and sheeting/formwork handling.")
    elif f.wind_max_kmh >= 30:
        raise_to("caution")
        msgs.append("Strong winds: restrict lifting operations, tie down scaffolding sheets and loose material.")

    if f.temp_max_c >= 40:
        raise_to("caution")
        msgs.append("Extreme heat: shift heavy work to early morning, provide water and shade, increase curing frequency, watch for rapid concrete setting.")
    elif f.temp_max_c >= 35:
        msgs.append("Hot day: cure concrete at least 3 times daily and keep workers hydrated.")

    if f.temp_min_c <= 5:
        raise_to("caution")
        msgs.append("Cold: protect fresh concrete from low temperatures and delay pours if the temperature drops further.")

    if not msgs:
        msgs.append("Conditions are favourable for normal site work.")
    return Advisory(level, msgs)


def rain_stop_dates(forecast: list[DayForecast]) -> set[date]:
    """Dates where work should be treated as blocked in the schedule."""
    return {f.day for f in forecast if assess_day(f).level == "stop"}
