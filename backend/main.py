"""FastAPI application entrypoint for the WhatsApp Message Notification Router."""

import sys
import structlog
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.db.database import create_tables
from app.services.data_loader import data_loader

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])


# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------

def _setup_logging() -> None:
    """Configure structured logging with structlog."""
    import logging
    
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure stdlib logging to route through structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    )

_setup_logging()
logger = structlog.get_logger(__name__)


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
        "deterministic rules and OpenAI GPT-4o-mini."
    ),
    lifespan=lifespan,
)

# CORS — allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else [settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

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
