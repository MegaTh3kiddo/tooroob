from contextlib import asynccontextmanager
import logging
import uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from torob.api.v1.endpoints_seller import router as seller_router
from torob.api.v1.router import api_v1_router
from torob.core.config import settings
from torob.ingestion.loader import initialize_storage
from torob.storage.db import db_manager
from torob.storage.merchant_import import seed_all_merchant_data
from torob.storage.test_shop import seed_jimbo_test_shop

logging.basicConfig(level=logging.INFO if not settings.debug else logging.DEBUG)
logger = logging.getLogger("torob.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Torob storage and catalog engines...")
    try:
        initialize_storage()
        logger.info("Storage initialized successfully.")
    except Exception as e:
        logger.warning(f"Could not initialize full catalog automatically on startup: {e}")
    try:
        seed_all_merchant_data()
        logger.info("Merchant storage and baseline seed initialized successfully.")
    except Exception as e:
        logger.warning(f"Could not seed merchant storage on startup: {e}")
    try:
        seed_jimbo_test_shop()
    except Exception as e:
        logger.warning(f"Could not seed Jimbo test shop: {e}")
    yield
    logger.info("Closing database connections...")
    db_manager.close()


app = FastAPI(
    title="Torob Intelligence Engine API",
    description=(
        "Evidence-Driven Price, Inventory, Shop Reliability, Merchant Android Integration, and Customer Purchase Feasibility Intelligence Engine. "
        "Built for Starcoach Hackathon (Torob Track)."
    ),
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for independently hosted frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# Correlation ID Middleware for distributed tracing and request observability
class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID") or f"req_{uuid.uuid4().hex[:12]}"
        request.state.correlation_id = correlation_id
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response


app.add_middleware(CorrelationIdMiddleware)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception at {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error occurred in Torob Intelligence Engine."},
    )


# Mount versioned API routes
app.include_router(api_v1_router)

# Mount Seller Router directly for native Android Retrofit compatibility (/seller/... and /api/seller/...)
app.include_router(seller_router)


@app.get("/", tags=["Root"])
def root():
    return {
        "engine": "Torob Intelligence Engine",
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/api/v1/health",
        "seller_portal": "/seller/shop",
        "description": "Unified Evidence-Driven backend supporting Customer Web/Mobile & Merchant Native Android Apps.",
    }
