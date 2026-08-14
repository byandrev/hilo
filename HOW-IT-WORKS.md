# How it works

A step-by-step walk through everything that happens, from the `<script>` tag to a document
in MongoDB. Read this before changing anything — most of the code is short, but a few pieces
are load-bearing in ways that are not obvious from the diff.

## Where the code lives

```
src/
├── main.py            app wiring: middleware, lifespan, routers, /embed.js
├── config.py          Settings, loaded from the environment and .env
├── schemas.py         Pydantic in/out models — the request and response contract
├── models.py          the Comment document and every Mongo query. Queries live nowhere else
├── database.py        the Mongo client and init_db(), which wires up Beanie
├── security.py        token signing, the current_user dependency, admin check
├── oauth.py           the GitHub client and profile normalisation
└── routers/
    ├── auth.py        /auth/{provider}/login and /callback
    └── comments.py    /api/comments

static/embed.js        the widget, vanilla JS, served verbatim
```

Two of those boundaries are deliberate rather than decorative:

- **`models.py` is the only file that queries Mongo.** Every query goes through Beanie's
  typed `Comment` fields, so there is one file to audit instead of grepping the whole app.
- **`schemas.py` owns the wire format**, including which fields of a deleted comment are
  blanked. Routes decide _whether_ you may do a thing; schemas decide _what leaves the
  server_.

---

## Architecture at a glance

There are two separate origins, and that single fact drives every design decision below:

```
   your blog (myblog.com)                 your API (comments.example.com)
  ┌────────────────────────┐             ┌──────────────────────────────┐
  │  <script src=.../>     │─── GET ────▶│  /embed.js                   │
  │       ↓                │             │                              │
  │  widget in Shadow DOM  │─── XHR ────▶│  /api/comments   ──▶ MongoDB │
  │       ↓                │             │                              │
  │  popup window          │──redirect──▶│  /auth/github/login          │
  └────────────────────────┘             └──────────────────────────────┘
                                                      │
                                                      ▼
                                          GitHub OAuth
```

The widget runs on **your blog's** origin. The API lives somewhere else. Browsers block
third-party cookies, so a normal session cookie would never reach the API from the widget.
Everything about the auth flow exists to work around that.

---

## Step 1 — The page loads the script

The browser hits `GET /embed.js`, which FastAPI serves straight off disk
([src/main.py](src/main.py)). No bundling, no minification, no versioning.

## Step 2 — The widget bootstraps itself

`embed.js` runs as an IIFE the moment it is parsed, so `document.currentScript` still
points at its own `<script>` tag. From that one node it derives everything it needs
([static/embed.js:2-6](static/embed.js#L2-L6)):

- **API base URL** — the origin of its own `src`. You never configure it twice.
- **`data-site`** — which site this is, for multi-blog instances.
- **`data-page`** — the thread key. Defaults to `location.pathname`.

It then inserts a `<div>` immediately after the script tag and attaches a **Shadow DOM**
to it ([static/embed.js:8-10](static/embed.js#L8-L10)). This is a native browser feature doing two jobs
for free: your blog's CSS cannot leak in and wreck the widget, and the widget's CSS cannot
leak out and wreck your blog. That is also why the widget renders where you put the tag —
there is no container element to declare.

## Step 3 — Fetching the thread

The widget calls:

```
GET /api/comments?site=myblog&page=/posts/hello-world
```

The server returns a **flat** list ordered by `id` — no nesting, no recursive query
([src/routers/comments.py](src/routers/comments.py)). Deleted comments stay in the list but
come back with their `body`, `author_name`, `author_avatar` and `author_id` blanked out.

That blanking happens in `CommentOut.from_doc` ([src/schemas.py](src/schemas.py)), not in
the route, and that placement is the point: every path that returns a comment goes through
the same response model, so there is no way to add an endpoint that leaks the text of a
deleted comment by forgetting a check.

This endpoint needs no authentication. Reading comments is public.

## Step 4 — Building the tree in the browser

Unlimited nesting without a recursive CTE. The client groups the flat rows by `parent_id`
into a `Map`, then walks depth-first from the roots ([static/embed.js:149-160](static/embed.js#L149-L160)):

```js
const byParent = new Map();
for (const c of rows) {
  if (!byParent.has(c.parent_id)) byParent.set(c.parent_id, []);
  byParent.get(c.parent_id).push(c);
}
(function walk(parent, depth) {
  for (const c of byParent.get(parent) || []) {
    list.append(node(c, depth));
    walk(c.id, depth + 1);
  }
})(null, 0);
```

Roots have `parent_id === null`, so the walk starts there. Indentation is
`min(depth, 5) * 20px` — nesting is unlimited but the visual indent stops growing at level
five, or deep threads slide off the screen on mobile.

Every piece of user data is written with `textContent`, never `innerHTML`
([static/embed.js:35-40](static/embed.js#L35-L40)). That is the entire XSS defence, and it is why the
widget renders plain text only — no markdown, no HTML.

## Step 5 — Signing in (the interesting part)

The widget cannot use a session cookie, because it is a third-party cookie from the
browser's point of view. So the flow is a popup that hands a token back through
`postMessage`:

**5a.** The user clicks _Sign in with GitHub_. The widget opens a popup
([static/embed.js:63-75](static/embed.js#L63-L75)):

```
window.open("https://comments.example.com/auth/github/login?origin=https://myblog.com")
```

**5b.** `/auth/{provider}/login` checks that `origin` is in `ALLOWED_ORIGINS`, **stores it
in the server-side session**, and redirects to the provider
([src/routers/auth.py](src/routers/auth.py)). Authlib generates the OAuth `state` parameter and
keeps it in that same session cookie. That cookie is first-party here — the popup is on
the API's own domain — so it works normally.

**5c.** The user authenticates with GitHub and is redirected back to
`/auth/{provider}/callback?code=...&state=...`.

**5d.** The callback re-reads the origin **from the session, not from the query string**
([src/routers/auth.py](src/routers/auth.py)). This is the security hinge of the whole project. If the
callback trusted an origin passed in the URL, anyone could open the popup from their own
domain and have the token delivered to them. The origin is validated at `/login`, carried
in a signed cookie, and validated again on the way out.

**5e.** Authlib exchanges the code for tokens, then the profile is normalised into one
shape ([src/oauth.py](src/oauth.py)):

- **GitHub** needs an extra `GET /user`. If the user hides their public email, a second
  call to `/user/emails` finds the primary one ([src/oauth.py](src/oauth.py)) —
  without it, admins whose GitHub email is private could never be recognised.

The result is `{"sub": "github:12345", "name": ..., "avatar": ..., "email": ...}`. The
`sub` prefix is what keeps one provider's user 42 from colliding with another's.

**5f.** The server signs that dict with `itsdangerous.URLSafeTimedSerializer` and returns a
tiny HTML page that posts it to the opener and closes itself
([src/routers/auth.py](src/routers/auth.py)):

```js
window.opener.postMessage({type: "comments-auth", token: "...", user: {...}}, "https://myblog.com");
window.close();
```

The second argument to `postMessage` is the allowlisted origin — the browser refuses to
deliver the message anywhere else. The profile is sent alongside the token so the widget
never has to decode it; it only needs the name and avatar to draw the UI.

The `<` characters in the JSON are escaped to `\u003c`, because a display name containing
`</script>` would otherwise break out of the tag.

**5g.** The widget's `message` listener checks `e.origin` matches the API, stores the token
and profile in `localStorage`, and re-renders ([static/embed.js:66-74](static/embed.js#L66-L74)).

**Why a signed token and not a sessions table?** The token _is_ the session. It carries the
profile, it is signed with `SECRET_KEY`, and it is rejected after 30 days by
`max_age` ([src/security.py](src/security.py)). No table, no cleanup job, no lookup per request.
The tradeoff is that you cannot revoke one token — rotating `SECRET_KEY` logs everyone out.

## Step 6 — Posting a comment

The widget sends the token as a normal header, which is why none of this needs cookies:

```
POST /api/comments
Authorization: Bearer <token>
{"site": "myblog", "page": "/posts/hello-world", "body": "...", "parent_id": 41}
```

`current_user` verifies the signature and expiry ([src/security.py](src/security.py)); a
tampered token raises `BadSignature` and returns 401. Then, in order
([src/routers/comments.py](src/routers/comments.py)):

1. **Pydantic** enforces the field limits — body 1–4000 chars, site ≤64, page ≤512 → 422.
2. **Whitespace-only bodies** are rejected by a validator on `CommentIn`
   ([src/schemas.py](src/schemas.py)) → 422. `"   "` passes `min_length` but is not a
   comment. The validator also strips the body, so the route never has to remember to.
3. **`site` must be in `ALLOWED_SITES`** → 403. Without this check anyone who finds your
   API URL can store arbitrary data in your database forever.
4. **`parent_id`, if present, must exist on the same `(site, page)`** → 404. This stops
   replies being grafted onto threads they don't belong to.
5. **Rate limit** — one count over the last 60 seconds for this author, max 5 → 429.
   One query, no Redis.
6. **Insert.** The author's name and avatar are copied _into the row_.

The reply form is a single `<form>` element that gets moved in the DOM to sit under
whichever comment you are replying to ([static/embed.js:77-102](static/embed.js#L77-L102)) — a DOM move is
native and needs no state tracking.

## Step 7 — Deleting

`DELETE /api/comments/{id}` allows the original author, or anyone whose token email is in
`ADMIN_EMAILS` ([src/routers/comments.py](src/routers/comments.py)).

It sets `deleted = true` — it does **not** remove the document. A real delete would
silently destroy an entire sub-thread of replies written by other people. Instead the
document survives as a tombstone rendered as _[deleted]_, and the conversation hanging off
it stays readable.

---

## Data model

One collection. That's it.

```python
class Comment(Document):
    site: str            # data-site, multi-blog on one instance
    page: str             # data-page, the thread key
    parent_id: PydanticObjectId | None = None   # None = top level
    body: str
    author_id: str        # "github:678"
    author_name: str
    author_avatar: str | None = None
    created_at: datetime  # UTC, defaults to now
    deleted: bool = False

    class Settings:
        name = "comments"
        indexes = [IndexModel([("site", 1), ("page", 1), ("_id", 1)])]
```

**There is deliberately no `users` collection.** The author's name and avatar are
denormalised onto every comment. A comment widget has no profile pages, no "edit your
display name", no user list — so the join you would be saving never happens, and the write
path stays a single insert. The visible consequence: if someone changes their GitHub
avatar, their old comments keep the old one.

**One client for the app's lifetime** ([src/database.py](src/database.py)), opened once at
startup instead of per request. Mongo's driver pools and multiplexes connections itself, so
there is no thread-safety question to sidestep the way SQLite's per-request connection did.

---

## Security boundaries

These are the checks that are load-bearing. If you modify this project, don't remove them:

1. **`ALLOWED_ORIGINS`** gates both the CORS middleware and the login popup. An origin not
   on this list cannot read the API from a browser and cannot receive a token.
2. **The `postMessage` target origin comes from the server session**, never from the
   callback URL. This is what stops token theft via a popup opened from an attacker's page.
3. **`ALLOWED_SITES`** stops your instance being used as an open write-anywhere database.
4. **`textContent` everywhere** in the widget. No user string ever reaches `innerHTML`.
5. **Typed queries** on every access — `Comment.field == value` through Beanie, never a
   hand-built filter dict built from string interpolation.
6. **Rate limiting** at 5 comments/minute/user, on top of mandatory OAuth login.

CORS is configured **without** `allow_credentials`, because auth rides in the
`Authorization` header rather than a cookie. That avoids the classic
wildcard-plus-credentials footgun entirely.
