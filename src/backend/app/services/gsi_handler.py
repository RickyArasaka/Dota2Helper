"""GSI (Game State Integration) event handler."""

from __future__ import annotations

import logging
from typing import Any, Optional

from ..models.schemas import GameStateEvent, GameStateSnapshot
from ..utils.constants import HERO_ID_TO_NAME

logger = logging.getLogger("dotablitz.gsi")


class GSIHandler:
    """Parses and tracks Dota 2 Game State Integration events."""

    def __init__(self) -> None:
        self._previous: GameStateSnapshot | None = None
        self._current: GameStateSnapshot = GameStateSnapshot()

    @property
    def current(self) -> GameStateSnapshot:
        return self._current

    # ── Parse raw GSI payload ────────────────────────────────────────

    def parse_event(self, data: dict[str, Any]) -> GameStateSnapshot:
        """
        Convert a raw GSI JSON payload into a ``GameStateSnapshot`` and
        update internal state.
        """
        self._previous = self._current.model_copy()

        hero_data = data.get("hero", {})
        player_data = data.get("player", {})
        map_data = data.get("map", {})
        items_data = data.get("items", {})
        abilities_data = data.get("abilities", {})

        # Determine team
        team: str | None = None
        if "team2" in player_data or player_data.get("team_name") == "radiant":
            team = "radiant"
        elif "team3" in player_data or player_data.get("team_name") == "dire":
            team = "dire"

        # Parse items from inventory slots
        item_names: list[str] = []
        for i in range(9):  # slot0..slot8 + stash/neutral
            slot_key = f"slot{i}"
            slot = items_data.get(slot_key, {})
            name = slot.get("name", "empty")
            if name and name != "empty":
                item_names.append(name.replace("item_", ""))

        # Neutral item slot
        neutral = items_data.get("neutral0", {})
        neutral_name = neutral.get("name", "empty")
        if neutral_name and neutral_name != "empty":
            item_names.append(neutral_name.replace("item_", ""))

        # Parse hero name / id
        hero_name = hero_data.get("name", "")
        if hero_name:
            hero_name = hero_name.replace("npc_dota_hero_", "")
        hero_id = hero_data.get("id")
        if not hero_id and hero_name:
            from ..utils.constants import HERO_NAME_TO_ID
            hero_id = HERO_NAME_TO_ID.get(hero_name)

        game_time = map_data.get("game_time", 0)
        clock_time = map_data.get("clock_time", game_time)
        last_hits = player_data.get("last_hits", 0)
        denies = player_data.get("denies", 0)
        minutes = max(0.1, clock_time / 60.0) if clock_time > 0 else 0.1
        cs_per_min = round(last_hits / minutes, 1) if clock_time > 60 else 0.0

        # CS Rating
        if cs_per_min >= 9.0:
            cs_rating = "S+"
        elif cs_per_min >= 7.5:
            cs_rating = "S"
        elif cs_per_min >= 6.0:
            cs_rating = "A"
        elif cs_per_min >= 4.5:
            cs_rating = "B"
        else:
            cs_rating = "C"

        # Objective timings (remaining seconds)
        if clock_time < 360:
            next_power_rune_sec = max(0, 360 - clock_time)
        else:
            rem = clock_time % 120
            next_power_rune_sec = 120 - rem if rem != 0 else 120

        rem_w = clock_time % 420
        next_wisdom_rune_sec = max(0, 420 - rem_w if rem_w != 0 else 420)

        rem_l = clock_time % 180
        next_lotus_sec = max(0, 180 - rem_l if rem_l != 0 else 180)

        next_tormentor_sec = max(0, 1200 - clock_time)

        # Neutrals
        neutral_tiers = [(1, 420), (2, 1020), (3, 1620), (4, 2220), (5, 3600)]
        next_tier = 1
        next_tier_sec = 0
        for tier, t_sec in neutral_tiers:
            if clock_time < t_sec:
                next_tier = tier
                next_tier_sec = t_sec - clock_time
                break
        else:
            next_tier = 5
            next_tier_sec = 0

        self._current = GameStateSnapshot(
            hero_id=hero_id,
            hero_name=hero_name or None,
            hero_level=hero_data.get("level", 0),
            game_time=game_time,
            clock_time=clock_time,
            gold=player_data.get("gold", 0),
            items=item_names,
            match_id=str(map_data.get("matchid", "")) if map_data.get("matchid") else None,
            is_alive=hero_data.get("alive", True),
            team=team,
            kills=player_data.get("kills", 0),
            deaths=player_data.get("deaths", 0),
            assists=player_data.get("assists", 0),
            last_hits=last_hits,
            denies=denies,
            gpm=player_data.get("gpm", 0),
            xpm=player_data.get("xpm", 0),
            net_worth=player_data.get("net_worth", 0),
            cs_per_min=cs_per_min,
            cs_rating=cs_rating,
            next_power_rune_sec=next_power_rune_sec,
            next_wisdom_rune_sec=next_wisdom_rune_sec,
            next_lotus_sec=next_lotus_sec,
            next_tormentor_sec=next_tormentor_sec,
            next_neutral_tier=next_tier,
            next_neutral_tier_sec=next_tier_sec,
            connected=True,
            abilities=abilities_data,
        )

        return self._current

    # ── Detection helpers ────────────────────────────────────────────

    def detect_hero_pick(self, data: dict[str, Any]) -> int | None:
        """Return hero_id if a hero is detected in the payload, else None."""
        hero = data.get("hero", {})
        hid = hero.get("id")
        if hid and hid > 0:
            return hid
        name = hero.get("name", "").replace("npc_dota_hero_", "")
        if name:
            from ..utils.constants import HERO_NAME_TO_ID
            return HERO_NAME_TO_ID.get(name)
        return None

    def detect_level_up(self) -> bool:
        """Return True if the hero leveled up since the previous event."""
        if self._previous is None:
            return False
        return self._current.hero_level > self._previous.hero_level

    def detect_item_change(self) -> list[str]:
        """Return list of newly acquired items since the previous event."""
        if self._previous is None:
            return []
        prev_set = set(self._previous.items)
        curr_set = set(self._current.items)
        return list(curr_set - prev_set)

    def get_game_phase(self) -> str:
        """Return 'pre_game', 'early', 'mid', or 'late'."""
        gt = self._current.game_time
        if gt <= 0:
            return "pre_game"
        minutes = gt / 60
        if minutes < 10:
            return "early"
        elif minutes < 25:
            return "mid"
        return "late"


# Module-level singleton
gsi_handler = GSIHandler()
