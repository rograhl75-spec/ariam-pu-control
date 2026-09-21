from datetime import date
from pathlib import Path
import json
import sqlite3

from src.services.anomalia_service import AnomaliaService
from src.storage.sqlite_repository import SQLiteRepository


def test_anomalia_atualiza_details_e_historico(tmp_path: Path):
    db = tmp_path / "test.db"
    repo = SQLiteRepository(db)
    repo.init_schema()

    service = AnomaliaService(repo)
    occurrence_id = service.abrir(
        {
            "created_at": "2026-01-01T10:00:00",
            "opened_by": "user1",
            "responsible_email": "q@example.com",
            "machine": "M1",
            "problem": "Falha",
            "status": "Pendente Ação Corretiva",
            "due_date": "2026-01-10",
            "details": {"what": "inicial"},
        }
    )

    service.atualizar_5w1h(occurrence_id, {"what": "atualizado"}, changed_by="user2")

    conn = sqlite3.connect(db)
    row = conn.execute("SELECT data_json FROM occurrences WHERE id = ?", (occurrence_id,)).fetchone()
    details = json.loads(row[0])
    assert details["what"] == "atualizado"

    history = conn.execute(
        "SELECT changed_by, note FROM occurrence_history WHERE occurrence_id = ? ORDER BY id DESC",
        (occurrence_id,),
    ).fetchone()
    conn.close()

    assert history[0] == "user2"
    assert history[1] == "Atualização 5W1H"


def test_anomalia_pendentes_vencidas_parse_data(tmp_path: Path):
    db = tmp_path / "test.db"
    repo = SQLiteRepository(db)
    repo.init_schema()
    service = AnomaliaService(repo)

    service.abrir(
        {
            "created_at": "2026-01-01T10:00:00",
            "opened_by": "user1",
            "machine": "M1",
            "problem": "Falha",
            "status": "Pendente Ação Corretiva",
            "due_date": "2026-01-01",
            "details": {},
        }
    )
    vencidas = service.pendentes_vencidas(date(2026, 1, 2))
    assert len(vencidas) == 1
