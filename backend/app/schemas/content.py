"""Pydantic schemas for content."""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class CategoryResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str] = None

    model_config = {"from_attributes": True}


class ContentResponse(BaseModel):
    id: int
    title: str
    description: str
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    popularity_score: float
    created_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}


class ContentListResponse(BaseModel):
    items: List[ContentResponse]
    total: int
    page: int
    page_size: int
