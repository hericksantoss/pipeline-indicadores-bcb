"""Camada silver: dados tipados, limpos, sem duplicidade, um CSV por série."""

from pathlib import Path

import pandas as pd

COLUNAS = ["data", "valor"]


def transformar(registros: list[dict]) -> pd.DataFrame:
    """Converte os registros brutos do SGS em DataFrame com `data` (date) e `valor` (float)."""
    if not registros:
        return pd.DataFrame(columns=COLUNAS)

    df = pd.DataFrame(registros)
    faltando = set(COLUNAS) - set(df.columns)
    if faltando:
        raise ValueError(f"Registros sem as colunas esperadas: {sorted(faltando)}")

    df = df[COLUNAS].copy()
    df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y", errors="coerce").dt.date
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    df = df.dropna(subset=COLUNAS)
    # Se a API devolver a mesma data duas vezes, fica a última ocorrência.
    df = df.drop_duplicates(subset="data", keep="last")
    return df.sort_values("data").reset_index(drop=True)


def mesclar(existente: pd.DataFrame, novo: pd.DataFrame) -> pd.DataFrame:
    """Une o histórico com a carga nova. Em caso de conflito na mesma data, vence o dado novo
    (é assim que correções publicadas pelo BCB dentro da janela de reprocessamento entram)."""
    if existente.empty:
        return novo.sort_values("data").reset_index(drop=True)
    if novo.empty:
        return existente.sort_values("data").reset_index(drop=True)
    unido = pd.concat([existente, novo], ignore_index=True)
    unido = unido.drop_duplicates(subset="data", keep="last")
    return unido.sort_values("data").reset_index(drop=True)


def caminho_silver(diretorio: Path, nome: str) -> Path:
    return diretorio / "silver" / f"{nome}.csv"


def ler_silver(diretorio: Path, nome: str) -> pd.DataFrame:
    caminho = caminho_silver(diretorio, nome)
    if not caminho.exists():
        return pd.DataFrame(columns=COLUNAS)
    df = pd.read_csv(caminho, parse_dates=["data"])
    df["data"] = df["data"].dt.date
    return df


def salvar_silver(df: pd.DataFrame, diretorio: Path, nome: str) -> Path:
    caminho = caminho_silver(diretorio, nome)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(caminho, index=False, float_format="%.6g")
    return caminho
