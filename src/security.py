from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from itsdangerous import BadSignature, URLSafeTimedSerializer

from .config import settings
from .schemas import User

serializer = URLSafeTimedSerializer(settings.secret_key, salt="comment-auth")


def issue_token(user: User) -> str:
    return serializer.dumps(user.model_dump())


def current_user(authorization: Annotated[str, Header()] = "") -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing token")
    try:
        return User(
            **serializer.loads(authorization[7:], max_age=settings.token_max_age)
        )
    except BadSignature:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid or expired token")


CurrentUser = Annotated[User, Depends(current_user)]


def is_admin(user: User) -> bool:
    return bool(user.email) and user.email in settings.admin_emails
