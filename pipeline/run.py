"""Orquestrador: extract → bronze → silver (com qualidade) → gold → relatório.

Uso:
    python -m pipeline.run                 # execução normal (incremental)
    python -m pipeline.run --hoje 2026-11-12
"""

import argparse
import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Callable

import pandas as pd

from pipeline import bronze, gold, quality, report, silver
from pipeline.config import (
    DATA_INICIAL,
    DIRETORIO_DADOS,
    JANELA_REPROCESSAMENTO_DIAS,
    README,
    SERIES,
)
from pipeline.extract import buscar_serie

log = logging.getLogger("pipeline")

Buscador = Callable[[int, date, date], list[dict]]


def inicio_da_carga(historico: pd.DataFrame) -> date:
    """Primeira carga: desde DATA_INICIAL. Depois: última data conhecida menos a janela de reprocessamento."""
    if historico.empty:
        return DATA_INICIAL
    ultima = max(historico["data"])
    return max(DATA_INICIAL, ultima - timedelta(days=JANELA_REPROCESSAMENTO_DIAS))


def executar(
    hoje: date,
    diretorio: Path = DIRETORIO_DADOS,
    readme: Path = README,
    buscador: Buscador = buscar_serie,
) -> pd.DataFrame:
    novos_silver: dict[str, pd.DataFrame] = {}

    # 1. Extração + bronze + transformação (ainda em memória)
    for nome, serie in SERIES.items():
        historico = silver.ler_silver(diretorio, nome)
        inicio = inicio_da_carga(historico)
        registros = buscador(serie.codigo, inicio, hoje)
        bronze.salvar_bronze(serie, registros, inicio, hoje, hoje, diretorio)
        novos_silver[nome] = silver.mesclar(historico, silver.transformar(registros))
        log.info("%s: %s registros no histórico (antes: %s)", nome, len(novos_silver[nome]), len(historico))

    # 2. Qualidade: se falhar, nada da silver é sobrescrito
    quality.validar_tudo(novos_silver, SERIES, hoje)

    # 3. Grava silver
    for nome, df in novos_silver.items():
        silver.salvar_silver(df, diretorio, nome)

    # 4. Gold
    tabela_gold = gold.construir_gold(novos_silver)
    gold.salvar_gold(tabela_gold, diretorio)

    # 5. Relatório
    report.gerar_grafico(novos_silver, diretorio / "gold" / "grafico.png")
    report.atualizar_readme(readme, report.gerar_markdown(novos_silver, tabela_gold, hoje))

    log.info("Pipeline concluído: %s meses na gold", len(tabela_gold))
    return tabela_gold


def main() -> None:
    parser = argparse.ArgumentParser(description="Pipeline de indicadores do Banco Central")
    parser.add_argument("--hoje", type=date.fromisoformat, default=date.today(), help="data de referência (AAAA-MM-DD)")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    executar(args.hoje)


if __name__ == "__main__":
    main()
