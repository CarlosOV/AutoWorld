from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from world.memory import init_db, get_all_agents, get_recent_events, get_world_state
from world.world_engine import answer_question
from world.tech_tree import get_all_discoveries, get_civ_tech_summary, _tier_name, _get_civ_tier, _get_discovered
import json

app = FastAPI(title="AutoWorld Dashboard")

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
        "era": era,
        "year": year,
        "agents": agents,
        "events": events,
        "civilizations": civs,
        "discoveries": discoveries,
    }

@app.get("/api/ask")
def ask(q: str):
    answer = answer_question(q)
    return {"answer": answer}

@app.get("/api/tech")
def tech_summary():
    civs = json.loads(get_world_state("civilizations", "[]"))
    return [get_civ_tech_summary(c["name"]) for c in civs]

@app.get("/", response_class=HTMLResponse)
def dashboard():
    with open(os.path.join(os.path.dirname(__file__), "../web/index.html")) as f:
        return f.read()
