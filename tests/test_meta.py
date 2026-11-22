# Patch Panic - defend your workstations from bloatware gremlins.
# Copyright (C) 2026 Kamran Zafar
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Tests for everything around a game: runs, difficulty, settings, save file."""
import json
import random
from datetime import date

import pygame
import pytest

from patch_panic.achievements import ACHIEVEMENTS, AchievementTracker
from patch_panic.events import Event, EventBus
from patch_panic.stats import RunStats

from patch_panic.config import COMBO_MAX, LEADERBOARD_SIZE, Difficulty, GameMode, Gremlins, LevelConfig
from patch_panic.run import Run
from patch_panic.settings import DEFAULT_KEYS, Action, Settings
from patch_panic.storage import SaveStore, ScoreEntry
from patch_panic.world import World


@pytest.fixture
def save_path(tmp_path):
    return tmp_path / "save.json"


# --- difficulty and runs ----------------------------------------------------------
def test_difficulty_scales_level_config():
    relaxed, normal, frantic = (LevelConfig.for_level(4, d) for d in Difficulty)
    assert normal == LevelConfig.for_level(4)
    assert relaxed.gremlin_speed < normal.gremlin_speed < frantic.gremlin_speed
    assert relaxed.install_time > normal.install_time > frantic.install_time
    assert relaxed.gremlins < normal.gremlins < frantic.gremlins
    assert relaxed.computers == normal.computers == frantic.computers


def test_difficulty_cycles():
    assert Difficulty.NORMAL.next() is Difficulty.FRANTIC
    assert Difficulty.FRANTIC.next() is Difficulty.RELAXED


def test_daily_run_builds_the_same_layout_for_everyone():
    day = date(2026, 11, 22)
    run_a, run_b = Run.daily(day), Run.daily(day)
    assert run_a.seed == 20261122 and run_a.difficulty is Difficulty.NORMAL
    world_a = World(3, rng=run_a.level_rng(3), config=run_a.level_config(3))
    world_b = World(3, rng=run_b.level_rng(3), config=run_b.level_config(3))
    assert [(c.x, c.y, c.native) for c in world_a.computers] == [(c.x, c.y, c.native) for c in world_b.computers]
    other_day = World(3, rng=Run.daily(date(2026, 11, 23)).level_rng(3))
    assert [(c.x, c.y) for c in other_day.computers] != [(c.x, c.y) for c in world_a.computers]


def test_world_uses_given_config():
    config = LevelConfig.for_level(1, Difficulty.FRANTIC)
    assert World(1, config=config).config is config


# --- settings ---------------------------------------------------------------------------
def test_settings_round_trip():
    settings = Settings(Difficulty.RELAXED, colourblind=True, screen_shake=False)
    settings.keys[Action.PAUSE] = 32
    assert Settings.from_dict(json.loads(json.dumps(settings.to_dict()))) == settings


@pytest.mark.parametrize("data", [None, [], {"difficulty": ["x"], "colourblind": "yes", "keys": {"PAUSE": True}}])
def test_settings_ignore_bad_values(data):
    settings = Settings.from_dict(data)
    assert settings == Settings()
    assert settings.keys == DEFAULT_KEYS


# --- save file -------------------------------------------------------------------------
def test_missing_or_corrupt_save_is_empty(save_path):
    assert SaveStore(save_path).best == 0
    save_path.write_text("{not json")
    store = SaveStore(save_path)
    assert store.best == 0 and store.leaderboard == []


def test_version_1_save_is_migrated(save_path):
    save_path.write_text(json.dumps({"highscore": 1234}))
    store = SaveStore(save_path)
    assert store.best == 1234
    assert len(store.leaderboard) == 1


def test_save_round_trip(save_path):
    store = SaveStore(save_path)
    store.record(ScoreEntry(500, 3, GameMode.DAILY.name, "KAZ", "2026-11-22"))
    store.unlock("first_swat")
    store.settings = {"colourblind": True}
    store.save()

    again = SaveStore(save_path)
    assert again.best == 500
    assert again.initials == "KAZ"
    assert again.achievements == {"first_swat"}
    assert again.settings == {"colourblind": True}
    assert again.entries_for(GameMode.DAILY, "2026-11-22")[0].initials == "KAZ"


def test_leaderboard_is_sorted_and_capped(save_path):
    store = SaveStore(save_path)
    for score in range(10, 10 * (LEADERBOARD_SIZE + 3), 10):
        store.record(ScoreEntry(score, 1))
    scores = [e.score for e in store.leaderboard]
    assert len(scores) == LEADERBOARD_SIZE
    assert scores == sorted(scores, reverse=True)
    assert not store.qualifies(scores[-1])
    assert store.record(ScoreEntry(0, 1)) is None
    assert store.record(ScoreEntry(10_000, 1)) == 0


# --- key bindings -------------------------------------------------------------------
def test_rebinding_a_used_key_swaps_the_two_actions():
    settings = Settings()
    settings.rebind(Action.PAUSE, DEFAULT_KEYS[Action.MUTE])
    assert settings.keys[Action.PAUSE] == DEFAULT_KEYS[Action.MUTE]
    assert settings.keys[Action.MUTE] == DEFAULT_KEYS[Action.PAUSE]
    event = pygame.event.Event(pygame.KEYDOWN, key=DEFAULT_KEYS[Action.MUTE])
    assert settings.is_action(event, Action.PAUSE)
    assert not settings.is_action(event, Action.MUTE)


# --- stats and achievements ---------------------------------------------------------------
@pytest.fixture
def tracked(save_path):
    """A bus with RunStats and achievements attached, the way App wires them."""
    bus = EventBus()
    stats = RunStats()
    stats.connect(bus)
    save = SaveStore(save_path)
    tracker = AchievementTracker(stats, save)
    tracker.connect(bus)
    unlocked = []
    bus.subscribe(Event.ACHIEVEMENT_UNLOCKED, lambda achievement: unlocked.append(achievement.id))
    return bus, stats, save, tracker, unlocked


def test_stats_count_hits_misses_and_combos(tracked):
    bus, stats, *_ = tracked
    world = World(1, bus=bus, rng=random.Random(2))
    computer = world.computers[0]
    for _ in range(3):
        g = world.spawn_gremlin(computer, pos=(computer.x, computer.y + 150))
        world.click((g.x, g.y - 12))
    world.click((-100, -100))
    assert stats.swats == 3 and stats.misses == 1
    assert stats.accuracy == pytest.approx(0.75)
    assert stats.best_combo == 3
    assert stats.level == 1


def test_achievements_unlock_once_and_persist(tracked, save_path):
    bus, stats, save, tracker, unlocked = tracked
    world = World(1, bus=bus, rng=random.Random(2))
    computer = world.computers[0]
    for _ in range(2):
        g = world.spawn_gremlin(computer, pos=(computer.x, computer.y + 150))
        world.click((g.x, g.y - 12))
    assert unlocked == ["first_swat"]
    assert "first_swat" in SaveStore(save_path).achievements


def test_every_achievement_can_be_earned(tracked):
    bus, stats, save, tracker, unlocked = tracked
    stats.reset(GameMode.DAILY)
    stats.swats = stats.armored_swats = stats.chain_zaps = stats.perfect_levels = 1
    stats.best_combo, stats.level_restores, stats.level = COMBO_MAX, 5, 10
    tracker.check(bus)
    assert set(unlocked) == {a.id for a in ACHIEVEMENTS}


def test_achievements_can_be_disabled(tracked):
    bus, stats, save, tracker, unlocked = tracked
    tracker.enabled = False
    stats.swats = 1
    tracker.check(bus)
    assert not unlocked and not save.achievements


def test_armored_and_chained_kills_are_counted(tracked):
    bus, stats, *_ = tracked
    bus.emit(Event.GREMLIN_SQUASHED, x=0, y=0, carrier=False, kind=Gremlins.ARMORED)
    bus.emit(Event.SURGE_ZAPPED, x=0, y=0, chained=True)
    assert stats.armored_swats == 1 and stats.chain_zaps == 1
