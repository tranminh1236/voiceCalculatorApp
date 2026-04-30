from datetime import datetime, timezone
from sqlalchemy import (
    CheckConstraint, ForeignKey, Integer, Float, String, Text, UniqueConstraint, DateTime
)
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Province(Base):
    __tablename__ = "provinces"
    code: Mapped[str] = mapped_column(String(8), primary_key=True)
    region: Mapped[str] = mapped_column(String(2), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    __table_args__ = (
        CheckConstraint("region IN ('mb','mt','mn')", name="ck_province_region"),
    )


class Template(Base):
    __tablename__ = "templates"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    groups_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)


class Capture(Base):
    __tablename__ = "captures"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("templates.id"), nullable=False)
    image_path: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    final_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    group_provinces_json: Mapped[str] = mapped_column(Text, nullable=False)
    writer_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    note_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    tags_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)
    __table_args__ = (
        CheckConstraint("status IN ('draft','final','settled')", name="ck_capture_status"),
    )


class OcrNumber(Base):
    __tablename__ = "ocr_numbers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    capture_id: Mapped[int] = mapped_column(ForeignKey("captures.id", ondelete="CASCADE"), nullable=False)
    bbox_x: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_y: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_w: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_h: Mapped[float] = mapped_column(Float, nullable=False)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    corrected_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)


class AudioGroup(Base):
    __tablename__ = "audio_groups"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    capture_id: Mapped[int] = mapped_column(ForeignKey("captures.id", ondelete="CASCADE"), nullable=False)
    group_index: Mapped[int] = mapped_column(Integer, nullable=False)
    audio_path: Mapped[str] = mapped_column(Text, nullable=False)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsed_numbers_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    sum: Mapped[float | None] = mapped_column(Float, nullable=True)
    multiplier_snapshot: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)


class Match(Base):
    __tablename__ = "matches"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ocr_number_id: Mapped[int] = mapped_column(ForeignKey("ocr_numbers.id", ondelete="CASCADE"), nullable=False)
    audio_group_id: Mapped[int] = mapped_column(ForeignKey("audio_groups.id", ondelete="CASCADE"), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(8), nullable=False)
    __table_args__ = (
        CheckConstraint("source IN ('auto','manual')", name="ck_match_source"),
    )
