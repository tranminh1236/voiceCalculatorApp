import json
import datetime as dt
import pytest
from sqlalchemy.exc import IntegrityError
from app.models import Province, Template, Capture, LotteryDraw, CaptureResult


def _setup_basic(db_session):
    p = Province(code="HN", region="mb", name="Hà Nội")
    t = Template(name="T", groups_json=json.dumps([{"index": 1, "label": "G", "bet_type": "lo", "multiplier": 80.0}]))
    db_session.add_all([p, t]); db_session.commit()
    return p, t


def test_create_lottery_draw(db_session):
    _setup_basic(db_session)
    d = LotteryDraw(
        province_code="HN",
        draw_date="2026-04-29",
        prizes_json=json.dumps({"DB": ["86569"]}),
        tails_2d_json=json.dumps([69, 20, 44]),
        special_tail_2d=69,
    )
    db_session.add(d); db_session.commit()
    assert d.id is not None


def test_lottery_draw_unique_province_date(db_session):
    _setup_basic(db_session)
    d1 = LotteryDraw(province_code="HN", draw_date="2026-04-29",
                     prizes_json="{}", tails_2d_json="[]", special_tail_2d=0)
    d2 = LotteryDraw(province_code="HN", draw_date="2026-04-29",
                     prizes_json="{}", tails_2d_json="[]", special_tail_2d=0)
    db_session.add(d1); db_session.commit()
    db_session.add(d2)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_capture_result_unique_per_capture(db_session):
    _, t = _setup_basic(db_session)
    c = Capture(template_id=t.id, image_path="/x", status="final", group_provinces_json=json.dumps({"1": ["HN"]}))
    db_session.add(c); db_session.commit()
    r1 = CaptureResult(capture_id=c.id, hits_json="{}", total_stake=0, winning_total_payout=0, profit_loss=0,
                       settled_at=dt.datetime.now(dt.timezone.utc))
    db_session.add(r1); db_session.commit()
    r2 = CaptureResult(capture_id=c.id, hits_json="{}", total_stake=0, winning_total_payout=0, profit_loss=0,
                       settled_at=dt.datetime.now(dt.timezone.utc))
    db_session.add(r2)
    with pytest.raises(IntegrityError):
        db_session.commit()
