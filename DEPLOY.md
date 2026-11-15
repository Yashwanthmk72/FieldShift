# DEPLOY.md — one Docker service, public link, no login
**Nothing here was executed by the author** (no network or Docker in the build sandbox). Follow the steps and tell us what breaks. The backend serves the frontend, so there is one service and one URL. Visitors need no account: guest mode is automatic.

## Read first: free tiers
- Free instances **sleep** after inactivity (first request can take ~30-60 s) .
- Free instance disks are **ephemeral**: the **SQLite database is wiped on restart/redeploy**, so saved fields and accounts disappear. Fields also live in each visitor's browser, but do not rely on that.
- For judging, open the link yourself a few minutes before the deadline to wake it.

## Option A: Render (web UI)
1. Push this repo to GitHub.
2. Render dashboard -> New -> **Blueprint** -> pick the repo (it reads `render.yaml`), or New -> Web Service -> Runtime **Docker**.
3. Environment variables (Blueprint sets most): `FIELDSHIFT_ENV=production`, `FIELDSHIFT_SECRET_KEY` (32+ random chars; Render can generate), `FIELDSHIFT_COOKIE_SECURE=true`, `FIELDSHIFT_CORS_ORIGINS=https://<your-service>.onrender.com`, optional `DATA_GOV_IN_API_KEY`.
4. Health check path: `/readyz`. Deploy.
5. After the first deploy copy the real URL into `FIELDSHIFT_CORS_ORIGINS` and redeploy. (Production refuses to start without a 32+ char secret and secure cookies.)
6. Check `https://<url>/api/health`: expect `"status":"ok"` or `"degraded"` with a per-provider list.
Optional: `TRUSTED_PROXIES` = Render's proxy CIDRs, otherwise all visitors share one rate-limit bucket for the AI assistant.

## Option B: Fly.io
```
fly launch --no-deploy --copy-config     # edit app name in fly.toml first
fly volumes create fieldshift_data --size 1   # keeps SQLite (volumes are not free)
fly secrets set FIELDSHIFT_SECRET_KEY=$(python -c "import secrets;print(secrets.token_urlsafe(48))")
fly deploy
```
Machines stop when idle (`auto_stop_machines`) and cold-start on the next request. Set `FIELDSHIFT_CORS_ORIGINS` in `fly.toml` to your `https://<app>.fly.dev`.

## Local Docker
`docker compose up --build` (see docker-compose.yml; needs `FIELDSHIFT_SECRET_KEY`). The container listens on `$PORT` (default 8000).

## After deploying
Open `/` (map and fields), `#market`, `#climate` (after analysing a field), `/api/health`. If the map is blank, your network may block unpkg.com (MapLibre) or tile servers.

## Verify the deployment
`python scripts/smoke.py https://<your-url>` — any FAIL is a bug (send it to the developer); WARN means NASA POWER, SoilGrids, FRED or Frankfurter was unreachable from the server.
