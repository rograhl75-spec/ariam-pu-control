"""Adapter legado para leitura inicial de planilhas."""

from __future__ import annotations

from pathlib import Path
import pandas as pd


class ExcelRepository:
    """Leitor simples para suportar migração legada."""

    @staticmethod
    def read(path: str | Path) -> pd.DataFrame:
        """Lê planilha Excel em DataFrame."""
        return pd.read_excel(path)
