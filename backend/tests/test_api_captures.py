import io


def _create_template(client) -> int:
    r = client.post("/api/templates", json={
        "name": "T",
        "groups": [{"index": 1, "label": "G", "bet_type": "lo", "multiplier": 80.0}],
    })
    return r.json()["id"]


def test_create_capture_with_stub_ocr(client):
    tid = _create_template(client)
    img_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    files = {"image": ("note.png", io.BytesIO(img_bytes), "image/png")}
    data = {"template_id": str(tid), "group_provinces": '{"1": ["HN"]}'}
    resp = client.post("/api/captures", files=files, data=data)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["id"] >= 1
    assert body["status"] == "draft"
    assert body["group_provinces"] == {"1": ["HN"]}
    assert len(body["ocr_numbers"]) >= 1
    assert body["ocr_numbers"][0]["raw_value"] is not None


def test_create_capture_mixed_per_group_provinces(client):
    """Group 1 = HN only; Group 3 = DNG+KH (matches spec §17 worked example)."""
    tid = _create_template(client)
    files = {"image": ("n.png", io.BytesIO(b"x"), "image/png")}
    data = {
        "template_id": str(tid),
        "group_provinces": '{"1": ["HN"], "2": ["HN"], "3": ["DNG", "KH"]}',
    }
    resp = client.post("/api/captures", files=files, data=data)
    assert resp.status_code == 201, resp.text
    gp = resp.json()["group_provinces"]
    assert gp == {"1": ["HN"], "2": ["HN"], "3": ["DNG", "KH"]}


def test_create_capture_invalid_group_provinces_json(client):
    tid = _create_template(client)
    files = {"image": ("n.png", io.BytesIO(b"x"), "image/png")}
    resp = client.post("/api/captures", files=files,
                       data={"template_id": str(tid), "group_provinces": "not-json"})
    assert resp.status_code == 422


def test_create_capture_empty_group_provinces_rejected(client):
    tid = _create_template(client)
    files = {"image": ("n.png", io.BytesIO(b"x"), "image/png")}
    resp = client.post("/api/captures", files=files,
                       data={"template_id": str(tid), "group_provinces": "{}"})
    assert resp.status_code == 422


def test_list_captures(client):
    tid = _create_template(client)
    for _ in range(2):
        files = {"image": ("n.png", io.BytesIO(b"x"), "image/png")}
        client.post("/api/captures", files=files,
                    data={"template_id": str(tid), "group_provinces": '{"1": ["HN"]}'})

    resp = client.get("/api/captures")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_get_capture_by_id(client):
    tid = _create_template(client)
    files = {"image": ("n.png", io.BytesIO(b"x"), "image/png")}
    r = client.post("/api/captures", files=files,
                    data={"template_id": str(tid), "group_provinces": '{"1": ["HN"]}'})
    cid = r.json()["id"]

    resp = client.get(f"/api/captures/{cid}")
    assert resp.status_code == 200
    assert resp.json()["id"] == cid


def test_capture_unknown_template_404(client):
    files = {"image": ("n.png", io.BytesIO(b"x"), "image/png")}
    resp = client.post("/api/captures", files=files,
                       data={"template_id": "999", "group_provinces": '{"1": ["HN"]}'})
    assert resp.status_code == 404
