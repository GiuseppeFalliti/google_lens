from src.ocr.models import OCRTextBlock
from src.services.translation_pipeline import TranslationPipeline


def _block(text, x, y, width=120, height=20, confidence=0.95):
    return OCRTextBlock(
        text=text,
        confidence=confidence,
        box=[
            (x, y),
            (x + width, y),
            (x + width, y + height),
            (x, y + height),
        ],
    )


def test_fullscreen_grouping_merges_wrapped_lines_but_not_distant_text():
    blocks = [
        _block("NEXT TIME,", 20, 20),
        _block("OTHER LABEL", 420, 20),
        _block("I AM MARKING IT", 18, 44, width=150),
        _block("AS AN ABSENCE", 22, 68, width=145),
    ]

    groups = TranslationPipeline._group_ocr_blocks(blocks)

    assert len(groups) == 2
    texts = [TranslationPipeline._group_text(group) for group in groups]
    assert "NEXT TIME, I AM MARKING IT AS AN ABSENCE" in texts
    assert "OTHER LABEL" in texts


def test_group_text_preserves_reading_order():
    blocks = [
        _block("SECOND", 10, 40),
        _block("FIRST", 10, 10),
        _block("THIRD", 10, 70),
    ]

    groups = TranslationPipeline._group_ocr_blocks(blocks)

    assert len(groups) == 1
    assert TranslationPipeline._group_text(groups[0]) == "FIRST SECOND THIRD"
