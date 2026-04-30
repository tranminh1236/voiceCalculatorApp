from app.models import Province
from app.seed import seed_provinces, PROVINCES


def test_provinces_constant_has_all_three_regions():
    regions = {p["region"] for p in PROVINCES}
    assert regions == {"mb", "mt", "mn"}


def test_provinces_has_required_codes():
    codes = {p["code"] for p in PROVINCES}
    assert {"HN", "DNG", "KH"}.issubset(codes)


def test_seed_inserts_all(db_session):
    seed_provinces(db_session)
    db_session.commit()
    n = db_session.query(Province).count()
    assert n == len(PROVINCES)


def test_seed_idempotent(db_session):
    seed_provinces(db_session)
    db_session.commit()
    seed_provinces(db_session)
    db_session.commit()
    n = db_session.query(Province).count()
    assert n == len(PROVINCES)
