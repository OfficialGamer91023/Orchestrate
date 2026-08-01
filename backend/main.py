"""FastAPI application entrypoint for the WhatsApp Message Notification Router."""

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.db.database import create_tables
from app.services.data_loader import data_loader


# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------

def _setup_logging() -> None:
    """Configure dual logging: stdout + log.txt."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    # Format
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Stdout handler
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(fmt)
    root_logger.addHandler(stdout_handler)

    # File handler (append mode)
    log_file = Path("log.txt")
    file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    file_handler.setFormatter(fmt)
    root_logger.addHandler(file_handler)

    logging.info("Logging initialized → stdout + %s", log_file.resolve())


_setup_logging()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    logger.info("Starting %s v%s", settings.APP_TITLE, settings.APP_VERSION)
    create_tables()
    logger.info("Database tables created/verified")

    # Pre-load dataset
    data_loader.load()

    # Mount static media files
    media_path = settings.media_dir
    if media_path.exists():
        app.mount(
            "/media",
            StaticFiles(directory=str(media_path)),
            name="media",
        )
        logger.info("Mounted static media at /media → %s", media_path)
    else:
        logger.warning("Media directory not found: %s", media_path)

    yield

    # Shutdown
    logger.info("Shutting down %s", settings.APP_TITLE)


# ---------------------------------------------------------------------------
# App Factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    description=(
        "AI-powered WhatsApp message routing engine. "
        "Routes messages into notify, digest, or mute using "
        "deterministic rules and Gemini 2.5 Flash."
    ),
    lifespan=lifespan,
)

# CORS — allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Register Routes
# ---------------------------------------------------------------------------

from app.api.routes.messages import router as messages_router
from app.api.routes.eval import router as eval_router

app.include_router(messages_router)
app.include_router(eval_router)


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["system"])
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "dataset_loaded": data_loader._loaded,
        "messages_count": len(data_loader.messages) if data_loader._loaded else 0,
    }
