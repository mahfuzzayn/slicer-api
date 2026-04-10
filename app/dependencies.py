from datetime import datetime
from typing import Generator

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.models.database import SessionLocal
from app.models.tables import ApiKey, User
from app.utils.errors import AuthenticationError, AuthorizationError
from app.utils.security import hash_api_key


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    auth_header = request.headers.get("authorization") or request.headers.get(
        "Authorization"
    )
    if not auth_header:
        raise AuthenticationError(
            message="Missing Authorization header",
            code="MISSING_API_KEY",
        )

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthenticationError(
            message="Authorization header must be 'Bearer <api_key>'",
            code="MISSING_API_KEY",
        )

    raw_key = parts[1]
    key_hash = hash_api_key(raw_key)

    api_key: ApiKey | None = (
        db.query(ApiKey).filter(ApiKey.key_hash == key_hash).one_or_none()
    )
    if api_key is None or not api_key.is_active:
        raise AuthenticationError()

    now = datetime.utcnow()
    if api_key.expires_at is not None and api_key.expires_at < now:
        raise AuthenticationError(
            message="API key has expired",
            code="EXPIRED_API_KEY",
        )

    user: User | None = db.query(User).filter(User.id == api_key.user_id).one_or_none()
    if user is None or not user.is_active:
        raise AuthorizationError()

    api_key.last_used_at = now
    db.commit()

    return user
