"""Sound effects, synthesised at startup (no audio files needed).

`SoundBank.connect()` subscribes to game events, mapping each to a sound.
"""
from __future__ import annotations

import array
import math
import random

import pygame

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
