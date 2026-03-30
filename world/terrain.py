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

    S = float(abs(_hash_seed(world_seed)) % 9999 + 1)

    # No inner function — compute each coordinate inline to avoid closure issues
    def _r(i, lo, hi):
        return round(lo + _srand(S * 3.7 + i * 1.13) * (hi - lo), 4)

    v = [_r(i, 0.0, 1.0) for i in range(28)]  # precompute all values

    centers = [
        {"x": 0.15 + v[0]  * 0.30, "y": 0.15 + v[1]  * 0.30},
        {"x": 0.50 + v[2]  * 0.30, "y": 0.25 + v[3]  * 0.30},
        {"x": 0.25 + v[4]  * 0.30, "y": 0.55 + v[5]  * 0.27},
        {"x": 0.60 + v[6]  * 0.25, "y": 0.55 + v[7]  * 0.27},
        {"x": 0.70 + v[8]  * 0.22, "y": 0.10 + v[9]  * 0.30},
        {"x": 0.05 + v[10] * 0.20, "y": 0.35 + v[11] * 0.30},
        {"x": 0.82 + v[12] * 0.14, "y": 0.38 + v[13] * 0.24},
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
