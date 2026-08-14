import sqlite3
from typing import Annotated, Iterator

from fastapi import Depends

from .config import settings
from .models import SCHEMA


def init_db() -> None:
    """Create the table if it is missing. Runs on every boot — there are no migrations."""

    con = sqlite3.connect(settings.db_path)
    con.execute("PRAGMA journal_mode=WAL")
    con.executescript(SCHEMA)
    con.commit()
    con.close()


def get_db() -> Iterator[sqlite3.Connection]:
    con = sqlite3.connect(settings.db_path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA busy_timeout=5000")

    try:
        yield con
    finally:
        con.close()


DB = Annotated[sqlite3.Connection, Depends(get_db)]
