from PIL import Image

from src.ocr.models import OCRResult, OCRTextBlock
from src.services.translation_pipeline import TranslationPipeline
from src.utils.image_utils import build_ocr_variants


def test_build_ocr_variants_creates_original_and_enhanced_inputs():
    image = Image.new("RGB", (120, 50), "white")
    variants = build_ocr_variants(image)

    assert [variant.name for variant in variants] == [
        "original",
        "upscale_color",
        "upscale_grayscale",
    ]
    assert variants[0].image.size == (120, 50)
    assert variants[1].image.size == (240, 100)
    assert variants[2].image.size == (240, 100)
    assert variants[0].scale == 1.0
    assert variants[1].scale == 2.0

    for variant in variants:
        variant.image.close()
    image.close()


def test_ocr_score_prefers_complete_high_confidence_reading():
    partial = OCRResult(
        blocks=[
            OCRTextBlock(
                text="ABSENCE",
                confidence=0.99,
                box=[(0.0, 0.0), (20.0, 0.0), (20.0, 10.0), (0.0, 10.0)],
            )
        ],
        full_text="ABSENCE",
    )
    complete = OCRResult(
        blocks=[
            OCRTextBlock(
                text="NEXT TIME I AM MARKING IT",
                confidence=0.94,
                box=[(0.0, 0.0), (80.0, 0.0), (80.0, 10.0), (0.0, 10.0)],
            ),
            OCRTextBlock(
                text="AS AN UNEXCUSED ABSENCE",
                confidence=0.93,
                box=[(0.0, 12.0), (90.0, 12.0), (90.0, 22.0), (0.0, 22.0)],
            ),
        ],
        full_text="NEXT TIME I AM MARKING IT\nAS AN UNEXCUSED ABSENCE",
    )

    assert (
        TranslationPipeline.score_ocr_result(complete)
        > TranslationPipeline.score_ocr_result(partial)
    )


def test_rescale_ocr_result_maps_boxes_back_to_original_image():
    result = OCRResult(
        blocks=[
            OCRTextBlock(
                text="HELLO",
                confidence=0.9,
                box=[
                    (20.0, 10.0),
                    (100.0, 10.0),
                    (100.0, 30.0),
                    (20.0, 30.0),
                ],
            )
        ],
        full_text="HELLO",
    )

    rescaled = TranslationPipeline.rescale_ocr_result(result, 2.0)

    assert rescaled.blocks[0].box == [
        (10.0, 5.0),
        (50.0, 5.0),
        (50.0, 15.0),
        (10.0, 15.0),
    ]
