"""GSI (Game State Integration) endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request

from ..models.schemas import GameStateSnapshot, NextAction
from ..services.gsi_handler import gsi_handler
from ..services.recommender import recommender

logger = logging.getLogger("dotablitz.gsi.route")

router = APIRouter(prefix="/gsi", tags=["gsi"])

# In-memory reference to connected WebSocket clients (set by main.py)
_ws_broadcast = None


def set_ws_broadcast(fn):
    """Called at startup to wire the WebSocket broadcast function."""
    global _ws_broadcast
    _ws_broadcast = fn


@router.post("/event")
async def receive_gsi_event(request: Request):
    """
    Receive a Game State Integration event from Dota 2.

    The Dota 2 client POSTs JSON to this endpoint every time the game
    state changes.
    """
    try:
        data = await request.json()
    except Exception:
        return {"status": "error", "detail": "Invalid JSON"}

    snapshot = gsi_handler.parse_event(data)

    # Log key info
    if snapshot.hero_name:
        logger.info(
            "GSI: hero=%s level=%d gold=%d time=%ds",
            snapshot.hero_name,
            snapshot.hero_level,
            snapshot.gold,
            snapshot.game_time,
        )

    # Broadcast to WebSocket clients
    if _ws_broadcast:
        try:
            await _ws_broadcast(snapshot.model_dump())
        except Exception as exc:
            logger.error("WS broadcast error: %s", exc)

    return {"status": "ok"}


@router.get("/state", response_model=GameStateSnapshot)
async def get_current_state():
    """Return the latest game state snapshot."""
    return gsi_handler.current


@router.get("/next-action", response_model=NextAction)
async def get_next_action(build_id: int | None = None):
    """
    Compute what the player should do next based on the current game
    state and the active build.
    """
    state = gsi_handler.current
    if not state.hero_id:
        return NextAction(tip="No hero detected – waiting for GSI data")

    return await recommender.get_next_action(
        hero_id=state.hero_id,
        current_level=state.hero_level,
        current_items=state.items,
        current_gold=state.gold,
        game_time=state.game_time,
        build_id=build_id,
    )
