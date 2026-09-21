"""Contratos de persistência."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class StorageRepository(ABC):
    """Interface abstrata para persistência."""

    @abstractmethod
    def init_schema(self) -> None:
        """Inicializa schema persistente."""

    @abstractmethod
    def list_occurrences(self) -> list[dict[str, Any]]:
        """Lista ocorrências."""

    @abstractmethod
    def create_occurrence(self, payload: dict[str, Any]) -> str:
        """Cria ocorrência e retorna ID."""

    @abstractmethod
    def update_occurrence(self, occurrence_id: str, payload: dict[str, Any]) -> None:
        """Atualiza ocorrência existente."""

    @abstractmethod
    def save_measurement(self, category: str, payload: dict[str, Any]) -> None:
        """Persiste medição genérica de processo."""

    @abstractmethod
    def list_measurements(self, category: str) -> list[dict[str, Any]]:
        """Lista medições por categoria."""
