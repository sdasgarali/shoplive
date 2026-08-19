"""Authentication: register, login (OAuth2 password flow), and current user."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select

from ..db import get_session
from ..models import Seller, User
from ..schemas import RegisterRequest, TokenResponse, UserPublic
from ..security import create_access_token, get_current_user, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, session: Session = Depends(get_session)) -> TokenResponse:
    exists = session.exec(
        select(User).where((User.email == payload.email) | (User.username == payload.username))
    ).first()
    if exists:
        raise HTTPException(status_code=409, detail="Email or username already registered")

    user = User(
        email=payload.email,
        username=payload.username,
        password_hash=hash_password(payload.password),
        is_seller=payload.is_seller,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    if payload.is_seller:
        session.add(Seller(user_id=user.id, display_name=payload.display_name or payload.username))
        session.commit()

    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/login", response_model=TokenResponse)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
) -> TokenResponse:
    # OAuth2 form uses "username"; we accept the email there.
    user = session.exec(select(User).where(User.email == form.username)).first()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserPublic)
def me(user: User = Depends(get_current_user)) -> UserPublic:
    return UserPublic(id=user.id, email=user.email, username=user.username, is_seller=user.is_seller)
