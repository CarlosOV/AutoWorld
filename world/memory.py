"""
Memory layer — PostgreSQL (prod) or SQLite (local dev).
Set DATABASE_URL=postgresql://user:pass@host/db for Postgres.
Falls back to SQLite (world.db) if not set.
"""
import os
import json
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL", "")

def _get_conn():
    if DATABASE_URL:
        import psycopg2
        return psycopg2.connect(DATABASE_URL)
    else:
        import sqlite3
        return sqlite3.connect("world.db")

def _cur(conn):
    """Always use a cursor — works for both psycopg2 and sqlite3."""
    return conn.cursor()

def _ph():
    return "%s" if DATABASE_URL else "?"

# --- Schema ---
def init_db():
    conn = _get_conn()
    c = _cur(conn)
    if DATABASE_URL:
        c.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                id SERIAL PRIMARY KEY,
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
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS world_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
    else:
        c.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                data TEXT NOT NULL
            )
        """)
        c.execute("""
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
    c = _cur(conn)
    if DATABASE_URL:
        c.execute(
            "INSERT INTO agents (name, data) VALUES (%s, %s) ON CONFLICT (name) DO UPDATE SET data=EXCLUDED.data",
            (name, json.dumps(data))
        )
    else:
        c.execute(
            "INSERT OR REPLACE INTO agents (name, data) VALUES (?, ?)",
            (name, json.dumps(data))
        )
    conn.commit()
    conn.close()

def get_all_agents() -> list:
    conn = _get_conn()
    c = _cur(conn)
    c.execute("SELECT name, data FROM agents")
    rows = c.fetchall()
    conn.close()
    return [{"name": r[0], **json.loads(r[1])} for r in rows]

# --- Events ---
def log_event(type_: str, description: str, agents: list = None):
    ph = _ph()
    conn = _get_conn()
    c = _cur(conn)
    c.execute(
        f"INSERT INTO events (timestamp, type, description, agents_involved) VALUES ({ph},{ph},{ph},{ph})",
        (datetime.utcnow().isoformat(), type_, description, json.dumps(agents or []))
    )
    conn.commit()
    conn.close()

def get_recent_events(limit: int = 20) -> list:
    ph = _ph()
    conn = _get_conn()
    c = _cur(conn)
    c.execute(
        f"SELECT timestamp, type, description, agents_involved FROM events ORDER BY id DESC LIMIT {ph}",
        (limit,)
    )
    rows = c.fetchall()
    conn.close()
    return [{"ts": r[0], "type": r[1], "desc": r[2], "agents": json.loads(r[3])} for r in rows]

def get_event_count() -> int:
    conn = _get_conn()
    c = _cur(conn)
    c.execute("SELECT COUNT(*) FROM events")
    row = c.fetchone()
    conn.close()
    return row[0]

def get_events(limit: int = 50, offset: int = 0, type_filter: str = None, search: str = None) -> list:
    ph = _ph()
    clauses, params = [], []
    if type_filter:
        clauses.append(f"type = {ph}")
        params.append(type_filter)
    if search:
        clauses.append(f"description ILIKE {ph}" if DATABASE_URL else f"description LIKE {ph}")
        params.append(f"%{search}%")
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    params += [limit, offset]
    conn = _get_conn()
    c = _cur(conn)
    c.execute(
        f"SELECT id, timestamp, type, description, agents_involved FROM events {where} ORDER BY id DESC LIMIT {ph} OFFSET {ph}",
        params
    )
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "ts": r[1], "type": r[2], "desc": r[3], "agents": json.loads(r[4])} for r in rows]

def get_agent_history(agent_name: str, limit: int = 50) -> list:
    ph = _ph()
    conn = _get_conn()
    c = _cur(conn)
    c.execute(
        f"SELECT id, timestamp, type, description, agents_involved FROM events WHERE agents_involved LIKE {ph} ORDER BY id DESC LIMIT {ph}",
        (f"%{agent_name}%", limit)
    )
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "ts": r[1], "type": r[2], "desc": r[3], "agents": json.loads(r[4])} for r in rows]

# --- World State ---
def set_world_state(key: str, value: str):
    ph = _ph()
    conn = _get_conn()
    c = _cur(conn)
    if DATABASE_URL:
        c.execute(
            "INSERT INTO world_state (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value",
            (key, value)
        )
    else:
        c.execute(
            "INSERT OR REPLACE INTO world_state (key, value) VALUES (?, ?)", (key, value)
        )
    conn.commit()
    conn.close()

def get_world_state(key: str, default: str = "") -> str:
    ph = _ph()
    conn = _get_conn()
    c = _cur(conn)
    c.execute(f"SELECT value FROM world_state WHERE key={ph}", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else default
