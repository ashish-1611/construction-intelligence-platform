"""Image validation and normalisation for multimodal requests."""
from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image, UnidentifiedImageError

MAX_SIDE = 2048
SUPPORTED = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}


class ImageError(ValueError):
    pass


@dataclass(frozen=True)
class ImageInput:
    data: bytes
    mime_type: str
    name: str = "image"


def load_image(raw: bytes, name: str = "image") -> ImageInput:
    """Validate an uploaded image, downscale if huge, and return bytes + MIME type."""
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise ImageError(f"'{name}' is not a readable image.") from exc

    fmt = (img.format or "").upper()
    if fmt not in SUPPORTED:
        raise ImageError(f"'{name}': unsupported format {fmt or 'unknown'} (use PNG, JPEG or WEBP).")

    if max(img.size) > MAX_SIDE:
        img.thumbnail((MAX_SIDE, MAX_SIDE))
        buf = io.BytesIO()
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        img.save(buf, format="JPEG", quality=88)
        return ImageInput(buf.getvalue(), "image/jpeg", name)
    return ImageInput(raw, SUPPORTED[fmt], name)
