"""Ad interaction API: impression and click tracking."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import User
from app.api.deps import get_current_user
from app.schemas.recommendations import AdImpressionCreate, AdClickCreate
from app.services.recommendation_service import record_ad_impression, record_ad_click

router = APIRouter(prefix="/api/ads", tags=["Advertisements"])


@router.post("/{ad_id}/impression")
async def create_impression(
    ad_id: int,
    data: AdImpressionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record an ad impression. Creates both an impression record and an event."""
    impression = await record_ad_impression(
        db=db,
        ad_id=ad_id,
        user_id=current_user.id,
        session_id=data.session_id,
        recommendation_score=data.recommendation_score,
        source=data.source,
    )
    return {"impression_id": impression.id, "ad_id": ad_id}


@router.post("/{ad_id}/click")
async def create_click(
    ad_id: int,
    data: AdClickCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Record an ad click. This triggers the feedback loop:
    1. Click record created
    2. Event created
    3. User interest for ad's category updated
    4. Next recommendation request will reflect updated profile
    """
    click = await record_ad_click(
        db=db,
        ad_id=ad_id,
        user_id=current_user.id,
        impression_id=data.impression_id,
    )
    return {"click_id": click.id, "ad_id": ad_id}
