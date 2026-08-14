"""
Schemas for the API.
"""

from datetime import datetime
from enum import StrEnum

from beanie import PydanticObjectId
from pydantic import BaseModel, Field, field_validator

from .models import Comment


class Provider(StrEnum):
    """The OAuth provider that issued the token."""

    GITHUB = "github"


class User(BaseModel):
    """The signed token payload. Also what the widget gets to draw the UI."""

    sub: str  # "github:12345" — prefixed so the provider cannot collide on an id
    name: str
    avatar: str | None = None
    email: str | None = None


class CommentIn(BaseModel):
    """The request body for creating a comment."""

    site: str = Field(max_length=64)
    page: str = Field(max_length=512)
    body: str = Field(min_length=1, max_length=4000)
    parent_id: PydanticObjectId | None = None

    @field_validator("body")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        """Reject empty or whitespace-only comments."""

        if not v.strip():
            raise ValueError("comment is empty")

        return v.strip()


class CommentOut(BaseModel):
    """The response body for a comment."""

    id: PydanticObjectId
    parent_id: PydanticObjectId | None
    body: str
    author_id: str
    author_name: str
    author_avatar: str | None
    created_at: datetime
    deleted: bool

    @classmethod
    def from_doc(cls, doc: Comment) -> "CommentOut":
        """Convert a Comment document to a CommentOut schema."""

        c = cls(**doc.model_dump())

        if not c.deleted:
            return c

        return c.model_copy(
            update={
                "body": "",
                "author_id": "",
                "author_name": "",
                "author_avatar": None,
            }
        )
