# Hilo

Self-hosted comments for blogs and static sites. A FastAPI backend, a SQLite file, and one
`<script>` tag you paste into your pages. Sign-in with Google and GitHub. MIT licensed.

No ORM, no migrations, no build step, no npm. A small FastAPI package under `src/`, and one
file of vanilla JS.

```html
<script
  src="https://comments.example.com/embed.js"
  data-site="myblog"
  data-page="/posts/hello-world"
></script>
```

The widget renders where you put the tag. `data-page` is optional — it defaults to
`location.pathname`.

### Optional `data-*` attributes

All except `data-site` are optional.

| Attribute     | Values                                  | Default             | What it does                                                            |
| ------------- | --------------------------------------- | ------------------- | ----------------------------------------------------------------------- |
| `data-site`   | any string                              | —                   | Required. The comment feed's namespace; must be in `ALLOWED_SITES`      |
| `data-page`   | any string                              | `location.pathname` | Which page's thread to load                                             |
| `data-sort`   | `oldest`, `newest`                      | `newest`            | Thread ordering: newest-first puts the latest comment on top            |
| `data-theme`  | `default`, `solarized`, `nord`, `sepia` | `default`           | Color theme from `static/themes/*.css`                                  |
| `data-scheme` | `light`, `dark`                         | follows the OS      | Force a light or dark color scheme regardless of `prefers-color-scheme` |

```html
<script
  src="https://comments.example.com/embed.js"
  data-site="myblog"
  data-page="/posts/hello-world"
  data-sort="newest"
  data-theme="nord"
  data-scheme="dark"
></script>
```

`data-theme` is a file under `themes/`; the embed falls back to `default` if the
named theme can't be loaded. `data-scheme` only makes sense when you want to pin
the look — normally the widget follows the OS setting automatically.

## Features

- Sign in with **Google** and **GitHub** — no passwords, no account management
- **Unlimited reply nesting**, resolved client-side from a single flat query
- Authors delete their own comments; admins delete any. Deletes are soft, so replies survive
- Rate limited to 5 comments per minute per user
- One SQLite file. Backup is `cp`
- Multi-site: one instance serves as many blogs as you list in `ALLOWED_SITES`
- Renders in **Shadow DOM**, so your CSS and the widget's cannot collide
- **Restyleable** with CSS custom properties and `::part()` — no build step, no fork
- Dark mode follows `prefers-color-scheme`
- Timestamps are relative and localise to each visitor's language

## Quick start

```bash
git clone <your-fork> comments && cd comments
cp .env.example .env
```

Edit `.env` — at minimum you need a `SECRET_KEY`, your OAuth credentials, and the domains
in `ALLOWED_ORIGINS` / `ALLOWED_SITES`. [DEPLOY.md](DEPLOY.md) walks through registering the
OAuth apps and explains every variable.

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn src.main:app --reload
```

### Build (optional)

`embed.js` and the CSS run unminified in development. To minify them for
production, run the build step and the server will serve the minified copies from
`dist/` instead of `static/`:

```bash
.venv/bin/pip install -r requirements-build.txt   # rjsmin, rcssmin
.venv/bin/python build.py
```

`build.py` emits `dist/embed.js`, `dist/embed.css` and `dist/themes/*.css`, and
`src/main.py` serves `dist/` whenever it exists — plain `uvicorn` in development
keeps using the readable `static/` originals. Re-run `build.py` after changing
any static file, and delete `dist/` (or leave it out of `.gitignore`'s `dist/`
entry) if you want to go back to source.

Then serve the example page on a **different port**, because same-origin testing hides the
two things most likely to break — CORS and `postMessage`:

```bash
python3 -m http.server 3000 --directory examples
# open http://localhost:3000/demo.html
```

For production, see [DEPLOY.md](DEPLOY.md).

## API

| Method   | Path                             | Auth   | Notes                                                     |
| -------- | -------------------------------- | ------ | --------------------------------------------------------- |
| `GET`    | `/api/comments?site=&page=`      | —      | Flat list ordered by `id`. Deleted rows come back blanked |
| `POST`   | `/api/comments`                  | Bearer | `{site, page, body, parent_id?}` → 201 with the new row   |
| `DELETE` | `/api/comments/{id}`             | Bearer | Author or admin → 204                                     |
| `GET`    | `/auth/{provider}/login?origin=` | —      | `provider` ∈ `google`, `github`                           |
| `GET`    | `/auth/{provider}/callback`      | —      | Returns the `postMessage` bridge page                     |
| `GET`    | `/embed.js`                      | —      | The widget                                                |

Interactive docs at `/docs`.

Error codes worth knowing: `401` bad or expired token, `403` site or origin not allowlisted,
or deleting someone else's comment, `404` parent comment missing, `422` body empty or too
long, `429` rate limited.

## Documentation

|                                    |                                                                                         |
| ---------------------------------- | --------------------------------------------------------------------------------------- |
| [HOW-IT-WORKS.md](HOW-IT-WORKS.md) | Step-by-step walkthrough of the whole flow, the data model, and the security boundaries |
| [DEPLOY.md](DEPLOY.md)             | OAuth setup, every config variable, reverse proxy, TLS, backups, upgrades               |
| [STYLES.md](STYLES.md)             | Restyling the widget: custom properties, `::part()`, recipes                            |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Dev setup, tests, and what kind of changes get merged                                   |
| [examples/](examples/)             | A runnable demo page and snippets for Hugo, Jekyll, Astro, Next.js                      |

## Project layout

```
src/
├── main.py            app wiring: middleware, lifespan, routers
├── config.py          settings from the environment and .env
├── schemas.py         Pydantic in/out models
├── models.py          the table and every SQL query
├── database.py        per-request connection dependency
├── security.py        token signing and the current_user dependency
├── oauth.py           Google/GitHub clients and profile normalisation
└── routers/           auth.py, comments.py

static/embed.js        the widget, vanilla JS, no build step (see STYLES.md)
build.py               minify static/ into dist/ (rjsmin, rcssmin)
test_api.py            run with: .venv/bin/python test_api.py
examples/              demo page and framework snippets
```

[HOW-IT-WORKS.md](HOW-IT-WORKS.md#where-the-code-lives) explains why the boundaries fall
where they do.

## Testing

```bash
.venv/bin/python test_api.py
```

It runs through `TestClient` against a throwaway database and asserts what you cannot check
by clicking around: forged tokens rejected, non-allowlisted sites rejected, empty and
oversized bodies rejected, orphan `parent_id` rejected, the sixth comment in a minute rate
limited, deleting someone else's comment forbidden, and — the subtle one — that after an
admin deletes a parent, the tombstone is blank _and its replies are still there_.

The cross-origin parts cannot be covered by that. Check them by hand with
[examples/demo.html](examples/demo.html), served on a different port.

## What this does not do

No markdown, no editing, no voting or reactions, no email notifications, no pagination, no
moderation queue, no spam filter. Mandatory OAuth login plus the rate limit is the entire
anti-abuse story, and for a personal blog it is enough.

All of these are easy to add later against a schema this small. Add them when you actually
feel the lack, not before — read [CONTRIBUTING.md](CONTRIBUTING.md) first if you plan to
send one upstream.

## License

MIT. See [LICENSE](LICENSE).
