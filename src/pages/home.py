"""Página principal."""

import streamlit as st
from ui.components import info_card


def render() -> None:
    """Renderiza menu de introdução."""
    st.title("🏭 ARIAM PU Control")
    info_card("Refatoração concluída", "Aplicação modular com serviços, SQLite e segurança via st.secrets.")
