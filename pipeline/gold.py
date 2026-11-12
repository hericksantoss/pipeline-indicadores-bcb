"""Camada gold: indicadores mensais calculados em SQL (SQLite em memória) a partir da silver."""

import math
import sqlite3
from pathlib import Path

import pandas as pd

SQL_GOLD = Path(__file__).parent / "sql" / "gold_indicadores_mensais.sql"


def _ln(x):
    return math.log(x) if x is not None else None


def _exp(x):
    return math.exp(x) if x is not None else None


def construir_gold(silver: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Carrega as tabelas silver num SQLite em memória e executa a query da gold."""
    with sqlite3.connect(":memory:") as conexao:
        conexao.create_function("LN", 1, _ln, deterministic=True)
        conexao.create_function("EXP", 1, _exp, deterministic=True)
        for nome, df in silver.items():
            # Datas viram texto ISO (AAAA-MM-DD) para ordenar e cortar com substr no SQL.
            tabela = df.assign(data=df["data"].astype(str))
            tabela.to_sql(nome, conexao, index=False)
        return pd.read_sql_query(SQL_GOLD.read_text(encoding="utf-8"), conexao)


def salvar_gold(df: pd.DataFrame, diretorio: Path) -> Path:
    caminho = diretorio / "gold" / "indicadores_mensais.csv"
    caminho.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(caminho, index=False)
    return caminho
