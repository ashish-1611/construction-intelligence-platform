"""Thin Gemini wrapper: multimodal input + JSON-schema enforced output (Activity 4.2)."""
from __future__ import annotations

import logging
from typing import Sequence, TypeVar

from pydantic import BaseModel, ValidationError

from .config import Settings, get_settings
from .image_utils import ImageInput

log = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class GeminiError(RuntimeError):
    """Raised when AI is not configured or the model cannot produce valid output."""


class GeminiClient:
    def __init__(self, settings: Settings | None = None, client=None):
        self.settings = settings or get_settings()
        self._client = client

    # ------------------------------------------------------------------ setup
    @property
    def client(self):
        if self._client is None:
            if not self.settings.ai_enabled:
                raise GeminiError(
                    "AI is not configured. Set GOOGLE_API_KEY (or Vertex AI variables) in .env."
                )
            from google import genai  # imported lazily so tests/offline mode work without it

            if self.settings.use_vertex:
                self._client = genai.Client(
                    vertexai=True, project=self.settings.project, location=self.settings.location
                )
            else:
                self._client = genai.Client(api_key=self.settings.api_key)
        return self._client

    @staticmethod
    def _types():
        from google.genai import types

        return types

    def _image_parts(self, images: Sequence[ImageInput]):
        t = self._types()
        return [t.Part.from_bytes(data=i.data, mime_type=i.mime_type) for i in images]

    # ------------------------------------------------------------- structured
    def generate_json(
        self,
        prompt: str,
        schema: type[T],
        images: Sequence[ImageInput] = (),
        system: str | None = None,
        retries: int = 2,
    ) -> T:
        """Call Gemini with a response schema and validate the result with Pydantic.

        If the model returns something that fails validation, retry with the error
        fed back, so the final return value is always a valid `schema` instance.
        """
        t = self._types()
        config = t.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_schema=schema,
            temperature=0.2,
        )
        current_prompt = prompt
        last_error: Exception | None = None
        for attempt in range(retries + 1):
            try:
                resp = self.client.models.generate_content(
                    model=self.settings.model,
                    contents=[*self._image_parts(images), current_prompt],
                    config=config,
                )
            except GeminiError:
                raise
            except Exception as exc:  # network / quota / auth errors
                raise GeminiError(f"Gemini request failed: {exc}") from exc

            parsed = getattr(resp, "parsed", None)
            if isinstance(parsed, schema):
                return parsed
            try:
                return schema.model_validate_json(resp.text or "")
            except (ValidationError, ValueError) as exc:
                last_error = exc
                log.warning("Schema validation failed (attempt %d): %s", attempt + 1, exc)
                current_prompt = (
                    f"{prompt}\n\nYour previous reply was invalid JSON for the required schema "
                    f"({exc}). Reply again with ONLY valid JSON matching the schema."
                )
        raise GeminiError(f"Model did not return schema-valid JSON: {last_error}")

    # ------------------------------------------------------------------- chat
    def chat(
        self,
        history: Sequence[tuple[str, str]],
        message: str,
        images: Sequence[ImageInput] = (),
        system: str | None = None,
    ) -> str:
        """history = [(role, text)] with role in {'user', 'assistant'}."""
        t = self._types()
        contents = [
            t.Content(role="user" if r == "user" else "model", parts=[t.Part(text=txt)])
            for r, txt in history
        ]
        contents.append(
            t.Content(role="user", parts=[*self._image_parts(images), t.Part(text=message)])
        )
        try:
            resp = self.client.models.generate_content(
                model=self.settings.model,
                contents=contents,
                config=t.GenerateContentConfig(system_instruction=system, temperature=0.4),
            )
        except GeminiError:
            raise
        except Exception as exc:
            raise GeminiError(f"Gemini request failed: {exc}") from exc
        return (resp.text or "").strip()
