"""Lógica de pesagem e classificação por tolerância."""

from __future__ import annotations


class PesagemService:
    """Valida massa real contra massa nominal."""

    def classificar(self, massa_nominal: float, massa_real: float, tolerancia: float) -> str:
        """Classifica conforme, alerta e crítico."""
        desvio = abs(massa_real - massa_nominal)
        if desvio <= tolerancia:
            return "conforme"
        if desvio <= tolerancia * 2:
            return "alerta"
        return "crítico"
