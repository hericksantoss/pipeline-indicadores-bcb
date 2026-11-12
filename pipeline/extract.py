"""Extração: busca as séries na API pública do SGS do Banco Central."""

import logging
import time
from datetime import date, timedelta

import requests

from pipeline.config import JANELA_MAXIMA_CONSULTA_DIAS

log = logging.getLogger(__name__)

URL_BASE = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"


class ErroExtracao(Exception):
    pass


def _janelas(inicio: date, fim: date, tamanho_dias: int) -> list[tuple[date, date]]:
    """Quebra o intervalo [inicio, fim] em janelas de no máximo `tamanho_dias`."""
    janelas = []
    atual = inicio
    while atual <= fim:
        fim_janela = min(atual + timedelta(days=tamanho_dias - 1), fim)
        janelas.append((atual, fim_janela))
        atual = fim_janela + timedelta(days=1)
    return janelas


def _buscar_janela(
    codigo: int,
    inicio: date,
    fim: date,
    sessao: requests.Session,
    tentativas: int,
    espera_base: float,
) -> list[dict]:
    params = {
        "formato": "json",
        "dataInicial": inicio.strftime("%d/%m/%Y"),
        "dataFinal": fim.strftime("%d/%m/%Y"),
    }
    url = URL_BASE.format(codigo=codigo)

    for tentativa in range(1, tentativas + 1):
        try:
            resposta = sessao.get(url, params=params, timeout=30)
            # O SGS responde 404 quando não há nenhum valor no período (ex.: feriado).
            if resposta.status_code == 404:
                return []
            resposta.raise_for_status()
            dados = resposta.json()
            if not isinstance(dados, list):
                raise ErroExtracao(f"Resposta inesperada da série {codigo}: {dados!r:.200}")
            return dados
        except (requests.RequestException, ValueError) as erro:
            if tentativa == tentativas:
                raise ErroExtracao(
                    f"Falha ao buscar série {codigo} ({inicio} a {fim}) após {tentativas} tentativas"
                ) from erro
            espera = espera_base * 2 ** (tentativa - 1)
            log.warning("Série %s: tentativa %s falhou (%s). Nova tentativa em %.0fs", codigo, tentativa, erro, espera)
            time.sleep(espera)
    return []  # inalcançável, mantém o type checker feliz


def buscar_serie(
    codigo: int,
    inicio: date,
    fim: date,
    sessao: requests.Session | None = None,
    tentativas: int = 3,
    espera_base: float = 2.0,
) -> list[dict]:
    """Retorna os registros brutos ({"data": "dd/mm/aaaa", "valor": "1.23"}) da série no período."""
    if inicio > fim:
        return []
    sessao = sessao or requests.Session()
    registros: list[dict] = []
    for ini, fi in _janelas(inicio, fim, JANELA_MAXIMA_CONSULTA_DIAS):
        registros.extend(_buscar_janela(codigo, ini, fi, sessao, tentativas, espera_base))
    log.info("Série %s: %s registros extraídos (%s a %s)", codigo, len(registros), inicio, fim)
    return registros
