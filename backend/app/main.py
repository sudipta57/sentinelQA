from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os
import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(os.getenv("SCREENSHOT_DIR", "/app/screenshots"), exist_ok=True)
    logger.info("SentinelQA backend starting up")
    yield
    logger.info("SentinelQA backend shutting down")


app = FastAPI(
    title="SentinelQA",
    description="Autonomous Bug Hunter Agent API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("CORS_ORIGIN", "http://localhost:3000"),
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

screenshot_dir = os.getenv("SCREENSHOT_DIR", "/app/screenshots")
os.makedirs(screenshot_dir, exist_ok=True)
app.mount(
    "/screenshots",
    StaticFiles(directory=screenshot_dir),
    name="screenshots"
)

from app.routers import health, agent
app.include_router(health.router)
app.include_router(agent.router, prefix="/api")
