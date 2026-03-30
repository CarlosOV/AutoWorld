"""
Terrain — server-side continent center generation.
Uses the same seeded RNG as the frontend JS to produce matching continent positions.
These centers are stored in the DB so agents always stay on land.
"""
import math, os
from .memory import get_world_state, set_world_state
import json

def _srand(s: float) -> float:
    """Mirror of JS srand(s) — deterministic float 0..1."""
    x = math.sin(s + 1) * 43758.5453123
    return x - math.floor(x)

def get_continent_centers(world_seed: str) -> list[dict]:
    """
    Return normalized (0..1) continent centers matching the JS terrain generator.
    Results are cached in world_state so they never change for a given world.
    """
    cached = get_world_state("continent_centers", "")
    if cached:
        return json.loads(cached)

    S = abs(_hash_seed(world_seed)) % 9999 + 1
    rng_i = [0]

    def rng():
        val = _srand(S * 1.7 + rng_i[0] * 0.31 + rng_i[0] * rng_i[0] * 0.007)
        rng_i[0] += 1
        return val

    centers = [
        {"x": .22 + rng() * .18, "y": .25 + rng() * .20},  # continent 1
        {"x": .58 + rng() * .18, "y": .38 + rng() * .20},  # continent 2
        {"x": .35 + rng() * .12, "y": .65 + rng() * .15},  # continent 3
        {"x": .72 + rng() * .10, "y": .65 + rng() * .12},  # continent 4
        {"x": .80 + rng() * .08, "y": .20 + rng() * .12},  # continent 5
        {"x": .12 + rng() * .08, "y": .45 + rng() * .08},  # continent 6
        {"x": .88 + rng() * .05, "y": .48 + rng() * .08},  # continent 7
    ]
    centers = [{"x": round(c["x"], 4), "y": round(c["y"], 4)} for c in centers]
    set_world_state("continent_centers", json.dumps(centers))
    return centers

def _hash_seed(s: str) -> int:
    """Mirror of JS hashCode(s)."""
    h = 0
    for ch in s:
        h = (31 * h + ord(ch)) & 0xFFFFFFFF
    return h if h < 0x80000000 else h - 0x100000000

def nearest_land_position(cx: float, cy: float, centers: list[dict],
                          spread: float = 0.08, agent_index: int = 0) -> tuple[float, float]:
    """
    Return a position near the given continent center (on land).
    Spread controls how far from center agents can wander.
    """
    import random
    rng = random.Random(agent_index * 9999 + int(cx * 1000) + int(cy * 1000))
    angle = rng.uniform(0, 2 * math.pi)
    dist = rng.uniform(0, spread)
    x = round(max(0.03, min(0.97, cx + math.cos(angle) * dist)), 3)
    y = round(max(0.03, min(0.97, cy + math.sin(angle) * dist * 0.7)), 3)
    return x, y

def assign_agent_to_continent(agent: dict, civ_index: int, centers: list[dict],
                               agent_index: int = 0) -> dict:
    """Place an agent on the correct continent based on their civ."""
    center = centers[civ_index % len(centers)]
    x, y = nearest_land_position(center["x"], center["y"], centers,
                                  spread=0.07, agent_index=agent_index)
    agent["x"] = x
    agent["y"] = y
    return agent
