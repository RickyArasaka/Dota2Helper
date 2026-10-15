"""FastAPI application entry point for DotaBlitz."""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import init_db
from .routes import builds, gsi, guides, heroes, sync
from .services.data_sync import data_sync

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("dotablitz.main")

# WebSocket connection manager
class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.debug("WS client connected. Total clients: %d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.debug("WS client disconnected. Total clients: %d", len(self.active_connections))

    async def broadcast(self, message: dict) -> None:
        for connection in list(self.active_connections):
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()
gsi.set_ws_broadcast(manager.broadcast)

scheduler = AsyncIOScheduler()

async def scheduled_sync_job() -> None:
    logger.info("Executing periodic data sync scheduled job...")
    if data_sync.should_sync():
        await data_sync.sync_all_builds()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting DotaBlitz backend on %s:%d", settings.BACKEND_HOST, settings.BACKEND_PORT)
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    (settings.DATA_DIR / "guides").mkdir(parents=True, exist_ok=True)
    
    await init_db()
    logger.info("Database initialized.")

    # Start APScheduler
    scheduler.add_job(scheduled_sync_job, "interval", hours=settings.CACHE_TTL_HOURS)
    scheduler.start()
    logger.info("Scheduler started with %d-hour interval.", settings.CACHE_TTL_HOURS)

    # Initial check in background: sync heroes if empty
    asyncio.create_task(data_sync.sync_heroes())

    yield

    # Shutdown
    scheduler.shutdown(wait=False)
    logger.info("DotaBlitz backend shut down.")

app = FastAPI(
    title="DotaBlitz API",
    description="Dota 2 companion app backend with GSI, live recommendations and Steam Guides generator",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(heroes.router, prefix="/api")
app.include_router(builds.router, prefix="/api")
app.include_router(gsi.router, prefix="/api")
app.include_router(guides.router, prefix="/api")
app.include_router(sync.router, prefix="/api")

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "DotaBlitz"}

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep-alive loop or incoming commands from frontend
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)

# Mount static frontend files
if settings.FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(settings.FRONTEND_DIR), html=True), name="frontend")
else:
    logger.warning("Frontend directory %s does not exist yet.", settings.FRONTEND_DIR)
