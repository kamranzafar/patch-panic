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

"""Unit tests for the game rules. No window or audio needed."""
import random

import pytest

from patch_panic.config import (BLOAT, CARRIER_SPEED_FACTOR, COMBO_MAX, COMBO_WINDOW, DISK_SNAP_RADIUS, FRY_TIME,
                                HITSTOP_TIME, HONEYPOT_TIME, PERFECT_SAFETY, SABOTAGE_TIME, SCAVENGE_WAIT, SHAKE_TIME,
                                SURGE_WARNING_TIME, SWEEP_CLICKS, Gremlins, LevelConfig, Points)
from patch_panic.effects import Effects
from patch_panic.entities import Disk, GremlinState, Surge
from patch_panic.events import Event, EventBus
from patch_panic.powerups import AntivirusSweep, AutoPatch, Firewall, HoneypotLure, Rollback, SurgeGuard
from patch_panic.world import Outcome, World


class Recorder:
    """Collects every event emitted on a bus."""

    def __init__(self, bus: EventBus):
        self.events = []
        for event in Event:
            bus.subscribe(event, lambda _e=event, **data: self.events.append((_e, data)))

    def names(self):
        return [e for e, _ in self.events]


@pytest.fixture
def bus():
    return EventBus()


@pytest.fixture
def world(bus):
    return World(level=1, score=0, bus=bus, rng=random.Random(42))


def run_until(world, condition, dt=1 / 60, max_seconds=60):
    for _ in range(int(max_seconds / dt)):
        if condition():
            return
        world.update(dt)
    raise AssertionError("condition never became true")


def infect(world, computer):
    """Put a gremlin on `computer` and let it finish installing."""
    gremlin = world.spawn_gremlin(computer)
    gremlin.x, gremlin.y = computer.work_spot()
    gremlin.start_install()
    world.to_spawn = 0
    run_until(world, lambda: gremlin.state is GremlinState.WALK_OUT)
    return gremlin


# --- configuration ---------------------------------------------------------------
def test_level_config_gets_harder_and_is_capped():
    easy, hard, extreme = (LevelConfig.for_level(n) for n in (1, 10, 100))
    assert easy.gremlins < hard.gremlins
    assert easy.install_time > hard.install_time
    assert extreme.computers == 16
    assert extreme.install_time == pytest.approx(1.1)


def test_level_config_rejects_level_zero():
    with pytest.raises(ValueError):
        LevelConfig.for_level(0)


# --- event bus -------------------------------------------------------------------
def test_event_bus_delivers_data_to_subscribers(bus):
    received = []
    bus.subscribe(Event.SCORED, lambda **data: received.append(data))
    bus.emit(Event.SCORED, points=5, x=1, y=2)
    assert received == [{"points": 5, "x": 1, "y": 2}]


# --- setup -------------------------------------------------------------------------
def test_new_world_has_clean_networked_computers(world):
    assert len(world.computers) == world.config.computers
    assert world.clean_count == len(world.computers)
    assert all(world.neighbours(c) for c in world.computers)


# --- gremlins -------------------------------------------------------------------------
def test_gremlin_installs_bloat_and_steals_os(world, bus):
    rec = Recorder(bus)
    computer = world.computers[0]
    native = computer.native
    gremlin = infect(world, computer)
    assert computer.os == BLOAT
    assert gremlin.carry == native
    assert Event.COMPUTER_INFECTED in rec.names()


def test_squashing_installer_saves_computer(world):
    computer = world.computers[0]
    gremlin = world.spawn_gremlin(computer)
    gremlin.x, gremlin.y = computer.work_spot()
    gremlin.start_install()
    world.update(0.5)
    assert world.click((gremlin.x, gremlin.y - 12))
    assert gremlin.state is GremlinState.DYING
    assert computer.targeted is None and computer.install == 0
    assert world.score == Points.SQUASH


def test_squashing_carrier_drops_disk_that_restores_computer(world):
    computer = world.computers[0]
    gremlin = infect(world, computer)
    world.click((gremlin.x, gremlin.y - 12))
    assert world.score == Points.SQUASH_CARRIER
    disk = world.disks[0]
    assert disk.kind == computer.native

    world.click((disk.x, disk.y))
    assert world.dragging is disk
    world.release((computer.x, computer.y))
    assert computer.is_clean
    assert world.score == Points.SQUASH_CARRIER + Points.RESTORE_OS


def test_disk_rejected_by_wrong_computer(world, bus):
    rec = Recorder(bus)
    wrong = next(c for c in world.computers if c.native != world.computers[0].native)
    world.dragging = Disk(world.computers[0].native, 10, 10)
    world.release((wrong.x, wrong.y))
    assert Event.DISK_REJECTED in rec.names()
    assert len(world.disks) == 1  # disk lands back on the floor


# --- surges ----------------------------------------------------------------------------
def test_surge_fries_computer_ejects_os_and_zaps_installer(world, bus):
    rec = Recorder(bus)
    src, dst = world.cables[0]
    gremlin = world.spawn_gremlin(dst)
    gremlin.x, gremlin.y = dst.work_spot()
    gremlin.start_install()
    world.surges.append(Surge(src, dst, 0.99, speed=10_000))
    world.update(0.01)

    assert dst.fried == pytest.approx(FRY_TIME, abs=0.05)
    assert dst.os is None
    assert any(d.kind == dst.native for d in world.disks)
    assert gremlin.state is GremlinState.DYING
    assert {Event.COMPUTER_FRIED, Event.OS_EJECTED, Event.GREMLIN_ZAPPED} <= set(rec.names())


def test_rebooting_computer_refuses_disk_until_reboot(world):
    src, dst = world.cables[0]
    world._fry(dst)
    assert not dst.accepts(dst.native)
    world.update(FRY_TIME + 0.1)
    assert dst.accepts(dst.native)


def test_clicking_surge_zaps_it(world):
    src, dst = world.cables[0]
    surge = Surge(src, dst, 0.5, speed=1)
    world.surges.append(surge)
    assert world.click(surge.pos)
    assert not world.surges
    assert world.score == Points.ZAP_SURGE


def test_surge_is_announced_before_it_appears(world, bus):
    rec = Recorder(bus)
    world.spawn_gremlin(world.computers[0])  # keeps the wave active
    world.to_spawn = 0
    world.surge_timer = 0
    world.update(0.01)
    assert not world.surges and len(world.surge_warnings) == 1
    assert Event.SURGE_WARNING in rec.names()
    world.update(SURGE_WARNING_TIME)
    assert len(world.surges) == 1 and not world.surge_warnings


def test_surge_guard_clears_pending_warnings(world):
    src, dst = world.cables[0]
    world.warn_surge(src, dst, 0.2)
    SurgeGuard().apply(world)
    world.update(SURGE_WARNING_TIME + 0.1)
    assert not world.surge_warnings and not world.surges


# --- disks -----------------------------------------------------------------------------
def test_disk_snaps_to_nearby_matching_computer(world):
    computer = world.computers[0]
    computer.os = BLOAT
    world.dragging = Disk(computer.native, 0, 0)
    world.release((computer.x + DISK_SNAP_RADIUS - 5, computer.y))
    assert computer.is_clean


def test_disk_does_not_snap_from_far_away(world):
    computer = world.computers[0]
    computer.os = BLOAT
    assert world.snap_target((computer.x, computer.y), computer.native) is computer
    assert world.snap_target((computer.x + DISK_SNAP_RADIUS + 5, computer.y + 40), computer.native) is None


# --- feedback effects -------------------------------------------------------------------
def test_carrier_swat_triggers_hitstop_and_fry_shakes(world, bus):
    effects = Effects()
    effects.connect(bus)
    rec = Recorder(bus)
    gremlin = infect(world, world.computers[0])
    world.click((gremlin.x, gremlin.y - 12))
    assert rec.events[-2] == (Event.GREMLIN_SQUASHED, {"x": gremlin.x, "y": gremlin.y, "carrier": True,
                                                        "kind": Gremlins.STANDARD})
    assert effects.hitstop == pytest.approx(HITSTOP_TIME)
    world._fry(world.computers[1])
    assert effects.shake == pytest.approx(SHAKE_TIME)
    effects.update(1.0)
    assert effects.hitstop == 0 and effects.shake_strength == 0


def test_motion_effects_can_be_turned_off(world, bus):
    effects = Effects()
    effects.motion = False
    effects.connect(bus)
    world._fry(world.computers[0])
    assert effects.shake == 0


# --- power-ups (strategies) ----------------------------------------------------------
def test_firewall_freezes_gremlins(world):
    gremlin = world.spawn_gremlin(world.computers[0])
    start = (gremlin.x, gremlin.y)
    Firewall().apply(world)
    world.update(0.5)
    assert (gremlin.x, gremlin.y) == start


def test_surge_guard_clears_and_blocks_surges(world):
    src, dst = world.cables[0]
    world.surges.append(Surge(src, dst, 0.5, speed=1))
    SurgeGuard().apply(world)
    assert not world.surges
    world.surge_timer = 0
    world.update(0.1)
    assert not world.surges


def test_auto_patch_only_available_when_something_is_broken(world):
    assert not AutoPatch().is_available(world)
    world.computers[0].os = BLOAT
    world.computers[1].os = None
    assert AutoPatch().is_available(world)
    AutoPatch().apply(world)
    assert world.computers[0].is_clean and world.computers[1].is_clean


def test_antivirus_sweep_extends_reach_for_a_few_clicks(world):
    AntivirusSweep().apply(world)
    gremlin = walking_gremlin(world, world.computers[0])
    assert world.click((gremlin.x + gremlin.HIT_RADIUS + 10, gremlin.y - 12))
    assert world.sweep_clicks == SWEEP_CLICKS - 1


def test_rollback_sends_disks_home(world):
    a, b = world.computers[0], world.computers[1]
    a.os, b.os = BLOAT, None
    world.disks.append(Disk(a.native, 100, 100))
    world.dragging = Disk(b.native, 200, 200)
    assert Rollback().is_available(world)
    Rollback().apply(world)
    assert a.is_clean and b.is_clean
    assert world.dragging is None and not world.disks
    assert not Rollback().is_available(world)


def test_honeypot_lures_walking_gremlins_until_it_expires(world):
    gremlin = walking_gremlin(world, world.computers[0])
    HoneypotLure().apply(world)
    honeypot = world.honeypot
    assert honeypot.timer == HONEYPOT_TIME
    run_until(world, lambda: (gremlin.x, gremlin.y) == honeypot.spot_for(gremlin), max_seconds=HONEYPOT_TIME)
    assert gremlin.state is GremlinState.WALK_IN
    run_until(world, lambda: world.honeypot is None)
    run_until(world, lambda: gremlin.state is GremlinState.INSTALL)


def test_powerup_appears_halfway_and_awards_points(world, bus):
    rec = Recorder(bus)
    world.to_spawn = world.config.gremlins // 2
    world.update(0.01)
    assert world.powerup is not None
    world.click((world.powerup.x, world.powerup.y))
    assert world.score == Points.POWERUP_PER_LEVEL
    assert Event.POWERUP_COLLECTED in rec.names()


# --- scoring -------------------------------------------------------------------------------
def walking_gremlin(world, computer):
    gremlin = world.spawn_gremlin(computer)
    gremlin.x, gremlin.y = computer.x, computer.y + 150
    return gremlin


def test_quick_swats_build_a_combo(world, bus):
    rec = Recorder(bus)
    first, second, third = (walking_gremlin(world, c) for c in world.computers[:3])
    world.click((first.x, first.y - 12))
    world.click((second.x, second.y - 12))
    assert world.combo == 2
    assert world.score == Points.SQUASH + 2 * Points.SQUASH
    assert (Event.COMBO, {"count": 2, "x": second.x, "y": second.y}) in rec.events

    world.update(COMBO_WINDOW + 0.01)
    assert world.combo == 0
    world.click((third.x, third.y - 12))
    assert world.combo == 1


def test_combo_is_capped_and_reset_by_a_miss(world, bus):
    rec = Recorder(bus)
    for _ in range(COMBO_MAX + 2):
        g = walking_gremlin(world, world.computers[0])
        world.click((g.x, g.y - 12))
    assert world.combo == COMBO_MAX
    assert not world.click((-500, -500))
    assert world.combo == 0
    assert Event.CLICK_MISSED in rec.names()


def test_carrier_runs_faster(world):
    gremlin = world.spawn_gremlin(world.computers[0])
    speed = gremlin.speed
    gremlin.x, gremlin.y = world.computers[0].work_spot()
    gremlin.start_install()
    world.to_spawn = 0
    run_until(world, lambda: gremlin.state is GremlinState.WALK_OUT)
    assert gremlin.speed == pytest.approx(speed * CARRIER_SPEED_FACTOR)


def test_catching_a_carrier_near_the_exit_is_a_close_call(world, bus):
    rec = Recorder(bus)
    gremlin = infect(world, world.computers[0])
    run_until(world, lambda: gremlin.escape_progress > 0.8)
    world.click((gremlin.x, gremlin.y - 12))
    assert Event.CLOSE_CALL in rec.names()
    assert world.score == Points.SQUASH_CARRIER + Points.LATE_CATCH


# --- gremlin kinds --------------------------------------------------------------------------
LAST_NEW_KIND_LEVEL = max(k.first_level for k in Gremlins.ALL)


def test_new_kinds_are_introduced_level_by_level():
    assert LevelConfig.for_level(1).kinds == (Gremlins.STANDARD,)
    for kind in Gremlins.ALL[1:]:
        assert kind not in LevelConfig.for_level(kind.first_level - 1).kinds
        assert kind in LevelConfig.for_level(kind.first_level).kinds
    assert LevelConfig.for_level(LAST_NEW_KIND_LEVEL).kinds == Gremlins.ALL


def test_first_appearance_of_a_kind_is_announced_once(bus):
    rec = Recorder(bus)
    world = World(level=Gremlins.SPRINTER.first_level, bus=bus, rng=random.Random(1))
    world.spawn_gremlin(world.computers[0], Gremlins.SPRINTER)
    world.spawn_gremlin(world.computers[1], Gremlins.SPRINTER)
    assert rec.names().count(Event.NEW_THREAT) == 1


def test_sprinter_is_faster_and_harder_to_hit(world):
    computer = world.computers[0]
    sprinter = world.spawn_gremlin(computer, Gremlins.SPRINTER, pos=(computer.x, computer.y + 150))
    assert sprinter.speed > world.config.gremlin_speed * 1.2
    edge = sprinter.HIT_RADIUS - 2  # inside a standard gremlin's reach, outside a sprinter's
    assert not world.click((sprinter.x + edge, sprinter.y - 12))


def test_armored_gremlin_takes_two_swats(world, bus):
    rec = Recorder(bus)
    gremlin = walking_gremlin(world, world.computers[0])
    gremlin.kind, gremlin.hp = Gremlins.ARMORED, Gremlins.ARMORED.hits
    world.click((gremlin.x, gremlin.y - 12))
    assert gremlin.is_alive and gremlin.is_damaged
    assert Event.GREMLIN_HIT in rec.names() and world.score == 0
    world.click((gremlin.x, gremlin.y - 12))
    assert not gremlin.is_alive
    assert world.score > 0


def test_splitter_splits_into_sprinters(world, bus):
    rec = Recorder(bus)
    computer = world.computers[0]
    splitter = world.spawn_gremlin(computer, Gremlins.SPLITTER, pos=(computer.x, computer.y + 150))
    world.click((splitter.x, splitter.y - 12))
    kids = [g for g in world.alive_gremlins if g.kind is Gremlins.SPRINTER]
    assert len(kids) == Gremlins.SPLITTER.splits
    assert all(k.target is not None and k.target.targeted is k for k in kids)
    assert Event.GREMLIN_SPLIT in rec.names()


def sabotaging(world):
    cable = world.cables[0]
    saboteur = world.spawn_saboteur(cable)
    saboteur.x, saboteur.y = saboteur.cable_spot()
    world.to_spawn = 0
    world.update(0.01)
    assert saboteur.state is GremlinState.SABOTAGE
    return saboteur


def test_saboteur_chews_a_cable_into_a_surge(world, bus):
    rec = Recorder(bus)
    saboteur = sabotaging(world)
    run_until(world, lambda: world.surges, max_seconds=SABOTAGE_TIME + 0.1)
    assert len(world.surges) == 1 and set((world.surges[0].src, world.surges[0].dst)) == set(saboteur.cable)
    assert saboteur.state is GremlinState.WALK_OUT
    assert Event.CABLE_SABOTAGED in rec.names()


def test_swatting_a_saboteur_stops_the_surge(world):
    saboteur = sabotaging(world)
    world.click((saboteur.x, saboteur.y - 12))
    world.update(SABOTAGE_TIME)
    assert not world.surges


def scavenger_near(world, x, y):
    gremlin = world.spawn_saboteur(world.cables[0], pos=(x, y), kind=Gremlins.SCAVENGER)
    world.to_spawn = 0
    return gremlin


def test_scavenger_steals_a_loose_disk_and_runs(world, bus):
    rec = Recorder(bus)
    computer = world.computers[0]
    computer.os = None
    disk = Disk(computer.native, 300, 300)
    world.disks.append(disk)
    scavenger = scavenger_near(world, 340, 300)
    speed = scavenger.speed
    run_until(world, lambda: scavenger.carry is not None, max_seconds=3)
    assert scavenger.carry == computer.native and disk not in world.disks
    assert scavenger.state is GremlinState.WALK_OUT
    assert scavenger.speed == pytest.approx(speed * CARRIER_SPEED_FACTOR)
    assert Event.DISK_STOLEN in rec.names()

    world.click((scavenger.x, scavenger.y - 12))  # swat it: the disk drops again
    assert [d.kind for d in world.disks] == [computer.native]


def test_scavenger_retargets_when_the_player_grabs_its_disk_first(world):
    a, b = world.computers[0], world.computers[1]
    a.os = b.os = None
    near, far = Disk(a.native, 320, 300), Disk(b.native, 600, 400)
    world.disks += [near, far]
    scavenger = scavenger_near(world, 360, 300)
    world.update(0.01)
    assert scavenger.loot is near
    world.click((near.x, near.y))  # the player picks it up first
    world.update(0.01)
    assert scavenger.loot is far


def test_two_scavengers_go_for_different_disks(world):
    a, b = world.computers[0], world.computers[1]
    world.disks += [Disk(a.native, 300, 300), Disk(b.native, 600, 400)]
    first, second = scavenger_near(world, 450, 350), scavenger_near(world, 460, 350)
    world.update(0.01)
    assert first.loot is not None and second.loot is not None and first.loot is not second.loot


def test_scavenger_chews_a_cable_then_waits_for_loot(world, bus):
    rec = Recorder(bus)
    scavenger = world.spawn_saboteur(world.cables[0], kind=Gremlins.SCAVENGER)
    scavenger.x, scavenger.y = scavenger.cable_spot()
    world.to_spawn = 0
    run_until(world, lambda: Event.CABLE_SABOTAGED in rec.names(), max_seconds=SABOTAGE_TIME + 0.5)
    assert scavenger.state is GremlinState.WALK_IN and scavenger.cable is None  # sticks around
    computer = world.computers[2]
    computer.os = None
    world.disks.append(Disk(computer.native, scavenger.x + 30, scavenger.y))
    run_until(world, lambda: scavenger.carry is not None, max_seconds=2)


def test_scavenger_leaves_if_nothing_turns_up(world):
    world.shield_cables(60)  # no surge, so nothing gets knocked loose
    scavenger = world.spawn_saboteur(world.cables[0], kind=Gremlins.SCAVENGER)
    scavenger.x, scavenger.y = scavenger.cable_spot()
    world.to_spawn = 0
    run_until(world, lambda: scavenger.state is GremlinState.WALK_OUT,
              max_seconds=SABOTAGE_TIME + SCAVENGE_WAIT + 0.5)
    assert scavenger.carry is None


def test_spawning_mixes_in_the_level_kinds(bus):
    world = World(level=LAST_NEW_KIND_LEVEL, bus=bus, rng=random.Random(5))
    world.to_spawn = 60
    spawned = set()
    for _ in range(60):
        world.spawn_timer = 0
        world._update_spawning(0.01)
        spawned.update(g.kind for g in world.gremlins)
        world.gremlins.clear()
        for c in world.computers:
            c.targeted = None
    assert spawned == set(Gremlins.ALL)


# --- level outcome -----------------------------------------------------------------------
def test_level_clears_when_wave_is_over(world, bus):
    rec = Recorder(bus)
    world.to_spawn = 0
    world.update(0.01)
    assert world.outcome is Outcome.CLEARED
    assert world.level_bonus == len(world.computers) * Points.CLEAN_PER_LEVEL
    assert Event.LEVEL_CLEARED in rec.names()


def test_level_fails_when_most_computers_are_infected(world):
    for computer in world.computers[: len(world.computers) // 2 + 1]:
        computer.os = BLOAT
    world.to_spawn = 0
    world.update(0.01)
    assert world.outcome is Outcome.FAILED


def test_level_waits_while_a_disk_can_still_be_restored(world):
    computer = world.computers[0]
    computer.os = None
    world.disks.append(Disk(computer.native, 100, 100))
    world.to_spawn = 0
    world.update(0.01)
    assert world.outcome is Outcome.IN_PROGRESS


def test_perfect_level_pays_a_bonus_and_earns_a_safety_net(world, bus):
    rec = Recorder(bus)
    world.to_spawn = 0
    world.update(0.01)
    assert world.perfect_bonus == Points.PERFECT_PER_LEVEL
    assert world.score == world.level_bonus + world.perfect_bonus
    assert world.earned_safety == PERFECT_SAFETY
    assert Event.PERFECT_LEVEL in rec.names()


def test_imperfect_level_has_no_perfect_bonus(world):
    world.computers[0].os = BLOAT
    world.to_spawn = 0
    world.update(0.01)
    assert world.outcome is Outcome.CLEARED
    assert world.perfect_bonus == 0 and world.earned_safety == 0


def test_safety_net_lowers_the_clean_machines_needed():
    normal = World(2, rng=random.Random(1))
    safe = World(2, rng=random.Random(1), safety=1)
    assert safe.required_clean == normal.required_clean - 1
    for computer in safe.computers[: len(safe.computers) - safe.required_clean]:
        computer.os = BLOAT
    safe.to_spawn = 0
    safe.update(0.01)
    assert safe.outcome is Outcome.CLEARED
