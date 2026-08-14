from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.middleware.sessions import SessionMiddleware

from .config import BUILD_DIR, STATIC_DIR, settings
from .database import init_db
from .routers import auth, comments


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="comments", lifespan=lifespan)


app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    same_site="lax",
    https_only=settings.https,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(comments.router)


def _asset(name: str) -> Path:
    """Serve the minified copy from dist/ when a build exists, else the source."""

    built = BUILD_DIR / name

    return built if built.is_file() else STATIC_DIR / name


@app.get("/embed.js", include_in_schema=False)
def embed_script():
    return FileResponse(_asset("embed.js"), media_type="application/javascript")


@app.get("/embed.css", include_in_schema=False)
def embed_styles():
    return FileResponse(_asset("embed.css"), media_type="text/css")


@app.get("/themes/{name}.css", include_in_schema=False)
def theme_styles(name: str):
    if "/" in name or name in (".", ".."):
        raise FileNotFoundError(name)

    return FileResponse(_asset(f"themes/{name}.css"), media_type="text/css")
