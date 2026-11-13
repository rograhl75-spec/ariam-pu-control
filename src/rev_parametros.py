"""Leitura da planilha controlada 59001000100_Parametros_e_Massas_PU_RevNN_AAAA-MM-DD.xlsx.

A planilha é a fonte única de massas e parâmetros. As massas são recalculadas aqui
a partir das entradas (volume, densidade moldada e fatores), para funcionar mesmo
quando o arquivo foi salvo sem os valores calculados das fórmulas.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import openpyxl

PADRAO_ARQUIVO = re.compile(r"59001000100_Parametros_e_Massas_PU_Rev(\d+)_(\d{4})-(\d{2})-(\d{2})\.xlsx$")
_FATOR_CALOR_FORMULA = re.compile(r"^=\s*([\d.]+)\s*-\s*([\d.]+)\s*/\s*1000\s*/\s*I\d+\s*$")


@dataclass(frozen=True)
class Item:
    cabecote: int
    expositor: str
    componente: str
    codigo: str
    descricao: str
    volume_m3: float
    densidade_moldada: float
    massa_kg: float
    massa_frio_kg: float
    massa_calor_kg: float
    vazao_g_s: float

    def massa_condicao(self, condicao: str) -> float:
        return {"frio": self.massa_frio_kg, "calor": self.massa_calor_kg}.get(condicao, self.massa_kg)

    def tempo_injecao_s(self, condicao: str = "nominal") -> float:
        return self.massa_condicao(condicao) * 1000 / self.vazao_g_s if self.vazao_g_s else 0.0


@dataclass(frozen=True)
class Regime:
    nome: str
    pct_pre_mistura: float
    pct_iso: float
    pct_poliol: float
    pct_agente: float


@dataclass
class Revisao:
    arquivo: Path
    numero: int
    data: str
    relacao_ip: float
    relacao_tol: float
    temp_tanques: str
    regime: Regime
    parametros_cabecote: dict[int, dict[str, str]] = field(default_factory=dict)
    itens: list[Item] = field(default_factory=list)

    @property
    def rotulo(self) -> str:
        return f"Rev. {self.numero:02d} — {self.data}"

    @property
    def relacao_min(self) -> float:
        return self.relacao_ip * (1 - self.relacao_tol)

    @property
    def relacao_max(self) -> float:
        return self.relacao_ip * (1 + self.relacao_tol)


def localizar_revisao_vigente(pasta: str | Path) -> Path:
    """Retorna o arquivo de maior número de revisão na pasta."""
    candidatos = []
    for arq in Path(pasta).glob("59001000100_Parametros_e_Massas_PU_Rev*.xlsx"):
        m = PADRAO_ARQUIVO.search(arq.name)
        if m:
            candidatos.append((int(m.group(1)), arq))
    if not candidatos:
        raise FileNotFoundError(
            f"Nenhuma planilha 59001000100_Parametros_e_Massas_PU_RevNN_AAAA-MM-DD.xlsx em {Path(pasta).resolve()}"
        )
    return max(candidatos)[1]


def _texto(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float):
        return f"{v:g}".replace(".", ",")
    return str(v).strip()


def _fator(valor, massa: float, linha: int, coluna: str) -> float:
    if isinstance(valor, (int, float)):
        return float(valor)
    m = _FATOR_CALOR_FORMULA.match(str(valor or ""))
    if m:
        return float(m.group(1)) - float(m.group(2)) / 1000 / massa
    raise ValueError(f"Fator na linha {linha}, coluna {coluna}, não reconhecido: {valor!r}")


def carregar_revisao(arquivo: str | Path, regime: str) -> Revisao:
    """Carrega parâmetros e itens ativos. `regime` é o cabeçalho da coluna na aba Parâmetros (linha 8)."""
    arquivo = Path(arquivo)
    m = PADRAO_ARQUIVO.search(arquivo.name)
    if not m:
        raise ValueError("Nome fora do padrão 59001000100_Parametros_e_Massas_PU_RevNN_AAAA-MM-DD.xlsx")
    wb = openpyxl.load_workbook(arquivo, data_only=False)
    p = wb["Parâmetros"]

    colunas_regime = {_texto(p[f"{c}8"].value): c for c in "DEF"}
    if regime not in colunas_regime:
        raise ValueError(f"Regime '{regime}' não existe na planilha. Opções: {', '.join(colunas_regime)}")
    rc = colunas_regime[regime]
    pct = float(p[f"{rc}10"].value)
    relacao = float(p["D11"].value)
    partes_agente = 100 * pct / (1 - pct)
    partes_iso = relacao * (100 + partes_agente)
    total = partes_iso + 100 + partes_agente
    reg = Regime(regime, pct, partes_iso / total, 100 / total, partes_agente / total)

    params: dict[int, dict[str, str]] = {1: {}, 2: {}}
    vazao = {1: 0.0, 2: 0.0}
    for r in range(36, 49):
        rotulo = _texto(p[f"B{r}"].value)
        if not rotulo:
            continue
        unidade, tol = _texto(p[f"C{r}"].value), _texto(p[f"F{r}"].value)
        for cab, col in ((1, "D"), (2, "E")):
            valor = p[f"{col}{r}"].value
            if rotulo == "Vazão":
                vazao[cab] = float(valor)
            if isinstance(valor, float) and unidade.startswith("%"):
                txt = f"{valor * 100:g}%".replace(".", ",")
            else:
                txt = f"{_texto(valor)} {unidade}".strip()
            if tol and tol not in {"—", "mínimo"}:
                txt += f" ({tol})"
            elif tol == "mínimo":
                txt = f"mín. {txt}"
            params[cab][rotulo] = txt

    rev = Revisao(arquivo=arquivo, numero=int(m.group(1)), data=f"{m.group(4)}/{m.group(3)}/{m.group(2)}",
                  relacao_ip=relacao, relacao_tol=float(p["D12"].value), temp_tanques=_texto(p["D29"].value),
                  regime=reg, parametros_cabecote=params)

    ws = wb["Massas"]
    for r in range(6, ws.max_row + 1):
        if ws.cell(r, 1).value != "Ativo":
            continue
        cab = int(ws.cell(r, 2).value)
        volume, dens = float(ws.cell(r, 7).value), float(ws.cell(r, 8).value)
        massa = volume * dens
        frio = massa * _fator(ws.cell(r, 10).value, massa, r, "J")
        calor = massa * _fator(ws.cell(r, 12).value, massa, r, "L")
        rev.itens.append(Item(cab, _texto(ws.cell(r, 3).value), _texto(ws.cell(r, 4).value),
                              _texto(ws.cell(r, 5).value), _texto(ws.cell(r, 6).value),
                              volume, dens, massa, frio, calor, vazao[cab]))
    return rev


def sugerir_condicao(temp_externa_c: float, limite_frio_c: float = 22.0, limite_calor_c: float = 28.0) -> str:
    """Sugestão pela temperatura externa. A decisão final é da supervisão de produção."""
    if temp_externa_c < limite_frio_c:
        return "frio"
    if temp_externa_c > limite_calor_c:
        return "calor"
    return "nominal"


def formatar(valor: float, casas: int = 3) -> str:
    """Formata com vírgula decimal, igual às fichas: normaliza para 15 dígitos (como o Excel guarda)
    e arredonda o valor resultante, de modo que a tela mostre o mesmo número da ficha impressa."""
    v = float(f"{valor:.15g}")
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
