"""Content API: list, detail, search, categories."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.content import ContentResponse, ContentListResponse, CategoryResponse
from app.services.content_service import (
    get_categories,
    get_content_list,
    get_content_by_id,
    search_content,
)

router = APIRouter(prefix="/api", tags=["Content"])


@router.get("/content/categories", response_model=list[CategoryResponse])
async def list_categories(db: AsyncSession = Depends(get_db)):
    """List all content categories."""
    categories = await get_categories(db)
    return categories


@router.get("/content", response_model=ContentListResponse)
async def list_content(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category_id: int = Query(None),
    sort_by: str = Query("created_at", regex="^(created_at|popularity)$"),
    db: AsyncSession = Depends(get_db),
):
    """List content with pagination and optional category filter."""
    items, total = await get_content_list(db, page, page_size, category_id, sort_by)
    return ContentListResponse(
        items=[
            ContentResponse(
                id=item.id,
                title=item.title,
                description=item.description,
                category_id=item.category_id,
                category_name=item.category.name if item.category else None,
                popularity_score=item.popularity_score,
                created_at=item.created_at,
                is_active=item.is_active,
            )
            for item in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/content/{content_id}", response_model=ContentResponse)
async def get_content(content_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single content item by ID."""
    item = await get_content_by_id(db, content_id)
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")
    return ContentResponse(
        id=item.id,
        title=item.title,
        description=item.description,
        category_id=item.category_id,
        category_name=item.category.name if item.category else None,
        popularity_score=item.popularity_score,
        created_at=item.created_at,
        is_active=item.is_active,
    )


@router.get("/search", response_model=ContentListResponse)
async def search(
    q: str = Query(..., min_length=1, max_length=200),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Search content by title or description."""
    items, total = await search_content(db, q, page, page_size)
    return ContentListResponse(
        items=[
            ContentResponse(
                id=item.id,
                title=item.title,
                description=item.description,
                category_id=item.category_id,
                category_name=item.category.name if item.category else None,
                popularity_score=item.popularity_score,
                created_at=item.created_at,
                is_active=item.is_active,
            )
            for item in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )
