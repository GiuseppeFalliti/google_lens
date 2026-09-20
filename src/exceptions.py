class ScreenTranslatorError(Exception):
    """Base exception for expected application errors."""


class CaptureError(ScreenTranslatorError):
    """Raised when a screen region cannot be captured."""


class OCRError(ScreenTranslatorError):
    """Raised when OCR cannot be initialized or executed."""


class NoTextDetectedError(OCRError):
    """Raised when OCR completes but finds no usable text."""


class TranslationError(ScreenTranslatorError):
    """Raised when a translation provider fails."""


class TranslationConfigurationError(TranslationError):
    """Raised when a translation provider is not configured correctly."""


class OperationCancelled(ScreenTranslatorError):
    """Raised when an in-flight translation operation was cancelled."""
