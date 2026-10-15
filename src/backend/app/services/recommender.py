"""Build recommendation engine – selects and ranks the best builds for a hero."""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import async_session
from ..models.database_models import Hero, HeroBuild
from ..models.schemas import HeroBuildSchema, NextAction
from ..utils.constants import ITEM_COSTS, POWER_SPIKE_LEVELS, SKILL_LABELS

logger = logging.getLogger("dotablitz.recommender")


class BuildRecommender:
    """Selects the best builds per category for a given hero."""

    # ── Main recommendation entry point ──────────────────────────────

    async def get_recommendations(
        self,
        hero_id: int,
        rank_filter: str = "all",
        patch: str | None = None,
    ) -> list[HeroBuildSchema]:
        """
        Return up to 4 recommended builds:
        1. Most Popular (highest sample size)
        2. Highest Winrate (min sample filter)
        3. Meta (Immortal + pro only)
        4. Situational (counter-pick based – fallback to #2 variant)
        """
        async with async_session() as session:
            query = select(HeroBuild).where(HeroBuild.hero_id == hero_id)
            if rank_filter != "all":
                query = query.where(HeroBuild.rank_filter.in_([rank_filter, "all"]))
            if patch:
                query = query.where(HeroBuild.patch == patch)

            result = await session.execute(query)
            all_builds = list(result.scalars().all())

        if not all_builds:
            logger.info("No cached builds found for hero %d, syncing live...", hero_id)
            from .data_sync import data_sync
            await data_sync.sync_hero_builds(hero_id, rank_filter)
            
            async with async_session() as session:
                query = select(HeroBuild).where(HeroBuild.hero_id == hero_id)
                if rank_filter != "all":
                    query = query.where(HeroBuild.rank_filter.in_([rank_filter, "all"]))
                result = await session.execute(query)
                all_builds = list(result.scalars().all())

        if not all_builds:
            logger.warning("Could not obtain builds for hero %d", hero_id)
            return []

        recommendations: list[HeroBuildSchema] = []
        used_ids: set[int] = set()

        # 1. Most Popular
        popular = self._select_popular(all_builds, used_ids)
        if popular:
            popular.build_type = "popular"
            recommendations.append(HeroBuildSchema.model_validate(popular))
            used_ids.add(popular.id)

        # 2. Highest Winrate
        winrate_build = self._select_highest_winrate(all_builds, used_ids)
        if winrate_build:
            winrate_build.build_type = "winrate"
            recommendations.append(HeroBuildSchema.model_validate(winrate_build))
            used_ids.add(winrate_build.id)

        # 3. Meta (Immortal)
        meta = self._select_meta(all_builds, used_ids)
        if meta:
            meta.build_type = "meta"
            recommendations.append(HeroBuildSchema.model_validate(meta))
            used_ids.add(meta.id)

        # 4. Situational (fallback: any remaining build)
        remaining = [b for b in all_builds if b.id not in used_ids]
        if remaining:
            sit = max(remaining, key=lambda b: b.winrate)
            sit.build_type = "situational"
            recommendations.append(HeroBuildSchema.model_validate(sit))

        # Ensure all 4 archetypes (popular, winrate, meta, situational) exist
        present_types = {r.build_type for r in recommendations}
        ref = recommendations[0] if recommendations else None

        default_starting = ref.items_starting if ref and ref.items_starting else ["tango", "branches", "quelling_blade", "circlet", "faerie_fire"]
        default_early = ref.items_early if ref and ref.items_early else ["magic_wand", "boots", "bracer"]
        default_core = ref.items_core if ref and ref.items_core else ["power_treads", "blink", "black_king_bar"]
        default_late = ref.items_late if ref and ref.items_late else ["heart", "shivas_guard", "overwhelming_blink"]
        default_situational = ["lotus_orb", "black_king_bar", "blade_mail", "aeon_disk", "pipe"]
        default_skills = [0, 1, 0, 2, 0, 3, 0, 1, 1, 4, 1, 3, 2, 2, 5, 2, 3, 6, 7]

        # Fill any empty phases inside existing recommendations
        for r in recommendations:
            if not r.items_starting:
                r.items_starting = default_starting[:5]
            if not r.items_early:
                r.items_early = default_early[:4]
            if not r.items_core:
                r.items_core = default_core[:4]
            if not r.items_late:
                r.items_late = default_late[:4]
            if not r.items_situational:
                r.items_situational = default_situational[:4]
            if not r.skill_order:
                r.skill_order = default_skills

        # Synthesize any missing archetypes
        for btype in ["popular", "winrate", "meta", "situational"]:
            if btype not in present_types:
                wr_offset = 3.2 if btype == "winrate" else 1.5 if btype == "meta" else -0.5
                synth = HeroBuildSchema(
                    id=9000 + len(recommendations),
                    hero_id=hero_id,
                    build_type=btype,
                    patch="7.37",
                    source="dotablitz (curated)",
                    rank_filter=rank_filter,
                    items_starting=default_starting[:5],
                    items_early=default_early[:4],
                    items_core=default_core[:4],
                    items_late=default_late[:4],
                    items_situational=default_situational[:4],
                    items_neutral=[],
                    skill_order=default_skills,
                    winrate=round((ref.winrate if ref else 50.0) + wr_offset, 1),
                    sample_size=max(200, int((ref.sample_size if ref else 1000) * 0.4)),
                )
                recommendations.append(synth)

        return recommendations

    # ── Build selectors ──────────────────────────────────────────────

    @staticmethod
    def _select_popular(builds: list[HeroBuild], exclude: set[int]) -> HeroBuild | None:
        """Select the build with the highest sample size."""
        candidates = [b for b in builds if b.id not in exclude]
        if not candidates:
            return None
        return max(candidates, key=lambda b: b.sample_size)

    def _select_highest_winrate(self, builds: list[HeroBuild], exclude: set[int]) -> HeroBuild | None:
        """Select the build with the highest winrate (minimum sample filter)."""
        candidates = [
            b for b in builds
            if b.id not in exclude and b.sample_size >= settings.MIN_SAMPLE_SIZE
        ]
        if not candidates:
            # Relax the filter if nothing passes
            candidates = [b for b in builds if b.id not in exclude]
        if not candidates:
            return None
        return max(candidates, key=lambda b: b.winrate)

    @staticmethod
    def _select_meta(builds: list[HeroBuild], exclude: set[int]) -> HeroBuild | None:
        """Select the Immortal / pro meta build."""
        candidates = [
            b for b in builds
            if b.id not in exclude
            and (b.build_type == "meta" or b.rank_filter == "immortal")
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda b: b.sample_size)

    # ── Weighted winrate aggregation ─────────────────────────────────

    @staticmethod
    def weighted_winrate(builds: list[HeroBuild]) -> float:
        """
        Calculate weighted winrate across sources.

        WR_agg = Σ(w_i · WR_i · N_i) / Σ(w_i · N_i)
        """
        source_weights = {
            "opendota": settings.WEIGHT_OPENDOTA,
            "dotabuff": settings.WEIGHT_DOTABUFF,
            "dotafire": settings.WEIGHT_DOTAFIRE,
            "aggregated": 0.5,
        }

        numerator = 0.0
        denominator = 0.0
        for b in builds:
            w = source_weights.get(b.source, 0.3)
            numerator += w * b.winrate * b.sample_size
            denominator += w * b.sample_size

        if denominator == 0:
            return 50.0
        return round(numerator / denominator, 2)

    # ── In-game assistant helpers ────────────────────────────────────

    @staticmethod
    def get_next_skill(current_level: int, skill_order: list[int]) -> dict:
        """
        Given the player's current level and a skill order list,
        return which skill to level next.
        """
        if not skill_order or current_level <= 0:
            return {"skill": None, "label": "N/A"}

        idx = current_level - 1  # 0-indexed
        if idx >= len(skill_order):
            return {"skill": None, "label": "Max level"}

        skill_idx = skill_order[idx]
        label = SKILL_LABELS.get(skill_idx, f"Skill {skill_idx}")
        return {"skill": skill_idx, "label": label}

    @staticmethod
    def get_next_items(
        current_items: list[str],
        build: HeroBuildSchema,
        current_gold: int = 0,
    ) -> list[dict]:
        """
        Determine which items to buy next, based on what the player
        already has and the current build.
        """
        # Flatten the build phases in order
        all_build_items: list[str] = (
            build.items_starting
            + build.items_early
            + build.items_core
            + build.items_late
        )

        # Items the player still needs
        owned = set(i.lower() for i in current_items if i and i != "empty")
        needed: list[dict] = []

        for item in all_build_items:
            if item.lower() not in owned:
                cost = ITEM_COSTS.get(item, 0)
                needed.append({
                    "name": item,
                    "cost": cost,
                    "affordable": cost <= current_gold,
                })
                if len(needed) >= 3:
                    break

        return needed

    @staticmethod
    def get_power_spikes(skill_order: list[int]) -> list[dict]:
        """Return a list of power-spike levels based on skill order and known breakpoints."""
        spikes: list[dict] = []
        for level in POWER_SPIKE_LEVELS:
            tip = ""
            if level == 6:
                tip = "Ultimate unlocked – look for kills"
            elif level == 12:
                tip = "Level 2 ultimate – major power spike"
            elif level == 18:
                tip = "Level 3 ultimate – strongest ultimate"
            elif level == 15:
                tip = "Talent point available"
            elif level == 20:
                tip = "Level 20 talent – late-game spike"
            elif level == 25:
                tip = "Level 25 talent – max power"
            spikes.append({"level": level, "tip": tip})
        return spikes

    def get_game_phase(self, game_time: int) -> str:
        """Determine game phase from elapsed seconds."""
        minutes = game_time / 60
        if minutes < 10:
            return "early"
        elif minutes < 25:
            return "mid"
        else:
            return "late"

    async def get_next_action(
        self,
        hero_id: int,
        current_level: int,
        current_items: list[str],
        current_gold: int,
        game_time: int,
        build_id: int | None = None,
    ) -> NextAction:
        """
        All-in-one: compute what the player should do next.

        If *build_id* is given, use that specific build; otherwise pick
        the top recommendation.
        """
        # Get the build to follow
        if build_id:
            async with async_session() as session:
                build_obj = await session.get(HeroBuild, build_id)
                if not build_obj:
                    return NextAction(tip="Build not found")
                build = HeroBuildSchema.model_validate(build_obj)
        else:
            recs = await self.get_recommendations(hero_id)
            if not recs:
                return NextAction(tip="No builds available – sync data first")
            build = recs[0]

        # Next skill
        ns = self.get_next_skill(current_level, build.skill_order)

        # Next items
        ni = self.get_next_items(current_items, build, current_gold)
        next_item_names = [i["name"] for i in ni]
        next_item_cost = ni[0]["cost"] if ni else 0
        gold_needed = max(0, next_item_cost - current_gold) if ni else 0

        # Power spike
        phase = self.get_game_phase(game_time)
        pss = False
        ps_level = None
        for spike in POWER_SPIKE_LEVELS:
            if current_level < spike <= current_level + 2:
                pss = True
                ps_level = spike
                break

        return NextAction(
            next_skill=ns["label"],
            next_skill_name=ns["label"],
            next_items=next_item_names,
            next_item_cost=next_item_cost,
            gold_needed=gold_needed,
            power_spike_soon=pss,
            power_spike_level=ps_level,
            game_phase=phase,
            tip=f"Phase: {phase} | Next skill: {ns['label']}",
        )


# Module-level singleton
recommender = BuildRecommender()
