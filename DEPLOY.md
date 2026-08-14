# Deploying

This runs as a single Python process talking to MongoDB. A $5 VPS is plenty — a comment
widget is a few requests per page view, and both processes can share the same box.

You need a **domain or subdomain for the API** (`comments.example.com`), separate from the
blog it serves. HTTPS is not optional: GitHub will not accept a plain-HTTP callback on a
public host, and the OAuth session cookie is marked `Secure` whenever `BASE_URL` starts
with `https`.

---

## 1. Register the OAuth app

The provider needs a callback URL that matches `{BASE_URL}/auth/{provider}/callback`
**exactly** — protocol, host, path, no trailing slash. A mismatch is the single most common
setup failure, and the error message comes from the provider, not from this app.

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
| `GITHUB_CLIENT_ID` / `_SECRET` | **yes**       | From step 1                                                                      |
| `MONGO_URI`                    | no              | Mongo connection string. Defaults to `mongodb://localhost:27017`; Docker points it at the `mongo` service |
| `MONGO_DB`                     | no              | Database name. Defaults to `hilo`                                                |

Two of these are load-bearing and worth stating plainly:

- **`ALLOWED_ORIGINS` must list scheme + host + port, exactly as the browser sends it** —
  `https://example.com`, not `example.com` and not a trailing slash. If your blog is
  reachable at both the apex and `www`, list both, or login silently fails on one of them.
- **`ALLOWED_SITES` is what stops your instance being an open database.** Without it, anyone
  who finds the API URL can log in with their own GitHub account and write rows under any
  `data-site` they invent, forever. It costs nothing and there is no reason to leave it empty.

---

## 3. Run it

### Docker (recommended)

```bash
docker compose up -d
```

The compose file also brings up a `mongo` service with `./data` mounted for its data
directory, and points `MONGO_URI` at it, overriding whatever is in `.env`. That override
matters: without it the app looks for Mongo on `localhost`, which is the container itself,
not the `mongo` service.

### systemd

If you would rather not run Docker, install MongoDB separately (`apt install mongodb-org` or
your distro's package) and point `MONGO_URI` at it.

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

**One worker is still plenty.** MongoDB handles concurrent readers and writers fine across
workers, but a comment widget's write volume is measured in comments per hour, so there is
nothing to gain from more of them. Scale by caching `GET /api/comments` at the proxy, not by
adding workers.

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

Use `mongodump`, which is consistent under concurrent writes:

```bash
mongodump --uri "$MONGO_URI" --db hilo --archive=/backups/hilo-$(date +%F).archive
```

A daily cron line is enough:

```cron
0 4 * * * mongodump --uri "mongodb://localhost:27017" --db hilo --archive=/backups/hilo-$(date +\%F).archive
```

Restore with `mongorestore --archive=... --nsInclude 'hilo.*'`. Keep the backups off the
same machine.

---

## 6. Upgrading

```bash
git pull
docker compose up -d --build      # or: pip install -r requirements.txt && systemctl restart comments
```

There is no migration system. MongoDB has no schema to alter — adding a field is just an
edit to the `Comment` document in `src/models.py`; existing documents simply don't have it
until they're next written. **Take a backup before any change that renames or removes a
field** — nothing will do it for you.

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
- [ ] The GitHub OAuth app is fully configured and its callback URL matches `BASE_URL`

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
| Comments vanished after rebuild      | `MONGO_URI` pointed at a Mongo whose data volume isn't mounted, or at the wrong `MONGO_DB`                                      |
