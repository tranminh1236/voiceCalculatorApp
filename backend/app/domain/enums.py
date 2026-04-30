from enum import Enum


class BetType(str, Enum):
    LO = "lo"
    DE = "de"
    XIEN_2 = "xien_2"
    XIEN_3 = "xien_3"
    XIEN_4 = "xien_4"
    BA_CANG = "3cang"
    XIEN_QUAY = "xien_quay"


class CaptureStatus(str, Enum):
    DRAFT = "draft"
    FINAL = "final"
    SETTLED = "settled"


class Region(str, Enum):
    MB = "mb"
    MT = "mt"
    MN = "mn"


class MatchSource(str, Enum):
    AUTO = "auto"
    MANUAL = "manual"
