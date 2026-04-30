import io


def _create_template(client) -> int:
    r = client.post("/api/templates", json={
        "name": "T",
        "groups": [{"index": 1, "label": "G", "bet_type": "lo", "multiplier": 80.0}],
    })
    return r.json()["id"]


def _create_capture(client, tid: int) -> tuple[int, list[int]]:
    files = {"image": ("n.png", io.BytesIO(b"x"), "image/png")}
    r = client.post("/api/captures", files=files,
                    data={"template_id": str(tid), "group_provinces": '{"1": ["HN"]}'})
    body = r.json()
    return body["id"], [n["id"] for n in body["ocr_numbers"]]


def test_patch_ocr_value(client, db_session):
    """Sửa OCR value 23 → 24."""
    from app.models import OcrNumber
    tid = _create_template(client)
    cid, ocr_ids = _create_capture(client, tid)
    target = ocr_ids[0]

    resp = client.patch(f"/api/captures/{cid}/ocr/{target}", json={"corrected_value": 24.0})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["id"] == target
    assert body["corrected_value"] == 24.0
    assert body["raw_value"] == 23.0  # raw unchanged

    # DB sanity
    n = db_session.get(OcrNumber, target)
    assert n.corrected_value == 24.0


def test_patch_ocr_clear_correction(client):
    tid = _create_template(client)
    cid, ocr_ids = _create_capture(client, tid)
    target = ocr_ids[0]
    client.patch(f"/api/captures/{cid}/ocr/{target}", json={"corrected_value": 999.0})

    resp = client.patch(f"/api/captures/{cid}/ocr/{target}", json={"corrected_value": None})
    assert resp.status_code == 200
    assert resp.json()["corrected_value"] is None


def test_patch_ocr_unknown_capture_404(client):
    resp = client.patch("/api/captures/9999/ocr/1", json={"corrected_value": 5.0})
    assert resp.status_code == 404


def test_patch_ocr_unknown_ocr_id_404(client):
    tid = _create_template(client)
    cid, _ = _create_capture(client, tid)
    resp = client.patch(f"/api/captures/{cid}/ocr/99999", json={"corrected_value": 5.0})
    assert resp.status_code == 404


def test_patch_ocr_id_belonging_to_other_capture_404(client):
    """OCR id exists but belongs to a different capture → 404."""
    tid = _create_template(client)
    cid_a, ocr_a = _create_capture(client, tid)
    cid_b, _ = _create_capture(client, tid)
    # Try to patch ocr_a's id via cid_b
    resp = client.patch(f"/api/captures/{cid_b}/ocr/{ocr_a[0]}", json={"corrected_value": 5.0})
    assert resp.status_code == 404
