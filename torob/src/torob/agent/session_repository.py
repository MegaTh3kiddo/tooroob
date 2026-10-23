from datetime import datetime, timezone
import json
import sqlite3
from typing import Optional

from torob.agent.models import ShoppingSession
from torob.storage.db import db_manager


class ShoppingSessionRepository:
    """Manages persistent shopping sessions in SQLite."""

    def __init__(self, conn: Optional[sqlite3.Connection] = None):
        self._conn = conn

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is not None:
            return self._conn
        return db_manager.get_sqlite()

    def save_session(self, session: ShoppingSession) -> None:
        session.updated_at = datetime.now(timezone.utc)
        state_json = session.model_dump_json()

        query = """
        INSERT INTO shopping_sessions (session_id, user_id, detected_intent, state_json, created_at, updated_at, expires_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(session_id) DO UPDATE SET
            user_id = excluded.user_id,
            detected_intent = excluded.detected_intent,
            state_json = excluded.state_json,
            updated_at = excluded.updated_at,
            expires_at = excluded.expires_at
        """
        self.conn.execute(
            query,
            (
                session.session_id,
                session.user_id,
                session.detected_intent.value if session.detected_intent else None,
                state_json,
                session.created_at.isoformat(),
                session.updated_at.isoformat(),
                session.expires_at.isoformat(),
            ),
        )
        self.conn.commit()

    def get_session(self, session_id: str) -> Optional[ShoppingSession]:
        cursor = self.conn.execute(
            "SELECT state_json, expires_at FROM shopping_sessions WHERE session_id = ?",
            (session_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None

        # Check expiration
        expires_at_str = row["expires_at"] if isinstance(row, sqlite3.Row) else row[1]
        try:
            exp = datetime.fromisoformat(expires_at_str)
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > exp:
                return None
        except Exception:
            pass

        state_str = row["state_json"] if isinstance(row, sqlite3.Row) else row[0]
        try:
            return ShoppingSession.model_validate_json(state_str)
        except Exception:
            return None

    def delete_session(self, session_id: str) -> bool:
        cursor = self.conn.execute(
            "DELETE FROM shopping_sessions WHERE session_id = ?",
            (session_id,),
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def expire_stale_sessions(self, now: Optional[datetime] = None) -> int:
        now = now or datetime.now(timezone.utc)
        cursor = self.conn.execute(
            "DELETE FROM shopping_sessions WHERE expires_at < ?",
            (now.isoformat(),),
        )
        self.conn.commit()
        return cursor.rowcount
