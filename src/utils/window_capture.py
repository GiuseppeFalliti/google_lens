from __future__ import annotations

import ctypes
import logging
import sys

from PySide6.QtWidgets import QWidget


_WDA_EXCLUDEFROMCAPTURE = 0x00000011


def exclude_widget_from_capture(widget: QWidget) -> bool:
    """Best-effort exclusion of one of our windows from Windows screen capture.

    This keeps the Screen Translator UI and its translation overlays out of the
    MSS live OCR feed. Windows 10 2004+ supports WDA_EXCLUDEFROMCAPTURE.
    """
    if sys.platform != "win32":
        return False

    logger = logging.getLogger("screen_translator.capture_exclusion")

    try:
        hwnd = int(widget.winId())
        if not hwnd:
            return False

        result = ctypes.windll.user32.SetWindowDisplayAffinity(
            hwnd,
            _WDA_EXCLUDEFROMCAPTURE,
        )
        if not result:
            logger.warning(
                "SetWindowDisplayAffinity failed for hwnd=%s; the app may appear in OCR.",
                hwnd,
            )
            return False

        logger.debug("Excluded hwnd=%s from screen capture.", hwnd)
        return True
    except Exception as exc:
        logger.warning("Unable to exclude window from capture: %s", exc)
        return False
