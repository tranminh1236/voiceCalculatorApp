from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class BBox:
    x: float
    y: float
    w: float
    h: float


@dataclass(frozen=True)
class OcrDetection:
    bbox: BBox
    raw_text: str
    value: float | None
    confidence: float


class OcrService(Protocol):
    def extract(self, image_bytes: bytes) -> list[OcrDetection]: ...


class StubOcrService:
    """Returns a fixed set of fake detections — used until Plan 2 wires PaddleOCR."""

    def extract(self, image_bytes: bytes) -> list[OcrDetection]:
        return [
            OcrDetection(BBox(10, 20, 40, 30), "23", 23.0, 0.95),
            OcrDetection(BBox(80, 20, 30, 30), "5", 5.0, 0.92),
            OcrDetection(BBox(140, 20, 50, 30), "105", 105.0, 0.88),
        ]


import re

_NUMBER_RE = re.compile(r"^-?\d+(?:[.,]\d+)?$")


def _bbox_from_corners(corners: list[list[float]]) -> BBox:
    """PaddleOCR returns 4 corner points; convert to axis-aligned (x,y,w,h)."""
    xs = [c[0] for c in corners]
    ys = [c[1] for c in corners]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    return BBox(x=x_min, y=y_min, w=x_max - x_min, h=y_max - y_min)


def _parse_numeric(text: str) -> float | None:
    t = text.strip().replace(",", ".")
    if not _NUMBER_RE.match(t):
        return None
    try:
        return float(t)
    except ValueError:
        return None


class PaddleOcrService:
    """OcrService backed by PaddleOCR. Lazy-loads model on first call."""

    def __init__(self, lang: str = "vi") -> None:
        self._lang = lang

    def _run_paddle(self, image_bytes: bytes) -> list:
        """Decode bytes → numpy array → call PaddleOCR. Isolated for monkey-patching in tests.

        We decode in-memory rather than via tempfile because PaddleOCR's tempfile
        path silently fails on macOS arm64 (returns None from cv2.imread).
        """
        import cv2
        import numpy as np
        from app.services._model_cache import get_paddle_ocr
        arr = np.frombuffer(image_bytes, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return [None]
        ocr = get_paddle_ocr(lang=self._lang)
        return ocr.ocr(img, cls=False)

    def extract(self, image_bytes: bytes) -> list[OcrDetection]:
        raw = self._run_paddle(image_bytes)

        if not raw or raw[0] is None:
            return []

        detections: list[OcrDetection] = []
        for entry in raw[0]:
            corners, (text, conf) = entry
            value = _parse_numeric(text)
            if value is None:
                continue
            detections.append(OcrDetection(
                bbox=_bbox_from_corners(corners),
                raw_text=text,
                value=value,
                confidence=float(conf),
            ))
        return detections


class EasyOcrService:
    """OcrService backed by EasyOCR (PyTorch-based). Lazy-loads model on first call.

    Recommended over PaddleOcrService on macOS arm64 because PaddlePaddle
    inference is extremely slow on Apple Silicon (no MPS support). EasyOCR
    uses PyTorch which has solid Apple Silicon support and runs ~5-30x faster
    on the same hardware.
    """

    def __init__(self, lang: str = "vi") -> None:
        # EasyOCR Reader takes a list of language codes
        self._langs = [lang] if isinstance(lang, str) else list(lang)

    def _run_easyocr(self, image_bytes: bytes) -> list:
        """Call EasyOCR Reader.readtext(). Isolated for monkey-patching in tests."""
        import cv2
        import numpy as np
        from app.services._model_cache import get_easyocr
        arr = np.frombuffer(image_bytes, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return []
        reader = get_easyocr(self._langs)
        return reader.readtext(img)

    def extract(self, image_bytes: bytes) -> list[OcrDetection]:
        raw = self._run_easyocr(image_bytes)

        detections: list[OcrDetection] = []
        for entry in raw:
            # EasyOCR returns: [bbox_4_corners, text, confidence]
            corners, text, conf = entry
            value = _parse_numeric(text)
            if value is None:
                continue
            detections.append(OcrDetection(
                bbox=_bbox_from_corners(corners),
                raw_text=text,
                value=value,
                confidence=float(conf),
            ))
        return detections
