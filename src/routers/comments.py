"""Comments API router."""

from beanie import PydanticObjectId
from fastapi import APIRouter, HTTPException, status

from .. import models
from ..config import settings
from ..schemas import CommentIn, CommentOut
from ..security import CurrentUser, is_admin

router = APIRouter(prefix="/api/comments", tags=["comments"])


@router.get("", response_model=list[CommentOut])
async def list_comments(site: str, page: str, sort: str = "newest"):
    """Public. Flat list ordered by id; deleted rows come back blanked."""

    return [
        CommentOut.from_doc(c) for c in await models.list_for_page(site, page, sort)
    ]


@router.post("", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
async def create_comment(comment: CommentIn, user: CurrentUser):
    """Authenticated. Create a comment on a page, optionally as a reply to another comment."""

    if comment.site not in settings.allowed_sites:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, f"site {comment.site!r} is not in ALLOWED_SITES"
        )

    if comment.parent_id is not None and not await models.exists_on_page(
        comment.parent_id, comment.site, comment.page
    ):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "parent comment not found")

    if await models.count_recent(user.sub) >= settings.rate_limit_per_minute:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS, "too many comments, wait a minute"
        )

    doc = await models.insert(
        site=comment.site,
        page=comment.page,
        parent_id=comment.parent_id,
        body=comment.body,
        author_id=user.sub,
        author_name=user.name,
        author_avatar=user.avatar,
    )
    return CommentOut.from_doc(doc)


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(comment_id: PydanticObjectId, user: CurrentUser):
    """Authenticated. Soft-delete a comment if you are the author or an admin."""

    doc = await models.get(comment_id)

    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    if doc.author_id != user.sub and not is_admin(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "not your comment")

    await models.soft_delete(comment_id)
