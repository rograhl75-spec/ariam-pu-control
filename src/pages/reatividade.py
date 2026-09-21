"""Página de reatividade."""

from datetime import datetime
import streamlit as st

from src.config import get_settings
from src.services.reatividade_service import ReatividadeService
from src.storage.sqlite_repository import SQLiteRepository


def render() -> None:
    """Renderiza avaliação de creme/gel por lote e cabeçote."""
    st.header("🧪 Reatividade")
    lote = st.text_input("Lote")
    materia_prima = st.text_input("Matéria-prima")
    cabecote = st.text_input("Cabeçote", value="CAB-1")
    tempo_creme = st.number_input("Tempo de creme (s)", min_value=0.0, value=15.0)
    tempo_gel = st.number_input("Tempo de gel (s)", min_value=0.0, value=55.0)

    limite_creme = (10.0, 25.0)
    limite_gel = (40.0, 70.0)
    resultado = ReatividadeService().avaliar(tempo_creme, tempo_gel, limite_creme, limite_gel)
    st.write(resultado)

    repo = SQLiteRepository(get_settings().db_path)
    repo.init_schema()
    if st.button("Salvar ensaio"):
        repo.save_measurement(
            "reatividade",
            {
                "created_at": datetime.utcnow().isoformat(),
                "lote": lote,
                "materia_prima": materia_prima,
                "cabecote": cabecote,
                "tempo_creme": tempo_creme,
                "tempo_gel": tempo_gel,
                **resultado,
            },
        )
        st.success("Ensaio salvo")
