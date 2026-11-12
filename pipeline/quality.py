"""Checagens de qualidade. Se alguma falhar, o pipeline para antes de gravar a silver."""

from datetime import date

import pandas as pd

from pipeline.config import FRESCOR_MAXIMO_DIAS, Serie


class ErroQualidade(Exception):
    pass


def checar(df: pd.DataFrame, serie: Serie, hoje: date) -> list[str]:
    """Retorna a lista de problemas encontrados (vazia se estiver tudo certo)."""
    problemas: list[str] = []
    prefixo = f"[{serie.nome}]"

    if df.empty:
        return [f"{prefixo} série vazia"]

    if df["data"].isna().any() or df["valor"].isna().any():
        problemas.append(f"{prefixo} há valores nulos")

    duplicadas = int(df["data"].duplicated().sum())
    if duplicadas:
        problemas.append(f"{prefixo} {duplicadas} datas duplicadas")

    fora = df[(df["valor"] < serie.valor_min) | (df["valor"] > serie.valor_max)]
    if not fora.empty:
        exemplo = fora.iloc[0]
        problemas.append(
            f"{prefixo} {len(fora)} valores fora da faixa [{serie.valor_min}, {serie.valor_max}], "
            f"ex.: {exemplo['data']} = {exemplo['valor']}"
        )

    if any(d > hoje for d in df["data"]):
        problemas.append(f"{prefixo} há datas no futuro")

    ultima = max(df["data"])
    atraso = (hoje - ultima).days
    limite = FRESCOR_MAXIMO_DIAS[serie.frequencia]
    if atraso > limite:
        problemas.append(f"{prefixo} dado desatualizado: último em {ultima} ({atraso} dias, limite {limite})")

    return problemas


def validar_tudo(dados: dict[str, pd.DataFrame], series: dict[str, Serie], hoje: date) -> None:
    problemas = [p for nome, df in dados.items() for p in checar(df, series[nome], hoje)]
    if problemas:
        raise ErroQualidade("Checagem de qualidade falhou:\n- " + "\n- ".join(problemas))
