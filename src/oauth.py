"""OAuth clients and the one thing they cannot agree on: the shape of a profile."""

import httpx
from authlib.integrations.starlette_client import OAuth

from .config import settings
from .schemas import Provider, User

oauth = OAuth()

oauth.register(
    name=Provider.google,
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

oauth.register(
    name=Provider.github,
    client_id=settings.github_client_id,
    client_secret=settings.github_client_secret,
    access_token_url="https://github.com/login/oauth/access_token",
    authorize_url="https://github.com/login/oauth/authorize",
    client_kwargs={"scope": "read:user user:email"},
)


def client(provider: Provider):
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


def _google_profile(token: dict) -> User:
    info = token["userinfo"]

    return User(
        sub=f"google:{info['sub']}",
        name=info.get("name") or info["email"],
        avatar=info.get("picture"),
        email=info.get("email"),
    )


async def fetch_profile(provider: Provider, token: dict) -> User:
    if provider is Provider.google:
        return _google_profile(token)

    return await _github_profile(token)
