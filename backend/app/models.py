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
