from datetime import date

import pandas as pd

from pipeline import silver


def test_transformar_tipa_limpa_e_ordena():
    registros = [
        {"data": "03/01/2025", "valor": "6.10"},
        {"data": "02/01/2025", "valor": "6.05"},
        {"data": "data-quebrada", "valor": "6.00"},
        {"data": "06/01/2025", "valor": ""},
        {"data": "02/01/2025", "valor": "6.07"},  # duplicada: fica a última
    ]
    df = silver.transformar(registros)
    assert list(df["data"]) == [date(2025, 1, 2), date(2025, 1, 3)]
    assert list(df["valor"]) == [6.07, 6.10]


def test_transformar_vazio():
    assert silver.transformar([]).empty


def test_mesclar_dado_novo_vence_em_conflito():
    existente = pd.DataFrame({"data": [date(2025, 1, 2), date(2025, 1, 3)], "valor": [1.0, 2.0]})
    novo = pd.DataFrame({"data": [date(2025, 1, 3), date(2025, 1, 6)], "valor": [2.5, 3.0]})
    unido = silver.mesclar(existente, novo)
    assert list(unido["valor"]) == [1.0, 2.5, 3.0]


def test_salvar_e_ler_silver_ida_e_volta(tmp_path):
    df = pd.DataFrame({"data": [date(2025, 1, 2)], "valor": [5.4321]})
    silver.salvar_silver(df, tmp_path, "dolar")
    lido = silver.ler_silver(tmp_path, "dolar")
    assert lido["data"].iloc[0] == date(2025, 1, 2)
    assert lido["valor"].iloc[0] == 5.4321
