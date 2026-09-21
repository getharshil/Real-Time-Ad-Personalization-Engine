"""Pydantic schemas for events."""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any, List


VALID_EVENT_TYPES = {
    "APP_OPEN", "SEARCH", "CONTENT_VIEW", "CONTENT_LIKE", "CONTENT_DISLIKE",
    "AD_IMPRESSION", "AD_CLICK", "AD_SKIP", "SESSION_START", "SESSION_END",
}


class EventCreate(BaseModel):
    session_id: Optional[int] = None
    event_type: str = Field(..., description="One of: APP_OPEN, SEARCH, CONTENT_VIEW, etc.")
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

    def model_post_init(self, __context: Any) -> None:
        if self.event_type not in VALID_EVENT_TYPES:
            raise ValueError(f"Invalid event_type: {self.event_type}. Must be one of {VALID_EVENT_TYPES}")


class EventBatchCreate(BaseModel):
    events: List[EventCreate] = Field(..., min_length=1, max_length=100)


class EventResponse(BaseModel):
    id: int
    user_id: int
    session_id: Optional[int] = None
    event_type: str
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    created_at: datetime
    metadata: Optional[Dict[str, Any]] = None

    model_config = {"from_attributes": True}
