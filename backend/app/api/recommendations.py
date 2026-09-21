"""Recommendation API: personalized content and ad recommendations."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import User
from app.api.deps import get_current_user
from app.services.recommendation_service import (
    get_ad_recommendations,
    get_content_recommendations,
)

router = APIRouter(prefix="/api/recommendations", tags=["Recommendations"])


@router.get("/ads")
async def recommend_ads(
    top_n: int = Query(5, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get personalized ad recommendations for the current user.

    The recommendation pipeline:
    1. Filters eligible ads (active campaigns, valid dates, budget, frequency caps)
    2. Scores each candidate using user affinity, engagement, CTR, recency, bid
    3. Ranks by score and applies diversity constraints
    4. Returns top-N recommendations with scores and algorithm used

    Cold-start users get popularity-based recommendations.
    Established users get personalized or ML-based recommendations.
    """
    result = await get_ad_recommendations(db, current_user.id, top_n)
    return result


@router.get("/content")
async def recommend_content(
    top_n: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get personalized content recommendations.
    Returns both personalized (based on user interests) and trending content.
    """
    result = await get_content_recommendations(db, current_user.id, top_n)
    return result
