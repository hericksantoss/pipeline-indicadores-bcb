from datetime import date

import pandas as pd
import pytest

from pipeline.config import SERIES
from pipeline.quality import ErroQualidade, checar, validar_tudo

HOJE = date(2026, 11, 12)


def _df(pares):
    return pd.DataFrame(pares, columns=["data", "valor"])


def test_serie_saudavel_passa():
    df = _df([(date(2026, 11, 10), 5.4), (date(2026, 11, 11), 5.5)])
    assert checar(df, SERIES["dolar"], HOJE) == []


def test_detecta_valor_fora_da_faixa():
    df = _df([(date(2026, 11, 11), 54.0)])  # vírgula no lugar errado, por exemplo
    problemas = checar(df, SERIES["dolar"], HOJE)
    assert any("fora da faixa" in p for p in problemas)


def test_detecta_dado_desatualizado():
    df = _df([(date(2026, 10, 1), 5.4)])
    problemas = checar(df, SERIES["dolar"], HOJE)
    assert any("desatualizado" in p for p in problemas)


def test_ipca_mensal_tolera_defasagem_de_publicacao():
    df = _df([(date(2026, 9, 1), 0.4)])
    assert checar(df, SERIES["ipca"], HOJE) == []


def test_detecta_duplicadas_e_vazia():
    df = _df([(date(2026, 11, 11), 5.4), (date(2026, 11, 11), 5.5)])
    assert any("duplicadas" in p for p in checar(df, SERIES["dolar"], HOJE))
    assert checar(_df([]), SERIES["dolar"], HOJE) == ["[dolar] série vazia"]


def test_validar_tudo_junta_todos_os_problemas():
    dados = {"dolar": _df([(date(2026, 11, 11), 99.0)]), "euro": _df([])}
    with pytest.raises(ErroQualidade) as erro:
        validar_tudo(dados, SERIES, HOJE)
    assert "[dolar]" in str(erro.value) and "[euro]" in str(erro.value)
