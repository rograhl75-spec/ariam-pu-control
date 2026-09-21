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
