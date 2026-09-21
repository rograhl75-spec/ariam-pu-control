import pandas as pd

from src.services.processo_service import ProcessoService


def test_processo_service_calcula_massa_frio_e_alerta():
    df = pd.DataFrame(
        [
            {
                "Codigo_Item": "A1",
                "Descricao": "Item teste",
                "Volume": 10,
                "Massa_Nominal": 4,
                "Massa_Frio": 3,
                "Massa_Calor": 6,
            }
        ]
    )

    out = ProcessoService().process_dataframe(df, temperatura=20)
    assert out.loc[0, "Massa_Trabalho"] == 3
    assert out.loc[0, "Condicao_Climatica"] == "FRIO"
    assert out.loc[0, "Alerta_Densidade"] == "OK"


def test_processo_service_calcula_nominal():
    df = pd.DataFrame(
        [
            {
                "Codigo_Item": "A1",
                "Descricao": "Item teste",
                "Volume": 10,
                "Massa_Nominal": 4,
                "Massa_Frio": 3,
                "Massa_Calor": 6,
            }
        ]
    )
    out = ProcessoService().process_dataframe(df, temperatura=25)
    assert out.loc[0, "Massa_Trabalho"] == 4
    assert out.loc[0, "Condicao_Climatica"] == "NOMINAL"


def test_processo_service_calcula_calor():
    df = pd.DataFrame(
        [
            {
                "Codigo_Item": "A1",
                "Descricao": "Item teste",
                "Volume": 10,
                "Massa_Nominal": 4,
                "Massa_Frio": 3,
                "Massa_Calor": 6,
            }
        ]
    )
    out = ProcessoService().process_dataframe(df, temperatura=30)
    assert out.loc[0, "Massa_Trabalho"] == 6
    assert out.loc[0, "Condicao_Climatica"] == "CALOR"


def test_processo_service_alerta_densidade_critico():
    df = pd.DataFrame(
        [
            {
                "Codigo_Item": "A1",
                "Descricao": "Item teste",
                "Volume": 1,
                "Massa_Nominal": 2.0,
                "Massa_Frio": 2.0,
                "Massa_Calor": 2.0,
            }
        ]
    )
    out = ProcessoService().process_dataframe(df, temperatura=25)
    assert out.loc[0, "Alerta_Densidade"] == "CRÍTICO"
