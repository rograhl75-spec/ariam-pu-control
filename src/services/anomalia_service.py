"""Serviço de gestão de anomalias e 5W1H."""

from __future__ import annotations

from datetime import date

from src.storage.base import StorageRepository


class AnomaliaService:
    """Orquestra abertura, atualização e vencimentos."""

    def __init__(self, repository: StorageRepository):
        self.repository = repository

    def abrir(self, payload: dict) -> str:
        """Abre nova anomalia com payload já validado."""
        return self.repository.create_occurrence(payload)

    def atualizar_5w1h(self, occurrence_id: str, details: dict, changed_by: str) -> None:
        """Atualiza detalhes da ocorrência e histórico."""
        self.repository.update_occurrence(
            occurrence_id,
            {
                "details": details,
                "changed_at": date.today().isoformat(),
                "changed_by": changed_by,
                "note": "Atualização 5W1H",
            },
        )

    def pendentes_vencidas(self, hoje: date) -> list[dict]:
        """Retorna ocorrências pendentes vencidas."""
        vencidas = []
        for item in self.repository.list_occurrences():
            due_date = item.get("due_date")
            if not due_date:
                continue
            if item.get("status", "").lower().startswith("concluído"):
                continue
            if due_date < hoje.isoformat():
                vencidas.append(item)
        return vencidas
