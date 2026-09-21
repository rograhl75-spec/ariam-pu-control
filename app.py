"""Novo entry point modular do ARIAM PU Control."""

import os

from src.pages import anomalias, home, inspecoes, pesagem, producao, reatividade, termico
from src.config import get_settings

import streamlit as st


def _apply_base_style() -> None:
    """Aplica estilo visual mínimo compatível com o layout legado."""
    st.markdown(
        """
        <style>
            [data-testid="stSidebar"] {
                min-width: 250px !important;
                max-width: 250px !important;
            }
            .block-container {
                padding-top: 1.2rem;
                padding-left: 1.4rem;
                padding-right: 1.4rem;
            }
            .modular-header h1 {
                margin: 0;
                color: #1F4E78;
                line-height: 1.2;
                font-size: clamp(1.35rem, 2.2vw, 2rem);
                text-align: center;
            }
            .modular-header p {
                margin: 0.35rem 0 0 0;
                color: #4a4a4a;
                font-weight: 600;
                text-align: center;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_modular_header() -> None:
    """Renderiza cabeçalho simples e estável para o app modular."""
    col_logo, col_titulo = st.columns([1, 5], gap="medium")
    with col_logo:
        logo_path = "logo.jpg" if os.path.exists("logo.jpg") else ("logo.png" if os.path.exists("logo.png") else None)
        if logo_path:
            st.image(logo_path, width=120)
    with col_titulo:
        st.markdown(
            """
            <div class="modular-header">
                <h1>ARIAM PU 4.0 - Assistente Técnico de Campo</h1>
                <p>Grahl Consultoria e Treinamentos | Gestão de Injeção, Reologia e Qualidade</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("---")


def _ensure_login() -> bool:
    """Garante autenticação básica via `st.secrets` já hashada."""
    settings = get_settings(require_users=True)
    st.session_state.setdefault("role", "operador")

    if st.session_state.get("authenticated"):
        return True

    st.title("🔒 ARIAM PU Control")
    username = st.text_input("Usuário")
    raw_secret = st.text_input("Senha", type="password")
    if st.button("Entrar", use_container_width=True):
        from src.auth_service import AuthService

        auth = AuthService(settings.users)
        result = auth.authenticate(username, raw_secret)
        if result.authenticated:
            st.session_state["authenticated"] = True
            st.session_state["username"] = username
            st.session_state["role"] = result.role
            st.rerun()
        else:
            st.error("Credenciais inválidas")
    return False


def main() -> None:
    """Inicializa a aplicação principal modular."""
    st.set_page_config(page_title="ARIAM PU Control", page_icon="🏭", layout="wide")
    if not _ensure_login():
        return

    _apply_base_style()
    _render_modular_header()

    st.sidebar.title("ARIAM PU Control")
    st.sidebar.caption(f"Usuário: {st.session_state.get('username', 'N/A')}")
    menu = st.sidebar.radio(
        "Módulos",
        [
            "Home",
            "Produção",
            "Pesagem",
            "Reatividade",
            "Térmico",
            "Inspeções",
            "Anomalias",
        ],
    )

    if menu == "Home":
        home.render()
    elif menu == "Produção":
        producao.render()
    elif menu == "Pesagem":
        pesagem.render()
    elif menu == "Reatividade":
        reatividade.render()
    elif menu == "Térmico":
        termico.render()
    elif menu == "Inspeções":
        inspecoes.render()
    else:
        anomalias.render()


if __name__ == "__main__":
    main()
