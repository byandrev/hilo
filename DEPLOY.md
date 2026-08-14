# Deploy Hilo

## Vercel

1. Fork this repo.
2. On Vercel, **New Project** → import your fork.
3. Set the environment variables from [.env.example](.env.example) (at minimum `SECRET_KEY`,
   `BASE_URL`, `ALLOWED_ORIGINS`, `ALLOWED_SITES`, `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`,
   and `MONGO_URI` pointing at your database).
4. Deploy.

## Docker

```bash
cp .env.example .env   # fill in the required values
docker compose up -d
```

[docker-compose.yml](docker-compose.yml) uses `ghcr.io/byandrev/hilo:latest` and already
includes a `mongo` service, so this works as-is.

To use an external MongoDB instead (e.g. [Atlas](https://www.mongodb.com/atlas)):

1. Create a database and copy its connection string.
2. Set `MONGO_URI` to that string in `.env`.
3. Remove the `mongo` service and the `MONGO_URI` override / `depends_on` from
   `docker-compose.yml`.
