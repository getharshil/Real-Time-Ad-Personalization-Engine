"""Pydantic schemas for user profile and analytics."""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, List


class UserInterestResponse(BaseModel):
    category: str
    affinity_score: float
    interaction_count: int

    model_config = {"from_attributes": True}


class UserProfileResponse(BaseModel):
    user_id: int
    username: str
    interests: List[UserInterestResponse]
    engagement_score: float
    preferred_categories: List[str]
    total_events: int
    is_cold_start: bool


class UserAnalyticsResponse(BaseModel):
    user_id: int
    total_sessions: int
    total_events: int
    content_views: int
    ad_impressions: int
    ad_clicks: int
    ctr: float
    most_viewed_categories: List[Dict[str, any]]
    avg_session_duration_seconds: Optional[float] = None
    recent_interests: List[str]


class PlatformOverviewResponse(BaseModel):
    total_users: int
    active_users: int
    total_sessions: int
    total_events: int
    total_impressions: int
    total_clicks: int
    overall_ctr: float
    total_content: int
    total_ads: int
    total_campaigns: int


class CampaignAnalyticsResponse(BaseModel):
    campaign_id: int
    campaign_name: str
    advertiser_name: str
    impressions: int
    clicks: int
    ctr: float
    budget: float
    spent: float


class CategoryAnalyticsResponse(BaseModel):
    category_name: str
    content_views: int
    ad_impressions: int
    ad_clicks: int
    engagement_score: float
