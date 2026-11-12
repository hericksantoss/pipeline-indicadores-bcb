"""Camada bronze: guarda a resposta da API exatamente como veio, com metadados da extração."""

import json
from datetime import date, datetime, timezone
from pathlib import Path

from pipeline.config import Serie


def salvar_bronze(
    serie: Serie,
    registros: list[dict],
    inicio: date,
    fim: date,
    data_execucao: date,
    diretorio: Path,
) -> Path:
    """Grava um arquivo JSON por série e por dia de execução. Reexecutar no mesmo dia sobrescreve."""
    pasta = diretorio / "bronze" / serie.nome
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / f"{data_execucao.isoformat()}.json"
    conteudo = {
        "serie": serie.nome,
        "codigo_sgs": serie.codigo,
        "extraido_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "periodo_inicio": inicio.isoformat(),
        "periodo_fim": fim.isoformat(),
        "quantidade": len(registros),
        "registros": registros,
    }
    caminho.write_text(json.dumps(conteudo, ensure_ascii=False, indent=1), encoding="utf-8")
    return caminho
