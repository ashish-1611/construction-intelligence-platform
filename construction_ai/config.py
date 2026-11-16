"""Environment-driven configuration (Activity 1.2: environment setup)."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    api_key: str | None
    use_vertex: bool
    project: str | None
    location: str
    model: str

    @property
    def ai_enabled(self) -> bool:
        return bool(self.api_key) or (self.use_vertex and bool(self.project))


def get_settings() -> Settings:
    return Settings(
        api_key=os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or None,
        use_vertex=os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").lower() in {"1", "true", "yes"},
        project=os.getenv("GOOGLE_CLOUD_PROJECT") or None,
        location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
    )
