from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class Provider(StrEnum):
    google = "google"
    github = "github"


class User(BaseModel):
    """The signed token payload. Also what the widget gets to draw the UI."""

    sub: str  # "google:12345" — prefixed so two providers cannot collide on an id
    name: str
    avatar: str | None = None
    email: str | None = None


class CommentIn(BaseModel):
    site: str = Field(max_length=64)
    page: str = Field(max_length=512)
    body: str = Field(min_length=1, max_length=4000)
    parent_id: int | None = None

    @field_validator("body")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("comment is empty")

        return v.strip()


class CommentOut(BaseModel):
    id: int
    parent_id: int | None
    body: str
    author_id: str
    author_name: str
    author_avatar: str | None
    created_at: str
    deleted: bool

    @classmethod
    def from_row(cls, row) -> "CommentOut":
        c = cls(**dict(row))

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
