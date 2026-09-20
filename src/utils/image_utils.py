from __future__ import annotations

from PIL import Image, ImageEnhance, ImageOps


def preprocess_for_ocr(
    image: Image.Image,
    *,
    grayscale: bool = False,
    contrast: float = 1.0,
    upscale: float = 1.0,
) -> Image.Image:
    """Return an in-memory image suitable for OCR without aggressive filtering."""
    processed = image.convert("RGB")

    if upscale > 1.0:
        width = max(1, round(processed.width * upscale))
        height = max(1, round(processed.height * upscale))
        processed = processed.resize((width, height), Image.Resampling.LANCZOS)

    if grayscale:
        processed = ImageOps.grayscale(processed).convert("RGB")

    if contrast != 1.0:
        processed = ImageEnhance.Contrast(processed).enhance(contrast)

    return processed
