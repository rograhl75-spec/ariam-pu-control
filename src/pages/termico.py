"""Página de controle térmico."""

from datetime import datetime
import streamlit as st

from src.config import get_settings
from src.services.termico_service import TermicoService
from src.storage.sqlite_repository import SQLiteRepository


def render() -> None:
    """Renderiza formulário térmico com limites por equipamento."""
    st.header("🌡️ Controle Térmico")
    equipamento = st.text_input("Equipamento", value="Molde A")
    minimo = st.number_input("Limite mínimo", value=40.0)
    maximo = st.number_input("Limite máximo", value=55.0)
    temperatura = st.number_input("Temperatura atual", value=45.0)

    resultado = TermicoService().avaliar(equipamento, temperatura, minimo, maximo)
    st.metric("Status", resultado["status"])

    repo = SQLiteRepository(get_settings().db_path)
    repo.init_schema()
    if st.button("Salvar medição"):
        repo.save_measurement(
            "termico",
            {
                "created_at": datetime.utcnow().isoformat(),
                **resultado,
                "minimo": minimo,
                "maximo": maximo,
            },
        )
        st.success("Medição salva")

    historico = repo.list_measurements("termico")
    if historico:
        st.line_chart([h["temperatura"] for h in historico][:20])
