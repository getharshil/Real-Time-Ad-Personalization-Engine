"""Pydantic schemas for recommendations and ads."""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class AdResponse(BaseModel):
    id: int
    title: str
    description: str
    cta_text: str
    landing_url: Optional[str] = None
    category_name: Optional[str] = None
    score: float = 0.0
    algorithm: str = "popularity"

    model_config = {"from_attributes": True}


class AdRecommendationResponse(BaseModel):
    user_id: int
    recommendations: List[AdResponse]
    algorithm: str
    is_cold_start: bool


class ContentRecommendationResponse(BaseModel):
    user_id: int
    personalized: list
    trending: list


class AdImpressionCreate(BaseModel):
    session_id: Optional[int] = None
    recommendation_score: Optional[float] = None
    source: str = "recommendation"


class AdClickCreate(BaseModel):
    impression_id: Optional[int] = None
