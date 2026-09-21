"""Lógica de validação de reatividade."""

from __future__ import annotations


class ReatividadeService:
    """Valida ensaios de creme/gel e rastreabilidade."""

    def avaliar(self, tempo_creme: float, tempo_gel: float, limite_creme: tuple[float, float], limite_gel: tuple[float, float]) -> dict[str, str]:
        """Retorna status por parâmetro e geral."""
        creme_ok = limite_creme[0] <= tempo_creme <= limite_creme[1]
        gel_ok = limite_gel[0] <= tempo_gel <= limite_gel[1]
        geral = "conforme" if creme_ok and gel_ok else "fora de especificação"
        return {
            "status_creme": "ok" if creme_ok else "fora",
            "status_gel": "ok" if gel_ok else "fora",
            "status_geral": geral,
        }
