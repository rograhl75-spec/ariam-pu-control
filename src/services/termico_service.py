"""Lógica de controle térmico."""

from __future__ import annotations


class TermicoService:
    """Avalia temperatura por equipamento."""

    def avaliar(self, equipamento: str, temperatura: float, minimo: float, maximo: float) -> dict[str, str | float]:
        """Retorna avaliação de status térmico."""
        if temperatura < minimo:
            status = "abaixo"
        elif temperatura > maximo:
            status = "acima"
        else:
            status = "normal"
        return {"equipamento": equipamento, "temperatura": temperatura, "status": status}
