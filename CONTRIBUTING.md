# Contributing

Bug reports, fixes, and small focused PRs are welcome. Open an issue first for anything
that changes behavior, adds a dependency, or touches auth, saves you a rewrite if the
direction isn't right. Typos and docs fixes can just be a PR.

## Project layout

```
src/          the FastAPI server (auth, comments API, embed asset routes)
static/       the widget — embed.js, embed.css, themes/*.css, published to npm
landing/      the marketing site + demo page, deployed to GitHub Pages
```

They're independent: changing the widget doesn't require touching the server, and vice
versa.

## Server

```bash
cp .env.example .env
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn src.main:app --reload
```

No ORM migrations, no build step. Keep it that way — a PR that adds either needs a good
reason in the issue first.

## Widget

Plain JS and CSS, no framework, no bundler for development. Edit `static/embed.js` /
`static/embed.css` / `static/themes/*.css` directly and reload the page — see
[STYLING.md](STYLING.md) for how the theming and custom properties fit together.

`static/package.json` has `npm run build` (minifies into `dist/`) and `npm run release`
(publishes to npm) — only maintainers run `release`.

## Style

Match the code around you: short functions, comments that explain _why_ not _what_, no
abstraction for a single caller. If you're unsure a change fits, ask in the issue before
writing the PR.

## Pull requests

- One change per PR, small enough to review in one pass.
- Say what you tested it against — this repo has no test suite, so a manual repro
  (`curl` output, a screenshot, the steps you ran) is what reviewers have to go on.
- Update the relevant doc ([README.md](README.md), [DEPLOY.md](DEPLOY.md),
  [STYLING.md](STYLING.md)) if the change affects what's documented there.

## What's out of scope

Markdown, comment editing, voting/reactions, email notifications, moderation queues —
deliberately not here. Open an issue to make the case before building one; most of these
are easy to add but change the project's shape.
