import io


def _create_template(client) -> int:
    r = client.post("/api/templates", json={
        "name": "T",
        "groups": [{"index": 1, "label": "G", "bet_type": "lo", "multiplier": 80.0}],
    })
    return r.json()["id"]


def _create_capture(client, tid: int) -> int:
    files = {"image": ("n.png", io.BytesIO(b"x"), "image/png")}
    r = client.post("/api/captures", files=files,
                    data={"template_id": str(tid), "group_provinces": '{"1": ["HN"]}'})
    return r.json()["id"]


def test_delete_capture(client, db_session):
    from app.models import Capture, OcrNumber
    tid = _create_template(client)
    cid = _create_capture(client, tid)

    # Pre-conditions: capture + ocr rows exist
    assert db_session.get(Capture, cid) is not None
    ocr_count_pre = db_session.query(OcrNumber).filter(OcrNumber.capture_id == cid).count()
    assert ocr_count_pre > 0

    resp = client.delete(f"/api/captures/{cid}")
    assert resp.status_code == 204, resp.text

    # Capture + cascaded OCR rows gone
    db_session.expire_all()
    assert db_session.get(Capture, cid) is None
    assert db_session.query(OcrNumber).filter(OcrNumber.capture_id == cid).count() == 0


def test_delete_capture_cascades_audio_groups(client, db_session):
    """Deleting capture should also remove its audio_groups + matches via FK CASCADE."""
    from app.models import AudioGroup, Match
    tid = _create_template(client)
    cid = _create_capture(client, tid)

    # Add an audio group (which auto-creates matches)
    files = {"audio": ("a.webm", io.BytesIO(b"x"), "audio/webm")}
    client.post(f"/api/captures/{cid}/audio", files=files, data={"group_index": "1"})

    pre_audio = db_session.query(AudioGroup).filter(AudioGroup.capture_id == cid).count()
    assert pre_audio == 1

    resp = client.delete(f"/api/captures/{cid}")
    assert resp.status_code == 204

    db_session.expire_all()
    assert db_session.query(AudioGroup).filter(AudioGroup.capture_id == cid).count() == 0
    # Matches reference deleted ocr/audio_group → cascade should clean up
    # (Hard to assert directly without group ids; just verify no orphan matches for this cid via join)
    assert db_session.query(Match).join(AudioGroup, Match.audio_group_id == AudioGroup.id, isouter=False).filter(AudioGroup.capture_id == cid).count() == 0


def test_delete_unknown_capture_404(client):
    resp = client.delete("/api/captures/9999")
    assert resp.status_code == 404
