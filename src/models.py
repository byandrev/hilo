"""The table, and every query that touches it.

SQL lives here and nowhere else. That is the point of this module: the rule that
every query is parameterised is auditable by reading one file.
"""

import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS comments (
  id            INTEGER PRIMARY KEY,
  site          TEXT NOT NULL,
  page          TEXT NOT NULL,
  parent_id     INTEGER REFERENCES comments(id),
  body          TEXT NOT NULL,
  author_id     TEXT NOT NULL,
  author_name   TEXT NOT NULL,
  author_avatar TEXT,
  created_at    TEXT NOT NULL DEFAULT (datetime('now')),
  deleted       INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_page ON comments(site, page, id);
"""

COLUMNS = (
    "id, parent_id, body, author_id, author_name, author_avatar, created_at, deleted"
)


def list_for_page(
    con: sqlite3.Connection, site: str, page: str, sort: str = "newest"
) -> list[sqlite3.Row]:
    """Flat, ordered by id. The client builds the tree — no recursive CTE needed.

    sort="oldest" gives the thread top-down; sort="newest" (default) puts the latest on top.
    """

    order = "DESC" if sort == "newest" else "ASC"

    return con.execute(
        f"SELECT {COLUMNS} FROM comments WHERE site = ? AND page = ? ORDER BY id {order}",
        (site, page),
    ).fetchall()


def get(con: sqlite3.Connection, comment_id: int) -> sqlite3.Row | None:
    return con.execute(
        f"SELECT {COLUMNS} FROM comments WHERE id = ?", (comment_id,)
    ).fetchone()


def exists_on_page(
    con: sqlite3.Connection, comment_id: int, site: str, page: str
) -> bool:
    """Used to reject replies grafted onto a thread they do not belong to."""

    row = con.execute(
        "SELECT 1 FROM comments WHERE id = ? AND site = ? AND page = ?",
        (comment_id, site, page),
    ).fetchone()

    return row is not None


def count_recent(con: sqlite3.Connection, author_id: str, seconds: int = 60) -> int:
    return con.execute(
        "SELECT count(*) FROM comments"
        " WHERE author_id = ? AND created_at > datetime('now', ?)",
        (author_id, f"-{seconds} seconds"),
    ).fetchone()[0]


def insert(
    con: sqlite3.Connection,
    *,
    site: str,
    page: str,
    parent_id: int | None,
    body: str,
    author_id: str,
    author_name: str,
    author_avatar: str | None,
) -> sqlite3.Row:
    cur = con.execute(
        "INSERT INTO comments (site, page, parent_id, body, author_id, author_name, author_avatar)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (site, page, parent_id, body, author_id, author_name, author_avatar),
    )

    con.commit()

    return get(con, cur.lastrowid)


def soft_delete(con: sqlite3.Connection, comment_id: int) -> None:
    con.execute("UPDATE comments SET deleted = 1 WHERE id = ?", (comment_id,))
    con.commit()
