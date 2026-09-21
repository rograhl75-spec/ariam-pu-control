"""Automação de migração inicial de base legada para SQLite."""

from __future__ import annotations

from pathlib import Path
import pandas as pd

from src.config import get_settings
from src.services.processo_service import ProcessoService
from src.storage.sqlite_repository import SQLiteRepository
from src.weather_service import WeatherService


def gerar_base_processada(input_path: str | Path) -> pd.DataFrame:
    """Lê planilha legada, processa e devolve DataFrame calculado."""
    settings = get_settings()
    temp = WeatherService(settings.weather_latitude, settings.weather_longitude).get_temperature()
    df = pd.read_excel(input_path)
    return ProcessoService().process_dataframe(df, temperatura=temp)


def migrar_para_sqlite(input_path: str | Path) -> int:
    """Importa dados de processo para tabela de medições SQLite."""
    df = gerar_base_processada(input_path)
    repo = SQLiteRepository(get_settings().db_path)
    repo.init_schema()
    for _, row in df.iterrows():
        repo.save_measurement(
            "producao",
            {
                "created_at": pd.Timestamp.utcnow().isoformat(),
                **row.to_dict(),
            },
        )
    return len(df)


if __name__ == "__main__":
    origem = "Relatorio_Processo_Injecao_Atualizado.xlsx"
    total = migrar_para_sqlite(origem)
    print(f"{total} registros migrados para SQLite em {get_settings().db_path}")
