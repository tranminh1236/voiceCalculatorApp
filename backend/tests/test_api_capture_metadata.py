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


def test_patch_metadata_full(client):
    tid = _create_template(client)
    cid = _create_capture(client, tid)

    resp = client.patch(f"/api/captures/{cid}/metadata", json={
        "writer_name": "Tom",
        "note_date": "2026-04-29",
        "tags": ["weekly", "lottery"],
        "notes": "Test note",
    })
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["writer_name"] == "Tom"
    assert body["note_date"] == "2026-04-29"
    assert body["tags"] == ["weekly", "lottery"]
    assert body["notes"] == "Test note"


def test_patch_metadata_partial_keeps_existing(client):
    tid = _create_template(client)
    cid = _create_capture(client, tid)
    client.patch(f"/api/captures/{cid}/metadata", json={
        "writer_name": "A", "note_date": "2026-04-01", "tags": ["x"], "notes": "n",
    })

    # Only update writer_name
    resp = client.patch(f"/api/captures/{cid}/metadata", json={"writer_name": "B"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["writer_name"] == "B"
    # Other fields unchanged
    assert body["note_date"] == "2026-04-01"
    assert body["tags"] == ["x"]
    assert body["notes"] == "n"


def test_patch_metadata_clear_with_null(client):
    """Sending `null` should set field to null (clear)."""
    tid = _create_template(client)
    cid = _create_capture(client, tid)
    client.patch(f"/api/captures/{cid}/metadata", json={"writer_name": "Tom"})

    # Note: distinguishing "not provided" vs "explicitly null" requires use of model_fields_set.
    # We send writer_name explicitly as null:
    resp = client.patch(f"/api/captures/{cid}/metadata", json={"writer_name": None})
    assert resp.status_code == 200
    assert resp.json()["writer_name"] is None


def test_patch_metadata_unknown_capture_404(client):
    resp = client.patch("/api/captures/9999/metadata", json={"writer_name": "x"})
    assert resp.status_code == 404
