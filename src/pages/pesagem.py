"""Página de pesagem."""

from datetime import datetime
import streamlit as st

from src.config import get_settings
from src.services.pesagem_service import PesagemService
from src.storage.sqlite_repository import SQLiteRepository


def render() -> None:
    """Renderiza formulário e histórico de pesagem."""
    st.header("⚖️ Pesagem")
    nominal = st.number_input("Massa nominal (g)", min_value=0.0, value=1000.0)
    real = st.number_input("Massa real (g)", min_value=0.0, value=1000.0)
    tolerancia = st.number_input("Tolerância (g)", min_value=1.0, value=50.0)

    status = PesagemService().classificar(nominal, real, tolerancia)
    st.metric("Status", status)

    repo = SQLiteRepository(get_settings().db_path)
    repo.init_schema()
    if st.button("Salvar registro"):
        repo.save_measurement(
            "pesagem",
            {
                "created_at": datetime.utcnow().isoformat(),
                "massa_nominal": nominal,
                "massa_real": real,
                "tolerancia": tolerancia,
                "status": status,
            },
        )
        st.success("Registro salvo")

    historico = repo.list_measurements("pesagem")
    if historico:
        st.line_chart([h["massa_real"] for h in historico][:20])
        st.dataframe(historico, use_container_width=True)
