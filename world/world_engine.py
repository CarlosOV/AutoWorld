import random
import json
import os
from .llm import ask_llm
from .memory import get_all_agents, log_event, save_agent, get_recent_events, get_world_state, set_world_state
from .agent import agent_react, generate_agent
from .notifier import notify
from .tech_tree import maybe_discover, get_all_discoveries, get_civ_tech_summary
from .context_manager import get_world_context, get_deep_context, trim_agent_memories, maybe_compress_lore

WORLD_NAME = os.getenv("WORLD_NAME", "Aethoria")
NUM_AGENTS = int(os.getenv("NUM_AGENTS", "5"))

EPIC_KEYWORDS = ["guerra", "war", "muerte", "death", "catástrofe", "revolución",
                 "traición", "milagro", "descubrimiento", "batalla", "battle",
                 "conquista", "extinción", "renaissance", "apocalipsis"]

ERAS = [
    "Primordial Age",
    "Age of Tribes",
    "Age of Cities",
    "Age of Empires",
    "Age of Enlightenment",
    "Age of Machines",
    "Age of Stars",
]

def _get_world_year() -> int:
    return int(get_world_state("world_year_num", "1"))

def _advance_year():
    y = _get_world_year() + 1
    set_world_state("world_year_num", str(y))
    set_world_state("world_year", f"Year {y}")
    # Era progression
    era_idx = min(y // 20, len(ERAS) - 1)
    current_era = get_world_state("era", ERAS[0])
    new_era = ERAS[era_idx]
    if new_era != current_era:
        set_world_state("era", new_era)
        log_event("era_change", f"🌅 A new era dawns: {new_era}!", [])
        notify(f"🌅 *{WORLD_NAME}* enters a new era: *{new_era}*!")
    return y

def _get_civilizations() -> list:
    raw = get_world_state("civilizations", "[]")
    return json.loads(raw)

def _save_civilizations(civs: list):
    set_world_state("civilizations", json.dumps(civs))

def _maybe_form_civilization(agents: list):
    """When enough agents exist, form a civilization."""
    civs = _get_civilizations()
    if len(civs) >= 4:
        return  # max civs

    unaffiliated = [a for a in agents if not a.get("civ")]
    if len(unaffiliated) < 3:
        return

    prompt = f"""
Create a civilization name, capital city, and emoji for the world "{WORLD_NAME}".
These agents are founding it: {", ".join([a["name"] for a in unaffiliated[:3]])}

Respond ONLY with JSON:
{{"name": "Civilization Name", "capital": "City Name", "emoji": "🏰", "description": "1 sentence"}}
"""
    raw = ask_llm(prompt, max_tokens=120)
    start, end = raw.find("{"), raw.rfind("}") + 1
    civ_data = json.loads(raw[start:end])
    civ_data["population"] = len(unaffiliated)
    civ_data["power"] = random.randint(5, 20)
    civ_data["status"] = "growing"
    civ_data["members"] = [a["name"] for a in unaffiliated[:3]]

    civs.append(civ_data)
    _save_civilizations(civs)

    # Assign agents to civ
    for a in unaffiliated[:3]:
        a["civ"] = civ_data["name"]
        save_agent(a["name"], a)

    log_event("civilization_formed", f"🏰 The civilization of {civ_data['name']} rises, with {civ_data['capital']} as its capital!", civ_data["members"])
    notify(f"🏰 *{WORLD_NAME}* — A new civilization rises: *{civ_data['name']}*!")

def _maybe_trigger_war():
    """If 2+ civs exist, maybe start a war."""
    civs = _get_civilizations()
    if len(civs) < 2:
        return None

    at_peace = [c for c in civs if c["status"] == "peace" or c["status"] == "growing"]
    if len(at_peace) < 2 or random.random() > 0.15:  # 15% chance per tick
        return None

    c1, c2 = random.sample(at_peace, 2)
    prompt = f"""
Write 2 sentences about why the civilization "{c1['name']}" declared war on "{c2['name']}" in the world of {WORLD_NAME}.
Be dramatic. No JSON, just the narrative.
"""
    reason = ask_llm(prompt, max_tokens=120)
    c1["status"] = "war"
    c2["status"] = "war"
    _save_civilizations(civs)

    log_event("war", f"⚔️ WAR! {c1['name']} vs {c2['name']}! {reason}", c1["members"] + c2["members"])
    notify(f"⚔️ *{WORLD_NAME}* — WAR DECLARED!\n*{c1['name']}* vs *{c2['name']}*\n\n{reason}")
    return reason

def _maybe_reproduction(agents: list):
    """Occasionally create a new agent (birth)."""
    if len(agents) >= int(os.getenv("MAX_AGENTS", "20")):
        return
    if random.random() > 0.20:  # 20% chance
        return

    parents = random.sample(agents, k=min(2, len(agents)))
    parent_names = [p["name"] for p in parents]
    existing = [a["name"] for a in agents]

    prompt = f"""
Create a new inhabitant for the world "{WORLD_NAME}" who is the child or new arrival influenced by: {", ".join(parent_names)}.
Respond ONLY with valid JSON:
{{"name": "Name", "age": 16, "occupation": "job", "personality": ["trait1","trait2","trait3"], "goals": ["goal1","goal2"], "backstory": "2 sentences", "mood": "curious", "memories": [], "civ": ""}}
"""
    raw = ask_llm(prompt, max_tokens=250)
    start, end = raw.find("{"), raw.rfind("}") + 1
    data = json.loads(raw[start:end])

    # Inherit civ from parents
    parent_civ = next((p.get("civ") for p in parents if p.get("civ")), "")
    data["civ"] = parent_civ

    save_agent(data["name"], data)
    log_event("birth", f"👶 A new soul arrives in {WORLD_NAME}: {data['name']}, future {data['occupation']}.", parent_names)
    print(f"[tick] 👶 New agent born: {data['name']}")

def world_tick():
    print(f"[tick] === World tick for {WORLD_NAME} ===")
    agents = get_all_agents()
    if not agents:
        print("[tick] No agents yet, skipping.")
        return

    year = _advance_year()
    print(f"[tick] World Year: {year}")

    # Try to form civilization
    if year >= 3:
        _maybe_form_civilization(agents)

    # Try war
    if year >= 5:
        _maybe_trigger_war()

    # Try reproduction
    if year >= 2:
        _maybe_reproduction(agents)

    # Refresh agents after possible changes
    agents = get_all_agents()

    # Compress lore if needed (keeps future prompts lean)
    maybe_compress_lore(WORLD_NAME)

    # Build lean world context
    ctx = get_world_context()
    civs = _get_civilizations()
    civs_str = ", ".join([f"{c['name']} ({c['status']})" for c in civs]) if civs else "none"

    event_prompt = f"""
World: {WORLD_NAME} | {ctx['year']} | Era: {ctx['era']}
Civilizations: {civs_str}
{f"World Lore: {ctx['lore']}" if ctx['lore'] else ""}
Recent events:
{ctx['recent']}

Generate ONE interesting event happening right now. 2-3 sentences. No JSON.
"""
    event_desc = ask_llm(event_prompt, max_tokens=200)
    print(f"[tick] Event: {event_desc[:80]}...")

    is_epic = any(kw in event_desc.lower() for kw in EPIC_KEYWORDS)
    involved = [a["name"] for a in random.sample(agents, k=min(2, len(agents)))]
    log_event("world_event", event_desc, involved)

    # Agent reactions (1-2 agents)
    reactors = random.sample(agents, k=min(2, len(agents)))
    for agent in reactors:
        agent = trim_agent_memories(agent)
        reaction = agent_react(agent, event_desc, WORLD_NAME)
        log_event("agent_reaction", f"{agent['name']}: {reaction}", [agent["name"]])
        agent["memories"] = agent.get("memories", []) + [f"Year {year}: {event_desc[:80]}"]
        agent = trim_agent_memories(agent)
        save_agent(agent["name"], agent)

    # Tech discoveries
    civs = _get_civilizations()
    if civs:
        maybe_discover(civs, WORLD_NAME, year)
        _save_civilizations(civs)  # save updated power levels

    if is_epic:
        summary = f"🌍 *{WORLD_NAME}* — Year {year}\n\n{event_desc}"
        notify(summary)
        print("[tick] ⚡ Epic event — notified!")

    print(f"[tick] Done. World year {year}.")

def answer_question(question: str, deep: bool = False) -> str:
    """
    Answer a question about the world.
    deep=True: pulls extended event history from DB for detailed queries.
    deep is auto-detected from question keywords.
    """
    agents = get_all_agents()
    civs = _get_civilizations()

    # Auto-detect if question needs deep history
    deep_keywords = ["history", "historia", "before", "antes", "how did", "cómo fue",
                     "when did", "cuándo", "all", "todo", "war", "guerra", "origin",
                     "origen", "first", "primero", "discovery", "descubrimiento"]
    needs_deep = deep or any(kw in question.lower() for kw in deep_keywords)

    ctx = get_deep_context(extra_events=40) if needs_deep else get_world_context()

    agents_summary = "\n".join([
        f"- {a['name']} ({a.get('occupation','?')}, civ: {a.get('civ','—')})"
        for a in agents[:12]
    ])
    civs_summary = "\n".join([
        f"- {c['name']}: capital {c.get('capital','?')}, status: {c.get('status','?')}, tech: {c.get('tech_tier_name','?')}"
        for c in civs
    ]) or "No civilizations yet."

    history_section = ctx.get("extended", ctx["recent"]) if needs_deep else ctx["recent"]

    prompt = f"""
You are the omniscient narrator of "{WORLD_NAME}".
{ctx['year']} | Era: {ctx['era']}

LORE (compressed history): {ctx['lore'] or '(world is young)'}

CIVILIZATIONS:
{civs_summary}

INHABITANTS:
{agents_summary}

{'FULL HISTORY' if needs_deep else 'RECENT EVENTS'}:
{history_section}

QUESTION: "{question}"

Answer as a vivid world narrator. Max 3 paragraphs. Be specific with names and dates.
"""
    return ask_llm(prompt, max_tokens=500)
