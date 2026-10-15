"""Pydantic v2 schemas for API request / response validation."""

from __future__ import annotations

import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ── Hero ──────────────────────────────────────────────────────────────

class HeroSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    localized_name: str
    primary_attr: str
    attack_type: str
    roles: list[str] = []
    img_url: Optional[str] = None


# ── Build ─────────────────────────────────────────────────────────────

class HeroBuildSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    hero_id: int
    build_type: str
    patch: str = ""
    source: str = ""
    rank_filter: str = "all"

    items_starting: list[str] = []
    items_early: list[str] = []
    items_core: list[str] = []
    items_late: list[str] = []
    items_situational: list[str] = []
    items_neutral: list[str] = []

    skill_order: list[int] = []
    facet: Optional[str] = None

    winrate: float = 0.0
    pick_rate: Optional[float] = None
    sample_size: int = 0

    created_at: Optional[datetime.datetime] = None
    updated_at: Optional[datetime.datetime] = None


class BuildResponse(BaseModel):
    """Wraps a list of builds for a hero."""
    hero: HeroSchema
    builds: list[HeroBuildSchema] = []
    patch: str = ""
    rank_filter: str = "all"


class BuildComparison(BaseModel):
    hero: HeroSchema
    builds: list[HeroBuildSchema] = []


# ── GSI ───────────────────────────────────────────────────────────────

class GSIAbility(BaseModel):
    name: str = ""
    level: int = 0
    can_cast: bool = False
    passive: bool = False
    ability_active: bool = False
    cooldown: int = 0
    ultimate: bool = False


class GSIItem(BaseModel):
    name: str = "empty"
    purchaser: Optional[int] = None
    can_cast: bool = False
    cooldown: int = 0
    passive: bool = False
    charges: int = 0


class GameStateEvent(BaseModel):
    """Parsed GSI event payload (simplified)."""
    provider: Optional[dict] = None
    map: Optional[dict] = None
    player: Optional[dict] = None
    hero: Optional[dict] = None
    abilities: Optional[dict] = None
    items: Optional[dict] = None

    # Derived helpers
    @property
    def hero_id(self) -> Optional[int]:
        if self.hero and "id" in self.hero:
            return self.hero["id"]
        return None

    @property
    def hero_name(self) -> Optional[str]:
        if self.hero and "name" in self.hero:
            return self.hero["name"]
        return None

    @property
    def hero_level(self) -> int:
        if self.hero and "level" in self.hero:
            return self.hero["level"]
        return 0

    @property
    def game_time(self) -> int:
        if self.map and "game_time" in self.map:
            return self.map["game_time"]
        return 0

    @property
    def match_id(self) -> Optional[str]:
        if self.map and "matchid" in self.map:
            return str(self.map["matchid"])
        return None

    @property
    def current_gold(self) -> int:
        if self.player:
            return self.player.get("gold", 0)
        return 0


class GameStateSnapshot(BaseModel):
    """Current game-state snapshot exposed to the frontend."""
    hero_id: Optional[int] = None
    hero_name: Optional[str] = None
    hero_level: int = 0
    game_time: int = 0
    clock_time: int = 0
    gold: int = 0
    items: list[str] = []
    match_id: Optional[str] = None
    is_alive: bool = True
    team: Optional[str] = None
    kills: int = 0
    deaths: int = 0
    assists: int = 0
    last_hits: int = 0
    denies: int = 0
    gpm: int = 0
    xpm: int = 0
    net_worth: int = 0
    cs_per_min: float = 0.0
    cs_rating: str = "A"
    next_power_rune_sec: int = 0
    next_wisdom_rune_sec: int = 0
    next_lotus_sec: int = 0
    next_tormentor_sec: int = 0
    next_neutral_tier: int = 1
    next_neutral_tier_sec: int = 0
    connected: bool = False
    abilities: dict = {}


# ── Guide ─────────────────────────────────────────────────────────────

class GuideExportRequest(BaseModel):
    build_id: int
    hero_id: int
    title: Optional[str] = None


class GuideExportResponse(BaseModel):
    title: str
    content: str
    html_preview: str = ""
    filename: str = ""


# ── Sync ──────────────────────────────────────────────────────────────

class SyncStatusResponse(BaseModel):
    last_sync: Optional[datetime.datetime] = None
    heroes_count: int = 0
    builds_count: int = 0
    is_syncing: bool = False
    current_patch: str = ""


# ── Build selection ───────────────────────────────────────────────────

class BuildSelectRequest(BaseModel):
    build_id: int
    match_id: Optional[str] = None


class BuildHistoryEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    hero_id: int
    build_id: int
    used_at: datetime.datetime
    match_id: Optional[str] = None


# ── In-game assistant ────────────────────────────────────────────────

class NextAction(BaseModel):
    """What the player should do next based on current game state."""
    next_skill: Optional[str] = None  # e.g. "Q", "W", "E", "R"
    next_skill_name: Optional[str] = None
    next_items: list[str] = []
    next_item_cost: int = 0
    gold_needed: int = 0
    power_spike_soon: bool = False
    power_spike_level: Optional[int] = None
    game_phase: str = "early"  # early / mid / late
    tip: str = ""
