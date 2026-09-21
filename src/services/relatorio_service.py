"""Serviço de geração de relatórios Word."""

from __future__ import annotations

import io
from docx import Document


class RelatorioService:
    """Gera relatórios DOCX executivos simples."""

    def gerar_relatorio_ocorrencia(self, titulo: str, secoes: dict[str, str]) -> bytes:
        """Gera conteúdo de relatório em bytes."""
        doc = Document()
        doc.add_heading(titulo, level=1)
        for secao, conteudo in secoes.items():
            doc.add_heading(secao, level=2)
            doc.add_paragraph(conteudo)

        buffer = io.BytesIO()
        doc.save(buffer)
        return buffer.getvalue()
