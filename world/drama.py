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
from .terrain import get_continent_centers, nearest_land_position

WORLD_NAME = os.getenv("WORLD_NAME", "Aethoria")

RELATIONSHIP_TYPES = ["friend", "enemy", "rival", "lover", "mentor", "student", "suspicious_of", "admires"]

def _rand_pos(seed: int, bounds: tuple = (0.05, 0.95)) -> float:
    """Deterministic-ish position from seed."""
    import hashlib
    h = int(hashlib.md5(str(seed).encode()).hexdigest(), 16)
    lo, hi = bounds
    return lo + (h % 10000) / 10000 * (hi - lo)

def ensure_positions(agents: list, civilizations: list = None) -> tuple:
    """Give every agent an (x, y) position on their civilization's continent."""
    world_seed = get_world_state("world_seed", "default")
    centers = get_continent_centers(world_seed)
    civs = civilizations or []
    changed = False

    for i, a in enumerate(agents):
        if "x" not in a or "y" not in a:
            civ_index = next((j for j, c in enumerate(civs) if c.get("name") == a.get("civ")), i % len(centers))
            center = centers[civ_index % len(centers)]
            x, y = nearest_land_position(center["x"], center["y"], centers,
                                          spread=0.07, agent_index=i)
            a["x"] = x
            a["y"] = y
            changed = True
    return agents, changed

def move_agents(agents: list, civilizations: list = None) -> list:
    """Move agents each tick — they wander near their civilization's continent."""
    world_seed = get_world_state("world_seed", "default")
    centers = get_continent_centers(world_seed)
    civs = civilizations or []

    for i, a in enumerate(agents):
        civ_index = next((j for j, c in enumerate(civs) if c.get("name") == a.get("civ")), i % len(centers))
        center = centers[civ_index % len(centers)]

        # Small drift around current position, clamped to continent area
        dx = random.uniform(-0.025, 0.025)
        dy = random.uniform(-0.020, 0.020)
        new_x = a.get("x", center["x"]) + dx
        new_y = a.get("y", center["y"]) + dy

        # Pull back toward continent center if drifting too far (land boundary)
        spread = 0.12
        dist_x = new_x - center["x"]
        dist_y = new_y - center["y"]
        dist = (dist_x**2 + (dist_y/0.7)**2) ** 0.5
        if dist > spread:
            pull = 0.3
            new_x = new_x - dist_x * pull
            new_y = new_y - dist_y * pull

        a["x"] = round(max(0.03, min(0.97, new_x)), 3)
        a["y"] = round(max(0.03, min(0.97, new_y)), 3)
    return agents

DRAMA_EVENTS = [
    # Traición y poder
    ("betrayal",    "💔", "{a} betrayed {b}'s trust — revealing a secret that could destroy them"),
    ("powerplay",   "👑", "{a} made a bold move to seize {b}'s position of influence"),
    ("conspiracy",  "🕵️", "{a} and {b} were caught conspiring against a common enemy"),
    # Romance y envidia
    ("romance",     "❤️",  "{a} and {b} share a forbidden attraction neither will admit"),
    ("jealousy",    "😡", "{b} is consumed by jealousy over {a}'s sudden rise to fame"),
    ("rivalry",     "⚔️", "The rivalry between {a} and {b} has reached a boiling point"),
    # Secretos y misterio
    ("secret",      "🤫", "{a} is hiding something from everyone — even {b} who suspects the truth"),
    ("blackmail",   "📜", "Someone is blackmailing {a} using {b}'s name as leverage"),
    ("revelation",  "😱", "A shocking truth about {a}'s past was uncovered, implicating {b}"),
    # Humor y vida cotidiana
    ("scandal",     "🗞️",  "A public scandal erupts: {a} was caught doing something {b} swore they'd never do"),
    ("debt",        "💰", "{a} owes {b} a debt they can't repay — and the deadline is approaching"),
    ("duel",        "🗡️",  "{a} challenged {b} to a public duel after an unforgivable insult"),
]

def maybe_gossip(agents: list, world_year: int) -> bool:
    """Generate a juicy dramatic event between two agents."""
    if len(agents) < 2 or random.random() > 0.40:
        return False

    a, b = random.sample(agents, 2)
    etype, emoji, seed_template = random.choice(DRAMA_EVENTS)
    seed_gossip = seed_template.format(a=a['name'], b=b['name'])

    existing_rel = a.get("relationships", {}).get(b["name"], "strangers")

    prompt = f"""World: {WORLD_NAME}, Year {world_year}.
{a['name']}: {a.get('occupation','?')}, personality: {', '.join(a.get('personality',[])[:3])}
{b['name']}: {b.get('occupation','?')}, personality: {', '.join(b.get('personality',[])[:3])}
Their relationship: {existing_rel}

Dramatic event: "{seed_gossip}"

Write 2-3 gripping sentences about this event as if a town crier is announcing it.
Be SPECIFIC — use names, places, objects. Make it feel real and consequential.
End with a hint of what might happen next. No JSON, no meta-commentary."""

    gossip = ask_llm(prompt, max_tokens=150)
    if not gossip:
        return False
    log_event("gossip", f"{emoji} {gossip}", [a["name"], b["name"]])

    # Relationship consequences
    rel_map = {
        "betrayal": ("enemy", "distrusts"), "powerplay": ("rival", "rivals"),
        "conspiracy": ("ally", "ally"), "romance": ("lover", "lover"),
        "jealousy": ("enemy", "jealous_of"), "rivalry": ("rival", "rival"),
        "secret": ("suspicious_of", "suspicious_of"), "blackmail": ("enemy", "fears"),
        "revelation": ("distrusts", "distrusts"), "scandal": ("rival", "rival"),
        "debt": ("owes", "owed_by"), "duel": ("enemy", "enemy"),
    }
    rel_a, rel_b = rel_map.get(etype, ("rival", "rival"))
    _update_relationship(a, b["name"], rel_a)
    _update_relationship(b, a["name"], rel_b)
    save_agent(a["name"], a)
    save_agent(b["name"], b)

    # Notify Telegram for spicy events
    if etype in ("betrayal", "duel", "revelation", "blackmail"):
        notify(f"🎭 *Drama en {WORLD_NAME}*\n{gossip}")
    return True

PERSONAL_ARCS = [
    ("quest",      "🗺️",  "{name} has secretly embarked on a quest no one else knows about"),
    ("obsession",  "🔮", "{name} has become dangerously obsessed with something forbidden"),
    ("loss",       "💀", "{name} is grieving a loss they refuse to show in public"),
    ("ambition",   "🏹", "{name}'s ambition is growing — they want something they shouldn't"),
    ("discovery",  "✨", "{name} discovered something ancient that changes everything they believed"),
    ("addiction",  "🌙", "{name} has developed a secret habit that's slowly consuming them"),
    ("vision",     "👁️",  "{name} has been having visions — or are they warnings?"),
    ("revenge",    "🔥", "{name} is quietly planning revenge against someone who wronged them"),
]

def maybe_secondary_story(agents: list, world_year: int) -> bool:
    """Generate a personal subplot for one agent."""
    if not agents or random.random() > 0.30:
        return False

    agent = random.choice(agents)
    etype, emoji, seed_template = random.choice(PERSONAL_ARCS)
    seed = seed_template.format(name=agent['name'])
    goals = ', '.join(agent.get('goals', [])[:2])
    memories_hint = agent.get('memories', ['nothing notable'])[-1] if agent.get('memories') else 'nothing notable'

    prompt = f"""World: {WORLD_NAME}, Year {world_year}.
Character: {agent['name']}, {agent.get('occupation','?')}
Personality: {', '.join(agent.get('personality',[])[:3])}
Goals: {goals}
Recent memory: {memories_hint}

Personal arc: "{seed}"

Write 2-3 vivid sentences about this character's inner struggle or secret journey.
Be SPECIFIC and emotionally resonant. Hint at consequences. No JSON."""

    story = ask_llm(prompt, max_tokens=150)
    if not story:
        return False
    log_event("personal_story", f"{emoji} [{agent['name']}] {story}", [agent["name"]])

    agent["memories"] = agent.get("memories", []) + [f"Año {world_year}: {story[:100]}"]
    save_agent(agent["name"], agent)

    if etype in ("obsession", "revenge", "vision"):
        notify(f"📖 *Historia personal — {agent['name']}*\n{story}")
    return True

def _update_relationship(agent: dict, other_name: str, rel_type: str):
    rels = agent.get("relationships", {})
    rels[other_name] = rel_type
    agent["relationships"] = rels
