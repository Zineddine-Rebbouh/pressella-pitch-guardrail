from datetime import datetime, timezone
import sqlite3
from typing import Optional

from app.models.draft import Draft

DEFAULT_DB_PATH = "guardrail.db"


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """Initializes the SQLite database schema idempotently.

    Creates the `drafts` table if it does not exist.
    """
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS drafts (
                id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def save_draft(draft: Draft, db_path: str = DEFAULT_DB_PATH) -> None:
    """Saves or updates a Draft object in the SQLite database (UPSERT).

    Args:
        draft: The Draft model instance to persist.
        db_path: The SQLite database file path.
    """
    init_db(db_path)
    draft_id_str = str(draft.id)
    json_data = draft.model_dump_json()
    updated_at_str = draft.updated_at.isoformat()

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO drafts (id, data, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                data = excluded.data,
                updated_at = excluded.updated_at
            """,
            (draft_id_str, json_data, updated_at_str),
        )
        conn.commit()


def get_draft(draft_id: str, db_path: str = DEFAULT_DB_PATH) -> Optional[Draft]:
    """Retrieves a Draft object by ID from the SQLite database.

    Args:
        draft_id: String representation of the draft UUID.
        db_path: The SQLite database file path.

    Returns:
        Draft model instance if found, or None if not found.
    """
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT data FROM drafts WHERE id = ?",
            (str(draft_id),),
        )
        row = cursor.fetchone()

    if row is None:
        return None

    raw_json = row[0]
    return Draft.model_validate_json(raw_json)
