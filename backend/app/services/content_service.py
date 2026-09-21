"""Content service: content listing, search, category management."""

from typing import List, Optional, Tuple

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models import Content, ContentCategory


async def get_categories(db: AsyncSession) -> List[ContentCategory]:
    result = await db.execute(
        select(ContentCategory).order_by(ContentCategory.name)
    )
    return list(result.scalars().all())


async def get_content_list(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    category_id: Optional[int] = None,
    sort_by: str = "created_at",
) -> Tuple[List[Content], int]:
    """Get paginated content list with optional category filter."""
    query = select(Content).where(Content.is_active == True).options(
        joinedload(Content.category)
    )

    if category_id:
        query = query.where(Content.category_id == category_id)

    # Count total
    count_query = select(func.count()).select_from(Content).where(Content.is_active == True)
    if category_id:
        count_query = count_query.where(Content.category_id == category_id)
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Sort
    if sort_by == "popularity":
        query = query.order_by(Content.popularity_score.desc())
    else:
        query = query.order_by(Content.created_at.desc())

    # Paginate
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    items = list(result.scalars().unique().all())
    return items, total


async def get_content_by_id(db: AsyncSession, content_id: int) -> Optional[Content]:
    result = await db.execute(
        select(Content)
        .where(Content.id == content_id)
        .options(joinedload(Content.category))
    )
    return result.scalar_one_or_none()


async def search_content(
    db: AsyncSession,
    query_str: str,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[Content], int]:
    """Search content by title or description using ILIKE."""
    search_pattern = f"%{query_str}%"

    query = (
        select(Content)
        .where(Content.is_active == True)
        .where(
            or_(
                Content.title.ilike(search_pattern),
                Content.description.ilike(search_pattern),
            )
        )
        .options(joinedload(Content.category))
    )

    # Count
    count_query = (
        select(func.count())
        .select_from(Content)
        .where(Content.is_active == True)
        .where(
            or_(
                Content.title.ilike(search_pattern),
                Content.description.ilike(search_pattern),
            )
        )
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Paginate
    offset = (page - 1) * page_size
    query = query.order_by(Content.popularity_score.desc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    items = list(result.scalars().unique().all())
    return items, total
