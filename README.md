# 🌍 AutoWorld — Autonomous AI Living World

An open-source, self-hosted autonomous world simulation powered by LLMs via OpenRouter (free tier).

## What is this?

AutoWorld creates a living, breathing world with AI agents that:
- Have their own names, personalities, jobs, and goals
- React to world events autonomously
- Build memories and relationships over time
- Send you notifications when epic events happen

The world runs 24/7 on your machine and keeps growing while you sleep.

## Quick Start

```bash
# 1. Clone and setup
git clone https://github.com/yourusername/autoworld
cd autoworld
cp .env.example .env
# Edit .env with your OpenRouter API key (free at openrouter.ai)

# 2. Install
pip install -r requirements.txt

# 3. Start the world!
python main.py start
```

## Commands

```bash
python main.py start          # Start (runs ticks every 30 min)
python main.py tick           # Run one tick manually
python main.py status         # See agents + recent events
python main.py ask "¿Qué pasó hoy?"   # Ask the narrator
python main.py add-agent      # Add a new inhabitant
```

## Docker

```bash
cp .env.example .env  # fill in your API key
docker-compose up -d
```

## Configuration (.env)

| Variable | Default | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | required | Get free at openrouter.ai |
| `WORLD_NAME` | Aethoria | Name of your world |
| `NUM_AGENTS` | 5 | Starting population |
| `TICK_INTERVAL` | 30 | Minutes between ticks |
| `LLM_MODEL` | mistral-7b-instruct:free | Any OpenRouter model |
| `TELEGRAM_TOKEN` | optional | For notifications |
| `TELEGRAM_CHAT_ID` | optional | Your Telegram chat ID |

## Free Models (OpenRouter)

- `mistralai/mistral-7b-instruct:free`
- `meta-llama/llama-3.1-8b-instruct:free`
- `google/gemma-2-9b-it:free`

## License

MIT — do whatever you want with it.
