"""
Context Manager — keeps LLM prompts lean.

Strategy:
- Keep last RECENT_EVENTS_WINDOW events in full detail for normal prompts
- Older events are periodically compressed into a "World Lore" summary stored in DB
- Agent memories are capped at AGENT_MEMORY_CAP entries
- For deep queries, caller can request extended context (get_deep_context)
- Total context per normal prompt: ~800-1200 tokens max
- ALL data is always preserved in DB — compression only affects what goes to LLM
"""
import os
from .memory import get_recent_events, get_events, get_world_state, set_world_state, get_event_count
from .llm import ask_llm

RECENT_EVENTS_WINDOW = int(os.getenv("RECENT_EVENTS_WINDOW", "8"))   # full-detail events in prompts
AGENT_MEMORY_CAP     = int(os.getenv("AGENT_MEMORY_CAP", "6"))        # memories per agent
COMPRESS_EVERY       = int(os.getenv("COMPRESS_EVERY", "30"))         # compress lore every N events
MAX_LORE_CHARS       = int(os.getenv("MAX_LORE_CHARS", "600"))        # max chars for lore summary

def get_world_context() -> dict:
    """
    Returns a lean context dict safe to inject into LLM prompts.
    {
      "lore": "<compressed history>",
      "recent": "<last N events as text>",
      "era": "...",
      "year": "...",
    }
    """
    recent_events = get_recent_events(RECENT_EVENTS_WINDOW)
    recent_text = "\n".join(
        f"[{e['ts'][:16]}] {e['desc'][:120]}"
        for e in reversed(recent_events)
    )
    lore = get_world_state("lore_summary", "")

    return {
        "lore": lore,
        "recent": recent_text,
        "era": get_world_state("era", "Primordial Age"),
        "year": get_world_state("world_year", "Year 1"),
    }

def trim_agent_memories(agent: dict) -> dict:
    """Cap agent memories to avoid bloating prompts."""
    memories = agent.get("memories", [])
    if len(memories) > AGENT_MEMORY_CAP:
        # Keep first entry (origin) + last N-1
        agent["memories"] = [memories[0]] + memories[-(AGENT_MEMORY_CAP - 1):]
    return agent

def get_deep_context(extra_events: int = 40) -> dict:
    """
    Extended context for deep oracle queries.
    Pulls lore + more events from DB — use only when needed.
    """
    ctx = get_world_context()
    extended = get_events(limit=extra_events)
    extended_text = "\n".join(
        f"[{e['ts'][:16]}] ({e['type']}) {e['desc'][:150]}"
        for e in reversed(extended)
    )
    ctx["extended"] = extended_text
    return ctx

def maybe_compress_lore(world_name: str):
    """
    Every COMPRESS_EVERY events, summarize the older events into lore.
    This keeps the DB intact but the LLM context small.
    """
    count = get_event_count()
    last_compress = int(get_world_state("last_compress_at", "0"))

    if count - last_compress < COMPRESS_EVERY:
        return  # not yet

    # Get events beyond the recent window (the "old" ones)
    all_recent = get_recent_events(RECENT_EVENTS_WINDOW)
    all_older  = get_recent_events(COMPRESS_EVERY + RECENT_EVENTS_WINDOW)[RECENT_EVENTS_WINDOW:]

    if len(all_older) < 5:
        return

    older_text = "\n".join(f"- {e['desc'][:120]}" for e in reversed(all_older))
    existing_lore = get_world_state("lore_summary", "")

    prompt = f"""
You are the historian of the world "{world_name}".

EXISTING LORE (already compressed):
{existing_lore or "(none yet)"}

NEW EVENTS TO COMPRESS:
{older_text}

Write a compact historical summary merging old lore + new events.
Max {MAX_LORE_CHARS} characters. Use vivid, chronicle-style language.
Focus on: wars, discoveries, births of civilizations, major shifts.
Drop minor details. This is the world's memory — make it count.
"""
    new_lore = ask_llm(prompt, max_tokens=300)
    # Hard-cap
    if len(new_lore) > MAX_LORE_CHARS:
        new_lore = new_lore[:MAX_LORE_CHARS] + "…"

    set_world_state("lore_summary", new_lore)
    set_world_state("last_compress_at", str(count))
    print(f"[context] Lore compressed at event #{count}.")
