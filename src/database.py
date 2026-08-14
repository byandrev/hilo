"""Database initialization."""

from beanie import init_beanie
from pymongo import AsyncMongoClient

from .config import settings
from .models import Comment


async def init_db() -> None:
    """One client for the app's lifetime — pymongo pools connections itself,
    so there is no per-request connection to open like SQLite needed."""

    client = AsyncMongoClient(settings.mongo_uri)
    await init_beanie(database=client[settings.mongo_db], document_models=[Comment])
