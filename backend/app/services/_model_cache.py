"""Lazy singletons for heavy ML models (PaddleOCR, Whisper).

Why singletons: loading paddleocr ~5-15s; whisper.load_model('small') ~5-30s.
We only want to pay this once per process. Tests should never trigger real loads
unless explicitly testing real services.
"""
from __future__ import annotations
from typing import Any

_paddle_singleton: Any = None
_whisper_singleton: Any = None


def get_paddle_ocr(lang: str = "vi") -> Any:
    """Return a singleton PaddleOCR instance. First call ~5-15s on CPU."""
    global _paddle_singleton
    if _paddle_singleton is None:
        from paddleocr import PaddleOCR
        _paddle_singleton = PaddleOCR(use_angle_cls=False, lang=lang, show_log=False)
    return _paddle_singleton


def get_whisper(model_name: str = "small") -> Any:
    """Return a singleton Whisper model. First call downloads model if absent."""
    global _whisper_singleton
    if _whisper_singleton is None:
        import whisper
        _whisper_singleton = whisper.load_model(model_name)
    return _whisper_singleton


def reset() -> None:
    """Drop cached models. Use in tests or to free memory."""
    global _paddle_singleton, _whisper_singleton
    _paddle_singleton = None
    _whisper_singleton = None
