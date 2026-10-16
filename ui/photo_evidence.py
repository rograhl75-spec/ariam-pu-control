"""Entrada compartilhada de evidências por arquivo ou câmera."""

from dataclasses import dataclass
from io import BytesIO
import json
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageOps
import streamlit as st

from src.validators import validate_image_upload
from ui.rear_camera import MAX_PHOTO_BYTES, render_rear_camera


FILE_SOURCE = "Enviar arquivo"
CAMERA_SOURCE = "Tirar foto com câmera traseira"
MAX_PHOTOS = 20


@dataclass
class Photo:
    name: str
    content: bytes


def prepare_photo(upload) -> Photo:
    """Valida os bytes e normaliza orientação e formato para prévia e Word."""
    content = upload.getvalue()
    validate_image_upload(upload.name, len(content), content)
    try:
        with Image.open(BytesIO(content)) as image:
            if image.format not in {"JPEG", "PNG", "WEBP"}:
                raise ValueError("Formato de imagem inválido")
            normalized = ImageOps.exif_transpose(image)
            has_alpha = "A" in normalized.getbands() or "transparency" in normalized.info
            normalized = normalized.convert("RGBA" if has_alpha else "RGB")
            output = BytesIO()
            normalized.save(output, format="PNG")
    except (OSError, Image.DecompressionBombError) as exc:
        raise ValueError("Não foi possível processar a imagem") from exc
    if output.tell() > MAX_PHOTO_BYTES:
        raise ValueError("Imagem normalizada excede o limite de 5 MiB")
    return Photo(name=f"{Path(upload.name).stem}.png", content=output.getvalue())


def select_photos(source, uploads, capture):
    """Seleciona somente a origem ativa, sem recorrer a uma imagem anterior."""
    if source == CAMERA_SOURCE:
        return [capture] if capture is not None else []
    if source == FILE_SOURCE:
        return uploads or []
    raise ValueError("Origem de foto inválida")


def save_photos(photos: list[Photo], directory: Path) -> list[str]:
    """Persiste cada evidência com nome único, sem sobrescrever inspeções."""
    paths = []
    for photo in photos:
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{uuid4().hex}.png"
        path.write_bytes(photo.content)
        paths.append(str(path))
    return paths


def photo_paths(record) -> list[str]:
    """Lê a lista nova ou o caminho único das inspeções antigas."""
    raw = record.get("Foto_Paths")
    if isinstance(raw, str) and raw:
        return json.loads(raw)
    legacy = record.get("Foto_Path")
    return [legacy] if isinstance(legacy, str) and legacy else []


def _reset_camera(key: str) -> None:
    active, session = st.session_state.get(f"{key}_camera_session", (None, 0))
    st.session_state[f"{key}_camera_session"] = (active, session + 1)


def reset_photo_evidence(key: str) -> None:
    """Inicia uma coleção vazia e invalida os controles de entrada antigos."""
    st.session_state[f"{key}_photos"] = []
    st.session_state[f"{key}_upload_revision"] = st.session_state.get(f"{key}_upload_revision", 0) + 1
    _reset_camera(key)


def render_photo_evidence(key: str) -> list[Photo] | None:
    """Retorna fotos validadas; None indica erro que deve impedir o salvamento."""
    photos = st.session_state.setdefault(f"{key}_photos", [])
    st.caption(f"Evidências anexadas: {len(photos)}/{MAX_PHOTOS}. Limite de 5 MiB por imagem, inclusive após conversão para PNG.")
    for index, photo in enumerate(photos):
        st.image(photo.content, caption=f"Evidência {index + 1}: {photo.name}", width=240)
        if st.button(f"Remover foto {index + 1}", key=f"{key}_remove_{index}"):
            photos.pop(index)
            st.rerun()
    if st.button("Limpar evidências", key=f"{key}_clear", disabled=not photos):
        reset_photo_evidence(key)
        st.rerun()

    source = st.radio(
        "Origem da evidência fotográfica",
        [FILE_SOURCE, CAMERA_SOURCE],
        key=f"{key}_source",
        help="A origem selecionada adiciona novas fotos. As evidências já anexadas são mantidas.",
    )
    revision = st.session_state.get(f"{key}_upload_revision", 0)
    uploads = st.file_uploader(
        "📁 Enviar Fotos do Local / Equipamento",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        key=f"{key}_upload_{revision}",
        disabled=source != FILE_SOURCE,
    )
    st.info(
        "Para tirar foto, selecione 'Tirar foto com câmera traseira' e permita o acesso "
        "à câmera no navegador. É necessário HTTPS ou localhost no próprio dispositivo. "
        "Se a câmera não aparecer, estiver ocupada ou a permissão for negada, "
        "verifique as permissões do site e do sistema, feche outros aplicativos de câmera "
        "ou selecione 'Enviar arquivo'. Em HTTP por IP da rede, use o envio de arquivo."
    )
    st.caption(
        "Capture ou selecione arquivos e toque em 'Adicionar evidências à inspeção'. "
        "Depois continue capturando ou enviando arquivos; revise a galeria antes de salvar."
    )
    if len(photos) >= MAX_PHOTOS:
        st.warning(f"Limite de {MAX_PHOTOS} fotos atingido. Remova fotos antes de capturar ou adicionar novas.")
    try:
        capture = render_rear_camera(key, active=source == CAMERA_SOURCE and len(photos) < MAX_PHOTOS)
        selected = select_photos(source, uploads, capture)
        if st.button("Adicionar evidências à inspeção", key=f"{key}_add", disabled=not selected):
            if len(photos) + len(selected) > MAX_PHOTOS:
                raise ValueError(f"Máximo de {MAX_PHOTOS} fotos. Remova fotos ou selecione menos arquivos")
            prepared = [prepare_photo(photo) for photo in selected]
            photos.extend(prepared)
            if source == FILE_SOURCE:
                st.session_state[f"{key}_upload_revision"] = revision + 1
            else:
                _reset_camera(key)
            st.rerun()
    except ValueError as exc:
        st.error(f"Foto inválida: {exc}. Remova ou substitua a imagem da origem ativa.")
        return None
    if selected:
        st.warning("Há fotos pendentes. Adicione-as à inspeção ou descarte a seleção antes de salvar.")
        return None
    if not photos:
        st.caption("Nenhuma evidência anexada. A inspeção será salva sem foto.")
    return list(photos)
