from fastapi import APIRouter, HTTPException, status

from .. import models
from ..config import settings
from ..database import DB
from ..schemas import CommentIn, CommentOut
from ..security import CurrentUser, is_admin

router = APIRouter(prefix="/api/comments", tags=["comments"])


@router.get("", response_model=list[CommentOut])
def list_comments(site: str, page: str, con: DB, sort: str = "newest"):
    """Public. Flat list ordered by id; deleted rows come back blanked."""

    return [CommentOut.from_row(r) for r in models.list_for_page(con, site, page, sort)]


@router.post("", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
def create_comment(comment: CommentIn, user: CurrentUser, con: DB):
    if comment.site not in settings.allowed_sites:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, f"site {comment.site!r} is not in ALLOWED_SITES"
        )

    if comment.parent_id is not None and not models.exists_on_page(
        con, comment.parent_id, comment.site, comment.page
    ):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "parent comment not found")

    if models.count_recent(con, user.sub) >= settings.rate_limit_per_minute:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS, "too many comments, wait a minute"
        )

    row = models.insert(
        con,
        site=comment.site,
        page=comment.page,
        parent_id=comment.parent_id,
        body=comment.body,
        author_id=user.sub,
        author_name=user.name,
        author_avatar=user.avatar,
    )
    return CommentOut.from_row(row)


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(comment_id: int, user: CurrentUser, con: DB):
    row = models.get(con, comment_id)

    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    if row["author_id"] != user.sub and not is_admin(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "not your comment")

    models.soft_delete(con, comment_id)
