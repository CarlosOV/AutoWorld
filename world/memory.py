"""
Memory layer — PostgreSQL (prod) or SQLite (local dev).
Set DATABASE_URL=postgresql://user:pass@host/db for Postgres.
Falls back to SQLite (world.db) if not set.
"""
import os
import json
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL", "")

# --- Driver selection ---
def _get_conn():
    if DATABASE_URL:
        import psycopg2
        return psycopg2.connect(DATABASE_URL)
    else:
        import sqlite3
        return sqlite3.connect("world.db")

def _ph():
    """Placeholder: %s for postgres, ? for sqlite."""
    return "%s" if DATABASE_URL else "?"

# --- Schema ---
def init_db():
    conn = _get_conn()
    c = conn.cursor()
    ph = _ph()
    # Use TEXT for both backends (Postgres supports it fine)
    c.execute("""
        CREATE TABLE IF NOT EXISTS agents (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            data TEXT NOT NULL
        )
    """ if DATABASE_URL else """
        CREATE TABLE IF NOT EXISTS agents (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            data TEXT NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id SERIAL PRIMARY KEY,
            timestamp TEXT NOT NULL,
            type TEXT NOT NULL,
            description TEXT NOT NULL,
            agents_involved TEXT NOT NULL DEFAULT '[]'
        )
    """ if DATABASE_URL else """
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            type TEXT NOT NULL,
            description TEXT NOT NULL,
            agents_involved TEXT NOT NULL DEFAULT '[]'
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS world_state (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

# --- Agents ---
def save_agent(name: str, data: dict):
    ph = _ph()
    conn = _get_conn()
    if DATABASE_URL:
        conn.cursor().execute(
            "INSERT INTO agents (name, data) VALUES (%s, %s) ON CONFLICT (name) DO UPDATE SET data=EXCLUDED.data",
            (name, json.dumps(data))
        )
    else:
        conn.cursor().execute(
            "INSERT OR REPLACE INTO agents (name, data) VALUES (?, ?)",
            (name, json.dumps(data))
        )
    conn.commit()
    conn.close()

def get_all_agents() -> list[dict]:
    conn = _get_conn()
    rows = conn.execute("SELECT name, data FROM agents").fetchall()
    conn.close()
    return [{"name": r[0], **json.loads(r[1])} for r in rows]

# --- Events ---
def log_event(type_: str, description: str, agents: list[str] = None):
    ph = _ph()
    conn = _get_conn()
    conn.cursor().execute(
        f"INSERT INTO events (timestamp, type, description, agents_involved) VALUES ({ph},{ph},{ph},{ph})",
        (datetime.utcnow().isoformat(), type_, description, json.dumps(agents or []))
    )
    conn.commit()
    conn.close()

def get_recent_events(limit: int = 20) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT timestamp, type, description, agents_involved FROM events ORDER BY id DESC LIMIT %s" % limit
        if DATABASE_URL else
        "SELECT timestamp, type, description, agents_involved FROM events ORDER BY id DESC LIMIT ?",
        () if DATABASE_URL else (limit,)
    ).fetchall()
    conn.close()
    return [{"ts": r[0], "type": r[1], "desc": r[2], "agents": json.loads(r[3])} for r in rows]

def get_event_count() -> int:
    conn = _get_conn()
    row = conn.execute("SELECT COUNT(*) FROM events").fetchone()
    conn.close()
    return row[0]

def get_events(limit: int = 50, offset: int = 0, type_filter: str = None, search: str = None) -> list[dict]:
    """Full event history with optional filtering. All data preserved."""
    ph = _ph()
    clauses, params = [], []
    if type_filter:
        clauses.append(f"type = {ph}")
        params.append(type_filter)
    if search:
        clauses.append(f"description ILIKE {ph}" if DATABASE_URL else f"description LIKE {ph}")
        params.append(f"%{search}%")
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    if DATABASE_URL:
        params += [limit, offset]
        query = f"SELECT id, timestamp, type, description, agents_involved FROM events {where} ORDER BY id DESC LIMIT %s OFFSET %s"
    else:
        params += [limit, offset]
        query = f"SELECT id, timestamp, type, description, agents_involved FROM events {where} ORDER BY id DESC LIMIT ? OFFSET ?"
    conn = _get_conn()
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [{"id": r[0], "ts": r[1], "type": r[2], "desc": r[3], "agents": json.loads(r[4])} for r in rows]

def get_agent_history(agent_name: str, limit: int = 50) -> list[dict]:
    """All events involving a specific agent."""
    ph = _ph()
    conn = _get_conn()
    if DATABASE_URL:
        rows = conn.execute(
            "SELECT id, timestamp, type, description, agents_involved FROM events WHERE agents_involved LIKE %s ORDER BY id DESC LIMIT %s",
            (f"%{agent_name}%", limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, timestamp, type, description, agents_involved FROM events WHERE agents_involved LIKE ? ORDER BY id DESC LIMIT ?",
            (f"%{agent_name}%", limit)
        ).fetchall()
    conn.close()
    return [{"id": r[0], "ts": r[1], "type": r[2], "desc": r[3], "agents": json.loads(r[4])} for r in rows]

# --- World State (key/value) ---
def set_world_state(key: str, value: str):
    conn = _get_conn()
    if DATABASE_URL:
        conn.cursor().execute(
            "INSERT INTO world_state (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value",
            (key, value)
        )
    else:
        conn.cursor().execute(
            "INSERT OR REPLACE INTO world_state (key, value) VALUES (?, ?)", (key, value)
        )
    conn.commit()
    conn.close()

def get_world_state(key: str, default: str = "") -> str:
    ph = _ph()
    conn = _get_conn()
    row = conn.execute(
        f"SELECT value FROM world_state WHERE key={ph}", (key,)
    ).fetchone()
    conn.close()
    return row[0] if row else default
