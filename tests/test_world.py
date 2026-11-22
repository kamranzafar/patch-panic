"""Unit tests for the game rules. No window or audio needed."""
import random

import pytest

from patch_panic.config import BLOAT, FRY_TIME, LevelConfig, Points
from patch_panic.entities import Disk, GremlinState, Surge
from patch_panic.events import Event, EventBus
from patch_panic.powerups import AutoPatch, Firewall, SurgeGuard
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


def test_powerup_appears_halfway_and_awards_points(world, bus):
    rec = Recorder(bus)
    world.to_spawn = world.config.gremlins // 2
    world.update(0.01)
    assert world.powerup is not None
    world.click((world.powerup.x, world.powerup.y))
    assert world.score == Points.POWERUP_PER_LEVEL
    assert Event.POWERUP_COLLECTED in rec.names()


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
