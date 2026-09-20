from __future__ import annotations

from dataclasses import dataclass

from PIL import Image, ImageEnhance, ImageOps


@dataclass(slots=True)
class OCRImageVariant:
    name: str
    image: Image.Image
    scale: float


def preprocess_for_ocr(
    image: Image.Image,
    *,
    grayscale: bool = False,
    contrast: float = 1.0,
    upscale: float = 1.0,
    sharpness: float = 1.0,
    autocontrast: bool = False,
) -> Image.Image:
    """Return an in-memory image prepared for OCR."""
    processed = image.convert("RGB")

    if upscale > 1.0:
        width = max(1, round(processed.width * upscale))
        height = max(1, round(processed.height * upscale))
        processed = processed.resize((width, height), Image.Resampling.LANCZOS)

    if grayscale:
        processed = ImageOps.grayscale(processed).convert("RGB")

    if autocontrast:
        processed = ImageOps.autocontrast(processed)

    if contrast != 1.0:
        processed = ImageEnhance.Contrast(processed).enhance(contrast)

    if sharpness != 1.0:
        processed = ImageEnhance.Sharpness(processed).enhance(sharpness)

    return processed


def build_ocr_variants(image: Image.Image) -> list[OCRImageVariant]:
    """Create complementary OCR inputs for small/stylized on-screen text."""
    return [
        OCRImageVariant(
            name="original",
            image=preprocess_for_ocr(image),
            scale=1.0,
        ),
        OCRImageVariant(
            name="upscale_color",
            image=preprocess_for_ocr(
                image,
                upscale=2.0,
                contrast=1.25,
                sharpness=1.30,
            ),
            scale=2.0,
        ),
        OCRImageVariant(
            name="upscale_grayscale",
            image=preprocess_for_ocr(
                image,
                upscale=2.5,
                grayscale=True,
                contrast=1.55,
                sharpness=1.45,
            ),
            scale=2.5,
        ),
        OCRImageVariant(
            name="autocontrast_3x",
            image=preprocess_for_ocr(
                image,
                upscale=3.0,
                grayscale=True,
                autocontrast=True,
                contrast=1.20,
                sharpness=1.65,
            ),
            scale=3.0,
        ),
    ]
