"""
User profile service: computes dynamic user profiles from actual event data.

The profile is NOT hardcoded — it's derived from aggregation queries
over the events, user_interests, ad_impressions, and ad_clicks tables.
"""

import logging
from typing import Dict, List, Optional

from sqlalchemy import select, func, case, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    User, UserInterest, Event, ContentCategory,
    AdImpression, AdClick,
)

logger = logging.getLogger(__name__)

COLD_START_THRESHOLD = 10  # Minimum events before personalization kicks in


async def get_user_profile(db: AsyncSession, user_id: int) -> dict:
    """
    Build a dynamic user profile from actual database records.

    Returns:
        dict with interests, engagement_score, preferred_categories, etc.
    """
    # Get user
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        return None

    # Get interests (JOIN user_interests with content_categories)
    interests_result = await db.execute(
        select(
            ContentCategory.name,
            UserInterest.affinity_score,
            UserInterest.interaction_count,
        )
        .join(ContentCategory, UserInterest.category_id == ContentCategory.id)
        .where(UserInterest.user_id == user_id)
        .order_by(UserInterest.affinity_score.desc())
    )
    interests = [
        {
            "category": row[0],
            "affinity_score": round(row[1], 3),
            "interaction_count": row[2],
        }
        for row in interests_result.all()
    ]

    # Total events count
    event_count_result = await db.execute(
        select(func.count()).select_from(Event).where(Event.user_id == user_id)
    )
    total_events = event_count_result.scalar() or 0

    # Engagement score: ratio of interactive events to total events
    interactive_types = ("CONTENT_LIKE", "AD_CLICK", "CONTENT_VIEW", "SEARCH")
    interactive_count_result = await db.execute(
        select(func.count())
        .select_from(Event)
        .where(Event.user_id == user_id, Event.event_type.in_(interactive_types))
    )
    interactive_count = interactive_count_result.scalar() or 0
    engagement_score = round(interactive_count / max(total_events, 1), 3)

    # Preferred categories (top 5 by affinity)
    preferred_categories = [i["category"] for i in interests[:5]]

    # Cold start check
    is_cold_start = total_events < COLD_START_THRESHOLD

    return {
        "user_id": user_id,
        "username": user.username,
        "interests": interests,
        "engagement_score": engagement_score,
        "preferred_categories": preferred_categories,
        "total_events": total_events,
        "is_cold_start": is_cold_start,
    }


async def get_user_analytics(db: AsyncSession, user_id: int) -> dict:
    """
    Compute user-level analytics from actual database records.

    Uses real SQL aggregations: COUNT, AVG, JOINs, GROUP BY.
    """
    from app.db.models import UserSession

    # Total sessions
    sessions_result = await db.execute(
        select(func.count()).select_from(UserSession).where(UserSession.user_id == user_id)
    )
    total_sessions = sessions_result.scalar() or 0

    # Total events
    events_result = await db.execute(
        select(func.count()).select_from(Event).where(Event.user_id == user_id)
    )
    total_events = events_result.scalar() or 0

    # Content views
    views_result = await db.execute(
        select(func.count())
        .select_from(Event)
        .where(Event.user_id == user_id, Event.event_type == "CONTENT_VIEW")
    )
    content_views = views_result.scalar() or 0

    # Ad impressions
    impressions_result = await db.execute(
        select(func.count()).select_from(AdImpression).where(AdImpression.user_id == user_id)
    )
    ad_impressions = impressions_result.scalar() or 0

    # Ad clicks
    clicks_result = await db.execute(
        select(func.count()).select_from(AdClick).where(AdClick.user_id == user_id)
    )
    ad_clicks = clicks_result.scalar() or 0

    # CTR
    ctr = round(ad_clicks / max(ad_impressions, 1), 4)

    # Most viewed categories (JOIN events → content → content_categories, GROUP BY)
    from app.db.models import Content
    category_views_result = await db.execute(
        select(
            ContentCategory.name,
            func.count().label("view_count"),
        )
        .select_from(Event)
        .join(Content, (Event.entity_id == Content.id) & (Event.entity_type == "content"))
        .join(ContentCategory, Content.category_id == ContentCategory.id)
        .where(
            Event.user_id == user_id,
            Event.event_type.in_(("CONTENT_VIEW", "CONTENT_LIKE")),
        )
        .group_by(ContentCategory.name)
        .order_by(func.count().desc())
        .limit(10)
    )
    most_viewed_categories = [
        {"category": row[0], "views": row[1]}
        for row in category_views_result.all()
    ]

    # Average session duration
    avg_duration_result = await db.execute(
        select(func.avg(UserSession.duration_seconds))
        .where(
            UserSession.user_id == user_id,
            UserSession.duration_seconds.isnot(None),
        )
    )
    avg_session_duration = avg_duration_result.scalar()
    if avg_session_duration is not None:
        avg_session_duration = round(float(avg_session_duration), 1)

    # Recent interests (categories from last 50 events)
    recent_result = await db.execute(
        select(ContentCategory.name)
        .select_from(Event)
        .join(Content, (Event.entity_id == Content.id) & (Event.entity_type == "content"))
        .join(ContentCategory, Content.category_id == ContentCategory.id)
        .where(Event.user_id == user_id)
        .order_by(Event.created_at.desc())
        .limit(50)
    )
    recent_categories = list(set(row[0] for row in recent_result.all()))

    return {
        "user_id": user_id,
        "total_sessions": total_sessions,
        "total_events": total_events,
        "content_views": content_views,
        "ad_impressions": ad_impressions,
        "ad_clicks": ad_clicks,
        "ctr": ctr,
        "most_viewed_categories": most_viewed_categories,
        "avg_session_duration_seconds": avg_session_duration,
        "recent_interests": recent_categories[:5],
    }
