import json
from app.models import Province, Template


def test_create_province(db_session):
    p = Province(code="HN", region="mb", name="Hà Nội")
    db_session.add(p)
    db_session.commit()
    fetched = db_session.get(Province, "HN")
    assert fetched.name == "Hà Nội"
    assert fetched.region == "mb"


def test_create_template_with_groups(db_session):
    groups = [
        {"index": 1, "label": "Lô", "bet_type": "lo", "multiplier": 80.0},
        {"index": 2, "label": "Đề", "bet_type": "de", "multiplier": 82.0},
        {"index": 3, "label": "Xiên 2", "bet_type": "xien_2", "multiplier": 14.5},
    ]
    t = Template(name="Lô-Đề-Xiên", groups_json=json.dumps(groups))
    db_session.add(t)
    db_session.commit()
    assert t.id is not None
    loaded_groups = json.loads(t.groups_json)
    assert len(loaded_groups) == 3
    assert loaded_groups[1]["bet_type"] == "de"
