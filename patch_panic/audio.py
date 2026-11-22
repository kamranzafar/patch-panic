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

"""Sound effects, synthesised at startup (no audio files needed).

`SoundBank.connect()` subscribes to game events, mapping each to a sound.
"""
from __future__ import annotations

import array
import math
import random

import pygame

from .config import COMBO_MAX
from .events import Event, EventBus

# name -> (segments, volume). A segment is (start_hz, end_hz, seconds[, noise]).
SOUND_DEFS = {
    "squash": ([(520, 110, 0.12)], 0.3),
    "restore": ([(440, 660, 0.08), (660, 990, 0.1)], 0.3),
    "infect": ([(180, 90, 0.35)], 0.25),
    "pickup": ([(600, 800, 0.05)], 0.2),
    "drop": ([(500, 350, 0.06)], 0.2),
    "nope": ([(200, 200, 0.08), (150, 150, 0.1)], 0.25),
    "level": ([(523, 523, 0.1), (659, 659, 0.1), (784, 784, 0.1), (1046, 1046, 0.2)], 0.3),
    "gameover": ([(400, 300, 0.2), (300, 200, 0.2), (200, 80, 0.4)], 0.3),
    "powerup": ([(660, 660, 0.06), (880, 880, 0.06), (1100, 1100, 0.06), (1320, 1760, 0.15)], 0.25),
    "zap": ([(1200, 2600, 0.09)], 0.2),
    "fry": ([(4000, 600, 0.35, True)], 0.3),
    "warn": ([(300, 340, 0.07), (300, 340, 0.07)], 0.12),
    "clank": ([(1500, 1400, 0.03, True), (900, 700, 0.06)], 0.22),
    "split": ([(300, 600, 0.05), (300, 600, 0.05)], 0.2),
    "threat": ([(220, 220, 0.12), (165, 165, 0.12), (220, 220, 0.12), (165, 165, 0.2)], 0.22),
    "perfect": ([(784, 784, 0.08), (988, 988, 0.08), (1175, 1175, 0.08), (1568, 1568, 0.25)], 0.3),
    # combo2..comboN: a blip that climbs a semitone-ish step with each link
    **{f"combo{n}": ([(700 * 1.12 ** n, 900 * 1.12 ** n, 0.06)], 0.18) for n in range(2, COMBO_MAX + 1)},
}

SOUND_FOR_EVENT = {
    Event.GREMLIN_SQUASHED: "squash",
    Event.OS_RESTORED: "restore",
    Event.COMPUTER_INFECTED: "infect",
    Event.DISK_PICKED_UP: "pickup",
    Event.DISK_DROPPED: "drop",
    Event.DISK_REJECTED: "nope",
    Event.LEVEL_CLEARED: "level",
    Event.GAME_OVER: "gameover",
    Event.POWERUP_COLLECTED: "powerup",
    Event.SURGE_ZAPPED: "zap",
    Event.COMPUTER_FRIED: "fry",
    Event.SURGE_WARNING: "warn",
    Event.PERFECT_LEVEL: "perfect",
    Event.GREMLIN_HIT: "clank",
    Event.GREMLIN_SPLIT: "split",
    Event.NEW_THREAT: "threat",
    Event.CABLE_SABOTAGED: "zap",
    Event.ACHIEVEMENT_UNLOCKED: "powerup",
}

MIXER_SETTINGS = dict(frequency=22050, size=-16, channels=1, buffer=512)


def synthesize(segments, volume: float, rate: int, channels: int) -> bytes:
    """Render square-wave sweeps (or held-noise crackle) to 16-bit PCM."""
    buf = array.array("h")
    phase = 0.0
    noise = 1
    for f0, f1, duration, *is_noise in segments:
        n = int(rate * duration)
        for i in range(n):
            freq = f0 + (f1 - f0) * i / n
            envelope = min(1.0, i / 80) * (1 - i / n)
            if is_noise:
                if i % max(1, int(rate / freq)) == 0:
                    noise = random.choice((-1, 1))
                wave = noise
            else:
                phase += math.tau * freq / rate
                wave = 1 if math.sin(phase) > 0 else -1
            buf.extend([int(wave * envelope * volume * 32767)] * channels)
    return buf.tobytes()


class SoundBank:
    def __init__(self) -> None:
        self.muted = False
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        init = pygame.mixer.get_init()
        if not init or init[1] != -16:  # no audio device, or an unexpected format
            return
        rate, _, channels = init
        try:
            self._sounds = {name: pygame.mixer.Sound(buffer=synthesize(segs, vol, rate, channels))
                            for name, (segs, vol) in SOUND_DEFS.items()}
        except pygame.error:
            self._sounds = {}

    def play(self, name: str) -> None:
        if not self.muted and name in self._sounds:
            self._sounds[name].play()

    def toggle_mute(self) -> None:
        self.muted = not self.muted

    def connect(self, bus: EventBus) -> None:
        for event, name in SOUND_FOR_EVENT.items():
            bus.subscribe(event, lambda _name=name, **_: self.play(_name))
        bus.subscribe(Event.COMBO, lambda count, **_: self.play(f"combo{count}"))
