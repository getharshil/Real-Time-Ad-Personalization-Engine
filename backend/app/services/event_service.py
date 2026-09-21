"""Event service: event creation, batch ingestion, profile update triggers."""

import logging
from typing import List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Event, UserInterest, Content, ContentCategory

logger = logging.getLogger(__name__)

# Events that indicate interest in a content category
INTEREST_EVENT_TYPES = {"CONTENT_VIEW", "CONTENT_LIKE", "AD_CLICK"}
# Events that indicate negative signal
NEGATIVE_EVENT_TYPES = {"CONTENT_DISLIKE", "AD_SKIP"}


async def create_event(
    db: AsyncSession,
    user_id: int,
    event_type: str,
    session_id: Optional[int] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    metadata: Optional[dict] = None,
) -> Event:
    """Create a single event and trigger profile update if needed."""
    event = Event(
        user_id=user_id,
        session_id=session_id,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata_=metadata,
    )
    db.add(event)
    await db.flush()
    await db.refresh(event)

    # Trigger profile update for interest-related events
    if event_type in INTEREST_EVENT_TYPES or event_type in NEGATIVE_EVENT_TYPES:
        await _update_user_interest(db, user_id, event_type, entity_type, entity_id)

    logger.info(
        "Event created",
        extra={"user_id": user_id, "event_type": event_type, "entity_id": entity_id},
    )
    return event


async def create_events_batch(
    db: AsyncSession,
    user_id: int,
    events_data: list,
) -> List[Event]:
    """Create multiple events in a single transaction."""
    created_events = []
    for event_data in events_data:
        event = await create_event(
            db=db,
            user_id=user_id,
            event_type=event_data.event_type,
            session_id=event_data.session_id,
            entity_type=event_data.entity_type,
            entity_id=event_data.entity_id,
            metadata=event_data.metadata,
        )
        created_events.append(event)
    return created_events


async def _update_user_interest(
    db: AsyncSession,
    user_id: int,
    event_type: str,
    entity_type: Optional[str],
    entity_id: Optional[int],
):
    """
    Update user interest scores based on the event.

    This is the core of the feedback loop:
    - CONTENT_VIEW / CONTENT_LIKE / AD_CLICK → increase affinity for that category
    - CONTENT_DISLIKE / AD_SKIP → decrease affinity for that category

    Affinity is computed as: interaction_count / (interaction_count + decay_factor)
    This gives a score between 0 and 1 that approaches 1 with more interactions.
    """
    if not entity_id or not entity_type:
        return

    # Determine the category of the interacted entity
    category_id = None

    if entity_type == "content":
        result = await db.execute(
            select(Content.category_id).where(Content.id == entity_id)
        )
        category_id = result.scalar_one_or_none()
    elif entity_type == "advertisement":
        from app.db.models import Advertisement
        result = await db.execute(
            select(Advertisement.target_category_id).where(Advertisement.id == entity_id)
        )
        category_id = result.scalar_one_or_none()

    if not category_id:
        return

    # Upsert user interest
    result = await db.execute(
        select(UserInterest).where(
            UserInterest.user_id == user_id,
            UserInterest.category_id == category_id,
        )
    )
    interest = result.scalar_one_or_none()

    decay_factor = 10  # Controls how quickly affinity saturates

    if interest:
        if event_type in INTEREST_EVENT_TYPES:
            interest.interaction_count += 1
        elif event_type in NEGATIVE_EVENT_TYPES:
            interest.interaction_count = max(0, interest.interaction_count - 1)

        # Recompute affinity score
        interest.affinity_score = min(
            1.0, interest.interaction_count / (interest.interaction_count + decay_factor)
        )
        interest.last_interaction_at = func.now()
    else:
        initial_count = 1 if event_type in INTEREST_EVENT_TYPES else 0
        new_interest = UserInterest(
            user_id=user_id,
            category_id=category_id,
            interaction_count=initial_count,
            affinity_score=initial_count / (initial_count + decay_factor),
            last_interaction_at=func.now(),
        )
        db.add(new_interest)

    logger.info(
        "User interest updated",
        extra={"user_id": user_id, "category_id": category_id, "event_type": event_type},
    )
