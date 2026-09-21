"""Novo entry point modular do ARIAM PU Control."""

from src.pages import anomalias, home, inspecoes, pesagem, producao, reatividade, termico
from src.config import get_settings

import streamlit as st


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
