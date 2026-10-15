"""Unit tests for the Build Recommender engine."""

import pytest
from src.backend.app.models.database_models import HeroBuild
from src.backend.app.models.schemas import HeroBuildSchema
from src.backend.app.services.recommender import BuildRecommender


def test_weighted_winrate_calculation():
    recommender = BuildRecommender()
    
    build1 = HeroBuild(
        id=1, hero_id=1, build_type="popular", source="opendota",
        winrate=50.0, sample_size=100
    )
    build2 = HeroBuild(
        id=2, hero_id=1, build_type="winrate", source="dotabuff",
        winrate=60.0, sample_size=100
    )
    
    # weights: opendota=0.5, dotabuff=0.3
    # num: (0.5 * 50 * 100) + (0.3 * 60 * 100) = 2500 + 1800 = 4300
    # den: (0.5 * 100) + (0.3 * 100) = 50 + 30 = 80
    # weighted: 4300 / 80 = 53.75
    aggregated = recommender.weighted_winrate([build1, build2])
    assert aggregated == 53.75


def test_next_skill_recommendation():
    recommender = BuildRecommender()
    skill_order = [0, 1, 0, 2, 0, 3]  # Q, W, Q, E, Q, R

    # Level 1 (idx 0) -> Q
    action1 = recommender.get_next_skill(current_level=1, skill_order=skill_order)
    assert action1["label"] == "Q"

    # Level 2 (idx 1) -> W
    action2 = recommender.get_next_skill(current_level=2, skill_order=skill_order)
    assert action2["label"] == "W"

    # Level 6 (idx 5) -> R
    action6 = recommender.get_next_skill(current_level=6, skill_order=skill_order)
    assert action6["label"] == "R"


def test_next_items_needed():
    recommender = BuildRecommender()
    build = HeroBuildSchema(
        id=1,
        hero_id=1,
        build_type="popular",
        items_starting=["tango", "branches"],
        items_early=["magic_wand", "power_treads"],
        items_core=["blink", "black_king_bar"],
        items_late=["heart"],
        items_situational=[],
        items_neutral=[],
        skill_order=[0, 1, 0, 2, 0, 3],
        winrate=52.0,
        sample_size=1000,
    )

    current_items = ["tango", "branches", "magic_wand"]
    needed = recommender.get_next_items(current_items, build, current_gold=1500)
    
    assert len(needed) > 0
    # Next required item in chain should be power_treads
    assert needed[0]["name"] == "power_treads"
    assert needed[0]["affordable"] is True  # 1500 gold >= 1400 cost
