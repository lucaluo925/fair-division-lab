"""
Behavior state machine.

Manages the pet's state (idle, walk, sleep, react, jump, pet) and
its (x, y) position in *screen* coordinates, where y is the bottom
of the cat (feet level).
"""
import math
import random
import time
from datetime import datetime


class BehaviorEngine:
    STATES = ("idle", "walk", "sleep", "react", "jump", "pet")

    def __init__(self, screen_w: int, screen_h: int, cfg: dict):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self._speed = cfg.get("walk_speed", 2)
        self._idle_timeout  = cfg.get("idle_timeout", 20)
        self._sleep_timeout = cfg.get("sleep_timeout", 120)

        # Logical position (center-x, feet-y) in screen pixels
        self.x: float = screen_w // 2
        self.y: float = screen_h - 80   # stay above dock/taskbar

        # Animation
        self.frame:  int = 0
        self.facing: str = "right"

        # State
        self.state: str = "idle"
        self._state_ts = time.monotonic()   # when current state started
        self._last_act  = time.monotonic()  # last user interaction

        # Mood
        self.mood: str = "happy"

        # Walk target
        self._target_x: float = self.x
        self._target_y: float = self.y

        # Jump physics
        self._jump_base_y: float = self.y
        self._jump_vy: float = 0.0

        # Drag
        self.dragging: bool = False
        self._drag_ox: float = 0.0
        self._drag_oy: float = 0.0

        # Speech bubble (text, expiry monotonic time)
        self.speech: str = ""
        self._speech_until: float = 0.0

    # ── Main update (called every frame) ─────────────────────────────────────

    def update(self) -> None:
        self.frame += 1
        now = time.monotonic()

        # Expire speech bubble
        if self.speech and now >= self._speech_until:
            self.speech = ""

        # Update mood
        self._refresh_mood(now)

        if self.dragging:
            return  # position driven by mouse events

        elapsed = now - self._state_ts

        if self.state == "idle":
            self._update_idle(elapsed)
        elif self.state == "walk":
            self._update_walk()
        elif self.state == "sleep":
            self._update_sleep(elapsed, now)
        elif self.state == "react":
            if elapsed > 1.4:
                self._set_state("idle")
        elif self.state == "pet":
            if elapsed > 2.0:
                self._set_state("idle")
        elif self.state == "jump":
            self._update_jump()

    # ── State handlers ────────────────────────────────────────────────────────

    def _update_idle(self, elapsed: float) -> None:
        # Fall asleep after prolonged inactivity
        if elapsed > self._sleep_timeout and self._is_night():
            self._set_state("sleep")
            return

        # Occasionally wander
        if elapsed > self._idle_timeout + random.uniform(0, 15):
            self._begin_walk()
            return

        # Rare spontaneous jump
        if elapsed > 8 and random.random() < 0.001:
            self._begin_jump()

    def _update_walk(self) -> None:
        dx = self._target_x - self.x
        dy = self._target_y - self.y
        dist = math.hypot(dx, dy)
        if dist < self._speed:
            self.x, self.y = self._target_x, self._target_y
            self._set_state("idle")
            return
        step = self._speed / dist
        self.x += dx * step
        self.y += dy * step
        self.facing = "right" if dx > 0 else "left"

    def _update_sleep(self, elapsed: float, now: float) -> None:
        # Wake up on its own after a while
        if elapsed > 40 and random.random() < 0.005:
            self.mood = "happy"
            self._set_state("idle")

    def _update_jump(self) -> None:
        gravity = 0.55
        self._jump_vy += gravity
        self.y += self._jump_vy
        if self.y >= self._jump_base_y:
            self.y = self._jump_base_y
            self._set_state("idle")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _set_state(self, state: str) -> None:
        self.state = state
        self._state_ts = time.monotonic()

    def _begin_walk(self) -> None:
        margin = 90
        self._target_x = random.uniform(margin, self.screen_w - margin)
        # Mostly stay near the floor, occasionally a bit higher
        floor = self.screen_h - 80
        if random.random() < 0.25:
            self._target_y = random.uniform(floor - 120, floor)
        else:
            self._target_y = floor
        self._set_state("walk")

    def _begin_jump(self) -> None:
        self._jump_base_y = self.y
        self._jump_vy = -13.0
        self._set_state("jump")

    def _refresh_mood(self, now: float) -> None:
        idle_secs = now - self._last_act
        if idle_secs > 300:
            self.mood = "bored"
        elif idle_secs > 120 and self._is_night():
            self.mood = "sleepy"
        elif idle_secs < 30:
            self.mood = "happy"

    @staticmethod
    def _is_night() -> bool:
        h = datetime.now().hour
        return h >= 22 or h < 6

    # ── Event callbacks ───────────────────────────────────────────────────────

    def on_click(self) -> None:
        self._last_act = time.monotonic()
        self.mood = "happy"
        self._set_state("react")

    def on_pet(self) -> None:
        self._last_act = time.monotonic()
        self.mood = "happy"
        self._set_state("pet")

    def on_wake(self) -> None:
        if self.state == "sleep":
            self.mood = "excited" if random.random() > 0.5 else "happy"
            self._set_state("react")

    def on_drag_start(self, mx: float, my: float) -> None:
        self.dragging = True
        self._drag_ox = mx - self.x
        self._drag_oy = my - self.y
        self._last_act = time.monotonic()

    def on_drag_move(self, mx: float, my: float) -> None:
        if self.dragging:
            self.x = mx - self._drag_ox
            self.y = my - self._drag_oy

    def on_drag_end(self) -> None:
        self.dragging = False
        self._set_state("react")

    def say(self, text: str, duration: float = 3.5) -> None:
        """Display a speech bubble for `duration` seconds."""
        self.speech = text
        self._speech_until = time.monotonic() + duration
