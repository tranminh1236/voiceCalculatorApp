from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.domain.enums import BetType, CaptureStatus


class GroupDef(BaseModel):
    index: int = Field(ge=1)
    label: str
    bet_type: BetType
    multiplier: float = Field(gt=0)
    default_provinces: list[str] = Field(default_factory=list)


class TemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    groups: list[GroupDef] = Field(min_length=1)


class TemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    groups: list[GroupDef]
    created_at: datetime


class ProvinceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    code: str
    region: str
    name: str


class BBoxOut(BaseModel):
    x: float
    y: float
    w: float
    h: float


class OcrNumberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    bbox: BBoxOut
    raw_text: str | None
    raw_value: float | None
    corrected_value: float | None
    confidence: float | None


class CaptureCreateMeta(BaseModel):
    template_id: int
    group_provinces: dict[int, list[str]] = Field(min_length=1)
    writer_name: str | None = None
    note_date: str | None = None
    tags: list[str] | None = None
    notes: str | None = None

    @field_validator("group_provinces")
    @classmethod
    def _validate_group_provinces(cls, v: dict[int, list[str]]) -> dict[int, list[str]]:
        for gi, provs in v.items():
            if not provs:
                raise ValueError(f"group {gi} must have at least one province")
            if any(not c.strip() for c in provs):
                raise ValueError(f"group {gi}: province codes must be non-empty")
        return v


class CaptureOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    template_id: int
    image_path: str
    status: CaptureStatus
    final_value: float | None
    group_provinces: dict[int, list[str]]
    writer_name: str | None
    note_date: str | None
    tags: list[str] | None
    notes: str | None
    ocr_numbers: list[OcrNumberOut] = []
    created_at: datetime
    updated_at: datetime
