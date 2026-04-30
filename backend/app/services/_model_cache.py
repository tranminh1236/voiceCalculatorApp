"""Lazy singletons for heavy ML models (PaddleOCR, EasyOCR, Whisper).

Why singletons: loading these models takes 5-60s. We only pay this once per
process. Tests should never trigger real loads unless explicitly testing
real services.
"""
from __future__ import annotations
from typing import Any

_paddle_singleton: Any = None
_easyocr_singleton: Any = None
_whisper_singleton: Any = None


def get_paddle_ocr(lang: str = "vi") -> Any:
    """Return a singleton PaddleOCR instance. First call ~5-15s on CPU.

    NOTE: PaddleOCR inference is extremely slow on Apple Silicon (no MPS).
    Prefer EasyOcrService on macOS arm64.
    """
    global _paddle_singleton
    if _paddle_singleton is None:
        from paddleocr import PaddleOCR
        _paddle_singleton = PaddleOCR(use_angle_cls=False, lang=lang, show_log=False)
    return _paddle_singleton


def get_easyocr(langs: list[str] | None = None) -> Any:
    """Return a singleton EasyOCR Reader. First call ~10-60s + downloads ~80MB on first use.

    Recommended over PaddleOCR on Apple Silicon (PyTorch backend has MPS).
    """
    global _easyocr_singleton
    if _easyocr_singleton is None:
        import easyocr
        _easyocr_singleton = easyocr.Reader(langs or ["vi"], gpu=False)
    return _easyocr_singleton


def get_whisper(model_name: str = "small") -> Any:
    """Return a singleton Whisper model. First call downloads model if absent."""
    global _whisper_singleton
    if _whisper_singleton is None:
        import whisper
        _whisper_singleton = whisper.load_model(model_name)
    return _whisper_singleton


def reset() -> None:
    """Drop cached models. Use in tests or to free memory."""
    global _paddle_singleton, _easyocr_singleton, _whisper_singleton
    _paddle_singleton = None
    _easyocr_singleton = None
    _whisper_singleton = None
