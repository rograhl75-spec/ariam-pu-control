"""Página principal."""

import streamlit as st


def render() -> None:
    """Renderiza menu de introdução."""
    st.title("🏭 ARIAM PU Control")
    st.info("Refatoração concluída: aplicação modular com serviços, SQLite e segurança via st.secrets.")
