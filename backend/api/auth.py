"""JWT authentication: register, login, and current-user endpoints."""

from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.hash import bcrypt
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.config import settings
from models.database import Profile, User
from models.session import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

EMAIL_PATTERN = r"^[\w.+-]+@[\w-]+\.[\w.-]+$"

UNAUTHORIZED_HEADERS = {"WWW-Authenticate": "Bearer"}


class Credentials(BaseModel):
    """Register/login request body."""

    email: str = Field(..., max_length=255, pattern=EMAIL_PATTERN)
    password: str = Field(..., min_length=8, max_length=128)


def create_access_token(subject: str) -> str:
    """Generate a signed JWT with the user id as the subject."""
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """FastAPI dependency: resolve the bearer token to a User or raise 401."""
    unauthorized = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers=UNAUTHORIZED_HEADERS,
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id = payload.get("sub")
        if not user_id:
            raise unauthorized
        user_uuid = UUID(user_id)
    except (JWTError, ValueError, TypeError):
        raise unauthorized

    user = db.get(User, user_uuid)
    if user is None:
        raise unauthorized
    return user


def _get_or_create_user_profile(db: Session, user_id: UUID) -> Profile:
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    if profile is None:
        profile = Profile(user_id=user_id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


@router.post("/register", status_code=201)
def register(payload: Credentials, db: Session = Depends(get_db)) -> dict:
    """Create a new user and return their id plus an access token and profile_id."""
    email = payload.email.strip().lower()
    if db.query(User).filter(User.email == email).first() is not None:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(email=email, password_hash=bcrypt.hash(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    profile = _get_or_create_user_profile(db, user.id)

    token = create_access_token(str(user.id))
    return {
        "user_id": str(user.id),
        "profile_id": str(profile.id),
        "token": token,
        "access_token": token,
        "token_type": "bearer",
    }


@router.post("/login")
def login(payload: Credentials, db: Session = Depends(get_db)) -> dict:
    """Verify credentials and return an access token and profile_id."""
    email = payload.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()

    valid = False
    if user is not None:
        try:
            valid = bcrypt.verify(payload.password, user.password_hash)
        except ValueError:
            valid = False

    if not valid:
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers=UNAUTHORIZED_HEADERS,
        )

    profile = _get_or_create_user_profile(db, user.id)
    token = create_access_token(str(user.id))

    return {
        "access_token": token,
        "token": token,
        "token_type": "bearer",
        "user_id": str(user.id),
        "profile_id": str(profile.id),
    }


@router.get("/me")
def read_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Return the authenticated user's profile information."""
    profile = _get_or_create_user_profile(db, current_user.id)
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "profile_id": str(profile.id),
        "created_at": current_user.created_at.isoformat(),
        "updated_at": current_user.updated_at.isoformat(),
    }
