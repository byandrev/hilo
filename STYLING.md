# Styling

No Shadow DOM: the widget renders inside a `.comments-widget` div, and every class in it
is prefixed `hilo-`, so it can't collide with anything else on the page.

## 1. Base styles

Required. Link `embed.css`, either from your own server or the CDN:

```html
<link rel="stylesheet" href="https://example.com/embed.css" />

<!-- or -->

<link
  rel="stylesheet"
  href="https://cdn.jsdelivr.net/npm/hilo_comments/embed.css"
/>
```

You can also download the file and serve it as a static asset on your own page instead of
linking it live.

## 2. Theme (optional)

A theme is just a CSS file that overrides the same custom properties `embed.css` reads.
Link one after `embed.css`, from [static/themes/](static/themes) (`default`, `nord`, `solarized`,
`sepia`) — same options apply: your own server, the CDN, or a downloaded copy.

```html
<link rel="stylesheet" href="https://example.com/themes/nord.css" />

<!-- or -->

<link
  rel="stylesheet"
  href="https://cdn.jsdelivr.net/npm/hilo_comments/themes/nord.css"
/>
```

## 3. Custom properties

Or set the tokens yourself, from your own stylesheet — no theme file needed:

```css
.comments-widget {
  --comments-accent: #2563eb;
  --comments-radius: 4px;
}
```

| Token                       | Default                                            |
| --------------------------- | -------------------------------------------------- |
| `--comments-font`           | `system-ui, -apple-system, "Segoe UI", sans-serif` |
| `--comments-font-size`      | `0.9375rem`                                        |
| `--comments-line-height`    | `1.6`                                              |
| `--comments-text`           | `#1a1a1a`                                          |
| `--comments-muted`          | `#6f6f6f`                                          |
| `--comments-bg`             | `transparent`                                      |
| `--comments-surface`        | `#ffffff`                                          |
| `--comments-border`         | `#e2e2e2`                                          |
| `--comments-accent`         | `#1a1a1a`                                          |
| `--comments-accent-text`    | `#ffffff`                                          |
| `--comments-danger`         | `#c0392b`                                          |
| `--comments-radius`         | `6px`                                              |
| `--comments-widget-padding` | `1.25rem`                                          |
| `--comments-gap`            | `1.25rem`                                          |
| `--comments-indent`         | `1.25rem`                                          |
| `--comments-avatar-size`    | `24px`                                             |

## 4. Dark mode

The widget follows `prefers-color-scheme` automatically — the color tokens above have a
built-in dark variant, no setup needed. To pin it regardless of the OS, use `data-scheme`
on the script tag:

```html
<script ... data-scheme="dark"></script>
```

## 5. Anything else

There's no Shadow DOM boundary, so your stylesheet can also target the markup directly —
`.comments-widget .hilo-primary`, `.hilo-avatar`, etc. See [static/embed.css](static/embed.css)
for the full class list.
