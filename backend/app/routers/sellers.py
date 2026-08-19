"""Sellers: public storefront and follow/unfollow."""
from fastapi import APIRouter, Depends, HTTPException, status as http_status
from pydantic import BaseModel
from sqlmodel import Session, select

from ..db import get_session
from ..models import Follow, Listing, ListingType, Seller, Show, User
from ..security import get_current_user

router = APIRouter(prefix="/sellers", tags=["sellers"])


class SellerPublic(BaseModel):
    user_id: int
    display_name: str
    bio: str
    rating: float
    follower_count: int
    shows: list[Show]
    listings: list[Listing]  # buy-now listings only


class FollowResponse(BaseModel):
    user_id: int
    seller_id: int
    follower_count: int


def _get_seller_or_404(user_id: int, session: Session) -> Seller:
    seller = session.get(Seller, user_id)
    if seller is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Seller not found")
    return seller


@router.get("/{user_id}", response_model=SellerPublic)
def get_seller(user_id: int, session: Session = Depends(get_session)) -> SellerPublic:
    seller = _get_seller_or_404(user_id, session)
    shows = session.exec(
        select(Show).where(Show.seller_id == user_id).order_by(Show.created_at.desc())
    ).all()
    listings = session.exec(
        select(Listing)
        .where(Listing.seller_id == user_id, Listing.type == ListingType.buy_now)
        .order_by(Listing.created_at.desc())
    ).all()
    return SellerPublic(
        user_id=seller.user_id,
        display_name=seller.display_name,
        bio=seller.bio,
        rating=seller.rating,
        follower_count=seller.follower_count,
        shows=shows,
        listings=listings,
    )


@router.post("/{user_id}/follow", response_model=FollowResponse, status_code=http_status.HTTP_201_CREATED)
def follow_seller(
    user_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> FollowResponse:
    seller = _get_seller_or_404(user_id, session)
    if user.id == user_id:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="Cannot follow yourself")
    existing = session.exec(
        select(Follow).where(Follow.user_id == user.id, Follow.seller_id == user_id)
    ).first()
    if existing is not None:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail="Already following this seller",
        )
    session.add(Follow(user_id=user.id, seller_id=user_id))
    seller.follower_count += 1
    session.add(seller)
    session.commit()
    return FollowResponse(user_id=user.id, seller_id=user_id, follower_count=seller.follower_count)


@router.delete("/{user_id}/follow", response_model=FollowResponse)
def unfollow_seller(
    user_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> FollowResponse:
    seller = _get_seller_or_404(user_id, session)
    follow = session.exec(
        select(Follow).where(Follow.user_id == user.id, Follow.seller_id == user_id)
    ).first()
    if follow is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Not following this seller")
    session.delete(follow)
    seller.follower_count = max(0, seller.follower_count - 1)
    session.add(seller)
    session.commit()
    return FollowResponse(user_id=user.id, seller_id=user_id, follower_count=seller.follower_count)
