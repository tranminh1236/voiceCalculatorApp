from app.services.ocr import OcrService, StubOcrService, OcrDetection
from app.services.stt import SttService, StubSttService


def test_stub_ocr_returns_fixed_detections():
    svc: OcrService = StubOcrService()
    detections = svc.extract(b"fake image bytes")
    assert len(detections) >= 1
    for d in detections:
        assert isinstance(d, OcrDetection)
        assert d.bbox.x >= 0
        assert d.value is not None


def test_stub_stt_returns_fixed_transcript():
    svc: SttService = StubSttService()
    result = svc.transcribe(b"fake audio bytes")
    assert result.transcript
    assert isinstance(result.transcript, str)
