# Contributing

Thanks for looking. Before you write code, please read the section below — this project has
an opinion about scope, and it is the main reason a pull request gets turned down.

## Philosophy

The API is a small FastAPI package under `src/`, and the widget is one file of vanilla JS.
No ORM, no migrations, no build step, no frontend framework, no npm. That is not an accident
to be fixed, it is the feature. Anyone can read the entire codebase in twenty minutes and
self-host it without learning a stack.

## Where things go

```
src/
├── main.py            app wiring: middleware, lifespan, routers, /embed.js
├── config.py          Settings, from the environment and .env
├── schemas.py         Pydantic in/out models — the request and response contract
├── models.py          the table DDL and every SQL query
├── database.py        the per-request connection dependency, and init_db()
├── security.py        token signing, the current_user dependency, admin check
├── oauth.py           the Google/GitHub clients and profile normalisation
└── routers/
    ├── auth.py        /auth/{provider}/login and /callback
    └── comments.py    /api/comments

static/embed.js        the widget (its CSS contract is STYLES.md)
test_api.py            the whole test suite
```

Two rules keep this layout worth having:

- **SQL only in `models.py`.** A query anywhere else is a review comment. Keeping it in one
  file is what makes "every query is parameterised" checkable by reading, not grepping.
- **Routes decide permission, schemas decide what leaves the server.** Blanking a deleted
  comment lives in `CommentOut.from_row`, not in the route, so a new endpoint cannot leak it
  by forgetting a check. Put that kind of rule in the schema.

Adding an endpoint: schema in `schemas.py` → query in `models.py` → route in a router. If
you find yourself wanting a new top-level module, say why in the PR — the current eight are
meant to be the whole list.

## Setup

```bash
git clone <your-fork> comments && cd comments
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

cp .env.example .env
python3 -c "import secrets; print(secrets.token_urlsafe(32))"   # → SECRET_KEY
```

For local OAuth, register a **separate** development app on each provider with
`http://localhost:8000/auth/{provider}/callback` as the callback — see
[DEPLOY.md](DEPLOY.md#1-register-the-oauth-apps). Keep `ALLOWED_ORIGINS=http://localhost:3000`
and `ALLOWED_SITES=myblog` as shipped in `.env.example`.

Run the API and the example page in two terminals:

```bash
.venv/bin/uvicorn src.main:app --reload
python3 -m http.server 3000 --directory examples
```

Then open <http://localhost:3000/demo.html>.

**Always test on a different port than the API.** Opening the demo from the API's own origin
makes CORS and `postMessage` trivially succeed, and those are exactly the two things that
break in real deployments. If you test same-origin you are not testing this project.

## Tests

```bash
.venv/bin/python test_api.py
```

Plain asserts, no pytest, no fixtures, a throwaway database. It runs in about a second and
prints `ok` at the end. Keep it that way.

If your change touches a rule — a limit, a permission, a validation — add an assert for it.
The existing tests cover exactly what a human clicking around cannot see: forged tokens,
allowlist rejections, the rate limit, deleting someone else's comment, and that a deleted
parent keeps its replies alive. That last one is the kind of test worth writing.

If your change is cross-origin behaviour, it cannot be covered by `test_api.py`. Say so in
the PR and describe what you clicked through instead.

## Style

Match what is already there. Practically:

- Python: standard formatting, type hints where they carry information, no ceremony.
  Dependencies come in through `Annotated` aliases (`DB`, `CurrentUser`) rather than
  `Depends()` in every signature — follow the existing routes.
- JS: vanilla, no transpiling, no dependencies. Anything that touches user data goes through
  `textContent` — **never** `innerHTML`. This is the widget's entire XSS defence.
- CSS: every colour and size in the widget reads a `--comments-*` token, and every styled
  element is a `::part()`. A hardcoded value is something a self-hoster cannot change
  without forking — add a token and document it in [STYLES.md](STYLES.md).
- SQL: always parameterised, and only in `models.py`. Never build a query with string
  formatting.
- Comments explain **why**, not what. If a line is doing something that looks wrong until
  you know the reason, say the reason. The existing comments are the model.

## Security

If you find a vulnerability, please report it privately rather than opening a public issue.

The parts to be careful around, all explained in
[HOW-IT-WORKS.md](HOW-IT-WORKS.md#security-boundaries):

1. The `postMessage` target origin comes from the server-side session, never from the
   callback query string. Changing this is how you leak auth tokens.
2. `ALLOWED_ORIGINS` and `ALLOWED_SITES` are both allowlists. Do not add wildcard support.
3. CORS runs without `allow_credentials` because auth is a header, not a cookie. Leave it.
4. `textContent`, always.

## Pull requests

- One change per PR. A bug fix and a refactor in the same diff is two PRs.
- Describe what breaks without the change. If it is a feature, describe who felt the lack.
- Say how you tested it, including the manual cross-origin steps if they apply.
- Update the docs in the same PR. [HOW-IT-WORKS.md](HOW-IT-WORKS.md) names the modules
  behind each step — if you move code between files, fix the references.

By contributing you agree your work is licensed under the [MIT License](LICENSE).
