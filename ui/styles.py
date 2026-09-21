"""Estilos centralizados de UI."""

import streamlit as st


BASE_STYLE = """
<style>
:root { --ariam-primary: #1f4e78; }
h1, h2, h3 { color: var(--ariam-primary); }
</style>
"""


def apply_base_style() -> None:
    """Aplica CSS base da aplicação."""
    st.markdown(BASE_STYLE, unsafe_allow_html=True)
