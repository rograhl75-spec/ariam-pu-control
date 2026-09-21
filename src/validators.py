"""Validações reutilizáveis de domínio."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from PIL import Image


REQUIRED_PROCESS_COLUMNS = {"Codigo_Item", "Descricao", "Volume", "Massa_Nominal"}


def validate_required_columns(columns: list[str] | set[str], required: set[str]) -> None:
    """Valida presença de colunas obrigatórias."""
    missing = sorted(required.difference(set(columns)))
    if missing:
        raise ValueError(f"Colunas obrigatórias ausentes: {', '.join(missing)}")


def validate_image(path: str, max_size_bytes: int = 5 * 1024 * 1024) -> None:
    """Valida arquivo de imagem por extensão e tamanho."""
    file_path = Path(path)
    if file_path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise ValueError("Formato de imagem inválido")
    if file_path.exists() and file_path.stat().st_size > max_size_bytes:
        raise ValueError("Imagem excede tamanho máximo permitido")


def validate_image_upload(
    file_name: str,
    file_size: int,
    file_content: bytes,
    max_size_bytes: int = 5 * 1024 * 1024,
) -> None:
    """Valida upload de imagem por extensão e tamanho em memória."""
    suffix = Path(file_name).suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise ValueError("Formato de imagem inválido")
    if file_size > max_size_bytes:
        raise ValueError("Imagem excede tamanho máximo permitido")
    try:
        image = Image.open(BytesIO(file_content))
        image.verify()
    except Exception as exc:  # noqa: BLE001
        raise ValueError("Conteúdo de imagem inválido") from exc
