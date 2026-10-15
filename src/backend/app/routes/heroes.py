"""Hero endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from ..database import async_session
from ..models.database_models import Hero
from ..models.schemas import HeroSchema

router = APIRouter(prefix="/heroes", tags=["heroes"])


@router.get("", response_model=list[HeroSchema])
async def list_heroes():
    """Return all heroes."""
    async with async_session() as session:
        result = await session.execute(select(Hero).order_by(Hero.localized_name))
        heroes = result.scalars().all()
    return [HeroSchema.model_validate(h) for h in heroes]


@router.get("/{hero_id}", response_model=HeroSchema)
async def get_hero(hero_id: int):
    """Return a single hero by ID."""
    async with async_session() as session:
        hero = await session.get(Hero, hero_id)
    if not hero:
        raise HTTPException(404, f"Hero {hero_id} not found")
    return HeroSchema.model_validate(hero)


@router.get("/search/{name}", response_model=list[HeroSchema])
async def search_heroes(name: str):
    """Search heroes by partial name match."""
    pattern = f"%{name}%"
    async with async_session() as session:
        result = await session.execute(
            select(Hero).where(
                Hero.localized_name.ilike(pattern) | Hero.name.ilike(pattern)
            )
        )
        heroes = result.scalars().all()
    return [HeroSchema.model_validate(h) for h in heroes]


@router.get("/{hero_id}/matchups")
async def get_hero_counters(hero_id: int):
    """
    Get top counters (bad against) and favorable matchups (good against)
    from real OpenDota match data.
    """
    from ..services.opendota import OpenDotaClient
    from ..utils.constants import HERO_DISPLAY_NAMES, HERO_ID_TO_NAME

    client = OpenDotaClient()
    try:
        raw_matchups = await client.get_hero_matchups(hero_id)
    except Exception:
        raw_matchups = []

    # Calculate winrate: in OpenDota /matchups, games_played is vs opponent, wins is how many times hero won vs opponent
    valid = []
    for m in raw_matchups:
        opp_id = m.get("hero_id")
        games = m.get("games_played", 0)
        wins = m.get("wins", 0)
        if games >= 30 and opp_id in HERO_ID_TO_NAME:
            winrate = round((wins / games) * 100, 1)
            opp_name = HERO_ID_TO_NAME.get(opp_id, "")
            valid.append({
                "hero_id": opp_id,
                "name": opp_name,
                "localized_name": HERO_DISPLAY_NAMES.get(opp_id, opp_name.title()),
                "winrate_vs": winrate,
                "advantage": round(winrate - 50.0, 1),
                "games": games,
                "img": f"https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/heroes/{opp_name}.png",
            })

    # Sort: lowest winrate = hero struggles most (Counters / Bad Against)
    # highest winrate = hero wins most (Good Against)
    valid.sort(key=lambda x: x["winrate_vs"])

    bad_against = valid[:5]
    good_against = sorted(valid, key=lambda x: x["winrate_vs"], reverse=True)[:5]

    return {
        "hero_id": hero_id,
        "bad_against": bad_against,
        "good_against": good_against,
    }
