from src.ocr.models import OCRResult, OCRTextBlock
from src.services.translation_pipeline import TranslationPipeline


def test_build_translation_text_joins_visual_ocr_lines():
    ocr_result = OCRResult(
        blocks=[
            OCRTextBlock(text="WHAT AM", confidence=0.99, box=[]),
            OCRTextBlock(text="I SUPPOSED", confidence=0.99, box=[]),
            OCRTextBlock(text="TO DO...", confidence=0.99, box=[]),
        ],
        full_text="WHAT AM\nI SUPPOSED\nTO DO...",
    )

    assert (
        TranslationPipeline.build_translation_text(ocr_result)
        == "WHAT AM I SUPPOSED TO DO..."
    )


def test_build_translation_text_collapses_internal_whitespace():
    ocr_result = OCRResult(
        blocks=[
            OCRTextBlock(text="  What   am  ", confidence=0.99, box=[]),
            OCRTextBlock(text=" I   supposed ", confidence=0.99, box=[]),
            OCRTextBlock(text=" to do? ", confidence=0.99, box=[]),
        ],
        full_text="  What   am  \n I   supposed \n to do? ",
    )

    assert (
        TranslationPipeline.build_translation_text(ocr_result)
        == "What am I supposed to do?"
    )


def test_build_translation_text_falls_back_to_full_text():
    ocr_result = OCRResult(
        blocks=[],
        full_text="Hello\nworld",
    )

    assert TranslationPipeline.build_translation_text(ocr_result) == "Hello world"
