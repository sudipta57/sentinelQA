# SentinelQA

SentinelQA is an autonomous AI bug-hunter agent that crawls web applications, generates test cases, executes browser checks, and reports classified defects. This scaffold provides a FastAPI backend, a React + Tailwind frontend, and a demo app, all orchestrated with Docker Compose for a fast local setup.

## Prerequisites

- Docker Desktop (or Docker Engine + Docker Compose plugin)
- Gemini API key

## Setup

1. Copy environment template:
   ```bash
   cp .env.example .env
   ```
2. Open `.env` and set your `GEMINI_API_KEY`.
3. Build and run everything:
   ```bash
   docker compose up --build
   ```

## URLs

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Demo app: http://localhost:3001
- API docs: http://localhost:8000/docs

## Project Structure

| Path | Description |
| --- | --- |
| `backend/` | FastAPI service with config, models, and API routers |
| `frontend/` | React + TypeScript + Tailwind UI for launching and viewing agent runs |
| `demo-app/` | Placeholder target application for testing workflows |
| `screenshots/` | Shared screenshot output directory mounted into backend |
| `docker-compose.yml` | Multi-service local orchestration |

Built for MLH Bot to Agent Hackathon - IEM Kolkata 2026
