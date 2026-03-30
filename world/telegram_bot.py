"""
Telegram Bot — query the world from Telegram.
Runs in a background thread via long-polling.

Commands:
  /ask <question>   — ask the world narrator
  /status           — world summary + stats
  /agents           — list all inhabitants
  /tech             — technology tree
  /events [n]       — last N events (default 5)
  /lore             — compressed world history
  Any free text     — treated as /ask
"""
import os
import time
import threading
import requests

TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
WORLD_NAME       = os.getenv("WORLD_NAME", "Aethoria")

API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

def _send(chat_id: str, text: str):
    try:
        requests.post(f"{API}/sendMessage", json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
        }, timeout=10)
    except Exception as e:
        print(f"[bot] send error: {e}")

def _handle(message: dict):
    chat_id = str(message.get("chat", {}).get("id", ""))
    text    = message.get("text", "").strip()
    if not text:
        return
    # Strip bot mention from commands (e.g. /status@mybot → /status)
    if text.startswith("/") and "@" in text.split()[0]:
        text = text.split("@")[0] + (" " + " ".join(text.split()[1:]) if len(text.split()) > 1 else "")

    # Security: only respond to the configured chat
    if TELEGRAM_CHAT_ID and chat_id != TELEGRAM_CHAT_ID:
        _send(chat_id, "⛔ Unauthorized.")
        return

    print(f"[bot] Message from {chat_id}: {text[:60]}")

    # Lazy import to avoid circular deps
    from world.memory import get_all_agents, get_world_state, get_event_count
    from world.world_engine import answer_question
    from world.tech_tree import get_civ_tech_summary, _get_discovered, _get_civ_tier, _tier_name
    import json

    if text.startswith("/start") or text.startswith("/help"):
        _send(chat_id, (
            f"🌍 *{WORLD_NAME} — World Console*\n\n"
            "/ask _<pregunta>_ — consulta al narrador\n"
            "/status — resumen del mundo\n"
            "/agents — lista de habitantes\n"
            "/tech — árbol de tecnologías\n"
            "/events — últimos eventos\n"
            "/lore — historia comprimida\n\n"
            "_O escribe cualquier pregunta directamente._"
        ))

    elif text.startswith("/status"):
        agents = get_all_agents()
        era    = get_world_state("era", "Primordial Age")
        year   = get_world_state("world_year", "Year 1")
        total  = get_event_count()
        civs   = json.loads(get_world_state("civilizations", "[]"))
        wars   = sum(1 for c in civs if c.get("status") == "war")
        civ_lines = "\n".join(f"  {c.get('emoji','🏰')} {c['name']} ({c.get('status','?')})" for c in civs) or "  (ninguna aún)"
        _send(chat_id, (
            f"🌍 *{WORLD_NAME}*\n"
            f"📅 {year} | 🏛 {era}\n"
            f"👥 {len(agents)} habitantes | ⚔️ {wars} guerras | 📜 {total} eventos\n\n"
            f"*Civilizaciones:*\n{civ_lines}"
        ))

    elif text.startswith("/agents"):
        agents = get_all_agents()
        if not agents:
            _send(chat_id, "No hay habitantes aún.")
            return
        lines = "\n".join(
            f"• *{a['name']}* — {a.get('occupation','?')} | {a.get('mood','neutral')} | civ: {a.get('civ','—')}"
            for a in agents
        )
        _send(chat_id, f"👥 *Habitantes de {WORLD_NAME}*\n\n{lines}")

    elif text.startswith("/tech"):
        import json
        civs = json.loads(get_world_state("civilizations", "[]"))
        if not civs:
            _send(chat_id, "Aún no hay civilizaciones."); return
        discovered = _get_discovered()
        lines = []
        for c in civs:
            tier     = _get_civ_tier(c["name"], discovered)
            tier_name = _tier_name(tier)
            techs    = discovered.get(c["name"], [])
            latest   = techs[-3:] if techs else []
            lines.append(f"{c.get('emoji','🏰')} *{c['name']}* — Tier {tier} ({tier_name})\n  └ {', '.join(latest) or 'sin descubrimientos'}")
        _send(chat_id, "🔬 *Tech Tree*\n\n" + "\n\n".join(lines))

    elif text.startswith("/events"):
        parts = text.split()
        n = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 5
        n = min(n, 15)
        from world.memory import get_recent_events
        events = get_recent_events(n)
        if not events:
            _send(chat_id, "No hay eventos aún."); return
        lines = "\n\n".join(
            f"[{e['ts'][:16]}]\n{e['desc'][:200]}"
            for e in reversed(events)
        )
        _send(chat_id, f"📜 *Últimos {n} eventos*\n\n{lines}")

    elif text.startswith("/lore"):
        lore = get_world_state("lore_summary", "")
        if not lore:
            _send(chat_id, "El mundo es joven — aún no hay historia comprimida."); return
        total = get_event_count()
        _send(chat_id, f"📖 *Lore de {WORLD_NAME}*\n_(basado en {total} eventos)_\n\n{lore}")

    else:
        # Free text → oracle
        question = text.lstrip("/ask").strip() if text.startswith("/ask") else text
        if not question:
            _send(chat_id, "¿Qué quieres saber del mundo?"); return
        _send(chat_id, "✨ _Consultando al oráculo..._")
        try:
            deep = any(w in question.lower() for w in ["historia","before","antes","guerra","origin","todo","all"])
            answer = answer_question(question, deep=deep)
            _send(chat_id, f"🔮 *{WORLD_NAME}*\n\n{answer}")
        except Exception as e:
            err = str(e)
            if "RATE_LIMIT" in err:
                _send(chat_id, "⏳ Límite de requests alcanzado. Intenta en unos minutos.")
            else:
                _send(chat_id, f"⚠️ El oráculo no puede responder ahora: {err[:100]}")


def _drain_pending() -> int:
    """On startup, skip all pending messages to avoid replaying old ones."""
    try:
        resp = requests.get(f"{API}/getUpdates", params={"offset": -1, "timeout": 0}, timeout=10)
        updates = resp.json().get("result", [])
        if updates:
            return updates[-1]["update_id"] + 1
    except Exception:
        pass
    return 0

def _poll_loop():
    if not TELEGRAM_TOKEN:
        print("[bot] No TELEGRAM_TOKEN — bot disabled.")
        return
    print(f"[bot] Telegram bot started, listening for messages...")
    # Skip messages that arrived before this run
    offset = _drain_pending()
    print(f"[bot] Skipped old messages, starting from offset {offset}")
    while True:
        try:
            resp = requests.get(f"{API}/getUpdates", params={"offset": offset, "timeout": 30}, timeout=35)
            if not resp.ok:
                time.sleep(5); continue
            for update in resp.json().get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message") or update.get("edited_message")
                if msg:
                    try:
                        _handle(msg)
                    except Exception as e:
                        print(f"[bot] Handler error: {e}")
        except Exception as e:
            print(f"[bot] Poll error: {e}")
            time.sleep(5)


def start_bot():
    """Start the Telegram bot in a background daemon thread."""
    t = threading.Thread(target=_poll_loop, daemon=True, name="telegram-bot")
    t.start()
    return t
