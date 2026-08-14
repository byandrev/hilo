"""Application settings."""

from pathlib import Path
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

ROOT = Path(__file__).parent.parent
STATIC_DIR = ROOT / "static"
BUILD_DIR = ROOT / "dist"


class Settings(BaseSettings):
    """Config from the environment, with `.env` as a fallback.

    Real environment variables win over `.env`, which is what makes the Docker
    setup work: compose passes `.env` through as env vars and overrides MONGO_URI.
    """

    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    secret_key: str
    base_url: str = "http://localhost:8000"
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "hilo"

    allowed_origins: Annotated[list[str], NoDecode] = []
    allowed_sites: Annotated[set[str], NoDecode] = set()
    admin_emails: Annotated[set[str], NoDecode] = set()

    github_client_id: str = ""
    github_client_secret: str = ""

    rate_limit_per_minute: int = 5
    token_max_age_days: int = 30

    @field_validator("allowed_origins", "allowed_sites", "admin_emails", mode="before")
    @classmethod
    def _split_csv(cls, v):
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]

        return v

    @field_validator("base_url")
    @classmethod
    def _no_trailing_slash(cls, v: str) -> str:
        return v.rstrip("/")

    @property
    def https(self) -> bool:
        """Whether the base URL is HTTPS, which is used to set the secure flag on cookies."""

        return self.base_url.startswith("https")

    @property
    def token_max_age(self) -> int:
        """The maximum age of a token in seconds, used to set the cookie expiration."""

        return self.token_max_age_days * 24 * 3600


settings = Settings()
