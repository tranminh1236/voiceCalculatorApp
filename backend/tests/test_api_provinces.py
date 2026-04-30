def test_list_provinces_seeded(client, db_session):
    from app.seed import seed_provinces
    seed_provinces(db_session)
    db_session.commit()

    resp = client.get("/api/provinces")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 3
    codes = {p["code"] for p in data}
    assert {"HN", "DNG", "KH"}.issubset(codes)


def test_list_provinces_filter_by_region(client, db_session):
    from app.seed import seed_provinces
    seed_provinces(db_session)
    db_session.commit()

    resp = client.get("/api/provinces?region=mb")
    assert resp.status_code == 200
    data = resp.json()
    assert all(p["region"] == "mb" for p in data)
