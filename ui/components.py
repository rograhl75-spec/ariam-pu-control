"""Componentes reutilizáveis de UI."""

import streamlit as st


def info_card(title: str, body: str) -> None:
    """Renderiza card informativo simples."""
    st.markdown(
        f"""
        <div style='border:1px solid #d0d7de;border-radius:8px;padding:12px;background:#f6f8fa;'>
            <h4 style='margin:0 0 6px 0'>{title}</h4>
            <p style='margin:0'>{body}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
