"""Serviço de inspeções com evidências."""

from __future__ import annotations

from src.validators import validate_image, validate_image_upload


class InspecaoService:
    """Controla inspeções semanais e status automático."""

    def avaliar_status(self, itens: dict[str, bool]) -> str:
        """Retorna status geral com base nos checks individuais."""
        return "conforme" if all(itens.values()) else "pendente"

    def validar_evidencias(self, caminhos: list[str]) -> None:
        """Valida todas as imagens anexadas na inspeção."""
        for caminho in caminhos:
            validate_image(caminho)

    def validar_uploads(self, arquivos: list) -> None:
        """Valida uploads recebidos pelo `st.file_uploader`."""
        for arquivo in arquivos:
            validate_image_upload(arquivo.name, arquivo.size, arquivo.getvalue())
