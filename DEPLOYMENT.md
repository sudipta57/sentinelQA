# SentinelQA — Deployment Guide

A complete guide to running SentinelQA locally and deploying it for free to the cloud.

---

## Table of Contents

1. [Project Structure](#project-structure)
2. [Prerequisites](#prerequisites)
3. [Local Development (without Docker)](#local-development-without-docker)
4. [Local Development (with Docker)](#local-development-with-docker)
5. [Free Cloud Deployment](#free-cloud-deployment)
   - [Backend → Railway](#backend--railway)
   - [Frontend → Vercel](#frontend--vercel)
6. [Environment Variables Reference](#environment-variables-reference)
7. [Troubleshooting](#troubleshooting)

---

## Project Structure

```
sentinelqa2/
├── backend/          # FastAPI + Playwright agent
│   ├── app/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/         # React + Vite + Tailwind UI
│   ├── src/
│   ├── Dockerfile
│   └── package.json
├── demo-app/         # Built-in demo target app
├── docker-compose.yml
├── .env.example
└── DEPLOYMENT.md     # ← you are here
```

---

## Prerequisites

| Tool | Version | Install |
|---|---|---|
| Python | 3.11+ | [python.org](https://python.org) |
| Node.js | 18+ | [nodejs.org](https://nodejs.org) |
| Docker Desktop | latest | [docker.com](https://docker.com) |
| Git | any | [git-scm.com](https://git-scm.com) |

You also need:
- A **Gemini API key** → [aistudio.google.com](https://aistudio.google.com/app/apikey) (free)
- A **Supabase** project for the database → [supabase.com](https://supabase.com) (free tier)

---

## Local Development (without Docker)

### 1. Clone and configure environment

```bash
git clone https://github.com/YOUR_USERNAME/sentinelqa2.git
cd sentinelqa2

# Copy the example env file and fill in your values
cp .env.example .env
```

Edit `.env`:

```env
GEMINI_API_KEY=your_gemini_api_key_here
CORS_ORIGIN=http://localhost:3000
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres
```

### 2. Set up the backend

```bash
cd backend

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright's Chromium browser
playwright install chromium

# Start the API server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend is now running at → **http://localhost:8000**  
API docs available at → **http://localhost:8000/docs**

### 3. Set up the frontend

Open a **new terminal**:

```bash
cd frontend

# Install dependencies
npm install

# Start the dev server
npm run dev
```

Frontend is now running at → **http://localhost:3000**

### 4. (Optional) Start the demo app

Open another terminal:

```bash
cd demo-app
npm install
npm run dev
```

Demo app runs at → **http://localhost:3001**

---

## Local Development (with Docker)

This is the easiest way — one command starts everything.

### 1. Configure environment

```bash
cp .env.example .env
# Edit .env with your GEMINI_API_KEY and DATABASE_URL
```

### 2. Start all services

```bash
docker compose up -d
```

This starts:
- **Backend** → http://localhost:8000
- **Frontend** → http://localhost:3000
- **Demo App** → http://localhost:3001

### Useful Docker commands

```bash
# View live logs
docker compose logs -f

# View logs for a specific service
docker compose logs -f backend

# Stop all services
docker compose down

# Rebuild after code changes
docker compose up -d --build

# Force a clean rebuild (e.g. after adding dependencies)
docker compose build --no-cache backend
docker compose up -d
```

### Health check

```bash
# Check if backend is healthy
curl http://localhost:8000/health

# Check last agent run result
curl http://localhost:8000/api/last-run
```

---

## Free Cloud Deployment

Recommended free stack:
- **Backend** → [Railway](https://railway.app) (free $5/month credit)
- **Frontend** → [Vercel](https://vercel.com) (free tier, unlimited)
- **Database** → [Supabase](https://supabase.com) (free tier)

### Backend → Railway

Railway supports Docker deployments natively, which is exactly what you need since the backend bundles Playwright + Chromium.

#### Step 1 — Create a Railway account

Go to [railway.app](https://railway.app) and sign up with GitHub.

#### Step 2 — Create a new project

1. Click **New Project**
2. Select **Deploy from GitHub repo**
3. Choose your `sentinelqa2` repository
4. Railway will detect the `backend/Dockerfile` automatically

#### Step 3 — Configure the root directory

In Railway project settings:
- **Root Directory**: `backend`
- **Dockerfile Path**: `Dockerfile`

#### Step 4 — Set environment variables

In Railway → your service → **Variables**, add:

```
GEMINI_API_KEY        = your_gemini_api_key_here
DATABASE_URL          = postgresql://postgres:[PASSWORD]@db.[REF].supabase.co:5432/postgres
SCREENSHOT_DIR        = /app/screenshots
CORS_ORIGIN           = https://your-vercel-app.vercel.app
```

> **Important**: Update `CORS_ORIGIN` to your actual Vercel URL after the frontend is deployed (Step below).

#### Step 5 — Deploy

Click **Deploy**. Railway will build the Docker image and start the service. This takes 3–5 minutes on first build (Playwright downloads Chromium).

Once done, Railway gives you a public URL like:  
`https://sentinelqa-backend-production.up.railway.app`

#### Step 6 — Verify

```bash
curl https://sentinelqa-backend-production.up.railway.app/health
# Should return: {"status": "ok"}
```

---

### Frontend → Vercel

#### Step 1 — Create a Vercel account

Go to [vercel.com](https://vercel.com) and sign up with GitHub.

#### Step 2 — Import your repository

1. Click **Add New → Project**
2. Import your `sentinelqa2` GitHub repository
3. Set **Root Directory** to `frontend`
4. Framework preset will auto-detect as **Vite**

#### Step 3 — Set environment variables

In Vercel project settings → **Environment Variables**, add:

```
VITE_BACKEND_URL = https://sentinelqa-backend-production.up.railway.app
```

> Replace the URL with your actual Railway backend URL from the previous step.

#### Step 4 — Update vite.config.ts (one-time code change)

Make sure your frontend reads the `VITE_BACKEND_URL` env variable. In `frontend/vite.config.ts`, the proxy should use this env var for production:

```ts
// In your API calls, use:
const BASE_URL = import.meta.env.VITE_BACKEND_URL ?? 'http://localhost:8000';
```

#### Step 5 — Deploy

Click **Deploy**. Vercel builds `npm run build` and serves the static output. Takes ~1 minute.

Your app will be live at: `https://sentinelqa.vercel.app` (or similar)

#### Step 6 — Update Railway CORS

Go back to Railway → Variables and update:
```
CORS_ORIGIN = https://sentinelqa.vercel.app
```

Then redeploy the Railway service for the change to take effect.

---

## Environment Variables Reference

| Variable | Required | Description | Example |
|---|---|---|---|
| `GEMINI_API_KEY` | ✅ | Google Gemini API key | `AIzaSy...` |
| `CORS_ORIGIN` | ✅ | Allowed frontend origin | `http://localhost:3000` |
| `DATABASE_URL` | ✅ | PostgreSQL connection string (Supabase) | `postgresql://postgres:pass@db.xxx.supabase.co:5432/postgres` |
| `SCREENSHOT_DIR` | ❌ | Directory to save screenshots | `/app/screenshots` (default) |
| `GEMINI_MODEL` | ❌ | Gemini model to use | `gemini-1.5-flash` (default) |
| `MAX_TEST_CASES` | ❌ | Max tests per run | `15` (default) |

For the frontend (prefix with `VITE_`):

| Variable | Required | Description | Example |
|---|---|---|---|
| `VITE_BACKEND_URL` | ✅ (production) | Backend API base URL | `https://xxx.up.railway.app` |

---

## Troubleshooting

### Backend won't start — "playwright chromium not found"

```bash
# Inside the container or venv
playwright install chromium
```

### Docker build fails — "libnss3 not found"

The `backend/Dockerfile` already installs all Playwright system dependencies. If you see this error, rebuild with no cache:

```bash
docker compose build --no-cache backend
docker compose up -d
```

### Frontend can't reach backend — CORS error

Ensure `CORS_ORIGIN` in your backend env exactly matches your frontend URL (including `https://` and no trailing slash).

### Railway deploy times out during Chromium download

This is normal on first deploy. Railway has a 5-minute build timeout on the free tier. If it fails, trigger a redeploy — cached layers make subsequent builds much faster.

### "Stream timed out after 120s" in the UI

The agent is still running on the backend. Check:

```bash
# Replace with your Railway URL in production
curl https://your-backend.up.railway.app/api/last-run
```

This returns the cached result of the most recent completed run.

### Supabase connection refused

Make sure you're using the **connection pooler** URL from Supabase (port `6543`), not the direct connection URL (port `5432`), especially on Railway which uses serverless-style networking:

```
# Use this (pooler):
postgresql://postgres.PROJECTREF:PASSWORD@aws-X-REGION.pooler.supabase.com:6543/postgres

# Not this (direct):
postgresql://postgres:PASSWORD@db.PROJECTREF.supabase.co:5432/postgres
```

---

## Quick Reference

```bash
# Local (Docker) — start everything
docker compose up -d

# Local (no Docker) — backend
cd backend && uvicorn app.main:app --reload --port 8000

# Local (no Docker) — frontend
cd frontend && npm run dev

# Production health checks
curl https://your-backend.up.railway.app/health
curl https://your-backend.up.railway.app/api/last-run
```
