"""Session service: session lifecycle management."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import UserSession


async def start_session(
    db: AsyncSession,
    user_id: int,
    device_type: str = "desktop",
) -> UserSession:
    """Start a new user session."""
    session = UserSession(
        user_id=user_id,
        device_type=device_type,
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return session


async def end_session(db: AsyncSession, session_id: int) -> Optional[UserSession]:
    """End a session and compute its duration."""
    result = await db.execute(
        select(UserSession).where(UserSession.id == session_id)
    )
    session = result.scalar_one_or_none()

    if session and not session.ended_at:
        session.ended_at = datetime.now(timezone.utc)
        if session.started_at:
            delta = session.ended_at - session.started_at
            session.duration_seconds = int(delta.total_seconds())
        await db.flush()
        await db.refresh(session)

    return session


async def get_active_session(db: AsyncSession, user_id: int) -> Optional[UserSession]:
    """Get the most recent active (not ended) session for a user."""
    result = await db.execute(
        select(UserSession)
        .where(UserSession.user_id == user_id, UserSession.ended_at.is_(None))
        .order_by(UserSession.started_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
