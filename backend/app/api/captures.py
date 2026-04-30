import json
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_ocr_service, get_stt_service
from app.config import settings
from app.models import Template, Capture, OcrNumber, AudioGroup, Match
from app.schemas import CaptureOut, OcrNumberOut, BBoxOut, AudioGroupOut, MatchOut, OcrCorrectionIn, MatchActionIn
from app.services.matcher import match_numbers
from app.services.ocr import OcrService
from app.services.stt import SttService
from app.services.audio import transcribe_and_parse


router = APIRouter(prefix="/api/captures", tags=["captures"])


def _capture_to_out(c: Capture, ocr_rows: list[OcrNumber]) -> CaptureOut:
    raw_gp = json.loads(c.group_provinces_json)
    group_provinces: dict[int, list[str]] = {int(k): v for k, v in raw_gp.items()}
    return CaptureOut(
        id=c.id,
        template_id=c.template_id,
        image_path=c.image_path,
        status=c.status,
        final_value=c.final_value,
        group_provinces=group_provinces,
        writer_name=c.writer_name,
        note_date=c.note_date,
        tags=json.loads(c.tags_json) if c.tags_json else None,
        notes=c.notes,
        ocr_numbers=[
            OcrNumberOut(
                id=n.id,
                bbox=BBoxOut(x=n.bbox_x, y=n.bbox_y, w=n.bbox_w, h=n.bbox_h),
                raw_text=n.raw_text,
                raw_value=n.raw_value,
                corrected_value=n.corrected_value,
                confidence=n.confidence,
            )
            for n in ocr_rows
        ],
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


@router.post("", response_model=CaptureOut, status_code=status.HTTP_201_CREATED)
def create_capture(
    template_id: int = Form(...),
    group_provinces: str = Form(..., description='JSON dict, e.g. {"1": ["HN"], "3": ["DNG","KH"]}'),
    writer_name: str | None = Form(default=None),
    note_date: str | None = Form(default=None),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    ocr: OcrService = Depends(get_ocr_service),
) -> CaptureOut:
    t = db.get(Template, template_id)
    if t is None:
        raise HTTPException(status_code=404, detail="template not found")

    try:
        gp_raw = json.loads(group_provinces)
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="group_provinces must be valid JSON")

    if not isinstance(gp_raw, dict) or not gp_raw:
        raise HTTPException(status_code=422, detail="group_provinces must be a non-empty object")

    gp_normalized: dict[str, list[str]] = {}
    for k, v in gp_raw.items():
        if not isinstance(v, list) or not v:
            raise HTTPException(status_code=422, detail=f"group {k}: provinces list must be non-empty")
        cleaned = [p.strip() for p in v if isinstance(p, str) and p.strip()]
        if not cleaned:
            raise HTTPException(status_code=422, detail=f"group {k}: no valid province codes")
        gp_normalized[str(k)] = cleaned

    Path(settings.media_dir, "captures").mkdir(parents=True, exist_ok=True)
    ext = (image.filename or "img").split(".")[-1] if "." in (image.filename or "") else "bin"
    fname = f"{uuid.uuid4().hex}.{ext}"
    fpath = Path(settings.media_dir, "captures", fname)
    image_bytes = image.file.read()
    fpath.write_bytes(image_bytes)

    detections = ocr.extract(image_bytes)

    c = Capture(
        template_id=template_id,
        image_path=str(fpath),
        status="draft",
        group_provinces_json=json.dumps(gp_normalized),
        writer_name=writer_name,
        note_date=note_date,
    )
    db.add(c)
    db.flush()

    ocr_rows: list[OcrNumber] = []
    for d in detections:
        n = OcrNumber(
            capture_id=c.id,
            bbox_x=d.bbox.x, bbox_y=d.bbox.y, bbox_w=d.bbox.w, bbox_h=d.bbox.h,
            raw_text=d.raw_text,
            raw_value=d.value,
            confidence=d.confidence,
        )
        db.add(n)
        ocr_rows.append(n)
    db.commit()
    db.refresh(c)
    for n in ocr_rows:
        db.refresh(n)

    return _capture_to_out(c, ocr_rows)


@router.get("", response_model=list[CaptureOut])
def list_captures(db: Session = Depends(get_db)) -> list[CaptureOut]:
    out: list[CaptureOut] = []
    for c in db.query(Capture).order_by(Capture.id.desc()).all():
        rows = db.query(OcrNumber).filter(OcrNumber.capture_id == c.id).all()
        out.append(_capture_to_out(c, rows))
    return out


@router.get("/{capture_id}", response_model=CaptureOut)
def get_capture(capture_id: int, db: Session = Depends(get_db)) -> CaptureOut:
    c = db.get(Capture, capture_id)
    if c is None:
        raise HTTPException(status_code=404, detail="capture not found")
    rows = db.query(OcrNumber).filter(OcrNumber.capture_id == c.id).all()
    return _capture_to_out(c, rows)


def _multiplier_for_group(template_groups_json: str, group_index: int) -> float | None:
    groups = json.loads(template_groups_json)
    for g in groups:
        if int(g["index"]) == group_index:
            return float(g["multiplier"])
    return None


@router.post("/{capture_id}/audio", response_model=AudioGroupOut, status_code=status.HTTP_201_CREATED)
def upload_audio(
    capture_id: int,
    group_index: int = Form(...),
    audio: UploadFile = File(...),
    db: Session = Depends(get_db),
    stt: SttService = Depends(get_stt_service),
) -> AudioGroupOut:
    c = db.get(Capture, capture_id)
    if c is None:
        raise HTTPException(status_code=404, detail="capture not found")

    t = db.get(Template, c.template_id)
    if t is None:
        raise HTTPException(status_code=500, detail="template missing for capture")

    multiplier = _multiplier_for_group(t.groups_json, group_index)
    if multiplier is None:
        raise HTTPException(status_code=400, detail=f"group_index {group_index} not in template")

    Path(settings.media_dir, "audio").mkdir(parents=True, exist_ok=True)
    fname = f"{uuid.uuid4().hex}_g{group_index}.webm"
    fpath = Path(settings.media_dir, "audio", fname)
    audio_bytes = audio.file.read()
    fpath.write_bytes(audio_bytes)

    pipeline_result = transcribe_and_parse(audio_bytes, stt)

    row = AudioGroup(
        capture_id=capture_id,
        group_index=group_index,
        audio_path=str(fpath),
        transcript=pipeline_result.transcript,
        parsed_numbers_json=json.dumps(pipeline_result.parsed_numbers),
        sum=pipeline_result.sum,
        multiplier_snapshot=multiplier,
    )
    db.add(row)
    db.flush()  # need row.id for matches

    # Auto-match: gather OCR numbers for this capture + existing match counts (across other groups)
    ocr_rows = db.query(OcrNumber).filter(OcrNumber.capture_id == capture_id).all()
    ocr_pairs = [
        (n.id, n.corrected_value if n.corrected_value is not None else n.raw_value)
        for n in ocr_rows
        if (n.corrected_value is not None or n.raw_value is not None)
    ]
    existing_counts = dict(
        db.query(Match.ocr_number_id, func.count(Match.id))
        .group_by(Match.ocr_number_id)
        .all()
    )
    proposals = match_numbers(pipeline_result.parsed_numbers, ocr_pairs, existing_counts)

    match_rows: list[Match] = []
    for prop in proposals:
        if prop.ocr_id is None:
            continue
        m = Match(
            ocr_number_id=prop.ocr_id,
            audio_group_id=row.id,
            confidence=prop.confidence,
            source="auto",
        )
        db.add(m)
        match_rows.append(m)
    db.commit()
    db.refresh(row)
    for m in match_rows:
        db.refresh(m)

    return AudioGroupOut(
        id=row.id,
        capture_id=row.capture_id,
        group_index=row.group_index,
        audio_path=row.audio_path,
        transcript=row.transcript,
        parsed_numbers=pipeline_result.parsed_numbers,
        sum=row.sum,
        multiplier_snapshot=row.multiplier_snapshot,
        matches=[MatchOut.model_validate(m) for m in match_rows],
    )


@router.patch("/{capture_id}/ocr/{ocr_id}", response_model=OcrNumberOut)
def patch_ocr(
    capture_id: int,
    ocr_id: int,
    body: OcrCorrectionIn,
    db: Session = Depends(get_db),
) -> OcrNumberOut:
    c = db.get(Capture, capture_id)
    if c is None:
        raise HTTPException(status_code=404, detail="capture not found")
    n = db.get(OcrNumber, ocr_id)
    if n is None or n.capture_id != capture_id:
        raise HTTPException(status_code=404, detail="ocr number not found in capture")
    n.corrected_value = body.corrected_value
    db.commit()
    db.refresh(n)
    return OcrNumberOut(
        id=n.id,
        bbox=BBoxOut(x=n.bbox_x, y=n.bbox_y, w=n.bbox_w, h=n.bbox_h),
        raw_text=n.raw_text,
        raw_value=n.raw_value,
        corrected_value=n.corrected_value,
        confidence=n.confidence,
    )


@router.post("/{capture_id}/matches", response_model=MatchOut)
def toggle_match(
    capture_id: int,
    body: MatchActionIn,
    response: Response,
    db: Session = Depends(get_db),
) -> MatchOut:
    c = db.get(Capture, capture_id)
    if c is None:
        raise HTTPException(status_code=404, detail="capture not found")

    if body.action not in ("add", "remove"):
        raise HTTPException(status_code=400, detail="action must be 'add' or 'remove'")

    # Validate ocr/audio_group belong to this capture
    n = db.get(OcrNumber, body.ocr_number_id)
    if n is None or n.capture_id != capture_id:
        raise HTTPException(status_code=404, detail="ocr number not found in capture")
    g = db.get(AudioGroup, body.audio_group_id)
    if g is None or g.capture_id != capture_id:
        raise HTTPException(status_code=404, detail="audio group not found in capture")

    if body.action == "add":
        m = Match(
            ocr_number_id=body.ocr_number_id,
            audio_group_id=body.audio_group_id,
            confidence=1.0,
            source="manual",
        )
        db.add(m)
        db.commit()
        db.refresh(m)
        response.status_code = 201
        return MatchOut.model_validate(m)
    else:  # remove
        # Remove the most recent match for this pair (LIFO behavior — same OCR may match same group N times)
        m = (
            db.query(Match)
            .filter(Match.ocr_number_id == body.ocr_number_id,
                    Match.audio_group_id == body.audio_group_id)
            .order_by(Match.id.desc())
            .first()
        )
        if m is None:
            raise HTTPException(status_code=404, detail="no match exists for this ocr/audio_group")
        snapshot = MatchOut.model_validate(m)
        db.delete(m)
        db.commit()
        return snapshot
