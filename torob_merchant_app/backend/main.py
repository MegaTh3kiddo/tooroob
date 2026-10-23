import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from database import init_db
from services.scheduler import scheduler
from routers import auth, shop, inquiries, push, metrics, admin

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize DB and start scheduler task
    init_db()
    scheduler_task = asyncio.create_task(scheduler.start())
    yield
    # Shutdown: Stop scheduler
    scheduler.stop()
    scheduler_task.cancel()

app = FastAPI(
    title="Torob Seller API & Notification Hub",
    description="Real-time seller application backend for Torob in-person inquiries, push notifications, and scheduling.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS setup for Web Admin Panel and Mobile HTTP calls
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(auth.router, prefix="/api")
app.include_router(shop.router, prefix="/api")
app.include_router(inquiries.router, prefix="/api")
app.include_router(push.router, prefix="/api")
app.include_router(metrics.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.add_api_route(
    "/api/seller/sync/batch-responses",
    inquiries.batch_sync_responses,
    methods=["POST"],
    response_model=inquiries.BatchSyncResponse,
    tags=["Seller Inquiries"]
)

# Mount Admin Web Panel
admin_dir = os.path.join(os.path.dirname(__file__), "..", "admin")
if os.path.exists(admin_dir):
    app.mount("/admin", StaticFiles(directory=admin_dir, html=True), name="admin")

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "torob-seller-backend",
        "scheduler_running": scheduler.is_running
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
