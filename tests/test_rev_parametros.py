import pytest

from src.rev_parametros import carregar_revisao, formatar, localizar_revisao_vigente, sugerir_condicao
from tests.planilha_teste import REGIME, criar_planilha_teste


def test_localiza_maior_revisao(tmp_path):
    criar_planilha_teste(tmp_path, "59001000100_Parametros_e_Massas_PU_Rev02_2026-11-12.xlsx")
    criar_planilha_teste(tmp_path, "59001000100_Parametros_e_Massas_PU_Rev10_2027-01-05.xlsx")
    assert localizar_revisao_vigente(tmp_path).name.startswith("59001000100_Parametros_e_Massas_PU_Rev10")


def test_sem_planilha_explica_o_padrao(tmp_path):
    with pytest.raises(FileNotFoundError, match="RevNN"):
        localizar_revisao_vigente(tmp_path)


def test_carrega_itens_ativos_e_calcula_massas(tmp_path):
    rev = carregar_revisao(criar_planilha_teste(tmp_path), REGIME)
    assert rev.rotulo == "Rev. 03 — 13/11/2026"
    assert [i.codigo for i in rev.itens] == ["59000000001", "59000000002", "EK000001"]
    a, b, kit = rev.itens
    assert formatar(a.massa_kg) == "0,462" and formatar(a.massa_frio_kg) == "0,499"
    assert formatar(b.massa_kg) == "0,931"  # 0,9315: mesmo arredondamento da ficha impressa
    assert formatar(kit.massa_calor_kg) == "9,148"  # fator calor por fórmula: 0,96 − 150 g ÷ massa
    assert kit.vazao_g_s == 2500 and a.tempo_injecao_s() == pytest.approx(0.462 * 1000 / 600, abs=1e-3)


def test_parametros_por_cabecote_e_regime(tmp_path):
    rev = carregar_revisao(criar_planilha_teste(tmp_path), REGIME)
    assert rev.parametros_cabecote[1]["Densidade livre"] == "21,0–23,0 kg/m³"
    assert rev.parametros_cabecote[2]["Densidade livre"] == "20,0–22,5 kg/m³"
    assert rev.parametros_cabecote[1]["Vazão"] == "600 g/s (± 20)"
    assert rev.parametros_cabecote[1]["Resistência à compressão — mínimo"] == "mín. 100 kPa"
    assert rev.parametros_cabecote[1]["Temperatura das estufas"] == "35–40 °C"
    assert formatar(rev.relacao_min) == "1,274" and formatar(rev.relacao_max) == "1,326"
    assert formatar(rev.regime.pct_iso * 100, 2) == "56,52"
    assert formatar(rev.regime.pct_poliol * 100, 2) == "40,00"
    assert formatar(rev.regime.pct_agente * 100, 2) == "3,48"


def test_regime_inexistente(tmp_path):
    with pytest.raises(ValueError, match="Opções"):
        carregar_revisao(criar_planilha_teste(tmp_path), "HFO")


@pytest.mark.parametrize("temp,esperado", [(15, "frio"), (22, "nominal"), (28, "nominal"), (31, "calor")])
def test_sugestao_pelo_clima(temp, esperado):
    assert sugerir_condicao(temp) == esperado
