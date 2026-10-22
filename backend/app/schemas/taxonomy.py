"""Taxonomy API contracts."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    description: str
    sort_order: int


class CategoryListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[CategoryResponse]


class TagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    tag_group: str


class TagListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[TagResponse]
