import pytest
from pydantic import ValidationError
from app.schemas import (
    GroupDef, TemplateCreate, TemplateOut,
    CaptureCreateMeta, CaptureOut, OcrNumberOut, BBoxOut,
    ProvinceOut,
)


def test_group_def_valid_with_default_provinces():
    g = GroupDef(index=1, label="Lô", bet_type="lo", multiplier=80.0, default_provinces=["HN"])
    assert g.bet_type == "lo"
    assert g.default_provinces == ["HN"]


def test_group_def_default_provinces_optional_defaults_empty():
    g = GroupDef(index=1, label="Lô", bet_type="lo", multiplier=80.0)
    assert g.default_provinces == []


def test_group_def_invalid_bet_type():
    with pytest.raises(ValidationError):
        GroupDef(index=1, label="x", bet_type="bogus", multiplier=1.0)


def test_template_create_with_groups():
    t = TemplateCreate(name="T", groups=[
        GroupDef(index=1, label="L", bet_type="lo", multiplier=80.0, default_provinces=["HN"]),
        GroupDef(index=2, label="D", bet_type="de", multiplier=82.0, default_provinces=["HN"]),
    ])
    assert len(t.groups) == 2


def test_capture_create_meta_minimal():
    m = CaptureCreateMeta(template_id=1, group_provinces={1: ["HN"]})
    assert m.group_provinces == {1: ["HN"]}
    assert m.writer_name is None


def test_capture_create_meta_requires_at_least_one_group():
    with pytest.raises(ValidationError):
        CaptureCreateMeta(template_id=1, group_provinces={})


def test_capture_create_meta_rejects_empty_province_list_per_group():
    with pytest.raises(ValidationError):
        CaptureCreateMeta(template_id=1, group_provinces={1: []})


def test_province_out():
    p = ProvinceOut(code="HN", region="mb", name="Hà Nội")
    assert p.code == "HN"
