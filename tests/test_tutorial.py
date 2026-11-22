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

"""Tests for the scripted world and the tutorial's step-by-step flow."""
from types import SimpleNamespace

import pytest

from patch_panic.config import BLOAT, FRY_TIME, LevelConfig
from patch_panic.effects import Effects
from patch_panic.entities import GremlinState
from patch_panic.events import Event, EventBus
from patch_panic.settings import Settings
from patch_panic.storage import SaveStore
from patch_panic.tutorial import STEP_PAUSE, FryStep, PatchStep, RescueStep, SurgeStep, SwatStep, TutorialScene
from patch_panic.world import Outcome, World


class FakeApp:
    """Just enough of `App` for scenes to run without a window."""

    def __init__(self, tmp_path):
        self.bus = EventBus()
        self.effects = Effects()
        self.settings = Settings()
        self.save = SaveStore(tmp_path / "save.json")
        self.sounds = SimpleNamespace(muted=False)
        self.scene = None
        self.titles = 0

    def change_scene(self, scene):
        if self.scene is not None:
            self.scene.on_exit()
        self.scene = scene

    def show_title(self):
        self.titles += 1


@pytest.fixture
def app(tmp_path):
    return FakeApp(tmp_path)


@pytest.fixture
def tutorial(app):
    scene = TutorialScene(app)
    app.change_scene(scene)
    return scene


def tick(scene, seconds, dt=1 / 60):
    for _ in range(int(seconds / dt)):
        scene.update(dt)


def finish_step(scene):
    tick(scene, STEP_PAUSE + 0.1)


def test_scripted_world_spawns_nothing_and_never_ends():
    world = World(1, config=LevelConfig.tutorial(), scripted=True)
    for _ in range(600):
        world.update(1 / 30)
    assert not world.gremlins and not world.surges and world.powerup is None
    assert world.outcome is Outcome.IN_PROGRESS


def test_tutorial_walks_through_every_step(tutorial):
    world = tutorial.world
    assert isinstance(tutorial.step, SwatStep)
    gremlin = world.gremlins[0]
    world.click((gremlin.x, gremlin.y - 12))
    assert tutorial.hint() == "Nice!"
    finish_step(tutorial)

    assert isinstance(tutorial.step, RescueStep)
    thief = tutorial.world.gremlins[0]
    world.click((thief.x, thief.y - 12))
    disk = world.disks[0]
    target = world.computers[1]
    world.click((disk.x, disk.y))
    world.release((target.x, target.y))
    finish_step(tutorial)

    assert isinstance(tutorial.step, SurgeStep)
    tick(tutorial, 1.0)
    world.click(world.surges[0].pos)
    finish_step(tutorial)

    assert isinstance(tutorial.step, FryStep)
    tick(tutorial, 0.1)
    fried = tutorial.step.computer
    assert fried.is_rebooting and fried.os is None and len(world.disks) == 1
    assert "reboot" in tutorial.hint()
    tick(tutorial, FRY_TIME)
    assert "Drag the disk back" in tutorial.hint()
    disk = world.disks[0]
    world.click((disk.x, disk.y))
    world.release((fried.x, fried.y))
    finish_step(tutorial)

    assert isinstance(tutorial.step, PatchStep)
    world.click((world.powerup.x, world.powerup.y))
    finish_step(tutorial)
    assert tutorial.finished


def test_missed_step_is_retried(tutorial):
    world = tutorial.world
    tick(tutorial, 30)  # let the gremlin finish its install
    assert isinstance(tutorial.step, SwatStep)
    assert not any(c.os == BLOAT for c in world.computers)  # board was reset...
    assert any(g.state is not GremlinState.WALK_OUT for g in world.gremlins)  # ...and a new gremlin sent


def test_leaving_the_tutorial_unsubscribes_it(app, tutorial):
    app.change_scene(None)
    app.bus.emit(Event.GREMLIN_SQUASHED, x=0, y=0, carrier=False, kind=None)
    assert not tutorial.step_done


def test_fry_step_is_retried_if_the_disk_expires(tutorial):
    while not isinstance(tutorial.step, FryStep):
        tutorial._next_step()
    first = tutorial.step.computer
    tick(tutorial, 0.1)
    tutorial.world.disks[0].age = 10_000  # let the ejected disk expire
    tick(tutorial, FRY_TIME + 0.1)
    assert tutorial.step.computer is first and first.is_rebooting  # fried again: the step restarted


def skip_to(scene, step_type):
    while not isinstance(scene.step, step_type):
        scene._next_step()


def test_missing_the_spark_hands_over_to_the_fry_lesson(tutorial):
    skip_to(tutorial, SurgeStep)
    world = tutorial.world
    for _ in range(60 * 30):  # don't zap: wait for the surge to reach its computer
        if isinstance(tutorial.step, FryStep):
            break
        tutorial.update(1 / 60)
    assert isinstance(tutorial.step, FryStep)
    fried = tutorial.step.computer
    assert fried.is_rebooting and fried.os is None
    assert [d.kind for d in world.disks] == [fried.native]  # the ejected disk is still there (no reset)
    tick(tutorial, FRY_TIME)
    disk = world.disks[0]
    world.click((disk.x, disk.y))
    world.release((fried.x, fried.y))
    finish_step(tutorial)
    assert isinstance(tutorial.step, PatchStep)


def test_fry_step_hints_follow_what_happens(tutorial):
    skip_to(tutorial, FryStep)
    hints = [tutorial.hint()]
    tick(tutorial, 0.05)
    hints.append(tutorial.hint())
    tick(tutorial, FRY_TIME)
    hints.append(tutorial.hint())
    assert "about to hit" in hints[0]
    assert "Wait for the reboot" in hints[1]
    assert "Drag the disk back" in hints[2]


def test_tutorial_points_at_the_ejected_disk(tutorial):
    world = tutorial.world
    assert tutorial.step.focus(world) == []  # swat step: nothing to point at
    skip_to(tutorial, FryStep)
    tick(tutorial, 0.05)
    disk = world.disks[0]
    assert tutorial.step.focus(world) == [(disk.x, disk.y)]
