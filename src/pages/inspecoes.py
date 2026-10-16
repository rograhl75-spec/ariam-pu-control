"""Página de inspeções."""

from datetime import datetime
from pathlib import Path
import streamlit as st

from src.config import get_settings
from src.services.inspecao_service import InspecaoService
from src.services.relatorio_service import RelatorioService
from src.storage.sqlite_repository import SQLiteRepository
from ui.photo_evidence import render_photo_evidence, reset_photo_evidence, save_photos


def render() -> None:
    """Renderiza inspeção com múltiplas evidências."""
    st.header("📋 Inspeções")
    check_pesagem = st.checkbox("Pesagem conforme")
    check_reatividade = st.checkbox("Reatividade conforme")
    check_termico = st.checkbox("Térmico conforme")

    fotos = render_photo_evidence("inspecao")

    service = InspecaoService()
    status = service.avaliar_status(
        {
            "pesagem": check_pesagem,
            "reatividade": check_reatividade,
            "termico": check_termico,
        }
    )
    st.metric("Status geral", status)

    db_path = Path(get_settings().db_path)
    repo = SQLiteRepository(db_path)
    repo.init_schema()
    if st.button("Salvar inspeção") and fotos is not None:
        caminhos = save_photos(fotos, db_path.parent / "fotos_inspecoes")
        repo.save_measurement(
            "inspecao",
            {
                "created_at": datetime.utcnow().isoformat(),
                "status": status,
                "fotos": [f.name for f in (fotos or [])],
                "foto_paths": caminhos,
            },
        )
        st.session_state["inspecao_laudo"] = RelatorioService().gerar_relatorio_inspecao(status, caminhos)
        reset_photo_evidence("inspecao")
        st.session_state["inspecao_salva"] = True
        st.rerun()
    if st.session_state.pop("inspecao_salva", False):
        st.success("Inspeção salva")
    if "inspecao_laudo" in st.session_state:
        st.download_button(
            "Baixar laudo da última inspeção",
            data=st.session_state["inspecao_laudo"],
            file_name="laudo_inspecao.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
