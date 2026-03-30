"""
Drama System — gossip, relationships, secondary stories, character movement.
This is what makes the world feel alive.
"""
import os
import random
import json
from .llm import ask_llm
from .memory import get_all_agents, save_agent, log_event, get_world_state
from .notifier import notify

WORLD_NAME = os.getenv("WORLD_NAME", "Aethoria")

RELATIONSHIP_TYPES = ["friend", "enemy", "rival", "lover", "mentor", "student", "suspicious_of", "admires"]

def _rand_pos(seed: int, bounds: tuple = (0.05, 0.95)) -> float:
    """Deterministic-ish position from seed."""
    import hashlib
    h = int(hashlib.md5(str(seed).encode()).hexdigest(), 16)
    lo, hi = bounds
    return lo + (h % 10000) / 10000 * (hi - lo)

def ensure_positions(agents: list) -> list:
    """Give every agent an (x, y) position if they don't have one yet."""
    changed = False
    for i, a in enumerate(agents):
        if "x" not in a or "y" not in a:
            a["x"] = round(_rand_pos(hash(a["name"]) + i), 3)
            a["y"] = round(_rand_pos(hash(a["name"]) * 3 + i), 3)
            changed = True
    return agents, changed

def move_agents(agents: list) -> list:
    """Slightly move agents each tick — they wander the world."""
    for a in agents:
        # Move toward civ capital area or random drift
        dx = random.uniform(-0.04, 0.04)
        dy = random.uniform(-0.04, 0.04)
        a["x"] = round(max(0.03, min(0.97, a.get("x", 0.5) + dx)), 3)
        a["y"] = round(max(0.03, min(0.97, a.get("y", 0.5) + dy)), 3)
    return agents

def maybe_gossip(agents: list, world_year: int) -> bool:
    """Generate a juicy gossip/rumor between two agents. Returns True if generated."""
    if len(agents) < 2 or random.random() > 0.35:
        return False

    a, b = random.sample(agents, 2)
    gossip_types = [
        f"{a['name']} was seen sneaking into {b['name']}'s home at midnight",
        f"Rumor has it {a['name']} and {b['name']} had a fierce argument",
        f"Whispers say {a['name']} is secretly in love with {b['name']}",
        f"{a['name']} allegedly stole something precious from {b['name']}",
        f"People say {b['name']} is jealous of {a['name']}'s recent success",
        f"{a['name']} and {b['name']} were caught making a secret pact",
    ]
    seed_gossip = random.choice(gossip_types)

    prompt = f"""
In the world of {WORLD_NAME}, Year {world_year}:
{a['name']} is a {a.get('occupation','?')} with personality: {', '.join(a.get('personality',[]))}
{b['name']} is a {b.get('occupation','?')} with personality: {', '.join(b.get('personality',[]))}

Rumor seed: "{seed_gossip}"

Write a juicy 2-sentence gossip/rumor about these two that spreads through the town.
Make it dramatic, specific, and entertaining. No JSON.
"""
    gossip = ask_llm(prompt, max_tokens=120)
    log_event("gossip", f"🗣️ {gossip}", [a["name"], b["name"]])

    # Update relationship
    rel_type = random.choice(["suspicious_of", "rival", "admires", "friend", "lover"])
    _update_relationship(a, b["name"], rel_type)
    _update_relationship(b, a["name"], rel_type)
    save_agent(a["name"], a)
    save_agent(b["name"], b)
    return True

def maybe_secondary_story(agents: list, world_year: int) -> bool:
    """Generate a personal subplot for one agent. Returns True if generated."""
    if not agents or random.random() > 0.25:
        return False

    agent = random.choice(agents)
    story_seeds = [
        f"{agent['name']} discovered a hidden secret about their past",
        f"{agent['name']} is on a personal quest no one knows about",
        f"{agent['name']} received a mysterious letter",
        f"{agent['name']} is struggling with an internal conflict",
        f"{agent['name']} found something ancient and valuable",
        f"{agent['name']} has been having strange dreams",
    ]
    seed = random.choice(story_seeds)
    goals = ', '.join(agent.get('goals', []))

    prompt = f"""
Personal subplot for {agent['name']} in {WORLD_NAME}, Year {world_year}.
Occupation: {agent.get('occupation','?')} | Goals: {goals}
Story seed: "{seed}"

Write 2 sentences expanding this personal story. Be specific and intriguing. No JSON.
"""
    story = ask_llm(prompt, max_tokens=120)
    log_event("personal_story", f"📖 [{agent['name']}] {story}", [agent["name"]])

    # Add to agent memories
    agent["memories"] = agent.get("memories", []) + [f"Year {world_year} personal: {story[:80]}"]
    save_agent(agent["name"], agent)
    return True

def _update_relationship(agent: dict, other_name: str, rel_type: str):
    rels = agent.get("relationships", {})
    rels[other_name] = rel_type
    agent["relationships"] = rels
