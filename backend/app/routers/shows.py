"""Shows: discovery feed (live + upcoming), category/search filters, and CRUD with ownership checks.

Schemas for this surface live here, per the delegation contract — schemas.py is
owned by the foundation and stays untouched.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status as http_status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import case
from sqlmodel import Session, select

from ..db import get_session
from ..models import Seller, Show, ShowStatus, User
from ..security import get_current_user, require_seller

router = APIRouter(prefix="/shows", tags=["shows"])

CATEGORIES = [
    "Trading Cards",
    "Sneakers",
    "Collectibles",
    "Comics",
    "Electronics",
    "Fashion",
    "Toys",
    "Other",
]


class ShowCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    category: str
    scheduled_at: datetime | None = None
    thumbnail_url: str | None = None

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("title must not be empty")
        return v

    @field_validator("category")
    @classmethod
    def category_must_be_known(cls, v: str) -> str:
        if v not in CATEGORIES:
            raise ValueError(f"category must be one of: {', '.join(CATEGORIES)}")
        return v


class ShowUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    category: str | None = None
    scheduled_at: datetime | None = None
    status: ShowStatus | None = None

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("title must not be empty")
        return v

    @field_validator("category")
    @classmethod
    def category_must_be_known(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if v not in CATEGORIES:
            raise ValueError(f"category must be one of: {', '.join(CATEGORIES)}")
        return v


class ShowPublic(BaseModel):
    id: int
    seller_id: int
    title: str
    category: str
    status: ShowStatus
    scheduled_at: datetime | None
    viewer_count: int
    thumbnail_url: str
    created_at: datetime
    seller_display_name: str | None = None


def _enrich(shows: list[Show], session: Session) -> list[ShowPublic]:
    """Attach the seller display_name to a list of shows."""
    seller_ids = {s.seller_id for s in shows}
    sellers: dict[int, str] = {}
    if seller_ids:
        rows = session.exec(select(Seller).where(Seller.user_id.in_(seller_ids))).all()
        sellers = {r.user_id: r.display_name for r in rows}
    return [
        ShowPublic(
            id=s.id,
            seller_id=s.seller_id,
            title=s.title,
            category=s.category,
            status=s.status,
            scheduled_at=s.scheduled_at,
            viewer_count=s.viewer_count,
            thumbnail_url=s.thumbnail_url,
            created_at=s.created_at,
            seller_display_name=sellers.get(s.seller_id),
        )
        for s in shows
    ]


def _get_show_or_404(show_id: int, session: Session) -> Show:
    show = session.get(Show, show_id)
    if show is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Show not found")
    return show


def _get_owned_show(show_id: int, user: User, session: Session) -> Show:
    show = _get_show_or_404(show_id, session)
    if show.seller_id != user.id:
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Not your show")
    return show


@router.get("", response_model=list[ShowPublic])
def list_shows(
    status: ShowStatus | None = None,
    category: str | None = None,
    q: str | None = None,
    session: Session = Depends(get_session),
) -> list[ShowPublic]:
    """Discovery feed. Defaults to live + scheduled (upcoming) shows."""
    stmt = select(Show)
    if status is None:
        stmt = stmt.where(Show.status.in_([ShowStatus.live, ShowStatus.scheduled]))
    else:
        stmt = stmt.where(Show.status == status)
    if category:
        stmt = stmt.where(Show.category == category)
    if q:
        stmt = stmt.where(Show.title.ilike(f"%{q}%"))
    # Live shows first, then scheduled, then the rest; newest first within a bucket.
    order = case(
        (Show.status == ShowStatus.live, 0),
        (Show.status == ShowStatus.scheduled, 1),
        else_=2,
    )
    stmt = stmt.order_by(order, Show.created_at.desc())
    return _enrich(session.exec(stmt).all(), session)


@router.get("/{show_id}", response_model=ShowPublic)
def get_show(show_id: int, session: Session = Depends(get_session)) -> ShowPublic:
    show = _get_show_or_404(show_id, session)
    return _enrich([show], session)[0]


@router.post("", response_model=ShowPublic, status_code=http_status.HTTP_201_CREATED)
def create_show(
    payload: ShowCreate,
    user: User = Depends(require_seller),
    session: Session = Depends(get_session),
) -> ShowPublic:
    show = Show(
        seller_id=user.id,
        title=payload.title,
        category=payload.category,
        scheduled_at=payload.scheduled_at,
        thumbnail_url=payload.thumbnail_url or "",
    )
    session.add(show)
    session.commit()
    session.refresh(show)
    return _enrich([show], session)[0]


@router.patch("/{show_id}", response_model=ShowPublic)
def update_show(
    show_id: int,
    payload: ShowUpdate,
    user: User = Depends(require_seller),
    session: Session = Depends(get_session),
) -> ShowPublic:
    show = _get_owned_show(show_id, user, session)
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    for field, value in data.items():
        setattr(show, field, value)
    session.add(show)
    session.commit()
    session.refresh(show)
    return _enrich([show], session)[0]


@router.delete("/{show_id}", status_code=http_status.HTTP_204_NO_CONTENT)
def delete_show(
    show_id: int,
    user: User = Depends(require_seller),
    session: Session = Depends(get_session),
) -> Response:
    show = _get_owned_show(show_id, user, session)
    session.delete(show)
    session.commit()
    return Response(status_code=http_status.HTTP_204_NO_CONTENT)
