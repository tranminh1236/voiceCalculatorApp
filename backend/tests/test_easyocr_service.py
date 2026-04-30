from unittest.mock import patch
from app.services.ocr import EasyOcrService, OcrDetection, BBox


# EasyOCR's raw return format: [box_4_corners, text, confidence] per detected text region.
_FAKE_EASYOCR_RESULT = [
    [[[10, 20], [50, 20], [50, 50], [10, 50]], "23", 0.95],
    [[[80, 20], [110, 20], [110, 50], [80, 50]], "hello", 0.88],  # non-numeric → filtered
    [[[140, 20], [190, 20], [190, 50], [140, 50]], "105", 0.91],
]


def test_easyocr_service_filters_non_numeric_and_normalizes_bbox():
    svc = EasyOcrService(lang="vi")
    with patch.object(svc, "_run_easyocr", return_value=_FAKE_EASYOCR_RESULT):
        detections = svc.extract(b"image-bytes")

    assert len(detections) == 2  # "hello" filtered out
    values = [d.value for d in detections]
    assert 23.0 in values
    assert 105.0 in values

    d23 = next(d for d in detections if d.value == 23.0)
    assert isinstance(d23.bbox, BBox)
    assert d23.bbox.x == 10.0
    assert d23.bbox.y == 20.0
    assert d23.bbox.w == 40.0
    assert d23.bbox.h == 30.0
    assert d23.confidence == 0.95


def test_easyocr_service_handles_empty_result():
    svc = EasyOcrService(lang="vi")
    with patch.object(svc, "_run_easyocr", return_value=[]):
        assert svc.extract(b"image-bytes") == []


def test_easyocr_service_handles_decimal_with_comma():
    fake = [[[[0, 0], [10, 0], [10, 10], [0, 10]], "3,5", 0.9]]
    svc = EasyOcrService(lang="vi")
    with patch.object(svc, "_run_easyocr", return_value=fake):
        d = svc.extract(b"x")
    assert len(d) == 1
    assert d[0].value == 3.5
