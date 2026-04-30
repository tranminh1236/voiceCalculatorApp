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
import tempfile
from pathlib import Path

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

    def _run_paddle(self, image_path: str) -> list:
        """Call into PaddleOCR. Isolated for monkey-patching in tests."""
        from app.services._model_cache import get_paddle_ocr
        ocr = get_paddle_ocr(lang=self._lang)
        return ocr.ocr(image_path, cls=False)

    def extract(self, image_bytes: bytes) -> list[OcrDetection]:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(image_bytes)
            tmp_path = f.name
        try:
            raw = self._run_paddle(tmp_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

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
