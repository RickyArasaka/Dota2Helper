"""Build recommendation endpoints."""

from __future__ import annotations

import datetime

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from ..database import async_session
from ..models.database_models import BuildHistory, Hero, HeroBuild
from ..models.schemas import (
    BuildComparison,
    BuildHistoryEntry,
    BuildResponse,
    BuildSelectRequest,
    HeroBuildSchema,
    HeroSchema,
)
from ..services.recommender import recommender

router = APIRouter(prefix="/builds", tags=["builds"])


@router.get("/{hero_id}", response_model=BuildResponse)
async def get_builds(
    hero_id: int,
    rank_filter: str = Query("all", regex="^(immortal|divine_plus|all)$"),
    patch: str | None = None,
    build_type: str | None = None,
):
    """
    Get recommended builds for a hero.

    Returns up to 4 builds: popular, winrate, meta, situational.
    """
    async with async_session() as session:
        hero = await session.get(Hero, hero_id)
    if not hero:
        raise HTTPException(404, f"Hero {hero_id} not found – try syncing data first")

    builds = await recommender.get_recommendations(hero_id, rank_filter, patch)
    if build_type:
        builds = [b for b in builds if b.build_type == build_type]

    return BuildResponse(
        hero=HeroSchema.model_validate(hero),
        builds=builds,
        patch=builds[0].patch if builds else "",
        rank_filter=rank_filter,
    )


@router.get("/{hero_id}/compare", response_model=BuildComparison)
async def compare_builds(
    hero_id: int,
    build_ids: str = Query(..., description="Comma-separated build IDs"),
):
    """Compare specific builds side-by-side."""
    async with async_session() as session:
        hero = await session.get(Hero, hero_id)
        if not hero:
            raise HTTPException(404, "Hero not found")

        ids = [int(x.strip()) for x in build_ids.split(",") if x.strip().isdigit()]
        result = await session.execute(
            select(HeroBuild).where(HeroBuild.id.in_(ids), HeroBuild.hero_id == hero_id)
        )
        builds = result.scalars().all()

    return BuildComparison(
        hero=HeroSchema.model_validate(hero),
        builds=[HeroBuildSchema.model_validate(b) for b in builds],
    )


@router.post("/{hero_id}/select")
async def select_build(hero_id: int, req: BuildSelectRequest):
    """Record that the user selected a build (for history tracking)."""
    async with async_session() as session:
        build = await session.get(HeroBuild, req.build_id)
        if not build:
            raise HTTPException(404, "Build not found")
        session.add(BuildHistory(
            hero_id=hero_id,
            build_id=req.build_id,
            match_id=req.match_id,
        ))
        await session.commit()
    return {"status": "ok", "build_id": req.build_id}


@router.get("/history/all", response_model=list[BuildHistoryEntry])
async def get_build_history(limit: int = Query(50, ge=1, le=200)):
    """Return the user's recent build selection history."""
    async with async_session() as session:
        result = await session.execute(
            select(BuildHistory).order_by(BuildHistory.used_at.desc()).limit(limit)
        )
        entries = result.scalars().all()
    return [BuildHistoryEntry.model_validate(e) for e in entries]
