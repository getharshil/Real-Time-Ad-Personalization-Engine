"""User profile and analytics API."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import User
from app.api.deps import get_current_user
from app.services.profile_service import get_user_profile, get_user_analytics

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.get("/me/profile")
async def my_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the current user's dynamic profile.
    All fields are computed from actual event data and user interests.
    """
    profile = await get_user_profile(db, current_user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.get("/me/analytics")
async def my_analytics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the current user's analytics.
    All metrics derived from real aggregation queries over events,
    sessions, impressions, and clicks tables.
    """
    analytics = await get_user_analytics(db, current_user.id)
    return analytics
