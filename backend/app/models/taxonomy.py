"""Database-configured taxonomy for categories and review tags."""

from __future__ import annotations

from sqlalchemy import Boolean, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class TaxonomyCategory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "taxonomy_categories"
    __table_args__ = (UniqueConstraint("code", name="uq_taxonomy_categories_code"),)

    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class TaxonomyTag(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "taxonomy_tags"
    __table_args__ = (UniqueConstraint("code", name="uq_taxonomy_tags_code"),)

    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    tag_group: Mapped[str] = mapped_column(String(64), nullable=False, default="pain_type")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
