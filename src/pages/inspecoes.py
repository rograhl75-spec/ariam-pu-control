"""Página de inspeções."""

from datetime import datetime
import streamlit as st

from src.config import get_settings
from src.services.inspecao_service import InspecaoService
from src.storage.sqlite_repository import SQLiteRepository


def render() -> None:
    """Renderiza inspeção com múltiplas evidências."""
    st.header("📋 Inspeções")
    check_pesagem = st.checkbox("Pesagem conforme")
    check_reatividade = st.checkbox("Reatividade conforme")
    check_termico = st.checkbox("Térmico conforme")

    fotos = st.file_uploader(
        "Evidências fotográficas",
        type=["png", "jpg", "jpeg", "webp"],
        accept_multiple_files=True,
    )

    service = InspecaoService()
    status = service.avaliar_status(
        {
            "pesagem": check_pesagem,
            "reatividade": check_reatividade,
            "termico": check_termico,
        }
    )
    st.metric("Status geral", status)

    repo = SQLiteRepository(get_settings().db_path)
    repo.init_schema()
    if st.button("Salvar inspeção"):
        service.validar_uploads(fotos or [])
        repo.save_measurement(
            "inspecao",
            {
                "created_at": datetime.utcnow().isoformat(),
                "status": status,
                "fotos": [f.name for f in (fotos or [])],
            },
        )
        st.success("Inspeção salva")
