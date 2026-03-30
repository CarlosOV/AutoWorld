"""
Technology & Discovery System for AutoWorld.
Civilizations discover technologies — from fire to mind-uploading.
"""
import json
import random
from .memory import get_world_state, set_world_state, log_event
from .llm import ask_llm
from .notifier import notify

# Ordered tech tiers — from ancient to beyond-human
TECH_TIERS = {
    0: ["Fire", "Stone Tools", "Language", "Shelter"],
    1: ["Agriculture", "Pottery", "Domestication", "Fishing Nets"],
    2: ["Writing", "Bronze Casting", "Wheel", "Sailing"],
    3: ["Iron Smelting", "Mathematics", "Philosophy", "Aqueducts"],
    4: ["Gunpowder", "Printing Press", "Compass", "Astronomy"],
    5: ["Steam Engine", "Electricity", "Germ Theory", "Railroads"],
    6: ["Nuclear Energy", "Computers", "Space Travel", "Internet"],
    7: ["Artificial Intelligence", "Genetic Engineering", "Quantum Computing", "Brain-Computer Interface"],
    8: ["AGI", "Nanotechnology", "Mind Uploading", "Zero-Point Energy"],
    9: ["Dyson Sphere", "Time Manipulation", "Consciousness Transfer", "Universe Simulation"],
    10: ["Reality Editing", "Dimensional Travel", "Entropy Reversal", "Post-Mortal Existence"],
}

def _get_discovered() -> dict:
    """Returns {civ_name: [tech1, tech2, ...]}"""
    raw = get_world_state("discoveries", "{}")
    return json.loads(raw)

def _save_discovered(data: dict):
    set_world_state("discoveries", json.dumps(data))

def get_all_discoveries() -> dict:
    return _get_discovered()

def _get_civ_tier(civ_name: str, discovered: dict) -> int:
    techs = discovered.get(civ_name, [])
    if not techs:
        return 0
    # Find max tier unlocked
    for tier in range(10, -1, -1):
        for t in TECH_TIERS.get(tier, []):
            if t in techs:
                return tier
    return 0

def maybe_discover(civilizations: list, world_name: str, world_year: int):
    """Each civ has a chance to discover the next available technology."""
    if not civilizations:
        return

    discovered = _get_discovered()

    for civ in civilizations:
        civ_name = civ["name"]
        if random.random() > 0.25:  # 25% chance per tick per civ
            continue

        civ_techs = discovered.get(civ_name, [])
        current_tier = _get_civ_tier(civ_name, discovered)

        # Can discover current tier or next tier
        available = []
        for tier in [current_tier, min(current_tier + 1, 10)]:
            for tech in TECH_TIERS.get(tier, []):
                if tech not in civ_techs:
                    available.append((tier, tech))

        if not available:
            continue

        # Weight towards lower tiers
        tier_num, tech_name = random.choice(available)

        # Generate discovery narrative
        prompt = f"""
The civilization "{civ_name}" in the world "{world_name}" (Year {world_year}) just discovered: "{tech_name}".

Write 2 dramatic sentences about this discovery and how it will change their civilization.
Be creative, vivid, in the style of a world chronicle. No JSON.
"""
        narrative = ask_llm(prompt, max_tokens=150)

        # Save
        if civ_name not in discovered:
            discovered[civ_name] = []
        discovered[civ_name].append(tech_name)
        _save_discovered(discovered)

        # Update civ power
        civ["power"] = civ.get("power", 10) + (tier_num + 1) * 3

        is_major = tier_num >= 6
        log_event(
            "discovery",
            f"🔬 [{civ_name}] Discovered: {tech_name}! {narrative}",
            civ.get("members", [])
        )

        if is_major:
            notify(f"🔬 *{world_name}* — Major Discovery!\n*{civ_name}* unlocks: *{tech_name}*\n\n{narrative}")
            print(f"[tech] 🔬 MAJOR: {civ_name} → {tech_name}")
        else:
            print(f"[tech] {civ_name} → {tech_name} (tier {tier_num})")

def get_civ_tech_summary(civ_name: str) -> dict:
    discovered = _get_discovered()
    techs = discovered.get(civ_name, [])
    tier = _get_civ_tier(civ_name, discovered)
    return {
        "civ": civ_name,
        "tier": tier,
        "tier_name": _tier_name(tier),
        "count": len(techs),
        "discoveries": techs,
    }

def _tier_name(tier: int) -> str:
    names = {
        0: "Primitive", 1: "Ancient", 2: "Classical", 3: "Medieval",
        4: "Renaissance", 5: "Industrial", 6: "Modern", 7: "Futuristic",
        8: "Post-Human", 9: "Cosmic", 10: "Transcendent"
    }
    return names.get(tier, "Unknown")
