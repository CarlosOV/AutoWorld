import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path("world.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS agents (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE,
            data TEXT  -- JSON blob
        );
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            type TEXT,
            description TEXT,
            agents_involved TEXT  -- JSON list of names
        );
        CREATE TABLE IF NOT EXISTS world_state (
            key TEXT PRIMARY KEY,
            value TEXT
        );
    """)
    conn.commit()
    conn.close()

def save_agent(name: str, data: dict):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT OR REPLACE INTO agents (name, data) VALUES (?, ?)",
        (name, json.dumps(data))
    )
    conn.commit()
    conn.close()

def get_all_agents() -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT name, data FROM agents").fetchall()
    conn.close()
    return [{"name": r[0], **json.loads(r[1])} for r in rows]

def log_event(type_: str, description: str, agents: list[str] = None):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO events (timestamp, type, description, agents_involved) VALUES (?,?,?,?)",
        (datetime.utcnow().isoformat(), type_, description, json.dumps(agents or []))
    )
    conn.commit()
    conn.close()

def get_recent_events(limit: int = 20) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT timestamp, type, description, agents_involved FROM events ORDER BY id DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [{"ts": r[0], "type": r[1], "desc": r[2], "agents": json.loads(r[3])} for r in rows]

def set_world_state(key: str, value: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT OR REPLACE INTO world_state (key, value) VALUES (?,?)", (key, value))
    conn.commit()
    conn.close()

def get_world_state(key: str, default: str = "") -> str:
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT value FROM world_state WHERE key=?", (key,)).fetchone()
    conn.close()
    return row[0] if row else default
