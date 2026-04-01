"""
SQLite 记忆数据库层
表结构：
  memories(id, session_id, turn_index, user_query, resolved_query, summary, keywords, created_at)
"""
import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional

logger = logging.getLogger(__name__)

# DB 文件放在 backend/ 目录下
DB_PATH = Path(__file__).parent.parent / "memory.db"


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库，创建表（幂等）"""git clone https://github.com/chenli123456424/Xiaozhi-Digital-Assistant.git
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id   TEXT    NOT NULL,
                turn_index   INTEGER NOT NULL,
                user_query   TEXT    NOT NULL,
                resolved_query TEXT,
                summary      TEXT    NOT NULL,
                keywords     TEXT,           -- JSON 数组字符串
                created_at   TEXT    NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_session ON memories(session_id)")
        conn.commit()
    logger.info(f"[MemoryDB] Initialized at {DB_PATH}")


def save_memory(session_id: str, turn_index: int,
                user_query: str, resolved_query: str,
                summary: str, keywords: List[str]):
    """写入一条记忆记录"""
    with _get_conn() as conn:
        conn.execute("""
            INSERT INTO memories
              (session_id, turn_index, user_query, resolved_query, summary, keywords, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id, turn_index, user_query, resolved_query,
            summary, json.dumps(keywords, ensure_ascii=False),
            datetime.utcnow().isoformat()
        ))
        conn.commit()
    logger.info(f"[MemoryDB] Saved turn {turn_index} for session {session_id[:8]}…")


def load_memories(session_id: str, limit: int = 20) -> List[dict]:
    """读取某会话的全部记忆，按轮次升序"""
    with _get_conn() as conn:
        rows = conn.execute("""
            SELECT turn_index, user_query, resolved_query, summary, keywords, created_at
            FROM memories
            WHERE session_id = ?
            ORDER BY turn_index ASC
            LIMIT ?
        """, (session_id, limit)).fetchall()
    return [dict(r) for r in rows]


def get_turn_count(session_id: str) -> int:
    """获取某会话已有的对话轮数"""
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM memories WHERE session_id = ?",
            (session_id,)
        ).fetchone()
    return row["cnt"] if row else 0
