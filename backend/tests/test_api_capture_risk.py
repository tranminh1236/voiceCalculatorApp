import io
import json


def _create_template(client, multipliers: dict[int, float]) -> int:
    groups = [
        {"index": gi, "label": f"G{gi}", "bet_type": "lo", "multiplier": m}
        for gi, m in sorted(multipliers.items())
    ]
    r = client.post("/api/templates", json={"name": "T", "groups": groups})
    return r.json()["id"]


def _create_capture_with_audio(client, multipliers: dict[int, float], group_provinces: dict[int, list[str]]):
    tid = _create_template(client, multipliers)
    files = {"image": ("n.png", io.BytesIO(b"x"), "image/png")}
    gp_str = json.dumps({str(k): v for k, v in group_provinces.items()})
    r = client.post("/api/captures", files=files,
                    data={"template_id": str(tid), "group_provinces": gp_str})
    cid = r.json()["id"]
    for gi in multipliers.keys():
        files = {"audio": ("a.webm", io.BytesIO(b"x"), "audio/webm")}
        client.post(f"/api/captures/{cid}/audio", files=files, data={"group_index": str(gi)})
    return cid


def test_risk_basic(client):
    """Stub STT yields parsed_numbers=[23,5,105]. With multiplier 80, 1 đài HN:
    capital = 23+5+105 = 133. payout per number = stake × 80.
    Entries: 23 → payout 1840, net 1707, take. 5 → payout 400, net 267, take. 105 → payout 8400, net 8267, take.
    """
    cid = _create_capture_with_audio(client, {1: 80.0}, {1: ["HN"]})
    resp = client.get(f"/api/captures/{cid}/risk")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["capture_id"] == cid
    assert body["total_capital"] == 133.0
    assert body["threshold"] == 0.0
    assert len(body["entries"]) == 3
    by_stake = {e["stake"]: e for e in body["entries"]}
    assert by_stake[23.0]["payout_if_hits"] == 1840.0
    assert by_stake[23.0]["recommendation"] == "take"
    assert body["take_count"] == 3
    assert body["pass_count"] == 0


def test_risk_with_threshold(client):
    """High threshold should flip some takes to passes."""
    cid = _create_capture_with_audio(client, {1: 80.0}, {1: ["HN"]})
    # threshold=2000: 23 → net 1707 < 2000 → pass; 5 → net 267 → pass; 105 → net 8267 → take
    resp = client.get(f"/api/captures/{cid}/risk?threshold=2000")
    assert resp.status_code == 200
    body = resp.json()
    assert body["threshold"] == 2000.0
    by_stake = {e["stake"]: e for e in body["entries"]}
    assert by_stake[23.0]["recommendation"] == "pass"
    assert by_stake[5.0]["recommendation"] == "pass"
    assert by_stake[105.0]["recommendation"] == "take"
    assert body["take_count"] == 1
    assert body["pass_count"] == 2


def test_risk_multi_province_doubles_capital(client):
    """provinces=[DNG,KH] → effective_stake doubles for that group."""
    cid = _create_capture_with_audio(client, {1: 80.0}, {1: ["DNG", "KH"]})
    resp = client.get(f"/api/captures/{cid}/risk")
    body = resp.json()
    assert body["total_capital"] == 133.0 * 2
    assert all(e["num_provinces"] == 2 for e in body["entries"])
    assert all(e["effective_stake"] == e["stake"] * 2 for e in body["entries"])


def test_risk_unknown_capture_404(client):
    resp = client.get("/api/captures/9999/risk")
    assert resp.status_code == 404


def test_risk_capture_with_no_audio_returns_empty(client):
    """Capture with no audio → empty entries, capital 0."""
    tid = _create_template(client, {1: 80.0})
    files = {"image": ("n.png", io.BytesIO(b"x"), "image/png")}
    r = client.post("/api/captures", files=files,
                    data={"template_id": str(tid), "group_provinces": '{"1": ["HN"]}'})
    cid = r.json()["id"]

    resp = client.get(f"/api/captures/{cid}/risk")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_capital"] == 0.0
    assert body["entries"] == []
