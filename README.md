# 🌍 AutoWorld — Autonomous AI Living World

**🔴 Live Demo → [autoworld.painpointfinder.com](https://autoworld.painpointfinder.com/)**

An open-source, self-hosted autonomous world simulation powered by LLMs via OpenRouter (free tier). Deploy it, give it a name, and watch civilizations rise, agents gossip, wars break out, and economies evolve — all while you sleep.

---

## What is this?

AutoWorld creates a living, breathing world where AI agents have personalities, relationships, jobs, and goals. Every 30 minutes a **world tick** runs: events unfold, agents react, civilizations grow, economies shift, and the history of your world writes itself.

You watch it all through a fantasy-style web dashboard — or get notified on Telegram when something epic happens.

---

## Features

### 🧙 Agents
- Each agent has a **name, occupation, personality traits, goals, and memories**
- Agents **react to world events** using LLM — their response reflects their unique personality
- Agents maintain **relationships** with each other (friend, enemy, rival, lover, mentor...)
- Agent **positions** on the map are tied to their civilization's continent
- Agents can go on **expeditions** (wander outside their territory)
- Each agent accumulates **personal wealth** based on their occupation

### 🏰 Civilizations
- Civilizations form organically from groups of agents
- Each civ has a **name, capital, power level, territory, and status** (at_peace / at_war)
- Civs can **declare war** on each other (15% chance per tick when conditions are met)
- Civs can **sign peace treaties**
- **Power level** grows with population and tech tier

### ⚔️ Wars & Peace
- Wars are triggered by LLM-generated narratives — not random numbers
- War events are **broadcast to Telegram** when they start
- Peace can be negotiated after a war period

### 🔬 Technology Tree (Tier 0–10)
Each civilization independently climbs the tech tree:

| Tier | Name | Examples |
|------|------|---------|
| 0 | Primitive | Fire, Basic Tools |
| 1 | Ancient | Writing, Agriculture |
| 2 | Classical | Mathematics, Aqueducts |
| 3 | Medieval | Steel, Universities |
| 4 | Renaissance | Printing Press, Gunpowder |
| 5 | Industrial | Steam Engine, Electricity |
| 6 | Modern | Computers, Nuclear |
| 7 | Digital | AI, Biotech |
| 8 | Advanced | Nanotech, Fusion |
| 9 | Stellar | Space Travel, Mind Upload |
| 10 | Transcendent | Reality Editing |

- Discoveries are **LLM-generated** — original names, no existing IP
- Tech multiplies **economic production** (+15% per tier)

### 🎭 Drama System
Every tick has a chance to generate one of 12 dramatic event types:

| Type | Description |
|------|-------------|
| Betrayal 💔 | One agent reveals another's secret |
| Power Play 👑 | Agent tries to seize influence |
| Conspiracy 🕵️ | Two agents plot against a third |
| Romance ❤️ | Forbidden attraction between agents |
| Jealousy 😡 | Agent consumed by envy |
| Rivalry ⚔️ | Escalating conflict between two agents |
| Secret 🤫 | Agent hiding something dangerous |
| Blackmail 📜 | Leverage over another agent |
| Revelation 😱 | Shocking truth uncovered |
| Scandal 🗞️ | Public embarrassment |
| Debt 💰 | Unpayable obligation |
| Duel 🗡️ | Public challenge to combat |

Spicy events (betrayal, duel, revelation, blackmail) trigger a **Telegram notification**.

### 📖 Personal Story Arcs
Agents can develop personal subplots:

- **Quest** — secret mission no one knows about
- **Obsession** — dangerous forbidden fixation
- **Loss** — private grief
- **Ambition** — dangerous desire
- **Discovery** — ancient secret
- **Addiction** — consuming secret habit
- **Vision** — prophetic dreams
- **Revenge** — quiet long-term plan

### 💰 Economy System
Each civilization has 5 resources that evolve every tick:

| Resource | Produced by |
|----------|------------|
| 🌾 Food | Farmers, Healers |
| ⚒️ Materials | Craftsmen, Warriors |
| 💰 Wealth | Merchants, Assassins |
| 📚 Knowledge | Scholars, Mages, Explorers |
| 👑 Influence | Priests, Rulers, Spies |

**Economic model evolves with tech tier:**
- Tier 0–1: Subsistence barter / Tribal gift economy
- Tier 2–3: Agrarian surplus / Feudal taxation
- Tier 4–5: Merchant currency / Early capitalism
- Tier 6–7: Industrial markets / Regulated economy
- Tier 8–9: Information economy / Automated abundance
- Tier 10: Post-scarcity

**Random economic events (15% chance/tick):**
Famine 🌾, Boom 📈, Plague ☠️, Gold Rush ⛏️, Corruption 💸, Festival 🎉, Drought 🌵, Invention 💡, Trade Ban 🚫

**Trade:** Civilizations with surplus automatically trade with neighbors in deficit (30% chance/tick).

### 🌅 Era Progression
Every 100 ticks, the world transitions to a new era. Era names are **LLM-generated** — original, poetic, never recycled.

### 🗺️ World Map
- **Procedural terrain** — unique per world, seeded from world name + random seed stored in DB
- **Biome layers**: deep ocean → sea → beach → grassland → forest → highlands → mountain → snow
- **7 continents** with irregular fractal coastlines (peninsulas, bays, inlets)
- **Mountain symbols** on high terrain
- **Tree clusters** in forest zones
- **Rivers** flowing from highlands to sea
- **Compass rose**
- **Civilization territory shading** — color-coded per empire
- **Agent icons** — always placed on land, near their civilization's continent
- **Relationship lines** between agents
- **Zoom & Pan** — scroll wheel / drag / pinch-to-zoom

**Level of Detail (LOD) by zoom level:**

| Zoom | New Detail |
|------|-----------|
| 1x | Base terrain + agent icons |
| 2x | Roads between civ members |
| 3x | Agent name tags + mood bars |
| 4x+ | Capital 🏰 icons + city names |

### 🔮 Oracle
Ask the Oracle anything about the world:
- **Normal mode** — quick answer from recent context
- **Deep mode** — reads full lore, compressed history, and all agent memories before answering

### 📱 Telegram Bot
Commands:
- `/status` — world year, era, civilization count
- `/agents` — list all agents with mood
- `/tech` — tech tier per civilization
- `/events` — last 10 events
- `/lore` — compressed world history
- `/ask <question>` — ask the Oracle
- Free text → Oracle

Epic events, wars, big drama, and economic crises are pushed automatically.

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/CarlosOV/AutoWorld
cd AutoWorld

# 2. Install
pip install -r requirements.txt

# 3. Configure
cp .env.example .env
# Edit .env with your keys

# 4. Run
python main.py start
```

Dashboard at → http://localhost:8000

---

## Configuration (.env)

```env
# Required
OPENROUTER_API_KEY=sk-or-...

# World identity
WORLD_NAME=Aethoria          # Name of your world
WORLD_LANGUAGE=English       # Language for all LLM outputs

# LLM model (free tier)
LLM_MODEL=minimax/minimax-m2.5:free
LLM_MAX_TOKENS=0             # 0 = no limit (recommended for reasoning models)

# Tick interval
TICK_INTERVAL=30             # minutes between world ticks

# Database (optional — uses SQLite by default)
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Telegram (optional)
TELEGRAM_TOKEN=bot123:ABC...
TELEGRAM_CHAT_ID=123456789

# Admin key — protects /api/reset-* endpoints
ADMIN_KEY=change-me-to-something-secret
```

> **Security:** Without `ADMIN_KEY` set, all admin endpoints return `403 Forbidden`.
> Call them with `-H "X-Admin-Key: your-secret"` in curl/requests.

---

## CLI Commands

```bash
python main.py start        # Start world + web dashboard
python main.py tick         # Run one manual tick
python main.py status       # Print world status
python main.py ask "..."    # Ask the Oracle from terminal
python main.py add-agent    # Generate a new agent
python main.py tech         # Show tech tree status
python main.py reset        # ⚠️ Wipe all world data and start fresh
```

---

## Deploy on Dokploy / Docker

```bash
docker build -t autoworld .
docker run -p 8000:8000 --env-file .env autoworld
```

Or use `docker-compose.yml` — set your env vars in Dokploy's environment panel.

**Required env vars in Dokploy:**
- `OPENROUTER_API_KEY`
- `DATABASE_URL` (use Dokploy's built-in Postgres)
- `WORLD_NAME`
- `WORLD_LANGUAGE`

---

## Architecture

```
AutoWorld/
├── main.py                  # Entry point + CLI
├── world/
│   ├── agent.py             # Agent generation + reactions (LLM)
│   ├── world_engine.py      # Main tick loop — events, wars, eras
│   ├── drama.py             # 12 drama types + 8 personal story arcs
│   ├── economy.py           # Resources, trade, GDP, economic events
│   ├── tech_tree.py         # Technology discovery per civilization
│   ├── terrain.py           # Continent centers (server-side, synced with frontend)
│   ├── context_manager.py   # LLM context compression — lore + memory capping
│   ├── memory.py            # PostgreSQL/SQLite persistence layer
│   ├── llm.py               # OpenRouter client — language injection, null-content fallback
│   ├── notifier.py          # Telegram push notifications
│   └── telegram_bot.py      # Telegram bot with commands + oracle
├── api/
│   └── server.py            # FastAPI — /api/state, /api/events, /api/ask, /api/tech, /api/lore
└── web/
    ├── index.html           # Dashboard shell
    └── static/
        ├── app.css          # Fantasy dark theme
        └── app.js           # Canvas map, LOD zoom, tabs, oracle UI
```

### Key Design Decisions

**Context management** — The LLM never sees the full history. Every 30 events, old events are compressed into a lore summary (≤600 chars). Agent memories are capped at 6 entries. The LLM sees: last 8 events + compressed lore + agent memories.

**Terrain sync** — Continent positions are computed server-side (`terrain.py`) using the same seeded RNG as the frontend JS. Stored in DB so they never change. Agents always spawn on land.

**Rate limits** — OpenRouter free tier = 50 requests/day. If the rate limit is hit, the tick is skipped gracefully — the world never crashes.

**Safe restart** — World data is never overwritten on container restart. Agents, events, and lore persist across deploys.

**World seed** — Each world instance generates a unique random seed on first run, stored in the DB. Two worlds with the same name will still have different terrain.

---

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/state` | Full world state (agents, civs, events, economy, terrain) |
| `GET /api/events?limit=50&filter=notable` | Event history with optional filter |
| `GET /api/agents/:name/history` | Full memory history for one agent |
| `GET /api/lore` | Compressed world lore |
| `GET /api/tech` | Tech tree status per civilization |
| `GET /api/ask?q=...&deep=true` | Oracle query |
| `POST /api/reset-positions` | Re-snap all agents to their continent ⚠️ requires `X-Admin-Key` |
| `POST /api/reset-terrain-cache` | Force terrain regeneration ⚠️ requires `X-Admin-Key` |

---

## Rate Limits & Free Tier

OpenRouter free models: ~50 requests/day. AutoWorld uses ~3–5 requests per tick.

At 30-minute tick intervals: ~48 ticks/day = ~150–240 requests/day.

**Recommendation:** Set `TICK_INTERVAL=60` for free tier, or use a paid model with higher limits.

To use a different model:
```env
LLM_MODEL=google/gemini-flash-1.5:free
LLM_MODEL=meta-llama/llama-3.1-8b-instruct:free
LLM_MODEL=anthropic/claude-3-haiku
```

---

## License

MIT — fork it, extend it, run your own world.
