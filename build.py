"""Minify the static assets into dist/.

Source stays readable under static/; this emits a minified copy under dist/ and
the server serves dist/ whenever it exists (see the _asset helper in main.py).
So `python build.py` is what switches a deployment to optimised files, while
plain `uvicorn` in development keeps using the unminified static/ originals.

Requires the build-only dependencies in requirements-build.txt (rjsmin, rcssmin).
"""

from pathlib import Path

import rcssmin
import rjsmin

ROOT = Path(__file__).parent
SRC = ROOT / "static"
DIST = ROOT / "dist"

MINIFY = {
    ".js": rjsmin.jsmin,
    ".css": rcssmin.cssmin,
}


def build() -> None:
    if DIST.exists():
        for p in DIST.rglob("*"):
            if p.is_file():
                p.unlink()
    else:
        DIST.mkdir()

    for src in SRC.rglob("*"):
        if not src.is_file():
            continue

        minify = MINIFY.get(src.suffix)
        text = src.read_text()

        if minify is not None:
            text = minify(text)

        out = DIST / src.relative_to(SRC)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text)

        print(f"{src.relative_to(SRC)}: {len(src.read_text())} -> {len(text)} bytes")


if __name__ == "__main__":
    build()
