def test_create_template(client):
    body = {
        "name": "Lô-Đề-Xiên",
        "groups": [
            {"index": 1, "label": "Lô", "bet_type": "lo", "multiplier": 80.0},
            {"index": 2, "label": "Đề", "bet_type": "de", "multiplier": 82.0},
            {"index": 3, "label": "Xiên 2", "bet_type": "xien_2", "multiplier": 14.5},
        ],
    }
    resp = client.post("/api/templates", json=body)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["id"] >= 1
    assert data["name"] == "Lô-Đề-Xiên"
    assert len(data["groups"]) == 3
    assert data["groups"][1]["bet_type"] == "de"


def test_list_templates(client):
    client.post("/api/templates", json={
        "name": "T1",
        "groups": [{"index": 1, "label": "G", "bet_type": "lo", "multiplier": 80.0}],
    })
    client.post("/api/templates", json={
        "name": "T2",
        "groups": [{"index": 1, "label": "G", "bet_type": "de", "multiplier": 82.0}],
    })
    resp = client.get("/api/templates")
    assert resp.status_code == 200
    names = [t["name"] for t in resp.json()]
    assert "T1" in names and "T2" in names


def test_get_template_by_id(client):
    r = client.post("/api/templates", json={
        "name": "T", "groups": [{"index": 1, "label": "G", "bet_type": "lo", "multiplier": 80.0}],
    })
    tid = r.json()["id"]
    resp = client.get(f"/api/templates/{tid}")
    assert resp.status_code == 200
    assert resp.json()["id"] == tid


def test_get_template_404(client):
    resp = client.get("/api/templates/999")
    assert resp.status_code == 404


def test_create_template_invalid_bet_type_400(client):
    resp = client.post("/api/templates", json={
        "name": "X", "groups": [{"index": 1, "label": "G", "bet_type": "bogus", "multiplier": 1.0}],
    })
    assert resp.status_code == 422
