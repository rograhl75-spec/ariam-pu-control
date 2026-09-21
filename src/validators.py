"""Validações reutilizáveis de domínio."""

from __future__ import annotations

from pathlib import Path


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
