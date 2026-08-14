"""The document, and every query that touches it.

Mongo lives here and nowhere else — same rule as before: one file to audit for how
comments are read and written.
"""

from datetime import datetime, timedelta, timezone

from beanie import Document, PydanticObjectId
from pydantic import Field
from pymongo import IndexModel


class Comment(Document):
    """A comment on a page, with optional parent_id for threading."""

    site: str
    page: str
    parent_id: PydanticObjectId | None = None
    body: str
    author_id: str
    author_name: str
    author_avatar: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    deleted: bool = False

    class Settings:
        """Beanie settings for the Comment document."""

        name = "comments"
        indexes = [IndexModel([("site", 1), ("page", 1), ("_id", 1)])]


async def list_for_page(site: str, page: str, sort: str = "newest") -> list[Comment]:
    """Flat, ordered by id. The client builds the tree — no recursive lookup needed.

    sort="oldest" gives the thread top-down; sort="newest" (default) puts the latest on top.
    """

    order = -1 if sort == "newest" else 1

    return (
        await Comment.find(Comment.site == site, Comment.page == page)
        .sort(("_id", order))
        .to_list()
    )


async def get(comment_id: PydanticObjectId) -> Comment | None:
    """Get a comment by its ID."""

    return await Comment.get(comment_id)


async def exists_on_page(comment_id: PydanticObjectId, site: str, page: str) -> bool:
    """Used to reject replies grafted onto a thread they do not belong to."""

    return (
        await Comment.find_one(
            Comment.id == comment_id, Comment.site == site, Comment.page == page
        )
        is not None
    )


async def count_recent(author_id: str, seconds: int = 60) -> int:
    """Count the number of comments made by an author in the last N seconds."""

    since = datetime.now(timezone.utc) - timedelta(seconds=seconds)

    return await Comment.find(
        Comment.author_id == author_id, Comment.created_at > since
    ).count()


async def insert(
    *,
    site: str,
    page: str,
    parent_id: PydanticObjectId | None,
    body: str,
    author_id: str,
    author_name: str,
    author_avatar: str | None,
) -> Comment:
    """Insert a new comment into the database."""

    comment = Comment(
        site=site,
        page=page,
        parent_id=parent_id,
        body=body,
        author_id=author_id,
        author_name=author_name,
        author_avatar=author_avatar,
    )
    await comment.insert()

    return comment


async def soft_delete(comment_id: PydanticObjectId) -> None:
    """Mark a comment as deleted, but do not remove it from the database."""

    comment = await Comment.get(comment_id)
    comment.deleted = True

    await comment.save()
