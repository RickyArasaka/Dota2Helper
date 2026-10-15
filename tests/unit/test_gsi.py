"""Unit tests for GSI event parser and detection."""

import pytest
from src.backend.app.services.gsi_handler import GSIHandler


def test_parse_gsi_event():
    handler = GSIHandler()
    sample_payload = {
        "provider": {"name": "Dota 2", "appid": 570},
        "map": {"matchid": "789123456", "game_time": 900, "game_state": "DOTA_GAMERULES_STATE_GAME_IN_PROGRESS"},
        "player": {"kills": 3, "deaths": 1, "assists": 5, "gold": 2150},
        "hero": {"id": 14, "name": "npc_dota_hero_pudge", "level": 9, "alive": True},
        "items": {
            "slot0": {"name": "item_boots"},
            "slot1": {"name": "item_magic_wand"},
            "slot2": {"name": "item_bottle"}
        }
    }

    snapshot = handler.parse_event(sample_payload)
    assert snapshot.hero_id == 14
    assert snapshot.hero_name == "pudge"
    assert snapshot.hero_level == 9
    assert snapshot.gold == 2150
    assert snapshot.match_id == "789123456"
    assert "boots" in snapshot.items
    assert "magic_wand" in snapshot.items
    assert "bottle" in snapshot.items
    assert snapshot.connected is True


def test_detect_level_up():
    handler = GSIHandler()
    
    # First event: level 5
    handler.parse_event({
        "hero": {"id": 14, "name": "npc_dota_hero_pudge", "level": 5}
    })
    assert handler.detect_level_up() is False

    # Second event: level 6
    handler.parse_event({
        "hero": {"id": 14, "name": "npc_dota_hero_pudge", "level": 6}
    })
    assert handler.detect_level_up() is True
