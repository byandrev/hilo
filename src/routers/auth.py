import json

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import HTMLResponse

from ..config import settings
from ..oauth import client, fetch_profile
from ..schemas import Provider
from ..security import issue_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/{provider}/login")
async def login(provider: Provider, origin: str, request: Request):
    """Open this in a popup. `origin` is the site the widget is running on."""

    if origin not in settings.allowed_origins:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "origin not allowed")

    request.session["origin"] = origin
    redirect_uri = f"{settings.base_url}/auth/{provider.value}/callback"

    return await client(provider).authorize_redirect(request, redirect_uri)


@router.get("/{provider}/callback", response_class=HTMLResponse)
async def callback(provider: Provider, request: Request):
    """Hands the token back to the widget through postMessage, then closes itself."""

    origin = request.session.pop("origin", None)

    if origin not in settings.allowed_origins:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "origin not allowed")

    token = await client(provider).authorize_access_token(request)
    user = await fetch_profile(provider, token)

    payload = json.dumps(
        {"type": "comments-auth", "token": issue_token(user), "user": user.model_dump()}
    )
    payload = payload.replace("<", "\\u003c")

    return HTMLResponse(
        f"""<!doctype html><meta charset="utf-8"><title>...</title><script>
window.opener.postMessage({payload}, {json.dumps(origin)});
window.close();
</script>"""
    )
