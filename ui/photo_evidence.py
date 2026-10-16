"""Entrada compartilhada de evidências por arquivo ou câmera."""

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps
import streamlit as st

from src.validators import validate_image_upload


FILE_SOURCE = "Enviar arquivo"
CAMERA_SOURCE = "Tirar foto / Usar câmera"


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
            normalized = ImageOps.exif_transpose(image).convert("RGB")
            output = BytesIO()
            normalized.save(output, format="PNG")
    except (OSError, Image.DecompressionBombError) as exc:
        raise ValueError("Não foi possível processar a imagem") from exc
    return Photo(name=f"{Path(upload.name).stem}.png", content=output.getvalue())


def select_photos(source, uploads, capture):
    """Seleciona somente a origem ativa, sem recorrer a uma imagem anterior."""
    if source == CAMERA_SOURCE:
        return [capture] if capture is not None else []
    if source == FILE_SOURCE:
        return uploads or []
    raise ValueError("Origem de foto inválida")


def render_photo_evidence(key: str, multiple: bool = False) -> list[Photo] | None:
    """Retorna fotos validadas; None indica erro que deve impedir o salvamento."""
    source = st.radio(
        "Origem da evidência fotográfica",
        [FILE_SOURCE, CAMERA_SOURCE],
        key=f"{key}_source",
        help="Somente a origem selecionada será salva. A outra será ignorada.",
    )
    uploads = st.file_uploader(
        "📁 Enviar Foto do Local / Equipamento",
        type=["jpg", "jpeg", "png", "webp"] if multiple else ["jpg", "jpeg", "png"],
        accept_multiple_files=multiple,
        key=f"{key}_upload",
    )
    st.info(
        "Para tirar foto, selecione 'Tirar foto / Usar câmera' e permita o acesso "
        "à câmera no navegador. É necessário HTTPS ou localhost no próprio dispositivo. "
        "Se a câmera não aparecer, estiver ocupada ou a permissão for negada, "
        "verifique as permissões do site e do sistema, feche outros aplicativos de câmera "
        "ou selecione 'Enviar arquivo'. Em HTTP por IP da rede, use o envio de arquivo."
    )
    capture = st.camera_input("📸 Tirar foto do Local / Equipamento", key=f"{key}_camera")
    files = uploads if multiple else ([uploads] if uploads is not None else [])
    selected = select_photos(source, files, capture)
    st.caption(f"Origem ativa: {source}. Somente as imagens desta origem serão anexadas.")
    if not selected:
        st.caption("Nenhuma foto selecionada na origem ativa. A inspeção será salva sem foto.")
    try:
        photos = [prepare_photo(photo) for photo in selected]
    except ValueError as exc:
        st.error(f"Foto inválida: {exc}. Remova ou substitua a imagem da origem ativa.")
        return None
    for photo in photos:
        st.image(photo.content, caption=f"Prévia da evidência: {photo.name}", width=320)
    return photos
