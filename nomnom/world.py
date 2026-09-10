from __future__ import annotations

import random

DIRS = {"n": (0, -1), "s": (0, 1), "e": (1, 0), "w": (-1, 0), "stay": (0, 0)}
ACTIONS = tuple(DIRS.keys())


def stage_for(age: int) -> str:
    if age < 15:
        return "hatchling"
    if age < 35:
        return "juvenile"
    return "adult"


class World:
    """A small grid with food, one slow predator, and a creature that gets hungry."""

    def __init__(
        self,
        seed: int,
        size: int = 10,
        start_energy: int = 20,
        max_energy: int = 30,
        food_value: int = 8,
        initial_food: int = 4,
        food_every: int = 2,
        predator: bool = True,
        predator_every: int = 2,
        drift_every: int = 15,
    ):
        self.rng = random.Random(seed)
        self.size = size
        self.max_energy = max_energy
        self.food_value = food_value
        self.food_every = food_every
        self.predator_every = predator_every

        self.tick_no = 0
        self.creature = (size // 2, size // 2)
        self.energy = start_energy
        self.alive = True
        self.cause_of_death = None
        self.eaten = 0
        self.food: set = set()
        self.predators = [(0, 0)] if predator else []
        self.predator_mode = "hunt"
        self.drift_every = drift_every
        self.drifts = []
        self._drift_pool = ["fast_predator", "scarce_food", "second_predator", "camping_predator"]
        if drift_every:
            self.rng.shuffle(self._drift_pool)
        else:
            self._drift_pool = []

        for _ in range(initial_food):
            self._spawn_food()

    # ---- helpers -------------------------------------------------------

    @property
    def predator(self):
        """Nearest predator, or None. Kept so reflexes written before drift keep working."""
        if not self.predators:
            return None
        cx, cy = self.creature
        return min(self.predators, key=lambda p: abs(p[0] - cx) + abs(p[1] - cy))

    def _empty_cells(self):
        occupied = set(self.food) | {self.creature} | set(self.predators)
        return [
            (x, y)
            for x in range(self.size)
            for y in range(self.size)
            if (x, y) not in occupied
        ]

    def _spawn_food(self) -> bool:
        cells = self._empty_cells()
        if not cells:
            return False
        self.food.add(self.rng.choice(cells))
        return True

    def _rel(self, cell):
        return [cell[0] - self.creature[0], cell[1] - self.creature[1]]

    # ---- public --------------------------------------------------------

    def observe(self) -> dict:
        cx, cy = self.creature
        dist = lambda d: abs(d[0]) + abs(d[1])  # noqa: E731
        food = sorted((self._rel(f) for f in self.food), key=dist)
        preds = sorted((self._rel(p) for p in self.predators), key=dist)
        return {
            "tick": self.tick_no,
            "pos": [cx, cy],
            "grid": self.size,
            "energy": self.energy,
            "stage": stage_for(self.tick_no),
            "food": food,
            "predator": preds[0] if preds else None,
            "predators": preds,
        }

    def _apply_drift(self) -> str:
        if not self._drift_pool:
            return None
        kind = self._drift_pool.pop(0)
        if kind == "fast_predator":
            self.predator_every = 1
            detail = "predators now move every tick"
        elif kind == "scarce_food":
            self.food_every, self.food_value = 4, 5
            detail = "food now spawns every 4 ticks and is worth 5"
        elif kind == "second_predator":
            cx, cy = self.creature
            corners = [(0, 0), (0, self.size - 1), (self.size - 1, 0), (self.size - 1, self.size - 1)]
            far = max(corners, key=lambda c: abs(c[0] - cx) + abs(c[1] - cy))
            self.predators.append(far)
            self.food.discard(far)
            detail = "a second predator appeared at %s" % list(far)
        else:
            self.predator_mode = "camp"
            detail = "predators now camp the nearest food instead of chasing you"
        self.drifts.append({"tick": self.tick_no, "kind": kind, "detail": detail})
        return "DRIFT: " + detail

    def state(self) -> dict:
        """Absolute positions after the last step, for renderers."""
        return {
            "pos": list(self.creature),
            "predator": list(self.predator) if self.predator is not None else None,
            "predators": [list(p) for p in self.predators],
            "predator_mode": self.predator_mode,
            "food": sorted(list(f) for f in self.food),
            "energy": self.energy,
            "alive": self.alive,
        }

    def step(self, action: str) -> list:
        """Advance one tick. Returns a list of human-readable events."""
        if not self.alive:
            return ["dead"]
        events = []
        self.tick_no += 1
        dx, dy = DIRS.get(action, (0, 0))
        nx = min(max(self.creature[0] + dx, 0), self.size - 1)
        ny = min(max(self.creature[1] + dy, 0), self.size - 1)
        if (nx, ny) != self.creature:
            self.creature = (nx, ny)
            events.append("moved " + action)
        elif action != "stay":
            events.append("bumped wall")

        if self.creature in self.food:
            self.food.discard(self.creature)
            self.energy = min(self.energy + self.food_value, self.max_energy)
            self.eaten += 1
            events.append("ate food (+%d)" % self.food_value)

        self.energy -= 1

        if self.predators and self.tick_no % self.predator_every == 0:
            moved = []
            for (px, py) in self.predators:
                target = self.creature
                if self.predator_mode == "camp" and self.food:
                    target = min(self.food, key=lambda f: abs(f[0] - px) + abs(f[1] - py))
                tx, ty = target
                if abs(tx - px) >= abs(ty - py):
                    px += (tx > px) - (tx < px)
                else:
                    py += (ty > py) - (ty < py)
                moved.append((px, py))
            self.predators = moved
            events.append("predator moved" if len(moved) == 1 else "predators moved")

        if self.creature in self.predators:
            self.alive = False
            self.cause_of_death = "eaten by predator"
            events.append("EATEN BY PREDATOR")
            return events

        if self.tick_no % self.food_every == 0 and self._spawn_food():
            events.append("food spawned")

        if self.energy <= 0:
            self.energy = 0
            self.alive = False
            self.cause_of_death = "starved"
            events.append("STARVED")
            return events

        if self.drift_every and self.tick_no % self.drift_every == 0:
            d = self._apply_drift()
            if d:
                events.append(d)
        return events

    def render(self) -> str:
        rows = []
        for y in range(self.size):
            row = []
            for x in range(self.size):
                c = (x, y)
                if c == self.creature:
                    row.append("@")
                elif c in self.predators:
                    row.append("P")
                elif c in self.food:
                    row.append("*")
                else:
                    row.append(".")
            rows.append(" ".join(row))
        return "\n".join(rows)
