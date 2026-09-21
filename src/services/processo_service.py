"""Serviço de cálculos técnicos de produção."""

from __future__ import annotations

import pandas as pd

from src.validators import REQUIRED_PROCESS_COLUMNS, validate_required_columns


class ProcessoService:
    """Calcula massas, densidade e recomendações de processo."""

    def process_dataframe(self, df: pd.DataFrame, temperatura: float) -> pd.DataFrame:
        """Processa base de itens e devolve parâmetros calculados."""
        validate_required_columns(list(df.columns), REQUIRED_PROCESS_COLUMNS)

        out = df.copy()
        out["Volume"] = pd.to_numeric(out["Volume"], errors="coerce")
        out["Massa_Nominal"] = pd.to_numeric(out["Massa_Nominal"], errors="coerce")
        out["Massa_Frio"] = pd.to_numeric(out.get("Massa_Frio", out["Massa_Nominal"]), errors="coerce").fillna(
            out["Massa_Nominal"]
        )
        out["Massa_Calor"] = pd.to_numeric(out.get("Massa_Calor", out["Massa_Nominal"]), errors="coerce").fillna(
            out["Massa_Nominal"]
        )

        if temperatura < 22:
            out["Massa_Trabalho"] = out["Massa_Frio"]
            out["Condicao_Climatica"] = "FRIO"
            recomendacao = "Aumentar atenção a overpacking"
        elif temperatura > 28:
            out["Massa_Trabalho"] = out["Massa_Calor"]
            out["Condicao_Climatica"] = "CALOR"
            recomendacao = "Ajustar para evitar underpacking"
        else:
            out["Massa_Trabalho"] = out["Massa_Nominal"]
            out["Condicao_Climatica"] = "NOMINAL"
            recomendacao = "Manter setpoint padrão"

        out["Densidade_Real_Calculada"] = out["Massa_Trabalho"] / out["Volume"]
        out["Alerta_Densidade"] = out["Densidade_Real_Calculada"].apply(
            lambda v: "CRÍTICO" if v < 0.10 or v > 0.80 else "OK"
        )
        out["Recomendacao_Climatica"] = recomendacao
        return out
