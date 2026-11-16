"""Milestone 5: Construction chatbot (5.1) and daily site assistant (5.2)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from .gemini_client import GeminiClient
from .image_utils import ImageInput
from .schemas import DailyBriefing

CHAT_SYSTEM = (
    "You are an AI construction assistant for engineers and contractors in India. Answer practically "
    "and concisely, cite relevant Indian standards (IS 456, IS 800, IS 1786, NBC 2016) where helpful, "
    "give quantities in metric/Indian units and costs in INR. For structural, geotechnical or legal "
    "decisions, remind the user to confirm with a licensed engineer. If you are unsure, say so."
)

DAILY_SYSTEM = (
    "You are a site supervisor's assistant. Produce a short, actionable plan for TODAY only, based "
    "strictly on the information provided. Do not invent tasks, quantities or crew numbers."
)


@dataclass
class ConstructionChatbot:
    client: GeminiClient
    project_context: str = ""
    history: list[tuple[str, str]] = field(default_factory=list)
    max_turns: int = 20

    def _system(self) -> str:
        ctx = f"\n\nProject context: {self.project_context}" if self.project_context.strip() else ""
        return CHAT_SYSTEM + ctx

    def ask(self, message: str, images: Sequence[ImageInput] = ()) -> str:
        reply = self.client.chat(self.history, message, images=images, system=self._system())
        self.history.append(("user", message))
        self.history.append(("assistant", reply))
        self.history = self.history[-2 * self.max_turns:]
        return reply

    def reset(self) -> None:
        self.history.clear()


def generate_daily_briefing(
    client: GeminiClient,
    site_log: str,
    todays_tasks: Sequence[str] = (),
    weather_notes: Sequence[str] = (),
) -> DailyBriefing:
    prompt = (
        "Site log / yesterday's notes:\n" + (site_log.strip() or "(none provided)") +
        "\n\nScheduled tasks for today:\n" + ("\n".join(f"- {t}" for t in todays_tasks) or "(none)") +
        "\n\nWeather advisory:\n" + ("\n".join(f"- {w}" for w in weather_notes) or "(not available)")
    )
    return client.generate_json(prompt, DailyBriefing, system=DAILY_SYSTEM)
