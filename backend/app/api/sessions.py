"""Session API: start and end user sessions."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import User
from app.api.deps import get_current_user
from app.services.session_service import start_session, end_session

router = APIRouter(prefix="/api/sessions", tags=["Sessions"])


@router.post("/start")
async def start_new_session(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start a new user session. Returns session ID for subsequent event tracking."""
    session = await start_session(db, current_user.id, current_user.device_type or "desktop")
    return {
        "session_id": session.id,
        "started_at": session.started_at,
    }


@router.post("/{session_id}/end")
async def end_existing_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """End a session. Computes and stores the session duration."""
    session = await end_session(db, session_id)
    if not session:
        return {"error": "Session not found"}
    return {
        "session_id": session.id,
        "ended_at": session.ended_at,
        "duration_seconds": session.duration_seconds,
    }
