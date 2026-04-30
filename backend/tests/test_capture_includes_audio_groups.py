import io


def _create_template(client) -> int:
    r = client.post("/api/templates", json={
        "name": "T",
        "groups": [
            {"index": 1, "label": "G1", "bet_type": "lo", "multiplier": 80.0},
            {"index": 2, "label": "G2", "bet_type": "de", "multiplier": 82.0},
        ],
    })
    return r.json()["id"]


def test_get_capture_includes_audio_groups_and_matches(client):
    tid = _create_template(client)
    files = {"image": ("n.png", io.BytesIO(b"x"), "image/png")}
    r = client.post("/api/captures", files=files,
                    data={"template_id": str(tid), "group_provinces": '{"1": ["HN"], "2": ["HN"]}'})
    cid = r.json()["id"]

    files = {"audio": ("a.webm", io.BytesIO(b"x"), "audio/webm")}
    client.post(f"/api/captures/{cid}/audio", files=files, data={"group_index": "1"})
    files = {"audio": ("a.webm", io.BytesIO(b"x"), "audio/webm")}
    client.post(f"/api/captures/{cid}/audio", files=files, data={"group_index": "2"})

    resp = client.get(f"/api/captures/{cid}")
    assert resp.status_code == 200
    body = resp.json()
    assert "audio_groups" in body
    assert len(body["audio_groups"]) == 2
    indices = sorted(g["group_index"] for g in body["audio_groups"])
    assert indices == [1, 2]
    # Each group has matches embedded
    for g in body["audio_groups"]:
        assert "matches" in g
        assert len(g["matches"]) == 3  # stub yields 3 numbers, each matches an OCR


def test_get_capture_includes_empty_audio_groups_when_none(client):
    tid = _create_template(client)
    files = {"image": ("n.png", io.BytesIO(b"x"), "image/png")}
    r = client.post("/api/captures", files=files,
                    data={"template_id": str(tid), "group_provinces": '{"1": ["HN"]}'})
    cid = r.json()["id"]
    resp = client.get(f"/api/captures/{cid}")
    assert resp.status_code == 200
    assert resp.json()["audio_groups"] == []
