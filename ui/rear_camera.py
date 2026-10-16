"""Componente local de câmera usando o protocolo de componentes do Streamlit v1."""

import base64
import binascii
from io import BytesIO
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components


MAX_PHOTO_BYTES = 5 * 1024 * 1024
_component = components.declare_component(
    "rear_camera", path=str(Path(__file__).parent / "rear_camera")
)


def decode_capture(value, session: int):
    """Converte somente a captura da sessão ativa em um upload validável."""
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("Resposta inválida da câmera")
    if value.get("session") != session:
        return None
    if value.get("status") == "empty":
        return None
    if value.get("status") != "photo":
        raise ValueError("Captura indisponível. Tente novamente ou selecione 'Enviar arquivo'")
    data = value.get("data")
    prefix = "data:image/jpeg;base64,"
    if not isinstance(data, str) or not data.startswith(prefix):
        raise ValueError("Formato inválido da captura")
    encoded = data[len(prefix):]
    if len(encoded) > 4 * ((MAX_PHOTO_BYTES + 2) // 3):
        raise ValueError("Imagem excede tamanho máximo permitido")
    try:
        content = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("Conteúdo inválido da captura") from exc
    if not content or len(content) > MAX_PHOTO_BYTES:
        raise ValueError("Tamanho inválido da captura")
    upload = BytesIO(content)
    upload.name = "camera.jpg"
    return upload


def render_rear_camera(key: str, active: bool):
    state_key = f"{key}_camera_session"
    previous, session = st.session_state.get(state_key, (None, 0))
    if previous != active:
        session += 1
    st.session_state[state_key] = (active, session)
    value = _component(
        active=active, session=session, max_bytes=MAX_PHOTO_BYTES,
        key=f"{key}_rear_camera", default=None,
    )
    return decode_capture(value, session) if active else None
