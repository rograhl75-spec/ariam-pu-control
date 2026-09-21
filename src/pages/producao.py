"""Página de produção."""

import streamlit as st
import pandas as pd

from src.config import get_settings
from src.services.processo_service import ProcessoService
from src.weather_service import WeatherService
from src.validators import REQUIRED_PROCESS_COLUMNS, validate_required_columns


def render() -> None:
    """Renderiza cálculos de produção com busca textual."""
    st.header("⚙️ Produção")
    uploaded = st.file_uploader("Base de produção (.xlsx)", type=["xlsx"])
    if not uploaded:
        st.info("Envie uma planilha para processar dados de produção.")
        return

    df = pd.read_excel(uploaded)
    validate_required_columns(list(df.columns), REQUIRED_PROCESS_COLUMNS)

    termo = st.text_input("Busca textual (código/descrição)")
    if termo and {"Codigo_Item", "Descricao"}.issubset(df.columns):
        mask = df["Codigo_Item"].astype(str).str.contains(termo, case=False, na=False) | df["Descricao"].astype(str).str.contains(termo, case=False, na=False)
        df = df.loc[mask]

    settings = get_settings()
    temp = WeatherService(settings.weather_latitude, settings.weather_longitude).get_temperature()
    out = ProcessoService().process_dataframe(df, temperatura=temp)
    st.caption(f"Temperatura externa: {temp:.1f}°C")
    st.dataframe(out, use_container_width=True)
