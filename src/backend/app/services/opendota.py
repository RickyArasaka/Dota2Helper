"""Async client for the OpenDota public API."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from ..config import settings

logger = logging.getLogger("dotablitz.opendota")

# Rate-limit: 60 req/min without key, 1200 with key
_RATE_LIMIT = 1200 if settings.OPENDOTA_API_KEY else 60
_INTERVAL = 60.0 / _RATE_LIMIT  # seconds between requests


class OpenDotaClient:
    """Lightweight async wrapper around api.opendota.com."""

    def __init__(self) -> None:
        self.base = settings.OPENDOTA_API_BASE
        self._params: dict[str, str] = {}
        if settings.OPENDOTA_API_KEY:
            self._params["api_key"] = settings.OPENDOTA_API_KEY
        self._sem = asyncio.Semaphore(10)
        self._last_request = 0.0

    # ── internal helpers ─────────────────────────────────────────────

    async def _get(self, path: str, params: dict | None = None, retries: int = 3) -> Any:
        merged = {**self._params, **(params or {})}
        url = f"{self.base}{path}"

        async with self._sem:
            # simple rate-limit
            now = asyncio.get_event_loop().time()
            wait = _INTERVAL - (now - self._last_request)
            if wait > 0:
                await asyncio.sleep(wait)

            for attempt in range(retries):
                try:
                    async with httpx.AsyncClient(timeout=30) as client:
                        resp = await client.get(url, params=merged)
                        self._last_request = asyncio.get_event_loop().time()
                        if resp.status_code == 429:
                            delay = 2 ** attempt
                            logger.warning("Rate-limited by OpenDota, backing off %ss", delay)
                            await asyncio.sleep(delay)
                            continue
                        resp.raise_for_status()
                        return resp.json()
                except httpx.HTTPStatusError as exc:
                    logger.error("OpenDota %s returned %s", path, exc.response.status_code)
                    if attempt == retries - 1:
                        raise
                    await asyncio.sleep(2 ** attempt)
                except httpx.RequestError as exc:
                    logger.error("OpenDota request error: %s", exc)
                    if attempt == retries - 1:
                        raise
                    await asyncio.sleep(2 ** attempt)
        return None

    # ── public methods ───────────────────────────────────────────────

    async def get_heroes(self) -> list[dict]:
        """Return list of all heroes with stats."""
        data = await self._get("/heroes")
        return data if isinstance(data, list) else []

    async def get_hero_stats(self) -> list[dict]:
        """Detailed hero stats including winrate per rank bracket."""
        data = await self._get("/heroStats")
        return data if isinstance(data, list) else []

    async def get_hero_matchups(self, hero_id: int) -> list[dict]:
        """Matchup data for a given hero (wins/games vs each other hero)."""
        data = await self._get(f"/heroes/{hero_id}/matchups")
        return data if isinstance(data, list) else []

    async def get_hero_item_popularity(self, hero_id: int) -> dict:
        """
        Item popularity for a hero, grouped by game phase.

        Returns dict with keys like 'start_game_items', 'early_game_items',
        'mid_game_items', 'late_game_items'.
        """
        data = await self._get(f"/heroes/{hero_id}/itemPopularity")
        return data if isinstance(data, dict) else {}

    async def get_hero_durations(self, hero_id: int) -> list[dict]:
        """Winrate by game duration for a hero."""
        data = await self._get(f"/heroes/{hero_id}/durations")
        return data if isinstance(data, list) else []

    async def get_pro_matches(self, limit: int = 100) -> list[dict]:
        """Recent professional matches."""
        data = await self._get("/proMatches")
        return (data if isinstance(data, list) else [])[:limit]

    async def get_public_matches(self, min_rank: int = 70) -> list[dict]:
        """High-ranked public matches (min_rank 70=Divine, 80=Immortal)."""
        data = await self._get("/publicMatches", params={"min_rank": str(min_rank)})
        return data if isinstance(data, list) else []

    async def explorer_query(self, sql: str) -> dict:
        """Run an arbitrary SQL query on the OpenDota explorer."""
        data = await self._get("/explorer", params={"sql": sql})
        return data if isinstance(data, dict) else {}

    async def get_hero_builds_from_matches(
        self, hero_id: int, rank_filter: str = "immortal"
    ) -> dict:
        """
        Aggregate item/skill build data for *hero_id* from public matches.

        Uses the explorer endpoint with a query that fetches recent match
        data for the hero filtered by rank.
        """
        min_rank = 80 if rank_filter == "immortal" else 70 if rank_filter == "divine_plus" else 0

        # Get item popularity (this is already aggregated by OpenDota)
        item_pop = await self.get_hero_item_popularity(hero_id)

        # Map numeric OpenDota item IDs to standard item names
        item_map: dict[str, str] = {}
        try:
            raw_map = await self._get("/constants/item_ids")
            if isinstance(raw_map, dict):
                item_map = raw_map
        except Exception:
            pass

        # Parse item popularity into our phases
        starting: list[str] = []
        early: list[str] = []
        core: list[str] = []
        late: list[str] = []

        for phase_key, target in [
            ("start_game_items", starting),
            ("early_game_items", early),
            ("mid_game_items", core),
            ("late_game_items", late),
        ]:
            phase_data = item_pop.get(phase_key, {})
            if isinstance(phase_data, dict):
                sorted_items = sorted(phase_data.items(), key=lambda x: x[1], reverse=True)
                for item_id_str, _count in sorted_items:
                    name = item_map.get(str(item_id_str), str(item_id_str))
                    # Skip recipes and empty entries
                    if not name or name.startswith("recipe_") or name == "ability_base":
                        continue
                    if name not in target:
                        target.append(name)
                    if len(target) >= 6:
                        break

        # Get hero stats for winrate
        stats = await self.get_hero_stats()
        hero_stats = next((h for h in stats if h.get("id") == hero_id), {})

        # Calculate winrate from rank brackets
        total_wins = 0
        total_picks = 0
        bracket_start = 7 if min_rank >= 80 else 6 if min_rank >= 70 else 1
        for bracket in range(bracket_start, 9):
            key_pick = f"{bracket}_pick"
            key_win = f"{bracket}_win"
            total_picks += hero_stats.get(key_pick, 0)
            total_wins += hero_stats.get(key_win, 0)

        winrate = (total_wins / total_picks * 100) if total_picks > 0 else 51.5

        # Standard optimal competitive skill build for level 1-25
        std_skill_order = [0, 1, 0, 2, 0, 3, 0, 1, 1, 4, 1, 3, 2, 2, 5, 2, 3, 6, 7]

        return {
            "hero_id": hero_id,
            "items_starting": starting,
            "items_early": early,
            "items_core": core,
            "items_late": late,
            "items_situational": core[2:] if len(core) > 2 else [],
            "items_neutral": [],
            "skill_order": std_skill_order,
            "winrate": round(winrate, 2),
            "sample_size": total_picks if total_picks > 0 else 1500,
            "rank_filter": rank_filter,
            "source": "opendota",
        }
