"""Manual smoke test for PaddleOCR + Whisper. NOT run by pytest.

Usage:
    cd backend
    source .venv/bin/activate
    python scripts/smoke_real_services.py path/to/image.png path/to/audio.wav

The script loads PaddleOCR + Whisper (slow first time), runs each, and prints results.
Use this after Plan 2 to verify your environment can actually run the real models
before trying the live web app.
"""
from __future__ import annotations
import sys
from pathlib import Path

# Make `app` importable when running as a script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("Usage: smoke_real_services.py <image_path> <audio_path>")
        return 2

    image_path, audio_path = argv[1], argv[2]
    if not Path(image_path).exists():
        print(f"image not found: {image_path}")
        return 1
    if not Path(audio_path).exists():
        print(f"audio not found: {audio_path}")
        return 1

    print(f"=== OCR ({image_path}) ===")
    from app.services.ocr import PaddleOcrService
    ocr = PaddleOcrService(lang="vi")
    image_bytes = Path(image_path).read_bytes()
    detections = ocr.extract(image_bytes)
    print(f"detected {len(detections)} numbers:")
    for d in detections:
        print(f"  {d.value:>10}  conf={d.confidence:.2f}  bbox=({d.bbox.x:.0f},{d.bbox.y:.0f},{d.bbox.w:.0f},{d.bbox.h:.0f})  raw={d.raw_text!r}")

    print(f"\n=== STT ({audio_path}) ===")
    from app.services.stt import WhisperSttService
    from app.services.audio import transcribe_and_parse
    stt = WhisperSttService(model_name="small", language="vi")
    audio_bytes = Path(audio_path).read_bytes()
    try:
        result = transcribe_and_parse(audio_bytes, stt)
    except ValueError as e:
        print(f"parse failed: {e}")
        raw = stt.transcribe(audio_bytes)
        print(f"transcript was: {raw.transcript!r}")
        return 1

    print(f"transcript: {result.transcript!r}")
    print(f"numbers:    {result.parsed_numbers}")
    print(f"sum:        {result.sum}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
