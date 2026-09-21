"""
Analytics service: platform-wide analytics derived from real database aggregations.

Every metric is computed from actual PostgreSQL queries using JOINs, GROUP BY,
COUNT, AVG, and other aggregation functions. Nothing is fabricated.
"""

import logging
from typing import List

from sqlalchemy import select, func, case, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    User, UserSession, Event, Content, ContentCategory,
    Advertiser, Campaign, Advertisement, AdImpression, AdClick,
    Recommendation,
)

logger = logging.getLogger(__name__)


async def get_platform_overview(db: AsyncSession) -> dict:
    """Platform-wide overview metrics using aggregation queries."""

    total_users = (await db.execute(select(func.count()).select_from(User))).scalar() or 0

    # Active users: users with at least one event in last 7 days
    from datetime import datetime, timedelta, timezone
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    active_users = (await db.execute(
        select(func.count(func.distinct(Event.user_id)))
        .where(Event.created_at >= week_ago)
    )).scalar() or 0

    total_sessions = (await db.execute(select(func.count()).select_from(UserSession))).scalar() or 0
    total_events = (await db.execute(select(func.count()).select_from(Event))).scalar() or 0
    total_impressions = (await db.execute(select(func.count()).select_from(AdImpression))).scalar() or 0
    total_clicks = (await db.execute(select(func.count()).select_from(AdClick))).scalar() or 0
    overall_ctr = round(total_clicks / max(total_impressions, 1), 4)
    total_content = (await db.execute(
        select(func.count()).select_from(Content).where(Content.is_active == True)
    )).scalar() or 0
    total_ads = (await db.execute(
        select(func.count()).select_from(Advertisement).where(Advertisement.is_active == True)
    )).scalar() or 0
    total_campaigns = (await db.execute(
        select(func.count()).select_from(Campaign).where(Campaign.is_active == True)
    )).scalar() or 0

    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_sessions": total_sessions,
        "total_events": total_events,
        "total_impressions": total_impressions,
        "total_clicks": total_clicks,
        "overall_ctr": overall_ctr,
        "total_content": total_content,
        "total_ads": total_ads,
        "total_campaigns": total_campaigns,
    }


async def get_campaign_analytics(db: AsyncSession) -> list:
    """
    Campaign performance using multi-table JOINs:
    campaigns → advertisements → ad_impressions / ad_clicks

    Demonstrates: JOIN, GROUP BY, COUNT, subquery correlation.
    """
    # Get campaign info with impression and click counts
    result = await db.execute(
        select(
            Campaign.id,
            Campaign.name.label("campaign_name"),
            Advertiser.name.label("advertiser_name"),
            func.count(func.distinct(AdImpression.id)).label("impressions"),
            func.count(func.distinct(AdClick.id)).label("clicks"),
            Campaign.budget,
            Campaign.spent,
        )
        .select_from(Campaign)
        .join(Advertiser, Campaign.advertiser_id == Advertiser.id)
        .join(Advertisement, Advertisement.campaign_id == Campaign.id, isouter=True)
        .join(AdImpression, AdImpression.ad_id == Advertisement.id, isouter=True)
        .join(AdClick, AdClick.ad_id == Advertisement.id, isouter=True)
        .group_by(Campaign.id, Campaign.name, Advertiser.name, Campaign.budget, Campaign.spent)
        .order_by(func.count(func.distinct(AdImpression.id)).desc())
    )

    campaigns = []
    for row in result.all():
        impressions = row[3] or 0
        clicks = row[4] or 0
        campaigns.append({
            "campaign_id": row[0],
            "campaign_name": row[1],
            "advertiser_name": row[2],
            "impressions": impressions,
            "clicks": clicks,
            "ctr": round(clicks / max(impressions, 1), 4),
            "budget": row[5],
            "spent": row[6],
        })

    return campaigns


async def get_category_analytics(db: AsyncSession) -> list:
    """
    Category engagement using JOINs across content, events, and ad tables.
    """
    # Content views per category
    result = await db.execute(
        select(
            ContentCategory.name,
            func.count(
                case((Event.event_type == "CONTENT_VIEW", 1))
            ).label("content_views"),
            func.count(
                case((Event.event_type == "AD_IMPRESSION", 1))
            ).label("ad_impressions"),
            func.count(
                case((Event.event_type == "AD_CLICK", 1))
            ).label("ad_clicks"),
        )
        .select_from(ContentCategory)
        .join(Content, Content.category_id == ContentCategory.id, isouter=True)
        .join(
            Event,
            (Event.entity_id == Content.id) & (Event.entity_type == "content"),
            isouter=True,
        )
        .group_by(ContentCategory.name)
        .order_by(func.count(case((Event.event_type == "CONTENT_VIEW", 1))).desc())
    )

    categories = []
    for row in result.all():
        views = row[1] or 0
        impressions = row[2] or 0
        clicks = row[3] or 0
        total = views + impressions + clicks
        categories.append({
            "category_name": row[0],
            "content_views": views,
            "ad_impressions": impressions,
            "ad_clicks": clicks,
            "engagement_score": round(total / max(total, 1), 3) if total > 0 else 0,
        })

    return categories
