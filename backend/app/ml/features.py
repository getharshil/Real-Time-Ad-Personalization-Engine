"""
Feature engineering for CTR prediction.

Generates feature vectors from actual database records for each user-ad pair.
All features are derived from real data — nothing is fabricated.
"""

from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    UserInterest, Event, AdImpression, AdClick, Advertisement,
)


FEATURE_NAMES = [
    "user_category_affinity",
    "user_historical_ctr",
    "ad_historical_ctr",
    "num_previous_impressions",
    "num_previous_clicks",
    "hour_of_day",
    "day_of_week",
    "user_engagement_score",
    "ad_recency_days",
    "bid_amount_normalized",
]


async def generate_features(
    db: AsyncSession,
    user_id: int,
    ad_id: int,
    category_id: Optional[int] = None,
) -> Optional[List[float]]:
    """
    Generate a feature vector for a user-ad pair.

    Features:
    1. user_category_affinity: user's affinity for this ad's category
    2. user_historical_ctr: user's overall click-through rate
    3. ad_historical_ctr: this ad's overall click-through rate
    4. num_previous_impressions: how many times user has seen this ad
    5. num_previous_clicks: how many times user clicked this ad
    6. hour_of_day: current hour (0-23), normalized to [0, 1]
    7. day_of_week: current day (0-6), normalized to [0, 1]
    8. user_engagement_score: ratio of interactive events to total
    9. ad_recency_days: days since ad was created, capped at 90
    10. bid_amount_normalized: ad's bid amount, normalized
    """
    try:
        # 1. User category affinity
        if category_id:
            affinity_result = await db.execute(
                select(UserInterest.affinity_score)
                .where(UserInterest.user_id == user_id, UserInterest.category_id == category_id)
            )
            affinity = affinity_result.scalar_one_or_none() or 0.0
        else:
            affinity = 0.0

        # 2. User historical CTR
        user_impressions = (await db.execute(
            select(func.count()).select_from(AdImpression).where(AdImpression.user_id == user_id)
        )).scalar() or 0
        user_clicks = (await db.execute(
            select(func.count()).select_from(AdClick).where(AdClick.user_id == user_id)
        )).scalar() or 0
        user_ctr = user_clicks / max(user_impressions, 1)

        # 3. Ad historical CTR
        ad_impressions = (await db.execute(
            select(func.count()).select_from(AdImpression).where(AdImpression.ad_id == ad_id)
        )).scalar() or 0
        ad_clicks = (await db.execute(
            select(func.count()).select_from(AdClick).where(AdClick.ad_id == ad_id)
        )).scalar() or 0
        ad_ctr = ad_clicks / max(ad_impressions, 1)

        # 4 & 5. Previous user-ad interactions
        user_ad_impressions = (await db.execute(
            select(func.count()).select_from(AdImpression)
            .where(AdImpression.ad_id == ad_id, AdImpression.user_id == user_id)
        )).scalar() or 0
        user_ad_clicks = (await db.execute(
            select(func.count()).select_from(AdClick)
            .where(AdClick.ad_id == ad_id, AdClick.user_id == user_id)
        )).scalar() or 0

        # 6 & 7. Time features
        now = datetime.now(timezone.utc)
        hour_normalized = now.hour / 23.0
        day_normalized = now.weekday() / 6.0

        # 8. User engagement score
        total_events = (await db.execute(
            select(func.count()).select_from(Event).where(Event.user_id == user_id)
        )).scalar() or 0
        interactive_events = (await db.execute(
            select(func.count()).select_from(Event)
            .where(
                Event.user_id == user_id,
                Event.event_type.in_(("CONTENT_VIEW", "CONTENT_LIKE", "AD_CLICK", "SEARCH")),
            )
        )).scalar() or 0
        engagement = interactive_events / max(total_events, 1)

        # 9. Ad recency
        ad_result = await db.execute(
            select(Advertisement.created_at, Advertisement.bid_amount)
            .where(Advertisement.id == ad_id)
        )
        ad_row = ad_result.one_or_none()
        recency_days = 45.0
        bid_normalized = 0.5
        if ad_row:
            created_at = ad_row[0]
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            recency_days = min((now - created_at).days, 90)
            bid_normalized = min(ad_row[1] / 10.0, 1.0)

        # 10. Bid normalization already done above

        features = [
            float(affinity),
            float(user_ctr),
            float(ad_ctr),
            float(min(user_ad_impressions, 50) / 50.0),  # Normalize
            float(min(user_ad_clicks, 10) / 10.0),        # Normalize
            float(hour_normalized),
            float(day_normalized),
            float(engagement),
            float(1.0 - recency_days / 90.0),  # Newer = higher
            float(bid_normalized),
        ]

        return features

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Feature generation failed: {e}")
        return None
