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
