import io


def test_can_fetch_uploaded_image(client):
    """After POST /api/captures, the saved image should be retrievable via /media/captures/<filename>."""
    # Create template + capture
    r = client.post("/api/templates", json={
        "name": "T", "groups": [{"index": 1, "label": "G", "bet_type": "lo", "multiplier": 80.0}],
    })
    tid = r.json()["id"]

    img_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    files = {"image": ("test.png", io.BytesIO(img_bytes), "image/png")}
    r = client.post("/api/captures", files=files,
                    data={"template_id": str(tid), "group_provinces": '{"1": ["HN"]}'})
    cap = r.json()
    img_path = cap["image_path"]
    # img_path is absolute filesystem path; we need just the filename
    fname = img_path.split("/")[-1]

    resp = client.get(f"/media/captures/{fname}")
    assert resp.status_code == 200
    assert resp.content.startswith(b"\x89PNG")


def test_unknown_media_404(client):
    resp = client.get("/media/captures/does-not-exist.png")
    assert resp.status_code == 404
