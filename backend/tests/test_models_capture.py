import json
import pytest
from sqlalchemy.exc import IntegrityError
from app.models import Template, Capture, OcrNumber, AudioGroup, Match


def _mk_template(db_session) -> Template:
    t = Template(name="T1", groups_json=json.dumps([
        {"index": 1, "label": "G1", "bet_type": "lo", "multiplier": 80.0},
    ]))
    db_session.add(t)
    db_session.commit()
    return t


def test_create_capture(db_session):
    t = _mk_template(db_session)
    c = Capture(
        template_id=t.id,
        image_path="/tmp/x.jpg",
        status="draft",
        group_provinces_json=json.dumps({"1": ["HN"]}),
    )
    db_session.add(c)
    db_session.commit()
    assert c.id is not None
    assert c.status == "draft"


def test_capture_invalid_status_raises(db_session):
    t = _mk_template(db_session)
    c = Capture(
        template_id=t.id,
        image_path="/tmp/x.jpg",
        status="bogus",
        group_provinces_json=json.dumps({"1": ["HN"]}),
    )
    db_session.add(c)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_ocr_number_cascade_delete(db_session):
    t = _mk_template(db_session)
    c = Capture(template_id=t.id, image_path="/tmp/x.jpg", status="draft",
                group_provinces_json=json.dumps({"1": ["HN"]}))
    db_session.add(c); db_session.commit()
    n = OcrNumber(capture_id=c.id, bbox_x=0, bbox_y=0, bbox_w=10, bbox_h=10, raw_text="23", raw_value=23.0, confidence=0.9)
    db_session.add(n); db_session.commit()
    db_session.delete(c); db_session.commit()
    assert db_session.query(OcrNumber).count() == 0


def test_match_allows_duplicate_pair(db_session):
    """Same OCR can match same audio_group multiple times (rule: 2a + 2c)."""
    t = _mk_template(db_session)
    c = Capture(template_id=t.id, image_path="/tmp/x.jpg", status="draft",
                group_provinces_json=json.dumps({"1": ["HN"]}))
    db_session.add(c); db_session.commit()
    n = OcrNumber(capture_id=c.id, bbox_x=0, bbox_y=0, bbox_w=10, bbox_h=10, raw_text="23", raw_value=23.0, confidence=0.9)
    g = AudioGroup(capture_id=c.id, group_index=1, audio_path="/tmp/a.webm", multiplier_snapshot=80.0)
    db_session.add_all([n, g]); db_session.commit()
    m1 = Match(ocr_number_id=n.id, audio_group_id=g.id, confidence=1.0, source="auto")
    m2 = Match(ocr_number_id=n.id, audio_group_id=g.id, confidence=1.0, source="auto")
    db_session.add_all([m1, m2]); db_session.commit()
    assert db_session.query(Match).count() == 2
