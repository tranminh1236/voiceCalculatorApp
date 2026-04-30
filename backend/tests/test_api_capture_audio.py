import io


def _create_template(client, multipliers: dict[int, float] | None = None) -> int:
    """Create a template with groups using given multipliers (default {1: 80.0})."""
    multipliers = multipliers or {1: 80.0}
    groups = [
        {"index": gi, "label": f"G{gi}", "bet_type": "lo", "multiplier": m}
        for gi, m in sorted(multipliers.items())
    ]
    r = client.post("/api/templates", json={"name": "T", "groups": groups})
    return r.json()["id"]


def _create_capture(client, tid: int, group_provinces: str = '{"1": ["HN"]}') -> int:
    files = {"image": ("n.png", io.BytesIO(b"x"), "image/png")}
    r = client.post("/api/captures", files=files,
                    data={"template_id": str(tid), "group_provinces": group_provinces})
    return r.json()["id"]


def test_audio_upload_creates_audio_group(client):
    tid = _create_template(client)
    cid = _create_capture(client, tid)

    files = {"audio": ("clip.webm", io.BytesIO(b"fake-audio-bytes"), "audio/webm")}
    data = {"group_index": "1"}
    resp = client.post(f"/api/captures/{cid}/audio", files=files, data=data)
    assert resp.status_code == 201, resp.text

    body = resp.json()
    assert body["capture_id"] == cid
    assert body["group_index"] == 1
    assert body["parsed_numbers"] == [23, 5, 105]
    assert body["sum"] == 133
    assert body["multiplier_snapshot"] == 80.0
    assert body["audio_path"].endswith(".webm")


def test_audio_upload_uses_template_group_multiplier(client):
    tid = _create_template(client, multipliers={1: 80.0, 2: 82.0, 3: 14.5})
    cid = _create_capture(client, tid, '{"3": ["DNG", "KH"]}')

    files = {"audio": ("a.webm", io.BytesIO(b"x"), "audio/webm")}
    resp = client.post(f"/api/captures/{cid}/audio", files=files, data={"group_index": "3"})
    assert resp.status_code == 201, resp.text
    assert resp.json()["multiplier_snapshot"] == 14.5


def test_audio_upload_unknown_capture_404(client):
    files = {"audio": ("a.webm", io.BytesIO(b"x"), "audio/webm")}
    resp = client.post("/api/captures/9999/audio", files=files, data={"group_index": "1"})
    assert resp.status_code == 404


def test_audio_upload_invalid_group_index_400(client):
    tid = _create_template(client)  # only group 1 exists
    cid = _create_capture(client, tid)

    files = {"audio": ("a.webm", io.BytesIO(b"x"), "audio/webm")}
    resp = client.post(f"/api/captures/{cid}/audio", files=files, data={"group_index": "99"})
    assert resp.status_code == 400
    assert "group" in resp.json()["detail"].lower()


def test_audio_upload_persists_to_db(client, db_session):
    """Verify the AudioGroup row is actually persisted, not just returned."""
    from app.models import AudioGroup
    tid = _create_template(client)
    cid = _create_capture(client, tid)

    files = {"audio": ("a.webm", io.BytesIO(b"x"), "audio/webm")}
    client.post(f"/api/captures/{cid}/audio", files=files, data={"group_index": "1"})

    rows = db_session.query(AudioGroup).filter(AudioGroup.capture_id == cid).all()
    assert len(rows) == 1
    assert rows[0].sum == 133
    assert rows[0].transcript is not None


def test_audio_upload_multiple_groups_for_same_capture(client, db_session):
    """User can record group 1, then group 2 on same capture; both persist."""
    from app.models import AudioGroup
    tid = _create_template(client, multipliers={1: 80.0, 2: 82.0})
    cid = _create_capture(client, tid, '{"1": ["HN"], "2": ["HN"]}')

    for gi in [1, 2]:
        files = {"audio": ("a.webm", io.BytesIO(b"x"), "audio/webm")}
        resp = client.post(f"/api/captures/{cid}/audio", files=files, data={"group_index": str(gi)})
        assert resp.status_code == 201

    rows = db_session.query(AudioGroup).filter(AudioGroup.capture_id == cid).order_by(AudioGroup.group_index).all()
    assert len(rows) == 2
    assert rows[0].group_index == 1
    assert rows[0].multiplier_snapshot == 80.0
    assert rows[1].group_index == 2
    assert rows[1].multiplier_snapshot == 82.0
