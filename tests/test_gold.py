from datetime import date

import pandas as pd
import pytest

from pipeline.gold import construir_gold


def _meses(ano_inicio, mes_inicio, quantidade):
    ano, mes = ano_inicio, mes_inicio
    for _ in range(quantidade):
        yield ano, mes
        ano, mes = ano + (mes == 12), mes % 12 + 1


def _silver(ipca_mensal=1.0, quantidade_meses=13):
    dolar, euro, selic, ipca = [], [], [], []
    for ano, mes in _meses(2025, 1, quantidade_meses):
        dolar += [(date(ano, mes, 2), 5.0), (date(ano, mes, 20), 6.0)]
        euro += [(date(ano, mes, 2), 6.0), (date(ano, mes, 20), 7.0)]
        selic += [(date(ano, mes, 2), 10.0), (date(ano, mes, 20), 12.0)]
        ipca.append((date(ano, mes, 1), ipca_mensal))
    cria = lambda pares: pd.DataFrame(pares, columns=["data", "valor"])  # noqa: E731
    return {"dolar": cria(dolar), "euro": cria(euro), "selic_meta": cria(selic), "ipca": cria(ipca)}


def test_agregados_mensais():
    gold = construir_gold(_silver())
    primeiro = gold.iloc[0]
    assert primeiro["mes"] == "2025-01"
    assert primeiro["dolar_medio"] == pytest.approx(5.5)
    assert primeiro["dolar_fechamento"] == pytest.approx(6.0)  # último dia útil do mês
    assert primeiro["euro_medio"] == pytest.approx(6.5)
    assert primeiro["selic_meta"] == pytest.approx(12.0)  # valor vigente no fim do mês


def test_ipca_12m_so_com_doze_meses_completos():
    gold = construir_gold(_silver(ipca_mensal=1.0))
    assert gold["ipca_12m"].iloc[:11].isna().all()
    # 12 meses de 1% ao mês: (1,01^12 - 1) * 100 = 12,68%
    assert gold["ipca_12m"].iloc[11] == pytest.approx(12.68, abs=0.01)


def test_juro_real_aproximado():
    gold = construir_gold(_silver(ipca_mensal=1.0))
    linha = gold.iloc[11]
    esperado = ((1 + 12.0 / 100) / (1 + linha["ipca_12m"] / 100) - 1) * 100
    assert linha["juro_real_aprox"] == pytest.approx(esperado, abs=0.01)


def test_mes_sem_ipca_publicado_fica_nulo():
    dados = _silver()
    dados["ipca"] = dados["ipca"].iloc[:-1]  # último IPCA ainda não divulgado
    gold = construir_gold(dados)
    assert pd.isna(gold.iloc[-1]["ipca_mes"])
    assert pd.isna(gold.iloc[-1]["ipca_12m"])
