"""AI layer tests use a fake Gemini client, so no network or API key is needed."""
import json
from types import SimpleNamespace

import pytest

from construction_ai.assistant import ConstructionChatbot, generate_daily_briefing
from construction_ai.config import Settings
from construction_ai.gemini_client import GeminiClient, GeminiError
from construction_ai.image_utils import ImageError, load_image
from construction_ai.safety import analyze_safety
from construction_ai.schemas import SafetyReport

SETTINGS = Settings(api_key="x", use_vertex=False, project=None, location="us", model="m")
GOOD = {"overall_risk": "high", "workers_detected": 2, "ppe_summary": "No helmets",
        "violations": [{"category": "ppe", "description": "No helmet", "severity": "high",
                        "location_hint": "left", "corrective_action": "Issue helmets"}],
        "compliant_observations": [], "confidence": 1.7}


class FakeModels:
    def __init__(self, replies):
        self.replies, self.calls = list(replies), 0

    def generate_content(self, **kw):
        self.calls += 1
        return SimpleNamespace(parsed=None, text=self.replies.pop(0))


def make(replies):
    fake = SimpleNamespace(models=FakeModels(replies))
    return GeminiClient(SETTINGS, client=fake), fake


def test_valid_json_is_parsed_and_confidence_clamped():
    c, _ = make([json.dumps(GOOD)])
    rep = analyze_safety(c, [])
    assert isinstance(rep, SafetyReport) and rep.confidence == 1.0


def test_invalid_then_valid_retries():
    c, fake = make(["not json", json.dumps(GOOD)])
    assert c.generate_json("p", SafetyReport).overall_risk == "high"
    assert fake.models.calls == 2


def test_gives_up_after_retries():
    c, _ = make(["bad"] * 3)
    with pytest.raises(GeminiError):
        c.generate_json("p", SafetyReport)


def test_unconfigured_client_raises():
    c = GeminiClient(Settings(None, False, None, "us", "m"))
    with pytest.raises(GeminiError):
        c.generate_json("p", SafetyReport)


def test_chatbot_keeps_bounded_history():
    class C:
        def chat(self, history, message, images=(), system=None):
            return "ok"
    bot = ConstructionChatbot(C(), max_turns=2)
    for i in range(5):
        bot.ask(f"q{i}")
    assert len(bot.history) == 4 and bot.history[-2] == ("user", "q4")


def test_daily_briefing_schema():
    reply = json.dumps({"headline": "h", "priorities": ["a"], "safety_focus": [], "material_and_equipment_checks": [],
                        "manpower_notes": "n", "weather_considerations": [], "risks": [], "end_of_day_checklist": []})
    c, _ = make([reply])
    assert generate_daily_briefing(c, "log").headline == "h"


def test_image_validation():
    with pytest.raises(ImageError):
        load_image(b"not an image", "x.png")
