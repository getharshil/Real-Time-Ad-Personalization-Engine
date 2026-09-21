"""
FastAPI application entry point.

Sets up:
- CORS middleware
- Request logging middleware
- All API routers
- Database initialization on startup
- Structured logging
"""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.db.database import init_db

# Configure structured logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("Starting AI Personalization Platform...")
    await init_db()
    logger.info("Database tables initialized")

    # Try to load ML model
    try:
        from app.ml.predictor import load_model
        load_model()
        logger.info("ML model loaded successfully")
    except Exception as e:
        logger.warning(f"ML model not loaded (will use rule-based scoring): {e}")

    yield

    logger.info("Shutting down...")


app = FastAPI(
    title=settings.app_name,
    description=(
        "Real-Time AI Personalization & Ad Recommendation Platform. "
        "Collects user interaction events, derives behavioral features, "
        "and serves personalized ad recommendations using ML."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration_ms = round((time.time() - start_time) * 1000, 2)

    logger.info(
        f"{request.method} {request.url.path} → {response.status_code} ({duration_ms}ms)"
    )
    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# Register routers
from app.api.auth import router as auth_router
from app.api.content import router as content_router
from app.api.events import router as events_router
from app.api.recommendations import router as recommendations_router
from app.api.ads import router as ads_router
from app.api.users import router as users_router
from app.api.sessions import router as sessions_router
from app.api.admin import router as admin_router

app.include_router(auth_router)
app.include_router(content_router)
app.include_router(events_router)
app.include_router(recommendations_router)
app.include_router(ads_router)
app.include_router(users_router)
app.include_router(sessions_router)
app.include_router(admin_router)


@app.get("/", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": "1.0.0",
    }


@app.get("/api/health", tags=["Health"])
async def api_health():
    return {"status": "ok"}
