#!/usr/bin/env python3
"""
AutoWorld — Autonomous AI Living World
Usage:
  python main.py start          # start world + web dashboard
  python main.py reset          # wipe world and start fresh (new seed + terrain)
  python main.py tick           # run one tick manually
  python main.py ask "question" # ask the world narrator
  python main.py status         # show agents + recent events
  python main.py add-agent      # generate a new agent
  python main.py tech           # show tech tree
"""

import sys
import os
from dotenv import load_dotenv

load_dotenv()

from world.memory import init_db, get_all_agents, get_recent_events, get_world_state
from world.agent import generate_agent
from world.world_engine import world_tick, answer_question

WORLD_NAME = os.getenv("WORLD_NAME", "Aethoria")
NUM_AGENTS = int(os.getenv("NUM_AGENTS", "5"))
TICK_INTERVAL = int(os.getenv("TICK_INTERVAL", "30"))


def cmd_reset():
    """Wipe all world data and start a brand new world with a fresh seed and terrain."""
    from world.memory import _get_conn, init_db
    force = "--yes" in sys.argv or "-y" in sys.argv
    if not force:
        try:
            confirm = input("⚠️  This will ERASE all world data. Type YES to confirm: ").strip()
            if confirm != "YES":
                print("Aborted.")
                return
        except EOFError:
            print("No TTY detected — proceeding with reset.")
    init_db()
    conn = _get_conn()
    cur = conn.cursor()
    for table in ("agents", "events", "world_state"):
        cur.execute(f"DELETE FROM {table}")
    conn.commit()
    cur.close()
    conn.close()
    print("✅ World wiped.")
    # Bootstrap terrain immediately (no LLM needed), agents generated via _ensure_agents in cmd_start
    import random as _rnd
    from world.memory import set_world_state
    from world.terrain import get_continent_centers
    seed = str(_rnd.randint(100000, 999999))
    set_world_state("world_seed", seed)
    print(f"🌱 World seed: {seed}")
    centers = get_continent_centers(seed)
    print(f"🗺️  Terrain generated — {len(centers)} continents")
    cmd_start()


def _bootstrap_world():
    """
    Generate agents with exponential backoff. Terrain must exist already.
    Called from _ensure_agents when no agents exist.
    """
    import json, time as _time
    from world.memory import set_world_state, ensure_world_seed, get_world_state as _gws
    from world.terrain import get_continent_centers
    from world.drama import ensure_positions

    # Ensure seed + terrain exist (idempotent — only creates if missing)
    seed = _gws("world_seed", "")
    if not seed:
        import random as _rnd
        seed = str(_rnd.randint(100000, 999999))
        set_world_state("world_seed", seed)
        print(f"🌱 World seed: {seed}")
    centers = get_continent_centers(seed)
    print(f"🗺️  Terrain: {len(centers)} continents")

    # Generate agents with backoff
    print(f"👥 Generating {NUM_AGENTS} inhabitants...")
    generated = 0
    backoff = 0
    while generated < NUM_AGENTS:
        if backoff > 0:
            print(f"   ⏳ Waiting {backoff}s before retrying...")
            _time.sleep(backoff)
        try:
            existing = [a["name"] for a in get_all_agents()]
            a = generate_agent(WORLD_NAME, existing)
            print(f"   ✨ {a['name']} ({a.get('occupation','?')})")
            generated += 1
            backoff = 0
        except Exception as e:
            backoff = min(max(backoff * 2, 60), 900)  # 60s → 120s → ... → max 15min
            print(f"   ⚠️ Agent generation failed: {e}. Backoff {backoff}s")

    # Assign positions on land
    agents = get_all_agents()
    civs = json.loads(_gws("civilizations", "[]"))
    agents, _ = ensure_positions(agents, civs)
    from world.memory import save_agent
    for a in agents:
        save_agent(a["name"], a)
    print(f"📍 All agents placed on land.")

def cmd_start():
    import threading
    import uvicorn
    from apscheduler.schedulers.blocking import BlockingScheduler

    print(f"🌍 Starting {WORLD_NAME}... tick every {TICK_INTERVAL} min")
    init_db()

    # 1. WEB SERVER FIRST — always available, even if LLM is down
    web_port = int(os.getenv("WEB_PORT", "8000"))
    def run_web():
        uvicorn.run("api.server:app", host="0.0.0.0", port=web_port, log_level="warning")
    t = threading.Thread(target=run_web, daemon=True)
    t.start()
    print(f"🌐 Dashboard running at http://localhost:{web_port}")

    # 2. Telegram bot
    from world.telegram_bot import start_bot
    start_bot()
    print(f"🤖 Telegram bot active")

    # 3. Ensure agents exist (retries in background if LLM is down)
    _ensure_agents()

    def safe_tick():
        try:
            world_tick()
        except Exception as e:
            print(f"[scheduler] Tick error (world keeps running): {e}")

    from datetime import datetime, timedelta
    scheduler = BlockingScheduler()

    last_tick_year = int(get_world_state("world_year_num", "0"))
    if last_tick_year == 0:
        print("🌱 First tick — generating world...")
        safe_tick()
    else:
        print(f"⏰ World at Year {last_tick_year} — next tick in {TICK_INTERVAL} min")

    scheduler.add_job(safe_tick, "interval", minutes=TICK_INTERVAL,
                      misfire_grace_time=300, coalesce=True,
                      next_run_time=datetime.now() + timedelta(minutes=TICK_INTERVAL))
    print("World is running. Press Ctrl+C to stop.\n")
    scheduler.start()


def cmd_tick():
    init_db()
    _ensure_agents()
    world_tick()


def cmd_ask(question: str):
    init_db()
    _ensure_agents()
    answer = answer_question(question)
    print(f"\n🌍 {WORLD_NAME} — Narrator speaks:\n")
    print(answer)
    print()


def cmd_status():
    init_db()
    agents = get_all_agents()
    events = get_recent_events(10)
    print(f"\n🌍 World: {WORLD_NAME}")
    print(f"👥 Agents ({len(agents)}):")
    for a in agents:
        mood = a.get("mood", "neutral")
        print(f"  - {a['name']} | {a.get('occupation','?')} | mood: {mood}")
    print(f"\n📜 Last {len(events)} events:")
    for e in reversed(events):
        ts = e["ts"][:16]
        print(f"  [{ts}] {e['desc'][:100]}")
    print()


def cmd_tech():
    init_db()
    import json
    from world.tech_tree import get_all_discoveries, _tier_name, _get_civ_tier, _get_discovered
    civs = json.loads(__import__("os").getenv("_", "") or "[]")
    from world.memory import get_world_state
    civs = json.loads(get_world_state("civilizations", "[]"))
    if not civs:
        print("No civilizations yet."); return
    print(f"\n🔬 Technology Tree — {WORLD_NAME}\n")
    for c in civs:
        summary = __import__("world.tech_tree", fromlist=["get_civ_tech_summary"]).get_civ_tech_summary(c["name"])
        print(f"  🏰 {c['name']} | Tier {summary['tier']} ({summary['tier_name']}) | {summary['count']} discoveries")
        for t in summary["discoveries"]:
            print(f"     ✓ {t}")
    print()

def cmd_add_agent():
    init_db()
    agents = get_all_agents()
    existing = [a["name"] for a in agents]
    print("Generating new agent...")
    agent = generate_agent(WORLD_NAME, existing)
    print(f"✨ New agent: {agent['name']} — {agent.get('occupation','?')}")
    print(f"   Personality: {', '.join(agent.get('personality',[]))}")
    print(f"   Backstory: {agent.get('backstory','')}")


def _ensure_agents():
    agents = get_all_agents()
    if agents:
        print(f"✅ World loaded: {len(agents)} existing inhabitants, resuming...")
        return
    # First run — bootstrap full world
    _bootstrap_world()


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] == "start":
        cmd_start()
    elif args[0] == "tick":
        cmd_tick()
    elif args[0] == "ask" and len(args) > 1:
        cmd_ask(" ".join(args[1:]))
    elif args[0] == "status":
        cmd_status()
    elif args[0] == "add-agent":
        cmd_add_agent()
    elif args[0] == "tech":
        cmd_tech()
    elif args[0] == "reset":
        cmd_reset()
    else:
        print(__doc__)
