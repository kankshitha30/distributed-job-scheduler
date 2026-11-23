import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

from app.config import settings
from app.database import engine, Base
from app.middleware.error_handler import (
    AppException,
    app_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
)
from app.routers import (
    auth_router,
    projects_router,
    retry_policies_router,
    queues_router,
    jobs_router,
    workers_router,
    metrics_router,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("scheduler.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Distributed Job Scheduler API Service...")
    # Create tables automatically on startup for development / sqlite / test harnesses
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schema synchronized.")
    yield
    logger.info("Shutting down Distributed Job Scheduler API Service...")
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Production-Grade Distributed Job Scheduling Platform with PostgreSQL Atomic Job Claiming, Retries, DLQ, and Worker Heartbeats.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Include Routers
app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(retry_policies_router)
app.include_router(queues_router)
app.include_router(jobs_router)
app.include_router(workers_router)
app.include_router(metrics_router)


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
    }
