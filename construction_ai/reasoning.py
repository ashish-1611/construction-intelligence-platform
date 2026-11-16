"""Milestone 4 / Activity 4.1: Multimodal reasoning (images + text -> structured insight)."""
from __future__ import annotations

from typing import Sequence

from .gemini_client import GeminiClient
from .image_utils import ImageInput
from .schemas import PlanExtraction, SiteInsight

SITE_SYSTEM = (
    "You are a senior site engineer and project manager on Indian construction projects. "
    "Reason from the images and the question together. Separate what you SEE (observations) from "
    "what you INFER (assumptions). Never fabricate measurements; if scale is unknown say so."
)

PLAN_SYSTEM = (
    "You read architectural floor plans. Extract only what is explicitly written or can be clearly "
    "computed from labelled dimensions. Convert areas to square feet (1 sq m = 10.764 sq ft). "
    "If the built-up area is not stated or computable, return 0 and explain in notes."
)


def reason_about_site(
    client: GeminiClient, images: Sequence[ImageInput], question: str
) -> SiteInsight:
    prompt = f"Question from the project team: {question.strip() or 'Give an overall site assessment.'}"
    return client.generate_json(prompt, SiteInsight, images=images, system=SITE_SYSTEM)


def extract_plan_details(client: GeminiClient, image: ImageInput) -> PlanExtraction:
    return client.generate_json(
        "Extract built-up area, number of floors, rooms and structural system from this plan.",
        PlanExtraction,
        images=[image],
        system=PLAN_SYSTEM,
    )
