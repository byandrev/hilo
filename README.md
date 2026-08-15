# Hilo

Self-hosted comments for blogs and static sites. Open source, privacy-first, and
minimalist by design: no ads, no tracking, no third party reading your visitors' data.
One `<script>` tag, sign-in with GitHub, MIT licensed.

A small FastAPI + MongoDB backend that you run yourself — on a VPS with Docker, or on
Vercel. See [DEPLOY.md](DEPLOY.md).

## The widget

The frontend is published as [`hilo_comments`](https://www.npmjs.com/package/hilo_comments)
on npm — `embed.js`, `embed.css`, and a few themes, no build step required. It just talks
to your own instance of the API, so **you need the server running** ([DEPLOY.md](DEPLOY.md))
before the widget will do anything.

```html
<!doctype html>
<meta charset="utf-8" />
<title>My blog post</title>

<link
  rel="stylesheet"
  href="https://cdn.jsdelivr.net/npm/hilo_comments/embed.css"
/>
<link
  rel="stylesheet"
  href="https://cdn.jsdelivr.net/npm/hilo_comments/themes/nord.css"
/>

<h1>Just some blog post</h1>

<script
  src="https://cdn.jsdelivr.net/npm/hilo_comments/embed.js"
  data-site="myblog"
  data-page="/posts/hello-world"
  data-api="https://hilo-comments.vercel.app"
></script>
```

The widget renders where you put the `<script>` tag. `data-api` is your own server's URL;
everything else about the CSS — themes, custom properties — is in [STYLING.md](STYLING.md).

See it running: [byandrev.github.io/hilo/examples/demo.html](https://byandrev.github.io/hilo/examples/demo.html).

### `data-*` attributes

| Attribute     | Values             | Default             | What it does                                                       |
| ------------- | ------------------ | ------------------- | ------------------------------------------------------------------ |
| `data-api`    | your server's URL  | —                   | Required. Where the widget sends requests                          |
| `data-site`   | any string         | —                   | Required. The comment feed's namespace; must be in `ALLOWED_SITES` |
| `data-page`   | any string         | `location.pathname` | Which page's thread to load                                        |
| `data-sort`   | `oldest`, `newest` | `newest`            | Thread ordering                                                    |
| `data-scheme` | `light`, `dark`    | follows the OS      | Force a color scheme regardless of `prefers-color-scheme`          |

## Features

- Sign in with **GitHub** — no passwords, no account management
- Unlimited reply nesting, resolved client-side from a single flat query
- Authors delete their own comments; admins delete any. Deletes are soft, so replies survive
- Rate limited per user
- MongoDB via [Beanie](https://beanie-odm.dev)
- Multi-site: one instance serves as many blogs as you list in `ALLOWED_SITES`
- No Shadow DOM, no build step — restyle with plain CSS custom properties
- Dark mode follows `prefers-color-scheme`

## Running the server

```bash
git clone <your-fork> comments && cd comments
cp .env.example .env   # SECRET_KEY, GITHUB_CLIENT_ID/SECRET, ALLOWED_ORIGINS, ALLOWED_SITES, MONGO_URI, MONGO_DB

python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn src.main:app --reload
```

For production — Docker on a VPS or Vercel — see [DEPLOY.md](DEPLOY.md).

## API

| Method   | Path                                            | Auth   | Notes                                                         |
| -------- | ----------------------------------------------- | ------ | ------------------------------------------------------------- |
| `GET`    | `/api/comments?site=&page=`                     | —      | Flat list ordered by creation. Deleted rows come back blanked |
| `POST`   | `/api/comments`                                 | Bearer | `{site, page, body, parent_id?}` → 201 with the new row       |
| `DELETE` | `/api/comments/{id}`                            | Bearer | Author or admin → 204                                         |
| `GET`    | `/auth/{provider}/login?origin=`                | —      | `provider` = `github`                                         |
| `GET`    | `/auth/{provider}/callback`                     | —      | Returns the `postMessage` bridge page                         |
| `GET`    | `/embed.js`, `/embed.css`, `/themes/{name}.css` | —      | The widget assets, also served by your own instance           |

Interactive docs at `/docs`.

## Documentation

|                                        |                                                           |
| -------------------------------------- | --------------------------------------------------------- |
| [DEPLOY.md](DEPLOY.md)                 | Deploying on Vercel or Docker, environment variables      |
| [STYLING.md](STYLING.md)               | Restyling the widget: base CSS, themes, custom properties |
| [landing/examples/](landing/examples/) | A runnable demo page                                      |

## License

MIT. See [LICENSE](LICENSE).
