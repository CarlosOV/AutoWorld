"""
Economy System — resources, trade, and economic evolution per civilization.

Economic models evolve with tech tier:
  Tier 0-1: Subsistence (barter, survival)
  Tier 2-3: Agrarian (surplus, feudal taxes)
  Tier 4-5: Mercantile (currency, trade routes)
  Tier 6-7: Industrial (manufacturing, markets)
  Tier 8-9: Digital (information economy, automation)
  Tier 10:  Abundance (post-scarcity, energy-based)
"""
import os, json, random
from .llm import ask_llm
from .memory import get_world_state, set_world_state, log_event
from .notifier import notify

WORLD_NAME = os.getenv("WORLD_NAME", "World")

# Resources tracked per civilization
RESOURCES = ["food", "materials", "wealth", "knowledge", "influence"]

# Economic model by tech tier
ECONOMIC_MODELS = {
    0: "subsistence barter",
    1: "tribal gift economy",
    2: "agrarian surplus",
    3: "feudal taxation",
    4: "merchant currency",
    5: "early capitalism",
    6: "industrial markets",
    7: "regulated economy",
    8: "information economy",
    9: "automated abundance",
    10: "post-scarcity",
}

# Base production rates by occupation (resources per tick)
OCCUPATION_PRODUCTION = {
    "farmer":      {"food": 3, "materials": 1},
    "merchant":    {"wealth": 3, "influence": 1},
    "scholar":     {"knowledge": 3, "influence": 1},
    "warrior":     {"influence": 2, "materials": 1},
    "priest":      {"influence": 3, "knowledge": 1},
    "craftsman":   {"materials": 3, "wealth": 1},
    "explorer":    {"knowledge": 2, "influence": 2},
    "ruler":       {"influence": 3, "wealth": 2},
    "healer":      {"knowledge": 2, "food": 1},
    "mage":        {"knowledge": 4},
    "assassin":    {"influence": 2, "wealth": 2},
    "spy":         {"knowledge": 3, "influence": 1},
    "default":     {"food": 1, "materials": 1, "wealth": 1},
}

def _get_economies() -> dict:
    raw = get_world_state("economies", "{}")
    return json.loads(raw) if raw else {}

def _save_economies(eco: dict):
    set_world_state("economies", json.dumps(eco))

def get_civ_economy(civ_name: str) -> dict:
    eco = _get_economies()
    if civ_name not in eco:
        eco[civ_name] = {r: 100 for r in RESOURCES}  # starting resources
        eco[civ_name]["model"] = "subsistence barter"
        eco[civ_name]["gdp"] = 100
        eco[civ_name]["trade_partners"] = []
        _save_economies(eco)
    return eco[civ_name]

def tick_economy(agents: list, civilizations: list, world_year: int):
    """Run one economic tick: production, trade, events, evolution."""
    eco = _get_economies()
    civs_by_name = {c["name"]: c for c in civilizations}

    # ── 1. Production — each agent contributes to their civ ──
    for a in agents:
        civ_name = a.get("civ")
        if not civ_name or civ_name not in civs_by_name:
            continue
        if civ_name not in eco:
            eco[civ_name] = {r: 100 for r in RESOURCES}
            eco[civ_name]["model"] = "subsistence barter"
            eco[civ_name]["gdp"] = 100
            eco[civ_name]["trade_partners"] = []

        occ = a.get("occupation", "default").lower()
        prod = next((v for k, v in OCCUPATION_PRODUCTION.items() if k in occ), OCCUPATION_PRODUCTION["default"])

        # Tech tier multiplier
        tier = _get_civ_tier(civ_name)
        multiplier = 1.0 + tier * 0.15

        for resource, amount in prod.items():
            eco[civ_name][resource] = eco[civ_name].get(resource, 0) + int(amount * multiplier)

        # Personal wealth stored in agent
        a["wealth"] = a.get("wealth", 10) + int(1 * multiplier)

    # ── 2. Upkeep — civilizations spend resources each tick ──
    for civ_name in eco:
        member_count = sum(1 for a in agents if a.get("civ") == civ_name)
        upkeep = max(1, member_count) * 2
        eco[civ_name]["food"] = max(0, eco[civ_name].get("food", 0) - upkeep)
        eco[civ_name]["materials"] = max(0, eco[civ_name].get("materials", 0) - 1)
        # Compute GDP
        eco[civ_name]["gdp"] = sum(eco[civ_name].get(r, 0) for r in RESOURCES)

    # ── 3. Trade between civs (30% chance per tick) ──
    if len(civilizations) >= 2 and random.random() < 0.30:
        _maybe_trade(eco, civilizations, world_year)

    # ── 4. Random economic event (15% chance) ──
    if random.random() < 0.15:
        _random_eco_event(eco, civilizations, agents, world_year)

    # ── 5. Economic model evolution ──
    for civ_name in eco:
        tier = _get_civ_tier(civ_name)
        model = ECONOMIC_MODELS.get(min(tier, 10), "subsistence barter")
        old_model = eco[civ_name].get("model", "")
        if model != old_model:
            eco[civ_name]["model"] = model
            log_event("economy", f"💰 [{civ_name}] Economic model evolved: {old_model} → {model}", [civ_name])
            notify(f"💰 *{civ_name}* transitioned to *{model}* economy")

    _save_economies(eco)
    return eco

def _maybe_trade(eco: dict, civilizations: list, world_year: int):
    """Generate a trade event between two civilizations."""
    names = [c["name"] for c in civilizations if c["name"] in eco]
    if len(names) < 2:
        return
    a, b = random.sample(names, 2)
    # Simple trade: exchange surpluses
    traded = []
    for resource in RESOURCES:
        if eco[a].get(resource, 0) > 150 and eco[b].get(resource, 0) < 80:
            amount = random.randint(10, 30)
            eco[a][resource] -= amount
            eco[b][resource] += amount
            traded.append(f"{amount} {resource}")
        elif eco[b].get(resource, 0) > 150 and eco[a].get(resource, 0) < 80:
            amount = random.randint(10, 30)
            eco[b][resource] -= amount
            eco[a][resource] += amount
            traded.append(f"{amount} {resource} (from {b})")
    if traded:
        # Add as trade partners
        eco[a].setdefault("trade_partners", [])
        eco[b].setdefault("trade_partners", [])
        if b not in eco[a]["trade_partners"]:
            eco[a]["trade_partners"].append(b)
        if a not in eco[b]["trade_partners"]:
            eco[b]["trade_partners"].append(a)
        log_event("economy", f"🤝 Trade: {a} and {b} exchanged {', '.join(traded[:2])}", [a, b])

ECONOMIC_EVENTS = [
    ("famine",     "🌾", "{civ} suffers a famine — food stores halved"),
    ("boom",       "📈", "{civ} experiences an economic boom — wealth surges"),
    ("plague",     "☠️",  "{civ} is struck by plague — production drops"),
    ("gold_rush",  "⛏️",  "{civ} discovers rich deposits — materials double"),
    ("corruption", "💸", "{civ} suffers corruption — wealth lost to thieves"),
    ("festival",   "🎉", "{civ} holds a great festival — influence spreads"),
    ("drought",    "🌵", "{civ} faces drought — food production halves"),
    ("invention",  "💡", "{civ} makes a breakthrough — knowledge surges"),
    ("trade_ban",  "🚫", "{civ} imposes trade restrictions — partners suffer"),
]

def _random_eco_event(eco: dict, civilizations: list, agents: list, world_year: int):
    names = [c["name"] for c in civilizations if c["name"] in eco]
    if not names:
        return
    civ_name = random.choice(names)
    etype, emoji, template = random.choice(ECONOMIC_EVENTS)
    desc = template.format(civ=civ_name)

    effects = {
        "famine":     {"food": 0.5},
        "boom":       {"wealth": 1.5, "influence": 1.2},
        "plague":     {"food": 0.7, "materials": 0.8},
        "gold_rush":  {"materials": 2.0, "wealth": 1.5},
        "corruption": {"wealth": 0.6},
        "festival":   {"influence": 2.0, "knowledge": 1.3},
        "drought":    {"food": 0.5, "materials": 0.8},
        "invention":  {"knowledge": 2.0, "influence": 1.5},
        "trade_ban":  {"wealth": 0.7},
    }
    mults = effects.get(etype, {})
    for res, mult in mults.items():
        eco[civ_name][res] = int(eco[civ_name].get(res, 50) * mult)

    log_event("economy", f"{emoji} {desc}", [civ_name])
    if etype in ("famine", "gold_rush", "plague", "invention"):
        notify(f"{emoji} *Economic event in {civ_name}*: {desc}")

def _get_civ_tier(civ_name: str) -> int:
    """Get tech tier for a civilization."""
    try:
        from .tech_tree import _get_civ_tier as _tt
        return _tt(civ_name)
    except Exception:
        return 0

def get_economy_summary(civilizations: list) -> list:
    """Return economy data for all civs — used by API."""
    eco = _get_economies()
    result = []
    for civ in civilizations:
        name = civ["name"]
        data = eco.get(name, {r: 0 for r in RESOURCES})
        result.append({
            "civ": name,
            "gdp": data.get("gdp", 0),
            "model": data.get("model", "unknown"),
            "resources": {r: data.get(r, 0) for r in RESOURCES},
            "trade_partners": data.get("trade_partners", []),
        })
    return result
