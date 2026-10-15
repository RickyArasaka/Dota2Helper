"""Data synchronization and status endpoints."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Query

from ..models.schemas import SyncStatusResponse
from ..services.data_sync import data_sync

router = APIRouter(prefix="/sync", tags=["sync"])


@router.get("/status", response_model=SyncStatusResponse)
async def get_sync_status():
    """Get the current data sync and cache status."""
    status = await data_sync.get_sync_status()
    return SyncStatusResponse(**status)


@router.post("/trigger")
async def trigger_sync(
    background_tasks: BackgroundTasks,
    rank_filter: str = Query("all", regex="^(immortal|divine_plus|all)$"),
):
    """Trigger an asynchronous background data synchronization."""
    if data_sync.is_syncing:
        return {"status": "busy", "message": "A data synchronization is already in progress."}

    background_tasks.add_task(data_sync.sync_all_builds, rank_filter)
    return {"status": "started", "message": "Background data sync started."}


@router.post("/hero/{hero_id}")
async def sync_single_hero(
    hero_id: int,
    rank_filter: str = Query("all", regex="^(immortal|divine_plus|all)$"),
):
    """Sync builds for a single hero synchronously."""
    count = await data_sync.sync_hero_builds(hero_id, rank_filter)
    return {"status": "ok", "hero_id": hero_id, "builds_updated": count}
