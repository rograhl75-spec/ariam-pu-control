"""Planilha sintética no formato 59001000100_Parametros_e_Massas_PU_RevNN.

Todos os valores são fictícios: não coloque dados reais de processo aqui (repositório público).
"""

from __future__ import annotations

from pathlib import Path

import openpyxl

NOME = "59001000100_Parametros_e_Massas_PU_Rev03_2026-11-13.xlsx"
# Mesmo rótulo do regime padrão do app; o percentual na planilha de teste é fictício.
REGIME = "n-Pentano 9,15% (provisório)"


def criar_planilha_teste(pasta: Path, nome: str = NOME) -> Path:
    wb = openpyxl.Workbook()
    wb.active.title = "Capa"
    p = wb.create_sheet("Parâmetros")
    p["D8"], p["E8"], p["F8"] = "Ciclopentano (oficial)", "n-Pentano 9% (provisório)", REGIME
    p["D10"], p["E10"], p["F10"] = 0.10, 0.09, 0.08
    p["D11"], p["D12"], p["D29"] = 1.30, 0.02, "20 ± 2"
    linhas = [
        ("Vazão", "g/s", 600, 2500, "± 20"),
        ("Pressão de injeção", "bar", 120, 120, "± 5"),
        ("Temperatura dos moldes", "°C", 40, 40, "± 3"),
        ("Tempo de creme", "s", "3–7", "3–7", "—"),
        ("Pega livre", "s", "60–80", "60–80", "—"),
        ("Densidade livre", "kg/m³", "21,0–23,0", "20,0–22,5", "—"),
        ("Resistência à compressão — mínimo", "kPa", 100, 100, "mínimo"),
        ("Vazamento (perda por injeção)", "% da massa", 0.02, 0.02, "—"),
        ("Temperatura das estufas", "°C", "35–40", "35–40", "—"),
    ]
    for r, (rot, un, c1, c2, tol) in enumerate(linhas, start=36):
        p[f"B{r}"], p[f"C{r}"], p[f"D{r}"], p[f"E{r}"], p[f"F{r}"] = rot, un, c1, c2, tol
    m = wb.create_sheet("Massas")
    itens = [
        ("Ativo", 1, "F01 TESTE", "22mm CABECEIRA", "59000000001", "CABECEIRA TESTE A", 0.01, 46.2, 1.08, 0.97),
        ("Ativo", 1, "F01 TESTE", "TANQUE 1", "59000000002", "TANQUE TESTE B", 0.023, 40.5, 1.03, 0.97),
        ("Ativo", 2, "F01 TESTE", "CAIXA", "EK000001", "KIT TESTE C", 0.242128512624, 40, 1.03, "=0.96-150/1000/I8"),
        ("Obsoleto", 2, "F01 TESTE", "CAIXA", "EK000002", "KIT FORA DE LINHA", 0.1, 40, 1.03, 0.97),
    ]
    for r, it in enumerate(itens, start=6):
        status, cab, expo, comp, cod, desc, vol, dens, ff, fc = it
        for c, v in zip((1, 2, 3, 4, 5, 6, 7, 8, 10, 12), (status, cab, expo, comp, cod, desc, vol, dens, ff, fc)):
            m.cell(r, c, v)
        m.cell(r, 9, f"=G{r}*H{r}")
    destino = Path(pasta) / nome
    wb.save(destino)
    return destino
