# AutoWorld — Autonomous AI Living World

## Concept
Un mundo simulado con agentes IA que viven, interactúan y crecen de forma autónoma.
Open source, self-hosted, conectado a OpenRouter (free tier).

## Stack
- **Lenguaje:** Python 3.11 (simple, disponible en cualquier PC)
- **DB:** SQLite (zero config, un solo archivo)
- **LLM:** OpenRouter API (free models: mistral-7b, llama-3.1-8b, etc.)
- **Scheduler:** APScheduler (world ticks cada X minutos)
- **Notificaciones:** Telegram Bot (opcional)
- **UI:** CLI + simple web (FastAPI + HTML estático)
- **Deploy:** Docker Compose (un solo comando)

## World Mechanics

### Agentes
Cada agente tiene:
- Nombre, edad, personalidad (5 traits)
- Ocupación, goals (3 objetivos)
- Memoria episódica (últimas N interacciones)
- Estado emocional actual
- Relaciones con otros agentes

### World Tick (cada 30 min)
1. El LLM decide qué pasa en el mundo (eventos aleatorios)
2. Cada agente reacciona según su personalidad
3. Agentes interactúan entre sí (conversaciones, conflictos, alianzas)
4. El mundo acumula historia en SQLite
5. Si pasa algo épico → notificación Telegram

### Crecimiento
- Nuevos agentes nacen/llegan con el tiempo
- Agentes pueden morir o irse
- Economía simple (recursos, trabajos)
- Historia acumulada (lore del mundo)

## Query Interface
```
python world.py ask "¿Qué pasó hoy?"
python world.py ask "¿Cómo está el agente X?"
python world.py status
python world.py history --days 7
```
O vía web: http://localhost:8000

## Estructura del Repo
```
autoworld/
├── docker-compose.yml
├── .env.example          # OPENROUTER_API_KEY=...
├── world/
│   ├── main.py           # entry point + scheduler
│   ├── agent.py          # Agent class
│   ├── world_engine.py   # tick logic
│   ├── memory.py         # SQLite layer
│   ├── llm.py            # OpenRouter client
│   └── notifier.py       # Telegram optional
├── api/
│   └── server.py         # FastAPI query interface
├── web/
│   └── index.html        # simple dashboard
└── README.md
```

## Configuración (.env)
```
OPENROUTER_API_KEY=sk-or-...   # free en openrouter.ai
WORLD_NAME=Mi Mundo
TICK_INTERVAL=30               # minutos entre ticks
NUM_AGENTS=5                   # agentes iniciales
TELEGRAM_TOKEN=...             # opcional, para notificaciones
TELEGRAM_CHAT_ID=...
```

## MVP Features (v0.1)
- [x] 5 agentes con personalidad generada por LLM
- [x] World tick cada 30 min
- [x] Historia en SQLite
- [x] CLI para consultar
- [x] README con instrucciones self-host

## v0.2
- Web dashboard
- Notificaciones Telegram
- Más agentes, economía simple
