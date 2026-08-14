# Deploying

This runs as a single Python process with a SQLite file next to it. A $5 VPS is plenty —
a comment widget is a few requests per page view, and reads never touch the network beyond
your own box.

You need a **domain or subdomain for the API** (`comments.example.com`), separate from the
blog it serves. HTTPS is not optional: Google will not accept a plain-HTTP callback on a
public host, and the OAuth session cookie is marked `Secure` whenever `BASE_URL` starts
with `https`.

---

## 1. Register the OAuth apps

Both providers need a callback URL that matches `{BASE_URL}/auth/{provider}/callback`
**exactly** — protocol, host, path, no trailing slash. A mismatch is the single most common
setup failure, and the error message comes from the provider, not from this app.

### Google

1. [console.cloud.google.com](https://console.cloud.google.com/apis/credentials) → create or
   pick a project.
2. _OAuth consent screen_ → **External** → fill in app name and support email. While the app
   is in _Testing_ only the accounts you list under _Test users_ can sign in — publish it
   when you are ready for real visitors.
3. _Credentials_ → _Create credentials_ → **OAuth client ID** → _Web application_.
4. Under **Authorised redirect URIs** add:
   ```
   https://comments.example.com/auth/google/callback
   ```
5. Copy the client ID and secret into `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`.

### GitHub

1. [github.com/settings/developers](https://github.com/settings/developers) → _OAuth Apps_ →
   **New OAuth App**.
2. _Homepage URL_: your blog. _Authorization callback URL_:
   ```
   https://comments.example.com/auth/github/callback
   ```
3. Generate a client secret and copy both into `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET`.

> One OAuth app per environment. Add a second local app with `http://localhost:8000/...`
> callbacks rather than putting localhost URLs on your production app.

---

## 2. Configure

```bash
cp .env.example .env
python3 -c "import secrets; print(secrets.token_urlsafe(32))"   # → SECRET_KEY
```

| Variable                       | Required        | What it does                                                                     |
| ------------------------------ | --------------- | -------------------------------------------------------------------------------- |
| `SECRET_KEY`                   | **yes**         | Signs auth tokens and the OAuth session cookie. Changing it logs everyone out    |
| `BASE_URL`                     | **yes** in prod | This API's own public URL, no trailing slash. Must match the OAuth callbacks     |
| `ALLOWED_ORIGINS`              | **yes**         | Comma-separated origins the widget may run on. Drives CORS _and_ the login popup |
| `ALLOWED_SITES`                | **yes**         | Comma-separated `data-site` values you accept                                    |
| `ADMIN_EMAILS`                 | no              | Comma-separated. These accounts can delete any comment                           |
| `RATE_LIMIT_PER_MINUTE`        | no              | Comments per minute per user. Defaults to 5                                      |
| `TOKEN_MAX_AGE_DAYS`           | no              | How long a login lasts. Defaults to 30                                           |
| `GOOGLE_CLIENT_ID` / `_SECRET` | per provider    | From step 1                                                                      |
| `GITHUB_CLIENT_ID` / `_SECRET` | per provider    | From step 1                                                                      |
| `DB_PATH`                      | no              | SQLite file path. Defaults to the project root; Docker sets `/data/comments.db`  |

Two of these are load-bearing and worth stating plainly:

- **`ALLOWED_ORIGINS` must list scheme + host + port, exactly as the browser sends it** —
  `https://example.com`, not `example.com` and not a trailing slash. If your blog is
  reachable at both the apex and `www`, list both, or login silently fails on one of them.
- **`ALLOWED_SITES` is what stops your instance being an open database.** Without it, anyone
  who finds the API URL can log in with their own Google account and write rows under any
  `data-site` they invent, forever. It costs nothing and there is no reason to leave it empty.

---

## 3. Run it

### Docker (recommended)

```bash
docker compose up -d
```

The compose file mounts `./data` and forces `DB_PATH=/data/comments.db`, overriding whatever
is in `.env`. That override matters: without it the database lands inside the container
filesystem and vanishes on the next `docker compose build`.

### systemd

If you would rather not run Docker:

```ini
# /etc/systemd/system/comments.service
[Unit]
Description=comments
After=network.target

[Service]
User=comments
WorkingDirectory=/srv/comments
ExecStart=/srv/comments/.venv/bin/uvicorn src.main:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now comments
```

Bind to `127.0.0.1`, never `0.0.0.0` — the reverse proxy is the only thing that should reach
it.

**One worker is the right answer here.** SQLite in WAL mode handles concurrent readers fine,
but multiple worker processes writing the same file buys you contention rather than
throughput, and a comment widget's write volume is measured in comments per hour. Scale by
caching `GET /api/comments` at the proxy, not by adding workers.

---

## 4. Reverse proxy and TLS

### Caddy

Automatic certificates, so this is the whole file:

```caddyfile
comments.example.com {
    reverse_proxy 127.0.0.1:8000
}
```

### nginx

```nginx
server {
    listen 443 ssl http2;
    server_name comments.example.com;

    ssl_certificate     /etc/letsencrypt/live/comments.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/comments.example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host              $host;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Do **not** let the proxy add its own `Access-Control-Allow-Origin` header. The app already
sends one, scoped to `ALLOWED_ORIGINS`; two headers make browsers reject the response
outright, and a proxy-level `*` would quietly undo your allowlist.

---

## 5. Backups

One file. Do not copy it with `cp` while the server is running — WAL mode means the
`-wal` sidecar holds committed data that a naive copy misses. Use SQLite's own backup,
which is consistent under concurrent writes:

```bash
sqlite3 /srv/comments/data/comments.db ".backup '/backups/comments-$(date +%F).db'"
```

A daily cron line is enough:

```cron
0 4 * * * sqlite3 /srv/comments/data/comments.db ".backup '/backups/comments-$(date +\%F).db'"
```

Restoring is copying the file back and restarting. Keep the backups off the same machine.

---

## 6. Upgrading

```bash
git pull
docker compose up -d --build      # or: pip install -r requirements.txt && systemctl restart comments
```

There is no migration system. The schema is a `CREATE TABLE IF NOT EXISTS` that runs on
every boot, so adding a column is a manual `ALTER TABLE` plus an edit to `SCHEMA` in
`src/models.py`. **Take a backup before any schema change** — nothing will do it for you.

---

## Production checklist

- [ ] `SECRET_KEY` is random and unique to this deployment, not the value from `.env.example`
- [ ] `.env` is not committed (it is in `.gitignore` — verify with `git status`)
- [ ] `BASE_URL` uses `https://` and matches both OAuth callbacks exactly
- [ ] `ALLOWED_ORIGINS` lists every hostname your blog answers on, apex and `www`
- [ ] `ALLOWED_SITES` is not empty
- [ ] `ADMIN_EMAILS` contains an address you can actually sign in with — on GitHub, the
      primary email on the account, even if it is private
- [ ] The app binds to `127.0.0.1`, only the proxy is exposed
- [ ] Backups run and you have restored one at least once
- [ ] The Google consent screen is published, not stuck in _Testing_

---

## Troubleshooting

| Symptom                              | Cause                                                                                                                           |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------- |
| `redirect_uri_mismatch`              | `BASE_URL` and the registered callback differ. Compare character by character                                                   |
| Popup opens, closes, nothing happens | The blog's origin is not in `ALLOWED_ORIGINS`, so `postMessage` was refused. Check the browser console on the blog page         |
| Comments load but posting gives 403  | `data-site` is not in `ALLOWED_SITES`                                                                                           |
| CORS error in the console            | Origin missing from `ALLOWED_ORIGINS`, or the proxy is injecting a second CORS header                                           |
| Everyone logged out after a deploy   | `SECRET_KEY` changed — it is probably being regenerated instead of set                                                          |
| Admin delete returns 403             | The token's email is not in `ADMIN_EMAILS`. GitHub users with a hidden email get their primary address; confirm which one it is |
| Comments vanished after rebuild      | `DB_PATH` pointed inside the container instead of the mounted volume                                                            |
