"""Admin analytics API: platform-wide metrics, campaign analytics, category analytics."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.analytics_service import (
    get_platform_overview,
    get_campaign_analytics,
    get_category_analytics,
)

router = APIRouter(prefix="/api/admin", tags=["Admin"])


@router.get("/analytics/overview")
async def platform_overview(db: AsyncSession = Depends(get_db)):
    """
    Platform-wide overview metrics.
    All values computed from real database aggregations.
    """
    return await get_platform_overview(db)


@router.get("/analytics/campaigns")
async def campaign_analytics(db: AsyncSession = Depends(get_db)):
    """
    Campaign performance metrics using multi-table JOINs:
    campaigns → advertisements → ad_impressions / ad_clicks.
    """
    return await get_campaign_analytics(db)


@router.get("/analytics/categories")
async def category_analytics(db: AsyncSession = Depends(get_db)):
    """Category engagement metrics from cross-table aggregations."""
    return await get_category_analytics(db)
