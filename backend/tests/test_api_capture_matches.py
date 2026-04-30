import io


def _create_template(client) -> int:
    r = client.post("/api/templates", json={
        "name": "T",
        "groups": [{"index": 1, "label": "G", "bet_type": "lo", "multiplier": 80.0}],
    })
    return r.json()["id"]


def _create_capture_with_audio(client) -> tuple[int, list[int], int]:
    """Create capture + upload audio. Returns (capture_id, ocr_ids, audio_group_id)."""
    tid = _create_template(client)
    files = {"image": ("n.png", io.BytesIO(b"x"), "image/png")}
    r = client.post("/api/captures", files=files,
                    data={"template_id": str(tid), "group_provinces": '{"1": ["HN"]}'})
    cb = r.json()
    cid = cb["id"]
    ocr_ids = [n["id"] for n in cb["ocr_numbers"]]

    files = {"audio": ("a.webm", io.BytesIO(b"x"), "audio/webm")}
    r = client.post(f"/api/captures/{cid}/audio", files=files, data={"group_index": "1"})
    ag_id = r.json()["id"]
    return cid, ocr_ids, ag_id


def test_manual_add_match(client, db_session):
    from app.models import Match
    cid, ocr_ids, ag_id = _create_capture_with_audio(client)
    # Stub already auto-matched all 3, so the new match becomes a 4th row
    pre_count = db_session.query(Match).filter(Match.audio_group_id == ag_id).count()

    resp = client.post(f"/api/captures/{cid}/matches", json={
        "ocr_number_id": ocr_ids[0],
        "audio_group_id": ag_id,
        "action": "add",
    })
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["source"] == "manual"
    assert body["ocr_number_id"] == ocr_ids[0]

    post_count = db_session.query(Match).filter(Match.audio_group_id == ag_id).count()
    assert post_count == pre_count + 1


def test_manual_remove_match(client, db_session):
    from app.models import Match
    cid, ocr_ids, ag_id = _create_capture_with_audio(client)
    # Find an existing auto-match for ocr_ids[0]
    auto = db_session.query(Match).filter(
        Match.audio_group_id == ag_id, Match.ocr_number_id == ocr_ids[0]
    ).first()
    assert auto is not None

    resp = client.post(f"/api/captures/{cid}/matches", json={
        "ocr_number_id": ocr_ids[0],
        "audio_group_id": ag_id,
        "action": "remove",
    })
    assert resp.status_code == 200, resp.text

    remaining = db_session.query(Match).filter(
        Match.audio_group_id == ag_id, Match.ocr_number_id == ocr_ids[0]
    ).count()
    # Should have removed AT LEAST one (could be multiple if rule "2a" matched twice)
    assert remaining < 1 or remaining == 0


def test_manual_match_unknown_capture_404(client):
    resp = client.post("/api/captures/9999/matches", json={
        "ocr_number_id": 1, "audio_group_id": 1, "action": "add",
    })
    assert resp.status_code == 404


def test_manual_match_invalid_action_400(client):
    cid, ocr_ids, ag_id = _create_capture_with_audio(client)
    resp = client.post(f"/api/captures/{cid}/matches", json={
        "ocr_number_id": ocr_ids[0],
        "audio_group_id": ag_id,
        "action": "explode",
    })
    assert resp.status_code in (400, 422)


def test_manual_match_remove_nonexistent_404(client):
    cid, ocr_ids, ag_id = _create_capture_with_audio(client)
    # First clear all matches for this ocr/group
    client.post(f"/api/captures/{cid}/matches", json={
        "ocr_number_id": ocr_ids[0], "audio_group_id": ag_id, "action": "remove",
    })
    # Try removing again (now nothing to remove)
    resp = client.post(f"/api/captures/{cid}/matches", json={
        "ocr_number_id": ocr_ids[0], "audio_group_id": ag_id, "action": "remove",
    })
    assert resp.status_code == 404
