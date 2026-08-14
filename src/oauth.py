"""OAuth clients and the one thing they cannot agree on: the shape of a profile."""

import httpx
from authlib.integrations.starlette_client import OAuth

from .config import settings
from .schemas import Provider, User

oauth = OAuth()

oauth.register(
    name=Provider.GITHUB,
    client_id=settings.github_client_id,
    client_secret=settings.github_client_secret,
    access_token_url="https://github.com/login/oauth/access_token",
    authorize_url="https://github.com/login/oauth/authorize",
    client_kwargs={"scope": "read:user user:email"},
)


def client(provider: Provider):
    """Get the OAuth client for a given provider."""

    return oauth.create_client(provider.value)


async def _github_profile(token: dict) -> User:
    headers = {"Authorization": f"Bearer {token['access_token']}"}

    async with httpx.AsyncClient(
        base_url="https://api.github.com", headers=headers
    ) as c:
        user = (await c.get("/user")).json()
        email = user.get("email")

        if not email:
            emails = (await c.get("/user/emails")).json()
            email = next((e["email"] for e in emails if e.get("primary")), None)

    return User(
        sub=f"github:{user['id']}",
        name=user.get("name") or user["login"],
        avatar=user.get("avatar_url"),
        email=email,
    )


async def fetch_profile(provider: Provider, token: dict) -> User:
    """Get the profile for a given provider and token."""

    return await _github_profile(token)
