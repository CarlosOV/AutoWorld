#!/usr/bin/env python3
"""
AutoWorld — Autonomous AI Living World
Usage:
  python main.py start          # start world + web dashboard
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


def cmd_start():
    import threading
    import uvicorn
    from apscheduler.schedulers.blocking import BlockingScheduler

    print(f"🌍 Starting {WORLD_NAME}... tick every {TICK_INTERVAL} min")
    init_db()
    _ensure_agents()

    # Launch web dashboard in background thread
    web_port = int(os.getenv("WEB_PORT", "8000"))
    def run_web():
        uvicorn.run("api.server:app", host="0.0.0.0", port=web_port, log_level="warning")
    t = threading.Thread(target=run_web, daemon=True)
    t.start()
    print(f"🌐 Dashboard running at http://localhost:{web_port}")

    # Launch Telegram bot in background thread
    from world.telegram_bot import start_bot
    start_bot()
    print(f"🤖 Telegram bot active")

    def safe_tick():
        try:
            world_tick()
        except Exception as e:
            print(f"[scheduler] Tick error (world keeps running): {e}")

    from datetime import datetime, timedelta
    scheduler = BlockingScheduler()

    # Only run immediately if world has never ticked, otherwise wait for next interval
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
        return  # never overwrite existing world data

    # Only generate if truly empty (first run)
    print(f"🌱 First run — generating {NUM_AGENTS} initial inhabitants...")
    for _ in range(NUM_AGENTS):
        existing = [a["name"] for a in get_all_agents()]
        a = generate_agent(WORLD_NAME, existing)
        print(f"  ✨ {a['name']} ({a.get('occupation','?')})")


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
    else:
        print(__doc__)
