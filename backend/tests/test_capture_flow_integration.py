"""Full capture flow end-to-end via HTTP. Uses stub OCR + stub STT."""
import io
import json


def test_full_capture_flow(client, db_session):
    # 1. Create template with 2 groups (lô + đề)
    r = client.post("/api/templates", json={
        "name": "Lô-Đề-MB",
        "groups": [
            {"index": 1, "label": "Lô", "bet_type": "lo", "multiplier": 80.0, "default_provinces": ["HN"]},
            {"index": 2, "label": "Đề", "bet_type": "de", "multiplier": 82.0, "default_provinces": ["HN"]},
        ],
    })
    assert r.status_code == 201
    tid = r.json()["id"]

    # 2. Upload image (creates capture + 3 stub OCR rows: 23, 5, 105)
    files = {"image": ("note.png", io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32), "image/png")}
    r = client.post("/api/captures", files=files, data={
        "template_id": str(tid),
        "group_provinces": json.dumps({"1": ["HN"], "2": ["HN"]}),
        "writer_name": "Tom",
        "note_date": "2026-04-29",
    })
    assert r.status_code == 201
    cap = r.json()
    cid = cap["id"]
    assert cap["status"] == "draft"
    assert cap["writer_name"] == "Tom"
    assert len(cap["ocr_numbers"]) == 3
    ocr_ids = [n["id"] for n in cap["ocr_numbers"]]

    # 3. Correct one OCR value (23 → 24)
    r = client.patch(f"/api/captures/{cid}/ocr/{ocr_ids[0]}", json={"corrected_value": 24.0})
    assert r.status_code == 200
    assert r.json()["corrected_value"] == 24.0

    # 4. Upload audio for group 1 (stub yields [23, 5, 105]; 23 no longer matches because we corrected to 24)
    files = {"audio": ("a1.webm", io.BytesIO(b"x"), "audio/webm")}
    r = client.post(f"/api/captures/{cid}/audio", files=files, data={"group_index": "1"})
    assert r.status_code == 201
    g1 = r.json()
    # 23 should be unmatched (we corrected it to 24); 5 + 105 still match
    matched_count = len(g1["matches"])
    assert matched_count == 2

    # 5. Manually add a match: link audio group 1's 23 to the (now-24) OCR row
    r = client.post(f"/api/captures/{cid}/matches", json={
        "ocr_number_id": ocr_ids[0],
        "audio_group_id": g1["id"],
        "action": "add",
    })
    assert r.status_code == 201
    assert r.json()["source"] == "manual"

    # 6. Upload audio for group 2
    files = {"audio": ("a2.webm", io.BytesIO(b"x"), "audio/webm")}
    r = client.post(f"/api/captures/{cid}/audio", files=files, data={"group_index": "2"})
    assert r.status_code == 201

    # 7. Finalize
    r = client.post(f"/api/captures/{cid}/finalize")
    assert r.status_code == 200
    final = r.json()
    assert final["status"] == "final"
    # Both groups have stub sum = 133. final = 133*80 + 133*82 = 21306
    assert final["final_value"] == 133 * 80 + 133 * 82

    # 8. GET capture: verify embedded structure
    r = client.get(f"/api/captures/{cid}")
    assert r.status_code == 200
    full = r.json()
    assert full["status"] == "final"
    assert len(full["audio_groups"]) == 2
    assert all("matches" in g for g in full["audio_groups"])
    # Group 1 should have 3 matches now (2 auto + 1 manual)
    g1_full = next(g for g in full["audio_groups"] if g["group_index"] == 1)
    assert len(g1_full["matches"]) == 3
    # Group 2 has 2 auto matches (ocr_ids[0] was corrected to 24, so audio 23 doesn't match it)
    g2_full = next(g for g in full["audio_groups"] if g["group_index"] == 2)
    assert len(g2_full["matches"]) == 2
