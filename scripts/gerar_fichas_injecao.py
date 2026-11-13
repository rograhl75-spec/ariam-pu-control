"""Gera as fichas de injeção (PDF) dos cabeçotes a partir da planilha controlada
59001000100_Parametros_e_Massas_PU_RevNN_AAAA-MM-DD.xlsx.

Uso:
    python scripts/gerar_fichas_injecao.py PLANILHA.xlsx --saida PASTA \
        --regime "n-Pentano 9,15% (provisório)" --regime-desde 16/10/2026

A planilha precisa ter os valores calculados gravados (abra e salve no Excel,
ou deixe o script recalcular com o LibreOffice, se instalado). Nenhum valor de
processo fica no código: massas, faixas e textos vêm da planilha.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import tempfile
from collections import defaultdict
from pathlib import Path

import openpyxl
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepTogether,
    LongTable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

AZUL = colors.HexColor("#1F3A5F")
AZUL_CLARO = colors.HexColor("#E8EEF6")
FAIXA = colors.HexColor("#DCE6F2")
AMARELO = colors.HexColor("#FFF4CE")
AMARELO_BORDA = colors.HexColor("#C9A227")
CINZA = colors.HexColor("#5B6573")
LINHA = colors.HexColor("#C9D2DE")

FONTES = [
    ("Ficha", "/usr/share/fonts/truetype/crosextra/Carlito-Regular.ttf"),
    ("Ficha-Bold", "/usr/share/fonts/truetype/crosextra/Carlito-Bold.ttf"),
]


def _registrar_fontes() -> tuple[str, str]:
    if all(Path(p).exists() for _, p in FONTES):
        for nome, caminho in FONTES:
            pdfmetrics.registerFont(TTFont(nome, caminho))
        registerFontFamily("Ficha", normal="Ficha", bold="Ficha-Bold", italic="Ficha", boldItalic="Ficha-Bold")
        return "Ficha", "Ficha-Bold"
    return "Helvetica", "Helvetica-Bold"


def _num(v: float, casas: int = 3) -> str:
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _pct(v: float) -> str:
    return _num(v * 100, 2) + "%"


def _carregar(planilha: Path) -> openpyxl.Workbook:
    wb = openpyxl.load_workbook(planilha, data_only=True)
    if wb["Massas"]["I6"].value is not None:
        return wb
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        raise SystemExit("A planilha não tem valores calculados. Abra e salve no Excel e rode de novo.")
    tmp = Path(tempfile.mkdtemp())
    subprocess.run([soffice, "--headless", "--convert-to", "xlsx", "--outdir", str(tmp), str(planilha)],
                   check=True, capture_output=True)
    return openpyxl.load_workbook(tmp / planilha.name, data_only=True)


def _revisao(planilha: Path, wb: openpyxl.Workbook) -> tuple[str, str]:
    m = re.search(r"Rev(\d+)_(\d{4})-(\d{2})-(\d{2})", planilha.name)
    if not m:
        raise SystemExit("Nome fora do padrão ..._RevNN_AAAA-MM-DD.xlsx")
    return f"Rev. {m.group(1)}", f"{m.group(4)}/{m.group(3)}/{m.group(2)}"


def _parametros(wb, regime: str) -> dict:
    p = wb["Parâmetros"]
    cab_col = {1: "D", 2: "E"}
    regimes = {p[f"{c}8"].value: c for c in "DEF"}
    if regime not in regimes:
        raise SystemExit(f"Regime '{regime}' não encontrado. Opções: {', '.join(regimes)}")
    rc = regimes[regime]

    def linha(rotulo: str) -> int:
        for r in range(36, 49):
            if (p[f"B{r}"].value or "").strip().lower() == rotulo.lower():
                return r
        raise SystemExit(f"Linha '{rotulo}' não encontrada na seção 3 da aba Parâmetros")

    out = {"regime_pct": p[f"{rc}10"].value, "iso": p[f"{rc}20"].value, "poliol": p[f"{rc}21"].value,
           "agente": p[f"{rc}22"].value, "rel": p["D11"].value, "rel_min": p["D13"].value,
           "rel_max": p["D14"].value, "rel_tol": p["D12"].value, "tanques": p["D29"].value,
           "cab": {}}
    for cab, col in cab_col.items():
        g = {}
        for chave, rotulo in [("vazao", "Vazão"), ("pressao", "Pressão de injeção"),
                              ("t_moldes", "Temperatura dos moldes"), ("t_pecas", "Temperatura das peças"),
                              ("creme", "Tempo de creme"), ("gel", "Tempo de gel"), ("pega", "Pega livre"),
                              ("dens", "Densidade livre"), ("cura", "Tempo de cura / desmolde"),
                              ("vazamento", "Vazamento (perda por injeção)"),
                              ("estufas", "Temperatura das estufas")]:
            try:
                r = linha(rotulo)
            except SystemExit:
                g[chave] = None
                continue
            g[chave] = (p[f"{col}{r}"].value, p[f"F{r}"].value)
        out["cab"][cab] = g
    return out


def _itens(wb, cab: int) -> dict[str, list[tuple]]:
    m = wb["Massas"]
    grupos: dict[str, list[tuple]] = defaultdict(list)
    for r in range(6, m.max_row + 1):
        status, c = m.cell(r, 1).value, m.cell(r, 2).value
        if status != "Ativo" or c != cab:
            continue
        grupos[str(m.cell(r, 4).value).strip()].append(
            (str(m.cell(r, 3).value).strip(), str(m.cell(r, 5).value).strip(), str(m.cell(r, 6).value).strip(),
             m.cell(r, 9).value, m.cell(r, 11).value, m.cell(r, 13).value, m.cell(r, 22).value))
    return {k: sorted(v, key=lambda t: (t[0], t[1])) for k, v in sorted(grupos.items())}


def gerar(planilha: Path, saida: Path, regime: str, desde: str, mudancas: str) -> list[Path]:
    fonte, negrito = _registrar_fontes()
    wb = _carregar(planilha)
    rev, data = _revisao(planilha, wb)
    prm = _parametros(wb, regime)
    agente_nome = regime.split(" (")[0]
    provisorio = "provisório" in regime.lower()

    est = {n: ParagraphStyle(n, fontName=fonte, fontSize=8.2, leading=10.5, textColor=colors.black)
           for n in ("txt", "cel")}
    est["titulo"] = ParagraphStyle("titulo", fontName=negrito, fontSize=15, leading=18, textColor=AZUL)
    est["sub"] = ParagraphStyle("sub", fontName=fonte, fontSize=8.8, leading=11, textColor=CINZA)
    est["sec"] = ParagraphStyle("sec", fontName=negrito, fontSize=11, leading=14, textColor=AZUL,
                                spaceBefore=6, spaceAfter=4)
    est["k"] = ParagraphStyle("k", fontName=negrito, fontSize=8, leading=10)
    est["th"] = ParagraphStyle("th", fontName=negrito, fontSize=8, leading=9.5, textColor=colors.white)
    est["thr"] = ParagraphStyle("thr", parent=est["th"], alignment=2)

    arquivos = []
    for cab in (1, 2):
        g = prm["cab"][cab]
        nome_cab = "Cabeçote 1 (RFG)" if cab == 1 else "Cabeçote 2"
        grupos = _itens(wb, cab)
        n_itens = sum(len(v) for v in grupos.values())
        destino = saida / f"59001000100_Ficha_Injecao_Cab{cab}_{rev.replace('. ', '')}_{planilha.stem[-10:]}.pdf"

        def faixa(par):
            v, tol = par
            v = _num(v, 0) if isinstance(v, (int, float)) and v >= 1000 else (
                str(v).replace(".", ",") if isinstance(v, float) else str(v))
            return v, tol

        vaz, vaz_tol = faixa(g["vazao"])
        pres, pres_tol = faixa(g["pressao"])
        linhas_par = [
            ("Agente expansor", f"<b>{agente_nome}</b> na pré-mistura" + (" (provisório)" if provisorio else ""),
             "Temperatura moldes / peças",
             f"{g['t_moldes'][0]} °C ({g['t_moldes'][1]}) / {g['t_pecas'][0]} °C ({g['t_pecas'][1]})"),
            ("Relação i/p (iso / pré-mistura)",
             f"{_num(prm['rel'], 3)} (mín. {_num(prm['rel_min'], 3)} — máx. {_num(prm['rel_max'], 3)}; "
             f"± {_num(prm['rel_tol'] * 100, 1)}%)",
             "Tempo de creme / gel / pega livre", f"{g['creme'][0]} s / {g['gel'][0]} s / {g['pega'][0]} s"),
            ("Vazão", f"{vaz} g/s ({vaz_tol} g/s)", "Densidade livre", f"{g['dens'][0]} kg/m³"),
            ("Pressão de injeção", f"{pres} bar ({pres_tol})", "Tempo de cura / desmolde", f"{g['cura'][0]} min"),
            ("Temperatura tanques / cabeçote", f"{prm['tanques']} °C", "Vazamento considerado",
             f"{_num(g['vazamento'][0] * 100, 0)}% da massa"),
        ]
        if g.get("estufas"):
            linhas_par.append(("Temperatura das estufas", f"{g['estufas'][0]} °C", "", ""))

        def topo(canvas, doc):
            canvas.saveState()
            w, h = landscape(A4)
            canvas.setFillColor(AZUL)
            canvas.rect(0, h - 11 * mm, w, 11 * mm, stroke=0, fill=1)
            canvas.setFillColor(colors.white)
            canvas.setFont(negrito, 9)
            canvas.drawString(12 * mm, h - 7 * mm, f"ARIAM LONDRINA · FICHA DE INJEÇÃO — {nome_cab.upper()}")
            canvas.setFont(fonte, 8.5)
            canvas.drawRightString(w - 12 * mm, h - 7 * mm, f"Doc. 59001000100 · {rev} — {data}")
            canvas.setFillColor(CINZA)
            canvas.setFont(fonte, 7.2)
            canvas.drawString(12 * mm, 7 * mm, f"Fonte: {planilha.name} · Cópia controlada — confira se esta é "
                                               "a revisão vigente antes de usar.")
            canvas.drawRightString(w - 12 * mm, 7 * mm, f"Página {doc.page}")
            canvas.restoreState()

        doc = SimpleDocTemplate(str(destino), pagesize=landscape(A4), leftMargin=12 * mm, rightMargin=12 * mm,
                                topMargin=17 * mm, bottomMargin=13 * mm,
                                title=f"Ficha de injeção — {nome_cab} — {rev}", author="Grahl Consultoria")
        larg = landscape(A4)[0] - 24 * mm
        hist = []
        hist.append(Paragraph(f"Ficha de injeção — {nome_cab}", est["titulo"]))
        hist.append(Paragraph(f"Isolamento espumado · poliuretano rígido VORACOR™ CR 2610 + CE 164 · "
                              f"{n_itens} itens ativos · {rev} — {data}", est["sub"]))
        hist.append(Spacer(1, 5))
        if provisorio:
            aviso = Table([[Paragraph(
                f"<b>ATENÇÃO — AGENTE EXPANSOR EM USO: {agente_nome.upper()} na pré-mistura</b> (uso provisório "
                f"desde {desde}, por falta de ciclopentano). O padrão oficial é o ciclopentano 9,71%; ao retornar "
                "ao ciclopentano, esta ficha deve ser substituída e as faixas de reatividade e densidade livre "
                "revalidadas. As massas de injeção e a relação i/p são as mesmas nos dois regimes.", est["txt"])]],
                colWidths=[larg])
            aviso.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), AMARELO),
                                       ("BOX", (0, 0), (-1, -1), 0.8, AMARELO_BORDA),
                                       ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 4),
                                       ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
            hist.append(aviso)
        hist.append(Paragraph("1. Parâmetros de máquina", est["sec"]))
        dados = [[Paragraph(a, est["k"]), Paragraph(b, est["txt"]), "", Paragraph(c, est["k"]),
                  Paragraph(d, est["txt"])] for a, b, c, d in linhas_par]
        cw = [larg * 0.17, larg * 0.31, larg * 0.04, larg * 0.17, larg * 0.31]
        tp = Table(dados, colWidths=cw)
        estilo = [("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                  ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]
        for i in range(len(dados)):
            if i % 2 == 0:
                estilo += [("BACKGROUND", (0, i), (1, i), AZUL_CLARO)]
                if linhas_par[i][2]:
                    estilo += [("BACKGROUND", (3, i), (4, i), AZUL_CLARO)]
        tp.setStyle(TableStyle(estilo))
        hist.append(tp)
        hist.append(Spacer(1, 4))
        obs = ("<b>Observações.</b> O parâmetro de injeção é a massa; o tempo é ajustado pela própria máquina. "
               "Massa frio e massa calor: usar conforme a condição definida pela supervisão de produção. "
               f"{mudancas} Divisão dos componentes com {agente_nome}: isocianato {_pct(prm['iso'])} · "
               f"poliol {_pct(prm['poliol'])} · {agente_nome.split(' ')[0].lower()} {_pct(prm['agente'])} da massa.")
        hist.append(Paragraph(obs, est["txt"]))
        hist.append(Paragraph("2. Massas de injeção por item", est["sec"]))

        cab_tab = [Paragraph(t, est["th"]) for t in ("Expositor", "Item", "Descrição")] + \
                  [Paragraph(t, est["thr"]) for t in ("Massa<br/>(kg)", "Massa frio<br/>(kg)", "Massa calor<br/>(kg)")]
        linhas = [cab_tab]
        estilo = [("BACKGROUND", (0, 0), (-1, 0), AZUL), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                  ("FONTNAME", (0, 1), (-1, -1), fonte), ("FONTSIZE", (0, 1), (-1, -1), 8), ("LEADING", (0, 1), (-1, -1), 9),
                  ("ALIGN", (3, 1), (-1, -1), "RIGHT"), ("LINEBELOW", (0, 1), (-1, -1), 0.3, LINHA),
                  ("TOPPADDING", (0, 0), (-1, -1), 1.6), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.6),
                  ("BOX", (0, 0), (-1, -1), 0.5, LINHA)]
        for nome, itens in grupos.items():
            i = len(linhas)
            linhas.append([f"{nome}  ·  {len(itens)} {'item' if len(itens) == 1 else 'itens'}", "", "", "", "", ""])
            estilo += [("SPAN", (0, i), (-1, i)), ("BACKGROUND", (0, i), (-1, i), FAIXA),
                       ("FONTNAME", (0, i), (-1, i), negrito)]
            for expo, item, desc, massa, frio, calor, _delta in itens:
                linhas.append([expo, item, desc, _num(massa), _num(frio), _num(calor)])
        t = LongTable(linhas, colWidths=[larg * f for f in (0.10, 0.11, 0.43, 0.12, 0.12, 0.12)], repeatRows=1)
        t.setStyle(TableStyle(estilo))
        hist.append(KeepTogether([t]) if len(linhas) < 25 else t)
        doc.build(hist, onFirstPage=topo, onLaterPages=topo)
        arquivos.append(destino)
    return arquivos


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("planilha", type=Path)
    ap.add_argument("--saida", type=Path, default=Path("."))
    ap.add_argument("--regime", default="n-Pentano 9,15% (provisório)",
                    help="cabeçalho da coluna de regime na aba Parâmetros (linha 8)")
    ap.add_argument("--regime-desde", default="16/10/2026")
    ap.add_argument("--mudancas", default="", help="texto sobre o que mudou nesta revisão")
    a = ap.parse_args()
    a.saida.mkdir(parents=True, exist_ok=True)
    for f in gerar(a.planilha, a.saida, a.regime, a.regime_desde, a.mudancas):
        print(f)


if __name__ == "__main__":
    main()
