from unittest.mock import patch
from app.services.ocr import PaddleOcrService, OcrDetection, BBox


_FAKE_PADDLE_RESULT = [[
    [[[10.0, 20.0], [50.0, 20.0], [50.0, 50.0], [10.0, 50.0]], ("23", 0.95)],
    [[[80.0, 20.0], [110.0, 20.0], [110.0, 50.0], [80.0, 50.0]], ("hello", 0.88)],
    [[[140.0, 20.0], [190.0, 20.0], [190.0, 50.0], [140.0, 50.0]], ("105", 0.91)],
    [[[200.0, 20.0], [240.0, 20.0], [240.0, 50.0], [200.0, 50.0]], ("3.5", 0.86)],
]]


def test_paddle_service_filters_non_numeric_and_normalizes_bbox():
    svc = PaddleOcrService(lang="vi")
    with patch.object(svc, "_run_paddle", return_value=_FAKE_PADDLE_RESULT):
        detections = svc.extract(b"image-bytes")

    assert len(detections) == 3
    values = [d.value for d in detections]
    assert 23.0 in values
    assert 105.0 in values
    assert 3.5 in values

    d23 = next(d for d in detections if d.value == 23.0)
    assert isinstance(d23.bbox, BBox)
    assert d23.bbox.x == 10.0
    assert d23.bbox.y == 20.0
    assert d23.bbox.w == 40.0
    assert d23.bbox.h == 30.0
    assert d23.confidence == 0.95


def test_paddle_service_handles_empty_result():
    svc = PaddleOcrService(lang="vi")
    with patch.object(svc, "_run_paddle", return_value=[None]):
        assert svc.extract(b"image-bytes") == []


def test_paddle_service_handles_negative_numbers():
    fake = [[[[[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0]], ("-5", 0.9)]]]
    svc = PaddleOcrService(lang="vi")
    with patch.object(svc, "_run_paddle", return_value=fake):
        d = svc.extract(b"x")
    assert len(d) == 1
    assert d[0].value == -5.0
