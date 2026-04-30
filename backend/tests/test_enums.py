from app.domain.enums import BetType, CaptureStatus, Region, MatchSource


def test_bet_type_members():
    assert BetType.LO.value == "lo"
    assert BetType.DE.value == "de"
    assert BetType.XIEN_2.value == "xien_2"
    assert BetType.XIEN_3.value == "xien_3"
    assert BetType.XIEN_4.value == "xien_4"
    assert BetType.BA_CANG.value == "3cang"
    assert BetType.XIEN_QUAY.value == "xien_quay"


def test_capture_status_members():
    assert CaptureStatus.DRAFT.value == "draft"
    assert CaptureStatus.FINAL.value == "final"
    assert CaptureStatus.SETTLED.value == "settled"


def test_region_members():
    assert Region.MB.value == "mb"
    assert Region.MT.value == "mt"
    assert Region.MN.value == "mn"


def test_match_source_members():
    assert MatchSource.AUTO.value == "auto"
    assert MatchSource.MANUAL.value == "manual"
