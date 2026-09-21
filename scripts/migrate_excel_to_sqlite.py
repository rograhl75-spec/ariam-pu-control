"""Script de migração de logs legados XLSX para SQLite."""

from __future__ import annotations

from pathlib import Path
import pandas as pd

from src.config import get_settings
from src.storage.sqlite_repository import SQLiteRepository


LEGACY_FILES = {
    "pesagem": "Log_Controle_Pesagem_Campo.xlsx",
    "reatividade": "Log_Controle_Reatividade_DOC0001.xlsx",
    "anomalia_legado": "Log_Registro_Anomalias.xlsx",
}


def run_migration(base_path: Path) -> dict[str, int]:
    """Migra planilhas legadas para medições SQLite."""
    repo = SQLiteRepository(get_settings().db_path)
    repo.init_schema()
    summary: dict[str, int] = {}

    for category, filename in LEGACY_FILES.items():
        path = base_path / filename
        if not path.exists():
            summary[category] = 0
            continue

        df = pd.read_excel(path)
        count = 0
        for _, row in df.iterrows():
            repo.save_measurement(
                category,
                {
                    "created_at": pd.Timestamp.utcnow().isoformat(),
                    **row.to_dict(),
                },
            )
            count += 1
        summary[category] = count

    return summary


if __name__ == "__main__":
    summary_result = run_migration(Path("."))
    for category, count in summary_result.items():
        print(f"{category}: {count}")
