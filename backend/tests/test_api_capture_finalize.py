import io


def _create_template_multi(client, multipliers: dict[int, float]) -> int:
    groups = [
        {"index": gi, "label": f"G{gi}", "bet_type": "lo", "multiplier": m}
        for gi, m in sorted(multipliers.items())
    ]
    r = client.post("/api/templates", json={"name": "T", "groups": groups})
    return r.json()["id"]


def _capture_with_groups(client, tid: int, group_indices: list[int]) -> int:
    files = {"image": ("n.png", io.BytesIO(b"x"), "image/png")}
    gp_dict = {str(gi): ["HN"] for gi in group_indices}
    import json as _j
    r = client.post("/api/captures", files=files,
                    data={"template_id": str(tid), "group_provinces": _j.dumps(gp_dict)})
    return r.json()["id"]


def _upload_audio(client, cid: int, group_index: int):
    files = {"audio": ("a.webm", io.BytesIO(b"x"), "audio/webm")}
    return client.post(f"/api/captures/{cid}/audio", files=files, data={"group_index": str(group_index)})


def test_finalize_single_group(client):
    """1 group with multiplier 80 + sum 133 (stub) → final_value = 133*80 = 10640."""
    tid = _create_template_multi(client, {1: 80.0})
    cid = _capture_with_groups(client, tid, [1])
    _upload_audio(client, cid, 1)

    resp = client.post(f"/api/captures/{cid}/finalize")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "final"
    assert body["final_value"] == 133 * 80


def test_finalize_multi_group(client):
    """3 groups with multipliers 80, 82, 14.5 — each gets stub sum 133."""
    tid = _create_template_multi(client, {1: 80.0, 2: 82.0, 3: 14.5})
    cid = _capture_with_groups(client, tid, [1, 2, 3])
    for gi in [1, 2, 3]:
        _upload_audio(client, cid, gi)

    resp = client.post(f"/api/captures/{cid}/finalize")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["final_value"] == 133 * 80 + 133 * 82 + 133 * 14.5


def test_finalize_with_no_audio_groups_400(client):
    tid = _create_template_multi(client, {1: 80.0})
    cid = _capture_with_groups(client, tid, [1])

    resp = client.post(f"/api/captures/{cid}/finalize")
    assert resp.status_code == 400


def test_finalize_unknown_capture_404(client):
    resp = client.post("/api/captures/9999/finalize")
    assert resp.status_code == 404


def test_finalize_idempotent_returns_400_for_already_final(client):
    tid = _create_template_multi(client, {1: 80.0})
    cid = _capture_with_groups(client, tid, [1])
    _upload_audio(client, cid, 1)
    client.post(f"/api/captures/{cid}/finalize")
    resp = client.post(f"/api/captures/{cid}/finalize")
    assert resp.status_code == 400
