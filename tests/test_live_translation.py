from src.ocr.models import OCRResult, OCRTextBlock
from src.services.translation_pipeline import TranslationPipeline


def _result(text: str, confidence: float = 0.9) -> OCRResult:
    return OCRResult(
        blocks=[
            OCRTextBlock(
                text=text,
                confidence=confidence,
                box=[(0.0, 0.0), (120.0, 0.0), (120.0, 20.0), (0.0, 20.0)],
            )
        ],
        full_text=text,
    )


def test_live_frame_change_score_detects_unchanged_content():
    previous = bytes([120] * (64 * 36))
    current = bytes([120] * (64 * 36))

    assert TranslationPipeline.frame_change_score(previous, current) == 0.0


def test_live_frame_change_score_detects_scrolled_content():
    previous = bytes([20] * (64 * 36))
    current = bytes([180] * (64 * 36))

    assert (
        TranslationPipeline.frame_change_score(previous, current)
        > TranslationPipeline.LIVE_CHANGE_THRESHOLD
    )


def test_live_ocr_prefers_original_when_enhanced_gain_is_small():
    original = _result("NEXT TIME I AM MARKING IT AS AN ABSENCE", 0.94)
    enhanced = _result("NEXT TIME I AM IT MARKING AS AN ABSENCE", 0.96)

    selected, name = TranslationPipeline._choose_live_ocr_result(
        original,
        enhanced,
    )

    assert name == "original"
    assert selected.full_text == original.full_text


def test_live_ocr_accepts_enhanced_when_it_recovers_much_more_text():
    original = _result("NEXT TIME", 0.95)
    enhanced = _result(
        "NEXT TIME I AM MARKING IT AS AN UNEXCUSED ABSENCE",
        0.90,
    )

    selected, name = TranslationPipeline._choose_live_ocr_result(
        original,
        enhanced,
    )

    assert name == "enhanced"
    assert selected.full_text == enhanced.full_text
