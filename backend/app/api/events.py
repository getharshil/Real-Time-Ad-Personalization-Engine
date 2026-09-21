"""Event API: single and batch event ingestion."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import User
from app.schemas.events import EventCreate, EventBatchCreate, EventResponse
from app.services.event_service import create_event, create_events_batch
from app.api.deps import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/events", tags=["Events"])


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def record_event(
    data: EventCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record a single user event. Triggers profile update for interest-related events."""
    event = await create_event(
        db=db,
        user_id=current_user.id,
        event_type=data.event_type,
        session_id=data.session_id,
        entity_type=data.entity_type,
        entity_id=data.entity_id,
        metadata=data.metadata,
    )
    return EventResponse(
        id=event.id,
        user_id=event.user_id,
        session_id=event.session_id,
        event_type=event.event_type,
        entity_type=event.entity_type,
        entity_id=event.entity_id,
        created_at=event.created_at,
        metadata=event.metadata_,
    )


@router.post("/batch", response_model=list[EventResponse], status_code=status.HTTP_201_CREATED)
async def record_events_batch(
    data: EventBatchCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record multiple events in a single request/transaction."""
    events = await create_events_batch(db, current_user.id, data.events)
    return [
        EventResponse(
            id=e.id,
            user_id=e.user_id,
            session_id=e.session_id,
            event_type=e.event_type,
            entity_type=e.entity_type,
            entity_id=e.entity_id,
            created_at=e.created_at,
            metadata=e.metadata_,
        )
        for e in events
    ]
