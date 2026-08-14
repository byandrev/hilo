# Examples

## Running the demo

Start the API from the project root, then serve this folder on a **different port**:

```bash
.venv/bin/uvicorn main:app --reload            # terminal 1, port 8000
python3 -m http.server 3000 --directory examples   # terminal 2
```

Open <http://localhost:3000/demo.html>.

The two ports are the point. Served from the API's own origin, CORS and `postMessage` both
succeed trivially and you learn nothing — those are the two things that actually break in
production. `.env.example` ships with `ALLOWED_ORIGINS=http://localhost:3000` for exactly
this reason.

## The tag

```html
<script src="https://comments.example.com/embed.js"
        data-site="myblog" data-page="/posts/hello-world"></script>
```

| Attribute | Required | Meaning |
|---|---|---|
| `src` | yes | `/embed.js`. The widget reads its API origin from this by default — override with `data-api` if you download and self-host `embed.js` elsewhere |
| `data-site` | yes | Which site this is. Must be listed in the server's `ALLOWED_SITES` |
| `data-page` | no | The thread key. Defaults to `location.pathname` |
| `data-api` | no | Backend origin, when `src` doesn't point at the API itself (a self-hosted `embed.js`) |
| `data-css` | no | URL of a downloaded, self-hosted `embed.css`, instead of the one served by the API |

The widget renders **where you put the tag** — there is no container element to declare. Put
the script exactly where you want comments to appear.

### About `data-page`

It is just a string key. The default (`location.pathname`) is right for most blogs, but set
it explicitly when the URL is not a stable identity:

- The same post is reachable at `/posts/x` and `/posts/x/` — those are two separate threads.
- URLs carry query strings or tracking parameters — `location.pathname` already ignores those.
- You might reorganise your permalinks later. A stable ID (`data-page="post-42"`) survives
  the move; a path does not.

## Framework snippets

### Hugo

`layouts/partials/comments.html`:

```html
<script src="https://comments.example.com/embed.js"
        data-site="myblog" data-page="{{ .RelPermalink }}"></script>
```

Include it in your single template with `{{ partial "comments.html" . }}`.

### Jekyll

`_includes/comments.html`:

```html
<script src="https://comments.example.com/embed.js"
        data-site="myblog" data-page="{{ page.url }}"></script>
```

Then `{% include comments.html %}` in `_layouts/post.html`.

### Astro

```astro
---
const { slug } = Astro.props;
---
<script is:inline src="https://comments.example.com/embed.js"
        data-site="myblog" data-page={`/posts/${slug}`}></script>
```

`is:inline` is required — without it Astro tries to process and bundle the script, which
strips the `data-*` attributes the widget reads from its own tag.

### Next.js (app router)

```jsx
export default function Comments({ page }) {
  return (
    <script
      async
      src="https://comments.example.com/embed.js"
      data-site="myblog"
      data-page={page}
    />
  );
}
```

The widget writes into a `<div>` it inserts itself, outside React's tree, so React will not
fight it over the DOM. Do not render it inside a component that remounts often.

### Plain HTML

See [demo.html](demo.html).

## Notes

- **Put the tag where you want the comments.** The widget renders in place. If you place it
  before any body content the browser parses it into `<head>`, and the widget falls back to
  the end of `<body>` — which is probably not where you wanted it.
- **The widget renders in Shadow DOM**, so your site's CSS cannot reach inside it. Restyle
  it with the `--comments-*` custom properties or `::part()` — see
  [STYLES.md](../STYLES.md).
- **Dark mode is automatic**, via `prefers-color-scheme`. If your site has its own theme
  toggle that ignores the OS setting, set the colour tokens under whatever selector it
  flips — [STYLES.md](../STYLES.md#dark-mode) shows how.
- **The script is not deferred by default.** Add `async` if you would rather it not block
  parsing; the widget does not care when it runs.
