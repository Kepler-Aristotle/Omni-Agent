import sqlite3
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from multi_agent_system.config import settings

class Database:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.DATABASE_PATH
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Sessions table (user id, platform e.g. telegram / web, created_at)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                mode TEXT DEFAULT 'auto' -- 'auto', 'council', 'claude', 'gemini', 'chatgpt', 'qwen', 'kimi'
            )
            """)
            
            # Messages table (session_id, role, content, agent_used, metadata, timestamp)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL, -- 'user', 'assistant', 'system'
                content TEXT NOT NULL,
                agent_used TEXT, -- e.g. 'council[claude+gemini]', 'router', 'qwen'
                metadata TEXT, -- JSON blob of sub-agent outputs, tokens, latency
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
            """)
            conn.commit()

    def get_or_create_session(self, session_id: str, user_id: str, platform: str = "web") -> Dict[str, Any]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            if row:
                cursor.execute("UPDATE sessions SET last_active = CURRENT_TIMESTAMP WHERE session_id = ?", (session_id,))
                conn.commit()
                return dict(row)
            else:
                cursor.execute(
                    "INSERT INTO sessions (session_id, user_id, platform) VALUES (?, ?, ?)",
                    (session_id, user_id, platform)
                )
                conn.commit()
                return {
                    "session_id": session_id,
                    "user_id": user_id,
                    "platform": platform,
                    "mode": "auto"
                }

    def update_session_mode(self, session_id: str, mode: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE sessions SET mode = ?, last_active = CURRENT_TIMESTAMP WHERE session_id = ?", (mode, session_id))
            conn.commit()

    def add_message(self, session_id: str, role: str, content: str, agent_used: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            meta_json = json.dumps(metadata or {})
            cursor.execute(
                "INSERT INTO messages (session_id, role, content, agent_used, metadata) VALUES (?, ?, ?, ?, ?)",
                (session_id, role, content, agent_used, meta_json)
            )
            cursor.execute("UPDATE sessions SET last_active = CURRENT_TIMESTAMP WHERE session_id = ?", (session_id,))
            conn.commit()

    def get_history(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT role, content, agent_used, metadata, created_at FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT ?",
                (session_id, limit)
            )
            rows = cursor.fetchall()
            messages = []
            for r in reversed(rows):
                messages.append({
                    "role": r["role"],
                    "content": r["content"],
                    "agent_used": r["agent_used"],
                    "metadata": json.loads(r["metadata"]) if r["metadata"] else {},
                    "created_at": r["created_at"]
                })
            return messages

    def clear_history(self, session_id: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            conn.commit()

db = Database()
