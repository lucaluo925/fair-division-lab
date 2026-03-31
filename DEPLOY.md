# World Monitor — Deployment Guide

> One-command Docker deployment for [koala73/worldmonitor](https://github.com/koala73/worldmonitor)

---

## Prerequisites

| Requirement | Min version | Notes |
|---|---|---|
| Docker | 24+ | `docker --version` |
| Docker Compose | v2 (plugin) | `docker compose version` |
| Node.js | 22+ | Only for running seed scripts on the host |
| Git | any | For cloning |
| RAM | 2 GB | 4 GB recommended |
| Disk | 3 GB | Image + Redis data |

---

## 1. Clone the repository

```bash
git clone https://github.com/koala73/worldmonitor.git
cd worldmonitor
npm install       # needed only for the seed scripts (runs on host)
```

---

## 2. Configure environment variables

All keys are **optional** — the dashboard works without any of them; features degrade gracefully when keys are absent.

```bash
cp .env.example .env
```

Then edit `.env` with any keys you have. The most impactful free ones:

```bash
# LLM summaries (pick one)
GROQ_API_KEY=          # https://console.groq.com  (free, 14 400 req/day)
OPENROUTER_API_KEY=    # https://openrouter.ai     (free, 50 req/day)

# Markets
FINNHUB_API_KEY=       # https://finnhub.io        (free tier)
FRED_API_KEY=          # https://fred.stlouisfed.org/docs/api/api_key.html
EIA_API_KEY=           # https://www.eia.gov/opendata/

# Geo/conflict
NASA_FIRMS_API_KEY=    # https://firms.modaps.eosdis.nasa.gov  (free)
ACLED_ACCESS_TOKEN=    # https://acleddata.com                 (free for researchers)

# Transport
AISSTREAM_API_KEY=     # https://aisstream.io  (free)
AVIATIONSTACK_API=     # https://aviationstack.com (free tier)
```

For a production server you can also create `docker-compose.override.yml` (gitignored) to keep secrets out of `.env`:

```yaml
# docker-compose.override.yml  (never committed — gitignored)
services:
  worldmonitor:
    environment:
      GROQ_API_KEY: "gsk_xxxxxxxxxxxx"
      FINNHUB_API_KEY: "xxxxxxxxxxxx"
  ais-relay:
    environment:
      AISSTREAM_API_KEY: "xxxxxxxxxxxx"
```

---

## 3. One-command deployment (Docker)

```bash
# Build images and start all four containers in the background
docker compose up -d --build
```

This starts:

| Container | Purpose | Exposed port |
|---|---|---|
| `worldmonitor` | nginx (static) + Node.js API | `3000` → internal `8080` |
| `worldmonitor-redis` | Data store | internal only |
| `worldmonitor-redis-rest` | Upstash-compatible REST proxy | `127.0.0.1:8079` |
| `worldmonitor-ais-relay` | Live vessel/aircraft WebSocket | internal only |

### 3a. Seed Redis with live data

After the stack is healthy, run the bundled seeder:

```bash
./scripts/run-seeders.sh
```

The health check at `/api/health` shows `0/55 OK` until seeders have run at least once.

### 3b. Open the dashboard

```bash
open http://localhost:3000   # macOS
# or navigate to http://<your-server-ip>:3000
```

---

## 4. Development mode (no Docker)

```bash
node --version   # must be ≥ 22
npm install
npm run dev      # Vite dev server → http://localhost:5173
```

The dev server proxies `/api/*` requests through Vite's built-in proxy (configured in `vite.config.ts`). You still need Redis running for full functionality — the quickest way:

```bash
docker compose up -d redis redis-rest     # only Redis services
npm run dev
```

---

## 5. Custom port

Change the host port by setting `WM_PORT` before starting:

```bash
WM_PORT=8080 docker compose up -d --build
# or add WM_PORT=8080 to your .env
```

---

## 6. Automated data refresh (cron)

Seed data expires. Add a cron job to keep it fresh:

```bash
crontab -e
# add:
*/30 * * * * cd /opt/worldmonitor && ./scripts/run-seeders.sh >> /tmp/wm-seeders.log 2>&1
```

---

## 7. Updating

```bash
git pull
docker compose down
docker compose up -d --build
./scripts/run-seeders.sh
```

> **Note:** `docker compose down` without `-v` preserves the `redis-data` volume (your cached data). Add `-v` only if you want a clean slate.

---

## 8. Vercel deployment (alternative / for API functions)

The `api/` directory contains Vercel Edge Functions. The frontend can be deployed to Vercel while pointing at a self-hosted relay for WebSocket/AIS data.

```bash
# Install Vercel CLI
npm i -g vercel

# Set all required env vars in Vercel dashboard, then:
vercel --prod
```

Key env vars for Vercel:
- `GROQ_API_KEY` / `OPENROUTER_API_KEY` — AI summaries
- `UPSTASH_REDIS_REST_URL` + `UPSTASH_REDIS_REST_TOKEN` — cross-user cache (get a free DB at upstash.com)
- `WS_RELAY_URL` — URL of your Railway/self-hosted relay service
- All data API keys listed in `.env.example`

---

## 9. Troubleshooting

| Symptom | Fix |
|---|---|
| Health check `0/55 OK` | Run `./scripts/run-seeders.sh` — seeders haven't run yet |
| `npm ci` fails during build | Lockfile mismatch: `docker run --rm -v $(pwd):/app -w /app node:22-alpine npm install --package-lock-only` |
| No vessel data on map | Set `AISSTREAM_API_KEY` in both `worldmonitor` and `ais-relay` env |
| No wildfire layer | Set `NASA_FIRMS_API_KEY` |
| No internet-outage layer | Requires paid `CLOUDFLARE_API_TOKEN` (Cloudflare Radar) |
| Port 3000 already in use | Set `WM_PORT=<other>` in `.env` |
| Container won't start (nginx) | `docker logs worldmonitor` — check for missing `gettext` in Alpine base image |

---

## 10. Complete command reference

```bash
# --- First-time setup ---
git clone https://github.com/koala73/worldmonitor.git && cd worldmonitor
npm install
cp .env.example .env                    # edit with your keys

# --- Start ---
docker compose up -d --build            # build + start all services
./scripts/run-seeders.sh                # populate Redis

# --- Check status ---
docker compose ps
docker logs worldmonitor --tail 50
curl http://localhost:3000/api/health

# --- Stop (keep data) ---
docker compose down

# --- Stop + wipe data ---
docker compose down -v

# --- Update ---
git pull && docker compose down && docker compose up -d --build && ./scripts/run-seeders.sh

# --- Build image only ---
docker build -t worldmonitor:latest -f Dockerfile .

# --- Custom port ---
WM_PORT=8080 docker compose up -d --build
```
