from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import os
from typing import Optional
from world.memory import init_db, get_all_agents, get_recent_events, get_events, get_agent_history, get_world_state, get_event_count, ensure_world_seed, save_agent
from world.terrain import get_continent_centers
from world.world_engine import answer_question
from world.tech_tree import get_all_discoveries, get_civ_tech_summary, _tier_name, _get_civ_tier, _get_discovered
import json

app = FastAPI(title="AutoWorld Dashboard")

# Serve CSS/JS as static files
_web_dir = os.path.join(os.path.dirname(__file__), "../web/static")
app.mount("/static", StaticFiles(directory=_web_dir), name="static")

@app.on_event("startup")
def startup():
    init_db()

@app.get("/api/state")
def get_state():
    agents = get_all_agents()
    events = get_recent_events(60)
    era = get_world_state("era", "Primordial Age")
    year = get_world_state("world_year", "Year 1")
    civs = json.loads(get_world_state("civilizations", "[]"))
    discoveries = get_all_discoveries()

    # Enrich civs with tech info
    for civ in civs:
        name = civ["name"]
        techs = discoveries.get(name, [])
        discovered_obj = _get_discovered()
        tier = _get_civ_tier(name, discovered_obj)
        civ["tech_tier"] = tier
        civ["tech_tier_name"] = _tier_name(tier)
        civ["tech_count"] = len(techs)
        civ["latest_tech"] = techs[-1] if techs else None

    return {
        "world_name": os.getenv("WORLD_NAME", "AutoWorld"),
        "world_seed": ensure_world_seed(),
        "continent_centers": get_continent_centers(ensure_world_seed()),
        "era": era,
        "year": year,
        "agents": agents,
        "events": events,
        "civilizations": civs,
        "discoveries": discoveries,
    }

@app.get("/api/ask")
def ask(q: str, deep: bool = False):
    answer = answer_question(q, deep=deep)
    return {"answer": answer}

@app.get("/api/events")
def events(
    limit: int = 50,
    offset: int = 0,
    type: Optional[str] = None,
    search: Optional[str] = None,
):
    """Full event history — all data, paginated. Nothing is hidden."""
    rows = get_events(limit=limit, offset=offset, type_filter=type, search=search)
    total = get_event_count()
    return {"total": total, "offset": offset, "limit": limit, "events": rows}

@app.get("/api/agents/{name}/history")
def agent_history(name: str, limit: int = 50):
    """Full event history for a specific agent."""
    rows = get_agent_history(agent_name=name, limit=limit)
    return {"agent": name, "total": len(rows), "events": rows}

@app.get("/api/lore")
def lore():
    """Compressed world lore + raw stats."""
    return {
        "lore": get_world_state("lore_summary", ""),
        "total_events": get_event_count(),
        "last_compressed_at": get_world_state("last_compress_at", "0"),
        "era": get_world_state("era", "Primordial Age"),
        "year": get_world_state("world_year", "Year 1"),
    }

@app.get("/api/tech")
def tech_summary():
    civs = json.loads(get_world_state("civilizations", "[]"))
    return [get_civ_tech_summary(c["name"]) for c in civs]

@app.post("/api/reset-terrain-cache")
def reset_terrain_cache():
    """Clear cached continent centers so they regenerate with correct RNG on next request."""
    from world.memory import set_world_state
    set_world_state("continent_centers", "")
    return {"status": "cleared"}

@app.post("/api/reset-positions")
def reset_positions():
    """Clear stored agent positions so they re-snap to correct CIV_CENTERS."""
    agents = get_all_agents()
    for a in agents:
        a.pop("x", None); a.pop("y", None)
        save_agent(a["name"], a)
    return {"reset": len(agents)}

@app.get("/", response_class=HTMLResponse)
def dashboard():
    with open(os.path.join(os.path.dirname(__file__), "../web/index.html")) as f:
        return f.read()
