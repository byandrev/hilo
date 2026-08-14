# Styling the widget

The widget renders inside a **Shadow DOM**. Your site's stylesheet cannot reach into it,
and its styles cannot leak out onto your page. That isolation is the feature — it is why
the widget looks the same on a Tailwind site and a hand-written one.

It also means `.comment { color: red }` in your stylesheet does nothing. Customisation
goes through two native mechanisms instead:

| | For | Effort |
|---|---|---|
| **[Custom properties](#custom-properties)** | Colours, spacing, fonts, radius | One `:root` block |
| **[`::part()`](#part)** | Anything the tokens don't cover | One rule per element |

Neither needs a build step, a config file, or a redeploy of the API.

---

## Custom properties

CSS custom properties **inherit through the shadow boundary**. Set them anywhere above the
widget — `:root` is easiest — and the widget picks them up.

```css
:root {
  --comments-accent: #2563eb;
  --comments-radius: 4px;
  --comments-gap: 2rem;
}
```

That's the whole API. Every token, with its default:

### Typography

| Token | Default | |
|---|---|---|
| `--comments-font` | `system-ui, -apple-system, "Segoe UI", sans-serif` | Font stack |
| `--comments-font-size` | `0.9375rem` | Base size — everything else is relative to it |
| `--comments-line-height` | `1.6` | |

### Colour

| Token | Light | Dark | |
|---|---|---|---|
| `--comments-text` | `#18181b` | `#f4f4f5` | Comment bodies, author names |
| `--comments-muted` | `#71717a` | `#a1a1aa` | Timestamps, buttons, empty state |
| `--comments-bg` | `transparent` | `transparent` | Widget background |
| `--comments-surface` | `transparent` | `transparent` | Textarea background |
| `--comments-border` | `#e4e4e7` | `#27272a` | Hairlines and the reply rail |
| `--comments-accent` | `#18181b` | `#f4f4f5` | Post button, focus rings |
| `--comments-accent-text` | `#ffffff` | `#18181b` | Text **on** the accent |
| `--comments-danger` | `#dc2626` | `#f87171` | Errors, delete on hover |

### Layout

| Token | Default | |
|---|---|---|
| `--comments-radius` | `8px` | Buttons and the textarea. `0` for square, `999px` for pill |
| `--comments-gap` | `1.5rem` | Vertical rhythm between comments |
| `--comments-indent` | `1.5rem` | Step per nesting level |
| `--comments-avatar-size` | `28px` | |

### Dark mode

The widget follows `prefers-color-scheme` on its own — do nothing and it works.

**But the moment you set a colour token, you own both themes.** A token you set wins in
light *and* dark, because your value is the fallback the widget reads in either mode. So
this leaves you with black text on a dark background:

```css
/* Broken in dark mode */
:root { --comments-text: #18181b; }
```

Set it per scheme instead:

```css
:root { --comments-text: #18181b; }
@media (prefers-color-scheme: dark) {
  :root { --comments-text: #f4f4f5; }
}
```

If your site has its own theme toggle that ignores the OS setting, scope the tokens to
whatever selector it flips — the widget just reads whatever is inherited:

```css
[data-theme="dark"] { --comments-text: #f4f4f5; --comments-border: #27272a; }
```

---

## `::part()`

When the tokens run out, `::part()` reaches individual elements from your stylesheet with
full CSS. The host element carries the class `comments-widget`:

```css
.comments-widget::part(author) {
  font-variant: small-caps;
  letter-spacing: 0.03em;
}

.comments-widget::part(comment) {
  padding-bottom: 1.5rem;
  border-bottom: 1px solid var(--comments-border);
}
```

Every class inside the widget is exposed as a part of the same name:

| Part | Element |
|---|---|
| `widget` | The outermost container |
| `bar` | The sign-in / signed-in row above the composer |
| `session` | The signed-in user's name |
| `thread` | The list of comments |
| `comment` | One comment. Replies also carry `nested` |
| `nested` | Any comment below the top level |
| `meta` | The author + timestamp row |
| `avatar` | The avatar image |
| `author` | The author name |
| `time` | The relative timestamp (`<time>`; hover shows the exact date) |
| `body` | The comment text |
| `tombstone` | The `[deleted]` placeholder |
| `actions` | The Reply / Delete row |
| `action` | A single Reply or Delete button. Delete also carries `danger` |
| `form` | A composer, top-level or reply |
| `textarea` | The input |
| `primary` | The Post and Sign in buttons |
| `error` | Inline error text |
| `empty` | "No comments yet." |
| `loading` | "Loading…" |

Two limits worth knowing before you lean on this: `::part()` cannot select **inside** a
part (`::part(comment) .author` does not work — target `::part(author)` directly), and
pseudo-classes go **after** the part (`::part(action):hover`).

---

## Recipes

### Match your brand

```css
:root {
  --comments-font: "Inter", sans-serif;
  --comments-accent: #7c3aed;
  --comments-radius: 6px;
}
```

### Cards instead of a plain list

```css
.comments-widget::part(comment) {
  background: var(--comments-surface, #fafafa);
  border: 1px solid var(--comments-border, #e4e4e7);
  border-radius: 10px;
  padding: 1rem;
}
.comments-widget::part(nested) { border-left-width: 3px; }
```

### Tighter, denser thread

```css
:root {
  --comments-gap: 1rem;
  --comments-indent: 1rem;
  --comments-font-size: 0.875rem;
  --comments-avatar-size: 22px;
}
```

### Serif, editorial

```css
:root {
  --comments-font: Georgia, "Times New Roman", serif;
  --comments-accent: #b45309;
  --comments-surface: #fffdfa;
  --comments-radius: 2px;
  --comments-gap: 1.75rem;
}
.comments-widget::part(author) { font-variant: small-caps; }
```

### Constrain the width

The widget fills its container, so size the container:

```css
.comments-widget { max-width: 42rem; margin-inline: auto; }
```

Note this is a plain class selector, not `::part()` — the host element itself *is* in your
document, so ordinary CSS applies to it. Only its insides are behind the shadow boundary.

---

## Changing the text

All user-facing strings sit in a `TEXT` object at the top of
[`static/embed.js`](static/embed.js):

```js
const TEXT = {
  empty: "No comments yet.",
  placeholder: "Write a comment…",
  submit: "Post",
  reply: "Reply",
  // …
};
```

Edit them for another language and reload — there is no build step. Timestamps are not in
there because they localise themselves: they are rendered with `Intl.RelativeTimeFormat`
using the **visitor's** locale, so a Spanish visitor sees "hace 2 horas" while the buttons
stay in whatever language you set.

---

## Going further

Anything the tokens and parts cannot express means editing the `<style>` block at the top
of `static/embed.js` directly. It is about 90 lines of plain CSS with no preprocessor, and
it is served straight off disk — edit, reload, done.

If you find yourself needing the same override on every site you run, that is worth an
issue: a missing token is a bug in this document as much as in the code.
