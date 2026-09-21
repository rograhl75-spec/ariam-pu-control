"""Implementação SQLite para persistência principal."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from src.storage.base import StorageRepository


class SQLiteRepository(StorageRepository):
    """Repositório SQLite para logs e ocorrências."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_schema(self) -> None:
        """Cria schema inicial de persistência."""
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS occurrences (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    opened_by TEXT NOT NULL,
                    responsible_email TEXT,
                    machine TEXT NOT NULL,
                    problem TEXT NOT NULL,
                    status TEXT NOT NULL,
                    due_date TEXT,
                    closed_by TEXT,
                    data_json TEXT NOT NULL DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS occurrence_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    occurrence_id TEXT NOT NULL,
                    changed_at TEXT NOT NULL,
                    changed_by TEXT NOT NULL,
                    old_status TEXT,
                    new_status TEXT,
                    note TEXT,
                    FOREIGN KEY(occurrence_id) REFERENCES occurrences(id)
                );

                CREATE TABLE IF NOT EXISTS measurements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    data_json TEXT NOT NULL
                );
                """
            )

    def list_occurrences(self) -> list[dict[str, Any]]:
        """Lista ocorrências ordenadas por data desc."""
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM occurrences ORDER BY created_at DESC").fetchall()
        return [dict(row) for row in rows]

    def _next_occurrence_id(self) -> str:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(1) AS total FROM occurrences").fetchone()
        return f"OC-{int(row['total']) + 1:03d}"

    def create_occurrence(self, payload: dict[str, Any]) -> str:
        """Cria ocorrência com número sequencial."""
        occurrence_id = payload.get("id") or self._next_occurrence_id()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO occurrences
                (id, created_at, opened_by, responsible_email, machine, problem, status, due_date, closed_by, data_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    occurrence_id,
                    payload["created_at"],
                    payload["opened_by"],
                    payload.get("responsible_email"),
                    payload["machine"],
                    payload["problem"],
                    payload.get("status", "Pendente Ação Corretiva"),
                    payload.get("due_date"),
                    payload.get("closed_by"),
                    json.dumps(payload.get("details", {}), ensure_ascii=False),
                ),
            )
        return occurrence_id

    def update_occurrence(self, occurrence_id: str, payload: dict[str, Any]) -> None:
        """Atualiza campos principais e detalhes JSON."""
        with self._connect() as conn:
            current = conn.execute(
                "SELECT status FROM occurrences WHERE id = ?", (occurrence_id,)
            ).fetchone()
            if current is None:
                raise ValueError("Ocorrência não encontrada")

            new_status = payload.get("status", current["status"])
            conn.execute(
                """
                UPDATE occurrences
                   SET responsible_email = COALESCE(?, responsible_email),
                       machine = COALESCE(?, machine),
                       problem = COALESCE(?, problem),
                       status = ?,
                       due_date = COALESCE(?, due_date),
                       closed_by = COALESCE(?, closed_by),
                       data_json = COALESCE(?, data_json)
                 WHERE id = ?
                """,
                (
                    payload.get("responsible_email"),
                    payload.get("machine"),
                    payload.get("problem"),
                    new_status,
                    payload.get("due_date"),
                    payload.get("closed_by"),
                    json.dumps(payload.get("details", {}), ensure_ascii=False)
                    if "details" in payload
                    else None,
                    occurrence_id,
                ),
            )
            conn.execute(
                """
                INSERT INTO occurrence_history (occurrence_id, changed_at, changed_by, old_status, new_status, note)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    occurrence_id,
                    payload["changed_at"],
                    payload["changed_by"],
                    current["status"],
                    new_status,
                    payload.get("note", "Atualização de ocorrência"),
                ),
            )

    def save_measurement(self, category: str, payload: dict[str, Any]) -> None:
        """Persiste medição serializada em JSON."""
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO measurements (category, created_at, data_json) VALUES (?, ?, ?)",
                (category, payload["created_at"], json.dumps(payload, ensure_ascii=False)),
            )

    def list_measurements(self, category: str) -> list[dict[str, Any]]:
        """Lista medições por categoria."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, category, created_at, data_json FROM measurements WHERE category = ? ORDER BY id DESC",
                (category,),
            ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            payload = json.loads(row["data_json"])
            payload.update({"id": row["id"], "category": row["category"], "created_at": row["created_at"]})
            result.append(payload)
        return result
