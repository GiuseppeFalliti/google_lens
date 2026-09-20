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
) -> Image.Image:
    """Return an in-memory image prepared for OCR."""
    processed = image.convert("RGB")

    if upscale > 1.0:
        width = max(1, round(processed.width * upscale))
        height = max(1, round(processed.height * upscale))
        processed = processed.resize((width, height), Image.Resampling.LANCZOS)

    if grayscale:
        processed = ImageOps.grayscale(processed).convert("RGB")

    if contrast != 1.0:
        processed = ImageEnhance.Contrast(processed).enhance(contrast)

    if sharpness != 1.0:
        processed = ImageEnhance.Sharpness(processed).enhance(sharpness)

    return processed


def build_ocr_variants(image: Image.Image) -> list[OCRImageVariant]:
    """Create complementary OCR inputs for small/stylized on-screen text.

    The original image is retained because enhancement is not universally
    beneficial. The other variants target the common failure modes found in
    games/comics: small glyphs, low contrast, anti-aliasing and textured
    backgrounds.
    """
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
                upscale=2.0,
                grayscale=True,
                contrast=1.60,
                sharpness=1.40,
            ),
            scale=2.0,
        ),
    ]
