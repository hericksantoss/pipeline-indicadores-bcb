"""Teste ponta a ponta do pipeline, com a API falsa."""

from datetime import date, timedelta

import pytest

from pipeline import silver
from pipeline.config import DATA_INICIAL, JANELA_REPROCESSAMENTO_DIAS, SERIES
from pipeline.quality import ErroQualidade
from pipeline.run import executar


def test_primeira_carga_completa(tmp_path, readme, api_falsa):
    gold = executar(date(2026, 11, 12), diretorio=tmp_path, readme=readme, buscador=api_falsa)

    # Primeira carga busca desde a data inicial
    assert all(inicio == DATA_INICIAL for _, inicio, _ in api_falsa.chamadas)

    for nome in SERIES:
        assert (tmp_path / "bronze" / nome / "2026-11-12.json").exists()
        assert not silver.ler_silver(tmp_path, nome).empty

    assert (tmp_path / "gold" / "indicadores_mensais.csv").exists()
    assert (tmp_path / "gold" / "grafico.png").stat().st_size > 0
    assert gold["mes"].iloc[0] == "2020-01" and gold["mes"].iloc[-1] == "2026-11"

    texto = readme.read_text(encoding="utf-8")
    assert "antigo" not in texto and "rodapé" in texto
    assert "Dólar americano (venda)" in texto and "12/11/2026" in texto


def test_segunda_execucao_e_incremental(tmp_path, readme, api_falsa):
    executar(date(2026, 11, 12), diretorio=tmp_path, readme=readme, buscador=api_falsa)
    linhas_antes = len(silver.ler_silver(tmp_path, "dolar"))

    api_falsa.chamadas.clear()
    api_falsa.ultimo_dia = date(2026, 11, 12)
    executar(date(2026, 11, 13), diretorio=tmp_path, readme=readme, buscador=api_falsa)

    codigo_dolar = SERIES["dolar"].codigo
    inicio = next(ini for cod, ini, _ in api_falsa.chamadas if cod == codigo_dolar)
    assert inicio == date(2026, 11, 11) - timedelta(days=JANELA_REPROCESSAMENTO_DIAS)
    # Só entrou o dia novo; o reprocessamento não duplicou nada
    assert len(silver.ler_silver(tmp_path, "dolar")) == linhas_antes + 1


def test_falha_de_qualidade_nao_sobrescreve_silver(tmp_path, readme, api_falsa):
    executar(date(2026, 11, 12), diretorio=tmp_path, readme=readme, buscador=api_falsa)
    euro_antes = silver.ler_silver(tmp_path, "euro")

    def api_com_dolar_quebrado(codigo, inicio, fim):
        registros = api_falsa(codigo, inicio, fim)
        if codigo == SERIES["dolar"].codigo:
            registros[-1] = {"data": registros[-1]["data"], "valor": "540.0"}
        return registros

    with pytest.raises(ErroQualidade):
        executar(date(2026, 11, 12), diretorio=tmp_path, readme=readme, buscador=api_com_dolar_quebrado)

    assert silver.ler_silver(tmp_path, "euro").equals(euro_antes)
    assert silver.ler_silver(tmp_path, "dolar")["valor"].max() < 20
